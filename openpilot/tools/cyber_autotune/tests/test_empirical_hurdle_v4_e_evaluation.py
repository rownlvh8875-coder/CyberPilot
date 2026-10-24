"""Synthetic E numerical/causal contracts. No actual permit or private input."""

import unittest
from unittest.mock import patch
import gzip
import io
import itertools
import tempfile
from pathlib import Path
import json

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as decision
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_evaluation as evaluation
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as inputs
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_publication as publication


def fixture_model(length=1):
  dim = 2 * length + 3
  norm = {'mean': np.zeros(dim), 'std': np.ones(dim), 'constant': np.zeros(dim, bool), 'effective': np.arange(dim), 'constant_reference': np.zeros(dim)}
  static = [i for i in range(dim) if i != dim - 3]
  return {
    'normalizer': norm,
    'heads': {0: {'positions': static, 'coefficients': np.zeros(dim - 1)}, 1: {'positions': list(range(dim)), 'coefficients': np.zeros(dim)}},
  }, {'normalizer': norm, 'coefficients': np.r_[1.0, np.zeros(dim - 1)]}


class TestEDecision(unittest.TestCase):
  def test_exhaustive_small_synthetic_objective(self):
    p = np.array([0.0, 0.25, 0.25, 1.0])
    for labels in itertools.product((False, True), repeat=4):
      if not 0 < sum(labels) < 4:
        continue
      y = np.array(labels)
      positive, negative = int(y.sum()), int((~y).sum())
      keys = []
      for value in sorted({0.0, 1.0, *p}):
        gate = p > value
        tp, tn = int(np.count_nonzero(gate & y)), int(np.count_nonzero(~gate & ~y))
        keys.append((tp * negative + tn * positive, tn, value))
      result = decision.select_context(p, y, role='TRAIN')
      self.assertEqual((result['BA_NUM'], result['TN'], result['decision']), max(keys))

  def test_exact_integer_objective_and_ties(self):
    p = np.array([0.1, 0.2, 0.7, 0.9], np.float64)
    y = np.array([False, False, True, True])
    selected = decision.select_context(p, y, role='TRAIN')
    self.assertEqual(selected['decision'], 0.2)
    self.assertEqual(selected['BA_NUM'], 8)
    self.assertIs(type(selected['BA_NUM']), int)
    self.assertEqual(selected['TN'], 2)

  def test_constant_scores_choose_larger_decision(self):
    row = decision.select_context(np.full(4, 0.5), np.array([False, True, False, True]), role='TRAIN')
    self.assertEqual(row['decision'], 1.0)
    self.assertEqual(row['TN'], 2)

  def test_signed_zero_and_endpoints(self):
    row = decision.select_context(np.array([-0.0, 0.0, 1.0, 1.0]), np.array([False, False, True, True]), role='TRAIN')
    self.assertEqual(row['decision'], 0.0)
    self.assertFalse(np.signbit(row['decision']))
    self.assertEqual(row['candidate_count'], 2)

  def test_only_train_and_both_classes(self):
    for role in ('DEV', 'HOLDOUT'):
      with self.assertRaises(ValueError):
        decision.select_context(np.array([0.1, 0.9]), np.array([False, True]), role=role)
    for y in (np.zeros(2, bool), np.ones(2, bool)):
      with self.assertRaises(ValueError):
        decision.select_context(np.array([0.1, 0.9]), y, role='TRAIN')

  def test_invalid_probability_label_and_shape(self):
    for p in (np.array([np.nan, 1.0]), np.array([np.inf, 1.0]), np.array([-0.1, 1.0]), np.array([0.1, 1.1]), np.ones((2, 1)), np.ones(2, np.float32)):
      with self.assertRaises(ValueError):
        decision.select_context(p, np.array([False, True]), role='TRAIN')
    with self.assertRaises(ValueError):
      decision.select_context(np.array([0.1, 0.9]), np.array([0, 1], np.int64), role='TRAIN')

  def test_two_contexts_bound_to_original_train_rows(self):
    p = np.array([0.1, 0.2, 0.6, 0.7])
    y = np.array([False, True, False, True])
    prior = np.array([0, 0, -1, 1], np.int64)
    r = decision.select_job(p, y, prior, candidate='HRI_D00_L01', fold='FOLD_A', anchor='a' * 64, role='TRAIN')
    self.assertEqual(r['contexts']['PREVIOUS_STATIC']['decision'], 0.1)
    self.assertEqual(r['contexts']['PREVIOUS_MOVE']['decision'], 0.6)
    self.assertEqual(r['candidate_id'], 'HRI_D00_L01')
    self.assertEqual(r['count'], 4)

  def test_strict_equality_static_and_context_routing(self):
    p = np.array([0.3, 0.3, 0.8, 0.8])
    prior = np.array([0, 1, 0, -1], np.int64)
    self.assertEqual(decision.gate(p, prior, (0.3, 0.8)).tolist(), [False, False, True, False])

  def test_wrong_identity_or_prior_type_fail(self):
    with self.assertRaises(ValueError):
      decision.select_job(
        np.array([0.1, 0.9]), np.array([False, True]), np.array([0, 1], np.int32), candidate='HRI_D00_L01', fold='FOLD_A', anchor='a' * 64, role='TRAIN'
      )
    with self.assertRaises(ValueError):
      decision.select_job(
        np.array([0.1, 0.9]), np.array([False, True]), np.array([0, 1], np.int64), candidate='D2', fold='FOLD_A', anchor='a' * 64, role='TRAIN'
      )


