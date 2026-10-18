"""Synthetic E2 numerical/capability contracts; no actual scientific inputs."""

import copy
import gzip
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as d
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_inputs as inp
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_evaluation as ev
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_publication as pub
from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_v4_e_evaluation import fixture_model


class TestE2Decision(unittest.TestCase):
  def test_same_gate_witness_and_four_guards(self):
    p = np.array([0.0, 0.2, 0.2, 0.7, 1.0], np.float64)
    y = np.array([0, 0, 1, 1, 1], bool)
    c = np.zeros(5, np.int64)
    t = y.astype(np.int64)
    u = np.array([1.0, 0.4, 0.6, 1.0, 1.0])
    result = d.select_context(p, y, c, t, u, np.rint(u).astype(np.int64), 0.5, role='TRAIN')
    self.assertTrue(result['witness_verified'])
    self.assertEqual(result['decision'], 0.0)
    self.assertEqual(result['net_exact_hit_gain'], 3)
    self.assertEqual(result['TRUE_MOVE_TP'], 3)
    self.assertTrue(all(result['guards'].values()))


def synthetic_population(n=1030):
  tick = np.resize(np.array([0, 1, 1, 0], np.int64), n)
  segment = {'tick': tick, 'command': np.zeros(n), 'speed': np.ones(n), 'streak': np.arange(1, n + 1)}
  indices = np.arange(1, n - 1, dtype=np.int64)
  current, target = tick[indices], tick[indices + 1]
  prior = tick[indices] - tick[indices - 1]
  p = np.linspace(0.1, 0.9, len(indices), dtype=np.float64)
  return segment, indices, p, target != current, prior


class TestE2SelectorEdges(unittest.TestCase):
  def fixture(self):
    p = np.array([0.0, 0.2, 0.2, 0.7, 1.0])
    y = np.array([0, 0, 1, 1, 1], bool)
    c = np.zeros(5, np.int64)
    return p, y, c, y.astype(np.int64), np.array([1.0, 0.4, 0.6, 1.0, 1.0]), np.array([1, 0, 1, 1, 1], np.int64)

  def test_integer_D0_objective_and_ties(self):
    counters = {}
    result = d.reconstruct_D0(np.array([0.0, 0.5, 0.5, 1.0]), np.array([0, 1, 0, 1], bool), role='TRAIN', counters=counters)
    self.assertEqual((result['value'], result['BA_NUM'], result['TN']), (0.5, 6, 2))
    self.assertEqual(counters['D0_TRAIN_reconstruction_calls'], 1)

  def test_no_DEV_selection(self):
    with self.assertRaisesRegex(ValueError, 'TRAIN_ONLY'):
      d.select_context(*self.fixture(), 0.5, role='DEV')

  def test_missing_class(self):
    v = list(self.fixture())
    v[1] = np.zeros(5, bool)
    v[3] = v[2].copy()
    with self.assertRaisesRegex(ValueError, 'CLASS_MISSING'):
      d.select_context(*v, 0.5, role='TRAIN')

  def test_probability_nan_inf_range_dtype(self):
    for bad in (float('nan'), float('inf'), -0.1, 1.1):
      v = list(self.fixture())
      v[0] = v[0].copy()
      v[0][1] = bad
      with self.subTest(bad=bad), self.assertRaises(ValueError):
        d.select_context(*v, 0.5, role='TRAIN')
    v = list(self.fixture())
    v[0] = v[0].astype(np.float32)
    with self.assertRaises(ValueError):
      d.select_context(*v, 0.5, role='TRAIN')

  def test_label_prior_dtype(self):
    p, y, *_ = self.fixture()
    for bad_y, prior in ((y.astype(np.int64), np.zeros(5, np.int64)), (y, np.zeros(5, np.int32))):
      with self.assertRaises(ValueError):
        d.validate(p, bad_y, prior)

  def test_label_tick_disagreement(self):
    v = list(self.fixture())
    v[3] = np.zeros(5, np.int64)
    with self.assertRaisesRegex(ValueError, 'LABEL_CONFLICT'):
      d.select_context(*v, 0.5, role='TRAIN')

  def test_invalid_static_potential_is_not_skipped(self):
    v = list(self.fixture())
    v[4][0] = 1e10
    with self.assertRaises(ValueError):
      d.select_context(*v, 1.0, role='TRAIN')

  def test_tree_update_exact_topology(self):
    leaves = np.tile(np.array([1e16, 1.0, 1.0, 1.0, 0.0])[:, None], (1, 4))
    tree = d.LossTree(leaves)
    before = tree.root.copy()
    tree.replace(0, np.zeros(4))
    self.assertTrue(d.byte_equal(tree.root, np.array([3.0, 3.0, 3.0, 3.0])))
    self.assertFalse(d.byte_equal(before - 1e16, tree.root))

  def test_tree_update_order_independent(self):
    leaves = np.arange(20, dtype=np.float64).reshape(5, 4)
    expected = d.LossTree(leaves)
    for order in ((0, 1, 2, 3, 4), (4, 1, 0, 3, 2)):
      tree = d.LossTree(np.zeros((5, 4)))
      for i in order:
        tree.replace(i, leaves[i])
      self.assertTrue(d.byte_equal(tree.root, expected.root))

  def test_tree_nonfinite_and_overflow(self):
    for x in (float('inf'), float('nan')):
      with self.assertRaises(ValueError):
        d.LossTree(np.full((2, 4), x))
    with self.assertRaises(FloatingPointError):
      d.LossTree(np.full((2, 4), 1e308))

  def test_signed_zero_comparison_and_byte_qualification(self):
    self.assertTrue(np.array_equal(np.array([-0.0]), np.array([0.0])))
    self.assertFalse(d.byte_equal(np.array([-0.0]), np.array([0.0])))
    v = list(self.fixture())
    v[0][0] = -0.0
    out = d.select_context(*v, 0.5, role='TRAIN')
    self.assertEqual(out['decision'], 0.0)
    self.assertFalse(np.signbit(out['decision']))

  def test_original_classification_tie_uses_larger_decision(self):
    p = np.array([0.0, 0.5, 0.5, 1.0])
    y = np.array([0, 1, 0, 1], bool)
    result = d.reconstruct_D0(p, y, role='TRAIN', counters={})
    self.assertEqual(result['value'], 0.5)
    self.assertEqual(result['decision'], '>')

  def test_tiny_exhaustive_oracle_matches_sweep(self):
    for scores in ([0.0, 0.3, 0.3, 1.0], [0.0, 0.0, 0.8, 0.8], [0.2, 0.4, 0.6, 0.9]):
      p = np.array(scores)
      y = np.array([0, 1, 0, 1], bool)
      c = np.zeros(4, np.int64)
      t = y.astype(np.int64)
      u = np.array([0.4, 0.6, 1.0, 1.0])
      move = np.rint(u).astype(np.int64)
      selected = d.select_context(p, y, c, t, u, move, 0.5, role='TRAIN')

      def metrics(theta, p=p, u=u, t=t, move=move, c=c, y=y):
        gate = p > theta
        delta = np.where(gate, u, 0.0)
        error = delta - t

        def pair_sum(v):
          return float((float(v[0]) + float(v[1])) + (float(v[2]) + float(v[3])))

        return (
          int(np.count_nonzero(np.where(gate, move, c) == t)) - 2,
          pair_sum(error * error),
          pair_sum(np.abs(error)),
          int(np.count_nonzero(gate & ~y & (move != c))),
          int(np.count_nonzero(gate & y)),
          pair_sum(np.where(y, error * error, 0.0)),
          pair_sum(np.where(y, np.abs(error), 0.0)),
        )

      old = metrics(0.5)
      choices = []
      for theta in sorted({0.0, 1.0, *scores}):
        g, sse, sae, harm, tp, tsse, tsae = metrics(theta)
        if tp >= old[4] and tsse <= old[5] and tsae <= old[6] and harm <= old[3]:
          choices.append((g, -sse, -sae, -harm, theta))
      self.assertEqual(selected['decision'], max(choices)[-1])


