"""Public-only V2 contracts and test-local synthetic qualification oracle; no runner."""
import ast
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic as diagnostic

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
AMENDMENT = 'empirical-hurdle-stage1-v4-e2-numerical-qualification-v2.json'
PROTOCOL = 'empirical-hurdle-stage1-v4-e2-execution-protocol-v2.json'
V1 = 'empirical-hurdle-stage1-v4-e2-execution-protocol.json'
Q1_FAILURE = 'E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED'
Q3_FAILURE = 'E2_D2_TRAIN_SELECTED_PATH_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED'


def digest(raw):
  return hashlib.sha256(raw).hexdigest()


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def document(name):
  return json.loads((PUBLIC / name).read_bytes())


def exact(a, b):
  return (a.dtype == b.dtype == np.dtype('float64') and a.shape == b.shape and a.ndim == b.ndim == 1
          and np.all(np.isfinite(a)) and np.all(np.isfinite(b)) and a.tobytes() == b.tobytes())


def qualify(cache, gate, selected, *, identity=True, transformed=True, empty_noop=False):
  """Test-local oracle over supplied synthetic outputs; never loads or computes a model."""
  if not identity or not transformed or cache.dtype != np.float64 or cache.ndim != 1 or not np.all(np.isfinite(cache)):
    return False
  if gate.dtype != bool or gate.shape != cache.shape:
    return False
  if not gate.any():
    return empty_noop and exact(selected, np.empty(0, np.float64))
  return exact(selected, cache[gate])


class Barrier:
  """Synthetic phase oracle, deliberately with no data/model/selection implementation."""
  def __init__(self, jobs):
    self.jobs = tuple(jobs)
    if len(self.jobs) != 32 or len(set(self.jobs)) != 32:
      raise ValueError('jobs')
    self.q1, self.q3 = set(), set()
    self.decisions = False
    self.sealed = False
    self.aborted = False

  def qualification(self, job, passed, *, stage):
    if self.aborted or job not in self.jobs or stage not in ('Q1', 'Q3'):
      raise ValueError('phase')
    target = self.q1 if stage == 'Q1' else self.q3
    if job in target or (stage == 'Q3' and not self.decisions):
      raise ValueError('phase')
    if not passed:
      self.aborted = True
      raise ValueError(Q1_FAILURE if stage == 'Q1' else Q3_FAILURE)
    target.add(job)

  def choose(self):
    if self.aborted or len(self.q1) != 32 or self.decisions:
      raise ValueError('before all Q1')
    self.decisions = True

  def seal(self, *, count, readback):
    if self.aborted or not self.decisions or len(self.q3) != 32 or count != 64 or not readback:
      raise ValueError('before all Q3 and durable readback')
    self.sealed = True

  def dev(self):
    if self.aborted or not self.sealed:
      raise ValueError('DEV blocked')
    return True


