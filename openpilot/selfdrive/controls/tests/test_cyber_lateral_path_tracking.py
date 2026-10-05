import importlib
import importlib.util
import math
import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import PathQualityObservation
from openpilot.selfdrive.controls.lib.cyber_lateral.types import (
  CyberLateralConfig, CyberLateralMode, LateralBinding, LateralContext, NativeLateralResult,
)


class TestCyberLateralPathTrackingSeparation(unittest.TestCase):
  def api(self):
    name = 'openpilot.selfdrive.controls.lib.cyber_lateral.path_tracking'
    self.assertIsNotNone(importlib.util.find_spec(name), 'path/tracking separation observer not implemented')
    return importlib.import_module(name)

  @staticmethod
  def path_quality(*, valid=True, reason='ok', bias=0.25):
    return PathQualityObservation(
      valid=valid,
      reason=reason,
      sample_count=3 if valid else 0,
      model_to_lane_center_bias_m=bias if valid else None,
      lane_width_mean_m=3.6 if valid else None,
      lane_width_std_m=0.0 if valid else None,
      confidence=0.9 if valid else None,
      minimum_edge_clearance_m=1.0 if valid else None,
    )

  def test_same_sample_keeps_model_bias_separate_from_curvature_tracking_error(self):
    api = self.api()
    result = api.observe_path_tracking(
      model_mono_time_ns=101,
      car_state_mono_time_ns=102,
      desired_curvature_1pm=0.010,
      current_curvature_1pm=0.007,
      path_quality=self.path_quality(bias=0.25),
    )
    self.assertTrue(result.valid)
    self.assertEqual(result.reason, 'ok')
    self.assertEqual(result.model_mono_time_ns, 101)
    self.assertEqual(result.car_state_mono_time_ns, 102)
    self.assertAlmostEqual(result.model_to_lane_center_bias_m, 0.25)
    self.assertAlmostEqual(result.curvature_tracking_error_1pm, -0.003)

  def test_missing_or_invalid_path_reference_fails_closed_without_partial_values(self):
    api = self.api()
    for path_quality, reason in (
      (None, 'missing_path_reference'),
      (self.path_quality(valid=False, reason='lane_loss'), 'invalid_path_reference'),
    ):
      with self.subTest(reason=reason):
        result = api.observe_path_tracking(
          model_mono_time_ns=101,
          car_state_mono_time_ns=102,
          desired_curvature_1pm=0.010,
          current_curvature_1pm=0.007,
          path_quality=path_quality,
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, reason)
        self.assertIsNone(result.model_to_lane_center_bias_m)
        self.assertIsNone(result.curvature_tracking_error_1pm)

  def test_invalid_timestamp_or_curvature_fails_closed(self):
    api = self.api()
    cases = (
      (0, 102, 0.01, 0.007, 'invalid_timestamp'),
      (101, 102, math.nan, 0.007, 'invalid_numeric_input'),
      (101, 102, 0.01, math.inf, 'invalid_numeric_input'),
    )
    for model_time, car_time, desired, current, reason in cases:
      with self.subTest(reason=reason):
        result = api.observe_path_tracking(
          model_mono_time_ns=model_time,
          car_state_mono_time_ns=car_time,
          desired_curvature_1pm=desired,
          current_curvature_1pm=current,
          path_quality=self.path_quality(),
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, reason)

  def test_finite_curvatures_with_overflowing_residual_fail_closed(self):
    api = self.api()
    result = api.observe_path_tracking(
      model_mono_time_ns=101,
      car_state_mono_time_ns=102,
      desired_curvature_1pm=-1e308,
      current_curvature_1pm=1e308,
      path_quality=self.path_quality(),
    )
    self.assertFalse(result.valid)
    self.assertEqual(result.reason, 'invalid_tracking_residual')
    self.assertIsNone(result.model_to_lane_center_bias_m)
    self.assertIsNone(result.curvature_tracking_error_1pm)

  def test_coordinator_attaches_read_only_separation_to_observation(self):
    api = self.api()
    from openpilot.selfdrive.controls.lib.cyber_lateral.coordinator import CyberLateralCoordinator

    binding = LateralBinding('car', 'fw', 'model', 'torque', 0)
    coordinator = CyberLateralCoordinator(
      CyberLateralConfig(mode=CyberLateralMode.OBSERVE_ONLY),
      binding,
    )
    context = LateralContext(
      model_mono_time_ns=101,
      car_state_mono_time_ns=102,
      vehicle_parameters_mono_time_ns=103,
      lateral_delay_mono_time_ns=104,
      input_valid=True,
      lat_active=True,
      steering_pressed=False,
      steer_limited_by_safety=False,
      curvature_limited=False,
      v_ego_mps=20.0,
      desired_curvature_1pm=0.010,
      current_curvature_1pm=0.007,
      roll_rad=0.0,
      lateral_delay_s=0.2,
      native_result=NativeLateralResult(0.1, 0.2, 'torque'),
      binding=binding,
      path_quality_observation=self.path_quality(bias=-0.18),
    )

    coordinator.observe(context)

    self.assertIsNotNone(coordinator.last_observation)
    separation = coordinator.last_observation.path_tracking_observation
    self.assertIsInstance(separation, api.PathTrackingObservation)
    self.assertTrue(separation.valid)
    self.assertAlmostEqual(separation.model_to_lane_center_bias_m, -0.18)
    self.assertAlmostEqual(separation.curvature_tracking_error_1pm, -0.003)


if __name__ == '__main__':
  unittest.main()
