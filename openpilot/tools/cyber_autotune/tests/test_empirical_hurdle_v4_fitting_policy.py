"""Synthetic fitting policy only. Actual scientific data are never loaded."""

from fractions import Fraction
import unittest
from unittest.mock import patch

import numpy as np


def module():
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_fitting_policy as p
  return p


def normalizer(constant_speed=False):
  return {'mean': np.array([1., 0., .5, 0., 10.]), 'std': np.array([0., 1., .5, 1., 0. if constant_speed else 2.]),
          'constant': np.array([False, False, False, False, constant_speed]),
          'effective': np.array([0, 1, 2, 3] if constant_speed else [0, 1, 2, 3, 4]),
          'constant_reference': np.array([1., 0., 0., 0., 10.])}


def fixture():
  # Both labels at every distinct feature row => explicit positive dual witness.
  x, y = [], []
  for z in (0, 1):
    for command in (-1., 1.):
      for tick in (-1., 1.):
        for speed in (8., 12.):
          for delta in ((0.,) if z == 0 else (-1., 1.)):
            for label in (0, 1):
              for _ in range(26):  # 208 / 416 per class, inherited floor 201.
                x.append([1., command, delta, tick, speed])
                y.append(label)
  return np.array(x, np.float64), np.array(y, np.int64)


def cert(x, y, *, dual=None, direction=None):
  p = module()
  value = {'matrix_binding': p.matrix_binding(x, y)}
  if dual is not None:
    value.update(kind='POSITIVE_DUAL', weights=dual)
  if direction is not None:
    value.update(kind='SEPARATING_DIRECTION', direction=direction)
  return value


class TestSharedBasis(unittest.TestCase):
  def test_static_drop_only_structural_raw_index(self):
    p = module()
    self.assertEqual(p.basis(normalizer(), 'HRI_D00_L01', 0), [0, 1, 3, 4])

  def test_move_retains_all_effective(self):
    p = module()
    self.assertEqual(p.basis(normalizer(), 'HRI_D00_L01', 1), [0, 1, 2, 3, 4])

  def test_intercept_retained_and_existing_constants_not_reselected(self):
    p = module()
    self.assertEqual(p.basis(normalizer(True), 'HRI_D00_L01', 0), [0, 1, 3])
    self.assertEqual(p.basis(normalizer(True), 'HRI_D00_L01', 1), [0, 1, 2, 3])

  def test_shared_normalization_exact_source_parity(self):
    p = module()
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    x, _ = fixture()
    n = normalizer()
    got = p.apply_shared(x, n, expected_identity=p.normalizer_identity(n), scope=p.SCOPE)
    np.testing.assert_array_equal(got, old.transform(x, n))

  def test_normalizer_identity_drift_fails(self):
    p = module()
    x, _ = fixture()
    with self.assertRaisesRegex(ValueError, 'NORMALIZER_IDENTITY'):
      p.apply_shared(x, normalizer(), expected_identity='0' * 64, scope=p.SCOPE)

  def test_no_context_normalizer_fit(self):
    p = module()
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    with patch.object(old, 'normalizer', side_effect=AssertionError('normalizer fit')):
      x, _ = fixture()
      p.apply_shared(x, normalizer(), expected_identity=p.normalizer_identity(normalizer()), scope=p.SCOPE)

  def test_affine_coefficient_bijection_and_static_intercept_absorption(self):
    p = module()
    w = p.algebra_witness()
    np.testing.assert_array_equal(w['raw_static_logits'], w['normalized_static_logits'])
    np.testing.assert_array_equal(w['raw_move_logits'], w['normalized_move_logits'])
    self.assertFalse(w['off_support_empirical_constant_equivalence_claim'])

  def test_no_extra_column_drop_for_context_rank(self):
    p = module()
    x = np.ones((402, 4), np.float64)
    with self.assertRaisesRegex(ValueError, 'RANK'):
      p.rank_certificate(x, scope=p.SCOPE)


