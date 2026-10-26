"""Synthetic-only tests for the frozen actual execution primitives."""

import unittest
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m


def fixture():
  t = np.arange(804, dtype=np.float64)
  x = np.column_stack((np.ones(len(t)), (t % 17) - 8, (t % 7) - 3))
  y = ((t % 4) == 0).astype(np.int64)
  return x, y


class TestHurdleMath(unittest.TestCase):
  def test_stable_sigmoid_extremes(self):
    with np.errstate(over='raise', invalid='raise'):
      p = m.sigmoid(np.array([-1000.0, -1.0, 0.0, 1.0, 1000.0]))
    np.testing.assert_array_equal(p[[0, 2, 4]], [0.0, 0.5, 1.0])
    self.assertTrue(np.all(np.diff(p) > 0))

  def test_threshold_sweep_matches_bruteforce(self):
    for probabilities in ([0.0, 0.1, 0.1, 0.7, 1.0], [0.2, 0.2, 0.2, 0.2, 0.2], [0.0, 0.0, 1.0, 1.0, 1.0]):
      for bits in range(1, 31):
        y = np.array([(bits >> i) & 1 for i in range(5)], dtype=bool)
        p = np.array(probabilities)
        values = sorted({0.0, 1.0, *p})
        rows = []
        for threshold in values:
          gate = p > threshold
          tp, tn = int((gate & y).sum()), int((~gate & ~y).sum())
          rows.append((tp * int((~y).sum()) + tn * int(y.sum()), tn, threshold))
        expected = max(rows)
        result = m.threshold(p, y, role='TRAIN')
        self.assertEqual((result['BA_NUM'], result['TN'], result['value']), expected)
        self.assertEqual(result['candidate_count'], len(values))

  def test_threshold_rejects_development(self):
    with self.assertRaisesRegex(ValueError, 'TRAIN_ONLY'):
      m.threshold(np.array([0.2, 0.7]), np.array([False, True]), role='DEVELOPMENT')

  def test_threshold_strict_boundary(self):
    result = m.threshold(np.array([0.2, 0.2]), np.array([False, True]), role='TRAIN')
    self.assertEqual(result['value'], 1.0)
    self.assertEqual(result['TP'], 0)

  def test_threshold_invalid_probability(self):
    for value in (np.nan, np.inf, -0.1, 1.1):
      with self.subTest(value=value), self.assertRaises(ValueError):
        m.threshold(np.array([value, 0.7]), np.array([False, True]), role='TRAIN')

  def test_normalizer_exact_constant(self):
    x, _ = fixture()
    x = np.column_stack((x, np.full(len(x), 0.1)))
    norm = m.normalizer(x, role='TRAIN', stage='STAGE1')
    self.assertTrue(norm['constant'][-1])
    self.assertEqual(norm['std'][-1], 0.0)
    self.assertEqual(m.transform(x, norm).shape[1], 3)
    self.assertTrue(np.all(m.transform(x, norm)[:, 0] == 1))

  def test_logistic_converges_and_is_repeatable(self):
    x, y = fixture()
    first = m.fit_stage1(x, y, role='TRAIN')
    second = m.fit_stage1(x, y, role='TRAIN')
    self.assertEqual(first['coefficients'].tobytes(), second['coefficients'].tobytes())
    self.assertLessEqual(first['convergence']['maxabs_gradient'], 1e-8)
    self.assertLessEqual(first['convergence']['updates'], 100)

  def test_support_before_solver(self):
    x, y = fixture()
    with patch.object(np.linalg, 'solve', side_effect=AssertionError('solver called')):
      with self.assertRaisesRegex(ValueError, 'CLASS'):
        m.fit_stage1(x, np.zeros_like(y), role='TRAIN')

  def test_rank_before_solver(self):
    x, y = fixture()
    x[:, 2] = x[:, 1]
    with patch.object(np.linalg, 'solve', side_effect=AssertionError('solver called')):
      with self.assertRaisesRegex(ValueError, 'RANK'):
        m.fit_stage1(x, y, role='TRAIN')

  def test_hessian_failure_no_fallback(self):
    x, y = fixture()
    with (
      patch.object(np.linalg, 'solve', side_effect=np.linalg.LinAlgError('singular')),
      patch.object(np.linalg, 'pinv', side_effect=AssertionError('fallback')),
      patch.object(np.linalg, 'lstsq', side_effect=AssertionError('fallback')),
    ):
      with self.assertRaisesRegex(ValueError, 'MOVE_GATE_NUMERICAL_FAILURE'):
        m.fit_stage1(x, y, role='TRAIN')

  def test_move_only_stage2(self):
    x, y = fixture()
    delta = np.where(y, x[:, 1] + 0.125, 0.0).astype(np.float64)
    model = m.fit_stage2(x, delta, role='TRAIN')
    np.testing.assert_array_equal(model['train_mask'], delta != 0)
    np.testing.assert_allclose(m.predict_delta(x[delta != 0], model), delta[delta != 0], atol=1e-12)

  def test_stage2_rank_failure_before_lstsq(self):
    x, y = fixture()
    x[:, 2] = x[:, 1]
    with patch.object(np.linalg, 'lstsq', side_effect=AssertionError('solver called')):
      with self.assertRaisesRegex(ValueError, 'RANK'):
        m.fit_stage2(x, np.where(y, 1.0, 0.0), role='TRAIN')

  def test_static_does_not_call_stage2(self):
    x, _ = fixture()
    with patch.object(m, 'probability', return_value=np.zeros(len(x))), patch.object(m, 'predict_delta', side_effect=AssertionError('static Stage2 call')):
      delta, projected, probability, gate = m.integrated(x, np.ones(len(x), dtype=np.int64), {}, 1.0, {})
    self.assertFalse(gate.any())
    self.assertTrue(np.all(delta == 0))
    self.assertTrue(np.all(projected == 1))

  def test_move_does_not_force_tick(self):
    x, _ = fixture()
    with patch.object(m, 'probability', return_value=np.ones(len(x))), patch.object(m, 'predict_delta', return_value=np.full(len(x), 0.125)):
      delta, projected, _, gate = m.integrated(x, np.ones(len(x), dtype=np.int64), {}, 0.0, {})
    self.assertTrue(gate.all())
    self.assertTrue(np.all(projected == 1))
    self.assertTrue(np.all(delta == 0.125))

  def test_exact_half_projection(self):
    np.testing.assert_array_equal(m.project(np.array([0.5, 1.5, -1.5, -2.5])), [0, 2, -2, -2])

  def test_undefined_precision_retains_confusion(self):
    result = m.diagnostics(np.array([True, False]), np.array([False, False]))
    self.assertEqual(result['status'], 'STAGE1_DIAGNOSTIC_UNDEFINED')
    self.assertIsNone(result['precision'])
    self.assertEqual(result['FN'], 1)


