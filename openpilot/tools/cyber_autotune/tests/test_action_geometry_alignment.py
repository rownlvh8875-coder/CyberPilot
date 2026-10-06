from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
import math
import unittest

from openpilot.tools.cyber_autotune.recenter_condition import observe_recenter_condition
from openpilot.tools.cyber_autotune.recenter_intent import RecenterIntentObservation


class TestActionGeometryAlignment(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.action_geometry_alignment'
    self.assertIsNotNone(importlib.util.find_spec(name), 'action geometry alignment diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def recenter(*, start=0.30, future=0.20):
    start_abs = abs(start)
    future_abs = abs(future)
    return RecenterIntentObservation(
      status='DESCRIPTIVE_ONLY',
      reason='ok',
      sample_count=5,
      start_station_m=0.0,
      future_station_m=6.75,
      start_offset_m=start,
      future_offset_m=future,
      start_abs_offset_m=start_abs,
      future_abs_offset_m=future_abs,
      abs_offset_delta_m=future_abs - start_abs,
      retained_abs_offset_fraction=None if start_abs == 0.0 else future_abs / start_abs,
      same_side=start * future > 0.0,
      recentered=future_abs < start_abs,
    )

  @classmethod
  def condition(cls, *, action=0.010, desired=0.009, current=0.008, start=0.30, future=0.20):
    return observe_recenter_condition(
      cls.recenter(start=start, future=future),
      model_action_curvature_1pm=action,
      controls_desired_curvature_1pm=desired,
      current_curvature_1pm=current,
      v_ego_mps=8.0,
    )

  def test_reports_action_and_controls_alignment_without_authority(self):
    api = self.api()
    result = api.observe_action_geometry_alignment(
      self.condition(),
      path_curvature_1pm=0.0085,
      lane_center_curvature_1pm=0.004,
    )

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertAlmostEqual(result.action_lane_turn_excess_1pm, 0.006)
    self.assertAlmostEqual(result.path_lane_turn_excess_1pm, 0.0045)
    self.assertAlmostEqual(result.action_path_turn_excess_1pm, 0.0015)
    self.assertAlmostEqual(result.controls_lane_turn_excess_1pm, 0.005)
    self.assertAlmostEqual(result.controls_path_turn_excess_1pm, 0.0005)
    self.assertAlmostEqual(result.action_abs_error_to_path_1pm, 0.0015)
    self.assertAlmostEqual(result.action_abs_error_to_lane_1pm, 0.006)
    self.assertEqual(result.action_reference_state, 'PATH_CLOSER')
    self.assertEqual(result.controls_reference_state, 'PATH_CLOSER')
    self.assertEqual(result.path_vs_lane_turn_state, 'MORE_TURN_THAN_LANE')
    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_mirrored_turn_preserves_turn_relative_metrics(self):
    api = self.api()
    positive = api.observe_action_geometry_alignment(
      self.condition(action=0.010, desired=0.009, current=0.008, start=0.30, future=0.20),
      path_curvature_1pm=0.0085,
      lane_center_curvature_1pm=0.004,
    )
    negative = api.observe_action_geometry_alignment(
      self.condition(action=-0.010, desired=-0.009, current=-0.008, start=-0.30, future=-0.20),
      path_curvature_1pm=-0.0085,
      lane_center_curvature_1pm=-0.004,
    )

    for field in (
      'action_lane_turn_excess_1pm',
      'path_lane_turn_excess_1pm',
      'action_path_turn_excess_1pm',
      'controls_lane_turn_excess_1pm',
      'controls_path_turn_excess_1pm',
      'action_abs_error_to_path_1pm',
      'action_abs_error_to_lane_1pm',
    ):
      self.assertAlmostEqual(getattr(positive, field), getattr(negative, field))
    self.assertEqual(positive.action_reference_state, negative.action_reference_state)
    self.assertEqual(positive.path_vs_lane_turn_state, negative.path_vs_lane_turn_state)

  def test_reports_lane_closer_and_equal_reference_without_thresholds(self):
    api = self.api()
    lane_closer = api.observe_action_geometry_alignment(
      self.condition(action=0.0042, desired=0.0041, current=0.0040),
      path_curvature_1pm=0.010,
      lane_center_curvature_1pm=0.004,
    )
    equal = api.observe_action_geometry_alignment(
      self.condition(action=0.006, desired=0.006, current=0.006),
      path_curvature_1pm=0.008,
      lane_center_curvature_1pm=0.004,
    )

    self.assertEqual(lane_closer.action_reference_state, 'LANE_CLOSER')
    self.assertEqual(equal.action_reference_state, 'EQUAL_DISTANCE')
    self.assertEqual(equal.controls_reference_state, 'EQUAL_DISTANCE')

  def test_reports_path_turn_relation_exactly(self):
    api = self.api()
    more = api.observe_action_geometry_alignment(
      self.condition(),
      path_curvature_1pm=0.007,
      lane_center_curvature_1pm=0.004,
    )
    less = api.observe_action_geometry_alignment(
      self.condition(),
      path_curvature_1pm=0.002,
      lane_center_curvature_1pm=0.004,
    )
    match = api.observe_action_geometry_alignment(
      self.condition(),
      path_curvature_1pm=0.004,
      lane_center_curvature_1pm=0.004,
    )

    self.assertEqual(more.path_vs_lane_turn_state, 'MORE_TURN_THAN_LANE')
    self.assertEqual(less.path_vs_lane_turn_state, 'LESS_TURN_THAN_LANE')
    self.assertEqual(match.path_vs_lane_turn_state, 'LANE_MATCH')

  def test_nonfinite_geometry_fails_closed(self):
    api = self.api()
    for path, lane in ((math.nan, 0.0), (0.0, math.inf), (-math.inf, 0.0)):
      with self.subTest(path=path, lane=lane):
        result = api.observe_action_geometry_alignment(
          self.condition(),
          path_curvature_1pm=path,
          lane_center_curvature_1pm=lane,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'NONFINITE_GEOMETRY')
        self.assertFalse(result.vehicle_activation_allowed)

  def test_blocked_upstream_condition_is_propagated_closed(self):
    api = self.api()
    blocked = observe_recenter_condition(
      self.recenter(),
      model_action_curvature_1pm=0.0,
      controls_desired_curvature_1pm=0.009,
      current_curvature_1pm=0.008,
      v_ego_mps=8.0,
    )
    result = api.observe_action_geometry_alignment(
      blocked,
      path_curvature_1pm=0.008,
      lane_center_curvature_1pm=0.004,
    )

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'RECENTER_CONDITION_BLOCKED')

  def test_forged_condition_numeric_identity_fails_closed(self):
    api = self.api()
    valid = self.condition()
    forged = replace(valid, tracking_abs_error_1pm=valid.tracking_abs_error_1pm + 0.1)
    result = api.observe_action_geometry_alignment(
      forged,
      path_curvature_1pm=0.008,
      lane_center_curvature_1pm=0.004,
    )

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'RECENTER_CONDITION_INVALID')

  def test_forged_recenter_outcome_fails_closed(self):
    api = self.api()
    valid = self.condition(start=0.30, future=0.20)
    forged = replace(valid, recentered=False)
    result = api.observe_action_geometry_alignment(
      forged,
      path_curvature_1pm=0.008,
      lane_center_curvature_1pm=0.004,
    )

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'RECENTER_CONDITION_INVALID')

  def test_forged_future_station_fails_closed(self):
    api = self.api()
    forged = replace(self.condition(), future_station_m=0.0)
    result = api.observe_action_geometry_alignment(
      forged,
      path_curvature_1pm=0.008,
      lane_center_curvature_1pm=0.004,
    )

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'RECENTER_CONDITION_INVALID')

  def test_forged_authority_fails_closed(self):
    api = self.api()
    forged = replace(self.condition(), vehicle_activation_allowed=True)
    result = api.observe_action_geometry_alignment(
      forged,
      path_curvature_1pm=0.008,
      lane_center_curvature_1pm=0.004,
    )

    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'RECENTER_CONDITION_INVALID')

  def test_result_is_frozen_and_has_no_command_surface(self):
    api = self.api()
    result = api.observe_action_geometry_alignment(
      self.condition(),
      path_curvature_1pm=0.008,
      lane_center_curvature_1pm=0.004,
    )
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))


if __name__ == '__main__':
  unittest.main()
