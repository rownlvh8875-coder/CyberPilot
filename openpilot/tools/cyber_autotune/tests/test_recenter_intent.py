from dataclasses import FrozenInstanceError
import importlib
import importlib.util
import math
import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import PathQualityInput


class TestRecenterIntent(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.recenter_intent'
    self.assertIsNotNone(importlib.util.find_spec(name), 'recenter intent diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def data(*, path=(0.30, 0.24, 0.18, 0.12, 0.06),
           left=(1.8, 1.8, 1.8, 1.8, 1.8),
           right=(-1.8, -1.8, -1.8, -1.8, -1.8),
           stations=(0.0, 1.0, 3.0, 6.75, 10.0),
           lane_change=False):
    n = len(stations)
    return PathQualityInput(
      station_m=stations,
      desired_path_y_m=path,
      left_lane_y_m=left,
      right_lane_y_m=right,
      left_lane_probability=(0.95,) * n,
      right_lane_probability=(0.94,) * n,
      left_lane_std_m=(0.08,) * n,
      right_lane_std_m=(0.09,) * n,
      left_road_edge_y_m=None,
      right_road_edge_y_m=None,
      lane_change_active=lane_change,
      maneuver_state='lane_change' if lane_change else 'none',
    )

  def test_reports_absolute_offset_reduction_without_vehicle_authority(self):
    api = self.api()
    source = self.data()
    result = api.observe_recenter_intent(source, future_station_m=6.75)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertEqual(result.sample_count, 5)
    self.assertEqual(result.start_station_m, 0.0)
    self.assertEqual(result.future_station_m, 6.75)
    self.assertAlmostEqual(result.start_offset_m, 0.30)
    self.assertAlmostEqual(result.future_offset_m, 0.12)
    self.assertAlmostEqual(result.start_abs_offset_m, 0.30)
    self.assertAlmostEqual(result.future_abs_offset_m, 0.12)
    self.assertAlmostEqual(result.abs_offset_delta_m, -0.18)
    self.assertAlmostEqual(result.retained_abs_offset_fraction, 0.4)
    self.assertTrue(result.same_side)
    self.assertTrue(result.recentered)
    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)
    self.assertEqual(source.desired_path_y_m, (0.30, 0.24, 0.18, 0.12, 0.06))

  def test_reports_worsening_and_equal_offset_without_threshold_tuning(self):
    api = self.api()
    worse = api.observe_recenter_intent(
      self.data(path=(0.20, 0.22, 0.24, 0.28, 0.30)),
      future_station_m=6.75,
    )
    equal = api.observe_recenter_intent(
      self.data(path=(0.20, 0.20, 0.20, 0.20, 0.20)),
      future_station_m=6.75,
    )

    self.assertGreater(worse.abs_offset_delta_m, 0.0)
    self.assertFalse(worse.recentered)
    self.assertAlmostEqual(worse.retained_abs_offset_fraction, 1.4)
    self.assertEqual(equal.abs_offset_delta_m, 0.0)
    self.assertFalse(equal.recentered)
    self.assertEqual(equal.retained_abs_offset_fraction, 1.0)

  def test_mirrored_coordinate_convention_preserves_absolute_recenter_metrics(self):
    api = self.api()
    positive_left = self.data()
    negative_left = self.data(
      path=(-0.30, -0.24, -0.18, -0.12, -0.06),
      left=(-1.8, -1.8, -1.8, -1.8, -1.8),
      right=(1.8, 1.8, 1.8, 1.8, 1.8),
    )

    a = api.observe_recenter_intent(positive_left, future_station_m=6.75)
    b = api.observe_recenter_intent(negative_left, future_station_m=6.75)

    self.assertEqual(a.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(b.status, 'DESCRIPTIVE_ONLY')
    self.assertAlmostEqual(a.start_abs_offset_m, b.start_abs_offset_m)
    self.assertAlmostEqual(a.future_abs_offset_m, b.future_abs_offset_m)
    self.assertAlmostEqual(a.abs_offset_delta_m, b.abs_offset_delta_m)
    self.assertAlmostEqual(a.retained_abs_offset_fraction, b.retained_abs_offset_fraction)
    self.assertEqual(a.same_side, b.same_side)
    self.assertEqual(a.recentered, b.recentered)

  def test_crossing_lane_center_is_descriptive_and_not_promoted(self):
    api = self.api()
    result = api.observe_recenter_intent(
      self.data(path=(0.30, 0.20, 0.10, -0.05, -0.10)),
      future_station_m=6.75,
    )

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertFalse(result.same_side)
    self.assertTrue(result.recentered)
    self.assertFalse(result.vehicle_activation_allowed)
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))

  def test_zero_start_offset_has_no_retained_ratio(self):
    api = self.api()
    result = api.observe_recenter_intent(
      self.data(path=(0.0, 0.02, 0.04, 0.06, 0.08)),
      future_station_m=6.75,
    )

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.start_abs_offset_m, 0.0)
    self.assertIsNone(result.retained_abs_offset_fraction)
    self.assertFalse(result.recentered)

  def test_invalid_geometry_lane_change_or_target_fails_closed(self):
    api = self.api()
    cases = (
      (self.data(lane_change=True), 6.75, 'lane_change_or_maneuver'),
      (self.data(path=(0.2, 0.2, math.nan, 0.2, 0.2)), 6.75, 'invalid_geometry_values'),
      (self.data(), 4.0, 'future_station_unavailable'),
      (self.data(), 0.0, 'future_station_not_after_start'),
      (self.data(), float('nan'), 'invalid_future_station'),
    )
    for source, station, reason in cases:
      with self.subTest(reason=reason):
        result = api.observe_recenter_intent(source, future_station_m=station)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, reason)
        self.assertIsNone(result.start_offset_m)
        self.assertIsNone(result.future_offset_m)
        self.assertFalse(result.vehicle_activation_allowed)

  def test_nonfinite_path_quality_derivatives_fail_closed(self):
    api = self.api()
    huge = 1e308
    source = self.data(
      path=(0.0, 0.0, 0.0, 0.0, 0.0),
      left=(huge, huge, huge, huge, huge),
      right=(-huge, -huge, -huge, -huge, -huge),
    )
    result = api.observe_recenter_intent(source, future_station_m=6.75)

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'invalid_path_reference_derived')
    self.assertIsNone(result.start_offset_m)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_derived_ratio_overflow_fails_closed(self):
    api = self.api()
    source = self.data(path=(1e-320, 0.1, 0.2, 1.0, 1.2))
    result = api.observe_recenter_intent(source, future_station_m=6.75)

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'derived_offset_invalid')
    self.assertIsNone(result.start_offset_m)
    self.assertIsNone(result.retained_abs_offset_fraction)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_result_is_frozen(self):
    api = self.api()
    result = api.observe_recenter_intent(self.data(), future_station_m=6.75)
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'


if __name__ == '__main__':
  unittest.main()
