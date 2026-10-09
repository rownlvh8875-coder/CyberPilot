"""Constructed target fixtures, never actual vehicle measurements."""
import copy
from pathlib import Path
import tempfile
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune.tests.test_camera_calibration_evidence import fixture
try:
  from openpilot.tools.cyber_autotune import stationary_target_calibration as t
except ImportError:
  t = None


def capture():
  m, i = fixture()
  r, center, _, _ = c.pose(m)
  # Target x points vehicle-right, target y down, normal points vehicle-forward.
  tr = c.BASE_ROTATION
  origin = np.array([5., .45, 1.7])
  points = np.array([[0., 0., 0.], [.6, 0., 0.], [0., .2, 0.], [.6, .2, 0.], [0., .4, 0.], [.6, .4, 0.]])
  world = points @ tr.T + origin
  cam = (world - center) @ r
  uv = cam @ np.array(i['matrix']).T
  uv = uv[:, :2] / uv[:, 2:]
  d = {
    'schema': 'STATIONARY_TARGET_CAPTURE_V1', 'scope': 'TEST_ONLY',
    'camera': m['camera'], 'intrinsics_sha256': i['receipt_sha256'],
    'image_sha256': 'a' * 64, 'image_wh': i['resolution_wh'],
    'target': {'width_m': .6, 'height_m': .4, 'dimension_bound_m': .001, 'planarity_bound_m': .001,
               'source_sha256': 'b' * 64, 'rotation_target_to_vehicle': tr.tolist(),
               'origin_vehicle_m': origin.tolist(), 'placement_translation_bound_m': [.001] * 3,
               'placement_rotation_bound_rad': [.001] * 3, 'placement_evidence_sha256': 'c' * 64},
    'corners_px': uv.tolist(), 'corner_bound_px': .5,
    'height_repeats_m': [float(center[2])] * 3, 'height_absolute_bound_m': .01,
    'height_evidence_sha256': 'd' * 64, 'ground_evidence_sha256': 'e' * 64,
    'ground_slope_bound_rad': .001, 'operator_id_sha256': 'f' * 64, 'timestamp': m['timestamp'],
    'provenance_role': 'INDEPENDENT_TARGET_OBSERVATION',
    'model_outputs_used': False, 'candidate_outputs_used': False,
    'physical_observation_acknowledged': True, 'distortion_state': 'DISTORTION_UNVERIFIED',
  }
  return d, i, r, center