class TestEEvaluation(unittest.TestCase):
  def test_two_repeats_of_complete_synthetic_job_all_horizons(self):
    # Explicit fixture only: no model fitting, filesystem evidence or source logs.
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data

    clauses = json.loads((Path(__file__).resolve().parents[4] / 'docs/cyberpilot/changes/empirical-hurdle-acceptance-gate-v1.json').read_bytes())['clauses']
    for candidate in ('HRI_D00_L01', 'HRI_D20_L45'):
      length = int(candidate[-2:])
      model, stage2 = fixture_model(length)
      tick = np.resize(np.array([0, 0, 1, 2, 2, 2, 1, 0, 0], np.int64), 1000)
      segment = {
        'tick': tick,
        'command': np.zeros(1000),
        'speed': np.full(1000, 10.0),
        'streak': np.arange(1, 1001, dtype=np.int64),
        'segment_sha256': '1' * 64,
      }
      segments = [segment]
      _, anchor, x, current, target = data.design(segments, candidate)
      p = evaluation.frozen.probability(x, model)
      expected = {
        'one_step': data.pair((current - target).astype(float), (current - target).astype(float), anchor, current, target, current),
        'true_move': data.pair(
          (current[target != current] - target[target != current]).astype(float),
          (current[target != current] - target[target != current]).astype(float),
          data.subset_sha(anchor, target != current),
          current[target != current],
          target[target != current],
          current[target != current],
        ),
        'rollout': {},
      }

      class FixtureProvider:
        def one_step(self, *_args, p=p, current=current, target=target, x=x):
          return {
            'p_move': p,
            'predicted_gate': np.zeros(len(p), bool),
            'integrated_delta': np.zeros(len(p)),
            'projected_next_tick': current.astype(np.int16),
            'candidate_error': (current - target).astype(float),
            'true_move': target != current,
            'prior_delta_tick': x[:, -3].astype(np.int64),
          }

        def rollout(self, _candidate, _fold, h, segments=segments, candidate=candidate, tick=tick, expected=expected):
          blocks, digest, _ = data.binding(segments, candidate, h)
          indices = blocks[0][1]
          observed = tick[indices[:, None] + np.arange(h + 1)]
          old = np.repeat(observed[:, :1], h + 1, axis=1)
          error = (old[:, -1] - observed[:, -1]).astype(float)
          moved = evaluation.path_moved(observed)
          expected['rollout'][str(h)] = {
            'overall': data.pair(error, error, digest),
            'path_moved': data.pair(error[moved], error[moved], data.subset_sha(digest, moved)),
            'path_moved_count': int(moved.sum()),
            'status': 'COMPLETE',
          }
          return {'projected_path': old.astype(np.int16), 'predicted_gate_path': np.zeros((len(indices), h), bool), 'candidate_error': error}

      results = []
      for _ in range(2):
        chosen = decision.select_job(p, target != current, x[:, -3].astype(np.int64), candidate=candidate, fold='FOLD_A', anchor=anchor, role='TRAIN')
        values = tuple(chosen['contexts'][context]['decision'] for context in ('PREVIOUS_STATIC', 'PREVIOUS_MOVE'))
        counters = {}
        result = evaluation.evaluate_job(segments, candidate, 'FOLD_A', model, values, stage2, FixtureProvider(), expected, clauses, counters)
        self.assertEqual(len(result['arms']['D1']['gate']['clauses']), 32)
        self.assertEqual(set(result['arms']['D1']['rollout']), {'25', '50', '100', '200'})
        self.assertTrue(counters['recursive_chunk_calls'] > 0)
        results.append(evaluation.canonical({'result': result, 'counters': counters}))
      self.assertEqual(*results)

  def test_gate_move_can_realize_hold_and_static_never_moves(self):
    model, stage2 = fixture_model()
    stage2['coefficients'][0] = 0.25
    x = np.array([[1, 0, 0, 2, 10], [1, 0, 1, 2, 10]], np.float64)
    result = evaluation.integrated(x, np.array([2, 2], np.int64), model, (0.0, 1.0), stage2, {})
    self.assertEqual(result['gate'].tolist(), [True, False])
    self.assertEqual(result['projected'].tolist(), [2, 2])

  def test_projection_uses_ties_to_even_and_signed16_fail_closed(self):
    self.assertEqual(evaluation.frozen.m.project(np.array([0.5, 1.5, -0.5, -1.5])).tolist(), [0, 2, 0, -2])
    with self.assertRaises(ValueError):
      evaluation.frozen.m.project(np.array([32767.5]))

  def test_recursive_uses_realized_delta_not_gate_bit(self):
    model, stage2 = fixture_model()
    stage2['coefficients'][0] = 0.25
    path, gates, contexts = evaluation.recursive(
      np.array([[0, 0]], np.int64), np.zeros((1, 25)), np.ones((1, 25)), 'HRI_D00_L01', model, (0.0, 1.0), stage2, 25, {}
    )
    self.assertTrue(np.all(gates))
    self.assertFalse(np.any(contexts))
    self.assertFalse(np.any(path))

  def test_recursive_full_numeric_history_and_context_update(self):
    model, stage2 = fixture_model(5)
    initial = np.array([[0, 1, 2, 3, 4, 4]], np.int64)
    seen = []
    original = evaluation.integrated

    def capture(x, *args):
      seen.append(x.copy())
      return original(x, *args)

    with patch.object(evaluation, 'integrated', side_effect=capture):
      path, _, context = evaluation.recursive(initial, np.zeros((1, 29)), np.ones((1, 25)), 'HRI_D00_L05', model, (0.0, 0.0), stage2, 25, {})
    self.assertEqual(path[0, :3].tolist(), [4, 5, 6])
    self.assertEqual(seen[0][0, 9:11].tolist(), [1, 0])
    self.assertEqual(seen[1][0, 9:11].tolist(), [0, 1])
    self.assertEqual(context[0, :2].tolist(), [False, True])

  def test_recursive_invalid_horizon_history_and_truth_argument(self):
    model, stage2 = fixture_model()
    for h in (1, 20, 201):
      with self.assertRaises(ValueError):
        evaluation.recursive(np.array([[0, 0]], np.int64), np.zeros((1, h)), np.ones((1, h)), 'HRI_D00_L01', model, (0.0, 0.0), stage2, h, {})
    with self.assertRaises(TypeError):
      evaluation.recursive(
        np.array([[0, 0]], np.int64), np.zeros((1, 25)), np.ones((1, 25)), 'HRI_D00_L01', model, (0.0, 0.0), stage2, 25, {}, future_truth=np.zeros((1, 26))
      )

  def test_four_population_and_exact_hit_decomposition(self):
    current = np.array([0, 0, 0, 0], np.int64)
    target = np.array([0, 1, 0, 1], np.int64)
    prior = np.array([0, 0, 1, 1], np.int64)
    result = {'gate': np.array([True, True, True, False]), 'projected': np.array([0, 1, 1, 0], np.int64), 'delta': np.array([0.2, 1.0, 1.0, 0.0])}
    r = evaluation.tick_diagnostics(current, target, prior, result)
    self.assertEqual(r['exact_hit']['static_hit_loss'], 1)
    self.assertEqual(r['exact_hit']['move_hit_gain'], 1)
    self.assertEqual(r['exact_hit']['net_delta'], 0)
    self.assertEqual(r['gate_FP'], 2)
    self.assertEqual(r['FP_projected_HOLD'], 1)
    self.assertEqual(r['harmful_false_movement'], 1)
    self.assertEqual(r['transitions']['MOVE_TERMINATION']['move_gate'], 1)

  def test_path_moved_is_observed_truth_definition(self):
    observed = np.array([[0, 0, 0], [0, 1, 0]], np.int64)
    self.assertEqual(evaluation.path_moved(observed).tolist(), [False, True])

  def test_undefined_ratio_not_fabricated(self):
    self.assertIsNone(evaluation.ratio(0, 0))

  def test_resume_rejects_empty_unsealed_or_incomplete_payload(self):
    for value in (
      {'schema': 'V4_E_CANONICAL_RESULT_V1', 'jobs': [], 'protocol_sha256': 'a' * 64},
      evaluation.seal({'schema': 'V4_E_CANONICAL_RESULT_V1', 'jobs': [], 'protocol_sha256': 'a' * 64}),
    ):
      raw = evaluation.canonical(value)
      with patch.object(evaluation, 'recursive', side_effect=AssertionError), patch.object(decision, 'select_job', side_effect=AssertionError):
        with self.assertRaises(ValueError):
          evaluation.verify_only(raw, evaluation.sha(raw), 'a' * 64)

  def test_numerical_failure_precedence_survives_later_support_failure(self):
    from unittest.mock import Mock

    expected = {'one_step': {}, 'true_move': {}, 'rollout': {str(h): {'status': 'COMPLETE', 'overall': {}} for h in evaluation.HORIZONS}}
    arms = {a: {'status': 'DEVELOPMENT_OR_ROLLOUT_FAILURE', 'one_step': {}, 'true_move': {}, 'rollout': {}} for a in ('D0', 'D1')}

    def roll(*args):
      h = args[5]
      return {'D0': expected['rollout'][str(h)], 'D1': {'status': 'NUMERICAL_FAILURE' if h == 25 else 'V4_ROLLOUT_SUPPORT_FAILURE'}}

    with (
      patch.object(evaluation, 'one_step', return_value=arms),
      patch.object(evaluation, 'rollout', side_effect=roll),
      patch.object(evaluation.gates, 'fold_gate', return_value={'pass': False}),
    ):
      row = evaluation.evaluate_job([], 'HRI_D00_L01', 'FOLD_A', {}, (0.0, 0.0), {}, Mock(), expected, [], {})
    self.assertEqual(row['arms']['D1']['status'], 'DEVELOPMENT_OR_ROLLOUT_FAILURE')

  def test_nontrivial_equal_decisions_match_frozen_math(self):
    rng = np.random.default_rng(753)
    for length in (1, 5, 45):
      model, stage2 = fixture_model(length)
      dim = 2 * length + 3
      model['normalizer']['mean'] = rng.normal(size=dim)
      model['normalizer']['std'] = rng.uniform(0.5, 2, size=dim)
      for head in model['heads'].values():
        head['coefficients'] = rng.normal(0, 0.02, len(head['positions']))
      stage2['coefficients'] = rng.normal(0, 0.02, dim)
      candidate = f'HRI_D05_L{length:02d}'
      initial = rng.integers(-2, 3, size=(8, length + 1), dtype=np.int64)
      command, speed = rng.normal(size=(8, length + 24)), rng.uniform(1, 3, size=(8, 25))
      expected = evaluation.frozen.recursive(initial, command, speed, candidate, model, 0.5, stage2, 25)
      actual = evaluation.recursive(initial, command, speed, candidate, model, (0.5, 0.5), stage2, 25, {})
      for old, new in zip(expected[:2], actual[:2], strict=True):
        self.assertEqual(old.tobytes(), new.tobytes())

  def test_drift_next_bit_lag_first_events_and_support(self):
    initial = np.array([[0, 0], [0, 1]], np.int64)
    observed = np.array([[0, 1, 1], [1, 1, 2]], np.int64)
    path = np.array([[0, 0, 1], [1, 1, 2]], np.int64)
    gate = np.array([[True, True], [False, True]])
    context = np.array([[False, False], [True, False]])
    row, perfect, movement = evaluation.drift_chunk(initial, observed, path, gate, context, 1)
    self.assertEqual(row['movement_mismatch'].tolist(), [1, 1])
    self.assertEqual(row['context_mismatch'].tolist(), [0, 1])
    self.assertEqual(row['first_gate_error'].tolist(), [0, 1, 1])
    self.assertEqual(perfect.tolist(), [False, True])
    self.assertEqual(movement.tolist(), [False, True])
    for n, state in ((0, 'EMPTY'), (200, 'SMALL'), (201, 'FULL')):
      self.assertEqual(evaluation.subset_support(np.zeros(201), np.zeros(201), np.arange(201) < n)['support'], state)
    context[0, 1] = True
    with self.assertRaisesRegex(ValueError, 'NEXT_CONTEXT'):
      evaluation.drift_chunk(initial, observed, path, gate, context, 1)

  def test_continuous_and_projected_residual_are_separate(self):
    current, target, prior = np.zeros(201, np.int64), np.ones(201, np.int64), np.zeros(201, np.int64)
    row = evaluation.tick_diagnostics(current, target, prior, {'gate': np.ones(201, bool), 'projected': target.copy(), 'delta': np.full(201, 0.7)})[
      'transitions'
    ]['MOVE_ONSET']
    self.assertAlmostEqual(row['gate_TP_magnitude_residual']['rmse'], 0.3)
    self.assertEqual(row['gate_TP_projected_step_residual']['rmse'], 0)

  def test_d0_empty_moved_support_preserves_original_nonpass(self):
    model, stage2 = fixture_model()
    segment = {
      'tick': np.zeros(500, np.int64),
      'command': np.zeros(500),
      'speed': np.ones(500),
      'streak': np.arange(1, 501, dtype=np.int64),
      'segment_sha256': '1' * 64,
    }
    expected, saved = evaluation.frozen.rollout([segment], 'HRI_D00_L01', model, 1.0, stage2, 25)
    row = evaluation.rollout([segment], 'HRI_D00_L01', model, (1.0, 1.0), stage2, 25, saved, expected['overall'], {})
    self.assertEqual(row['D0'], expected)
    self.assertEqual(row['D1']['moved_gate_perfect']['support'], 'EMPTY')
    self.assertEqual(row['D1']['status'], 'V4_ROLLOUT_SUPPORT_FAILURE')


