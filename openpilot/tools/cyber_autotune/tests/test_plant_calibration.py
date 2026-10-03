import math
import unittest
from dataclasses import replace


def h(char):
  return char * 64


def horizons():
  from openpilot.tools.cyber_autotune.plant_calibration import CalibrationHorizon
  return tuple(
    CalibrationHorizon(
      horizon_s=horizon,
      sample_count=1000,
      window_count=20,
      yaw_rate_rmse_rad_s=0.005,
      yaw_rate_correlation=0.96,
      heading_endpoint_rmse_rad=0.02,
      path_endpoint_rmse_m=0.9,
      path_xy_rmse_m=0.4,
    )
    for horizon in (1.0, 5.0, 10.0)
  )


def evidence():
  from openpilot.tools.cyber_autotune.plant_calibration import PlantCalibrationEvidence
  return PlantCalibrationEvidence(
    target_vehicle='HYUNDAI_SANTA_FE_2022',
    model_family='YR_AR1_SPEED_FIXED',
    feature_names=('r1', 'u0', 'u0_inv_v', 'u0_v', 'roll'),
    delay_frames=3,
    model_source_commit='1' * 40,
    model_canonical_sha256=h('a'),
    assurance_contract_sha256=h('b'),
    precommit_sha256=h('c'),
    development_sha256=h('d'),
    frozen_sha256=h('e'),
    validation_sha256=h('f'),
    smoke_sha256=h('1'),
    adapter_sha256=h('2'),
    plant_builder_sha256=h('3'),
    validation_runner_sha256=h('4'),
    development_route_count=8,
    validation_route_count=4,
    validation_sequence_count=17,
    eligible_pose_samples=6359,
    stability_radius=0.957,
    development_validation_disjoint=True,
    model_structure_fixed_before_validation=True,
    validation_refit_performed=False,
    candidate_outputs_used_for_model_selection=False,
    deterministic_trace=True,
    deterministic_pose=True,
    acceptance_threshold_precommitted=False,
    descriptive_validation_only=True,
    primary_position_truth_independent=False,
    external_reproduction_established=False,
    current_platform_revalidated=False,
    real_vehicle_write=False,
    performance_acceptance=False,
    recommendation_authorized=False,
    horizons=horizons(),
  )