class TestStationaryTarget(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(t, 'stationary target software missing')

  def test_target_measured_dimensions_not_nominal_print(self):
    pts = t.object_points(.6, .4)
    np.testing.assert_allclose(pts[-1], [.6, .4, 0])
    np.testing.assert_allclose(t.object_points(1.2, .8), pts * 2)
    self.assertIn('NOT PHYSICAL TRUTH', t.target_sheet())

  def test_height_repeats_preserve_spread_not_instrument_uncertainty(self):
    x = t.height_summary([1.4, 1.41, 1.39], .03)
    self.assertAlmostEqual(x['spread_m'], .02)
    self.assertEqual(x['declared_absolute_bound_m'], .03)
    with self.assertRaises(ValueError):
      t.height_summary([1.4, 1.41], None)
    with self.assertRaises(ValueError):
      t.height_summary([1.4, 1.5], .01)

  def test_known_pose_original_pixel_sign_conventions(self):
    d, i, r, center = capture()
    out = t.solve(d, i)
    np.testing.assert_allclose(out['camera_to_vehicle'], r, atol=1e-7)
    np.testing.assert_allclose(out['camera_center_vehicle_m'], center, atol=1e-7)
    self.assertLess(out['reprojection_max_px'], 1e-7)
    self.assertAlmostEqual(out['orientation_rad']['pitch_rad'], .04, places=7)
    self.assertAlmostEqual(out['orientation_rad']['roll_rad'], .01, places=7)
    self.assertAlmostEqual(out['orientation_rad']['yaw_rad'], .02, places=7)
    self.assertEqual(out['status'], 'CALIBRATION_SOLVED')
    self.assertFalse(out['qualification_allowed'])
    self.assertEqual(out['independent_validation'], 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING')

  def test_no_defaults_missing_uncertainty_or_provenance(self):
    d, i, _, _ = capture()
    for key in ('height_absolute_bound_m', 'ground_evidence_sha256', 'corner_bound_px'):
      bad = copy.deepcopy(d)
      bad.pop(key)
      with self.assertRaises(ValueError):
        t.solve(bad, i)

  def test_model_and_candidate_contamination_rejected(self):
    d, i, _, _ = capture()
    for change in ('model_outputs_used', 'candidate_outputs_used'):
      bad = copy.deepcopy(d)
      bad[change] = True
      with self.assertRaises(ValueError):
        t.solve(bad, i)
    d['provenance_role'] = 'MODEL_DERIVED_LIVECALIBRATION'
    with self.assertRaises(ValueError):
      t.solve(d, i)

  def test_height_resolution_image_binding(self):
    d, i, _, _ = capture()
    for change in ('height_repeats_m', 'image_wh', 'intrinsics_sha256'):
      bad = copy.deepcopy(d)
      bad[change] = [2., 2., 2.] if change == 'height_repeats_m' else [526, 330] if change == 'image_wh' else '0' * 64
      with self.assertRaises(ValueError):
        t.solve(bad, i)

  def test_degenerate_and_nonfinite_target_rejected(self):
    d, i, _, _ = capture()
    for corners in ([[100., 100.]] * 6, [[float('nan'), 2.]] * 6):
      d['corners_px'] = corners
      with self.assertRaises(ValueError):
        t.solve(d, i)

  def test_reprojection_bad_corner_rejected(self):
    d, i, _, _ = capture()
    d['corners_px'][2][0] += 30
    with self.assertRaises(ValueError):
      t.solve(d, i)

  def test_target_axis_swap_and_left_handed_rejected(self):
    d, i, _, _ = capture()
    d['target']['rotation_target_to_vehicle'][0][2] = -1
    with self.assertRaises(ValueError):
      t.solve(d, i)

  def test_reversed_corner_labels_cannot_solve_rear_facing_road_camera(self):
    d, i, _, _ = capture()
    d['corners_px'] = [d['corners_px'][n] for n in (1, 0, 3, 2, 5, 4)]
    with self.assertRaises(ValueError):
      t.solve(d, i)

  def test_repeat_consistency_not_validation(self):
    d, i, _, _ = capture()
    a = t.solve(d, i)
    b = copy.deepcopy(d)
    b['image_sha256'] = '1' * 64
    other = t.solve(b, i)
    x = t.repeat_consistency([a, other], .01, .001, 'a' * 64)
    self.assertTrue(x['within_declared_comparison_bounds'])
    self.assertFalse(x['independent_calibration_validated'])

  def test_duplicate_capture_cannot_prove_repeat_consistency(self):
    d, i, _, _ = capture()
    a = t.solve(d, i)
    with self.assertRaises(ValueError):
      t.repeat_consistency([a, a], .01, .001, 'a' * 64)

  def test_capture_private_immutable_no_false_admission(self):
    d, i, _, _ = capture()
    with tempfile.TemporaryDirectory() as root:
      session = t.CaptureSession(Path(root) / 'capture', scope='TEST_ONLY')
      self.assertEqual(session.state()['status'], 'CALIBRATION_MEASUREMENT_PENDING')
      session.save_draft(d)
      session.save_draft(d)
      # Source bytes must match image SHA, so synthetic test cannot pretend unrelated bytes are the capture.
      with self.assertRaises(ValueError):
        session.freeze(d, i, b'unrelated')
      self.assertFalse((session.root / 'capture.json').exists())

  def test_pose_result_cannot_enter_existing_admission(self):
    d, i, _, _ = capture()
    out = t.solve(d, i)
    self.assertEqual(c.admit(out, i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')


if __name__ == '__main__':
  unittest.main()
