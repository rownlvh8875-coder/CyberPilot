from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
import math
import unittest

from openpilot.tools.cyber_autotune.action_horizon_convergence import ActionHorizonConvergenceObservation


class TestPixelActionHorizonConsistency(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.pixel_action_horizon_consistency'
    self.assertIsNotNone(importlib.util.find_spec(name), 'pixel action-horizon consistency diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def model_observation(*, offset=0.20, slope=-0.02, turn=1, recentered=True):
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
      recentered=recentered,
    )

  def test_reports_convergence_and_offset_sign_agreement_without_authority(self):
    api = self.api()
    result = api.observe_pixel_action_horizon_consistency(
      self.model_observation(offset=0.20, slope=-0.02),
      pixel_offset_lane_fraction=0.08,
      pixel_offset_lane_fraction_slope_per_m=-0.01,
    )

    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.reason, 'ok')
    self.assertEqual(result.model_convergence_state, 'CONVERGING')
    self.assertEqual(result.pixel_convergence_state, 'CONVERGING')
    self.assertTrue(result.model_locally_converging)
    self.assertTrue(result.pixel_locally_converging)
    self.assertTrue(result.convergence_agreement)
    self.assertTrue(result.offset_sign_agreement)
    self.assertIsNone(getattr(result, 'recentered', None))
    self.assertEqual(result.readiness, 'NOT_READY')
    self.assertEqual(result.vehicle_status, 'REAL_VEHICLE_UNVERIFIED')
    self.assertEqual(result.safety_status, 'VEHICLE_ACTIVATION_BLOCKED')
    self.assertFalse(result.vehicle_activation_allowed)

  def test_reports_consistent_divergence(self):
    api = self.api()
    result = api.observe_pixel_action_horizon_consistency(
      self.model_observation(offset=-0.20, slope=-0.02, recentered=False),
      pixel_offset_lane_fraction=-0.07,
      pixel_offset_lane_fraction_slope_per_m=-0.005,
    )
    self.assertEqual(result.model_convergence_state, 'DIVERGING')
    self.assertEqual(result.pixel_convergence_state, 'DIVERGING')
    self.assertTrue(result.convergence_agreement)
    self.assertTrue(result.offset_sign_agreement)
    self.assertIsNone(getattr(result, 'recentered', None))

  def test_reports_disagreement_descriptively_without_promotion(self):
    api = self.api()
    result = api.observe_pixel_action_horizon_consistency(
      self.model_observation(offset=0.20, slope=-0.02),
      pixel_offset_lane_fraction=0.08,
      pixel_offset_lane_fraction_slope_per_m=0.01,
    )
    self.assertEqual(result.model_convergence_state, 'CONVERGING')
    self.assertEqual(result.pixel_convergence_state, 'DIVERGING')
    self.assertFalse(result.convergence_agreement)
    self.assertTrue(result.offset_sign_agreement)
    self.assertFalse(result.vehicle_activation_allowed)
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))

  def test_pixel_center_and_flat_are_exact_states(self):
    api = self.api()
    center = api.observe_pixel_action_horizon_consistency(
      self.model_observation(offset=0.0, slope=-0.02),
      pixel_offset_lane_fraction=0.0,
      pixel_offset_lane_fraction_slope_per_m=0.01,
    )
    flat = api.observe_pixel_action_horizon_consistency(
      self.model_observation(offset=0.20, slope=0.0),
      pixel_offset_lane_fraction=0.08,
      pixel_offset_lane_fraction_slope_per_m=0.0,
    )
    self.assertEqual(center.pixel_convergence_state, 'CENTER')
    self.assertIsNone(center.offset_sign_agreement)
    self.assertEqual(flat.pixel_convergence_state, 'FLAT')
    self.assertTrue(flat.offset_sign_agreement)

  def test_mirrored_coordinates_preserve_consistency(self):
    api = self.api()
    a = api.observe_pixel_action_horizon_consistency(
      self.model_observation(offset=0.20, slope=-0.02, turn=1),
      pixel_offset_lane_fraction=0.08,
      pixel_offset_lane_fraction_slope_per_m=-0.01,
    )
    b = api.observe_pixel_action_horizon_consistency(
      self.model_observation(offset=-0.20, slope=0.02, turn=-1),
      pixel_offset_lane_fraction=-0.08,
      pixel_offset_lane_fraction_slope_per_m=0.01,
    )
    self.assertEqual(a.model_convergence_state, b.model_convergence_state)
    self.assertEqual(a.pixel_convergence_state, b.pixel_convergence_state)
    self.assertEqual(a.convergence_agreement, b.convergence_agreement)
    self.assertEqual(a.offset_sign_agreement, b.offset_sign_agreement)

  def test_nonfinite_pixel_values_fail_closed(self):
    api = self.api()
    for offset, slope in ((math.nan, 0.0), (0.0, math.inf), (-math.inf, 0.0)):
      with self.subTest(offset=offset, slope=slope):
        result = api.observe_pixel_action_horizon_consistency(
          self.model_observation(),
          pixel_offset_lane_fraction=offset,
          pixel_offset_lane_fraction_slope_per_m=slope,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'NONFINITE_PIXEL_REFERENCE')
        self.assertFalse(result.vehicle_activation_allowed)

  def test_pixel_product_overflow_fails_closed(self):
    api = self.api()
    result = api.observe_pixel_action_horizon_consistency(
      self.model_observation(),
      pixel_offset_lane_fraction=1e308,
      pixel_offset_lane_fraction_slope_per_m=1e308,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'PIXEL_DERIVED_VALUE_INVALID')

  def test_blocked_or_forged_model_observation_fails_closed(self):
    api = self.api()
    blocked = replace(self.model_observation(), status='BLOCKED', reason='NONFINITE_GEOMETRY')
    forged = replace(self.model_observation(), locally_converging=False)
    blocked_result = api.observe_pixel_action_horizon_consistency(
      blocked,
      pixel_offset_lane_fraction=0.08,
      pixel_offset_lane_fraction_slope_per_m=-0.01,
    )
    forged_result = api.observe_pixel_action_horizon_consistency(
      forged,
      pixel_offset_lane_fraction=0.08,
      pixel_offset_lane_fraction_slope_per_m=-0.01,
    )
    self.assertEqual(blocked_result.reason, 'ACTION_HORIZON_CONVERGENCE_BLOCKED')
    self.assertEqual(forged_result.reason, 'ACTION_HORIZON_CONVERGENCE_INVALID')

  def test_forged_authority_or_turn_normalization_fails_closed(self):
    api = self.api()
    cases = (
      replace(self.model_observation(), vehicle_activation_allowed=True),
      replace(self.model_observation(), turn_relative_offset_m=99.0),
      replace(self.model_observation(), convergence_state='DIVERGING'),
    )
    for forged in cases:
      with self.subTest(forged=forged):
        result = api.observe_pixel_action_horizon_consistency(
          forged,
          pixel_offset_lane_fraction=0.08,
          pixel_offset_lane_fraction_slope_per_m=-0.01,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'ACTION_HORIZON_CONVERGENCE_INVALID')

  def test_result_is_frozen(self):
    api = self.api()
    result = api.observe_pixel_action_horizon_consistency(
      self.model_observation(),
      pixel_offset_lane_fraction=0.08,
      pixel_offset_lane_fraction_slope_per_m=-0.01,
    )
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'


if __name__ == '__main__':
  unittest.main()
