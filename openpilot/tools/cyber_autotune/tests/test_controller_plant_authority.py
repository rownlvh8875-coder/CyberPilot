import math
import unittest

from openpilot.tools.cyber_autotune import controller_plant_authority as a


class TestAuthorityMath(unittest.TestCase):
  def test_arc_zero(self):
    self.assertEqual(a.arc(0., 20.), {'heading_rad': 0., 'pose_x_m': 20., 'pose_y_m': 0.})

  def test_arc_left_right(self):
    left, right = a.arc(.01, 30.), a.arc(-.01, 30.)
    self.assertGreater(left['pose_y_m'], 0.)
    self.assertEqual(left['pose_y_m'], -right['pose_y_m'])
    self.assertEqual(left['pose_x_m'], right['pose_x_m'])

  def test_arc_heading_radians(self):
    self.assertAlmostEqual(a.arc(.01, 20.)['heading_rad'], .2)
    self.assertNotAlmostEqual(a.arc(.01, 20.)['heading_rad'], math.degrees(.2))

  def test_oracle_dt_convergence(self):
    coarse, fine = a.oracle(.01, 10., 2., .01), a.oracle(.01, 10., 2., .005)
    self.assertLess(fine['position_error_m'], coarse['position_error_m'])
    self.assertTrue(coarse['within_riemann_bound'])

  def test_oracle_negative(self):
    self.assertAlmostEqual(a.oracle(.01, 10., 2., .01)['discrete']['pose_y_m'],
                           -a.oracle(-.01, 10., 2., .01)['discrete']['pose_y_m'])

  def test_oracle_zero(self):
    row = a.oracle(0., 10., 2., .01)
    self.assertLessEqual(row['position_error_m'], row['roundoff_allowance_m'])

  def test_integrals_zero(self):
    self.assertIsNone(a.signal([0., 0.], .01)['cancellation_ratio'])

  def test_cancellation(self):
    row = a.signal([1., -1., 1., -1.], .01)
    self.assertEqual(row['signed_integral'], 0.)
    self.assertEqual(row['absolute_integral'], .04)
    self.assertEqual(row['cancellation_ratio'], 1.)
    self.assertEqual(row['sign_changes'], 3)

  def test_ratio_zero_explicit(self):
    self.assertEqual(a.ratio(1., 0.), {'value': None, 'status': 'ZERO_DENOMINATOR'})
    self.assertEqual(a.ratio(0., 1.)['value'], 0.)

  def test_ratio_no_epsilon(self):
    self.assertEqual(a.ratio(1e-20, 1e-20)['value'], 1.)

  def test_nonfinite(self):
    with self.assertRaises(ValueError):
      a.signal([float('nan')], .01)

  def test_raw_torque_rejected(self):
    with self.assertRaises(ValueError):
      a.command(384., 'NORMALIZED_TORQUE')

  def test_wrong_unit_rejected(self):
    with self.assertRaises(ValueError):
      a.command(.2, 'RAW_TORQUE')

  def test_normalized_command(self):
    self.assertEqual(a.command(-.2, 'NORMALIZED_TORQUE'), -.2)

  def test_no_extrapolation(self):
    samples = [{'pose_x_m': 1., 'pose_y_m': 0.}, {'pose_x_m': 2., 'pose_y_m': 1.}]
    self.assertIsNone(a.query(samples, 3.))
    self.assertEqual(a.query(samples, 1.5)['pose_y_m'], .5)

  def test_firewall(self):
    row = a.seal({'schema': 'TEST', 'qualification_allowed': True})
    self.assertFalse(row['qualification_allowed'])
    self.assertIsNone(row['total_physical_bound_m'])
    self.assertEqual(row['sealed_reference_status'], 'NOT_GENERATED')

  def test_near_zero_arc(self):
    self.assertAlmostEqual(a.arc(1e-12, 20.)['pose_y_m'], 2e-10)

  def test_degenerate_inputs(self):
    for dt in (0., -.01, float('inf')):
      with self.assertRaises(ValueError):
        a.signal([1.], dt)
