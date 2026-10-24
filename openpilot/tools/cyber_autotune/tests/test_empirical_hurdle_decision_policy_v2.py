"""Synthetic interpretation of a declarative design; no actual threshold executor."""

import copy
import importlib
import importlib.util
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

MODULE = 'openpilot.tools.cyber_autotune.empirical_hurdle_decision_policy_v2'


class TestHurdleDecisionPolicyV2(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'V2 public-only design builder missing')
    self.d = importlib.import_module(MODULE)
    self.bundle = self.d.build()

  def row(self, label):
    return self.bundle[self.d.filename(label)]

  def test_design_only_readiness(self):
    r = self.row('readiness')
    self.assertEqual(r['status'], 'HURDLE_STAGE1_DECISION_POLICY_V2_DESIGN_FROZEN')
    self.assertEqual(r['actual_v2_threshold'], 'NOT_COMPUTED')
    self.assertEqual(r['private_access'], 0)
    self.assertEqual(len(self.bundle), 10)

  def test_four_constraints_and_order(self):
    self.assertEqual(
      self.row('feasibility')['clauses'],
      [
        ['MOVE_RMSE', '<=', 'HOLD_MOVE_RMSE'],
        ['MOVE_MAE', '<=', 'HOLD_MOVE_MAE'],
        ['MOVE_P95', '<=', 'HOLD_MOVE_P95'],
        ['ALL_RMSE', '<', 'HOLD_ALL_RMSE'],
      ],
    )
    self.assertEqual(
      self.row('objective')['maximize_keys'],
      [
        'ALL_PROJECTED_EXACT_HIT_COUNT',
        'NEGATIVE_STATIC_PROJECTED_FALSE_MOVE_COUNT',
        'ALL_WITHIN_ONE_TICK_COUNT',
        'threshold',
      ],
    )

  def test_resealed_policy_mutation_rejected(self):
    b = copy.deepcopy(self.bundle)
    name = self.d.filename('objective')
    b[name]['maximize_keys'] = ['BALANCED_ACCURACY']
    b[name] = p.seal({k: v for k, v in b[name].items() if k != 'receipt_sha256'})
    with self.assertRaisesRegex(ValueError, 'HURDLE_STAGE1_DECISION_POLICY_V2_DESIGN_CONFLICT'):
      self.d.validate(b)

  def reject(self, label, key, value):
    b = copy.deepcopy(self.bundle)
    name = self.d.filename(label)
    b[name][key] = value
    b[name] = p.seal({k: v for k, v in b[name].items() if k != 'receipt_sha256'})
    with self.assertRaisesRegex(ValueError, 'DESIGN_CONFLICT'):
      self.d.validate(b)

  def fixture(self, **updates):
    row = {
      'MOVE_RMSE': 1.0,
      'MOVE_MAE': 1.0,
      'MOVE_P95': 1.0,
      'ALL_RMSE': 0.9,
      'HOLD_MOVE_RMSE': 1.0,
      'HOLD_MOVE_MAE': 1.0,
      'HOLD_MOVE_P95': 1.0,
      'HOLD_ALL_RMSE': 1.0,
      'ALL_PROJECTED_EXACT_HIT_COUNT': 10,
      'STATIC_PROJECTED_FALSE_MOVE_COUNT': 2,
      'ALL_WITHIN_ONE_TICK_COUNT': 15,
      'threshold': 0.2,
    }
    row.update(updates)
    return row

  def select_synthetic(self, rows, *, population='TRAIN', provenance='SYNTHETIC', **extra):
    # Test-only contract interpreter: not imported by the builder or any executor.
    import math
    import operator

    if population != self.row('policy')['threshold_population'] or provenance != 'SYNTHETIC' or extra:
      raise ValueError('SYNTHETIC_TRAIN_ONLY_NO_EXTERNAL_EVIDENCE')
    feasible = []
    for row in rows:
      ops = {'<': operator.lt, '<=': operator.le}
      if not all(math.isfinite(row[k]) and row[k] >= 0 for a, _, b in self.row('feasibility')['clauses'] for k in (a, b)):
        raise ValueError('INVALID_METRIC')
      if all(ops[op](row[a], row[b]) for a, op, b in self.row('feasibility')['clauses']):
        values = {**row, 'NEGATIVE_STATIC_PROJECTED_FALSE_MOVE_COUNT': -row['STATIC_PROJECTED_FALSE_MOVE_COUNT']}
        feasible.append((tuple(values[k] for k in self.row('objective')['maximize_keys']), row))
    return max(feasible, key=lambda x: x[0])[1] if feasible else self.row('feasibility')['empty_state']

  def test_primary_projected_hit_count(self):
    a, b = self.fixture(ALL_PROJECTED_EXACT_HIT_COUNT=11, threshold=0.1), self.fixture(threshold=0.9)
    self.assertIs(self.select_synthetic([b, a]), a)

  def test_projected_false_move_tiebreak(self):
    a, b = self.fixture(STATIC_PROJECTED_FALSE_MOVE_COUNT=1), self.fixture(threshold=0.9)
    self.assertIs(self.select_synthetic([b, a]), a)

  def test_within_one_tiebreak(self):
    a, b = self.fixture(ALL_WITHIN_ONE_TICK_COUNT=16), self.fixture(threshold=0.9)
    self.assertIs(self.select_synthetic([b, a]), a)

  def test_higher_threshold_final_tiebreak(self):
    a, b = self.fixture(threshold=0.3), self.fixture(threshold=0.8)
    self.assertIs(self.select_synthetic([a, b]), b)

  def test_empty_feasible_set_no_fallback(self):
    r = self.select_synthetic([self.fixture(ALL_RMSE=1.0), self.fixture(MOVE_MAE=2.0)])
    self.assertEqual(r, 'STAGE1_DECISION_POLICY_V2_NO_FEASIBLE_THRESHOLD')
    self.assertEqual(self.row('feasibility')['fallback'], 'NONE')

  def test_move_constraints_individually_reject(self):
    for key in ('MOVE_RMSE', 'MOVE_MAE', 'MOVE_P95'):
      with self.subTest(key=key):
        self.assertIsInstance(self.select_synthetic([self.fixture(**{key: 1.01})]), str)

  def test_all_rmse_equality_and_regression_reject(self):
    for v in (1.0, 1.1):
      self.assertIsInstance(self.select_synthetic([self.fixture(ALL_RMSE=v)]), str)

  def test_no_epsilon_at_binary64_boundary(self):
    import math

    self.assertIsInstance(self.select_synthetic([self.fixture(MOVE_RMSE=math.nextafter(1.0, math.inf))]), str)
    self.assertIsInstance(self.select_synthetic([self.fixture(ALL_RMSE=math.nextafter(1.0, 0.0))]), dict)

  def test_nonfinite_negative_metrics_reject(self):
    for v in (float('nan'), float('inf'), -1.0):
      with self.assertRaisesRegex(ValueError, 'INVALID_METRIC'):
        self.select_synthetic([self.fixture(MOVE_P95=v)])

  def test_no_extra_feasibility_or_balanced_accuracy_authority(self):
    self.assertEqual(self.row('policy')['balanced_accuracy'], 'REPORT_ONLY')
    self.reject('feasibility', 'clauses', self.row('feasibility')['clauses'] + [['ALL_MAE', '<=', 'HOLD_ALL_MAE']])
    self.reject('objective', 'maximize_keys', ['BALANCED_ACCURACY'])

  def test_exact_candidate_set_and_strict_equality(self):
    t = self.row('candidates')
    probs = [0.0, 0.2, 0.2, 1.0]
    self.assertEqual(sorted(set(t['boundary_candidates']) | set(probs)), [0.0, 0.2, 1.0])
    self.assertEqual(t['move_operator'], '>')
    self.assertEqual(t['static_operator'], '<=')
    self.assertFalse(0.2 > 0.2)
    self.assertFalse(1.0 > 1.0)
    for key, value in [('move_operator', '>='), ('default_threshold', 0.5), ('midpoints', True), ('epsilon', 1e-8)]:
      self.reject('candidates', key, value)

  def integrate_synthetic(self, current, probability, conditional_delta, threshold):
    import numpy as np

    policy = self.row('policy')
    gate = eval(policy['gate_expression'], {'__builtins__': {}}, {'p_move': probability, 'threshold': threshold})
    if not gate:
      return policy['static_delta'], current
    tick = eval(policy['move_projection'], {'__builtins__': {}, 'np': np}, {'current_tick': current, 'stage2_delta': conditional_delta})
    if not np.isfinite(tick) or tick < -32768 or tick > 32767:
      raise ValueError('SIGNED16_INTEGER_FAIL_CLOSED_NO_CLIPPING')
    return conditional_delta, int(tick)

  def test_static_branch_exact_hold(self):
    self.assertEqual(self.integrate_synthetic(11, 0.2, 1000.0, 0.2), (0.0, 11))

  def test_move_gate_can_project_hold(self):
    self.assertEqual(self.integrate_synthetic(10, 0.8, 0.4, 0.2), (0.4, 10))
    self.assertEqual(self.integrate_synthetic(10, 0.8, 0.6, 0.2), (0.6, 11))

  def test_direct_half_even_parity_both_directions(self):
    for current, delta, want in [(10, 0.5, 10), (11, 0.5, 12), (10, -0.5, 10), (11, -0.5, 10)]:
      self.assertEqual(self.integrate_synthetic(current, 0.8, delta, 0.2)[1], want)

  def test_projected_exactness_not_gate_accuracy_or_continuous_exactness(self):
    import numpy as np

    current = np.array([10, 10, 10])
    target = np.array([10, 11, 10])
    projected = np.array([10, 11, 11])
    delta = target - current
    result = eval(self.row('objective')['exact_hit_count'], {'__builtins__': {}, 'np': np}, locals())
    self.assertEqual(result, 2)
    self.assertNotEqual(result, int(np.count_nonzero(delta != 0)))  # All-MOVE gate accuracy is one, projected exact hits two.
    self.reject('objective', 'exact_hit_count', 'np.count_nonzero(predicted_gate == true_move)')
    self.reject('objective', 'exact_hit_count', 'np.count_nonzero(integrated_delta == delta)')
    self.reject('objective', 'exact_hit_count', 'np.count_nonzero(np.rint(p_move) == true_move)')

  def test_false_move_counts_projection_not_gate(self):
    import numpy as np

    current = np.array([10, 10, 10])
    projected = np.array([10, 11, 11])
    delta = np.array([0, 0, 1])
    result = eval(self.row('tiebreak')['static_false_move_count'], {'__builtins__': {}, 'np': np}, locals())
    self.assertEqual(result, 1)  # First two gates may both be MOVE; only one STATIC tick actually moves.
    self.reject('tiebreak', 'static_false_move_count', 'np.count_nonzero((delta == 0) & predicted_gate)')

  def test_leakage_and_counterfactual_inputs_rejected(self):
    for population in ('DEVELOPMENT', 'HOLDOUT', 'POOLED_A_B', 'ROLLOUT_DEVELOPMENT'):
      with self.assertRaisesRegex(ValueError, 'TRAIN_ONLY'):
        self.select_synthetic([self.fixture()], population=population)
    for key in ('development_metrics', 'attribution_candidate_results', 'v1_development_exact_hit', 'v1_fold_failure_count'):
      with self.assertRaisesRegex(ValueError, 'TRAIN_ONLY'):
        self.select_synthetic([self.fixture()], **{key: []})
    with self.assertRaisesRegex(ValueError, 'TRAIN_ONLY'):
      self.select_synthetic([self.fixture()], provenance='PRIVATE')

  def test_unchanged_components_resealed_drift_rejected(self):
    for key in ('stage1_model', 'stage2_model', 'features', 'route_folds', 'rollout', 'acceptance_gate', 'selection_rule'):
      self.assertEqual(self.row('readiness')[key], 'UNCHANGED')
      self.reject('readiness', key, 'CHANGED')
    self.assertEqual(self.row('readiness')['structures'], '16_UNCHANGED')
    for key in self.row('unchanged')['bindings']:
      changed = copy.deepcopy(self.row('unchanged')['bindings'])
      changed[key] = '0' * 64
      self.reject('unchanged', 'bindings', changed)

  def test_exact_evidence_and_missing_input_rejected(self):
    r = self.row('evidence')
    self.assertEqual(r['baseline'], '13e1ac7c8b892d3bd61b5e2eab9deba8f4dc08d6')
    self.assertEqual(r['attribution_manifest_sha256'], '07345517d3bca95e90962e0566a58e2b756a8aa6f5c658b8b312f02d4961f77d')
    inputs = self.d.load_inputs()
    inputs.pop(next(iter(inputs)))
    with self.assertRaisesRegex(ValueError, 'DESIGN_CONFLICT'):
      self.d.check_inputs(inputs)

  def test_input_byte_drift_rejected(self):
    from pathlib import Path
    from unittest.mock import patch

    with patch.object(Path, 'read_bytes', return_value=b'{}'):
      with self.assertRaisesRegex(ValueError, 'DESIGN_CONFLICT'):
        self.d.load_inputs()

  def test_no_actual_executor_api(self):
    for symbol in ('fit', 'predict', 'select_threshold', 'rollout', 'load_private', 'select_candidate'):
      self.assertFalse(hasattr(self.d, symbol))

  def test_design_generation_under_execution_and_file_firewall(self):
    import builtins
    import io
    from contextlib import ExitStack
    from pathlib import Path
    from unittest.mock import patch
    import numpy as np

    modules = [
      importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_fit_cv_' + name) for name in ('math', 'data', 'execution', 'gates', 'store')
    ]
    allowed = {p.PUBLIC / n for n in self.d.PINS} | {Path(self.d.__file__)}
    original_bytes, original_io, original_open = Path.read_bytes, io.open, builtins.open
    accessed = []

    def guard(path, mode='r'):
      self.assertIn(Path(path), allowed)
      self.assertNotIn('w', mode)
      self.assertNotIn('a', mode)
      self.assertNotIn('+', mode)

    def read_public(path):
      guard(path)
      accessed.append(path)
      return original_bytes(path)

    def guarded_io(path, mode='r', *args, **kwargs):
      guard(path, mode)
      return original_io(path, mode, *args, **kwargs)

    def guarded_open(path, mode='r', *args, **kwargs):
      guard(path, mode)
      return original_open(path, mode, *args, **kwargs)

    def trap(*args, **kwargs):
      raise AssertionError('EXECUTION_FORBIDDEN')

    with ExitStack() as stack:
      stack.enter_context(patch.object(Path, 'read_bytes', read_public))
      stack.enter_context(patch.object(io, 'open', guarded_io))
      stack.enter_context(patch.object(builtins, 'open', guarded_open))
      for name in ('solve', 'lstsq', 'pinv'):
        stack.enter_context(patch.object(np.linalg, name, trap))
      stack.enter_context(patch.object(np, 'load', trap))
      for module in modules:
        for name, value in vars(module).items():
          if callable(value) and (getattr(value, '__module__', None) == module.__name__ or name in ('project', 'transform')):
            stack.enter_context(patch.object(module, name, trap))
      self.d.validate(self.d.build())
    self.assertEqual(set(accessed), allowed)

  def test_future_strategy_unresolved(self):
    r = self.row('future')
    self.assertEqual(r['next_increment'], 'HURDLE_STAGE1_DECISION_POLICY_V2_EXECUTION_POLICY')
    self.assertEqual(r['status'], 'REQUIRES_SEPARATE_AUTHORIZATION')
    self.assertEqual(r['model_strategy'], 'UNRESOLVED')
    self.assertEqual(r['stage2_train_prediction_lineage'], 'UNRESOLVED')
    self.reject('future', 'model_strategy', 'REUSE_V1')

  def test_authority_and_historical_states(self):
    r = self.row('readiness')
    self.assertEqual(r['historical_verdict'], 'HURDLE_NO_ADMISSIBLE_CANDIDATE')
    self.assertEqual(r['historical_selection'], 'MODEL_SELECTION_FAILED_CLOSED')
    self.assertEqual(r['holdout'], 'CLOSED')
    self.assertEqual(r['opening_count'], 0)
    self.assertEqual(r['vehicle_authority'], 'NONE')
    self.assertTrue(all(v == 'NOT_RUN' for v in r['execution_states'].values()))
    self.assertTrue(all(v == 0 for v in r['openings'].values()))
    self.assertEqual(r['stage2_residual_risk'], 'STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS')

  def test_publication_repeatable_and_immutable(self):
    import json
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp)
      self.assertEqual(self.d.publish(root), self.d.publish(root))
      for name, row in self.bundle.items():
        self.assertEqual(json.loads((root / name).read_bytes()), row)
      (root / self.d.filename('policy')).write_text('{}')
      with self.assertRaisesRegex(ValueError, 'IMMUTABLE'):
        self.d.publish(root)

  def test_projection_range_failure_no_clipping(self):
    for current, delta in ((32767, 1.0), (-32768, -1.0), (0, float('inf'))):
      with self.assertRaisesRegex(ValueError, 'SIGNED16'):
        self.integrate_synthetic(current, 0.8, delta, 0.2)
    self.assertEqual(self.row('policy')['projection_range'], 'SIGNED16_INTEGER_FAIL_CLOSED_NO_CLIPPING')

  def test_within_one_widened_tick_subtraction(self):
    import numpy as np

    projected = np.array([-32768, 11, 12], dtype=np.int16).astype(np.int64)
    target = np.array([32767, 10, 10], dtype=np.int16).astype(np.int64)
    result = eval(self.row('tiebreak')['within_one_tick_count'], {'__builtins__': {}, 'np': np}, locals())
    self.assertEqual(result, 1)
    self.assertEqual(self.row('tiebreak')['integer_arithmetic'], 'WIDEN_TICKS_BEFORE_SUBTRACTION_NO_SIGNED16_OVERFLOW')

  def test_resealed_input_mutation_each_unchanged_contract(self):
    inputs = self.d.load_inputs()
    for label in self.row('unchanged')['bindings']:
      with self.subTest(label=label):
        changed = copy.deepcopy(inputs)
        name = self.d.oldname(label)
        changed[name] = p.seal({**{k: v for k, v in changed[name].items() if k != 'receipt_sha256'}, 'override': True})
        with self.assertRaisesRegex(ValueError, 'DESIGN_CONFLICT'):
          self.d.check_inputs(changed)

  def test_leakage_contract_mutations(self):
    self.reject('policy', 'threshold_population', 'DEVELOPMENT')
    self.reject('policy', 'allowed_selection_inputs', ['V1_DEVELOPMENT_METRICS'])
    self.reject('policy', 'forbidden_selection_inputs', [])
    self.reject('policy', 'branch', 'TRUE_MOVE_LABEL')
    self.reject('policy', 'actual_execution_authorized', True)

  def test_no_actual_value_or_array_in_bundle(self):
    import json

    text = json.dumps(self.bundle, allow_nan=False)
    for forbidden in ('selected_threshold_value', 'private_store_path', 'normalizer_mean', 'normalizer_std', 'p_move_array'):
      self.assertNotIn('"' + forbidden + '"', text)
    self.assertEqual(self.row('policy')['actual_threshold_visibility'], 'PRIVATE_NOT_COMPUTED_THIS_INCREMENT')
