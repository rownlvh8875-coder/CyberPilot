from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
import math
import unittest

from openpilot.tools.cyber_autotune.action_horizon_convergence import ActionHorizonConvergenceObservation
from openpilot.tools.cyber_autotune.position_orientation_separation import observe_position_orientation_separation


class TestPositionOrientationPersistence(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.position_orientation_persistence'
    self.assertIsNotNone(importlib.util.find_spec(name), 'position/orientation persistence diagnostic not implemented')
    return importlib.import_module(name)

  @staticmethod
  def convergence(*, offset=0.20, slope=0.02, turn=1):
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
      recentered=False,
    )

  @classmethod
  def obs(cls, *, more_turn=False, turn=1):
    lane_slope = 0.02 * turn
    model_slope = 0.03 * turn if more_turn else 0.01 * turn
    return observe_position_orientation_separation(
      cls.convergence(offset=0.20 * turn, slope=0.02 * turn, turn=turn),
      lane_center_slope_per_m=lane_slope,
      model_orientation_yaw_rad=math.atan(model_slope),
    )

  def test_groups_same_state_within_gap(self):
    api = self.api()
    obs = self.obs(more_turn=False)
    result = api.observe_position_orientation_persistence(
      ((0.00, obs), (0.05, obs), (0.10, obs)),
      max_gap_s=0.075,
    )
    self.assertEqual(result.status, 'DESCRIPTIVE_ONLY')
    self.assertEqual(result.sample_count, 3)
    self.assertEqual(result.run_count, 1)
    run = result.runs[0]
    self.assertEqual(run.combined_state, obs.combined_state)
    self.assertEqual(run.sample_count, 3)
    self.assertAlmostEqual(run.start_time_s, 0.0)
    self.assertAlmostEqual(run.end_time_s, 0.10)
    self.assertAlmostEqual(run.span_s, 0.10)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_state_change_splits_run(self):
    api = self.api()
    less = self.obs(more_turn=False)
    more = self.obs(more_turn=True)
    result = api.observe_position_orientation_persistence(
      ((0.00, less), (0.05, less), (0.10, more), (0.15, more)),
      max_gap_s=0.075,
    )
    self.assertEqual(result.run_count, 2)
    self.assertEqual(result.runs[0].orientation_relation, 'LESS_TURN_THAN_LANE')
    self.assertEqual(result.runs[1].orientation_relation, 'MORE_TURN_THAN_LANE')
    self.assertEqual(result.runs[0].sample_count, 2)
    self.assertEqual(result.runs[1].sample_count, 2)

  def test_large_gap_splits_same_state(self):
    api = self.api()
    obs = self.obs()
    result = api.observe_position_orientation_persistence(
      ((0.00, obs), (0.05, obs), (0.20, obs)),
      max_gap_s=0.075,
    )
    self.assertEqual(result.run_count, 2)
    self.assertEqual(tuple(run.sample_count for run in result.runs), (2, 1))
    self.assertAlmostEqual(result.runs[1].span_s, 0.0)

  def test_mirrored_turn_has_same_state_identity(self):
    api = self.api()
    positive = self.obs(more_turn=False, turn=1)
    negative = self.obs(more_turn=False, turn=-1)
    self.assertEqual(positive.combined_state, negative.combined_state)
    result = api.observe_position_orientation_persistence(
      ((0.00, positive), (0.05, negative)),
      max_gap_s=0.075,
    )
    self.assertEqual(result.run_count, 1)
    self.assertEqual(result.runs[0].orientation_relation, 'LESS_TURN_THAN_LANE')

  def test_empty_samples_fail_closed(self):
    api = self.api()
    result = api.observe_position_orientation_persistence((), max_gap_s=0.075)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'NO_SAMPLES')

  def test_invalid_gap_fails_closed(self):
    api = self.api()
    obs = self.obs()
    for gap in (0.0, -0.1, math.nan, math.inf):
      with self.subTest(gap=gap):
        result = api.observe_position_orientation_persistence(((0.0, obs),), max_gap_s=gap)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'INVALID_MAX_GAP')

  def test_timestamps_must_be_finite_and_strictly_increasing(self):
    api = self.api()
    obs = self.obs()
    cases = (
      ((math.nan, obs),),
      ((0.0, obs), (0.0, obs)),
      ((0.1, obs), (0.05, obs)),
    )
    for samples in cases:
      with self.subTest(samples=samples):
        result = api.observe_position_orientation_persistence(samples, max_gap_s=0.075)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.reason, 'INVALID_TIMESTAMPS')

  def test_forged_observation_fails_closed(self):
    api = self.api()
    valid = self.obs()
    forged = replace(valid, vehicle_activation_allowed=True)
    result = api.observe_position_orientation_persistence(((0.0, forged),), max_gap_s=0.075)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'POSITION_ORIENTATION_INVALID')

  def test_forged_numeric_identity_fails_closed(self):
    api = self.api()
    valid = self.obs()
    forged = replace(valid, lane_center_yaw_rad=valid.lane_center_yaw_rad + 0.1)
    result = api.observe_position_orientation_persistence(((0.0, forged),), max_gap_s=0.075)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.reason, 'POSITION_ORIENTATION_INVALID')

  def test_result_and_runs_are_frozen_and_have_no_decision_surface(self):
    api = self.api()
    obs = self.obs()
    result = api.observe_position_orientation_persistence(((0.0, obs),), max_gap_s=0.075)
    with self.assertRaises(FrozenInstanceError):
      result.status = 'READY'
    with self.assertRaises(FrozenInstanceError):
      result.runs[0].span_s = 1.0
    self.assertIsNone(getattr(result, 'accepted', None))
    self.assertIsNone(getattr(result, 'command', None))
    self.assertIsNone(getattr(result, 'tune', None))
    self.assertIsNone(getattr(result, 'threshold_pass', None))


if __name__ == '__main__':
  unittest.main()