class TestEInputs(unittest.TestCase):
  def test_exact_file_guard_rejects_symlink_alias_wrong_hash_and_oversize(self):
    with tempfile.TemporaryDirectory() as tmp:
      base = Path(tmp)
      owners = {name: str(base / name) for name in ('V4', 'V1', 'V1_TOP', 'CAUSAL', 'DERIVED')}
      for path in owners.values():
        Path(path).mkdir()
      target = Path(owners['V4']) / 'manifest.json'
      target.write_bytes(b'fixture')
      identity = (base.stat().st_dev, base.stat().st_ino)
      for digest, cap in ((evaluation.sha(b'wrong'), 100), (evaluation.sha(b'fixture'), 2)):
        reader = inputs.Reader(owners, tmp, identity, inputs.Phase())
        with self.assertRaises(ValueError):
          reader.raw('V4', 'manifest.json', 'metadata', digest, cap)
      target.unlink()
      outside = base / 'other.json'
      outside.write_bytes(b'fixture')
      target.symlink_to(outside)
      reader = inputs.Reader(owners, tmp, identity, inputs.Phase())
      with self.assertRaises(ValueError):
        reader.raw('V4', 'manifest.json', 'metadata', evaluation.sha(b'fixture'), 100)

  def test_exact_member_classes_reject_mixed_carrier_and_extra_models(self):
    candidate = 'candidates/HRI_D00_L01/FOLD_A/'
    for owner, member, kind in [
      ('V4', candidate + 'train/receipt.json', 'metadata'),
      ('V1', candidate + 'stage1/model/coefficients.npy.gz', 'array'),
      ('V1', candidate + 'decision/threshold.npy.gz', 'array'),
      ('V4', candidate + 'train/MOVE_coefficients.npy.gz', 'metadata'),
      ('V4', candidate.replace('D00', 'D01') + 'one-step/p_move.npy.gz', 'array'),
      ('V4', '../manifest.json', 'metadata'),
    ]:
      with self.assertRaises(ValueError):
        inputs.member_allowed(owner, member, kind)
    inputs.member_allowed('V4', candidate + 'train/STATIC_coefficients.npy.gz', 'array')
    inputs.member_allowed('V1', candidate + 'stage2/normalizer/std.npy.gz', 'array')

  def test_exact_npy_gzip_hash_shape_dtype_and_no_pickle(self):
    value = np.arange(12, dtype=np.int64).reshape(3, 4)
    stream = io.BytesIO()
    np.save(stream, value, allow_pickle=False)
    npy = stream.getvalue()
    raw = gzip.compress(npy, mtime=0)
    desc = {
      'dtype': '<i8',
      'shape': [3, 4],
      'order': 'C',
      'file_sha256': evaluation.sha(raw),
      'npy_sha256': evaluation.sha(npy),
      'array_sha256': evaluation.sha(value.tobytes()),
    }
    decoded, proof = inputs.decode(raw, desc, shape=(3, 4), dtype='<i8', compressed=True)
    np.testing.assert_array_equal(decoded, value)
    self.assertFalse(decoded.flags.writeable)
    self.assertEqual(proof['payload_sha256'], desc['array_sha256'])
    for bad in ({**desc, 'file_sha256': '0' * 64}, {**desc, 'array_sha256': '0' * 64}, {**desc, 'dtype': '|O'}):
      with self.assertRaises(ValueError):
        inputs.decode(raw, bad, shape=(3, 4), dtype='<i8', compressed=True)
    for bad in (raw[:-1], raw + raw, raw + b'extra'):
      with self.assertRaises(ValueError):
        inputs.decode(bad, {**desc, 'file_sha256': evaluation.sha(bad)}, shape=(3, 4), dtype='<i8', compressed=True)

  def test_uncompressed_source_npy_and_oversized_header(self):
    value = np.array([0.0, 1.0], np.float64)
    stream = io.BytesIO()
    np.save(stream, value, allow_pickle=False)
    raw = stream.getvalue()
    desc = {'dtype': '<f8', 'shape': [2], 'order': 'C', 'file_sha256': evaluation.sha(raw), 'array_sha256': evaluation.sha(value.tobytes())}
    actual, _ = inputs.decode(raw, desc, shape=(2,), dtype='<f8', compressed=False)
    np.testing.assert_array_equal(actual, value)
    with self.assertRaises(ValueError):
      inputs.decode(raw, desc, shape=(1,), dtype='<f8', compressed=False)
    with self.assertRaises(ValueError):
      inputs.decode(raw, desc, shape=(inputs.MAX_SOURCE_ROWS + 1,), dtype='<f8', compressed=False)

  def test_phase_gate_all_64_decisions_before_dev(self):
    phase = inputs.Phase()
    with self.assertRaises(ValueError):
      phase.require_dev()
    with self.assertRaises(ValueError):
      phase.seal_train([])
    jobs = []
    for candidate, fold in decision.JOBS:
      jobs.append(
        {
          'candidate_id': candidate,
          'fold': fold,
          'contexts': {context: {'decision': 0.0, 'positive': 1, 'negative': 1} for context in ('PREVIOUS_STATIC', 'PREVIOUS_MOVE')},
        }
      )
    phase.seal_train(jobs)
    phase.require_dev()
    with self.assertRaises(ValueError):
      phase.seal_train(jobs)