class TestSupportRank(unittest.TestCase):
  def test_below_move_support(self):
    p = module()
    with self.assertRaisesRegex(ValueError, 'SUPPORT'):
      p.support(np.array([1] * 200 + [0] * 201), 2, scope=p.SCOPE)

  def test_below_static_support(self):
    p = module()
    with self.assertRaisesRegex(ValueError, 'SUPPORT'):
      p.support(np.array([1] * 201 + [0] * 200), 2, scope=p.SCOPE)

  def test_exact_historical_support_floor(self):
    p = module()
    self.assertEqual(p.support(np.array([0] * 201 + [1] * 201), 2, scope=p.SCOPE), {'positive': 201, 'negative': 201, 'count': 402})
    self.assertEqual(p.SUPPORT, 201)

  def test_n_must_exceed_parameter_count(self):
    p = module()
    with self.assertRaisesRegex(ValueError, 'SUPPORT'):
      p.support(np.array([0] * 201 + [1] * 201), 402, scope=p.SCOPE)

  def test_explicit_rank_tolerance_formula(self):
    p = module()
    x = np.array([[1., -1.], [1., 0.], [1., 1.]])
    r = p.rank_certificate(x, scope=p.SCOPE)
    s = np.linalg.svd(x, compute_uv=False)
    self.assertEqual(r['tolerance'], float(s[0] * max(x.shape) * np.finfo(np.float64).eps))
    self.assertEqual(r['rank'], 2)
    self.assertTrue(r['exact_minor_verified'])

  def test_rank_deficiency_fails_without_pseudoinverse(self):
    p = module()
    x = np.array([[1., 1.], [1., 1.], [1., 1.]])
    with patch('numpy.linalg.pinv', side_effect=AssertionError('fallback')), self.assertRaisesRegex(ValueError, 'RANK'):
      p.rank_certificate(x, scope=p.SCOPE)

  def test_numerical_full_rank_is_not_exact_rank_proof(self):
    p = module()
    x = np.ones((3, 2), np.float64)
    with patch('numpy.linalg.svd', return_value=np.array([2., 1.])), self.assertRaisesRegex(ValueError, 'RANK'):
      p.rank_certificate(x, scope=p.SCOPE)


class TestSeparation(unittest.TestCase):
  def test_complete_separation_positive_direction(self):
    p = module()
    x, y = np.array([[1., -1.], [1., 1.]]), np.array([0, 1])
    r = p.separation_certificate(x, y, cert(x, y, direction=[0, 1]), scope=p.SCOPE)
    self.assertEqual(r['status'], 'SEPARATION_PRESENT')
    self.assertEqual(r['positive_margin_count'], 2)

  def test_quasi_separation_fixture(self):
    p = module()
    x, y = np.array([[1., 0.], [1., 0.], [1., 1.]]), np.array([0, 1, 1])
    r = p.separation_certificate(x, y, cert(x, y, direction=[0, 1]), scope=p.SCOPE)
    self.assertEqual(r['status'], 'SEPARATION_PRESENT')
    self.assertEqual(r['zero_margin_count'], 2)

  def test_overlap_exact_positive_dual(self):
    p = module()
    x = np.array([[1., -1.], [1., -1.], [1., 1.], [1., 1.]])
    y = np.array([0, 1, 0, 1])
    r = p.separation_certificate(x, y, cert(x, y, dual=[1] * 4), scope=p.SCOPE)
    self.assertEqual(r['status'], 'NO_SEPARATION')
    self.assertEqual(r['exact_dual_residual'], '0')
    self.assertEqual(r['certified_lp_optimum'], '0')

  def test_zero_dual_not_certificate(self):
    p = module()
    x, y = np.array([[1.], [1.]]), np.array([0, 1])
    self.assertEqual(p.separation_certificate(x, y, cert(x, y, dual=[0, 0]), scope=p.SCOPE)['status'],
                     'SEPARATION_CERTIFICATE_INCONCLUSIVE')

  def test_nearly_zero_residual_is_not_zero(self):
    p = module()
    x, y = np.array([[1.], [1.]]), np.array([0, 1])
    c = cert(x, y, dual=[Fraction(1), Fraction(1) + Fraction(1, 10**30)])
    self.assertEqual(p.separation_certificate(x, y, c, scope=p.SCOPE)['status'], 'SEPARATION_CERTIFICATE_INCONCLUSIVE')

  def test_exact_binary64_not_rounded_decimal(self):
    p = module()
    x, y = np.array([[.1], [.1]]), np.array([0, 1])
    self.assertEqual(p.separation_certificate(x, y, cert(x, y, dual=[1, 1]), scope=p.SCOPE)['status'], 'NO_SEPARATION')

  def test_wrong_row_order_or_binding_rejected(self):
    p = module()
    x, y = np.array([[1.], [1.]]), np.array([0, 1])
    c = cert(x, y, dual=[1, 1])
    self.assertEqual(p.separation_certificate(x, y[::-1].copy(), c, scope=p.SCOPE)['status'], 'SEPARATION_CERTIFICATE_INCONCLUSIVE')

  def test_missing_certificate_inconclusive(self):
    p = module()
    x, y = np.array([[1.], [1.]]), np.array([0, 1])
    self.assertEqual(p.separation_certificate(x, y, None, scope=p.SCOPE)['status'], 'SEPARATION_CERTIFICATE_INCONCLUSIVE')