class TestE2Potentials(unittest.TestCase):
  def run_fixture(self, counters=None):
    segment, ix, p, y, prior = synthetic_population()
    return d.potentials(
      [(segment, ix)], 'HRI_D00_L01', fixture_model()[1], p, y, prior, 0.5, {'count': len(p), 'feature_dimension': 5}, counters if counters is not None else {}
    )

  def test_fixed_chunks_full_count_and_original_order(self):
    counters = {}
    v = self.run_fixture(counters)
    self.assertEqual(len(v['u']), 1028)
    np.testing.assert_array_equal(v['u'], np.ones(1028))
    self.assertEqual(counters['TRAIN_counterfactual_Stage2_calls'], 3)
    self.assertEqual(counters['TRAIN_counterfactual_Stage2_calls_rows'], 1028)
    self.assertEqual(counters['TRAIN_numerical_qualification_jobs'], 1)

  def test_bit_difference_is_failure_without_tolerance(self):
    original = d.frozen.m.predict_delta

    def altered(x, model):
      value = original(x, model)
      if len(x) != 512:
        value = np.nextafter(value, np.inf)
      return value

    with patch.object(d.frozen.m, 'predict_delta', altered), self.assertRaisesRegex(ValueError, 'NUMERICAL_EQUIVALENCE_NOT_PROVEN'):
      self.run_fixture()

  def test_wrong_row_order_prior_fails(self):
    segment, ix, p, y, prior = synthetic_population()
    prior = prior[::-1].copy()
    with self.assertRaisesRegex(ValueError, 'RECORDED_ORDER'):
      d.potentials([(segment, ix)], 'HRI_D00_L01', fixture_model()[1], p, y, prior, 0.5, {'count': len(p), 'feature_dimension': 5}, {})

  def test_wrong_count_and_dimension(self):
    segment, ix, p, y, prior = synthetic_population()
    for expected in ({'count': 1, 'feature_dimension': 5}, {'count': len(p), 'feature_dimension': 7}):
      with self.assertRaises(ValueError):
        d.potentials([(segment, ix)], 'HRI_D00_L01', fixture_model()[1], p, y, prior, 0.5, expected, {})