class TestPlantCalibrationEvidence(unittest.TestCase):
  def test_descriptive_evidence_is_verified_without_qualification(self):
    from openpilot.tools.cyber_autotune.plant_calibration import assess_plant_calibration

    result = assess_plant_calibration(evidence())

    self.assertEqual(result.status, 'DESCRIPTIVE_CALIBRATION_EVIDENCE')
    self.assertTrue(result.evidence_chain_verified)
    self.assertTrue(result.descriptive_validation_verified)
    self.assertEqual(result.development_route_count, 8)
    self.assertEqual(result.validation_route_count, 4)
    self.assertEqual(result.validation_sequence_count, 17)
    self.assertEqual(result.eligible_pose_samples, 6359)
    self.assertIn('ACCEPTANCE_THRESHOLD_NOT_PRECOMMITTED', result.blockers)
    self.assertIn('PRIMARY_POSITION_TRUTH_NOT_INDEPENDENT', result.blockers)
    self.assertIn('EXTERNAL_REPRODUCTION_NOT_ESTABLISHED', result.blockers)
    self.assertIn('CURRENT_PLATFORM_REVALIDATION_REQUIRED', result.blockers)
    self.assertIn('QUALIFICATION_AUTHORITY_NOT_GRANTED', result.blockers)
    self.assertFalse(result.plant_calibration_qualified)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_evidence_digest_is_deterministic_and_horizon_order_is_bound(self):
    from openpilot.tools.cyber_autotune.plant_calibration import assess_plant_calibration

    first = assess_plant_calibration(evidence())
    second = assess_plant_calibration(evidence())
    self.assertEqual(first.evidence_sha256, second.evidence_sha256)

    reordered = replace(evidence(), horizons=tuple(reversed(horizons())))
    result = assess_plant_calibration(reordered)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_HORIZON_EVIDENCE', result.blockers)

  def test_invalid_hashes_identity_and_authority_fail_closed(self):
    from openpilot.tools.cyber_autotune.plant_calibration import assess_plant_calibration

    mutations = (
      replace(evidence(), frozen_sha256='bad'),
      replace(evidence(), model_source_commit='x' * 40),
      replace(evidence(), target_vehicle='OTHER'),
      replace(evidence(), real_vehicle_write=True),
      replace(evidence(), performance_acceptance=True),
      replace(evidence(), recommendation_authorized=True),
    )
    for mutation in mutations:
      with self.subTest(mutation=mutation):
        result = assess_plant_calibration(mutation)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertFalse(result.plant_calibration_qualified)

  def test_development_validation_separation_and_determinism_are_mandatory(self):
    from openpilot.tools.cyber_autotune.plant_calibration import assess_plant_calibration

    cases = (
      (replace(evidence(), development_validation_disjoint=False),
       'DEVELOPMENT_VALIDATION_NOT_DISJOINT'),
      (replace(evidence(), model_structure_fixed_before_validation=False),
       'MODEL_STRUCTURE_NOT_FIXED'),
      (replace(evidence(), validation_refit_performed=True),
       'VALIDATION_REFIT_DETECTED'),
      (replace(evidence(), candidate_outputs_used_for_model_selection=True),
       'VALIDATION_SELECTION_LEAKAGE'),
      (replace(evidence(), deterministic_trace=False),
       'NONDETERMINISTIC_SMOKE_EVIDENCE'),
      (replace(evidence(), deterministic_pose=False),
       'NONDETERMINISTIC_SMOKE_EVIDENCE'),
    )
    for mutation, blocker in cases:
      with self.subTest(blocker=blocker):
        result = assess_plant_calibration(mutation)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn(blocker, result.blockers)

  def test_unstable_model_and_invalid_horizon_metrics_are_blocked(self):
    from openpilot.tools.cyber_autotune.plant_calibration import assess_plant_calibration

    result = assess_plant_calibration(replace(evidence(), stability_radius=1.0))
    self.assertIn('UNSTABLE_MODEL', result.blockers)

    bad = replace(horizons()[0], yaw_rate_rmse_rad_s=math.nan)
    result = assess_plant_calibration(
      replace(evidence(), horizons=(bad,) + horizons()[1:]),
    )
    self.assertIn('INVALID_HORIZON_EVIDENCE', result.blockers)

  def test_complete_evidence_is_ready_for_review_but_never_self_qualifies(self):
    from openpilot.tools.cyber_autotune.plant_calibration import assess_plant_calibration

    complete = replace(
      evidence(),
      acceptance_threshold_precommitted=True,
      descriptive_validation_only=False,
      primary_position_truth_independent=True,
      external_reproduction_established=True,
      current_platform_revalidated=True,
    )
    result = assess_plant_calibration(complete)
    self.assertEqual(result.status, 'CALIBRATION_EVIDENCE_READY_FOR_REVIEW')
    self.assertEqual(result.blockers, ('QUALIFICATION_AUTHORITY_NOT_GRANTED',))
    self.assertTrue(result.evidence_chain_verified)
    self.assertTrue(result.descriptive_validation_verified)
    self.assertFalse(result.plant_calibration_qualified)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_counts_features_delay_and_horizon_shape_fail_closed(self):
    from openpilot.tools.cyber_autotune.plant_calibration import assess_plant_calibration

    mutations = (
      replace(evidence(), development_route_count=0),
      replace(evidence(), validation_route_count=0),
      replace(evidence(), validation_sequence_count=0),
      replace(evidence(), eligible_pose_samples=0),
      replace(evidence(), delay_frames=0),
      replace(evidence(), feature_names=('r1',)),
      replace(evidence(), horizons=horizons()[:2]),
    )
    for mutation in mutations:
      with self.subTest(mutation=mutation):
        result = assess_plant_calibration(mutation)
        self.assertEqual(result.status, 'BLOCKED')

  def test_invalid_types_return_blocked_without_exception(self):
    from openpilot.tools.cyber_autotune.plant_calibration import assess_plant_calibration

    for value in (None, {}, [], 'evidence'):
      with self.subTest(value=value):
        result = assess_plant_calibration(value)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.blockers, ('INVALID_EVIDENCE',))
        self.assertFalse(result.evidence_chain_verified)
        self.assertFalse(result.plant_calibration_qualified)
        self.assertFalse(result.runtime_accepted)
        self.assertFalse(result.promotable)


if __name__ == '__main__':
  unittest.main()
