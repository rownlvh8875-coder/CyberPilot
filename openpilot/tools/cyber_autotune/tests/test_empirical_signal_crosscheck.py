import importlib.util
import math
import unittest
import numpy as np


class TestYawCrosscheck(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_signal_crosscheck'), 'yaw crosscheck missing')
    from openpilot.tools.cyber_autotune import empirical_signal_crosscheck as c

    self.c = c
    self.profile = {'wheelbase': 2.0, 'steer_ratio': 10.0}

  def segment(self, n=700):
    # Exact known signed source: ESP yaw degrees/s, device x radians/s.
    rows = []
    options = {str(l): [] for l in [0, 1, 2, 5, 10, 20]}
    for i in range(n):
      yaw = 0.05 * math.sin(i * 0.03)
      angle = math.degrees(math.atan(yaw * 2.0 / 10.0)) * 10.0
      rows.append(
        {
          'state_time_ns': i * 10_000_000,
          'grid_time_ns': i * 10_000_000,
          'angle_deg': angle,
          'speed_mps': 10.0,
          'yaw_raw': math.degrees(yaw),
          'diagnostic_valid': True,
          'gyro_common_valid': True,
          'speed_bin': 'LOW',
        }
      )
      for lag in options:
        options[lag].append([yaw, 0.003 * math.cos(i * 0.02), 0.002 * math.sin(i * 0.07)])
    return {'segment_id': 'a' * 64, 'aligned': {'rows': rows, 'gyro_options': options}}

  def test_kinematic_units_and_sign(self):
    self.assertAlmostEqual(self.c.kinematic(100.0, 10.0, 2.0, 10.0), 5.0 * math.tan(math.radians(10.0)))
    self.assertLess(self.c.kinematic(-100.0, 10.0, 2.0, 10.0), 0.0)

  def test_invalid_kinematic_geometry(self):
    with self.assertRaises(ValueError):
      self.c.kinematic(1.0, 10.0, 0.0, 10.0)

  def test_discrete_unit_recovery(self):
    x = self.c.select({'TRAIN': [self.segment()], 'DEVELOPMENT': [self.segment()]}, self.profile)
    self.assertEqual(x['hypothesis'], 'YAW_H1')
    self.assertEqual(x['gyro_candidate'], {'axis': 0, 'sign': 1, 'lag_samples': 0})
    self.assertTrue(x['unit_supported'])
    self.assertEqual(x['vehicle_frame'], 'DEVICE_AXIS_CORRESPONDENCE_ONLY')

  def test_sign_recovery_not_physical_frame(self):
    r = self.segment()
    for x in r['aligned']['rows']:
      x['yaw_raw'] *= -1
    z = self.c.select({'TRAIN': [r], 'DEVELOPMENT': [r]}, self.profile)
    self.assertEqual(z['hypothesis'], 'YAW_H2')
    self.assertFalse(z['vehicle_frame_calibrated'])

  def test_rad_hypothesis_negative_test(self):
    r = self.segment()
    for x in r['aligned']['rows']:
      x['yaw_raw'] = math.radians(x['yaw_raw'])
    z = self.c.select({'TRAIN': [r], 'DEVELOPMENT': [r]}, self.profile)
    self.assertEqual(z['hypothesis'], 'YAW_H3')

  def test_holdout_cannot_select(self):
    with self.assertRaises(ValueError):
      self.c.select({'TRAIN': [], 'DEVELOPMENT': [], 'YAW_HOLDOUT': []}, self.profile)

  def test_empty_support_unavailable(self):
    z = self.c.select({'TRAIN': [], 'DEVELOPMENT': []}, self.profile)
    self.assertFalse(z['unit_supported'])
    self.assertIsNone(z['hypothesis'])

  def test_common_mask_exclusion(self):
    r = self.segment()
    r['aligned']['rows'][5]['gyro_common_valid'] = False
    z = self.c.analyze([r], 'YAW_H1', {'axis': 0, 'sign': 1, 'lag_samples': 0}, self.profile)
    self.assertEqual(z['gyro']['count'], 699)
    self.assertEqual(z['coverage']['unavailable'], 1)

  def test_coverage_separate_from_error(self):
    r = self.segment()
    for x in r['aligned']['rows']:
      x['diagnostic_valid'] = False
    z = self.c.analyze([r], 'YAW_H1', {'axis': 0, 'sign': 1, 'lag_samples': 0}, self.profile)
    self.assertIsNone(z['gyro']['RMSE'])
    self.assertEqual(z['coverage']['unavailable'], 700)

  def test_no_arbitrary_axis_or_lag(self):
    with self.assertRaises(ValueError):
      self.c.analyze([self.segment()], 'YAW_H1', {'axis': 3, 'sign': 1, 'lag_samples': 0}, self.profile)

  def test_unknown_hypothesis_rejected(self):
    with self.assertRaises(ValueError):
      self.c.analyze([self.segment()], 'fitted scale', {'axis': 0, 'sign': 1, 'lag_samples': 0}, self.profile)

  def test_yaw_runs_gap_break(self):
    r = self.segment(100)
    r['aligned']['rows'][50]['gyro_common_valid'] = False
    runs = self.c.yaw_runs([r], 'YAW_H1', self.profile, 'LOW')
    self.assertEqual([len(x['y']) for x in runs], [50, 49])

  def test_yaw_input_is_measured_steering_speed(self):
    r = self.segment(100)
    runs = self.c.yaw_runs([r], 'YAW_H1', self.profile, 'LOW')
    np.testing.assert_allclose(runs[0]['u'], runs[0]['y'], atol=1e-16)

  def test_no_cross_segment_correlation(self):
    a = self.segment(3)
    b = self.segment(3)
    b['segment_id'] = 'b' * 64
    z = self.c.analyze([a, b], 'YAW_H1', {'axis': 0, 'sign': 1, 'lag_samples': 0}, self.profile)
    self.assertEqual(z['residual_autocorrelation']['1']['count'], 4)

  def test_repeatability(self):
    roles = {'TRAIN': [self.segment()], 'DEVELOPMENT': [self.segment()]}
    self.assertEqual(self.c.select(roles, self.profile), self.c.select(roles, self.profile))