class TestE2Phase(unittest.TestCase):
  def records(self):
    context = {
      'decision': 0.5,
      'positive': 1,
      'negative': 1,
      'count': 2,
      'witness_verified': True,
      'guards': dict.fromkeys(('TRUE_MOVE_TP', 'TRUE_MOVE_SSE', 'TRUE_MOVE_SAE', 'HARMFUL_STATIC'), True),
    }
    return [{'candidate_id': c, 'fold': f, 'count': 4, 'contexts': {k: copy.deepcopy(context) for k in d.CONTEXTS}} for c, f in d.JOBS]

  def test_no_selection_before_all32_qualifications(self):
    phase = inp.Phase()
    for c, f in d.JOBS[:-1]:
      phase.qualify(c, f)
    with self.assertRaisesRegex(ValueError, 'ALL32'):
      phase.require_selection()
    phase.qualify(*d.JOBS[-1])
    phase.require_selection()

  def test_no_DEV_before_durable_readback(self):
    phase = inp.Phase()
    for c, f in d.JOBS:
      phase.qualify(c, f)
    with self.assertRaises(ValueError):
      phase.require_dev()
    with self.assertRaises(ValueError):
      phase.unlock(self.records(), 'a' * 64, 'b' * 64)
    phase.unlock(self.records(), 'a' * 64, 'a' * 64)
    phase.require_dev()
    with self.assertRaises(ValueError):
      phase.unlock(self.records(), 'a' * 64, 'a' * 64)

  def test_incomplete_or_invalid_records_never_unlock(self):
    for defect in ('missing', 'guard', 'nan'):
      phase = inp.Phase()
      for c, f in d.JOBS:
        phase.qualify(c, f)
      records = self.records()
      if defect == 'missing':
        records.pop()
      if defect == 'guard':
        records[0]['contexts']['PREVIOUS_STATIC']['guards']['TRUE_MOVE_TP'] = False
      if defect == 'nan':
        records[0]['contexts']['PREVIOUS_STATIC']['decision'] = float('nan')
      with self.assertRaises(ValueError):
        phase.unlock(records, 'a' * 64, 'a' * 64)
      with self.assertRaises(ValueError):
        phase.require_dev()

  def test_train_field_and_candidate_scope(self):
    phase = inp.Phase()
    phase.job = d.JOBS[0]
    prefix = 'candidates/' + '/'.join(d.JOBS[0]) + '/'
    phase.authorize('V4', prefix + 'train/combined_probability.npy.gz', 'array')
    phase.authorize('V1', prefix + 'stage2/model/coefficients.npy.gz', 'array')
    for owner, tail in [
      ('V4', 'one-step/p_move.npy.gz'),
      ('V4', 'one-step/predicted_gate.npy.gz'),
      ('V4', 'rollout-25/candidate_error.npy.gz'),
      ('V4', 'train/MOVE_coefficients.npy.gz'),
      ('V1', 'stage1/normalizer/mean.npy.gz'),
    ]:
      with self.assertRaises(ValueError):
        phase.authorize(owner, prefix + tail, 'array')
    with self.assertRaises(ValueError):
      phase.authorize('V4', prefix.replace('FOLD_A', 'FOLD_B') + 'train/combined_probability.npy.gz', 'array')

  def test_source_capability_scoped(self):
    phase = inp.Phase()
    with self.assertRaises(ValueError):
      phase.authorize('CAUSAL', 'repeat-1/manifest.json', 'metadata')
    with phase.source():
      phase.authorize('CAUSAL', 'repeat-1/manifest.json', 'metadata')
    with self.assertRaises(ValueError):
      phase.authorize('CAUSAL', 'repeat-1/manifest.json', 'metadata')

  def test_mixed_carrier_and_unneeded_paths_rejected(self):
    prefix = 'candidates/HRI_D00_L01/FOLD_A/'
    for owner, member, kind in [
      ('V4', prefix + 'train/receipt.json', 'metadata'),
      ('V1', prefix + 'stage1/model/coefficients.npy.gz', 'array'),
      ('V4', prefix + 'rollout-25/projected_path.npy.gz', 'array'),
      ('V4', '../manifest.json', 'metadata'),
    ]:
      with self.assertRaises(ValueError):
        inp.member_allowed(owner, member, kind)

  def test_reader_hash_size_and_symlink_protection(self):
    with tempfile.TemporaryDirectory() as tmp:
      base = Path(tmp)
      roots = {k: str(base / k) for k in ('V4', 'V1', 'V1_TOP', 'CAUSAL', 'DERIVED')}
      for value in roots.values():
        Path(value).mkdir()
      path = Path(roots['V4']) / 'manifest.json'
      path.write_bytes(b'fixture')
      ident = (base.stat().st_dev, base.stat().st_ino)
      for digest, cap in ((ev.sha(b'wrong'), 100), (ev.sha(b'fixture'), 2)):
        r = inp.Reader(roots, tmp, ident, inp.Phase())
        with self.assertRaises(ValueError):
          r.raw('V4', 'manifest.json', 'metadata', digest, cap)
      path.unlink()
      outside = base / 'other'
      outside.write_bytes(b'fixture')
      path.symlink_to(outside)
      r = inp.Reader(roots, tmp, ident, inp.Phase())
      with self.assertRaises(ValueError):
        r.raw('V4', 'manifest.json', 'metadata', ev.sha(b'fixture'), 100)

  def test_decode_rejects_pickle_bad_shape_and_trailing(self):
    x = np.arange(4, dtype=np.int64)
    stream = io.BytesIO()
    np.save(stream, x, allow_pickle=False)
    npy = stream.getvalue()
    raw = gzip.compress(npy, mtime=0)
    desc = {'dtype': '<i8', 'shape': [4], 'order': 'C', 'file_sha256': ev.sha(raw), 'array_sha256': ev.sha(x.tobytes())}
    a, _ = inp.e1.decode(raw, desc, shape=(4,), dtype='<i8', compressed=True)
    self.assertFalse(a.flags.writeable)
    for bad in (raw[:-1], raw + raw, raw + b'trailing'):
      with self.assertRaises(ValueError):
        inp.e1.decode(bad, {**desc, 'file_sha256': ev.sha(bad)}, shape=(4,), dtype='<i8', compressed=True)
    with self.assertRaises(ValueError):
      inp.e1.decode(raw, desc, shape=(4,), dtype='|O', compressed=True)


