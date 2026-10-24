"""V3 contracts and small in-memory fixtures; never private performance data."""

import copy
import importlib
import importlib.util
import itertools
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np


class TestV3(unittest.TestCase):
  def setUp(self):
    name = 'openpilot.tools.cyber_autotune.empirical_hurdle_v3_scaffold'
    self.assertIsNotNone(importlib.util.find_spec(name), 'V3 scaffold missing')
    self.s = importlib.import_module(name)

  def fixture(self, scores=None):
    return {
      'probability': np.array(scores if scores is not None else [0.1, 0.2, 0.8, 0.9], dtype=np.float64),
      'branch_delta': np.array([0.1, 1.1, 1.0, -2.0]),
      'current': np.zeros(4, dtype=np.int64),
      'target': np.array([0, 0, 1, -2], dtype=np.int64),
      'reference_tp': 1,
      'role': 'SYNTHETIC_TRAIN',
    }

  def test_private_execution_always_disabled_before_any_path_read(self):
    with patch.object(Path, 'open', side_effect=AssertionError('private read')):
      for auth in (None, {}, {'authorized': True}):
        with self.assertRaisesRegex(ValueError, 'PRIVATE_EXECUTION_NOT_IMPLEMENTED'):
          self.s.execute_private(authorization=auth)

  def test_exact_recall_floor(self):
    r = self.s.evaluate(**self.fixture())
    self.assertGreaterEqual(r['selected']['tp'], 1)
    self.assertEqual(r['selected']['exact_hit_count'], 4)

  def test_empty_feasible_no_fallback(self):
    x = self.fixture()
    x['branch_delta'] = np.zeros(4)
    r = self.s.evaluate(**x)
    self.assertEqual(r['status'], 'V3_NO_FEASIBLE_THRESHOLD')
    self.assertIsNone(r['threshold'])

  def test_reference_must_not_be_extreme_suppression(self):
    for ref in (0, -1, 3, True, 1.0):
      x = self.fixture()
      x['reference_tp'] = ref
      with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, 'REFERENCE_CONFLICT'):
        self.s.evaluate(**x)

  def test_source_reference_guard_exact_boundary(self):
    self.s.validate_reference(2, 20)
    with self.assertRaisesRegex(ValueError, 'REFERENCE_CONFLICT'):
      self.s.validate_reference(1, 20)

  def test_all_static_and_all_move_rejected(self):
    for target in (np.zeros(4, dtype=np.int64), np.ones(4, dtype=np.int64)):
      x = self.fixture()
      x['target'] = target
      with self.assertRaisesRegex(ValueError, 'CLASSES_REQUIRED'):
        self.s.evaluate(**x)

  def test_exhaustive_ties_ranks_and_reference_counts(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as old

    for scores in itertools.product((0.0, 0.25, 1.0), repeat=4):
      for ref in (1, 2):
        x = self.fixture(scores)
        x['reference_tp'] = ref
        r = self.s.evaluate(**x)
        rows = []
        for threshold in old.candidates(x['probability']):
          row = old.canonical(x['probability'], x['branch_delta'], x['current'], x['target'], threshold)
          row['tp'] = int(np.count_nonzero((x['target'] != 0) & (x['probability'] > threshold)))
          row['feasible'] = row['feasible'] and row['tp'] >= ref
          rows.append((float(threshold), row))
        self.assertEqual(r['rows'], rows)
        feasible = [(old.key(th, row), th) for th, row in rows if row['feasible']]
        self.assertEqual(r['threshold'], max(feasible)[1] if feasible else None)

  def test_rare_burst_isolated_multi_tick(self):
    for truth in ([0] * 20 + [1] + [0] * 10, [0, 1, 1, 1, 0, 0], [0, 1, 0, -1, 0], [0, 2, 0, -3, 0]):
      target = np.array(truth, dtype=np.int64)
      r = self.s.evaluate(
        probability=np.where(target != 0, 0.9, 0.1),
        branch_delta=target.astype(float),
        current=np.zeros(len(target), dtype=np.int64),
        target=target,
        reference_tp=int(np.count_nonzero(target)),
        role='SYNTHETIC_TRAIN',
      )
      self.assertEqual(r['selected']['exact_hit_count'], len(target))

  def test_calibration_shift_preserves_order_but_no_dev_guarantee(self):
    for scores in ([0.01, 0.02, 0.08, 0.09], [0.81, 0.82, 0.88, 0.89]):
      self.assertEqual(self.s.evaluate(**self.fixture(scores))['selected']['exact_hit_count'], 4)

  def test_equality_is_static(self):
    self.assertEqual(self.s.gate(np.array([0.2, 0.5, 0.8]), 0.5).tolist(), [False, False, True])

  def test_gate_is_stateless_across_route_and_segment_resets(self):
    scores = np.array([0.8, 0.1, 0.8, 0.1])
    whole = self.s.gate(scores, 0.2)
    split = np.r_[self.s.gate(scores[:2], 0.2), self.s.gate(scores[2:], 0.2)]
    np.testing.assert_array_equal(whole, split)

  def test_future_scores_cannot_change_prefix(self):
    a = np.array([0.1, 0.8, 0.2, 0.9])
    b = a.copy()
    b[2:] = 0
    np.testing.assert_array_equal(self.s.gate(a, 0.3)[:2], self.s.gate(b, 0.3)[:2])

  def test_no_true_label_inference_interface(self):
    with self.assertRaises(TypeError):
      self.s.gate(np.array([0.2]), 0.3, true_move=np.array([True]))

  def test_leakage_roles_rejected(self):
    for role in ('TRAIN', 'DEVELOPMENT', 'HOLDOUT', 'ROLLOUT', 'V1_DEVELOPMENT'):
      x = self.fixture()
      x['role'] = role
      with self.subTest(role=role), self.assertRaisesRegex(ValueError, 'SYNTHETIC_TRAIN_ONLY'):
        self.s.evaluate(**x)

  def test_extra_leakage_arguments_rejected(self):
    for key in (
      'development',
      'holdout',
      'v1_dev_metrics',
      'attribution',
      'future_angle',
      'steeringRateDeg',
      'request_torque',
      'epsilon',
      'threshold_candidates',
    ):
      with self.subTest(key=key), self.assertRaises(TypeError):
        self.s.evaluate(**self.fixture(), **{key: []})

  def test_projected_false_move_not_gate_move(self):
    x = self.fixture()
    x['branch_delta'][:2] = [0.1, 0.2]
    r = self.s.evaluate(**x)
    row = r['rows'][0][1]
    self.assertEqual(row['static_projected_false_move_count'], 0)

  def test_half_even_signed_tick_projection(self):
    x = self.fixture()
    x['branch_delta'] = np.array([0.5, 1.5, 1.0, -2.0])
    row = self.s.evaluate(**x)['rows'][0][1]
    self.assertEqual(row['static_projected_false_move_count'], 1)

  def test_p95_adjacent_binary64_and_signed_zero(self):
    x = self.fixture([0.0, -0.0, np.nextafter(0.5, 1), 0.5])
    x['branch_delta'] = np.array([0.0, -0.0, np.nextafter(1.0, 2.0), -1.999])
    self.assertEqual(self.s.evaluate(**x), self.s.evaluate(**x))

  def test_no_fit_calls(self):
    with patch.object(np.linalg, 'solve', side_effect=AssertionError('fit')), patch.object(np.linalg, 'lstsq', side_effect=AssertionError('fit')):
      self.s.evaluate(**self.fixture())

  def test_projection_nonfinite_failure_no_drop(self):
    for value in (np.nan, np.inf, 40000.0):
      x = self.fixture()
      x['branch_delta'][0] = value
      with self.assertRaises(ValueError):
        self.s.evaluate(**x)

  def test_out_of_range_truth_and_current_rejected_before_arithmetic(self):
    for field in ('current', 'target'):
      for value in (-32769, 32768, 40000, np.iinfo(np.int64).max):
        x = self.fixture()
        x[field][0] = value
        x['branch_delta'][0] = -float(value) if field == 'current' else 0.0
        with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, 'TICK_RANGE'):
          self.s.evaluate(**x)

  def test_objective_tie_order(self):
    base = {'exact_hit_count': 10, 'static_projected_false_move_count': 3, 'within_one_tick_count': 12}
    key = self.s.objective_key
    for better in ({**base, 'exact_hit_count': 11}, {**base, 'static_projected_false_move_count': 2}, {**base, 'within_one_tick_count': 13}):
      self.assertGreater(key(0.2, better), key(0.2, base))
    self.assertGreater(key(0.8, base), key(0.2, base))

  def test_same_model_and_anchor_identity(self):
    reference = dict.fromkeys(self.s.IDENTITY_FIELDS, 'a' * 64)
    self.s.check_identity(reference, dict(reference))
    for field in reference:
      with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'IDENTITY_CONFLICT'):
        self.s.check_identity(reference, {**reference, field: 'b' * 64})

  def test_deterministic_lossless_compression(self):
    x = np.array([0.0, -0.0, 1.0, np.nextafter(1.0, 2.0)])
    first = self.s.compress(x)
    second = self.s.compress(x.copy())
    self.assertEqual(first, second)
    np.testing.assert_array_equal(self.s.decode(*first), x)
    self.assertEqual(self.s.decode(*first).tobytes(), x.tobytes())

  def test_one_byte_mutation_rejected(self):
    payload, receipt = self.s.compress(np.arange(10, dtype=np.int64))
    damaged = bytearray(payload)
    damaged[-1] ^= 1
    with self.assertRaisesRegex(ValueError, 'CONTENT_CONFLICT'):
      self.s.decode(bytes(damaged), receipt)

  def test_c_output_traversal_and_overlap_rejected(self):
    for path in ('/mnt/c/out', '/mnt/d/a/../out', '/mnt/d/source/out'):
      with self.assertRaises(ValueError):
        self.s.check_output(Path(path), Path('/mnt/d/source'))

  def test_saved_store_resume_no_compute_or_source(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp) / 'result'
      with patch.object(self.s, 'check_output'):
        m = self.s.write_store(root, Path('/synthetic-source'), {'readiness': 'SYNTHETIC_ONLY', 'gate_count': 32})
      with (
        patch.object(self.s, 'evaluate', side_effect=AssertionError('compute')),
        patch.object(self.s, 'execute_private', side_effect=AssertionError('source')),
      ):
        self.assertEqual(self.s.resume(root), m)
      (root / 'aggregate.json').write_text('{}')
      with self.assertRaises(ValueError):
        self.s.resume(root)

  def test_store_no_private_payload_or_model_duplication(self):
    for key in ('threshold', 'coefficients', 'normalizer', 'truth', 'observed_path', 'hold_last_path', 'private_path', 'predictions'):
      with self.assertRaisesRegex(ValueError, 'AGGREGATE_ALLOWLIST'):
        self.s.validate_aggregate({key: [1]})

  def test_run2_cleanup_requires_exact_durable_proof(self):
    a = {'files': {'a': 'f' * 64}, 'manifest_sha256': 'a' * 64}
    with self.assertRaises(ValueError):
      self.s.cleanup_eligible(a, a, {})
    proof = dict.fromkeys(self.s.DURABLE_FIELDS, 'a' * 64)
    self.assertTrue(self.s.cleanup_eligible(a, a, proof))
    with self.assertRaises(ValueError):
      self.s.cleanup_eligible(a, {**a, 'files': {'a': 'b' * 64}}, proof)

  def test_contracts_freeze_only_decision_and_preserve_authority(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_policy as policy

    b = policy.build()
    policy.validate(b)
    r = b[policy.filename('design-readiness')]
    self.assertEqual(r['status'], 'HURDLE_STAGE1_DECISION_POLICY_V3_DESIGN_FROZEN')
    self.assertEqual(r['v3_private_execution'], 'NOT_RUN')
    self.assertEqual(r['model_strategy'], 'REUSE_BYTE_IDENTICAL_V1_FITTED_MODELS')

  def test_contract_mutations_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_policy as policy

    b = policy.build()
    for label, field, value in (
      ('training-policy', 'recall_constraint', 'TP>=0'),
      ('parameter-contract', 'decision_operator', '>='),
      ('state-contract', 'state', 'HYSTERESIS'),
      ('execution-policy', 'actual_execution_authorized', True),
      ('acceptance-binding', 'gate', 'RELAXED'),
    ):
      changed = copy.deepcopy(b)
      n = policy.filename(label)
      changed[n] = policy.p.seal({**changed[n], field: value})
      with self.subTest(label=label), self.assertRaisesRegex(ValueError, 'POLICY_CONFLICT'):
        policy.validate(changed)

  def test_resealed_unpinned_temporal_trigger_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v3_policy as policy

    read = policy.io.read_json

    def substitute(path, expected=None):
      if path.name == policy.filename('temporal-design-trigger'):
        return policy.p.seal({'v3_performance': 'NOT_RUN', 'persistence_state': 'TEMPORAL_MOVE_PERSISTENCE_PRESENT_BOTH_ROUTES'})
      return read(path, expected)

    with patch.object(policy.io, 'read_json', side_effect=substitute), self.assertRaisesRegex(ValueError, 'EVIDENCE_CONFLICT'):
      policy.build()

  def test_frozen_gate_all_32_and_no_epsilon_or_missing_horizon(self):
    metrics = {'rmse': 1.0, 'mae': 1.0, 'p95': 1.0, 'exact_hit': 0.5, 'within_one_tick': 0.8}
    pair = {'count': 201, 'anchor_sha256': 'a' * 64, 'comparator_anchor_sha256': 'a' * 64, 'candidate': dict(metrics), 'comparator': dict(metrics)}
    job = {
      'status': 'EXECUTED_COMPLETE',
      'one_step': copy.deepcopy(pair),
      'true_move': copy.deepcopy(pair),
      'rollout': {str(h): {'overall': copy.deepcopy(pair), 'path_moved': copy.deepcopy(pair)} for h in (25, 50, 100, 200)},
    }
    self.assertEqual(self.s.synthetic_gate(job, role='SYNTHETIC')['failures'], ['ONE_STEP_RMSE'])
    job['one_step']['candidate']['rmse'] = np.nextafter(1.0, 0.0)
    self.assertTrue(self.s.synthetic_gate(job, role='SYNTHETIC')['pass'])
    del job['rollout']['200']
    r = self.s.synthetic_gate(job, role='SYNTHETIC')
    self.assertFalse(r['pass'])
    self.assertEqual(len(r['clauses']), 32)
    self.assertEqual(len(r['failures']), 6)
    with self.assertRaisesRegex(ValueError, 'SYNTHETIC_ONLY'):
      self.s.synthetic_gate(job, role='DEVELOPMENT')

  def test_store_no_overwrite_and_symlink_rejection(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp) / 'result'
      aggregate = {'readiness': 'SYNTHETIC_ONLY', 'gate_count': 32}
      with patch.object(self.s, 'check_output'):
        self.s.write_store(root, Path('/synthetic'), aggregate)
        with self.assertRaisesRegex(ValueError, 'NO_OVERWRITE'):
          self.s.write_store(root, Path('/synthetic'), aggregate)
        link = Path(tmp) / 'linked'
        link.symlink_to(root, target_is_directory=True)
        with self.assertRaises(ValueError):
          self.s.write_store(link, Path('/synthetic'), aggregate)