class TestEPublication(unittest.TestCase):
  def test_cells_and_complements_and_joint_arm_suppression(self):
    self.assertTrue(publication.safe_cell(0, 500))
    self.assertTrue(publication.safe_cell(250, 500))
    self.assertFalse(publication.safe_cell(1, 500))
    self.assertFalse(publication.safe_cell(499, 500))
    self.assertFalse(publication.safe_cell(0, 200))
    self.assertFalse(publication.safe_changes(5))
    self.assertTrue(publication.safe_changes(0))
    self.assertTrue(publication.safe_changes(201))

  def test_c_suppressed_onset_and_continuation_never_released(self):
    self.assertEqual(publication.INHERITED_SUPPRESSED, {'MOVE_ONSET', 'MOVE_CONTINUATION'})

  def test_no_raw_rows_or_private_values_in_summary(self):
    row = publication.summary([1.0, 2.0, 3.0])
    self.assertEqual(row, {'valid_jobs': 3, 'median': 2.0, 'minimum': 1.0, 'maximum': 3.0})


class TestEProtocol(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.root = Path(__file__).resolve().parents[4]
    cls.public = cls.root / 'docs/cyberpilot/changes'
    cls.protocol = json.loads((cls.public / 'empirical-hurdle-stage1-v4-e-execution-protocol.json').read_bytes())

  def test_protocol_own_receipt_and_public_input_seals(self):
    value = dict(self.protocol)
    digest = value.pop('receipt_sha256')
    self.assertEqual(evaluation.sha(evaluation.canonical(value)), digest)
    for name, pin in self.protocol['public_inputs'].items():
      raw = (self.public / name).read_bytes()
      self.assertEqual(evaluation.sha(raw), pin['raw_sha256'])
      row = json.loads(raw)
      seal = row.pop('receipt_sha256')
      self.assertEqual(seal, pin['receipt_sha256'])
      self.assertEqual(evaluation.sha(evaluation.canonical(row)), seal)

  def test_protocol_source_bytes_and_original_sources_unchanged(self):
    for name, digest in self.protocol['source_sha256'].items():
      self.assertEqual(evaluation.sha((self.root / 'openpilot/tools/cyber_autotune' / name).read_bytes()), digest)
    old = json.loads((self.public / 'empirical-hurdle-stage1-v4-retrospective-execution-authorization.json').read_bytes())
    for name, digest in old['executor_sources'].items():
      self.assertEqual(self.protocol['source_sha256'][name], digest)

  def test_frozen_job_policy_acceptance_and_22_domains(self):
    p = self.protocol
    d = json.loads((self.public / 'empirical-hurdle-stage1-v4-d-offline-evaluation-contract.json').read_bytes())
    self.assertEqual(tuple((r['candidate_id'], r['fold']) for r in p['jobs']), decision.JOBS)
    self.assertEqual(p['policy_arms'], ['D0', 'D1'])
    self.assertEqual(p['acceptance'], d['acceptance'])
    self.assertEqual(p['validation_domains'], d['validation_domains'])
    self.assertEqual(len(p['validation_domains']), 22)
    self.assertFalse(p['automatic_adoption'])
    self.assertFalse(p['F_AUTHORIZED'])
    self.assertFalse(p['V5_AUTHORIZED'])

  def test_32_clause_operators_support_and_fold_failure(self):
    clauses = json.loads((self.public / 'empirical-hurdle-acceptance-gate-v1.json').read_bytes())['clauses']
    metric = {'rmse': 1.0, 'mae': 1.0, 'p95': 1.0, 'exact_hit': 0.5, 'within_one_tick': 0.5}
    pair = {'candidate': dict(metric), 'comparator': dict(metric), 'count': 201, 'anchor_sha256': 'a' * 64, 'comparator_anchor_sha256': 'a' * 64}
    row = {
      'status': 'EXECUTED_COMPLETE',
      'one_step': pair,
      'true_move': pair,
      'rollout': {str(h): {'overall': pair, 'path_moved': pair} for h in evaluation.HORIZONS},
    }
    result = evaluation.gates.fold_gate(row, clauses)
    self.assertFalse(result['pass'])  # Strict original one-step RMSE inequality.
    self.assertEqual(len(result['clauses']), 32)
    pair['candidate']['rmse'] = 0.9
    self.assertTrue(evaluation.gates.fold_gate(row, clauses)['pass'])
    pair['count'] = 200
    self.assertFalse(evaluation.gates.fold_gate(row, clauses)['pass'])
    pair['count'] = 201
    pair['comparator_anchor_sha256'] = 'b' * 64
    with self.assertRaises(ValueError):
      evaluation.gates.fold_gate(row, clauses)

  def test_stored_complete_receipt_and_incomplete_rejection(self):
    import copy

    clauses = json.loads((self.public / 'empirical-hurdle-acceptance-gate-v1.json').read_bytes())['clauses']
    pair = {
      'count': 201,
      'anchor_sha256': 'c' * 64,
      'comparator_anchor_sha256': 'c' * 64,
      'candidate': {'rmse': 1.0, 'mae': 1.0, 'p95': 1.0},
      'comparator': {'rmse': 1.0, 'mae': 1.0, 'p95': 1.0},
    }
    arm = {
      'status': 'EXECUTED_COMPLETE',
      'one_step': pair,
      'true_move': pair,
      'rollout': {str(h): {'status': 'COMPLETE', 'overall': pair, 'path_moved': pair} for h in evaluation.HORIZONS},
      'gate': {'pass': False, 'failures': [c['id'] for c in clauses], 'clauses': [{'id': c['id'], 'pass': False, 'evaluated': True} for c in clauses]},
    }
    context = decision.select_context(np.array([0.1, 0.9]), np.array([False, True]), role='TRAIN')
    jobs = [
      {
        'candidate_id': c,
        'fold': f,
        'TRAIN': {'candidate_id': c, 'fold': f, 'count': 4, 'contexts': {k: dict(context) for k in ('PREVIOUS_STATIC', 'PREVIOUS_MOVE')}},
        'arms': {a: copy.deepcopy(arm) for a in ('D0', 'D1')},
      }
      for c, f in decision.JOBS
    ]
    value = {
      'schema': 'V4_E_CANONICAL_RESULT_V1',
      'protocol_sha256': 'a' * 64,
      'head': 'b' * 40,
      'jobs': jobs,
      'selected_candidate': None,
      'selected_policy': None,
      'holdout': 'CLOSED',
      'vehicle_authority': 'NONE',
      'forbidden_operation_counters': dict.fromkeys(evaluation.FORBIDDEN_OPERATIONS, 0),
      'mixed_carrier_openings': 0,
      'original_D0_threshold_readings': 0,
      'operation_counters': {'TRAIN_context_decision_selection_calls': 64, 'E_scientific_job_evaluation_calls': 32},
    }
    raw = evaluation.canonical(evaluation.seal(value))
    with patch.object(evaluation, 'recursive', side_effect=AssertionError), patch.object(decision, 'select_job', side_effect=AssertionError):
      self.assertEqual(evaluation.verify_only(raw, evaluation.sha(raw), 'a' * 64, head='b' * 40)['recompute_calls'], 0)
    for defect in ('horizon', 'context', 'clause', 'forbidden', 'metric'):
      bad = copy.deepcopy(value)
      if defect == 'horizon':
        bad['jobs'][0]['arms']['D1']['rollout'].pop('200')
      elif defect == 'context':
        bad['jobs'][0]['TRAIN']['contexts']['PREVIOUS_STATIC'] = {}
      elif defect == 'clause':
        bad['jobs'][0]['arms']['D1']['gate']['clauses'][0].pop('evaluated')
      elif defect == 'metric':
        bad['jobs'][0]['arms']['D1']['rollout']['200']['path_moved'] = None
      else:
        bad['forbidden_operation_counters'] = {'source_writes': 0}
      raw = evaluation.canonical(evaluation.seal(bad))
      with self.assertRaises((ValueError, KeyError)):
        evaluation.verify_only(raw, evaluation.sha(raw), 'a' * 64)

  def test_score_diagnostics_missing_class_and_context_support(self):
    row = evaluation.score_diagnostics(np.array([0.0, 0.5, 1.0]), np.array([False, False, False]), np.array([0, 0, 1], np.int64))
    self.assertIsNone(row['OVERALL']['auc']['value'])
    self.assertEqual(row['PREVIOUS_STATIC']['n'], 2)
    self.assertEqual(row['PREVIOUS_MOVE']['n'], 1)
    transfer = evaluation.score_transfer(row, row)
    self.assertIsNone(transfer['OVERALL']['auc'])
    self.assertEqual(transfer['OVERALL']['brier'], 0)

  def test_exogenous_indexing_and_fresh_horizon_reset(self):
    model, stage2 = fixture_model(5)
    initial = np.array([[1, 2, 3, 4, 5, 6]], np.int64)
    command, speed = np.arange(29, dtype=float)[None, :], np.arange(25, dtype=float)[None, :]
    seen = []
    original = evaluation.integrated

    def capture(x, *args):
      seen.append(x.copy())
      return original(x, *args)

    with patch.object(evaluation, 'integrated', side_effect=capture):
      first = evaluation.recursive(initial, command, speed, 'HRI_D05_L05', model, (1.0, 1.0), stage2, 25, {})
      second = evaluation.recursive(initial, command, speed, 'HRI_D05_L05', model, (1.0, 1.0), stage2, 25, {})
    np.testing.assert_array_equal(first[0], second[0])
    for step in (0, 1, 24):
      np.testing.assert_array_equal(seen[step][0, 1:6], command[0, step : step + 5])
      self.assertEqual(seen[step][0, -1], speed[0, step])
    np.testing.assert_array_equal(initial, [[1, 2, 3, 4, 5, 6]])

  def test_recursive_overflow_is_not_repaired(self):
    model, stage2 = fixture_model()
    with self.assertRaises(ValueError):
      evaluation.recursive(np.array([[32767, 32767]], np.int64), np.zeros((1, 25)), np.ones((1, 25)), 'HRI_D00_L01', model, (0.0, 0.0), stage2, 25, {})

  def test_invalid_npy_fortran_binary_and_nonfinite_scores(self):
    for array, dtype in ((np.asfortranarray(np.ones((2, 2))), '<f8'), (np.array([True, False]), '|b1')):
      stream = io.BytesIO()
      np.save(stream, array, allow_pickle=False)
      raw = stream.getvalue()
      if dtype == '|b1':
        raw = raw[:-1] + bytes([2])
      desc = {'file_sha256': evaluation.sha(raw), 'dtype': dtype, 'shape': list(array.shape), 'order': 'C'}
      with self.assertRaises(ValueError):
        inputs.decode(raw, desc, shape=array.shape, dtype=dtype, compressed=False)
    for values in ([float('nan')], [float('inf')], [-0.01], [1.01]):
      with self.assertRaises(ValueError):
        decision.probability(np.array(values))

  def test_public_projection_joint_privacy_full_payload(self):
    import copy

    pair = {'count': 500, 'candidate': {'rmse': 1.0, 'mae': 0.5, 'p95': 2.0, 'exact_hit': 1 / 500, 'within_one_tick': 1 / 500}}
    transitions = {state: {'n': 500, 'move_gate': 0, 'move_gate_rate': 0.0, 'paired_changed_gate_rows': 0} for state in evaluation.TRANSITIONS}
    arm = {
      'one_step': pair,
      'true_move': pair,
      'tick_diagnostics': {'transitions': transitions},
      'paired_changes': dict.fromkeys(('projected_rows', 'continuous_rows', 'true_move_projected_rows', 'true_move_continuous_rows'), 201),
      'gate': {'pass': False, 'failures': ['synthetic']},
      'rollout': {
        str(h): {'overall': pair, 'path_moved': pair, 'paired_changed_endpoint_rows': 201, 'paired_changed_path_moved_endpoint_rows': 201}
        for h in evaluation.HORIZONS
      },
    }
    payload = {
      'protocol_sha256': 'a' * 64,
      'jobs': [{'candidate_id': c, 'fold': f, 'arms': {a: copy.deepcopy(arm) for a in ('D0', 'D1')}} for c, f in decision.JOBS],
    }
    out = publication.project(payload)
    self.assertNotIn('exact_hit', out['metric_families']['one_step']['metrics'])
    self.assertNotIn('within_one_tick', out['metric_families']['one_step']['metrics'])
    self.assertEqual(out['transitions']['MOVE_ONSET']['status'], 'SUPPRESSED_C_COMPATIBLE_JOINT_POLICY')
    payload['jobs'][-1]['arms']['D1']['tick_diagnostics']['transitions']['STATIC_HOLD']['move_gate'] = 1
    payload['jobs'][-1]['arms']['D1']['paired_changes']['continuous_rows'] = 1
    out = publication.project(payload)
    self.assertEqual(out['transitions']['STATIC_HOLD']['status'], 'SUPPRESSED_C_COMPATIBLE_JOINT_POLICY')
    self.assertEqual(out['metric_families']['one_step']['status'], 'JOINTLY_SUPPRESSED_OR_NUMERICAL_NONPASS')


class TestEProvider(unittest.TestCase):
  def test_synthetic_manifest_source_and_model_admission_chain(self):
    import copy

    candidate, fold = decision.JOBS[0]
    prefix = f'candidates/{candidate}/{fold}'
    metadata, arrays, maps = {}, {}, {k: {} for k in ('V4', 'V1', 'CAUSAL', 'DERIVED')}

    def meta(owner, member, row):
      value = evaluation.seal(row)
      metadata[owner, member] = value
      maps[owner][member] = evaluation.sha(evaluation.canonical(value))
      return value

    def array(owner, member, value):
      stream = io.BytesIO()
      np.save(stream, value, allow_pickle=False)
      compressed = member.endswith('.gz')
      raw = gzip.compress(stream.getvalue(), mtime=0) if compressed else stream.getvalue()
      desc = {
        'file_sha256': evaluation.sha(raw),
        'shape': list(value.shape),
        'dtype': value.dtype.str,
        'order': 'C',
        'array_sha256': evaluation.sha(value.tobytes()),
      }
      arrays[owner, member] = raw, desc, compressed
      maps[owner][member] = desc['file_sha256']
      return desc

    route = 'a' * 64
    source_policy = {'receipt_sha256': 'b' * 64, 'route_ids': [route], 'excluded_qlog_content_sha256': []}
    indexed, ids = [], []
    for number in range(154):
      identity = evaluation.sha(str(number).encode())
      ids.append(identity)
      source_prefix = f'repeat-1/routes/{route}/segments/{identity}'
      derived_prefix = f'repeat-1/segments/{identity}'
      source_arrays = {f: array('CAUSAL', source_prefix + '/arrays/' + f + '.npy', np.ones(8, np.float64)) for f in inputs.CAUSAL_FIELDS}
      source = meta('CAUSAL', source_prefix + '/receipt.json', {'route_id': route, 'segment_sha256': identity, 'arrays': source_arrays})
      values = {
        'angle_tick': np.arange(8, dtype=np.int64),
        'streak_all': np.arange(1, 9, dtype=np.int64),
        'model_eligible': np.ones(8, bool),
        'rail': np.zeros(8, bool),
        's2_ri_causal_run_id': np.zeros(8, np.int64),
        'within_s2_ri_causal_run_index': np.arange(8, dtype=np.int64),
      }
      descs = {f: array('DERIVED', derived_prefix + '/' + f + '.npy', values[f]) for f in inputs.DERIVED_FIELDS}
      derived = meta(
        'DERIVED',
        derived_prefix + '/receipt.json',
        {'source_receipt_sha256': source['receipt_sha256'], 'policy_sha256': source_policy['receipt_sha256'], 'arrays': descs},
      )
      indexed.append({'content_sha256': identity, 'receipt_sha256': derived['receipt_sha256']})
    source_manifest = meta('CAUSAL', 'repeat-1/manifest.json', {})
    meta('CAUSAL', 'authorization.json', {'segments': {route: ids}})
    index = meta('DERIVED', 'repeat-1/derived-index.json', {'segments': indexed})
    admission = meta('DERIVED', 'repeat-1/admission.json', {'manifest_sha256': source_manifest['receipt_sha256']})
    result = meta('DERIVED', 'repeat-1/results.json', {'admission_sha256': admission['receipt_sha256']})
    normalizer = fixture_model()[0]['normalizer']
    norm_receipts = {}
    for stage in ('stage1', 'stage2'):
      part = f'{prefix}/{stage}/normalizer'
      descs = {f: array('V1', part + '/' + f + '.npy.gz', normalizer[f]) for f in inputs.NORMALIZER_FIELDS}
      norm_receipts[stage] = meta('V1', part + '/receipt.json', {'candidate_id': candidate, 'fold': fold, 'stage': stage.upper(), 'arrays': descs})
    coefficient = array('V1', prefix + '/stage2/model/coefficients.npy.gz', np.ones(5, np.float64))
    stage2_receipt = meta(
      'V1',
      prefix + '/stage2/model/receipt.json',
      {'candidate_id': candidate, 'fold': fold, 'normalizer_sha256': norm_receipts['stage2']['receipt_sha256'], 'arrays': {'coefficients': coefficient}},
    )
    reference = {
      'candidate_id': candidate,
      'fold': fold,
      'stage1': {'normalizer_receipt_sha256': norm_receipts['stage1']['receipt_sha256']},
      'stage2': {
        'normalizer_receipt_sha256': norm_receipts['stage2']['receipt_sha256'],
        'model_receipt_sha256': stage2_receipt['receipt_sha256'],
        'coefficient_sha256': coefficient['array_sha256'],
      },
    }
    train_files = {}
    for label, count in (('STATIC', 4), ('MOVE', 5)):
      desc = array('V4', prefix + '/train/' + label + '_coefficients.npy.gz', np.zeros(count))
      train_files[label + '_coefficients.npy.gz'] = desc['file_sha256']
    train = meta('V4', prefix + '/train/manifest.json', {'files': train_files, 'train_receipt_sha256': 'c' * 64})
    finalized = meta(
      'V4',
      prefix + '/train-finalized.json',
      {
        'candidate_id': candidate,
        'fold': fold,
        'status': 'TRAIN_COMPLETE',
        'authorization_sha256': 'd' * 64,
        'train_anchor_sha256': 'e' * 64,
        'train_manifest_sha256': train['receipt_sha256'],
        'model_threshold_receipt_sha256': 'c' * 64,
      },
    )
    catalog = {
      'candidate_id': candidate,
      'fold': fold,
      'train_manifest_sha256': train['receipt_sha256'],
      'train_finalized_sha256': finalized['receipt_sha256'],
      'train_receipt_sha256': 'c' * 64,
      'train_anchor_sha256': 'e' * 64,
      'v1_stage1_normalizer_receipt_sha256': norm_receipts['stage1']['receipt_sha256'],
      'v1_stage2_receipts_sha256': evaluation.sha(evaluation.canonical(reference['stage2'])),
    }
    roots = {owner: meta(owner, 'manifest.json', {'files': dict(maps[owner])}) for owner in ('V4', 'V1')}
    original = evaluation.seal(
      {
        'source_file_set_sha256': evaluation.sha(evaluation.canonical(maps['CAUSAL'])),
        'derived_file_set_sha256': evaluation.sha(evaluation.canonical(maps['DERIVED'])),
        'source_manifest_sha256': source_manifest['receipt_sha256'],
        'derived_index_sha256': index['receipt_sha256'],
        'derived_result_sha256': result['receipt_sha256'],
      }
    )
    metadata['V1_TOP', 'authorization.json'] = original
    metadata['V1_TOP', 'input-pins.json'] = evaluation.seal(
      {
        'source': maps['CAUSAL'],
        'derived': maps['DERIVED'],
        'authorization_sha256': original['receipt_sha256'],
        **dict.fromkeys(inputs.b0.AUTHORITY_KEYS, False),
      }
    )

    class FixtureReader:
      def __init__(self):
        self.maps, self.phase, self.opened = {}, inputs.Phase(), set()

      def metadata(self, owner, member, **pins):
        inputs.member_allowed(owner, member, 'metadata')
        row = metadata[owner, member]
        if pins.get('receipt_sha'):
          decision.need(row['receipt_sha256'] == pins['receipt_sha'])
        return copy.deepcopy(row)

      def array(self, owner, member, desc, **schema):
        inputs.member_allowed(owner, member, 'array')
        decision.need((owner, member) not in self.opened)
        self.opened.add((owner, member))
        raw, _, compressed = arrays[owner, member]
        decision.need(schema.pop('compressed', compressed) == compressed)
        decision.need(self.maps[owner][member] == desc['file_sha256'])
        return inputs.decode(raw, desc, compressed=compressed, **schema)[0]

    reader = FixtureReader()
    jobs = [{'candidate_id': c, 'fold': f} for c, f in decision.JOBS]
    auth = {
      'authorization_sha256': 'd' * 64,
      'source_manifests': {
        'source_file_set': original['source_file_set_sha256'],
        'derived_file_set': original['derived_file_set_sha256'],
        'causal': source_manifest['receipt_sha256'],
        'derived_index': index['receipt_sha256'],
        'derived_result': result['receipt_sha256'],
      },
    }
    provider = inputs.Provider(
      reader,
      jobs,
      v4_manifest={'raw_sha256': '0' * 64, 'receipt_sha256': roots['V4']['receipt_sha256']},
      v1_manifest={'raw_sha256': '0' * 64, 'receipt_sha256': roots['V1']['receipt_sha256']},
      v4_authorization=auth,
      v1_authorization_sha=original['receipt_sha256'],
      references=[reference],
      job_catalog=[catalog],
      source_policy=source_policy,
    )
    with self.assertRaises(ValueError):
      provider.admit_segments()
    reader.phase.train_sha256 = 'f' * 64  # Test grants DEV only, not a production authority path.
    provider.admit_segments()
    self.assertEqual(len(provider.segments), 154)
    model, stage2 = provider.models(0)
    self.assertEqual(model['heads'][0]['positions'], [0, 1, 3, 4])
    self.assertEqual(len(stage2['coefficients']), 5)
    self.assertFalse(any(member.endswith('train/receipt.json') for _, member in reader.opened))
    metadata['V4', prefix + '/train-finalized.json']['train_anchor_sha256'] = '0' * 64
    with self.assertRaises(ValueError):
      provider.models(0)


if __name__ == '__main__':
  unittest.main()
