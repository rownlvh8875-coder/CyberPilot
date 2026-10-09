import copy
import unittest

from openpilot.tools.cyber_autotune import controller_plant_experiment as e
from openpilot.tools.cyber_autotune import curvature_yaw_screening as s


class TestPlantExperiment(unittest.TestCase):
  def run_trace(self, amplitude=.01, speed=17.5, mode='STEP'):
    return e.run_input(s.PLANT, s.RESET, speed, amplitude, mode, 401)

  def test_positive_control(self):
    row = self.run_trace()
    self.assertGreater(row['samples'][-1]['pose_y_m'], 0.)
    self.assertTrue(row['analytic_recurrence_agrees'])

  def test_negative_control(self):
    a, b = self.run_trace(0.), self.run_trace(0.)
    self.assertEqual(a, b)
    self.assertEqual(a['samples'][-1]['pose_y_m'], 0.)

  def test_mirror(self):
    left, right = self.run_trace(.01), self.run_trace(-.01)
    for x, y in zip(left['samples'], right['samples'], strict=True):
      self.assertEqual(x['pose_y_m'], -y['pose_y_m'])
      self.assertEqual(x['pose_x_m'], y['pose_x_m'])

  def test_delay(self):
    row = self.run_trace()['samples']
    self.assertEqual([x['applied_normalized_torque'] for x in row[:2]], [0., 0.])
    self.assertEqual(row[2]['applied_normalized_torque'], .01)

  def test_steady_gain(self):
    r = self.run_trace()
    self.assertAlmostEqual(r['samples'][-1]['curvature_1pm'] / -.01, e.dc_gain(s.PLANT, 17.5), places=12)

  def test_gain_determinism(self):
    self.assertEqual(self.run_trace(), self.run_trace())

  def test_raw_amplitude(self):
    with self.assertRaises(ValueError):
      self.run_trace(384.)

  def test_invalid_mode(self):
    with self.assertRaises(ValueError):
      self.run_trace(mode='SEARCH')

  def test_reset_immutable(self):
    original = copy.deepcopy(s.RESET)
    self.run_trace()
    self.assertEqual(s.RESET, original)

  def test_ramp(self):
    row = self.run_trace(mode='RAMP')['samples']
    self.assertEqual(row[0]['requested_torque'], 0.)
    self.assertEqual(row[-1]['requested_torque'], .01)

  def test_unknown_speed(self):
    with self.assertRaises(ValueError):
      self.run_trace(speed=100.)

  def test_independent_oracle_rejects_changed_gain(self):
    changed = copy.deepcopy(s.PLANT)
    changed['command_gain_1pm'] = float('nan')
    with self.assertRaises(ValueError):
      e.run_input(changed, s.RESET, 17.5, .01, 'STEP', 401)

  def test_original_geometry_oracle(self):
    row = e.original_geometry_oracle(s.PLANT, .001, 17.5, 401)
    self.assertTrue(row['within_discrete_bound'])
    self.assertGreater(row['actual']['pose_y_m'], 0.)

  def test_original_geometry_sign(self):
    left = e.original_geometry_oracle(s.PLANT, .001, 17.5, 401)
    right = e.original_geometry_oracle(s.PLANT, -.001, 17.5, 401)
    self.assertEqual(left['actual']['pose_y_m'], -right['actual']['pose_y_m'])

  def test_original_geometry_defect_detected(self):
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import curvature_yaw_v2_search as old
    actual = old.plant_trace
    def wrong(*args):
      rows = actual(*args)
      for row in rows:
        row['pose_y_m'] *= -1
      return rows
    with patch.object(old, 'plant_trace', side_effect=wrong):
      self.assertFalse(e.original_geometry_oracle(s.PLANT, .001, 17.5, 401)['within_discrete_bound'])

  def test_reverse_forward_basis(self):
    row = self.run_trace(.3927772509070631, 25.)
    from openpilot.tools.cyber_autotune import controller_plant_authority as a
    self.assertEqual(a.query_status(row['samples'], 5.), 'UNCOMPARABLE_COORDINATE_BASIS')

  def test_degrees_integration_defect_detected(self):
    import math
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import curvature_yaw_v2_search as old
    actual = old.plant_trace
    def wrong(*args):
      rows = actual(*args)
      for row in rows:
        row['heading_rad'] = math.degrees(row['heading_rad'])
      return rows
    with patch.object(old, 'plant_trace', side_effect=wrong):
      self.assertFalse(e.original_geometry_oracle(s.PLANT, .001, 17.5, 401)['within_discrete_bound'])
