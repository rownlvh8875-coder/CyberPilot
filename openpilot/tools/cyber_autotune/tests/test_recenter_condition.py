from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
import math
import unittest

from openpilot.tools.cyber_autotune.recenter_intent import RecenterIntentObservation


class TestRecenterCondition(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.recenter_condition'
    self.assertIsNotNone(importlib.util.find_spec(name), 'recenter condition diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def recenter(*, start=0.20, future=0.10, recentered=True):
    return RecenterIntentObservation(
      status='DESCRIPTIVE_ONLY',
      reason='ok',
      sample_count=5,
      start_station_m=0.0,
      future_station_m=6.75,
      start_offset_m=start,
      future_offset_m=future,
      start_abs_offset_m=abs(start),
      future_abs_offset_m=abs(future),
      abs_offset_delta_m=abs(future) - abs(start),
      retained_abs_offset_fraction=None if start == 0.0 else abs(future) / abs(start),
      same_side=start * future > 0.0,
      recentered=recentered,
    )

  def test_positive_curvature_positive_offset_is_turn_inside_and_undertrack(self):
    api = self.api()
    result = api.observe_recenter_condition(
      self.recenter(start=0.20, future=0.15),
      model_action_curvature_1pm=0.002,
      controls_desired_curvature_1pm=0.0021,
      current_curvature_1pm=0.0017,
      v_ego_mps=8.0,
    )

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.start_turn_relative_state, 'INSIDE')
    self.assertAlmostEqual(result.start_turn_relative_offset_m, 0.20)
    self.assertEqual(result.tracking_state, 'UNDER')
    self.assertAlmostEqual(result.tracking_toward_turn_1pm, -0.0004)
    self.assertAlmostEqual(result.tracking_abs_error_1pm, 0.0004)
    self.assertEqual(result.recentered, True)
    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_negative_curvature_negative_offset_is_turn_inside_and_overtrack(self):
    api = self.api()
    result = api.observe_recenter_condition(
      self.recenter(start=-0.25, future=-0.30, recentered=False),
      model_action_curvature_1pm=-0.003,
      controls_desired_curvature_1pm=-0.0028,
      current_curvature_1pm=-0.0034,
      v_ego_mps=5.0,
    )

    self.assertEqual(result.start_turn_relative_state, 'INSIDE')
    self.assertAlmostEqual(result.start_turn_relative_offset_m, 0.25)
    self.assertEqual(result.tracking_state, 'OVER')
    self.assertAlmostEqual(result.tracking_toward_turn_1pm, 0.0006)
    self.assertEqual(result.recentered, False)

  def test_turn_outside_is_coordinate_sign_invariant(self):
    api = self.api()
    positive_turn = api.observe_recenter_condition(
      self.recenter(start=-0.20, future=-0.10),
      model_action_curvature_1pm=0.001,
      controls_desired_curvature_1pm=0.001,
      current_curvature_1pm=0.001,
      v_ego_mps=10.0,
    )
    negative_turn = api.observe_recenter_condition(
      self.recenter(start=0.20, future=0.10),
      model_action_curvature_1pm=-0.001,
      controls_desired_curvature_1pm=-0.001,
      current_curvature_1pm=-0.001,
      v_ego_mps=10.0,
    )

    for result in (positive_turn, negative_turn):
      self.assertEqual(result.start_turn_relative_state, 'OUTSIDE')
      self.assertAlmostEqual(result.start_turn_relative_offset_m, -0.20)
      self.assertEqual(result.tracking_state, 'NEUTRAL')

  def test_center_state_does_not_invent_inside_or_outside(self):
    api = self.api()
    result = api.observe_recenter_condition(
      self.recenter(start=0.0, future=0.05, recentered=False),
      model_action_curvature_1pm=0.001,
      controls_desired_curvature_1pm=0.001,
      current_curvature_1pm=0.001,
      v_ego_mps=4.0,
    )
    self.assertEqual(result.start_turn_relative_state, 'CENTER')
    self.assertEqual(result.start_turn_relative_offset_m, 0.0)

  def test_sign_mismatch_or_unresolved_turn_fails_closed(self):
    api = self.api()
    cases = (
      (0.0, 0.001, 0.001, 'ACTION_TURN_UNRESOLVED'),
      (0.001, 0.0, 0.001, 'CONTROL_TURN_UNRESOLVED'),
      (0.001, -0.001, -0.001, 'ACTION_CONTROL_SIGN_MISMATCH'),
    )
    for action, desired, current, reason in cases:
      with self.subTest(reason=reason):
        result = api.observe_recenter_condition(
          self.recenter(),
          model_action_curvature_1pm=action,
          controls_desired_curvature_1pm=desired,
          current_curvature_1pm=current,
          v_ego_mps=5.0,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, reason)
        self.assertIsNone(result.start_turn_relative_state)
        self.assertFalse(result.vehicle_activation_allowed)

  def test_nonfinite_or_negative_speed_fails_closed(self):
    api = self.api()
    cases = (
      (math.nan, 0.001, 0.001, 5.0, 'NONFINITE_INPUT'),
      (0.001, math.inf, 0.001, 5.0, 'NONFINITE_INPUT'),
      (0.001, 0.001, math.nan, 5.0, 'NONFINITE_INPUT'),
      (0.001, 0.001, 0.001, math.inf, 'NONFINITE_INPUT'),
      (0.001, 0.001, 0.001, -0.1, 'INVALID_SPEED'),
    )
    for action, desired, current, speed, reason in cases:
      with self.subTest(reason=reason):
        result = api.observe_recenter_condition(
          self.recenter(),
          model_action_curvature_1pm=action,
          controls_desired_curvature_1pm=desired,
          current_curvature_1pm=current,
          v_ego_mps=speed,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, reason)

  def test_forged_or_internally_inconsistent_recenter_observation_fails_closed(self):
    api = self.api()
    valid = self.recenter()
    cases = (
      replace(valid, start_abs_offset_m=9.0),
      replace(valid, future_abs_offset_m=9.0),
      replace(valid, abs_offset_delta_m=9.0),
      replace(valid, retained_abs_offset_fraction=9.0),
      replace(valid, recentered=False),
      replace(valid, same_side=False),
      replace(valid, start_station_m=7.0, future_station_m=6.75),
      replace(valid, sample_count=0),
      replace(valid, readiness='READY'),
      replace(valid, vehicle_status='REAL_VEHICLE_VERIFIED'),
      replace(valid, safety_status='VEHICLE_ACTIVATION_ALLOWED'),
      replace(valid, vehicle_activation_allowed=True),
    )
    for forged in cases:
      with self.subTest(forged=forged):
        result = api.observe_recenter_condition(
          forged,
          model_action_curvature_1pm=0.001,
          controls_desired_curvature_1pm=0.001,
          current_curvature_1pm=0.001,
          v_ego_mps=5.0,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'RECENTER_OBSERVATION_INVALID')
        self.assertIsNone(result.start_turn_relative_state)

  def test_blocked_recenter_observation_stays_blocked(self):
    api = self.api()
    blocked = RecenterIntentObservation(
      status='BLOCKED',
      reason='future_station_unavailable',
      sample_count=0,
      start_station_m=None,
      future_station_m=None,
      start_offset_m=None,
      future_offset_m=None,
      start_abs_offset_m=None,
      future_abs_offset_m=None,
      abs_offset_delta_m=None,
      retained_abs_offset_fraction=None,
      same_side=None,
      recentered=None,
    )
    result = api.observe_recenter_condition(
      blocked,
      model_action_curvature_1pm=0.001,
      controls_desired_curvature_1pm=0.001,
      current_curvature_1pm=0.001,
      v_ego_mps=5.0,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'RECENTER_OBSERVATION_BLOCKED')

  def test_result_is_frozen_and_has_no_control_authority(self):
    api = self.api()
    result = api.observe_recenter_condition(
      self.recenter(),
      model_action_curvature_1pm=0.001,
      controls_desired_curvature_1pm=0.001,
      current_curvature_1pm=0.001,
      v_ego_mps=5.0,
    )
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))
    self.assertIsNone(getattr(result, 'accepted', None))


if __name__ == '__main__':
  unittest.main()
