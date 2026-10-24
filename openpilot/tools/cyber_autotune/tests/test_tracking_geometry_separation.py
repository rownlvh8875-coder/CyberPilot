from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
import math
import unittest

from openpilot.tools.cyber_autotune.action_horizon_convergence import ActionHorizonConvergenceObservation


class TestTrackingGeometrySeparation(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.tracking_geometry_separation'
    self.assertIsNotNone(importlib.util.find_spec(name), 'tracking geometry separation diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def model(*, offset=0.20, slope=-0.02, turn=1):
    turn_offset = offset * turn
    turn_slope = slope * turn
    side = 'INSIDE' if turn_offset > 0.0 else 'OUTSIDE' if turn_offset < 0.0 else 'CENTER'
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
      recentered=True,
    )

  def test_converging_inside_tracking_reinforces_is_separated(self):
    api = self.api()
    result = api.observe_tracking_geometry_separation(
      self.model(offset=0.20, slope=-0.02),
      future_tracking_heading_error_toward_turn_rad=0.003,
    )
    self.assertEqual(result.geometry_state, 'CONVERGING')
    self.assertEqual(result.offset_side, 'INSIDE')
    self.assertEqual(result.tracking_relation, 'REINFORCES_OFFSET')
    self.assertAlmostEqual(result.future_tracking_heading_error_toward_offset_rad, 0.003)
    self.assertEqual(result.separation_state, 'CONVERGING__REINFORCES_OFFSET')
    self.assertFalse(result.geometry_diverging)
    self.assertTrue(result.tracking_reinforces_offset)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_converging_inside_tracking_counteracts_is_separated(self):
    api = self.api()
    result = api.observe_tracking_geometry_separation(
      self.model(offset=0.20, slope=-0.02),
      future_tracking_heading_error_toward_turn_rad=-0.004,
    )
    self.assertEqual(result.tracking_relation, 'COUNTERACTS_OFFSET')
    self.assertAlmostEqual(result.future_tracking_heading_error_toward_offset_rad, -0.004)
    self.assertEqual(result.separation_state, 'CONVERGING__COUNTERACTS_OFFSET')
    self.assertFalse(result.tracking_reinforces_offset)

  def test_diverging_geometry_remains_explicit_independent_of_tracking(self):
    api = self.api()
    reinforce = api.observe_tracking_geometry_separation(
      self.model(offset=0.20, slope=0.02),
      future_tracking_heading_error_toward_turn_rad=0.003,
    )
    counteract = api.observe_tracking_geometry_separation(
      self.model(offset=0.20, slope=0.02),
      future_tracking_heading_error_toward_turn_rad=-0.003,
    )
    self.assertTrue(reinforce.geometry_diverging)
    self.assertTrue(counteract.geometry_diverging)
    self.assertEqual(reinforce.separation_state, 'DIVERGING__REINFORCES_OFFSET')
    self.assertEqual(counteract.separation_state, 'DIVERGING__COUNTERACTS_OFFSET')

  def test_outside_offset_reverses_tracking_relation(self):
    api = self.api()
    result = api.observe_tracking_geometry_separation(
      self.model(offset=-0.20, slope=0.02),
      future_tracking_heading_error_toward_turn_rad=0.003,
    )
    self.assertEqual(result.offset_side, 'OUTSIDE')
    self.assertAlmostEqual(result.future_tracking_heading_error_toward_offset_rad, -0.003)
    self.assertEqual(result.tracking_relation, 'COUNTERACTS_OFFSET')

  def test_zero_tracking_is_neutral_without_threshold(self):
    api = self.api()
    result = api.observe_tracking_geometry_separation(
      self.model(offset=0.20, slope=-0.02),
      future_tracking_heading_error_toward_turn_rad=0.0,
    )
    self.assertEqual(result.tracking_relation, 'NEUTRAL')
    self.assertFalse(result.tracking_reinforces_offset)
    self.assertEqual(result.separation_state, 'CONVERGING__NEUTRAL')

  def test_center_offset_does_not_invent_tracking_relation(self):
    api = self.api()
    result = api.observe_tracking_geometry_separation(
      self.model(offset=0.0, slope=-0.02),
      future_tracking_heading_error_toward_turn_rad=0.003,
    )
    self.assertEqual(result.offset_side, 'CENTER')
    self.assertIsNone(result.future_tracking_heading_error_toward_offset_rad)
    self.assertEqual(result.tracking_relation, 'OFFSET_UNRESOLVED')
    self.assertIsNone(result.tracking_reinforces_offset)
    self.assertEqual(result.separation_state, 'CENTER__OFFSET_UNRESOLVED')

  def test_nonfinite_future_tracking_fails_closed(self):
    api = self.api()
    for value in (math.nan, math.inf, -math.inf):
      with self.subTest(value=value):
        result = api.observe_tracking_geometry_separation(
          self.model(),
          future_tracking_heading_error_toward_turn_rad=value,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'NONFINITE_FUTURE_TRACKING')
        self.assertFalse(result.vehicle_activation_allowed)

  def test_blocked_or_forged_model_observation_fails_closed(self):
    api = self.api()
    blocked = replace(self.model(), status='BLOCKED', reason='NONFINITE_GEOMETRY')
    forged = replace(self.model(), convergence_state='DIVERGING')
    a = api.observe_tracking_geometry_separation(
      blocked,
      future_tracking_heading_error_toward_turn_rad=0.003,
    )
    b = api.observe_tracking_geometry_separation(
      forged,
      future_tracking_heading_error_toward_turn_rad=0.003,
    )
    self.assertEqual(a.reason, 'ACTION_HORIZON_CONVERGENCE_BLOCKED')
    self.assertEqual(b.reason, 'ACTION_HORIZON_CONVERGENCE_INVALID')

  def test_forged_authority_or_turn_normalization_fails_closed(self):
    api = self.api()
    cases = (
      replace(self.model(), vehicle_activation_allowed=True),
      replace(self.model(), turn_relative_offset_m=99.0),
      replace(self.model(), offset_side='OUTSIDE'),
    )
    for forged in cases:
      with self.subTest(forged=forged):
        result = api.observe_tracking_geometry_separation(
          forged,
          future_tracking_heading_error_toward_turn_rad=0.003,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'ACTION_HORIZON_CONVERGENCE_INVALID')

  def test_result_is_frozen_and_has_no_control_surface(self):
    api = self.api()
    result = api.observe_tracking_geometry_separation(
      self.model(),
      future_tracking_heading_error_toward_turn_rad=0.003,
    )
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))
    self.assertIsNone(getattr(result, 'candidate', None))


if __name__ == '__main__':
  unittest.main()
