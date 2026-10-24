from dataclasses import FrozenInstanceError
import importlib
import importlib.util
import math
import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import PathQualityInput


class TestDivergingAffineCandidate(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.diverging_affine_candidate'
    self.assertIsNotNone(importlib.util.find_spec(name), 'diverging affine candidate diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def data(*, path=None, lane_half_width=1.5):
    station = (0.0, 2.0, 4.0, 6.0, 8.0)
    desired = path if path is not None else (0.0, 0.02, 0.04, 0.06, 0.08)
    return PathQualityInput(
      station_m=station,
      desired_path_y_m=desired,
      left_lane_y_m=tuple(-lane_half_width for _ in station),
      right_lane_y_m=tuple(lane_half_width for _ in station),
      left_lane_probability=(0.99,) * len(station),
      right_lane_probability=(0.99,) * len(station),
      left_lane_std_m=(0.05,) * len(station),
      right_lane_std_m=(0.05,) * len(station),
      left_road_edge_y_m=tuple(-(lane_half_width + 1.0) for _ in station),
      right_road_edge_y_m=tuple(lane_half_width + 1.0 for _ in station),
      lane_change_active=False,
      maneuver_state='none',
    )

  def test_flat_preserves_horizon_offset_and_flattens_divergence(self):
    api = self.api()
    result = api.build_diverging_affine_candidate(
      self.data(),
      action_horizon_station_m=4.0,
      requested_curvature_1pm=0.002,
      mode='FLAT',
    )
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertEqual(result.mode, 'FLAT')
    self.assertAlmostEqual(result.turn_relative_offset_m, 0.04)
    self.assertAlmostEqual(result.original_offset_slope_per_m, 0.01)
    self.assertAlmostEqual(result.target_offset_slope_per_m, 0.0)
    self.assertAlmostEqual(result.candidate_offset_slope_per_m, 0.0)
    for actual, expected in zip(result.candidate_path_y_m, (0.04, 0.04, 0.04, 0.04, 0.04), strict=True):
      self.assertAlmostEqual(actual, expected)
    self.assertAlmostEqual(result.correction_at_action_horizon_m, 0.0)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_mirror_reverses_divergence_slope_without_moving_horizon_point(self):
    api = self.api()
    result = api.build_diverging_affine_candidate(
      self.data(),
      action_horizon_station_m=4.0,
      requested_curvature_1pm=0.002,
      mode='MIRROR',
    )
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertAlmostEqual(result.target_offset_slope_per_m, -0.01)
    self.assertAlmostEqual(result.candidate_offset_slope_per_m, -0.01)
    for actual, expected in zip(result.candidate_path_y_m, (0.08, 0.06, 0.04, 0.02, 0.0), strict=True):
      self.assertAlmostEqual(actual, expected)
    self.assertAlmostEqual(result.correction_at_action_horizon_m, 0.0)
    self.assertTrue(result.candidate_within_lane_envelope)

  def test_mirrored_turn_preserves_normalized_geometry(self):
    api = self.api()
    positive = api.build_diverging_affine_candidate(
      self.data(),
      action_horizon_station_m=4.0,
      requested_curvature_1pm=0.002,
      mode='MIRROR',
    )
    negative = api.build_diverging_affine_candidate(
      self.data(path=(0.0, -0.02, -0.04, -0.06, -0.08)),
      action_horizon_station_m=4.0,
      requested_curvature_1pm=-0.002,
      mode='MIRROR',
    )
    self.assertAlmostEqual(positive.turn_relative_offset_m, negative.turn_relative_offset_m)
    self.assertAlmostEqual(positive.turn_relative_offset_slope_per_m, negative.turn_relative_offset_slope_per_m)
    self.assertAlmostEqual(positive.delta_slope_per_m, -negative.delta_slope_per_m)
    self.assertEqual(positive.candidate_path_y_m, tuple(-v for v in negative.candidate_path_y_m))

  def test_outside_path_is_blocked(self):
    api = self.api()
    result = api.build_diverging_affine_candidate(
      self.data(path=(0.0, -0.02, -0.04, -0.06, -0.08)),
      action_horizon_station_m=4.0,
      requested_curvature_1pm=0.002,
      mode='FLAT',
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'PATH_NOT_TURN_INSIDE')

  def test_converging_path_is_blocked(self):
    api = self.api()
    result = api.build_diverging_affine_candidate(
      self.data(path=(0.08, 0.06, 0.04, 0.02, 0.0)),
      action_horizon_station_m=4.0,
      requested_curvature_1pm=0.002,
      mode='FLAT',
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'PATH_NOT_DIVERGING')

  def test_mirror_candidate_outside_lane_fails_closed(self):
    api = self.api()
    result = api.build_diverging_affine_candidate(
      self.data(path=(0.0, 0.02, 0.04, 0.06, 0.08), lane_half_width=0.10),
      action_horizon_station_m=6.0,
      requested_curvature_1pm=0.002,
      mode='MIRROR',
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'CANDIDATE_OUTSIDE_LANES')

  def test_horizon_must_be_finite_and_inside_centered_slope_axis(self):
    api = self.api()
    for horizon in (math.nan, math.inf, 0.0, 8.0):
      with self.subTest(horizon=horizon):
        result = api.build_diverging_affine_candidate(
          self.data(),
          action_horizon_station_m=horizon,
          requested_curvature_1pm=0.002,
          mode='FLAT',
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'INVALID_ACTION_HORIZON')

  def test_requested_curvature_must_be_finite_nonzero(self):
    api = self.api()
    for curvature in (0.0, math.nan, math.inf):
      with self.subTest(curvature=curvature):
        result = api.build_diverging_affine_candidate(
          self.data(),
          action_horizon_station_m=4.0,
          requested_curvature_1pm=curvature,
          mode='FLAT',
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'TURN_UNRESOLVED')

  def test_unsupported_mode_fails_closed(self):
    api = self.api()
    result = api.build_diverging_affine_candidate(
      self.data(),
      action_horizon_station_m=4.0,
      requested_curvature_1pm=0.002,
      mode='RECENTER',
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'UNSUPPORTED_MODE')

  def test_invalid_upstream_geometry_fails_closed(self):
    api = self.api()
    data = self.data()
    bad = PathQualityInput(
      station_m=data.station_m,
      desired_path_y_m=data.desired_path_y_m,
      left_lane_y_m=data.left_lane_y_m,
      right_lane_y_m=data.right_lane_y_m,
      left_lane_probability=data.left_lane_probability,
      right_lane_probability=data.right_lane_probability,
      left_lane_std_m=data.left_lane_std_m,
      right_lane_std_m=data.right_lane_std_m,
      left_road_edge_y_m=data.left_road_edge_y_m,
      right_road_edge_y_m=data.right_road_edge_y_m,
      lane_change_active=True,
      maneuver_state='lane_change',
    )
    result = api.build_diverging_affine_candidate(
      bad,
      action_horizon_station_m=4.0,
      requested_curvature_1pm=0.002,
      mode='FLAT',
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('lane_change', result.reason)

  def test_result_is_frozen_and_has_no_control_surface(self):
    api = self.api()
    result = api.build_diverging_affine_candidate(
      self.data(),
      action_horizon_station_m=4.0,
      requested_curvature_1pm=0.002,
      mode='FLAT',
    )
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))
    self.assertIsNone(getattr(result, 'profile', None))


if __name__ == '__main__':
  unittest.main()
