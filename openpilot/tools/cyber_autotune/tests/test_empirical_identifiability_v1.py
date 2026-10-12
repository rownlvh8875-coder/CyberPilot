import unittest
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_identifiability_math as m


class TestIdentifiabilityMath(unittest.TestCase):
  def data(self, n=60):
    a = np.arange(n, dtype=np.float64)
    return {'angle': a/10, 'rate': (a % 4)*4, 'command': (a % 7-3)/409,
            'raw': a % 7-3, 'request': a/100, 'speed': 10+a/100,
            'state_time': np.arange(n, dtype=np.int64)*10_000_000}

  def test_history_envelope_exact(self):
    self.assertEqual(m.HISTORIES, tuple(range(1, 46)))
    self.assertEqual(m.LAGS, tuple(range(21)))

  def test_streak_breaks_mask_run_and_grid(self):
    mask = np.array([1, 1, 0, 1, 1, 1], dtype=bool)
    runs = np.array([0, 0, 0, 0, 1, 1])
    within = np.array([0, 1, 2, 3, 0, 1])
    grid = np.array([0, 1, 2, 3, 4, 6])*10_000_000
    np.testing.assert_array_equal(m.streaks(mask, runs, within, grid), [1, 2, 0, 1, 1, 1])

  def test_history_never_crosses_segment(self):
    one = m.streaks(np.ones(2, bool), np.zeros(2, int), np.arange(2), np.arange(2)*10_000_000)
    np.testing.assert_array_equal(np.r_[one, one], [1, 2, 1, 2])

  def test_within_run_break(self):
    np.testing.assert_array_equal(m.streaks(np.ones(3, bool), np.zeros(3, int), np.array([0, 2, 3]),
                                                   np.arange(3)*10_000_000), [1, 1, 2])

  def test_s1_exact_layout(self):
    d = self.data()
    x, names = m.features(d, np.array([10, 11]), 'S1', 5)
    self.assertEqual(names, ['angle_k', 'rate_native_k', 'command_lag_5', 'speed_k', 'intercept'])
    np.testing.assert_array_equal(x[:, 2], d['command'][[5, 6]])
    np.testing.assert_array_equal(x[:, 0], d['angle'][[10, 11]])

  def test_s2_chronological_layout(self):
    d = self.data()
    x, names = m.features(d, np.array([10]), 'S2', 3)
    np.testing.assert_array_equal(x[0], np.r_[d['command'][8:11], d['angle'][8:11], d['rate'][10], d['speed'][10]])
    self.assertEqual(len(names), 8)

  def test_future_values_do_not_change_features(self):
    d = self.data()
    a = m.features(d, np.array([10]), 'S2', 3)[0]
    for v in d.values():
      v[11:] = 999
    np.testing.assert_array_equal(a, m.features(d, np.array([10]), 'S2', 3)[0])

  def test_invalid_layout_rejected(self):
    for family, parameter in [('S3', 1), ('S1', 21), ('S1', -1), ('S2', 0), ('S2', 46), ('S2', True)]:
      with self.subTest(family=family, parameter=parameter), self.assertRaises(ValueError):
        m.features(self.data(), np.array([50]), family, parameter)

  def test_negative_history_rejected(self):
    with self.assertRaises(ValueError):
      m.features(self.data(), np.array([1]), 'S2', 3)

  def test_rank_matches_numpy_documented_rule(self):
    x = np.array([[1, 2], [2, 0], [3, 2], [4, 1]], dtype=float)
    z = (x-x.mean(axis=0))/x.std(axis=0)
    r = m.rank_diagnostic(x, ['a', 'b'])
    self.assertEqual(r['numerical_rank'], np.linalg.matrix_rank(z))
    np.testing.assert_allclose(r['singular_values'], np.linalg.svd(z, compute_uv=False), rtol=0, atol=0)

  def test_constant_and_duplicate_columns(self):
    x = np.c_[np.arange(10), np.arange(10), np.ones(10)]
    r = m.rank_diagnostic(x, ['a', 'b', 'constant'])
    self.assertEqual(r['constant_columns'], ['constant'])
    self.assertIn(['a', 'b'], r['duplicate_columns'])
    self.assertEqual(r['numerical_rank'], 1)
    self.assertEqual(r['status'], 'RANK_DEFICIENT')

  def test_intercept_retained(self):
    r = m.rank_diagnostic(np.c_[np.arange(10), np.ones(10)], ['a', 'intercept'])
    self.assertEqual(r['numerical_rank'], 2)
    self.assertEqual(r['constant_columns'], ['intercept'])

  def test_empty_rank_is_unavailable(self):
    r = m.rank_diagnostic(np.empty((0, 2)), ['a', 'b'])
    self.assertIsNone(r['numerical_rank'])
    self.assertIsNone(r['condition_number'])

  def test_nonfinite_rank_rejected(self):
    with self.assertRaises(ValueError):
      m.rank_diagnostic(np.array([[1., np.nan]]), ['a', 'b'])

  def test_no_target_argument(self):
    with self.assertRaises(TypeError):
      m.rank_diagnostic(np.ones((3, 1)), ['a'], target=np.ones(3))

  def test_no_model_calls(self):
    with patch('numpy.linalg.lstsq', side_effect=AssertionError('FIT_FORBIDDEN')), patch('numpy.linalg.pinv', side_effect=AssertionError):
      r = m.rank_diagnostic(np.c_[np.arange(20, dtype=float), np.arange(20, dtype=float)**2], ['a', 'b'])
    self.assertEqual(r['numerical_rank'], 2)

  def test_repeatability(self):
    x = np.c_[np.arange(25, dtype=float), np.arange(25, dtype=float) % 4]
    self.assertEqual(m.rank_diagnostic(x, ['a', 'b']), m.rank_diagnostic(x, ['a', 'b']))

  def test_rank_is_report_only(self):
    r = m.rank_diagnostic(np.c_[np.arange(20, dtype=float), np.arange(20, dtype=float)**2], ['a', 'b'])
    self.assertEqual(r['conditioning_status'], 'CONDITION_NUMBER_REPORTED_NO_ACCEPTANCE_THRESHOLD')
    self.assertFalse(r['fitting_admission'])
    for key in ('coefficients', 'predictions', 'residuals', 'winner', 'loss'):
      self.assertNotIn(key, r)

  def test_delta_counts_only_run_local(self):
    d = self.data(5)
    r = m.target_diagnostic(d, np.array([0, 1, 3]))
    self.assertEqual(r['count'], 3)
    self.assertEqual(r['positive'], 3)
    self.assertNotIn('targets', r)

  def test_rate_diagnostic_never_proves_semantics(self):
    r = m.rate_diagnostic(self.data(6), np.arange(5))
    self.assertEqual(r['status'], 'EMPIRICAL_DIAGNOSTIC_ONLY_NOT_SOURCE_SEMANTIC_PROOF')
    self.assertFalse(r['source_semantics_promotable'])

  def test_constant_correlation_null(self):
    self.assertIsNone(m.correlation(np.ones(5), np.arange(5)))

  def test_support_gate_per_route(self):
    self.assertFalse(m.support_gate([1000, 200]))
    self.assertTrue(m.support_gate([201, 201]))
    self.assertFalse(m.support_gate([1000]))

  def test_no_selected_history_or_delay(self):
    self.assertNotIn('select', m.features.__code__.co_names)
    self.assertEqual(m.MIN_SUPPORT, 201)
