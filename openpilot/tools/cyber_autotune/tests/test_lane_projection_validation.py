import unittest

import numpy as np

from openpilot.tools.cyber_autotune import lane_projection_validation as v


class TestKnownCameraProjectionValidation(unittest.TestCase):
  def geometry(self):
    k = np.array([[1341.684118, 0, 1437.123805], [0, 1348.879723, 973.23026], [0, 0, 1]])
    r = np.array([[0., 0., 1.], [-1., 0., 0.], [0., -1., 0.]])
    c = np.array([0., 0., 1.213])
    return k, r, c

  def test_forward_back_known_points_and_five_sensitivities(self):
    k, r, c = self.geometry()
    report = v.distance_validation(k, r, c, [5., 10., 20., 30.], 1.5)
    self.assertEqual(len(report['rows']), 4)
    for row in report['rows']:
      self.assertLess(row['forward_back_error_m'], 1e-10)
      self.assertLess(row['maximum_jacobian_difference'], 1e-5)
      self.assertEqual(set(row['sensitivities']), {'u_px', 'fx_px', 'pitch_world_y_rad', 'camera_height_m', 'roll_world_x_rad'})
      self.assertAlmostEqual(row['sensitivities']['u_px']['analytic'], -row['distance_m'] / k[0, 0])
    self.assertFalse(report['reference_promotable'])
    self.assertIsNone(report['total_conservative_uncertainty_m'])

  def test_rotated_rig_signs_are_not_assumed_level(self):
    k, r, c = self.geometry()
    angle = .04
    roll = np.array([[1., 0., 0.], [0., np.cos(angle), -np.sin(angle)], [0., np.sin(angle), np.cos(angle)]])
    report = v.distance_validation(k, roll @ r, c, [5., 10., 20., 30.], -1.5)
    for row in report['rows']:
      self.assertLess(row['maximum_jacobian_difference'], 1e-5)
    self.assertEqual(report, v.distance_validation(k, roll @ r, c, [5., 10., 20., 30.], -1.5))

  def test_invalid_and_model_derived_calibration_cannot_be_certified(self):
    k, r, c = self.geometry()
    for distances in ([], [0.], [float('nan')], [True]):
      with self.subTest(distances=distances), self.assertRaises(ValueError):
        v.distance_validation(k, r, c, distances, 1.5)
    self.assertEqual(v.calibration_blockers()['CAMERA_EXTRINSICS_MODEL_DERIVED']['status'], 'BLOCKED')
    self.assertEqual(v.calibration_blockers()['CAMERA_INTRINSICS_AVAILABLE']['status'], 'NOMINAL_ONLY')
    self.assertNotEqual(v.calibration_blockers()['CAMERA_HEIGHT_UNVERIFIED']['effect'], v.calibration_blockers()['CAMERA_MOUNT_PITCH_UNVERIFIED']['effect'])
