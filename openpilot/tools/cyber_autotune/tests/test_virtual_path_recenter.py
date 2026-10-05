from dataclasses import FrozenInstanceError
import importlib
import importlib.util
import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import PathQualityInput


class TestVirtualPathRecenter(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.virtual_path_recenter'
    self.assertIsNotNone(importlib.util.find_spec(name), 'virtual path recenter diagnostic not implemented')
    return importlib.import_module(name)

  def data(self, *, desired=(0.0, 0.0, 0.0, 0.0, 0.0),
           left=(1.8, 1.8, 1.8, 1.8, 1.8),
           right=(-1.8, -1.8, -1.8, -1.8, -1.8),
           lane_change=False):
    n = len(desired)
    return PathQualityInput(
      station_m=tuple(float(i * 5) for i in range(n)),
      desired_path_y_m=tuple(desired),
      left_lane_y_m=tuple(left),
      right_lane_y_m=tuple(right),
      left_lane_probability=(0.95,) * n,
      right_lane_probability=(0.94,) * n,
      left_lane_std_m=(0.08,) * n,
      right_lane_std_m=(0.09,) * n,
      left_road_edge_y_m=None,
      right_road_edge_y_m=None,
      lane_change_active=lane_change,
      maneuver_state='lane_change' if lane_change else 'none',
    )

  def test_recenters_only_virtual_geometry_and_preserves_authority_blocks(self):
    api = self.api()
    source = self.data(desired=(0.4, 0.4, 0.4, 0.4, 0.4))
    result = api.build_virtual_lane_center_candidate(source)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertEqual(result.sample_count, 5)
    self.assertEqual(result.station_m, source.station_m)
    self.assertEqual(result.original_path_y_m, source.desired_path_y_m)
    self.assertEqual(result.candidate_path_y_m, (0.0,) * 5)
    self.assertEqual(result.correction_y_m, (-0.4,) * 5)
    self.assertAlmostEqual(result.correction_signed_mean_m, -0.4)
    self.assertAlmostEqual(result.correction_rmse_m, 0.4)
    self.assertAlmostEqual(result.correction_max_abs_m, 0.4)
    self.assertEqual(source.desired_path_y_m, (0.4,) * 5)

    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_uses_model_lane_center_even_when_coordinate_convention_is_mirrored(self):
    api = self.api()
    source = self.data(
      desired=(-0.4, -0.3, -0.2, -0.1, 0.0),
      left=(-1.8, -1.7, -1.6, -1.5, -1.4),
      right=(1.8, 1.9, 2.0, 2.1, 2.2),
    )
    result = api.build_virtual_lane_center_candidate(source)

    expected_center = (0.0, 0.1, 0.2, 0.3, 0.4)
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    for actual, expected in zip(result.candidate_path_y_m, expected_center, strict=True):
      self.assertAlmostEqual(actual, expected)
    for actual in result.correction_y_m:
      self.assertAlmostEqual(actual, 0.4)

  def test_reports_curvature_continuity_without_accepting_or_tuning_candidate(self):
    api = self.api()
    source = self.data(
      desired=(0.0, 0.4, 0.8, 1.2, 1.6),
      left=(1.8, 2.0, 2.2, 2.4, 2.6),
      right=(-1.8, -1.6, -1.4, -1.2, -1.0),
    )
    result = api.build_virtual_lane_center_candidate(source)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertGreaterEqual(result.original_curvature_rmse_1pm, 0.0)
    self.assertGreaterEqual(result.candidate_curvature_rmse_1pm, 0.0)
    self.assertGreaterEqual(result.original_curvature_jump_max_abs_1pm, 0.0)
    self.assertGreaterEqual(result.candidate_curvature_jump_max_abs_1pm, 0.0)
    self.assertGreaterEqual(result.original_curvature_rate_max_abs_1pm2, 0.0)
    self.assertGreaterEqual(result.candidate_curvature_rate_max_abs_1pm2, 0.0)
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'tune', None))
    self.assertIsNone(getattr(result, 'command', None))

  def test_curvature_metric_matches_known_three_point_geometry(self):
    api = self.api()
    source = PathQualityInput(
      station_m=(0.0, 1.0, 2.0),
      desired_path_y_m=(0.0, 0.0, 0.0),
      left_lane_y_m=(1.8, 2.8, 1.8),
      right_lane_y_m=(-1.8, -0.8, -1.8),
      left_lane_probability=(1.0,) * 3,
      right_lane_probability=(1.0,) * 3,
      left_lane_std_m=(0.0,) * 3,
      right_lane_std_m=(0.0,) * 3,
      left_road_edge_y_m=None,
      right_road_edge_y_m=None,
      lane_change_active=False,
      maneuver_state='none',
    )
    result = api.build_virtual_lane_center_candidate(source)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.original_curvature_rmse_1pm, 0.0)
    self.assertAlmostEqual(result.candidate_curvature_rmse_1pm, 1.0)
    self.assertEqual(result.original_curvature_jump_max_abs_1pm, 0.0)
    self.assertEqual(result.candidate_curvature_jump_max_abs_1pm, 0.0)

  def test_curvature_rate_normalizes_adjacent_change_by_station_distance(self):
    api = self.api()
    center = (0.0, 0.0, 0.0, 4.0)
    source = PathQualityInput(
      station_m=(0.0, 2.0, 4.0, 8.0),
      desired_path_y_m=(0.0, 0.0, 0.0, 0.0),
      left_lane_y_m=tuple(value + 5.0 for value in center),
      right_lane_y_m=tuple(value - 5.0 for value in center),
      left_lane_probability=(1.0,) * 4,
      right_lane_probability=(1.0,) * 4,
      left_lane_std_m=(0.0,) * 4,
      right_lane_std_m=(0.0,) * 4,
      left_road_edge_y_m=None,
      right_road_edge_y_m=None,
      lane_change_active=False,
      maneuver_state='none',
    )
    result = api.build_virtual_lane_center_candidate(source)

    expected_second_curvature = 1.0 / (26.0 ** 0.5)
    expected_rate = expected_second_curvature / 2.0
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertAlmostEqual(result.candidate_curvature_jump_max_abs_1pm, expected_second_curvature)
    self.assertAlmostEqual(result.candidate_curvature_rate_max_abs_1pm2, expected_rate)

  def test_mean_shift_candidate_removes_mean_bias_with_one_constant_translation(self):
    api = self.api()
    center = (0.0, 0.1, 0.2, 0.3, 0.4)
    desired = (0.4, 0.6, 0.9, 1.3, 1.8)
    source = self.data(
      desired=desired,
      left=tuple(value + 1.8 for value in center),
      right=tuple(value - 1.8 for value in center),
    )
    result = api.build_virtual_mean_shift_candidate(source)

    expected_bias = sum(d - c for d, c in zip(desired, center, strict=True)) / len(center)
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertAlmostEqual(result.applied_shift_m, -expected_bias)
    for original, candidate in zip(desired, result.candidate_path_y_m, strict=True):
      self.assertAlmostEqual(candidate - original, -expected_bias)
    self.assertAlmostEqual(result.residual_lane_center_bias_mean_m, 0.0)
    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_mean_shift_preserves_spatial_curvature_metrics(self):
    api = self.api()
    source = self.data(
      desired=(0.4, 0.8, 1.3, 1.9, 2.6),
      left=(1.8, 2.0, 2.3, 2.7, 3.2),
      right=(-1.8, -1.6, -1.3, -0.9, -0.4),
    )
    result = api.build_virtual_mean_shift_candidate(source)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertAlmostEqual(result.candidate_curvature_rmse_1pm, result.original_curvature_rmse_1pm, places=12)
    self.assertAlmostEqual(result.candidate_curvature_jump_max_abs_1pm, result.original_curvature_jump_max_abs_1pm, places=12)
    self.assertAlmostEqual(result.candidate_curvature_rate_max_abs_1pm2, result.original_curvature_rate_max_abs_1pm2, places=12)

  def test_mean_shift_invalid_geometry_and_lane_change_fail_closed(self):
    api = self.api()
    for source in (
      self.data(lane_change=True),
      self.data(left=(1.8, 1.8, 0.0, 1.8, 1.8), right=(-1.8, -1.8, 0.0, -1.8, -1.8)),
    ):
      with self.subTest(source=source):
        result = api.build_virtual_mean_shift_candidate(source)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIsNone(result.candidate_path_y_m)
        self.assertFalse(result.vehicle_activation_allowed)

  def test_mean_shift_blocks_translation_that_leaves_model_lane_envelope(self):
    api = self.api()
    source = self.data(desired=(1.7, 1.7, 1.7, -1.7, -1.7))
    result = api.build_virtual_mean_shift_candidate(source)

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'candidate_outside_lanes')
    self.assertIsNone(result.candidate_path_y_m)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_invalid_geometry_and_lane_change_fail_closed_without_candidate(self):
    api = self.api()
    cases = (
      self.data(lane_change=True),
      self.data(left=(1.8, 1.8, 0.0, 1.8, 1.8), right=(-1.8, -1.8, 0.0, -1.8, -1.8)),
      self.data(desired=(0.0, 0.0, 3.0, 0.0, 0.0)),
    )
    for source in cases:
      with self.subTest(source=source):
        result = api.build_virtual_lane_center_candidate(source)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIsNone(result.candidate_path_y_m)
        self.assertIsNone(result.correction_y_m)
        self.assertFalse(result.vehicle_activation_allowed)

  def test_derived_numeric_overflow_fails_closed(self):
    api = self.api()
    huge = 1e308
    source = PathQualityInput(
      station_m=(0.0, huge / 4, huge / 2, huge * 0.75, huge),
      desired_path_y_m=(0.0, 0.0, 0.0, 0.0, 0.0),
      left_lane_y_m=(huge, huge, huge, huge, huge),
      right_lane_y_m=(-huge, -huge, -huge, -huge, -huge),
      left_lane_probability=(1.0,) * 5,
      right_lane_probability=(1.0,) * 5,
      left_lane_std_m=(0.0,) * 5,
      right_lane_std_m=(0.0,) * 5,
      left_road_edge_y_m=None,
      right_road_edge_y_m=None,
      lane_change_active=False,
      maneuver_state='none',
    )
    result = api.build_virtual_lane_center_candidate(source)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'derived_geometry_invalid')
    self.assertIsNone(result.candidate_path_y_m)

  def test_transition_attributes_lane_center_translation_without_vehicle_authority(self):
    api = self.api()
    previous = self.data()
    current = self.data(
      left=(2.1, 2.1, 2.1, 2.1, 2.1),
      right=(-1.5, -1.5, -1.5, -1.5, -1.5),
    )
    result = api.attribute_virtual_mean_shift_transition(previous, current)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertAlmostEqual(result.shift_delta_m, 0.3)
    self.assertAlmostEqual(result.lane_center_component_m, 0.3)
    self.assertAlmostEqual(result.path_component_m, 0.0)
    self.assertAlmostEqual(result.common_lane_center_component_m, 0.3)
    self.assertAlmostEqual(result.common_path_component_m, 0.0)
    self.assertAlmostEqual(result.horizon_component_m, 0.0)
    self.assertAlmostEqual(result.left_lane_component_m, 0.3)
    self.assertAlmostEqual(result.right_lane_component_m, 0.3)
    self.assertAlmostEqual(result.lane_width_mean_delta_m, 0.0)
    self.assertTrue(result.lane_boundaries_same_direction)
    self.assertFalse(result.sample_count_changed)
    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_transition_attributes_path_motion_separately(self):
    api = self.api()
    previous = self.data(desired=(0.2, 0.2, 0.2, 0.2, 0.2))
    current = self.data(desired=(0.5, 0.5, 0.5, 0.5, 0.5))
    result = api.attribute_virtual_mean_shift_transition(previous, current)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertAlmostEqual(result.shift_delta_m, -0.3)
    self.assertAlmostEqual(result.lane_center_component_m, 0.0)
    self.assertAlmostEqual(result.path_component_m, -0.3)
    self.assertAlmostEqual(result.common_lane_center_component_m, 0.0)
    self.assertAlmostEqual(result.common_path_component_m, -0.3)
    self.assertAlmostEqual(result.horizon_component_m, 0.0)

  def test_transition_separates_horizon_composition_from_common_geometry(self):
    api = self.api()
    previous = self.data(
      desired=(0.0, 0.0, 0.0, 0.0, 1.0),
      left=(1.8, 1.8, 1.8, 1.8, 1.8),
      right=(-1.8, -1.8, -1.8, -1.8, -1.8),
    )
    current = self.data(
      desired=(0.0, 0.0, 0.0, 0.0),
      left=(1.8, 1.8, 1.8, 1.8),
      right=(-1.8, -1.8, -1.8, -1.8),
    )
    result = api.attribute_virtual_mean_shift_transition(previous, current)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.previous_sample_count, 5)
    self.assertEqual(result.current_sample_count, 4)
    self.assertEqual(result.common_sample_count, 4)
    self.assertTrue(result.sample_count_changed)
    self.assertAlmostEqual(result.horizon_delta_m, -5.0)
    self.assertAlmostEqual(result.shift_delta_m, 0.2)
    self.assertAlmostEqual(result.common_lane_center_component_m, 0.0)
    self.assertAlmostEqual(result.common_path_component_m, 0.0)
    self.assertAlmostEqual(result.horizon_component_m, 0.2)

  def test_transition_distinguishes_equal_length_station_change_from_geometry_motion(self):
    api = self.api()
    previous = PathQualityInput(
      station_m=(0.0, 5.0, 10.0, 15.0, 20.0),
      desired_path_y_m=(0.0, 0.0, 0.0, 0.0, 0.5),
      left_lane_y_m=(1.8, 1.8, 1.8, 1.8, 2.3),
      right_lane_y_m=(-1.8, -1.8, -1.8, -1.8, -1.3),
      left_lane_probability=(0.95,) * 5,
      right_lane_probability=(0.94,) * 5,
      left_lane_std_m=(0.08,) * 5,
      right_lane_std_m=(0.09,) * 5,
      left_road_edge_y_m=None,
      right_road_edge_y_m=None,
      lane_change_active=False,
      maneuver_state='none',
    )
    current = PathQualityInput(
      station_m=(0.0, 5.0, 10.0, 15.0, 25.0),
      desired_path_y_m=(0.0, 0.0, 0.0, 0.0, -0.5),
      left_lane_y_m=(1.8, 1.8, 1.8, 1.8, 1.3),
      right_lane_y_m=(-1.8, -1.8, -1.8, -1.8, -2.3),
      left_lane_probability=(0.95,) * 5,
      right_lane_probability=(0.94,) * 5,
      left_lane_std_m=(0.08,) * 5,
      right_lane_std_m=(0.09,) * 5,
      left_road_edge_y_m=None,
      right_road_edge_y_m=None,
      lane_change_active=False,
      maneuver_state='none',
    )

    result = api.attribute_virtual_mean_shift_transition(previous, current)

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertFalse(result.sample_count_changed)
    self.assertTrue(result.station_axis_changed)
    self.assertAlmostEqual(result.common_left_lane_component_m, 0.0)
    self.assertAlmostEqual(result.common_right_lane_component_m, 0.0)
    self.assertFalse(result.lane_boundaries_same_direction)

  def test_transition_fails_closed_for_blocked_frame_or_insufficient_overlap(self):
    api = self.api()
    previous = self.data()
    blocked = api.attribute_virtual_mean_shift_transition(previous, self.data(lane_change=True))
    self.assertEqual(blocked.status, 'BLOCKED')
    self.assertEqual(blocked.reason, 'current_lane_change_or_maneuver')
    self.assertIsNone(blocked.shift_delta_m)
    self.assertFalse(blocked.vehicle_activation_allowed)

    far = PathQualityInput(
      station_m=(100.0, 105.0, 110.0),
      desired_path_y_m=(0.0, 0.0, 0.0),
      left_lane_y_m=(1.8, 1.8, 1.8),
      right_lane_y_m=(-1.8, -1.8, -1.8),
      left_lane_probability=(0.95,) * 3,
      right_lane_probability=(0.94,) * 3,
      left_lane_std_m=(0.08,) * 3,
      right_lane_std_m=(0.09,) * 3,
      left_road_edge_y_m=None,
      right_road_edge_y_m=None,
      lane_change_active=False,
      maneuver_state='none',
    )
    no_overlap = api.attribute_virtual_mean_shift_transition(previous, far)
    self.assertEqual(no_overlap.status, 'BLOCKED')
    self.assertEqual(no_overlap.reason, 'insufficient_common_stations')
    self.assertTrue(no_overlap.station_axis_changed)
    self.assertIsNone(no_overlap.shift_delta_m)
    self.assertFalse(no_overlap.vehicle_activation_allowed)

  def test_result_is_frozen_and_deterministic(self):
    api = self.api()
    source = self.data(desired=(0.2, 0.2, 0.2, 0.2, 0.2))
    first = api.build_virtual_lane_center_candidate(source)
    second = api.build_virtual_lane_center_candidate(source)
    self.assertEqual(first, second)
    with self.assertRaises(FrozenInstanceError):
      first.status = 'READY'


if __name__ == '__main__':
  unittest.main()
