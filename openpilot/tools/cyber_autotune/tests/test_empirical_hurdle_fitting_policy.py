"""Public policy and synthetic contract tests; no actual model executor."""

import builtins
import copy
import importlib
import importlib.util
import json
import math
import operator
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

MODULE = 'openpilot.tools.cyber_autotune.empirical_hurdle_fitting_policy'
OPS = {'<': operator.lt, '<=': operator.le, '>': operator.gt, '>=': operator.ge, '==': operator.eq}


class TestHurdleFittingPolicy(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'public-only fitting policy builder missing')
    self.d = importlib.import_module(MODULE)
    self.bundle = self.d.build()

  def row(self, label):
    return self.bundle[self.d.filename(label)]

  def reject(self, label, key, value):
    bundle = copy.deepcopy(self.bundle)
    row = bundle[self.d.filename(label)]
    row[key] = value
    bundle[self.d.filename(label)] = p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaisesRegex(ValueError, 'HURDLE_FITTING_POLICY_CONTRACT_DRIFT'):
      self.d.validate(bundle)

  def formula(self, label, field, **values):
    # Evaluate only the generated, validated declarative formula against synthetic literals.
    return eval(self.row(label)[field], {'__builtins__': {}, 'np': np}, values)

  def test_ready_is_policy_only(self):
    r = self.row('fitting-policy-readiness')
    self.assertEqual(r['status'], 'HURDLE_FITTING_POLICY_FROZEN')
    self.assertEqual(len(self.bundle), 14)
    self.assertEqual(r['private_arrays_opened'], 0)
    self.assertEqual(r['historical_verdict'], 'S2_RI_NO_ADMISSIBLE_CANDIDATE')
    for label in (
      'model_fitting',
      'move_gate_fitting',
      'conditional_delta_fitting',
      'normalizer_fitting',
      'threshold_selection',
      'cv_scoring',
      'prediction',
      'rollout',
      'model_selection',
    ):
      self.assertEqual(r[label], 'NOT_RUN')

  def test_exact_design_binding(self):
    inputs = self.d.load_inputs()
    self.assertEqual(self.d.BASELINE, 'cce79c2762e4e83f39fa2239f7129253fb5b713b')
    r = inputs['empirical-hurdle-design-readiness-v1.json']
    self.assertEqual(r['receipt_sha256'], '8d08f9c06583983e237cbdf92dc6028865a3d87a9a289aaba00ea895ede9fd2a')
    for key, value in [('family', 'NEW_FAMILY'), ('structural_configurations', 17), ('move_gate_threshold', 0.5), ('steering_rate_dependency', 'RATE')]:
      changed = copy.deepcopy(inputs)
      changed['empirical-hurdle-design-readiness-v1.json'][key] = value
      changed['empirical-hurdle-design-readiness-v1.json'] = p.seal(
        {k: v for k, v in changed['empirical-hurdle-design-readiness-v1.json'].items() if k != 'receipt_sha256'}
      )
      with self.assertRaisesRegex(ValueError, 'DESIGN_BINDING_CONFLICT'):
        self.d.check_inputs(changed)

  def test_missing_design_input_rejected(self):
    inputs = self.d.load_inputs()
    inputs.pop(next(iter(inputs)))
    with self.assertRaisesRegex(ValueError, 'DESIGN_BINDING_CONFLICT'):
      self.d.check_inputs(inputs)

  def test_file_byte_drift_rejected_before_decode(self):
    with patch.object(Path, 'read_bytes', return_value=b'{}'):
      with self.assertRaisesRegex(ValueError, 'DESIGN_BINDING_CONFLICT'):
        self.d.load_inputs()

  def test_exact_tied_candidates_and_parameter_counts(self):
    rows = self.row('candidate-set')['candidates']
    self.assertEqual([r['candidate_id'] for r in rows], [f'HRI_D{d:02d}_L{length:02d}' for d in (0, 5, 10, 20) for length in (1, 5, 15, 45)])
    for r in rows:
      self.assertEqual(r['stage1_context'], r['stage2_context'])
      self.assertEqual(r['total_nominal_parameters'], {1: 10, 5: 26, 15: 66, 45: 186}[r['L']])
      p.verify(r)
      self.assertEqual(r['stage1_feature_sha256'], r['stage2_feature_sha256'])
    self.reject('candidate-set', 'candidates', rows + [rows[0]])

  def test_two_route_inverse_folds_and_order(self):
    cv = self.row('route-cv-contract')
    a = '7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677'
    b = '962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c'
    self.assertEqual(cv['folds'], [{'fold': 'FOLD_A', 'train': a, 'development': b}, {'fold': 'FOLD_B', 'train': b, 'development': a}])
    jobs = self.row('fitting-policy')['job_order']
    self.assertEqual(len(jobs), 32)
    self.assertEqual(jobs[:2], [['HRI_D00_L01', 'FOLD_A'], ['HRI_D00_L01', 'FOLD_B']])
    self.assertEqual(jobs[-1], ['HRI_D20_L45', 'FOLD_B'])
    self.reject('route-cv-contract', 'random_split', True)

  def test_stable_sigmoid_large_logits(self):
    for z, want in [(-1000.0, 0.0), (0.0, 0.5), (1000.0, 1.0)]:
      field = 'sigmoid_nonnegative' if z >= 0 else 'sigmoid_negative'
      self.assertEqual(self.formula('stage1-fit-method', field, z=z), want)

  def test_bce_and_newton_quantities(self):
    x = np.array([[1.0, -1.0], [1.0, 1.0]])
    y = np.array([0.0, 1.0])
    z = np.zeros(2)
    prob = np.full(2, 0.5)
    self.assertEqual(self.formula('stage1-fit-method', 'loss', z=z, y=y), math.log(2))
    g = self.formula('stage1-fit-method', 'gradient', X=x, p=prob, y=y, n=2)
    np.testing.assert_array_equal(g, [0.0, -0.5])
    w = self.formula('stage1-fit-method', 'weights', p=prob)
    h = self.formula('stage1-fit-method', 'hessian', X=x, w=w, n=2)
    np.testing.assert_array_equal(h, np.eye(2) * 0.25)
    direction = self.formula('stage1-fit-method', 'direction', H=h, g=g)
    np.testing.assert_array_equal(direction, [0.0, -2.0])
    np.testing.assert_array_equal(self.formula('stage1-fit-method', 'update', beta=z, alpha=1.0, direction=direction), [0.0, 2.0])

  def test_hessian_failure_has_no_fallback(self):
    with self.assertRaises(np.linalg.LinAlgError):
      self.formula('stage1-fit-method', 'direction', H=np.zeros((2, 2)), g=np.ones(2))
    self.assertEqual(self.row('stage1-fit-method')['solve_failure'], 'MOVE_GATE_NUMERICAL_FAILURE')
    self.reject('stage1-fit-method', 'fallback', 'PINV')

  def test_convergence_boundary_and_final_check(self):
    c = self.row('stage1-convergence')
    self.assertTrue(self.formula('stage1-convergence', 'converged', g=np.array([1e-8]), tolerance=c['gradient_tolerance']))
    self.assertFalse(self.formula('stage1-convergence', 'converged', g=np.array([np.nextafter(1e-8, np.inf)]), tolerance=c['gradient_tolerance']))
    self.assertEqual(c['max_updates'], 100)
    self.assertEqual(c['final_gradient_check'], 'AFTER_UPDATE_100_BEFORE_NONCONVERGENCE')
    self.assertEqual(c['nonconvergence'], 'MOVE_GATE_NONCONVERGENCE')

  def test_armijo_backtrack_boundary(self):
    c = self.row('stage1-convergence')
    self.assertEqual([c['alpha_initial'] * c['shrink'] ** j for j in (0, 1, 20)], [1.0, 0.5, 2.0**-20])
    self.assertEqual(c['trial_exponents'], list(range(21)))
    bound = 1.0 - 1e-4
    self.assertTrue(self.formula('stage1-convergence', 'armijo', loss_new=bound, loss_old=1.0, c=1e-4, alpha=1.0, slope=1.0))
    self.assertFalse(self.formula('stage1-convergence', 'armijo', loss_new=np.nextafter(bound, np.inf), loss_old=1.0, c=1e-4, alpha=1.0, slope=1.0))
    self.assertEqual(c['line_search_failure'], 'MOVE_GATE_LINE_SEARCH_FAILURE')

  def test_invalid_newton_values(self):
    for slope in [0.0, -1.0, np.nan, np.inf]:
      self.assertFalse(self.formula('stage1-convergence', 'valid_slope', slope=slope))
    self.reject('stage1-fit-method', 'regularization', 'RIDGE')

  def threshold(self, probs, labels):
    t = self.row('threshold-policy')
    candidates = sorted(set(t['boundary_candidates']) | set(probs))
    positives, negatives = labels.count(1), labels.count(0)
    keys = []
    for threshold in candidates:
      moves = [OPS[t['move_operator']](p_, threshold) for p_ in probs]
      tp = sum(m and y == 1 for m, y in zip(moves, labels, strict=True))
      tn = sum(not m and y == 0 for m, y in zip(moves, labels, strict=True))
      score = self.formula('threshold-policy', 'integer_score', TP=tp, TN=tn, P=positives, N=negatives)
      values = {'BA_NUM': score, 'TN': tn, 'threshold': threshold}
      keys.append((tuple(values[k] for k in t['maximize_keys']), threshold))
    return candidates, max(keys)[1]

  def test_threshold_exact_candidates_and_strict_equality(self):
    candidates, threshold = self.threshold([0.0, 0.2, 0.2, 1.0], [0, 0, 1, 1])
    self.assertEqual(candidates, [0.0, 0.2, 1.0])
    self.assertEqual(threshold, 0.2)
    self.assertFalse(OPS[self.row('threshold-policy')['move_operator']](0.2, threshold))
    self.assertFalse(OPS[self.row('threshold-policy')['move_operator']](1.0, 1.0))

  def test_threshold_tn_and_high_threshold_ties(self):
    self.assertEqual(self.threshold([0.2, 0.8], [1, 0])[1], 1.0)
    self.assertEqual(self.threshold([0.2, 0.2], [1, 0])[1], 1.0)

  def test_integer_score_does_not_overflow_or_round(self):
    n = 2**62
    a = self.formula('threshold-policy', 'integer_score', TP=n, TN=n - 1, P=n, N=n)
    b = self.formula('threshold-policy', 'integer_score', TP=n, TN=n, P=n, N=n)
    self.assertEqual(b - a, n)
    self.assertIs(type(b), int)
    self.assertEqual(self.row('threshold-policy')['integer_type'], 'UNBOUNDED_PYTHON_INT')

  def test_threshold_population_and_privacy(self):
    t = self.row('threshold-policy')
    self.assertEqual(t['population'], 'CANDIDATE_FOLD_STAGE1_TRAIN_ONLY')
    self.assertEqual(t['actual_threshold'], 'NOT_COMPUTED_PRIVATE_FUTURE_BUNDLE_ONLY')
    self.reject('threshold-policy', 'population', 'DEVELOPMENT')
    self.reject('threshold-policy', 'move_operator', '>=')
    self.reject('threshold-policy', 'boundary_candidates', [0.5])

  def test_separate_train_normalizer_and_move_filter(self):
    n = self.row('stage-normalization')
    labels = np.array([0, 1, 0, 1])
    x = np.array([[1.0, 0.0], [1.0, 2.0], [1.0, 4.0], [1.0, 6.0]])
    mask = self.formula('stage2-fit-method', 'population_mask', move_label=labels)
    np.testing.assert_array_equal(mask, [False, True, False, True])
    self.assertEqual(n['stage1_population'], 'ALL_CANDIDATE_SPECIFIC_TRAIN_ROWS')
    self.assertEqual(n['stage2_population'], 'TRUE_MOVE_CANDIDATE_SPECIFIC_TRAIN_ROWS')
    self.assertEqual(self.formula('stage-normalization', 'mean', X=x[:, 1:])[0], 3.0)
    self.assertEqual(self.formula('stage-normalization', 'mean', X=x[mask, 1:])[0], 4.0)
    self.assertEqual(self.formula('stage-normalization', 'std', X=x[mask, 1:])[0], 2.0)
    self.assertEqual(n['constant_columns'], 'DROP_EFFECTIVE_KEEP_NOMINAL_COEFFICIENT_ZERO')
    self.reject('stage-normalization', 'reuse_stage1_for_stage2', True)

  def test_rank_and_support_preconditions(self):
    s = self.row('stage2-fit-method')
    self.assertEqual(s['minimum_move_train'], 'max(P, 201)')
    self.assertEqual(s['rank_operator'], '==')
    self.assertEqual(s['rcond'], None)
    self.assertEqual(s['precondition_failure'], 'CONDITIONAL_DELTA_RANK_FAILURE')
    self.assertEqual(s['solve_on_failed_rank'], False)
    self.reject('stage2-fit-method', 'rcond', 1e-4)

  def test_no_weighting_warmstart_regularization(self):
    self.reject('stage1-fit-method', 'class_weighting', 'BALANCED')
    self.reject('stage1-fit-method', 'initial_beta', 'WARM_START')
    self.reject('stage2-fit-method', 'regularization', 'RIDGE')
    self.reject('stage2-fit-method', 'population_mask', 'move_label >= 0')

  def test_metric_canonical_buffer_and_p95(self):
    m = self.row('metric-contract')
    self.assertEqual(m['canonical_one_step_error'], 'FINAL_INTEGRATED_DELTA_MINUS_FLOAT64_ACTUAL_DELTA')
    self.assertEqual(m['next_angle_error'], 'ALIAS_OF_CANONICAL_ONE_STEP_ERROR')
    self.assertEqual(self.formula('metric-contract', 'p95', error=np.array([0.0, 1.0, 2.0])), 1.9)
    self.assertEqual(m['rollout_error'], 'PROJECTED_ENDPOINT_MINUS_OBSERVED_ENDPOINT')
    self.assertEqual(m['rollout_scoring'], 'ENDPOINT_ONLY')

  def test_comparator_exact_population_and_no_oracle_primary(self):
    self.assertEqual(self.row('comparator-contract')['primary'], 'HOLD_LAST_ANGLE')
    self.assertEqual(self.row('comparator-contract')['anchor_identity'], 'EXACT_SAME_ORDERED_SHA_PER_POPULATION')
    self.reject('metric-contract', 'true_move_output', 'ORACLE_STAGE2')
    self.reject('acceptance-gate', 'oracle_admission', True)

  def fixtures(self):
    gate = self.row('acceptance-gate')
    return {
      fold: {
        clause['id']: {'candidate': 0.5 if clause['operator'] in ('<', '<=') else 0.9, 'hold': 1.0 if clause['operator'] in ('<', '<=') else 0.8}
        for clause in gate['clauses']
      }
      for fold in ('FOLD_A', 'FOLD_B')
    }

  def admitted(self, fixtures):
    gate = self.row('acceptance-gate')
    return all(OPS[c['operator']](fixtures[f][c['id']]['candidate'], fixtures[f][c['id']]['hold']) for f in gate['required_folds'] for c in gate['clauses'])

  def test_all_gate_clauses_both_folds_required(self):
    clauses = self.row('acceptance-gate')['clauses']
    self.assertEqual(len(clauses), 32)
    self.assertTrue(self.admitted(self.fixtures()))
    for fold in ('FOLD_A', 'FOLD_B'):
      for c in clauses:
        fixtures = self.fixtures()
        fixtures[fold][c['id']]['candidate'] = 2.0 if c['operator'] in ('<', '<=') else 0.0
        with self.subTest(fold=fold, clause=c['id']):
          self.assertFalse(self.admitted(fixtures))

  def test_gate_no_epsilon_and_strict_one_step(self):
    fixtures = self.fixtures()
    fixtures['FOLD_A']['ONE_STEP_RMSE']['candidate'] = 1.0
    self.assertFalse(self.admitted(fixtures))
    fixtures = self.fixtures()
    fixtures['FOLD_A']['MOVE_MAE']['candidate'] = np.nextafter(1.0, np.inf)
    self.assertFalse(self.admitted(fixtures))
    self.reject('acceptance-gate', 'epsilon', 1e-9)

  def test_path_moved_all_horizons_and_no_flat_gate(self):
    ids = [c['id'] for c in self.row('acceptance-gate')['clauses']]
    self.assertEqual(len([i for i in ids if i.startswith('PATH_MOVED_')]), 12)
    self.assertFalse(any('PATH_FLAT' in i for i in ids))
    self.assertEqual(self.row('metric-contract')['minimum_path_moved_per_horizon'], 201)

  def test_zero_one_multiple_selection(self):
    s = self.row('selection-rule')
    self.assertEqual(s['zero'], ['HURDLE_NO_ADMISSIBLE_CANDIDATE', 'MODEL_SELECTION_FAILED_CLOSED'])
    self.assertEqual(s['one'], ['HURDLE_SINGLE_ADMISSIBLE_CANDIDATE', 'HURDLE_RETROSPECTIVE_CV_SELECTED'])
    self.assertEqual(s['multiple'], 'HURDLE_RETROSPECTIVE_CV_SELECTED')
    self.assertEqual(s['input'], 'ONLY_CANDIDATES_ADMISSIBLE_IN_BOTH_FOLDS')
    keys = s['ascending_keys']
    self.assertEqual(
      keys,
      [
        'WORST_PATH_MOVED_ROLLOUT_RMSE_RATIO',
        'WORST_OVERALL_ROLLOUT_RMSE_RATIO',
        'WORST_INTEGRATED_ONE_STEP_P95_RATIO',
        'TOTAL_NOMINAL_PARAMETER_COUNT',
        'L',
        'd',
        'candidate_id',
      ],
    )
    base = [1.0, 1.0, 1.0, 186, 45, 20, 'HRI_D20_L45']
    for index, lower in enumerate([0.9, 0.9, 0.9, 66, 15, 10, 'HRI_D10_L45']):
      better = base.copy()
      better[index] = lower
      a = dict(zip(keys, base, strict=True))
      b = dict(zip(keys, better, strict=True))
      self.assertEqual(sorted([a, b], key=lambda r: tuple(r[k] for k in keys))[0], b)
    self.reject('selection-rule', 'ascending_keys', keys[1:] + keys[:1])

  def test_ratio_zero_denominator_policy(self):
    r = self.row('selection-rule')['ratio']
    self.assertEqual(
      r,
      {
        'positive_denominator': 'FLOAT64_NUMERATOR_DIVIDE_DENOMINATOR',
        'zero_over_zero': 1.0,
        'positive_over_zero': 'POSITIVE_INFINITY',
        'negative_or_nonfinite_input': 'CANDIDATE_INVALID',
        'positive_denominator_overflow': 'CANDIDATE_INVALID',
      },
    )
    self.reject('selection-rule', 'zero', ['RELAX_GATE'])

  def test_hard_rollout_composition_and_no_fitting(self):
    r = self.row('fitting-policy')
    self.assertEqual(r['composition']['move_operator'], '>')
    self.assertEqual(r['composition']['static_delta'], 0.0)
    self.assertFalse(r['composition']['stage2_on_static'])
    self.assertFalse(r['composition']['force_minimum_movement'])
    self.assertEqual(r['rollout']['horizons_steps'], [25, 50, 100, 200])
    self.assertEqual(r['rollout']['state'], 'PROJECTED_INTEGER_TICK')
    self.assertFalse(r['rollout']['future_measured_steering_feedback'])
    self.reject('fitting-policy', 'actual_execution_authorized', True)

  def test_firewall_generation_no_numeric_import_or_array_read(self):
    original_import = builtins.__import__
    original_read = Path.read_bytes
    allow = {p.PUBLIC / name for name in self.d.PINS} | {Path(self.d.__file__).with_name(n) for n in self.d.SOURCES}

    def imports(name, *args, **kwargs):
      if name.startswith(('numpy', 'scipy', 'sklearn')) or any(
        x in name for x in ('logreader', 'fit_cv_execution', 'reconstruction', 'empirical_dataset', 'failure_attribution')
      ):
        raise AssertionError('EXECUTION_IMPORT_FORBIDDEN')
      return original_import(name, *args, **kwargs)

    def read(path):
      if path not in allow:
        raise AssertionError('PRIVATE_OR_UNBOUND_READ_FORBIDDEN')
      return original_read(path)

    with (
      patch.object(builtins, '__import__', imports),
      patch.object(Path, 'read_bytes', read),
      patch.object(np.linalg, 'lstsq', side_effect=AssertionError('FIT_FORBIDDEN')),
      patch.object(np.linalg, 'solve', side_effect=AssertionError('FIT_FORBIDDEN')),
      patch.object(np, 'load', side_effect=AssertionError('PRIVATE_ARRAY_FORBIDDEN')),
    ):
      self.assertEqual(self.d.build(), self.bundle)

  def test_all_authority_false_and_historical_preservation(self):
    for row in self.bundle.values():
      self.assertTrue(all(v is False for v in row['authority'].values()))
    r = self.row('fitting-policy-readiness')
    self.assertEqual(r['holdout'], 'HOLDOUT_OPENING_CLOSED')
    self.assertEqual(r['opening_count'], 0)
    self.assertFalse(r['vehicle_authority'])
    self.assertEqual(r['final_pooled_refit'], 'FINAL_POOLED_REFIT_NOT_AUTHORIZED')

  def test_publication_exact_resume_and_conflict_preflight(self):
    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp) / 'output'
      self.d.publish(root)
      before = {f.name: f.read_bytes() for f in root.iterdir()}
      self.d.publish(root)
      self.assertEqual(before, {f.name: f.read_bytes() for f in root.iterdir()})
      conflict = Path(temp) / 'conflict'
      conflict.mkdir()
      name = self.d.filename('fitting-policy-validation')
      (conflict / name).write_text('{}')
      with self.assertRaisesRegex(ValueError, 'IMMUTABLE_OUTPUT_CONFLICT'):
        self.d.publish(conflict)
      self.assertEqual([f.name for f in conflict.iterdir()], [name])

  def test_publication_symlink_and_traversal_reject(self):
    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp)
      (root / 'link').symlink_to(root, target_is_directory=True)
      for dest in (root / 'link' / 'output', root / '..' / 'output'):
        with self.assertRaisesRegex(ValueError, 'UNSAFE_PATH'):
          self.d.publish(dest)

  def test_unknown_or_missing_artifact_rejected(self):
    for extra in (True, False):
      b = copy.deepcopy(self.bundle)
      if extra:
        b['unknown.json'] = {}
      else:
        b.pop(next(iter(b)))
      with self.assertRaisesRegex(ValueError, 'CONTRACT_DRIFT'):
        self.d.validate(b)

  def test_published_bundle_matches(self):
    if not (p.PUBLIC / self.d.filename('fitting-policy')).exists():
      self.skipTest('publication follows implementation')
    b = {name: json.loads((p.PUBLIC / name).read_bytes()) for name in self.bundle}
    self.d.validate(b)

  def test_logit_equation_is_machine_readable(self):
    result = self.formula('stage1-fit-method', 'logits', X=np.array([[1.0, 2.0], [1.0, -2.0]]), beta=np.array([0.5, 1.0]))
    np.testing.assert_array_equal(result, [2.5, -1.5])

  def test_class_and_rank_preconditions_block_solve(self):
    s = self.row('stage1-fit-method')
    for static, move, expected in [(200, 201, False), (201, 200, False), (201, 201, True), (0, 202, False)]:
      self.assertEqual(static >= s['minimum_train_static'] and move >= s['minimum_train_move'], expected)
    stage2 = self.row('stage2-fit-method')
    for rank, width, expected in [(2, 3, False), (3, 3, True)]:
      self.assertEqual(OPS[stage2['rank_operator']](rank, width), expected)
    self.assertFalse(stage2['solve_on_failed_rank'])

  def test_undefined_precision_cannot_be_silently_zero(self):
    m = self.row('metric-contract')
    self.assertEqual(m['stage1_diagnostics']['precision'], 'TP/(TP+FP)')
    self.assertEqual(m['undefined_diagnostic'], 'STAGE1_DIAGNOSTIC_UNDEFINED_WHOLE_FOLD_FAIL_CLOSED')
    with self.assertRaises(ZeroDivisionError):
      eval(m['stage1_diagnostics']['precision'], {'__builtins__': {}}, {'TP': 0, 'FP': 0})
    self.reject('metric-contract', 'undefined_diagnostic', 'SUBSTITUTE_ZERO_AND_ADMIT')

  def test_static_and_move_support_do_not_share_201_budget(self):
    m = self.row('metric-contract')
    self.assertEqual([m['minimum_one_step_all'], m['minimum_one_step_static'], m['minimum_one_step_move']], [201, 201, 201])
    self.assertEqual(m['minimum_overall_rollout_per_horizon'], 201)
    self.reject('metric-contract', 'minimum_path_moved_per_horizon', 0)

  def test_finite_exact_comparison_domains(self):
    g = self.row('acceptance-gate')
    self.assertEqual(g['nonfinite_or_negative_error_metric'], 'WHOLE_FOLD_INVALID')
    self.assertEqual(g['grid_rate_domain'], 'FINITE_CLOSED_0_1')
    self.assertEqual(g['quantifier'], 'ALL_CLAUSES_AND_SUPPORT_AND_NUMERICAL_PRECONDITIONS_IN_BOTH_FOLDS')

  def test_rate_free_feature_coordinate_bound(self):
    cs = self.row('candidate-set')['candidates']
    self.assertTrue(all(x['stage1_feature_sha256'] == '517288519b2ae0ef9edaa4b2a0c5e5a1b296389e4381ac4af0a2bddfec41be3a' for x in cs))
    self.assertEqual(self.row('fitting-policy')['steering_rate_dependency'], 'NONE')
    self.reject('fitting-policy', 'stage1_feature_sha256', 'unbound-rate-dependent')

  def test_cold_policy_import_has_no_execution_dependency(self):
    import subprocess
    import sys

    code = """
import builtins
original = builtins.__import__
def guarded(name, *a, **k):
  if name.startswith(('numpy', 'scipy', 'sklearn')) or any(s in name for s in ('fit_cv_execution', 'logreader', 'reconstruction')):
    raise AssertionError(name)
  return original(name, *a, **k)
builtins.__import__ = guarded
from openpilot.tools.cyber_autotune import empirical_hurdle_fitting_policy as module
assert len(module.build()) == 14
"""
    subprocess.run([sys.executable, '-c', code], check=True, capture_output=True, text=True)


if __name__ == '__main__':
  unittest.main()
