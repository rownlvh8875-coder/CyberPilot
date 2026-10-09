"""Architecture guards, not candidate performance tests."""
import dataclasses
import math
import unittest

from openpilot.tools.cyber_autotune import candidate_role_contracts as c
from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import candidate_architecture_probe as p


def core_input(**changes):
  return dict(desired_curvature_1pm=0.001, actual_curvature_1pm=0., speed_mps=10., roll_rad=0.,
              time_s=0., dt_s=0.01, active=True, steering_pressed=False, safety_limited=False,
              curvature_limited=False, **changes)


def output():
  return c.TrajectoryAuthorityOutput(0.2, None, None, None, None, None, None, 'UNAVAILABLE',
                                     'a' * 64, 'b' * 64)


class TestRoleContracts(unittest.TestCase):
  def test_core_exact_input(self):
    self.assertEqual(c.TrajectoryInput.parse(core_input()).speed_mps, 10.)

  def test_unknown_input(self):
    with self.assertRaises(ValueError):
      c.TrajectoryInput.parse({**core_input(), 'unknown': 1})

  def test_lane_contamination(self):
    for key in ('lane_center', 'modelV2', 'path', 'candidate_output', 'future_truth', 'plant_state'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        c.TrajectoryInput.parse({**core_input(), key: 0})

  def test_nonfinite(self):
    for key in ('desired_curvature_1pm', 'speed_mps', 'time_s', 'roll_rad'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        c.TrajectoryInput.parse({**core_input(), key: math.nan})

  def test_timebase(self):
    with self.assertRaises(ValueError):
      c.TrajectoryInput.parse({**core_input(), 'dt_s': 0.02})

  def test_bool_strict(self):
    with self.assertRaises(ValueError):
      c.TrajectoryInput.parse({**core_input(), 'active': 1})

  def test_direct_construction_validates(self):
    with self.assertRaises(ValueError):
      c.TrajectoryInput(**{**core_input(), 'speed_mps': -1})

  def test_frozen_input(self):
    with self.assertRaises(dataclasses.FrozenInstanceError):
      c.TrajectoryInput.parse(core_input()).speed_mps = 2

  def test_governor_exact_whitelist(self):
    row = {'time_s': 0., 'dt_s': 0.01, 'active': True, 'steering_pressed': False, 'release': False, 'reengagement': False}
    self.assertEqual(c.InterventionInput.parse(row).dt_s, 0.01)
    for key in ('desired_curvature_1pm', 'tracking_error', 'lane', 'modelV2', 'path'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        c.InterventionInput.parse({**row, key: 0})

  def test_output_unavailable_not_zero(self):
    self.assertIsNone(output().pre_limit_intent)
    self.assertIsNone(output().feedback_component)

  def test_output_limit(self):
    with self.assertRaises(ValueError):
      dataclasses.replace(output(), raw_requested_torque=384.)

  def test_fake_observability(self):
    with self.assertRaises(ValueError):
      dataclasses.replace(output(), pre_limit_intent=0.)

  def test_source_identity(self):
    with self.assertRaises(ValueError):
      dataclasses.replace(output(), source_sha256='unknown')

  def test_disabled_passthrough(self):
    row = c.InterventionInput(0., .01, True, False, False, False)
    result = a.SmoothnessGovernor().update(output().for_governor(), row)
    self.assertEqual(result.final_requested_torque, output().raw_requested_torque)
    self.assertEqual(result.pre_governor, result.post_governor)
    self.assertEqual(result.governor_state, ())

  def test_governor_cannot_receive_core_observations(self):
    with self.assertRaises(ValueError):
      a.SmoothnessGovernor().update(output(), c.InterventionInput(0., .01, True, False, False, False))

  def test_governor_enabled_blocked(self):
    with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
      a.SmoothnessGovernor(enabled=True)

  def test_core_blocked(self):
    with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
      a.TrajectoryAuthorityCore().update(c.TrajectoryInput.parse(core_input()))

  def test_composition_blocked(self):
    with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
      a.compose()

  def test_search_blocked(self):
    with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
      a.authorize_execution('DEVELOPMENT_SCREEN')

  def test_probe_only(self):
    self.assertIsNone(a.authorize_execution('ARCHITECTURE_PROBE'))

  def test_ownership(self):
    a.validate_ownership(a.OWNERS)

  def test_duplicate_state_owner(self):
    with self.assertRaises(ValueError):
      a.validate_ownership(a.OWNERS + (a.OWNERS[0],))

  def test_delay_owner(self):
    wrong = tuple((s, 'SG' if s == 'physical_delay' else o) for s, o in a.OWNERS)
    with self.assertRaises(ValueError):
      a.validate_ownership(wrong)

  def test_hidden_queue(self):
    with self.assertRaises(ValueError):
      a.validate_ownership(a.OWNERS + (('second_physical_queue', 'SG'),))

  def test_reset_complete(self):
    a.validate_resets(a.RESETS)

  def test_reset_missing(self):
    with self.assertRaises(ValueError):
      a.validate_resets(a.RESETS[:-1])

  def test_reset_wrong_owner(self):
    rows = list(a.RESETS)
    rows[0] = (*rows[0][:2], 'RETAIN_IMPLICITLY')
    with self.assertRaises(ValueError):
      a.validate_resets(tuple(rows))

  def test_identity_config_binding(self):
    self.assertNotEqual(a.identity('TA', {'schema': 'PENDING'}), a.identity('TA', {'schema': 'CHANGED'}))

  def test_separate_identities(self):
    self.assertNotEqual(a.identity('TA', {}), a.identity('SG', {}))

  def test_identity_frozen(self):
    with self.assertRaises(dataclasses.FrozenInstanceError):
      a.identity('TA', {}).role = 'SG'

  def test_identity_missing_sha(self):
    with self.assertRaises(ValueError):
      dataclasses.replace(a.identity('TA', {}), plant_sha256='')

  def test_current_alias(self):
    self.assertEqual(a.HISTORY['CURRENT'], 'BASELINE_EXACT')
    self.assertEqual(a.HISTORY['V1'], 'TRADEOFF_ONLY')
    self.assertEqual(a.HISTORY['V2'], 'REJECTED')

  def test_no_retroactive_role(self):
    self.assertEqual(a.HISTORICAL_ROLES, ('MIXED_HISTORICAL', 'MIXED_HISTORICAL'))

  def test_no_fake_arm(self):
    with self.assertRaises(ValueError):
      a.validate_matrix({**a.matrix(), 'current_alias': False})

  def test_composed_arm_not_authorized(self):
    with self.assertRaises(ValueError):
      a.validate_matrix({**a.matrix(), 'composition_execution_allowed': True})

  def test_no_weighted_score(self):
    self.assertNotIn('weighted_score', a.matrix())
    self.assertEqual(a.matrix()['objective_combination'], 'NO_COMPENSATION_ACROSS_HARD_FAILURES')

  def test_probe_deterministic(self):
    self.assertEqual(p.run(), p.run())

  def test_positive_controls(self):
    report = p.run()
    self.assertTrue(report['trajectory']['analytic_sign_and_amplitude_order'])
    self.assertTrue(report['smoothness']['derivative_and_reversals_detected'])

  def test_negative_controls(self):
    self.assertTrue(p.run()['negative']['disabled_passthrough_exact'])
    self.assertTrue(p.run()['negative']['identical_reset_exact'])

  def test_no_algorithm_probe(self):
    self.assertEqual(p.run()['scope'], 'FIXTURE_OBSERVABILITY_ONLY_NO_CANDIDATE_ALGORITHM')

  def test_readiness(self):
    r = a.readiness()
    self.assertFalse(r['search_execution_allowed'])
    self.assertFalse(r['composed_implementation_authorized'])
    self.assertEqual(r['sealed_reference'], 'NOT_GENERATED')

  def test_reference_blockers(self):
    self.assertIn('INDEPENDENT_REFERENCE_UNAVAILABLE', a.readiness()['reference_track'])
    self.assertIn('CALIBRATION_UNCERTAINTY_PENDING', a.readiness()['reference_track'])

  def test_no_vehicle_authority(self):
    self.assertFalse(a.readiness()['vehicle_activation_allowed'])
    self.assertFalse(a.readiness()['production_authority'])

  def test_no_parameter_range(self):
    for role in ('TA', 'SG'):
      policy = a.search_policy(role)
      self.assertEqual(policy['status'], 'NOT_FROZEN')
      self.assertIsNone(policy['ranges'])
      self.assertFalse(policy['execution_allowed'])


if __name__ == '__main__':
  unittest.main()
