import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.experiments import (
  LateralExperimentVariant, features_for_variant,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.optimizer import (
  CyberLateralOptimizer, OfflineOptimizerConfig, OptimizerStepInput,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.speed_aware_tune import (
  SpeedAwareTuneTable, SpeedTunePoint, evaluate_speed_aware_tune,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.steering_rate import (
  SteeringRateLimits, evaluate_steering_rate_candidate,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.torque_authority import (
  TorqueAuthorityEnvelope, TorqueAuthorityPoint, observe_torque_authority,
)


class TestSpeedAwareTune(unittest.TestCase):
  def setUp(self):
    self.table = SpeedAwareTuneTable(
      points=(
        SpeedTunePoint(5., 3., 0.1, 0.8),
        SpeedTunePoint(10., 4., 0.2, 1.0),
      ),
      provenance='approved-development-corpus-v1',
    )

  def test_interpolates_only_inside_qualified_domain(self):
    result = evaluate_speed_aware_tune(self.table, 7.5, 3.5, 0.15, 0.9)
    self.assertTrue(result.valid)
    self.assertEqual(result.reason, 'ok')
    self.assertAlmostEqual(result.lat_accel_factor, 3.5)
    self.assertAlmostEqual(result.friction, 0.15)
    self.assertAlmostEqual(result.steering_response, 0.9)
    self.assertEqual(result.provenance, self.table.provenance)

  def test_falls_back_exactly_outside_qualified_domain(self):
    result = evaluate_speed_aware_tune(self.table, 12., 3.5, 0.15, 0.9)
    self.assertFalse(result.valid)
    self.assertEqual(result.reason, 'outside_qualified_speed_domain')
    self.assertEqual((result.lat_accel_factor, result.friction, result.steering_response), (3.5, 0.15, 0.9))

  def test_rejects_missing_provenance_duplicate_speed_and_invalid_values(self):
    with self.assertRaises(ValueError):
      SpeedAwareTuneTable(self.table.points, '')
    with self.assertRaises(ValueError):
      SpeedAwareTuneTable((self.table.points[0], self.table.points[0]), 'duplicate')
    with self.assertRaises(ValueError):
      SpeedTunePoint(5., 0., 0.1, 1.)
    with self.assertRaises(ValueError):
      evaluate_speed_aware_tune(self.table, float('nan'), 3.5, 0.15, 0.9)


class TestTorqueAuthorityEnvelope(unittest.TestCase):
  def setUp(self):
    self.envelope = TorqueAuthorityEnvelope(
      points=(TorqueAuthorityPoint(5., 0.3), TorqueAuthorityPoint(10., 0.2)),
      existing_vehicle_limit=0.4,
      provenance='hkg-offline-envelope-v1',
    )

  def test_candidate_can_only_reduce_requested_authority(self):
    result = observe_torque_authority(self.envelope, 7.5, requested=0.35, applied=0.24)
    self.assertTrue(result.valid)
    self.assertAlmostEqual(result.envelope_limit, 0.25)
    self.assertAlmostEqual(result.candidate, 0.25)
    self.assertLessEqual(abs(result.candidate), abs(result.requested))
    self.assertTrue(result.envelope_limited)

  def test_classifies_vehicle_rail_rate_and_driver_limits_without_changing_applied(self):
    result = observe_torque_authority(
      self.envelope, 5., requested=-0.5, applied=-0.2,
      rate_limited=True, driver_limited=True,
    )
    self.assertEqual(result.applied, -0.2)
    self.assertTrue(result.safety_rail_requested)
    self.assertTrue(result.rate_limited)
    self.assertTrue(result.driver_limited)

  def test_reports_applied_authority_above_envelope_without_clipping_the_observation(self):
    result = observe_torque_authority(self.envelope, 7.5, requested=0.2, applied=0.3)
    self.assertTrue(result.applied_exceeds_envelope)
    self.assertGreater(result.authority_utilization, 1.)
    self.assertEqual(result.applied, 0.3)

  def test_envelope_cannot_exceed_existing_vehicle_limit(self):
    with self.assertRaises(ValueError):
      TorqueAuthorityEnvelope(
        (TorqueAuthorityPoint(5., 0.5), TorqueAuthorityPoint(10., 0.2)),
        existing_vehicle_limit=0.4,
        provenance='unsafe',
      )


class TestSteeringRateCandidate(unittest.TestCase):
  def test_limits_rise_and_release_as_an_offline_candidate(self):
    limits = SteeringRateLimits(max_magnitude_increase_per_s=0.2, max_magnitude_decrease_per_s=0.4)
    rise = evaluate_steering_rate_candidate(
      requested=1., previous_candidate=0., dt=0.5, limits=limits,
      baseline_max_magnitude_increase_per_s=0.3,
      baseline_max_magnitude_decrease_per_s=0.5,
    )
    release = evaluate_steering_rate_candidate(
      requested=0., previous_candidate=0.5, dt=0.5, limits=limits,
      baseline_max_magnitude_increase_per_s=0.3,
      baseline_max_magnitude_decrease_per_s=0.5,
    )
    self.assertAlmostEqual(rise.candidate, 0.1)
    self.assertAlmostEqual(release.candidate, 0.3)
    self.assertTrue(rise.rate_limited)
    self.assertTrue(release.rate_limited)

  def test_rejects_rates_faster_than_existing_controller(self):
    with self.assertRaises(ValueError):
      evaluate_steering_rate_candidate(
        requested=1., previous_candidate=0., dt=0.01,
        limits=SteeringRateLimits(0.4, 0.4),
        baseline_max_magnitude_increase_per_s=0.3,
        baseline_max_magnitude_decrease_per_s=0.5,
      )


class TestExperimentMatrix(unittest.TestCase):
  def test_a0_through_a5_are_exact_independent_feature_combinations(self):
    expected = {
      LateralExperimentVariant.A0: (False, False, False),
      LateralExperimentVariant.A1: (True, False, False),
      LateralExperimentVariant.A2: (False, True, False),
      LateralExperimentVariant.A3: (False, False, True),
      LateralExperimentVariant.A4: (True, True, False),
      LateralExperimentVariant.A5: (True, True, True),
    }
    for variant, flags in expected.items():
      with self.subTest(variant=variant):
        features = features_for_variant(variant)
        self.assertEqual(
          (features.speed_aware_tune, features.torque_authority_envelope, features.steering_rate_control),
          flags,
        )
        self.assertEqual(features.execution_stage, 'offline_only')
        self.assertFalse(features.live_actuator_authority)


class TestOfflineOptimizerOrchestration(unittest.TestCase):
  def setUp(self):
    self.speed_table = SpeedAwareTuneTable(
      (SpeedTunePoint(5., 3., 0.1, 0.8), SpeedTunePoint(10., 4., 0.2, 1.0)),
      'development-only-table',
    )
    self.envelope = TorqueAuthorityEnvelope(
      (TorqueAuthorityPoint(5., 0.3), TorqueAuthorityPoint(10., 0.2)),
      existing_vehicle_limit=0.4,
      provenance='development-only-envelope',
    )
    self.rate_limits = SteeringRateLimits(0.2, 0.4)

  @staticmethod
  def step(command, *, speed=7.5, applied=0.):
    return OptimizerStepInput(
      speed_mps=speed,
      baseline_command=command,
      applied_command=applied,
      dt_s=0.5,
      baseline_lat_accel_factor=3.5,
      baseline_friction=0.15,
      baseline_steering_response=0.9,
    )

  def test_a0_is_exact_stateless_baseline_parity(self):
    optimizer = CyberLateralOptimizer(OfflineOptimizerConfig(LateralExperimentVariant.A0))
    for command in (0., 0.25, -0.125, 0.4):
      result = optimizer.evaluate(OptimizerStepInput(
        speed_mps=7.5, baseline_command=command, applied_command=0., dt_s=0.01,
      ))
      self.assertTrue(result.valid)
      self.assertEqual(result.reason, 'baseline')
      self.assertEqual(result.candidate_command, command)
      self.assertFalse(result.live_actuator_authority)

  def test_a1_and_variants_containing_it_block_without_native_controller_adapter(self):
    for variant in (LateralExperimentVariant.A1, LateralExperimentVariant.A4, LateralExperimentVariant.A5):
      with self.subTest(variant=variant):
        kwargs = {'speed_tune_table': self.speed_table}
        if variant in (LateralExperimentVariant.A4, LateralExperimentVariant.A5):
          kwargs['authority_envelope'] = self.envelope
        if variant == LateralExperimentVariant.A5:
          kwargs.update(
            rate_limits=self.rate_limits,
            baseline_max_magnitude_increase_per_s=0.3,
            baseline_max_magnitude_decrease_per_s=0.5,
          )
        optimizer = CyberLateralOptimizer(OfflineOptimizerConfig(variant, **kwargs))
        result = optimizer.evaluate(self.step(0.3))
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, 'native_speed_tune_adapter_missing')
        self.assertEqual(result.candidate_command, 0.3)
        self.assertIsNotNone(result.speed_tune)

  def test_a2_applies_only_the_nonincreasing_authority_envelope(self):
    optimizer = CyberLateralOptimizer(OfflineOptimizerConfig(
      LateralExperimentVariant.A2, authority_envelope=self.envelope,
    ))
    result = optimizer.evaluate(self.step(0.35, applied=0.24))
    self.assertTrue(result.valid)
    self.assertEqual(result.reason, 'ok')
    self.assertAlmostEqual(result.candidate_command, 0.25)
    self.assertIsNotNone(result.authority)
    self.assertTrue(result.authority.envelope_limited)

  def test_a3_is_stateful_but_reset_makes_the_trace_repeatable(self):
    optimizer = CyberLateralOptimizer(OfflineOptimizerConfig(
      LateralExperimentVariant.A3,
      rate_limits=self.rate_limits,
      baseline_max_magnitude_increase_per_s=0.3,
      baseline_max_magnitude_decrease_per_s=0.5,
    ))

    def trace():
      optimizer.reset()
      return tuple(optimizer.evaluate(self.step(command)).candidate_command for command in (0., 1., 1., 0.))

    first = trace()
    second = trace()
    self.assertEqual(first, second)
    self.assertEqual(first, (0., 0.1, 0.2, 0.))

  def test_required_candidate_configuration_fails_closed(self):
    with self.assertRaises(ValueError):
      CyberLateralOptimizer(OfflineOptimizerConfig(LateralExperimentVariant.A2))
    with self.assertRaises(ValueError):
      CyberLateralOptimizer(OfflineOptimizerConfig(
        LateralExperimentVariant.A3,
        rate_limits=self.rate_limits,
      ))


if __name__ == '__main__':
  unittest.main()