class TestOptimizer(unittest.TestCase):
  def test_existing_constants_and_unweighted_loss(self):
    p = module()
    self.assertEqual((p.MAX_UPDATES, p.GRADIENT_TOLERANCE, p.ARMIJO_C, p.TRIAL_EXPONENTS), (100, 1e-8, 1e-4, tuple(range(21))))
    self.assertEqual(p.REGULARIZATION, 'NONE')
    self.assertEqual(p.CLASS_WEIGHTING, 'NONE')

  def test_zero_initialization_overlap_gradient_zero(self):
    p = module()
    x = np.array([[1., -1.], [1., -1.], [1., 1.], [1., 1.]])
    y = np.array([0, 1, 0, 1])
    beta, receipt = p.newton_synthetic(x, y, scope=p.SCOPE)
    np.testing.assert_array_equal(beta, [0., 0.])
    self.assertEqual(receipt['updates'], 0)

  def test_nonzero_fit_reuses_exact_old_newton(self):
    p = module()
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    x = np.ones((4, 1), np.float64)
    y = np.array([0, 1, 1, 1])
    b, r = p.newton_synthetic(x, y, scope=p.SCOPE)
    reference, rr = old.newton(x, y.astype(np.float64))
    np.testing.assert_array_equal(b, reference)
    self.assertEqual(r, rr)
    self.assertGreater(r['updates'], 0)

  def test_no_armijo_trial_fails(self):
    p = module()
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    with patch.object(old, 'TRIAL_EXPONENTS', ()), self.assertRaisesRegex(ValueError, 'LINE_SEARCH'):
      p.newton_synthetic(np.ones((4, 1)), np.array([0, 1, 1, 1]), scope=p.SCOPE)

  def test_max_updates_failure(self):
    p = module()
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    with patch.object(old, 'MAX_UPDATES', 0), self.assertRaisesRegex(ValueError, 'NONCONVERGENCE'):
      p.newton_synthetic(np.ones((4, 1)), np.array([0, 1, 1, 1]), scope=p.SCOPE)

  def test_singular_hessian_fails(self):
    p = module()
    with self.assertRaisesRegex(ValueError, 'NUMERICAL'):
      p.newton_synthetic(np.ones((4, 2)), np.array([0, 1, 1, 1]), scope=p.SCOPE)

  def test_nonpositive_slope_fails(self):
    p = module()
    with patch('numpy.linalg.solve', return_value=np.array([1.])), self.assertRaisesRegex(ValueError, 'NUMERICAL'):
      p.newton_synthetic(np.ones((4, 1)), np.array([0, 1, 1, 1]), scope=p.SCOPE)

  def test_nonfinite_input_fails(self):
    p = module()
    with self.assertRaises(ValueError):
      p.newton_synthetic(np.array([[np.nan]]), np.array([1]), scope=p.SCOPE)

  def test_local_head_gradient_not_global_scaled(self):
    p = module()
    self.assertFalse(p.converged(np.array([2e-8])))
    self.assertTrue(p.converged(np.array([2e-9])))


