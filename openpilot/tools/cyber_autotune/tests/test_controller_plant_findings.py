import unittest
from openpilot.tools.cyber_autotune import controller_plant_findings as f


class TestAuthorityFindings(unittest.TestCase):
  def test_scalar_gain_units(self):
    row = f.transfer_gains(.92, .004, .01)
    self.assertAlmostEqual(row['dc_curvature_gain'], .05)
    self.assertAlmostEqual(row['nyquist_curvature_gain'], .004 / 1.92)
    self.assertLess(row['nyquist_curvature_gain'], row['dc_curvature_gain'])

  def test_yaw_filter_semantics(self):
    self.assertIn('RESIDUAL', f.CHAIN[6]['semantics'])

  def test_raw_stage_not_executed(self):
    self.assertFalse(f.CHAIN[3]['executed_in_historical_harness'])
    self.assertIn('384', f.CHAIN[3]['semantics'])

  def test_sign_chain(self):
    self.assertIn('-requested', f.CHAIN[4]['semantics'])
    self.assertIn('-curvature', f.CHAIN[6]['semantics'])

  def test_no_physical_gain_claim(self):
    row = f.transfer_gains(.92, .004, .01)
    self.assertEqual(row['scope'], 'DESCRIPTIVE_DISCRETE_TRANSFER_ONLY')

  def test_dt_transfer_pole(self):
    row = f.transfer_gains(.92, .004, .01)
    other = f.transfer_gains(.92, .004, .005)
    self.assertAlmostEqual(row['pole_time_constant_s'], 2 * other['pole_time_constant_s'])

  def test_invalid_pole(self):
    with self.assertRaises(ValueError):
      f.transfer_gains(1., .004, .01)

  def test_desired_curvature_geometric_sign(self):
    self.assertIn('controller k=-geometric k', f.CHAIN[0]['semantics'])
