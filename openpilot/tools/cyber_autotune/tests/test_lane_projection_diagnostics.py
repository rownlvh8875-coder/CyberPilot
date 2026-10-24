import unittest
import numpy as np
from openpilot.tools.cyber_autotune import lane_projection_diagnostics as p


class TestLaneProjectionDiagnostics(unittest.TestCase):
  def geometry(self):
    return np.array([[1000.0, 0, 500], [0, 1000, 300], [0, 0, 1]]), np.array([[0.0, 0, 1], [-1, 0, 0], [0, -1, 0]]), np.array([0.0, 0, 1.0])

  def test_ground_ray_axis_and_distance_sensitivity(self):
    k, r, c = self.geometry()
    result = p.ground_projection(k, r, c, (600.0, 350.0))
    self.assertAlmostEqual(result['forward_m'], 20.0)
    self.assertAlmostEqual(result['lateral_left_m'], -2.0)
    self.assertEqual(result['scope'], 'DIAGNOSTIC_GEOMETRY_ONLY_NOT_REFERENCE')
    self.assertAlmostEqual(result['jacobian']['u_px'], -0.02)
    self.assertAlmostEqual(result['jacobian']['v_px'], 0.04)

  def test_pixel_and_intrinsic_jacobian_matches_finite_difference(self):
    k, r, c = self.geometry()
    uv = np.array([600.0, 350.0])
    base = p.ground_projection(k, r, c, uv)
    for key, axis in [('u_px', 0), ('v_px', 1)]:
      plus = uv.copy()
      minus = uv.copy()
      plus[axis] += 0.001
      minus[axis] -= 0.001
      derivative = (p.ground_projection(k, r, c, plus)['lateral_left_m'] - p.ground_projection(k, r, c, minus)['lateral_left_m']) / 0.002
      self.assertAlmostEqual(base['jacobian'][key], derivative, places=7)
    for key, i, j in [('fx_px', 0, 0), ('fy_px', 1, 1), ('cx_px', 0, 2), ('cy_px', 1, 2)]:
      plus = k.copy()
      minus = k.copy()
      plus[i, j] += 0.001
      minus[i, j] -= 0.001
      derivative = (p.ground_projection(plus, r, c, uv)['lateral_left_m'] - p.ground_projection(minus, r, c, uv)['lateral_left_m']) / 0.002
      self.assertAlmostEqual(base['jacobian'][key], derivative, places=7)

  def test_horizon_behind_camera_bad_intrinsics_and_rotation_rejected(self):
    k, r, c = self.geometry()
    for kk, rr, cc, uv in (
      (k, r, c, (500.0, 300.0)),
      (k, r, c, (500.0, 250.0)),
      (k, r, [0, 0, -1], (500.0, 350.0)),
      (k, np.eye(3) * 2, c, (500.0, 350.0)),
      (k, r, c, (float('nan'), 350.0)),
    ):
      with self.subTest(uv=uv):
        with self.assertRaises(ValueError):
          p.ground_projection(kk, rr, cc, uv)
    k[0, 0] = 0
    with self.assertRaises(ValueError):
      p.ground_projection(k, r, c, (500.0, 350.0))

  def test_missing_uncertainty_never_zero_filled_or_promoted(self):
    k, r, c = self.geometry()
    result = p.ground_projection(k, r, c, (600.0, 350.0))
    report = p.first_order_budget(result['jacobian'], None)
    self.assertEqual(report['status'], 'BLOCKED')
    self.assertIsNone(report['detector_error_m'])
    self.assertIsNone(report['total_conservative_uncertainty_m'])
    self.assertFalse(report['reference_promotable'])

  def test_first_order_budget_explicitly_not_conservative_certification(self):
    k, r, c = self.geometry()
    jac = p.ground_projection(k, r, c, (600.0, 350.0))['jacobian']
    bounds = dict.fromkeys(jac, 0.0)
    bounds['u_px'] = 2.0
    bounds['camera_height_m'] = 0.01
    report = p.first_order_budget(jac, bounds)
    self.assertAlmostEqual(report['detector_error_m'], 0.04)
    self.assertAlmostEqual(report['calibration_error_m'], 0.02)
    self.assertIsNone(report['projection_error_m'])
    self.assertIsNone(report['total_conservative_uncertainty_m'])
    self.assertEqual(report['status'], 'BLOCKED')
    for invalid in ({'u_px': 2.0}, dict(bounds, u_px=-1.0), dict(bounds, u_px=True), dict(bounds, u_px=float('inf'))):
      with self.assertRaises(ValueError):
        p.first_order_budget(jac, invalid)

  def test_nominal_distance_table_is_not_meter_accuracy(self):
    table = p.nominal_sensitivity(2648.0, (5.0, 10.0, 20.0, 30.0))
    self.assertAlmostEqual(table['rows'][2]['absolute_lateral_sensitivity_m_per_px'], 20 / 2648)
    self.assertEqual(table['scope'], 'ALIGNED_PINHOLE_SENSITIVITY_NOT_MEASURED_ERROR')
    self.assertIsNone(table['measured_meter_error'])
    self.assertFalse(table['reference_promotable'])

  def test_unknown_jacobian_keys_and_nonfinite_nominal_sensitivity_rejected(self):
    with self.assertRaises(ValueError):
      p.first_order_budget({'fake': 1.0}, {'fake': 1.0})
    with self.assertRaises(ValueError):
      p.nominal_sensitivity(1e-300, (1e300,))

  def test_rotation_jacobian_matches_world_left_perturbation(self):
    k, r, c = self.geometry()
    uv = (600.0, 350.0)
    result = p.ground_projection(k, r, c, uv)
    angle = 1e-5
    for key, axis in [('roll_world_x_rad', 0), ('pitch_world_y_rad', 1), ('yaw_world_z_rad', 2)]:

      def rotation(a, rotation_axis=axis):
        direction = np.eye(3)[rotation_axis]
        x, y, z = direction
        skew = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
        return np.eye(3) + np.sin(a) * skew + (1 - np.cos(a)) * (skew @ skew)

      derivative = (
        p.ground_projection(k, rotation(angle) @ r, c, uv)['lateral_left_m'] - p.ground_projection(k, rotation(-angle) @ r, c, uv)['lateral_left_m']
      ) / (2 * angle)
      self.assertAlmostEqual(result['jacobian'][key], derivative, places=4)