class TestV2QualificationSynthetic(unittest.TestCase):
  def setUp(self):
    self.cache = np.array([0.25, -0.75, 1.5, 0.0])
    self.gate = np.array([True, False, True, False])

  def test_contract_artifacts_required(self):
    self.assertTrue((PUBLIC / AMENDMENT).is_file(), 'V2 amendment missing')
    self.assertTrue((PUBLIC / PROTOCOL).is_file(), 'V2 protocol missing')

  def test_b_equal_c_equal(self):
    self.assertTrue(qualify(self.cache, self.gate, self.cache[self.gate]))

  def test_b_mismatch_c_equal(self):
    b = np.nextafter(self.cache[self.gate], np.inf)
    self.assertFalse(exact(b, self.cache[self.gate]))
    self.assertTrue(qualify(self.cache, self.gate, self.cache[self.gate]))

  def test_b_equal_c_mismatch(self):
    self.assertTrue(exact(self.cache[self.gate], self.cache[self.gate]))
    self.assertFalse(qualify(self.cache, self.gate, np.nextafter(self.cache[self.gate], np.inf)))

  def test_b_mismatch_c_mismatch(self):
    self.assertFalse(qualify(self.cache, self.gate, np.nextafter(self.cache[self.gate], -np.inf)))

  def test_projection_equality_cannot_replace_bytes(self):
    a = np.array([0.25])
    b = np.nextafter(a, np.inf)
    np.testing.assert_array_equal(diagnostic.frozen.project(a), diagnostic.frozen.project(b))
    self.assertFalse(qualify(a, np.ones(1, bool), b))

  def test_one_ulp_can_change_tick(self):
    a = np.array([0.5])
    b = np.nextafter(a, np.inf)
    self.assertNotEqual(diagnostic.frozen.project(a)[0], diagnostic.frozen.project(b)[0])
    self.assertFalse(exact(a, b))

  def test_signed_zero_not_equal(self):
    self.assertFalse(exact(np.array([0.0]), np.array([-0.0])))

  def test_dtype_mismatch(self):
    self.assertFalse(qualify(self.cache, self.gate, self.cache[self.gate].astype(np.float32)))

  def test_shape_mismatch(self):
    self.assertFalse(qualify(self.cache, self.gate, self.cache[self.gate, None]))

  def test_original_order_required(self):
    self.assertFalse(qualify(self.cache, self.gate, self.cache[self.gate][::-1]))

  def test_normalizer_or_model_identity_conflict(self):
    self.assertFalse(qualify(self.cache, self.gate, self.cache[self.gate], identity=False))

  def test_transformed_row_conflict(self):
    self.assertFalse(qualify(self.cache, self.gate, self.cache[self.gate], transformed=False))

  def test_anchor_conflict(self):
    self.assertFalse(qualify(self.cache, self.gate, self.cache[self.gate], identity=False))

  def test_nonfinite(self):
    for value in (np.nan, np.inf, -np.inf):
      a = self.cache.copy()
      a[0] = value
      self.assertFalse(qualify(a, self.gate, a[self.gate]))

  def test_empty_gate_requires_noop_proof(self):
    gate = np.zeros(4, bool)
    self.assertFalse(qualify(self.cache, gate, np.empty(0)))
    self.assertTrue(qualify(self.cache, gate, np.empty(0), empty_noop=True))

  def test_original_empty_gate_skips_stage2(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as frozen
    score = np.zeros(4, np.float64)
    predict = Mock(side_effect=AssertionError('empty gate must not call Stage2'))
    from unittest.mock import patch
    with patch.object(frozen, 'probability', return_value=score), patch.object(frozen.m, 'predict_delta', predict):
      current = np.array([1, 2, 3, 4], np.int64)
      delta, projected, _, gate = frozen.integrated(np.ones((4, 5)), current, {}, 1.0, {})
    self.assertFalse(gate.any())
    self.assertEqual(delta.tobytes(), np.zeros(4, np.float64).tobytes())
    np.testing.assert_array_equal(projected, current)
    predict.assert_not_called()

  def test_all_move_gate(self):
    self.assertTrue(qualify(self.cache, np.ones(4, bool), self.cache.copy()))

  def test_duplicate_scores_signedzero_and_strict_gate(self):
    score = np.array([-0.0, 0.0, 0.2, 0.2, 1.0])
    candidates = sorted({0.0, 1.0, *score.tolist()})
    self.assertEqual(candidates, [0.0, 0.2, 1.0])
    np.testing.assert_array_equal(score > 0.2, [False, False, False, False, True])

  def test_original_d0_reconstruction_synthetic(self):
    score = np.array([0.1, 0.5, 0.5, 0.9])
    truth = np.array([0, 0, 1, 1], bool)
    candidates = sorted({0.0, 1.0, *score.tolist()})
    expected = max(candidates, key=lambda t: (int(np.sum((score > t) & truth)) * 2 + int(np.sum((score <= t) & ~truth)) * 2,
                                              int(np.sum((score <= t) & ~truth)), t))
    self.assertEqual(diagnostic.frozen.threshold(score, truth, role="TRAIN")["value"], expected)

  def test_different_batch_shapes_transform_rows_preserved(self):
    x, gate, model = diagnostic.fixture(1, 1.0, 'alternating')
    transformed = diagnostic.frozen.transform(x, model['normalizer'])
    selected = diagnostic.frozen.transform(np.ascontiguousarray(x[gate]), model['normalizer'])
    self.assertTrue(diagnostic.byte_equal(selected, transformed[gate]))
    row = diagnostic.diagnose([x[:701].copy(), x[701:].copy()], gate, model, current=np.zeros(len(x), np.int64))
    self.assertTrue(row['transformed_rows_byte_equal'])
    self.assertEqual(row['calls']['all_chunk'], 4)
    self.assertEqual(row['calls']['whole_subset'], 1)
    # No backend-dependent expectation that a particular synthetic fixture must differ.
    self.assertIn(row['comparisons']['C_vs_A']['byte_qualification'], ('PASS', 'FAIL'))

  def test_frozen_60_plus_60_fixture_identity(self):
    self.assertEqual((diagnostic.SEED, diagnostic.ROWS, diagnostic.CHUNK), (20261018, 1537, 512))
    self.assertEqual(len(diagnostic.LENGTHS) * len(diagnostic.SCALES) * len(diagnostic.MASKS), 60)
    self.assertIn('def parity_control(', inspect.getsource(diagnostic))

  def test_partial_q1_blocks_selection(self):
    b = Barrier(range(32))
    for job in range(31):
      b.qualification(job, True, stage='Q1')
    with self.assertRaises(ValueError):
      b.choose()

  def test_q1_failure_is_global_terminal(self):
    b = Barrier(range(32))
    with self.assertRaisesRegex(ValueError, Q1_FAILURE):
      b.qualification(0, False, stage='Q1')
    with self.assertRaises(ValueError):
      b.choose()

  def test_q3_cannot_precede_selection(self):
    with self.assertRaises(ValueError):
      Barrier(range(32)).qualification(0, True, stage='Q3')

  def ready(self):
    b = Barrier(range(32))
    for job in range(32):
      b.qualification(job, True, stage='Q1')
    b.choose()
    return b

  def test_q3_failure_blocks_dev_and_reselection(self):
    b = self.ready()
    with self.assertRaisesRegex(ValueError, Q3_FAILURE):
      b.qualification(0, False, stage='Q3')
    with self.assertRaises(ValueError):
      b.dev()
    with self.assertRaises(ValueError):
      b.choose()

  def test_missing_q3_blocks_seal(self):
    b = self.ready()
    for job in range(31):
      b.qualification(job, True, stage='Q3')
    with self.assertRaises(ValueError):
      b.seal(count=64, readback=True)

  def test_durable_seal_readback_required(self):
    b = self.ready()
    for job in range(32):
      b.qualification(job, True, stage='Q3')
    for count, readback in ((63, True), (64, False)):
      with self.assertRaises(ValueError):
        b.seal(count=count, readback=readback)
    with self.assertRaises(ValueError):
      b.dev()
    b.seal(count=64, readback=True)
    self.assertTrue(b.dev())

  def test_duplicate_or_unknown_job_rejected(self):
    with self.assertRaises(ValueError):
      Barrier([0] * 32)
    b = Barrier(range(32))
    with self.assertRaises(ValueError):
      b.qualification(33, True, stage='Q1')
    b.qualification(0, True, stage='Q1')
    with self.assertRaises(ValueError):
      b.qualification(0, True, stage='Q1')


class TestV2FrozenDocuments(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.a, cls.p, cls.old = document(AMENDMENT), document(PROTOCOL), document(V1)

  def test_canonical_receipts(self):
    for value in (self.a, self.p):
      self.assertEqual(value['receipt_sha256'], digest(canonical({k: v for k, v in value.items() if k != 'receipt_sha256'})))

  def test_lineage_hashes(self):
    for item in self.a['input_lock']:
      self.assertEqual(digest((ROOT / item['path']).read_bytes()), item['raw_sha256'])
    self.assertEqual(digest((PUBLIC / AMENDMENT).read_bytes()), self.p['qualification_amendment']['raw_sha256'])

  def test_v1_historical_failure_immutable(self):
    self.assertEqual(digest((PUBLIC / V1).read_bytes()), '177925af0d9a70fecaeb2f8d848dbdee9c620f92047a9d8320e0ed6e1e7ef7db')
    self.assertEqual(self.a['historical_status'], Q1_FAILURE)
    self.assertFalse(self.a['historical_failure_reclassified'])

  def test_q1_q2_q3_roles(self):
    self.assertEqual(self.a['qualifications']['Q1']['role'], 'MANDATORY_HARD_GATE')
    self.assertEqual(self.a['qualifications']['Q2']['role'], 'NON_AUTHORITATIVE_DIAGNOSTIC')
    self.assertEqual(self.a['qualifications']['Q3']['role'], 'MANDATORY_POST_SELECTION_HARD_GATE')
    self.assertEqual(self.a['qualifications']['Q2']['default_private_status'], 'NOT_EXECUTED_DIAGNOSTIC')
    self.assertEqual(self.a['qualifications']['Q3']['failure'], Q3_FAILURE)

  def test_phase_order_exact(self):
    self.assertEqual([x['id'] for x in self.a['phases']], list('ABCDEFGH'))
    self.assertEqual(self.p['phases'][:8], [x['name'] for x in self.a['phases']])

  def test_no_optimizer_semantics_amendment(self):
    self.assertEqual(self.a['D2_compatibility']['decision_recipe_changed'], False)
    self.assertFalse(self.a['D2_compatibility']['Q3_filters_or_reselects_candidates'])
    self.assertEqual(self.p['selection'], self.old['selection'])
    self.assertEqual(self.p['D0_reconstruction'], self.old['D0_reconstruction'])

  def test_inherited_scientific_contracts_unchanged(self):
    for key in self.p['inheritance']['equal_keys']:
      self.assertEqual(self.p[key], self.old[key], key)

  def test_exact_source_pins(self):
    self.assertEqual(self.p['source_sha256'], self.old['source_sha256'])
    for name, expected in self.p['source_sha256'].items():
      self.assertEqual(digest((ROOT / 'openpilot/tools/cyber_autotune' / name).read_bytes()), expected)

  def test_public_input_pins(self):
    self.assertEqual(self.p['public_inputs'], self.old['public_inputs'])
    for name, expected in self.p['public_inputs'].items():
      self.assertEqual(digest((PUBLIC / name).read_bytes()), expected['raw_sha256'])

  def test_three_arms_and_32_ordered_jobs(self):
    self.assertEqual(self.p['jobs'], self.old['jobs'])
    self.assertEqual(len(self.p['jobs']), 32)
    self.assertEqual(len({(x['candidate_id'], x['fold']) for x in self.p['jobs']}), 32)
    self.assertEqual(self.p['policy_arms'], self.old['policy_arms'])

  def test_frozen_acceptance(self):
    self.assertEqual(self.p['acceptance'], self.old['acceptance'])
    self.assertEqual(self.p['acceptance']['clause_count'], 32)
    self.assertEqual(self.p['acceptance']['epsilon'], 0)

  def test_22_domains_and_17_requirements(self):
    self.assertEqual(self.p['validation_domains'], self.old['validation_domains'])
    self.assertEqual(len(self.p['validation_domains']), 22)
    self.assertEqual(len(self.p['requirements_traceability']['ids']), 17)

  def test_horizons_recursion_and_bothfold(self):
    self.assertEqual(self.p['evaluation'], self.old['evaluation'])
    self.assertEqual(self.p['causal_state'], self.old['causal_state'])
    self.assertEqual(self.p['acceptance']['folds'], ['FOLD_A', 'FOLD_B'])

  def test_future_authority_not_granted(self):
    self.assertFalse(self.p['execution_authorized'])
    self.assertFalse(self.a['future_E2_granted'])
    self.assertIn('FRESH_EXPLICIT_E2_V2_GRANT', self.p['execution_prerequisites'])
    self.assertIn('V2_ADDITIVE_CALLER_SOURCE_HASHES_AND_TWO_FINAL_BYTE_APPROVALS', self.p['execution_prerequisites'])

  def test_privacy_unchanged_and_telemetry_private(self):
    self.assertEqual(self.p['publication'], self.old['publication'])
    self.assertTrue(self.a['privacy']['qualification_row_telemetry_private'])
    raw = canonical(self.a) + canonical(self.p)
    self.assertNotRegex(raw, rb'/(?:home|mnt)/[^/\s]+/')
    self.assertNotRegex(raw, rb'[A-Za-z]:[/\\]')
    for fragment in (b'GPS_VALUE', b'PRIVATE_THRESHOLD_VALUE'):
      self.assertNotIn(fragment, raw)

  def test_all_actual_private_counters_zero(self):
    self.assertTrue(self.a['actual_operation_counters'])
    self.assertTrue(all(v == 0 for v in self.a['actual_operation_counters'].values()))
    self.assertEqual(self.p['current_scope'], 'CONTRACT_DESIGN_AND_SYNTHETIC_VALIDATION_ONLY')

  def test_resource_arithmetic(self):
    r = self.p['resource_review']
    n, p, jobs = 336941, 93, 32
    self.assertEqual(r['qualification_matrix_workspace_bytes'], 8 * n * p * 8)
    self.assertEqual(r['comparison_vector_workspace_bytes'], 32 * n)
    self.assertEqual(r['Q3_selected_rows_upper_bound_per_repeat'], jobs * n)
    self.assertLess(r['analytical_peak_including_runtime_reserve_bytes'], self.p['resources']['address_space_bytes'])
    self.assertEqual(self.p['resources']['cpu_seconds_per_repeat'], self.old['resources']['cpu_seconds_per_repeat'])
    self.assertEqual(self.p['resources']['wall_seconds_per_repeat'], self.old['resources']['wall_seconds_per_repeat'])

  def test_qualification_call_budget(self):
    r = self.p['resource_review']
    self.assertEqual((r['Q1_calls_upper_bound_per_repeat'], r['Q3_calls_upper_bound_per_repeat']), (32, 32))
    self.assertEqual(r['Q2_private_calls_default'], 0)
    self.assertFalse(r['capacity_certified_by_private_measurement'])
    self.assertTrue(r['future_capacity_and_caller_liveness_proof_required'])

  def test_repeat_and_resume_unchanged(self):
    self.assertEqual(self.p['repeats'], self.old['repeats'])
    self.assertEqual(self.p['qualification_repeat_scope'], 'INDEPENDENT_Q1_Q3_ALL32_PER_FRESH_REPEAT')

  def test_no_executor_implementation(self):
    source = inspect.getsource(__import__(__name__, fromlist=['']))
    calls = {ast.unparse(node.func) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    self.assertTrue(calls.isdisjoint({'run_private', 'np.load', 'np.save', 'rglob'}))
    self.assertEqual(self.a['executor_modified'], False)

  def test_preserved_safety_states(self):
    self.assertEqual(self.p['preserved'], self.old['preserved'])
    self.assertEqual(self.p['preserved']['holdout'], 'CLOSED')
    self.assertEqual(self.p['preserved']['vehicle_authority'], 'NONE')
    self.assertIsNone(self.p['preserved']['selected_policy'])
    self.assertIsNone(self.p['preserved']['selected_candidate'])

  def test_fail_closed_without_fallback(self):
    self.assertFalse(self.a['qualifications']['Q3']['reselection_allowed'])
    self.assertFalse(self.a['qualifications']['Q1']['rebatching_retry_allowed'])
    self.assertIn(Q3_FAILURE, self.p['failure_states'])
    bad = np.array([1.0])
    self.assertFalse(exact(bad, np.nextafter(bad, np.inf)))


if __name__ == '__main__':
  unittest.main()