class TestDualFitting(unittest.TestCase):
  def run_fixture(self):
    p = module()
    x, y = fixture()
    n = normalizer()
    return p.fit_synthetic(x, y, n, candidate='HRI_D00_L01', fold='FOLD_A',
      expected_normalizer_identity=p.normalizer_identity(n), certificate_factory=lambda a, b, z: cert(a, b, dual=[1] * len(b)),
      scope=p.SCOPE, role='TRAIN')

  def test_both_heads_independent_and_combined_original_order(self):
    r = self.run_fixture()
    self.assertEqual(r['heads']['STATIC']['basis'], [0, 1, 3, 4])
    self.assertEqual(r['heads']['MOVE']['basis'], [0, 1, 2, 3, 4])
    np.testing.assert_array_equal(r['probabilities'], .5)
    self.assertEqual(r['threshold']['candidate_count'], 3)

  def test_two_synthetic_runs_byte_equal(self):
    p = module()
    self.assertEqual(p.result_identity(self.run_fixture()), p.result_identity(self.run_fixture()))

  def test_block_minimizer_algebra_not_byte_optimizer_claim(self):
    p = module()
    r = p.algebra_witness()
    self.assertEqual(r['independent_sum_nll'], r['block_sum_nll'])
    self.assertFalse(r['block_optimizer_byte_equivalence_claim'])

  def test_separation_gate_precedes_newton(self):
    p = module()
    x, y = fixture()
    with patch.object(p, 'newton_synthetic', side_effect=AssertionError('must not fit')):
      r = p.fit_synthetic(x, y, normalizer(), candidate='HRI_D00_L01', fold='FOLD_A',
        expected_normalizer_identity=p.normalizer_identity(normalizer()), certificate_factory=lambda a, b, z: None,
        scope=p.SCOPE, role='TRAIN')
    self.assertEqual(r['status'], 'V4_STAGE1_FIT_FAILED_CLOSED')
    self.assertEqual(r['cause'], 'SEPARATION_CERTIFICATE_INCONCLUSIVE')
    self.assertNotIn('probabilities', r)

  def test_combined_head_choice_interleaved_order(self):
    p = module()
    x = np.array([[1., 1.], [1., 2.], [1., 3.], [1., 4.]])
    z = np.array([1, 0, 1, 0])
    got = p.combine(x, z, {0: {'positions': [0], 'coefficients': np.array([-1.])},
                            1: {'positions': [0], 'coefficients': np.array([1.])}}, scope=p.SCOPE)
    self.assertGreater(got[0], got[1])
    self.assertEqual(got[0], got[2])
    self.assertEqual(got[1], got[3])


class TestThreshold(unittest.TestCase):
  def test_exact_v1_semantics_all_thresholds(self):
    p = module()
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    probabilities = np.array([0., .2, .2, .6, 1., 1.])
    y = np.array([0, 0, 1, 1, 0, 1])
    got = p.threshold_synthetic(probabilities, y, scope=p.SCOPE, role='TRAIN')
    self.assertEqual(got, old.threshold(probabilities, y, role='TRAIN'))
    keys = []
    for t in np.unique(np.r_[0., 1., probabilities]):
      gate = probabilities > t
      tp, tn = int(np.count_nonzero(gate & (y == 1))), int(np.count_nonzero(~gate & (y == 0)))
      keys.append((tp * 3 + tn * 3, tn, t))
    self.assertEqual((got['BA_NUM'], got['TN'], got['value']), max(keys))

  def test_tn_and_max_threshold_ties(self):
    p = module()
    r = p.threshold_synthetic(np.array([.5, .5]), np.array([0, 1]), scope=p.SCOPE, role='TRAIN')
    self.assertEqual(r['value'], 1.)
    self.assertEqual(r['TN'], 1)

  def test_equal_probability_static_and_endpoints(self):
    p = module()
    r = p.threshold_synthetic(np.array([0., 1.]), np.array([0, 1]), scope=p.SCOPE, role='TRAIN')
    self.assertEqual(r['value'], 0.)
    np.testing.assert_array_equal(np.array([0., 1.]) > r['value'], [False, True])

  def test_dev_threshold_forbidden(self):
    p = module()
    with self.assertRaises(ValueError):
      p.threshold_synthetic(np.array([.1, .9]), np.array([0, 1]), scope=p.SCOPE, role='DEVELOPMENT')


class TestAuthority(unittest.TestCase):
  def test_actual_entrypoint_blocked_before_loader(self):
    p = module()
    with patch('numpy.load', side_effect=AssertionError('numeric open')), self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
      p.execute_private()

  def test_non_synthetic_scopes_blocked(self):
    p = module()
    for scope in ('PRIVATE', 'TRAIN', 'DEVELOPMENT', 'HOLDOUT'):
      with self.assertRaises(ValueError):
        p.newton_synthetic(np.ones((2, 1)), np.array([0, 1]), scope=scope)

  def test_no_private_io_hf_or_rollout_calls(self):
    import ast
    from pathlib import Path
    p = module()
    tree = ast.parse(Path(p.__file__).read_text())
    forbidden = {'open', 'read_bytes', 'read_text', 'load', 'rollout', 'recursive', 'normalizer', 'fit_stage1', 'fit_stage2',
                 'lstsq', 'pinv', 'clip', 'choice', 'shuffle', 'linprog', 'requests', 'urlopen'}
    calls = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    self.assertFalse(calls & forbidden)

  def test_unweighted_unregularized_contract(self):
    p = module()
    self.assertEqual(p.REGULARIZATION, 'NONE')
    self.assertEqual(p.CLASS_WEIGHTING, 'NONE')
    self.assertFalse(p.RESAMPLING)


