import unittest
import numpy as np
from importlib import import_module


class TestS2RIGrid(unittest.TestCase):
  def module(self):
    return import_module('openpilot.tools.cyber_autotune.empirical_s2_ri_math')

  def test_all_source_codes_exact(self):
    m = self.module()
    codes = np.arange(-32768, 32768, dtype=np.int64)
    values = (codes*.1).astype(np.float32).astype(np.float64)
    ticks, good = m.grid_ticks(values)
    np.testing.assert_array_equal(ticks, codes)
    self.assertTrue(good.all())

  def test_no_blind_rounding(self):
    ticks, good = self.module().grid_ticks(np.array([.11, np.nan, np.inf, 4000., -.15]))
    self.assertFalse(good.any())
    self.assertTrue((ticks == 0).all())  # invalid sentinel never admitted

  def test_signed_delta(self):
    m = self.module()
    data = {'tick': np.array([-2, -2, 0, -1]), 'streak': np.arange(1, 5)}
    ids = m.target_indices(data)
    np.testing.assert_array_equal(ids, [0, 1, 2])
    np.testing.assert_array_equal(data['tick'][ids+1]-data['tick'][ids], [0, 2, -1])

  def test_target_run_end(self):
    ids = self.module().target_indices({'streak': np.array([1, 2, 1, 0, 1])})
    np.testing.assert_array_equal(ids, [0])

  def test_past_delta_not_target(self):
    m = self.module()
    data = {'tick': np.array([1, 3, 6, 100]), 'command': np.arange(4.)/10,
            'speed': np.ones(4)*12, 'streak': np.arange(1, 5)}
    x, names = m.feature_matrix(data, np.array([2]), (0, 1, 1))
    self.assertEqual(names, ['intercept', 'command_offset_0', 'past_increment_1', 'angle_tick_k', 'speed_k'])
    np.testing.assert_array_equal(x, [[1, .2, 3, 6, 12]])
    data['tick'][3] = -200
    np.testing.assert_array_equal(m.feature_matrix(data, np.array([2]), (0, 1, 1))[0], x)

  def test_no_padding(self):
    m = self.module()
    data = {'tick': np.arange(4), 'command': np.arange(4.), 'speed': np.ones(4), 'streak': np.arange(1, 5)}
    with self.assertRaisesRegex(ValueError, 'HISTORY'):
      m.feature_matrix(data, np.array([0]), (0, 1, 1))

  def test_form_search_rejected(self):
    with self.assertRaisesRegex(ValueError, 'BOUNDARY'):
      self.module().feature_matrix({}, np.array([], dtype=int), (1, 2, 3))

  def test_rate_overlay_ignored(self):
    m = self.module()
    d = {'tick': np.arange(4), 'command': np.arange(4.), 'speed': np.ones(4), 'streak': np.arange(1, 5)}
    expected = m.feature_matrix(d, np.array([2]), (0, 1, 1))[0]
    for value in (np.full(4, np.nan), np.arange(4.)+999):
      np.testing.assert_array_equal(m.feature_matrix({**d, 'state.rate': value}, np.array([2]), (0, 1, 1))[0], expected)

  def test_every_boundary_form_shape(self):
    m = self.module()
    d = {'tick': np.arange(100), 'command': np.arange(100.)/100, 'speed': np.ones(100), 'streak': np.arange(1, 101)}
    for form in m.FORMS:
      with self.subTest(form=form):
        ids = m.feature_indices(d, form)
        x, names = m.feature_matrix(d, ids, form)
        self.assertEqual(x.shape, (100-m.history_required(form), 3+form[1]+form[2]))
        self.assertEqual(len(names), x.shape[1])
        self.assertLess(ids.max(), 99)

  def test_off_grid_float64_not_float32_source(self):
    _, good = self.module().grid_ticks(np.array([.1, float(np.float32(.1))]))
    np.testing.assert_array_equal(good, [False, True])

  def test_overflow_never_cast(self):
    with np.errstate(over='ignore'):
      _, good = self.module().grid_ticks(np.array([1e300, -1e300]))
    self.assertFalse(good.any())

  def test_feature_invalid_indices(self):
    m = self.module()
    d = {'tick': np.arange(4), 'command': np.arange(4.), 'speed': np.ones(4), 'streak': np.arange(1, 5)}
    for ids in (np.array([-1]), np.array([4]), np.array([1.5])):
      with self.subTest(ids=str(ids)), self.assertRaises(ValueError):
        m.feature_matrix(d, ids, (0, 1, 1))

  def test_break_drops_all_history(self):
    m = self.module()
    d = {'streak': np.array([1, 2, 3, 0, 1, 2, 3])}
    np.testing.assert_array_equal(m.feature_indices(d, (0, 1, 1)), [1, 5])

  def test_target_independent_rank_no_fit(self):
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune.empirical_identifiability_math import rank_diagnostic
    x = np.array([[1., 0.], [1., 1.], [1., 2.]])
    with patch.object(np.linalg, 'lstsq', side_effect=AssertionError('NO_FIT')), patch.object(np, 'polyfit', side_effect=AssertionError('NO_FIT')):
      result = rank_diagnostic(x, ['intercept', 'angle_tick_k'])
    self.assertEqual(result['numerical_rank'], 2)
    self.assertFalse(result['fitting_admission'])