class TestNewtonBoundaries(unittest.TestCase):
  def test_update_100_gets_final_gradient_check(self):
    x, y = np.ones((2, 1)), np.zeros(2)
    losses = [float(-i) for i in range(101) for _ in range(2)][1:202]
    probabilities = [np.ones(2)] * 100 + [np.zeros(2)]
    with (
      patch.object(m, 'loss', side_effect=losses),
      patch.object(m, 'sigmoid', side_effect=probabilities),
      patch.object(np.linalg, 'solve', return_value=np.ones(1)),
    ):
      beta, receipt = m.newton(x, y)
    self.assertEqual(receipt['updates'], 100)
    self.assertEqual(receipt['maxabs_gradient'], 0.0)
    self.assertEqual(beta[0], -100.0)

  def test_update_budget_nonconvergence(self):
    x, y = np.ones((2, 1)), np.zeros(2)
    losses = [float(-i) for i in range(101) for _ in range(2)][1:202]
    with (
      patch.object(m, 'loss', side_effect=losses),
      patch.object(m, 'sigmoid', return_value=np.ones(2)),
      patch.object(np.linalg, 'solve', return_value=np.ones(1)) as solve,
    ):
      with self.assertRaisesRegex(ValueError, 'NONCONVERGENCE'):
        m.newton(x, y)
      self.assertEqual(solve.call_count, 100)

  def test_twenty_first_trial_can_accept(self):
    with (
      patch.object(m, 'loss', side_effect=[0.0] + [1.0] * 20 + [-1.0, -1.0]),
      patch.object(m, 'sigmoid', side_effect=[np.ones(2), np.zeros(2)]),
      patch.object(np.linalg, 'solve', return_value=np.ones(1)),
    ):
      _, receipt = m.newton(np.ones((2, 1)), np.zeros(2))
    self.assertEqual(receipt['accepted_trial_exponents'], [20])

  def test_all_21_finite_trials_fail(self):
    with (
      patch.object(m, 'loss', side_effect=[0.0] + [1.0] * 21) as loss,
      patch.object(m, 'sigmoid', return_value=np.ones(2)),
      patch.object(np.linalg, 'solve', return_value=np.ones(1)),
    ):
      with self.assertRaisesRegex(ValueError, 'LINE_SEARCH_FAILURE'):
        m.newton(np.ones((2, 1)), np.zeros(2))
      self.assertEqual(loss.call_count, 22)

  def test_nonfinite_trial_stops_immediately(self):
    with (
      patch.object(m, 'loss', side_effect=[0.0, ValueError('HURDLE_NUMERICAL_FAILURE_NONFINITE'), -1.0]) as loss,
      patch.object(m, 'sigmoid', return_value=np.ones(2)),
      patch.object(np.linalg, 'solve', return_value=np.ones(1)),
    ):
      with self.assertRaisesRegex(ValueError, 'NUMERICAL_FAILURE'):
        m.newton(np.ones((2, 1)), np.zeros(2))
      self.assertEqual(loss.call_count, 2)

  def test_nonpositive_direction_rejected(self):
    with (
      patch.object(m, 'loss', return_value=0.0),
      patch.object(m, 'sigmoid', return_value=np.ones(2)),
      patch.object(np.linalg, 'solve', return_value=-np.ones(1)),
    ):
      with self.assertRaisesRegex(ValueError, 'NUMERICAL_FAILURE'):
        m.newton(np.ones((2, 1)), np.zeros(2))

  def test_no_solver_policy_override_arguments(self):
    x, y = fixture()
    for override in ({'warm_start': np.zeros(3)}, {'regularization': 1.0}, {'max_updates': 101}, {'damping': 1.0}):
      with self.subTest(override=list(override)), self.assertRaises(TypeError):
        m.fit_stage1(x, y, role='TRAIN', **override)

  def test_no_threshold_policy_override_arguments(self):
    for override in ({'development': [1.0]}, {'default_threshold': 0.5}, {'operator': '>='}, {'class_weight': 2.0}):
      with self.subTest(override=list(override)), self.assertRaises(TypeError):
        m.threshold(np.array([0.2, 0.8]), np.array([False, True]), role='TRAIN', **override)

  def test_stage2_rcond_none_and_separate_normalizer(self):
    x, y = fixture()
    delta = np.where(y, x[:, 1] + 0.125, 0.0)
    original = np.linalg.lstsq
    with patch.object(np.linalg, 'lstsq', wraps=original) as solve:
      second = m.fit_stage2(x, delta, role='TRAIN')
    self.assertIsNone(solve.call_args.kwargs['rcond'])
    expected = m.normalizer(x[delta != 0], role='TRAIN', stage='STAGE2')
    np.testing.assert_array_equal(second['normalizer']['mean'], expected['mean'])

  def test_bad_rows_rejected_not_dropped(self):
    x, y = fixture()
    x[0, 1] = np.nan
    with self.assertRaisesRegex(ValueError, 'NONFINITE'):
      m.fit_stage1(x, y, role='TRAIN')
    with self.assertRaisesRegex(ValueError, 'NONFINITE'):
      m.fit_stage2(x, np.where(y, 1.0, 0.0), role='TRAIN')