class TestPublicPolicy(unittest.TestCase):
  def test_exact_input_receipts_and_mutation(self):
    from tools.cyberpilot.build_hurdle_v4_fitting_policy import locked_inputs, PINS
    self.assertEqual(len(locked_inputs()), 18)
    name = next(iter(PINS))
    with patch.dict(PINS, {name: ('0' * 64, PINS[name][1])}), self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      locked_inputs()

  def test_exact_source_pin_mutation(self):
    from tools.cyberpilot.build_hurdle_v4_fitting_policy import locked_inputs, SOURCE_PINS
    name = next(iter(SOURCE_PINS))
    with patch.dict(SOURCE_PINS, {name: '0' * 64}), self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      locked_inputs()

  def test_fourteen_receipts_exact_builder(self):
    import json
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from tools.cyberpilot.build_hurdle_v4_fitting_policy import build
    rows = build()
    self.assertEqual(len(rows), 14)
    for name, row in rows.items():
      self.assertEqual(p.verify(row), json.loads((p.PUBLIC / name).read_bytes()))
      self.assertEqual(set(row['v4'].values()), {'NOT_RUN'})
      self.assertEqual(row['private_numeric_array_opens'], 0)
      self.assertFalse(row['actual_execution_authorized'])

  def test_frozen_policy_not_actual_fitting_or_executor_readiness(self):
    from tools.cyberpilot.build_hurdle_v4_fitting_policy import build, PREFIX, FROZEN
    rows = build()
    self.assertEqual(rows[PREFIX + 'fitting-policy-decision.json']['status'], FROZEN)
    ready = rows[PREFIX + 'fitting-policy-readiness.json']
    self.assertTrue(ready['policy_ready'])
    self.assertFalse(ready['actual_private_executor_ready'])
    validation = rows[PREFIX + 'fitting-policy-validation.json']
    self.assertIn('SYNTHETIC', validation['operation_counter_scope'])
    self.assertEqual(validation['synthetic_operations']['head_fitting'], 'EXECUTED_SYNTHETIC_ONLY')
    self.assertEqual(validation['actual_coefficients'], 'NOT_GENERATED')

  def test_gate_selector_and_source_job_identity_bindings(self):
    from tools.cyberpilot.build_hurdle_v4_fitting_policy import build, PREFIX
    rows = build()
    jobs = rows[PREFIX + 'fitting-policy-inputs.json']['public_v1_jobs']
    self.assertEqual(len(jobs), 32)
    self.assertTrue(all(j['stages']['stage1']['effective_columns'] == j['stages']['stage1']['nominal_columns'] for j in jobs))
    failure = rows[PREFIX + 'failure-policy.json']
    self.assertEqual(len(failure['final_gate']['clauses']), 32)
    self.assertTrue(failure['final_gate']['both_folds_required'])
    proof = failure['selection']['complexity_binding']
    self.assertEqual(proof['pairs_verified'], 256)
    self.assertFalse(proof['selector_code_changed'])
    self.assertTrue(proof['historical_proxy_is_not_reported_as_actual_v4_count'])

  def test_privacy_and_future_authority_storage(self):
    from tools.cyberpilot.build_hurdle_v4_fitting_policy import build, PREFIX
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    rows = build()
    text = p.canonical(rows).decode()
    for bad in ('/mnt/e/', '/mnt/d/', 'E:\\', 'D:\\', 'normalizer_values', 'actual_threshold_value'):
      self.assertNotIn(bad, text)
    row = rows[PREFIX + 'artifact-identity-policy.json']
    self.assertFalse(row['historical_storage_receipt_is_v4_execution_authority'])
    self.assertIn('E_EXTERNAL_SSD_ONLY', row['storage'])
    self.assertEqual(row['vehicle_authority'], 'NONE')
    self.assertEqual(row['holdout'], 'CLOSED')
    self.assertEqual(row['hugging_face']['upload'], 0)
    self.assertEqual(row['hugging_face']['download'], 0)


if __name__ == '__main__':
  unittest.main()