class TestE2EvaluationAndPrivacy(unittest.TestCase):
  def test_triangle_lower_bound_is_conservative(self):
    self.assertEqual(ev.changed_lower_bound(800, 500), 300)
    self.assertIsNone(ev.changed_lower_bound(500, 500))
    self.assertEqual(ev.changed_lower_bound(0, 0), 0)
    self.assertEqual(ev.changed_lower_bound(500, 500, exact_same_policy=True), 0)
    self.assertFalse(pub.safe_change_proof(None))
    self.assertFalse(pub.safe_change_proof(200))
    self.assertTrue(pub.safe_change_proof(201))

  def test_equal_nonextreme_counts_are_not_row_equality(self):
    self.assertFalse(pub.safe_three_counts([300, 300, 300], 1000))
    self.assertTrue(pub.safe_three_counts([0, 0, 0], 1000))
    self.assertFalse(pub.safe_three_counts([300, 301, 700], 1000))

  def test_strict_gate_and_projected_HOLD(self):
    model, stage2 = fixture_model()
    stage2['coefficients'][0] = 0.4
    x = np.ones((2, 5))
    x[:, -3] = 0
    current = np.zeros(2, np.int64)
    result = ev.e1.integrated(x, current, model, (0.5, 0.5), stage2, {}, p_move=np.array([0.5, 0.6]))
    np.testing.assert_array_equal(result['gate'], [False, True])
    np.testing.assert_array_equal(result['projected'], [0, 0])

  def test_recursive_realized_context_and_no_truth(self):
    model, stage2 = fixture_model()
    stage2['coefficients'][0] = 0.4
    path, gate, context = ev.e1.recursive(np.zeros((1, 2), np.int64), np.zeros((1, 25)), np.ones((1, 25)), 'HRI_D00_L01', model, (0.1, 0.1), stage2, 25, {})
    self.assertTrue(gate.all())
    self.assertFalse(context.any())
    self.assertFalse(path.any())

  def test_horizons_and_segment_support(self):
    self.assertEqual(ev.HORIZONS, (25, 50, 100, 200))
    s, _, _, _, _ = synthetic_population(20)
    for h in ev.HORIZONS:
      self.assertEqual(len(ev.e1.frozen.m.anchors(s, 'HRI_D00_L01', h)), 0)

  def test_three_arms_no_extra_policy_and_frozen_guard(self):
    self.assertEqual(pub.ARMS, ('D0', 'D1', 'D2'))
    self.assertEqual(len(d.JOBS), 32)
    self.assertEqual(len(ev.FORBIDDEN), 18)
    self.assertEqual(pub.prior.INHERITED_SUPPRESSED, {'MOVE_ONSET', 'MOVE_CONTINUATION'})

  def test_verify_only_rejects_bad_digest_without_inference(self):
    with patch.object(ev.e1.frozen.m, 'predict_delta', side_effect=AssertionError('inference')):
      with self.assertRaises(ValueError):
        ev.verify_only(b'{}', '0' * 64, '1' * 64)


