from dataclasses import FrozenInstanceError
import importlib
import importlib.util
import unittest

import numpy as np


class TestPixelLaneReference(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.pixel_lane_reference'
    self.assertIsNotNone(importlib.util.find_spec(name), 'pixel lane reference diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def synthetic_qcamera_frame() -> np.ndarray:
    rgb = np.zeros((330, 526, 3), dtype=np.uint8)
    y0, y1 = 185, 292

    def draw_lane(xt: float, xb: float):
      for y in range(y0, y1 + 1):
        x = int(round(xt + (xb - xt) * (y - y0) / (y1 - y0)))
        rgb[max(0, y - 1):min(rgb.shape[0], y + 2),
            max(0, x - 2):min(rgb.shape[1], x + 3)] = 255

    draw_lane(233, 160)
    draw_lane(319, 463)
    return rgb

  def test_detects_synthetic_perspective_lane_pair_without_model_input(self):
    api = self.api()
    rgb = self.synthetic_qcamera_frame()
    before = rgb.copy()

    result = api.detect_qcamera_lane_pair(rgb)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertLess(abs(result.center_x_px - 300.88317757009344), 4.0)
    self.assertLess(abs(result.lane_width_px - 238.10280373831776), 10.0)
    self.assertLess(result.left_x_px, result.center_x_px)
    self.assertLess(result.center_x_px, result.right_x_px)
    self.assertTrue(np.array_equal(rgb, before), 'detector mutated caller-owned pixels')
    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_blank_frame_fails_closed_instead_of_returning_geometry_only_pair(self):
    api = self.api()
    result = api.detect_qcamera_lane_pair(np.zeros((330, 526, 3), dtype=np.uint8))

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'INSUFFICIENT_LANE_SIGNAL')
    self.assertIsNone(result.center_x_px)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_frame_shape_and_dtype_are_exact_and_fail_closed(self):
    api = self.api()
    cases = (
      np.zeros((329, 526, 3), dtype=np.uint8),
      np.zeros((330, 525, 3), dtype=np.uint8),
      np.zeros((330, 526), dtype=np.uint8),
      np.zeros((330, 526, 3), dtype=np.float32),
    )
    for frame in cases:
      with self.subTest(shape=frame.shape, dtype=str(frame.dtype)):
        result = api.detect_qcamera_lane_pair(frame)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'INVALID_QCAMERA_FRAME')
        self.assertIsNone(result.center_x_px)

  def test_left_curve_comparison_reproduces_directional_decomposition(self):
    api = self.api()
    result = api.compare_projection_to_pixel_reference(
      pixel_lane_center_x_px=300.0,
      model_lane_center_x_px=302.0,
      model_path_x_px=294.0,
      desired_curvature_1pm=0.01,
    )

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.turn, 'LEFT')
    self.assertAlmostEqual(result.model_center_abs_error_px, 2.0)
    self.assertAlmostEqual(result.model_path_abs_error_px, 6.0)
    self.assertAlmostEqual(result.model_center_inside_pixel_center_px, -2.0)
    self.assertAlmostEqual(result.model_path_inside_pixel_center_px, 6.0)
    self.assertAlmostEqual(result.model_path_inside_model_center_px, 8.0)
    self.assertTrue(result.path_farther_from_pixel_center)
    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_right_curve_comparison_reproduces_directional_decomposition(self):
    api = self.api()
    result = api.compare_projection_to_pixel_reference(
      pixel_lane_center_x_px=300.0,
      model_lane_center_x_px=304.0,
      model_path_x_px=320.0,
      desired_curvature_1pm=-0.01,
    )

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.turn, 'RIGHT')
    self.assertAlmostEqual(result.model_center_inside_pixel_center_px, 4.0)
    self.assertAlmostEqual(result.model_path_inside_pixel_center_px, 20.0)
    self.assertAlmostEqual(result.model_path_inside_model_center_px, 16.0)
    self.assertTrue(result.path_farther_from_pixel_center)

  def test_comparison_nonfinite_or_unresolved_turn_fails_closed(self):
    api = self.api()
    cases = (
      {'pixel_lane_center_x_px': float('nan'), 'model_lane_center_x_px': 300.0,
       'model_path_x_px': 301.0, 'desired_curvature_1pm': 0.01, 'reason': 'NONFINITE_INPUT'},
      {'pixel_lane_center_x_px': 300.0, 'model_lane_center_x_px': 300.0,
       'model_path_x_px': 301.0, 'desired_curvature_1pm': float('inf'), 'reason': 'NONFINITE_INPUT'},
      {'pixel_lane_center_x_px': 300.0, 'model_lane_center_x_px': 300.0,
       'model_path_x_px': 301.0, 'desired_curvature_1pm': 0.0, 'reason': 'TURN_UNRESOLVED'},
      {'pixel_lane_center_x_px': -1.0, 'model_lane_center_x_px': 300.0,
       'model_path_x_px': 301.0, 'desired_curvature_1pm': 0.01, 'reason': 'PIXEL_REFERENCE_OUT_OF_FRAME'},
      {'pixel_lane_center_x_px': 526.0, 'model_lane_center_x_px': 300.0,
       'model_path_x_px': 301.0, 'desired_curvature_1pm': 0.01, 'reason': 'PIXEL_REFERENCE_OUT_OF_FRAME'},
    )
    for case in cases:
      reason = case.pop('reason')
      with self.subTest(reason=reason):
        result = api.compare_projection_to_pixel_reference(**case)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, reason)
        self.assertIsNone(result.model_path_abs_error_px)
        self.assertFalse(result.vehicle_activation_allowed)

  def test_outputs_are_frozen_and_expose_no_vehicle_command_or_tune(self):
    api = self.api()
    detection = api.detect_qcamera_lane_pair(self.synthetic_qcamera_frame())
    comparison = api.compare_projection_to_pixel_reference(300.0, 301.0, 295.0, 0.01)

    for value in (detection, comparison):
      with self.subTest(value=type(value).__name__):
        with self.assertRaises(FrozenInstanceError):
          value.status = 'READY'
        self.assertIsNone(getattr(value, 'command', None))
        self.assertIsNone(getattr(value, 'tune', None))
        self.assertIsNone(getattr(value, 'accepted', None))


if __name__ == '__main__':
  unittest.main()
