from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
import math
import unittest

from openpilot.tools.cyber_autotune.action_horizon_convergence import ActionHorizonConvergenceObservation


class TestPositionOrientationSeparation(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.position_orientation_separation'
    self.assertIsNotNone(importlib.util.find_spec(name), 'position/orientation separation diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def convergence(*, offset=0.20, slope=0.02, turn=1):
    turn_offset = offset * turn
    turn_slope = slope * turn
    if turn_offset > 0:
      side = 'INSIDE'
    elif turn_offset < 0:
      side = 'OUTSIDE'
    else:
      side = 'CENTER'
    if offset == 0.0:
      state = 'CENTER'
    elif slope == 0.0:
      state = 'FLAT'
    elif offset * slope < 0.0:
      state = 'CONVERGING'
    else:
      state = 'DIVERGING'
    return ActionHorizonConvergenceObservation(
      status='DESCRIPTIVE_ONLY',
      reason='ok',
      path_minus_lane_m=offset,
      path_minus_lane_slope_per_m=slope,
      turn_relative_offset_m=turn_offset,
      turn_relative_slope_per_m=turn_slope,
      offset_side=side,
      convergence_state=state,
      locally_converging=state == 'CONVERGING',
      recentered=False,
    )

  def test_diverging_inside_can_have_orientation_less_turn_than_lane(self):
    api = self.api()
    result = api.observe_position_orientation_separation(
      self.convergence(offset=0.20, slope=0.02, turn=1),
      lane_center_slope_per_m=0.03,
      model_orientation_yaw_rad=math.atan(0.02),
    )
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.geometry_state, 'DIVERGING')
    self.assertEqual(result.offset_side, 'INSIDE')
    self.assertEqual(result.orientation_relation, 'LESS_TURN_THAN_LANE')
    self.assertLess(result.turn_relative_orientation_minus_lane_yaw_rad, 0.0)
    self.assertEqual(result.combined_state, 'DIVERGING_INSIDE__LESS_TURN_THAN_LANE')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_diverging_inside_more_turn_is_distinct_state(self):
    api = self.api()
    result = api.observe_position_orientation_separation(
      self.convergence(offset=0.20, slope=0.02, turn=1),
      lane_center_slope_per_m=0.01,
      model_orientation_yaw_rad=math.atan(0.03),
    )
    self.assertEqual(result.orientation_relation, 'MORE_TURN_THAN_LANE')
    self.assertGreater(result.turn_relative_orientation_minus_lane_yaw_rad, 0.0)
    self.assertEqual(result.combined_state, 'DIVERGING_INSIDE__MORE_TURN_THAN_LANE')

  def test_exact_lane_tangent_match_is_preserved(self):
    api = self.api()
    lane_slope = 0.02
    result = api.observe_position_orientation_separation(
      self.convergence(offset=0.20, slope=0.02, turn=1),
      lane_center_slope_per_m=lane_slope,
      model_orientation_yaw_rad=math.atan(lane_slope),
    )
    self.assertEqual(result.orientation_relation, 'LANE_TANGENT_MATCH')
    self.assertAlmostEqual(result.turn_relative_orientation_minus_lane_yaw_rad, 0.0)

  def test_mirrored_turn_preserves_normalized_relation(self):
    api = self.api()
    pos = api.observe_position_orientation_separation(
      self.convergence(offset=0.20, slope=0.02, turn=1),
      lane_center_slope_per_m=0.03,
      model_orientation_yaw_rad=math.atan(0.02),
    )
    neg = api.observe_position_orientation_separation(
      self.convergence(offset=-0.20, slope=-0.02, turn=-1),
      lane_center_slope_per_m=-0.03,
      model_orientation_yaw_rad=math.atan(-0.02),
    )
    self.assertEqual(pos.geometry_state, neg.geometry_state)
    self.assertEqual(pos.offset_side, neg.offset_side)
    self.assertEqual(pos.orientation_relation, neg.orientation_relation)
    self.assertAlmostEqual(
      pos.turn_relative_orientation_minus_lane_yaw_rad,
      neg.turn_relative_orientation_minus_lane_yaw_rad,
    )

  def test_nonfinite_orientation_inputs_fail_closed(self):
    api = self.api()
    cases = ((math.nan, 0.0), (0.0, math.inf), (-math.inf, 0.0))
    for lane_slope, yaw in cases:
      with self.subTest(lane_slope=lane_slope, yaw=yaw):
        result = api.observe_position_orientation_separation(
          self.convergence(),
          lane_center_slope_per_m=lane_slope,
          model_orientation_yaw_rad=yaw,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'NONFINITE_ORIENTATION_GEOMETRY')

  def test_centered_offset_cannot_recover_turn_sign(self):
    api = self.api()
    result = api.observe_position_orientation_separation(
      self.convergence(offset=0.0, slope=0.02, turn=1),
      lane_center_slope_per_m=0.01,
      model_orientation_yaw_rad=0.02,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'TURN_UNRESOLVED')

  def test_blocked_or_forged_upstream_fails_closed(self):
    api = self.api()
    blocked = replace(self.convergence(), status='BLOCKED', reason='NONFINITE_GEOMETRY')
    forged = replace(self.convergence(), convergence_state='CONVERGING')
    blocked_result = api.observe_position_orientation_separation(
      blocked, lane_center_slope_per_m=0.01, model_orientation_yaw_rad=0.02,
    )
    forged_result = api.observe_position_orientation_separation(
      forged, lane_center_slope_per_m=0.01, model_orientation_yaw_rad=0.02,
    )
    self.assertEqual(blocked_result.reason, 'ACTION_HORIZON_CONVERGENCE_BLOCKED')
    self.assertEqual(forged_result.reason, 'ACTION_HORIZON_CONVERGENCE_INVALID')

  def test_forged_turn_normalization_or_authority_fails_closed(self):
    api = self.api()
    cases = (
      replace(self.convergence(), turn_relative_offset_m=99.0),
      replace(self.convergence(), vehicle_activation_allowed=True),
      replace(self.convergence(), locally_converging=True),
    )
    for forged in cases:
      with self.subTest(forged=forged):
        result = api.observe_position_orientation_separation(
          forged, lane_center_slope_per_m=0.01, model_orientation_yaw_rad=0.02,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'ACTION_HORIZON_CONVERGENCE_INVALID')

  def test_centered_forged_authority_is_invalid_not_merely_unresolved(self):
    api = self.api()
    forged = replace(
      self.convergence(offset=0.0, slope=0.02, turn=1),
      vehicle_activation_allowed=True,
    )
    result = api.observe_position_orientation_separation(
      forged,
      lane_center_slope_per_m=0.01,
      model_orientation_yaw_rad=0.02,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'ACTION_HORIZON_CONVERGENCE_INVALID')

  def test_result_is_frozen_and_has_no_correction_surface(self):
    api = self.api()
    result = api.observe_position_orientation_separation(
      self.convergence(),
      lane_center_slope_per_m=0.01,
      model_orientation_yaw_rad=0.02,
    )
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'
    self.assertIsNone(getattr(result, 'candidate_action', None))
    self.assertIsNone(getattr(result, 'delta_curvature', None))
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))


if __name__ == '__main__':
  unittest.main()
