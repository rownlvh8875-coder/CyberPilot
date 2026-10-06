from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
import math
import unittest

from openpilot.tools.cyber_autotune.recenter_condition import observe_recenter_condition
from openpilot.tools.cyber_autotune.recenter_intent import RecenterIntentObservation


class TestActionHorizonConvergence(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.action_horizon_convergence'
    self.assertIsNotNone(importlib.util.find_spec(name), 'action horizon convergence diagnostic not implemented')
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

  def test_inside_offset_with_opposite_slope_is_converging(self):
    api = self.api()
    result = api.observe_action_horizon_convergence(
      self.condition(),
      path_minus_lane_m=0.20,
      path_minus_lane_slope_per_m=-0.02,
    )

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertAlmostEqual(result.turn_relative_offset_m, 0.20)
    self.assertAlmostEqual(result.turn_relative_slope_per_m, -0.02)
    self.assertEqual(result.offset_side, 'INSIDE')
    self.assertEqual(result.convergence_state, 'CONVERGING')
    self.assertTrue(result.locally_converging)
    self.assertTrue(result.recentered)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_inside_offset_with_same_direction_slope_is_diverging(self):
    api = self.api()
    result = api.observe_action_horizon_convergence(
      self.condition(),
      path_minus_lane_m=0.20,
      path_minus_lane_slope_per_m=0.02,
    )
    self.assertEqual(result.offset_side, 'INSIDE')
    self.assertEqual(result.convergence_state, 'DIVERGING')
    self.assertFalse(result.locally_converging)

  def test_outside_offset_uses_general_offset_times_slope_rule(self):
    api = self.api()
    converging = api.observe_action_horizon_convergence(
      self.condition(),
      path_minus_lane_m=-0.20,
      path_minus_lane_slope_per_m=0.02,
    )
    diverging = api.observe_action_horizon_convergence(
      self.condition(),
      path_minus_lane_m=-0.20,
      path_minus_lane_slope_per_m=-0.02,
    )

    self.assertEqual(converging.offset_side, 'OUTSIDE')
    self.assertEqual(converging.convergence_state, 'CONVERGING')
    self.assertTrue(converging.locally_converging)
    self.assertEqual(diverging.convergence_state, 'DIVERGING')
    self.assertFalse(diverging.locally_converging)

  def test_mirrored_turn_preserves_turn_relative_state(self):
    api = self.api()
    positive = api.observe_action_horizon_convergence(
      self.condition(action=0.010, desired=0.009, current=0.008, start=0.30, future=0.20),
      path_minus_lane_m=0.20,
      path_minus_lane_slope_per_m=-0.02,
    )
    negative = api.observe_action_horizon_convergence(
      self.condition(action=-0.010, desired=-0.009, current=-0.008, start=-0.30, future=-0.20),
      path_minus_lane_m=-0.20,
      path_minus_lane_slope_per_m=0.02,
    )

    self.assertAlmostEqual(positive.turn_relative_offset_m, negative.turn_relative_offset_m)
    self.assertAlmostEqual(positive.turn_relative_slope_per_m, negative.turn_relative_slope_per_m)
    self.assertEqual(positive.offset_side, negative.offset_side)
    self.assertEqual(positive.convergence_state, negative.convergence_state)

  def test_center_and_flat_are_exact_descriptive_states(self):
    api = self.api()
    center = api.observe_action_horizon_convergence(
      self.condition(),
      path_minus_lane_m=0.0,
      path_minus_lane_slope_per_m=-0.02,
    )
    flat = api.observe_action_horizon_convergence(
      self.condition(),
      path_minus_lane_m=0.20,
      path_minus_lane_slope_per_m=0.0,
    )

    self.assertEqual(center.offset_side, 'CENTER')
    self.assertEqual(center.convergence_state, 'CENTER')
    self.assertFalse(center.locally_converging)
    self.assertEqual(flat.offset_side, 'INSIDE')
    self.assertEqual(flat.convergence_state, 'FLAT')
    self.assertFalse(flat.locally_converging)

  def test_nonfinite_geometry_fails_closed(self):
    api = self.api()
    for offset, slope in ((math.nan, 0.0), (0.0, math.inf), (-math.inf, 0.0)):
      with self.subTest(offset=offset, slope=slope):
        result = api.observe_action_horizon_convergence(
          self.condition(),
          path_minus_lane_m=offset,
          path_minus_lane_slope_per_m=slope,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'NONFINITE_GEOMETRY')
        self.assertFalse(result.vehicle_activation_allowed)

  def test_offset_slope_product_overflow_fails_closed(self):
    api = self.api()
    result = api.observe_action_horizon_convergence(
      self.condition(),
      path_minus_lane_m=1e308,
      path_minus_lane_slope_per_m=1e308,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'DERIVED_VALUE_INVALID')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_blocked_or_forged_upstream_condition_fails_closed(self):
    api = self.api()
    blocked = observe_recenter_condition(
      self.recenter(),
      model_action_curvature_1pm=0.0,
      controls_desired_curvature_1pm=0.009,
      current_curvature_1pm=0.008,
      v_ego_mps=8.0,
    )
    forged = replace(self.condition(), recentered=False)

    blocked_result = api.observe_action_horizon_convergence(
      blocked,
      path_minus_lane_m=0.2,
      path_minus_lane_slope_per_m=-0.02,
    )
    forged_result = api.observe_action_horizon_convergence(
      forged,
      path_minus_lane_m=0.2,
      path_minus_lane_slope_per_m=-0.02,
    )

    self.assertEqual(blocked_result.reason, 'RECENTER_CONDITION_BLOCKED')
    self.assertEqual(forged_result.reason, 'RECENTER_CONDITION_INVALID')

  def test_forged_authority_or_tracking_identity_fails_closed(self):
    api = self.api()
    cases = (
      replace(self.condition(), vehicle_activation_allowed=True),
      replace(self.condition(), tracking_abs_error_1pm=0.5),
      replace(self.condition(), future_station_m=0.0),
    )
    for forged in cases:
      with self.subTest(forged=forged):
        result = api.observe_action_horizon_convergence(
          forged,
          path_minus_lane_m=0.2,
          path_minus_lane_slope_per_m=-0.02,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'RECENTER_CONDITION_INVALID')

  def test_result_is_frozen_and_has_no_command_surface(self):
    api = self.api()
    result = api.observe_action_horizon_convergence(
      self.condition(),
      path_minus_lane_m=0.20,
      path_minus_lane_slope_per_m=-0.02,
    )
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))


if __name__ == '__main__':
  unittest.main()
