"""Synthetic-only interpreters of the additive execution policy."""

import importlib
import importlib.util
import unittest


class TestHurdleV2ExecutionPolicy(unittest.TestCase):
  def setUp(self):
    module = 'openpilot.tools.cyber_autotune.empirical_hurdle_v2_execution_policy'
    self.assertIsNotNone(importlib.util.find_spec(module), 'execution policy builder missing')
    self.e = importlib.import_module(module)
    self.bundle = self.e.build()

  def row(self, label):
    return self.bundle[self.e.filename(label)]

  def test_public_only_readiness(self):
    r = self.row('readiness')
    self.assertEqual(r['status'], self.e.READY)
    self.assertEqual(r['private_access'], 0)
    self.assertEqual(r['actual_execution'], 'NOT_RUN')
    self.assertEqual(len(self.bundle), 12)

  def test_reuse_no_refit(self):
    self.assertEqual(self.row('reuse')['model_strategy'], 'REUSE_BYTE_IDENTICAL_V1_FITTED_MODELS')
    self.assertEqual(self.row('reuse')['refit'], dict.fromkeys(('stage1', 'stage2', 'normalizer'), 'FORBIDDEN'))

  def test_stage2_all_train(self):
    self.assertEqual(self.row('stage2')['population'], 'ALL_CANDIDATE_SPECIFIC_TRAIN_ANCHORS')

  def reject(self, label, field, value):
    import copy
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    b = copy.deepcopy(self.bundle)
    n = self.e.filename(label)
    b[n][field] = value
    b[n] = p.seal({k: v for k, v in b[n].items() if k != 'receipt_sha256'})
    with self.assertRaisesRegex(ValueError, '_CONFLICT'):
      self.e.validate(b)

  def model_fixture(self):
    return {k: str(i) * 64 for i, k in enumerate(self.row('reuse')['model_identity_fields'])}

  def check_model(self, expected, actual):
    if set(actual) != set(expected) or any(actual[k] != expected[k] for k in self.row('reuse')['model_identity_fields']):
      raise ValueError(self.row('reuse')['mismatch'])

  def test_each_model_identity_field_rejects(self):
    a = self.model_fixture()
    self.check_model(a, dict(a))
    for k in a:
      with self.subTest(field=k), self.assertRaisesRegex(ValueError, 'V2_V1_MODEL_IDENTITY_CONFLICT'):
        self.check_model(a, {**a, k: 'f' * 64})

  def test_refit_and_replacement_mutations(self):
    for k in ('stage1', 'stage2', 'normalizer'):
      self.reject('reuse', 'refit', {**self.row('reuse')['refit'], k: 'ALLOWED'})
    self.reject('reuse', 'model_strategy', 'CLEAN_32_JOB_REFIT_WITH_FROZEN_V1_ALGORITHMS')
    self.reject('reuse', 'model_replacement', True)

  def test_anchor_identity_and_order(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    def verify(a, b):
      if p.sha(p.canonical(a)) != p.sha(p.canonical(b)):
        raise ValueError('ANCHOR_CONFLICT')

    verify([1, 2, 3], [1, 2, 3])
    for b in ([2, 1, 3], [1, 2], [1, 2, 3, 4]):
      with self.assertRaisesRegex(ValueError, 'ANCHOR_CONFLICT'):
        verify([1, 2, 3], b)
    self.assertIn('REORDER', self.row('train')['no_row_drift'])

  def synthetic_replay(self, x, beta, mean, std):
    import numpy as np

    # Fixture is in-memory; there is no loader or fitting call.
    z = ((x - mean) / std) @ beta
    result = np.empty_like(z)
    pos = z >= 0
    result[pos] = 1 / (1 + np.exp(-z[pos]))
    exp = np.exp(z[~pos])
    result[~pos] = exp / (1 + exp)
    return result

  def test_prediction_only_synthetic_replay_and_saved_identity(self):
    import numpy as np
    from unittest.mock import patch

    with patch.object(np.linalg, 'solve', side_effect=AssertionError('fit')), patch.object(np.linalg, 'lstsq', side_effect=AssertionError('fit')):
      a = self.synthetic_replay(np.array([[-1000.0], [0.0], [1000.0]]), np.array([1.0]), np.array([0.0]), np.array([1.0]))
    np.testing.assert_array_equal(a, [0.0, 0.5, 1.0])
    self.assertEqual(a.tobytes(), a.copy().tobytes())
    changed = a.copy()
    changed[1] = np.nextafter(changed[1], 1.0)
    self.assertNotEqual(a.tobytes(), changed.tobytes())
    self.assertEqual(self.row('train')['mismatch'], 'V2_STAGE1_TRAIN_PREDICTION_IDENTITY_FAILURE')
    self.reject('train', 'canonical', 'SAVED_ARRAY_BLIND_REUSE')

  def test_all_train_stage2_static_row_requires_delta(self):
    import numpy as np

    truth = np.array([0.0, 1.0])
    # Immutable MOVE-normalizer applied to ALL rows; no mean/std estimation.
    x, mean, std, beta = np.array([[2.0], [4.0]]), np.array([1.0]), np.array([1.0]), np.array([1.0])
    branch_delta = ((x - mean) / std) @ beta
    gate = np.array([0.9, 0.2]) > 0.5
    integrated = np.where(gate, branch_delta, 0.0)
    self.assertEqual(integrated[truth == 0].tolist(), [1.0])
    self.reject('stage2', 'population', 'TRUE_MOVE_ONLY')
    self.reject('stage2', 'normalization_recalculation', True)
    self.reject('stage2', 'true_label_branch', True)

  def synthetic_thresholds(self, *, population='TRAIN', **extra):
    import numpy as np

    if population != 'TRAIN' or extra:
      raise ValueError('TRAIN_INPUT_ALLOWLIST')
    # Finite, deterministic fixture, including equal probabilities and STATIC FP.
    current = np.array([0, 1, 2, 3, 4, 5], dtype=np.int64)
    delta = np.array([0, 1, 0, -2, 0, 2], dtype=np.float64)
    probability = np.array([0.1, 0.9, 0.6, 0.8, 0.4, 0.9])
    stage2 = np.array([0.1, 0.8, 1.1, -1.8, 0.2, 1.8])
    target = current + delta.astype(np.int64)
    move = delta != 0

    def metrics(error):
      return (float(np.sqrt(np.mean(error * error))), float(np.mean(np.abs(error))), float(np.percentile(np.abs(error), 95, method='linear')))

    hold_all, hold_move = metrics(-delta), metrics(-delta[move])
    out = []
    candidates = sorted(set(self.row('train')['threshold_contracts']['candidates']['boundary_candidates']) | set(probability))
    for threshold in candidates:
      gate = probability > threshold
      integrated = np.where(gate, stage2, 0.0)
      projected = current.copy()
      projected[gate] = np.rint(current[gate].astype(np.float64) + stage2[gate]).astype(np.int64)
      all_m, move_m = metrics(integrated - delta), metrics((integrated - delta)[move])
      out.append(
        {
          'threshold': float(threshold),
          'ALL_RMSE': all_m[0],
          'HOLD_ALL_RMSE': hold_all[0],
          'MOVE_RMSE': move_m[0],
          'MOVE_MAE': move_m[1],
          'MOVE_P95': move_m[2],
          'HOLD_MOVE_RMSE': hold_move[0],
          'HOLD_MOVE_MAE': hold_move[1],
          'HOLD_MOVE_P95': hold_move[2],
          'ALL_PROJECTED_EXACT_HIT_COUNT': int(np.count_nonzero(projected == target)),
          'STATIC_PROJECTED_FALSE_MOVE_COUNT': int(np.count_nonzero(~move & (projected != current))),
          'ALL_WITHIN_ONE_TICK_COUNT': int(np.count_nonzero(np.abs(projected - target) <= 1)),
        }
      )
    return out

  def select_fixture(self, rows):
    # Use the already tested V2 design interpreter, with this bound contract.
    from openpilot.tools.cyber_autotune.tests.test_empirical_hurdle_decision_policy_v2 import TestHurdleDecisionPolicyV2

    t = TestHurdleDecisionPolicyV2()
    t.setUp()
    return t.select_synthetic(rows)

  def test_synthetic_threshold_end_to_end(self):
    rows = self.synthetic_thresholds()
    selected = self.select_fixture(rows)
    self.assertEqual(selected['ALL_PROJECTED_EXACT_HIT_COUNT'], 6)
    self.assertEqual(selected['STATIC_PROJECTED_FALSE_MOVE_COUNT'], 0)
    self.assertEqual(selected['threshold'], 0.6)
    # all-STATIC is not feasible because strict ALL RMSE improvement fails.
    self.assertIsInstance(self.select_fixture([rows[-1]]), str)

  def test_all_objective_ties_and_move_constraints(self):
    rows = self.synthetic_thresholds()
    good = self.select_fixture(rows)
    for field in ('MOVE_RMSE', 'MOVE_MAE', 'MOVE_P95'):
      with self.subTest(field=field):
        self.assertIsInstance(self.select_fixture([{**good, field: good['HOLD_' + field] + 1}]), str)
    for key, better in [('ALL_PROJECTED_EXACT_HIT_COUNT', 7), ('STATIC_PROJECTED_FALSE_MOVE_COUNT', -1), ('ALL_WITHIN_ONE_TICK_COUNT', 7), ('threshold', 0.7)]:
      # For the false-move tie use nonnegative counts.
      a = {**good, 'STATIC_PROJECTED_FALSE_MOVE_COUNT': 2}
      b = {**a, key: 1 if key == 'STATIC_PROJECTED_FALSE_MOVE_COUNT' else better}
      self.assertIs(self.select_fixture([a, b]), b)

  def test_no_approximate_p95_or_reduction_reassociation(self):
    import numpy as np

    e = np.array([0.0, 1.0, 2.0, 19.0])
    self.assertEqual(float(np.percentile(e, 95, method='linear')), 16.449999999999996)
    self.assertIn('CANONICAL_REDUCTION_REQUIRED', self.row('train')['evaluator']['reduction'])
    self.reject('train', 'evaluator', {**self.row('train')['evaluator'], 'p95': 'APPROXIMATE_HISTOGRAM'})

  def test_no_optimized_executor_claim(self):
    import ast
    from pathlib import Path

    tree = ast.parse(Path(self.e.__file__).read_text())
    functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    self.assertEqual(functions, {'filename', 'load_inputs', 'sealed', 'build', 'validate', 'publish', 'main'})
    self.assertIn('ONE_THRESHOLD_AT_A_TIME', self.row('train')['evaluator']['canonical_reference'])

  def test_leakage_inputs_rejected(self):
    for name in ('DEVELOPMENT', 'HOLDOUT', 'V1_DEVELOPMENT_METRICS', 'V1_ATTRIBUTION_CANDIDATE_RESULTS', 'ROLLOUT_RESULT', 'V1_THRESHOLD_VALUE'):
      with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'TRAIN_INPUT_ALLOWLIST'):
        self.synthetic_thresholds(**{name: []})
    for population in ('DEVELOPMENT', 'HOLDOUT', 'POOLED_A_B'):
      with self.assertRaises(ValueError):
        self.synthetic_thresholds(population=population)

  def test_development_requires_finalization(self):
    def open_dev(receipt):
      if receipt != 'IMMUTABLY_PUBLISHED_TRAIN_THRESHOLD_FINALIZATION':
        raise ValueError('NO_DEV_BEFORE_THRESHOLD')

    with self.assertRaises(ValueError):
      open_dev(None)
    open_dev('IMMUTABLY_PUBLISHED_TRAIN_THRESHOLD_FINALIZATION')
    self.assertIn('BEFORE_ANY_DEV_OPEN', self.row('development')['prerequisite'])
    self.reject('development', 'prerequisite', 'AFTER_DEV_INSPECTION')

  def test_comparison_candidate_fold_anchor_identity(self):
    identity = self.row('comparison')['identity']
    a = dict(zip(identity, ('HRI_D00_L01', 'FOLD_A', 'a' * 64), strict=True))

    def compare(b):
      if any(a[k] != b[k] for k in identity):
        raise ValueError(self.row('comparison')['mismatch'])

    compare(dict(a))
    for key in identity:
      with self.assertRaisesRegex(ValueError, 'COMPARISON_IDENTITY_CONFLICT'):
        compare({**a, key: 'different'})

  def test_comparison_report_only_no_numerical_threshold(self):
    self.assertEqual(self.row('comparison')['authority'], 'REPORT_ONLY')
    self.assertFalse(self.row('comparison')['actual_threshold_publication'])
    self.reject('comparison', 'v1_metrics_selection_authority', True)
    self.reject('comparison', 'actual_threshold_publication', True)
    self.assertIn('AFTER_V2_FINALIZATION', self.row('comparison')['v1_threshold_compartment'])

  def test_unchanged_components_and_32_jobs(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_decision_policy_v2 as d

    original = d.build()[d.filename('unchanged')]
    r = self.row('reuse')
    for k in ('candidates', 'folds', 'acceptance_clauses', 'selection_rule'):
      self.assertEqual(r[k], original[k])
    self.assertEqual(len(r['candidates']), 16)
    self.assertEqual(len(r['acceptance_clauses']), 32)
    self.reject('reuse', 'expected_jobs', 31)
    self.reject('reuse', 'acceptance_clauses', r['acceptance_clauses'][:-1])

  def test_rollout_projected_state_and_fixed_gate(self):
    r = self.row('rollout')
    self.assertEqual(r['horizons'], [25, 50, 100, 200])
    self.assertIn('PROJECTED_INTEGER_TICK', r['state'])
    self.assertIn('SCORING_ONLY_NOT_FEATURE_OR_BRANCH', r['truth'])
    self.reject('rollout', 'state', 'FUTURE_MEASURED_TICK')
    self.reject('rollout', 'horizons', [25, 50])

  def synthetic_storage_guard(self, path, *, symlink=False, exists=False, duplicate=None):
    from pathlib import PureWindowsPath

    r = self.row('storage')
    q = PureWindowsPath(path)
    if r['volume'] != 'D_ONLY' or q.drive.upper() != 'D:' or not q.is_absolute() or '..' in q.parts or symlink or exists:
      raise ValueError('STORAGE_PATH_CONFLICT')
    if duplicate in r['reference_only']:
      raise ValueError('DUPLICATE_V1_PAYLOAD')
    return q

  def test_storage_d_only_traversal_symlink_overwrite(self):
    self.synthetic_storage_guard('D:/synthetic-v2/run1')
    for path, kw in [
      ('C:/synthetic-v2/run1', {}),
      ('D:relative', {}),
      ('D:/synthetic-v2/../source', {}),
      ('D:/synthetic-v2/run1', {'symlink': True}),
      ('D:/synthetic-v2/run1', {'exists': True}),
    ]:
      with self.subTest(path=path, kw=kw), self.assertRaises(ValueError):
        self.synthetic_storage_guard(path, **kw)

  def test_storage_no_model_truth_duplication(self):
    for name in self.row('storage')['reference_only']:
      with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'DUPLICATE_V1_PAYLOAD'):
        self.synthetic_storage_guard('D:/synthetic-v2/run1', duplicate=name)

  def compressed_fixture(self, values):
    import gzip
    import io
    import numpy as np

    buf = io.BytesIO()
    np.save(buf, np.array(values, dtype=np.float64, order='C'), allow_pickle=False)
    raw = buf.getvalue()
    out = io.BytesIO()
    c = self.row('storage')['compression']
    with gzip.GzipFile(fileobj=out, mode='wb', filename=c['filename'], mtime=c['mtime'], compresslevel=c['level']) as handle:
      handle.write(raw)
    return raw, out.getvalue()

  def test_deterministic_lossless_gzip(self):
    import gzip

    a = self.compressed_fixture([1.0, 2.0, 3.0])
    b = self.compressed_fixture([1.0, 2.0, 3.0])
    self.assertEqual(a, b)
    self.assertEqual(gzip.decompress(a[1]), a[0])
    self.assertEqual(a[1][3] & 8, 0)  # No embedded filename flag.
    self.assertEqual(a[1][4:8], b'\0' * 4)

  def compare_runs(self, first, second):
    if first != second:
      raise ValueError(self.row('repeatability')['failure'])

  def test_independent_synthetic_runs_exact_and_byte_mutation(self):
    a = (self.synthetic_thresholds(), self.compressed_fixture([1.0, 2.0]))
    b = (self.synthetic_thresholds(), self.compressed_fixture([1.0, 2.0]))
    self.compare_runs(a, b)
    with self.assertRaisesRegex(ValueError, 'REPEATABILITY_FAILURE'):
      self.compare_runs(a[1][1], a[1][1][:-1] + bytes([a[1][1][-1] ^ 1]))

  def test_run2_cleanup_requires_all_durable_equality_evidence(self):
    required = self.row('storage')['run2_cleanup_requires']

    def cleanup_allowed(checks):
      return set(checks) == set(required) and all(checks.values())

    self.assertTrue(cleanup_allowed(dict.fromkeys(required, True)))
    for k in required:
      checks = dict.fromkeys(required, True)
      checks[k] = False
      self.assertFalse(cleanup_allowed(checks))
      del checks[k]
      self.assertFalse(cleanup_allowed(checks))
    self.assertFalse(self.row('storage')['deletion_this_increment'])

  def test_resume_saved_only_with_all_compute_trapped(self):
    from contextlib import ExitStack
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    payload = b'synthetic saved V2 evidence'
    saved = p.seal({'payload_sha': p.sha(payload), 'readiness': 'SYNTHETIC_COMPLETE'})
    modules = [
      importlib.import_module('openpilot.tools.cyber_autotune.' + n)
      for n in (
        'empirical_hurdle_fit_cv_math',
        'empirical_hurdle_fit_cv_data',
        'empirical_hurdle_fit_cv_store',
        'empirical_hurdle_fit_cv_execution',
        'empirical_hurdle_fit_cv_gates',
      )
    ]

    def resume(receipt, data):
      p.verify(receipt)
      if p.sha(data) != receipt['payload_sha']:
        raise ValueError('SAVED_STORE_CORRUPTION')
      return receipt

    # Active traps replace existing numerical/source functions, not disconnected mocks.
    # This is still a synthetic saved-receipt interpreter, not a future V2 executor.
    with ExitStack() as stack:
      active = []
      for module in modules:
        for name, value in vars(module).items():
          if callable(value) and not isinstance(value, type):
            stack.enter_context(patch.object(module, name, side_effect=AssertionError('RESUME_COMPUTE_TRAP')))
            active.append((module, name))
      self.assertTrue(active)
      self.assertEqual(resume(saved, payload), saved)
      with self.assertRaises(ValueError):
        resume(saved, payload + b'!')
      # Mutation control proves that invoking any patched service is rejected.
      for module, name in active:
        with self.assertRaisesRegex(AssertionError, 'RESUME_COMPUTE_TRAP'):
          getattr(module, name)()
    self.assertEqual(self.row('resume')['compute_calls'], 0)
    self.assertEqual(self.row('resume')['source_open_calls'], 0)

  def test_publication_privacy_allowlist(self):
    forbidden = self.row('storage')['public_forbidden']

    def publish(fields):
      if set(fields) & set(forbidden):
        raise ValueError('PRIVATE_NUMERIC_PUBLICATION')

    publish({'THRESHOLD_RECEIPT_SHA': 'a' * 64, 'FEASIBLE_THRESHOLD_COUNT': 3})
    for k in forbidden:
      with self.assertRaises(ValueError):
        publish({k: 0.123})

  def test_historical_and_authority(self):
    r = self.row('readiness')
    self.assertEqual(r['historical_verdict'], 'HURDLE_NO_ADMISSIBLE_CANDIDATE')
    self.assertEqual(r['historical_selection'], 'MODEL_SELECTION_FAILED_CLOSED')
    self.assertEqual(r['opening_count'], 0)
    self.assertEqual(r['vehicle_authority'], 'NONE')
    self.assertTrue(all(v == 'NOT_RUN' for v in r['execution_states'].values()))
    self.assertEqual(r['stage2_residual_risk'], 'STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS')
    self.assertEqual(r['next_increment_status'], 'REQUIRES_SEPARATE_AUTHORIZATION')

  def test_exact_reference_receipts(self):
    r = self.row('policy')['references']
    self.assertEqual(r['v2_design_policy'], '463ac0c2f34b59b67c1a1d7365c5662d717a49de328cabfd9101f185bff2bf19')
    self.assertEqual(r['v2_design_readiness'], '6963e8a3d0b3ae018a6612e7d07e18143db0f5147d7ccb5b75e90dbc77dc00e8')
    self.assertEqual(r['v2_future_requirements'], '52586eae8858a3cf31f54c74917dbb7df2d7b792a14a4e39567a5f2b057c74f9')

  def test_public_input_sha_drift_rejects(self):
    from pathlib import Path
    from unittest.mock import patch

    original = Path.read_bytes
    target = next(iter(self.e.PINS))

    def read(path):
      raw = original(path)
      return raw + b' ' if path.name == target else raw

    with patch.object(Path, 'read_bytes', read), self.assertRaisesRegex(ValueError, '_CONFLICT'):
      self.e.build()

  def test_policy_generation_private_and_execution_firewall(self):
    import builtins
    import io
    import os
    from contextlib import ExitStack
    from pathlib import Path
    from unittest.mock import patch
    import numpy as np
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    # Imports happen before traps. Trap every callable in historical execution modules.
    modules = [
      importlib.import_module('openpilot.tools.cyber_autotune.' + n)
      for n in (
        'empirical_hurdle_fit_cv_math',
        'empirical_hurdle_fit_cv_data',
        'empirical_hurdle_fit_cv_store',
        'empirical_hurdle_fit_cv_execution',
        'empirical_hurdle_fit_cv_gates',
      )
    ]
    allowed = {str((p.PUBLIC / n).absolute()) for n in self.e.PINS} | {str(Path(self.e.__file__).absolute())}
    original = io.open

    def read_only(file, mode='r', *args, **kwargs):
      if not isinstance(file, (str, bytes, os.PathLike)) or str(Path(file).absolute()) not in allowed or mode not in ('r', 'rb'):
        raise AssertionError('PRIVATE_OR_UNDECLARED_ACCESS')
      return original(file, mode, *args, **kwargs)

    with ExitStack() as stack:
      for module in modules:
        for name, value in vars(module).items():
          if callable(value) and not isinstance(value, type):
            stack.enter_context(patch.object(module, name, side_effect=AssertionError('EXECUTION_TRAP')))
      for name in ('solve', 'lstsq'):
        stack.enter_context(patch.object(np.linalg, name, side_effect=AssertionError('FIT_TRAP')))
      stack.enter_context(patch.object(io, 'open', read_only))
      stack.enter_context(patch.object(builtins, 'open', read_only))
      for name in ('listdir', 'scandir', 'walk'):
        stack.enter_context(patch.object(os, name, side_effect=AssertionError('DISCOVERY_TRAP')))
      result = self.e.build()
    self.assertEqual(result, self.bundle)

  def test_publish_immutable_and_verify_exact(self):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
      root = Path(td)
      self.assertEqual(self.e.publish(root), self.bundle)
      self.assertEqual(self.e.publish(root), self.bundle)
      path = root / self.e.filename('reuse')
      path.write_bytes(b'conflict')
      before = {x.name: x.read_bytes() for x in root.iterdir()}
      with self.assertRaisesRegex(ValueError, 'IMMUTABLE_OUTPUT_CONFLICT'):
        self.e.publish(root)
      self.assertEqual(before, {x.name: x.read_bytes() for x in root.iterdir()})

  def test_all_contract_resealed_mutations_fail_closed(self):
    for label, key, value in (
      ('train', 'threshold_input_allowlist', ['DEVELOPMENT']),
      ('reuse', 'unchanged_components', {}),
      ('comparison', 'authority', 'SELECTION'),
      ('storage', 'volume', 'C_ALLOWED'),
      ('repeatability', 'equality', 'EPSILON'),
      ('resume', 'source_open_calls', 1),
      ('policy', 'actual_execution_authorized', True),
    ):
      with self.subTest(label=label):
        self.reject(label, key, value)


if __name__ == '__main__':
  unittest.main()