class TestE2ControlAndContracts(unittest.TestCase):
  def test_protocol_fixed_policy_and_22_domains(self):
    import json
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    p = run.checked((run.PUBLIC / run.PROTOCOL_NAME).read_bytes())
    self.assertEqual(p['policy_arms'], ['D0', 'D1', 'D2'])
    self.assertEqual(tuple((j['candidate_id'], j['fold']) for j in p['jobs']), d.JOBS)
    self.assertEqual([x['order'] for x in p['validation_domains']], list(range(1, 23)))
    original = json.loads((run.PUBLIC / 'empirical-hurdle-stage1-v4-d2-evaluation-contract.json').read_bytes())
    self.assertEqual(p['validation_domains'], original['validation_domains'])
    self.assertEqual(p['acceptance']['raw_sha256'], '606d5d3f46677d0107298f8b94e0a6d5a73da62f01db0164c4812a9fa2cccee1')
    self.assertEqual(ev.CLAUSE_IDS, tuple(c['id'] for c in json.loads((run.PUBLIC / 'empirical-hurdle-acceptance-gate-v1.json').read_bytes())['clauses']))
    self.assertFalse(p['automatic_adoption'])
    self.assertFalse(p['F_AUTHORIZED'])
    self.assertEqual(p['input_scope']['D0_rollout'], ['candidate_error'])
    self.assertEqual(set(p['forbidden_operations']), set(ev.FORBIDDEN))

  def test_source_and_public_pins(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    p = run.checked((run.PUBLIC / run.PROTOCOL_NAME).read_bytes())
    for name, digest in p['source_sha256'].items():
      self.assertEqual(ev.sha((run.SOURCE / name).read_bytes()), digest, name)
    for name, pin in p['public_inputs'].items():
      raw = (run.PUBLIC / name).read_bytes()
      self.assertEqual(ev.sha(raw), pin['raw_sha256'])
      self.assertEqual(run.checked(raw)['receipt_sha256'], pin['receipt_sha256'])

  def test_resource_derivation(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    p = run.checked((run.PUBLIC / run.PROTOCOL_NAME).read_bytes())
    r = p['resources']
    self.assertEqual(r['TRAIN_cache_bytes'], 32 * r['TRAIN_DEV_row_upper_bound'] * 50)
    self.assertLess(r['peak_live_buffer_bound_bytes'], r['address_space_bytes'] // 2)
    self.assertEqual(r['chunk_rows'], 512)
    self.assertEqual(
      p['selection']['objective_order'],
      ['MAX_NET_TICK_EXACT_HIT_GAIN', 'MIN_OVERALL_CONTINUOUS_SSE', 'MIN_OVERALL_CONTINUOUS_SAE', 'MIN_HARMFUL_STATIC_REALIZED_COUNT', 'MAX_DECISION'],
    )

  def test_private_output_exclusive_permissions_and_no_alias(self):
    import os
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    with tempfile.TemporaryDirectory() as tmp:
      folder = Path(tmp)
      folder.chmod(0o700)
      value = run.sealed({'synthetic': True})
      digest = run.persist(folder, 'execution-binding.json', value, 1024)
      self.assertEqual(ev.sha(run.private(folder / 'execution-binding.json')), digest)
      self.assertEqual((folder / 'execution-binding.json').stat().st_mode & 0o777, 0o600)
      with self.assertRaises(FileExistsError):
        run.persist(folder, 'execution-binding.json', value, 1024)
      with self.assertRaises(ValueError):
        run.persist(folder, '../escape', value, 1024)
      with self.assertRaises(ValueError):
        run.persist(folder, 'train-decisions.json', value, 1)
      alias = folder / 'alias'
      os.link(folder / 'execution-binding.json', alias)
      with self.assertRaises(ValueError):
        run.private(alias)

  def test_private_symlink_directory_and_file_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    with tempfile.TemporaryDirectory() as tmp:
      folder = Path(tmp)
      folder.chmod(0o700)
      (folder / 'target').mkdir(mode=0o700)
      (folder / 'link').symlink_to(folder / 'target', target_is_directory=True)
      with self.assertRaises(OSError):
        run.directory(folder / 'link')
      f = folder / 'target/value'
      f.write_bytes(b'fixture')
      f.chmod(0o600)
      (folder / 'value-link').symlink_to(f)
      with self.assertRaises(OSError):
        run.private(folder / 'value-link')
      f.chmod(0o644)
      with self.assertRaises(ValueError):
        run.private(f)

  def test_failures_are_not_performance_results(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    expected = 'E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED'
    self.assertEqual(run.failure_status(ValueError(expected)), expected)
    self.assertEqual(run.failure_status(FileNotFoundError()), 'E2_INPUT_INSUFFICIENT')
    self.assertEqual(run.failure_status(ValueError('HASH_CONFLICT')), 'E2_INPUT_CONFLICT_FAIL_CLOSED')
    self.assertEqual(run.failure_status(FloatingPointError()), 'E2_TRAIN_NUMERICAL_FAILURE_JOB_NONPASS')
    self.assertEqual(run.failure_status(ValueError('E2_NONFINITE_LOSS')), 'E2_TRAIN_NUMERICAL_FAILURE_JOB_NONPASS')
    self.assertEqual(run.failure_status(MemoryError()), 'E2_RESOURCE_PREFLIGHT_BLOCKED')

  def test_train_binding_requires_anchor_and_run_boundaries(self):
    segment, _, _, _, _ = synthetic_population()
    segment.update(route_id='r', segment_sha256='a' * 64, run=np.zeros(len(segment['tick']), np.int64), within=np.arange(len(segment['tick']), dtype=np.int64))
    candidate, fold = d.JOBS[0]
    _, anchor, n = ev.e1.data.binding([segment], candidate, 1)
    provider = object.__new__(inp.Provider)
    provider.reader = type('R', (), {'phase': inp.Phase()})()
    provider.reader.phase.job = (candidate, fold)
    provider.segments = (segment,)
    provider.references = [{'candidate_id': candidate, 'fold': fold, 'train_route': 'r', 'train_anchor_sha256': anchor, 'train_count': n}]
    provider.bound_jobs = [{'fields': [{'anchor_sha256': anchor}]}]
    self.assertEqual(provider.train_blocks(0)[1:], (anchor, n))
    provider.references[0]['train_anchor_sha256'] = 'b' * 64
    with self.assertRaisesRegex(ValueError, 'ANCHOR_CONFLICT'):
      provider.train_blocks(0)
    provider.references[0]['train_anchor_sha256'] = anchor
    segment['within'][100] = 1
    with self.assertRaisesRegex(ValueError, 'BOUNDARY'):
      provider.train_blocks(0)

  def test_no_source_access_in_verify_only_code(self):
    import inspect

    source = inspect.getsource(ev.verify_only) + inspect.getsource(ev.validate_stored)
    for forbidden in ('np.load', 'predict_delta(', 'recursive(', 'open(', 'reconstruct_D0(', 'select_job('):
      self.assertNotIn(forbidden, source)


def stored_fixture():
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

  context = {
    'decision': 0.5,
    'positive': 201,
    'negative': 201,
    'count': 402,
    'witness_verified': True,
    'guards': dict.fromkeys(('TRUE_MOVE_TP', 'TRUE_MOVE_SSE', 'TRUE_MOVE_SAE', 'HARMFUL_STATIC'), True),
    'candidate_count': 2,
    'feasible_count': 1,
    'TRUE_MOVE_TP': 201,
    'harmful_static': 0,
    'continuous_sse': 0.0,
    'continuous_sae': 0.0,
    'TRUE_MOVE_SSE': 0.0,
    'TRUE_MOVE_SAE': 0.0,
  }
  pair = {
    'count': 804,
    'anchor_sha256': 'a' * 64,
    'comparator_anchor_sha256': 'a' * 64,
    'candidate': {'rmse': 0.0, 'mae': 0.0, 'p95': 0.0},
    'comparator': {'rmse': 1.0, 'mae': 1.0, 'p95': 1.0},
  }
  arm = {
    'status': 'EXECUTED_COMPLETE',
    'one_step': pair,
    'true_move': pair,
    'rollout': {str(h): {'overall': pair, 'path_moved': pair, 'status': 'COMPLETE'} for h in ev.HORIZONS},
    'gate': {'pass': True, 'failures': [], 'clauses': [{'id': cid, 'pass': True, 'evaluated': True} for cid in ev.CLAUSE_IDS]},
  }
  context.update(net_exact_hit_gain=201, D0_reference={'TP': 201, 'TRUE_MOVE_SSE': 0.0, 'TRUE_MOVE_SAE': 0.0, 'harmful_static': 0, 'net_exact_hit_gain': 201})
  jobs = [
    {
      'candidate_id': c,
      'fold': f,
      'TRAIN': {'candidate_id': c, 'fold': f, 'count': 804, 'contexts': {k: copy.deepcopy(context) for k in d.CONTEXTS}},
      'arms': {a: copy.deepcopy(arm) for a in pub.ARMS},
    }
    for c, f in d.JOBS
  ]
  return run.sealed(
    {
      'schema': 'V4_E2_CANONICAL_RESULT_V1',
      'protocol_sha256': '1' * 64,
      'head': 'h',
      'jobs': jobs,
      'operation_counters': {
        'TRAIN_numerical_qualification_jobs': 32,
        'D0_TRAIN_reconstruction_calls': 32,
        'D2_context_decision_selection_calls': 64,
        'D2_scientific_job_evaluation_calls': 32,
      },
      'selected_candidate': None,
      'selected_policy': None,
      'holdout': 'CLOSED',
      'vehicle_authority': 'NONE',
      'forbidden_operation_counters': dict.fromkeys(ev.FORBIDDEN, 0),
      'mixed_carrier_openings': 0,
      'original_D0_threshold_readings': 0,
      'original_TRAIN_gate': 'NOT_SAVED',
      'original_replica': 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED',
    }
  )


class TestE2StoredResult(unittest.TestCase):
  def test_stored_guard_flags_cannot_override_scalar_contradictions(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    for key, new in [('TRUE_MOVE_TP', 202), ('harmful_static', 202), ('net_exact_hit_gain', 'invalid'), ('TRUE_MOVE_SSE', 1.0), ('TRUE_MOVE_SAE', 1.0)]:
      v = stored_fixture()
      v['jobs'][0]['TRAIN']['contexts']['PREVIOUS_STATIC'][key] = new
      v.pop('receipt_sha256')
      v = run.sealed(v)
      with self.subTest(key=key), self.assertRaises(ValueError):
        ev.validate_stored(v, '1' * 64)

  def test_duplicate_or_wrong_role_review_cannot_grant_access(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    one = run.sealed(
      {'reviewer': 'science-agent', 'role': 'SCIENTIFIC_NUMERICAL_CAUSAL', 'approval': 'APPROVED', 'protocol_raw_sha256': 'a' * 64, 'source_sha256': {}}
    )
    two = run.sealed(
      {
        'reviewer': 'authority-agent',
        'role': 'AUTHORITY_PRIVACY_SOURCE_INTEGRITY',
        'approval': 'APPROVED',
        'protocol_raw_sha256': 'a' * 64,
        'source_sha256': {},
      }
    )
    gate = {'review_receipts': {'science-review.json': one['receipt_sha256'], 'authority-review.json': two['receipt_sha256']}}
    run.verify_reviews(gate, {'science-review.json': one, 'authority-review.json': two}, 'a' * 64, {})
    for bad in (one, {**two, 'reviewer': 'science-agent'}, {**two, 'role': 'SCIENTIFIC_NUMERICAL_CAUSAL'}):
      with self.assertRaises(ValueError):
        run.verify_reviews(gate, {'science-review.json': one, 'authority-review.json': bad}, 'a' * 64, {})

  def test_valid_verify_only_never_calls_inference(self):
    v = stored_fixture()
    raw = ev.canonical(v)
    with patch.object(d, 'potentials', side_effect=AssertionError('source/inference')), patch.object(d, 'select_job', side_effect=AssertionError('recompute')):
      out = ev.verify_only(raw, ev.sha(raw), '1' * 64, head='h')
    self.assertEqual(out, {'status': 'E2_VERIFY_ONLY_PASS', 'source_rereads': 0, 'inference_calls': 0, 'recompute_calls': 0, 'source_writes': 0})

  def test_stored_authority_gate_train_mutations_fail(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run

    for defect in (
      'mixed',
      'threshold',
      'gate',
      'train',
      'guard',
      'horizon',
      'nonfinite',
      'count',
      'fake_clause',
      'null_metric',
      'bool_decision',
      'unevaluated',
    ):
      v = stored_fixture()
      if defect == 'mixed':
        v['mixed_carrier_openings'] = 1
      elif defect == 'threshold':
        v['original_D0_threshold_readings'] = 1
      elif defect == 'gate':
        v['jobs'][0]['arms']['D2']['gate']['pass'] = False
      elif defect == 'train':
        v['jobs'][0]['TRAIN']['fold'] = 'FOLD_B'
      elif defect == 'guard':
        v['jobs'][0]['TRAIN']['contexts']['PREVIOUS_MOVE']['guards']['TRUE_MOVE_SSE'] = False
      elif defect == 'horizon':
        del v['jobs'][0]['arms']['D2']['rollout']['200']
      elif defect == 'nonfinite':
        v['jobs'][0]['TRAIN']['contexts']['PREVIOUS_MOVE']['continuous_sse'] = -1.0
      elif defect == 'unevaluated':
        v['jobs'][0]['arms']['D2']['gate']['clauses'][0]['evaluated'] = False
      elif defect == 'fake_clause':
        v['jobs'][0]['arms']['D2']['gate']['clauses'][0]['id'] = 'FAKE'
      elif defect == 'null_metric':
        v['jobs'][0]['arms']['D2']['one_step'] = None
      elif defect == 'bool_decision':
        v['jobs'][0]['TRAIN']['contexts']['PREVIOUS_MOVE']['decision'] = True
      elif defect == 'count':
        v['jobs'][0]['TRAIN']['count'] = 803
      del v['receipt_sha256']
      v = run.sealed(v)
      with self.subTest(defect=defect), self.assertRaises(ValueError):
        ev.validate_stored(v, '1' * 64)


class TestE2ProviderChain(unittest.TestCase):
  def test_complete_synthetic_root_source_normalizer_head_chain(self):
    from openpilot.tools.cyber_autotune.tests import test_empirical_hurdle_v4_e_evaluation as previous

    class Adapter(inp.Provider):
      def admit_segments(self):
        self.reader.phase.require_dev()
        self.admit_train_sources()

      def models(self, index):
        if index not in self.stage2_cache:
          self.stage2(index)
        return super().models(index)

    # The existing in-memory fixture supplies all154 bound segment receipts,
    # NPY bytes, root maps and model chains. Only its phase setup is adapted;
    # production E2 member/phase enforcement has separate negative tests.
    with patch.object(previous.inputs, 'Provider', Adapter), patch.object(previous.inputs, 'Phase', inp.Phase):
      previous.TestEProvider('test_synthetic_manifest_source_and_model_admission_chain').test_synthetic_manifest_source_and_model_admission_chain()


class TestE2Lifecycle(unittest.TestCase):
  def run_boundary(self, fail_qualification):
    import json
    import contextlib
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as run
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_bootstrap as boot
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as olddec
    from openpilot.tools.cyber_autotune import empirical_s2_ri_policy

    protocol = run.checked((run.PUBLIC / run.PROTOCOL_NAME).read_bytes())
    p = np.array([0.1, 0.9, 0.1, 0.9])
    y = np.array([0, 1, 0, 1], bool)
    prior = np.array([0, 0, 1, 1], np.int64)
    cache = {
      'p': p,
      'y': y,
      'prior': prior,
      'current': np.zeros(4, np.int64),
      'target': y.astype(np.int64),
      'u': np.ones(4),
      'move_tick': np.ones(4, np.int64),
      'D0_gate': y.copy(),
    }
    jobs = [{'candidate_id': c, 'fold': f, 'fields': [{'anchor_sha256': 'a' * 64}]} for c, f in d.JOBS]

    class Provider:
      def __init__(self, *_args, **_kwargs):
        pass

      def admit_train_sources(self):
        pass

      def train(self, index):
        return p.copy(), y.copy(), prior.copy()

      def train_blocks(self, index):
        return [], 'a' * 64, 4

      def stage2(self, index):
        return fixture_model()[1]

    modules = {
      'empirical_hurdle_v4_e2_inputs': inp,
      'empirical_hurdle_v4_e2_decision': d,
      'empirical_hurdle_v4_e2_evaluation': ev,
      'empirical_hurdle_v4_e_evaluation': ev.e1,
      'empirical_hurdle_v4_e_decision': olddec,
      'empirical_hurdle_v4_e_bootstrap': boot,
      'empirical_s2_ri_policy': empirical_s2_ri_policy,
    }
    boot.warm_dependencies()
    original_private = run.private
    reads = []

    def controlled_private(path, cap=16 * 1024**2):
      if path.name == 'canonical-result.json':
        reads.append('DEV_ATTEMPT')
        raise FileNotFoundError('synthetic missing comparison after barrier')
      return original_private(path, cap)

    def potential(*_args, **_kwargs):
      if fail_qualification:
        raise ValueError('E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED')
      return {k: v.copy() for k, v in cache.items()}

    with tempfile.TemporaryDirectory() as tmp:
      work = Path(tmp)
      work.chmod(0o700)
      roots = {k: str(work / k) for k in ('V4', 'V1', 'V1_TOP', 'CAUSAL', 'DERIVED')}
      refs = {'references': {'WORK': str(work / 'old')}}
      binding = {'E1_canonical_raw_sha256': 'a' * 64, 'E1_head': 'old', 'prior_lineage': {}}
      args = (
        protocol,
        b'synthetic-protocol',
        modules,
        binding,
        roots,
        {'manifests': {'V4_REPEAT_1': {}, 'V1_REFERENCE': {}}, 'authorization': {'V1_REFERENCE': 'a' * 64}},
        {},
        jobs,
        (work.stat().st_dev, work.stat().st_ino),
        refs,
      )
      with (
        patch.object(run.resource, 'setrlimit'),
        patch.object(run.signal, 'signal'),
        patch.object(run.signal, 'alarm'),
        patch.object(run, 'preflight', return_value=args),
        patch.object(inp, 'Provider', Provider),
        patch.object(d, 'potentials', side_effect=potential),
        patch.object(run, 'private', side_effect=controlled_private),
        contextlib.redirect_stdout(io.StringIO()),
        self.assertRaises(SystemExit),
      ):
        run.run(work, 'repeat-1')
      envelope = json.loads((work / 'repeat-1/execution-envelope.json').read_bytes())
      if fail_qualification:
        self.assertEqual(envelope['status'], 'E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED', envelope)
        self.assertEqual(envelope['qualified_TRAIN_jobs'], 0)
        self.assertEqual(envelope['operation_counters'].get('D2_context_decision_selection_calls', 0), 0)
        self.assertEqual(reads, [])
        self.assertFalse((work / 'repeat-1/train-decisions.json').exists())
      else:
        self.assertEqual(envelope['qualified_TRAIN_jobs'], 32, envelope)
        self.assertEqual(envelope['operation_counters']['D2_context_decision_selection_calls'], 64)
        self.assertEqual(reads, ['DEV_ATTEMPT'])
        train = run.checked(original_private(work / 'repeat-1/train-decisions.json'))
        self.assertEqual(train['qualification_PASS_jobs'], 32)
        self.assertEqual(len(train['jobs']), 32)
      self.assertEqual(envelope['source_writes'], 0)

  def test_numeric_failure_never_selects_or_opens_DEV(self):
    self.run_boundary(True)

  def test_all32_qualification_then64_durable_before_DEV(self):
    self.run_boundary(False)


class TestE2CompositeDisclosure(unittest.TestCase):
  def fixture(self):
    rows = []
    for c, f in d.JOBS:
      arms = {}
      for a, n_all, n_move in [('D0', 600, 600), ('D1', 100, 100), ('D2', 400, 399)]:

        def pair(n, sse):
          return {'count': n, 'candidate': {'rmse': (sse / n) ** 0.5, 'mae': sse / n, 'p95': 1.0}}

        arms[a] = {
          'one_step': pair(1000, n_all),
          'true_move': pair(600, n_move),
          'tick_diagnostics': None,
          'rollout': {str(h): {'overall': None, 'path_moved': None} for h in ev.HORIZONS},
          'gate': {'pass': False, 'failures': ['synthetic']},
        }
      arms['D1']['paired_changes'] = dict(
        zip(('projected_rows', 'continuous_rows', 'true_move_projected_rows', 'true_move_continuous_rows'), (500, 500, 500, 500), strict=True)
      )
      arms['D2']['paired_changes'] = dict(zip(arms['D1']['paired_changes'], (202, 202, 201, 201), strict=True))
      arms['D2']['D1_changed_lower_bounds'] = dict(zip(arms['D1']['paired_changes'], (298, 298, 299, 299), strict=True))
      rows.append({'candidate_id': c, 'fold': f, 'arms': arms})
    return {'jobs': rows, 'protocol_sha256': '0' * 64}

  def test_whole_true_MOVE_rare_STATIC_complement_suppresses_both(self):
    payload = self.fixture()
    out = pub.project(payload)
    self.assertFalse(pub.complement_safe(payload['jobs']))
    for name in ('one_step', 'true_move'):
      self.assertEqual(out['metric_families'][name]['status'], 'JOINTLY_SUPPRESSED_OR_NONPASS')

  def test_rollout_rare_STATIC_PATH_complement_suppresses_both(self):
    payload = self.fixture()
    for row in payload['jobs']:
      for a in pub.ARMS:
        row['arms'][a]['rollout']['25'].update(overall=row['arms'][a]['one_step'], path_moved=row['arms'][a]['true_move'])
      for a, full, sub in [('D1', 500, 500), ('D2', 202, 201)]:
        row['arms'][a]['rollout']['25'].update(paired_changed_endpoint_rows=full, paired_changed_path_moved_endpoint_rows=sub)
      row['arms']['D2']['rollout']['25'].update(D1_changed_endpoint_lower_bound=298, D1_changed_path_moved_endpoint_lower_bound=299)
    out = pub.project(payload)
    self.assertFalse(pub.complement_safe(payload['jobs'], horizon=25))
    for name in ('H25_OVERALL', 'H25_PATH_MOVED'):
      self.assertEqual(out['metric_families'][name]['status'], 'JOINTLY_SUPPRESSED_OR_NONPASS')

  def test_harmful_count_never_reveals_rare_FP_to_HOLD_complement(self):
    out = pub.project(self.fixture())
    self.assertEqual(out['metric_families']['HARMFUL_NEXT_STATIC_REALIZATION']['status'], 'WITHHELD_GATE_TO_HOLD_COMPLEMENT_C_E_PROTECTION')


if __name__ == '__main__':
  unittest.main()
