import unittest
from dataclasses import replace


def h(char):
  return char * 64


def thresholds():
  from openpilot.tools.cyber_autotune.plant_calibration_protocol import HorizonAcceptance
  return (
    HorizonAcceptance(1.0, 200, 4000, 0.005, 0.97, 0.005, 0.05, 0.025),
    HorizonAcceptance(5.0, 40, 4000, 0.006, 0.96, 0.025, 0.75, 0.35),
    HorizonAcceptance(10.0, 20, 4000, 0.006, 0.955, 0.04, 2.0, 0.9),
  )


def policy():
  from openpilot.tools.cyber_autotune.plant_calibration_protocol import ProspectiveCalibrationProtocol
  return ProspectiveCalibrationProtocol(
    schema_version=1,
    protocol_id='CYBER_D3Y_PROSPECTIVE_V1',
    frozen_at_utc='2026-10-03T12:00:00+00:00',
    target_vehicle='HYUNDAI_SANTA_FE_2022',
    model_family='YR_AR1_SPEED_FIXED',
    expected_model_sha256=h('a'),
    expected_adapter_sha256=h('b'),
    expected_plant_builder_sha256=h('c'),
    expected_validation_runner_sha256=h('d'),
    minimum_validation_routes=4,
    minimum_validation_sequences=16,
    minimum_eligible_pose_samples=5000,
    maximum_stability_radius=0.98,
    require_independent_primary_position_truth=True,
    require_external_reproduction_for_review=True,
    horizons=thresholds(),
  )


def horizon_evidence():
  from openpilot.tools.cyber_autotune.plant_calibration_protocol import ProspectiveHorizonEvidence
  return (
    ProspectiveHorizonEvidence(1.0, 220, 5000, 0.004, 0.98, 0.004, 0.04, 0.02),
    ProspectiveHorizonEvidence(5.0, 45, 4800, 0.005, 0.97, 0.02, 0.6, 0.3),
    ProspectiveHorizonEvidence(10.0, 24, 4500, 0.005, 0.96, 0.035, 1.8, 0.8),
  )


def evidence(protocol_sha=None):
  from openpilot.tools.cyber_autotune.plant_calibration_protocol import (
    ProspectiveCalibrationEvidence,
    protocol_sha256,
  )
  policy_sha = protocol_sha or protocol_sha256(policy())
  return ProspectiveCalibrationEvidence(
    protocol_sha256=policy_sha,
    data_manifest_sha256=h('e'),
    source_commit='1' * 40,
    target_vehicle='HYUNDAI_SANTA_FE_2022',
    model_family='YR_AR1_SPEED_FIXED',
    model_sha256=h('a'),
    adapter_sha256=h('b'),
    plant_builder_sha256=h('c'),
    validation_runner_sha256=h('d'),
    collection_started_at_utc='2026-10-04T00:00:00+00:00',
    collection_ended_at_utc='2026-10-04T03:00:00+00:00',
    manifest_frozen_at_utc='2026-10-04T03:30:00+00:00',
    evaluation_started_at_utc='2026-10-04T04:00:00+00:00',
    semantic_content_opened_before_manifest=False,
    validation_route_count=5,
    validation_sequence_count=20,
    eligible_pose_samples=6000,
    stability_radius=0.95,
    independent_primary_position_truth=True,
    external_reproduction_established=False,
    validation_refit_performed=False,
    candidate_outputs_used_for_model_selection=False,
    real_vehicle_write=False,
    performance_acceptance=False,
    recommendation_authorized=False,
    horizons=horizon_evidence(),
  )


class TestProspectivePlantCalibrationProtocol(unittest.TestCase):
  def test_historical_evidence_is_rejected_as_pre_freeze(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import assess_prospective_calibration

    historical = replace(
      evidence(),
      collection_started_at_utc='2026-09-20T00:00:00+00:00',
      collection_ended_at_utc='2026-09-20T03:00:00+00:00',
      manifest_frozen_at_utc='2026-09-20T03:30:00+00:00',
      evaluation_started_at_utc='2026-09-20T04:00:00+00:00',
    )
    result = assess_prospective_calibration(policy(), historical)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('DATA_PREDATES_PROTOCOL_FREEZE', result.blockers)
    self.assertFalse(result.prospective_revalidation_pass)

  def test_future_internal_revalidation_passes_without_qualification(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import assess_prospective_calibration

    result = assess_prospective_calibration(policy(), evidence())
    self.assertEqual(result.status, 'PROSPECTIVE_INTERNAL_REVALIDATION_PASS')
    self.assertTrue(result.protocol_verified)
    self.assertTrue(result.prospective_revalidation_pass)
    self.assertEqual(result.failed_horizons, ())
    self.assertIn('EXTERNAL_REPRODUCTION_NOT_ESTABLISHED', result.blockers)
    self.assertIn('QUALIFICATION_AUTHORITY_NOT_GRANTED', result.blockers)
    self.assertFalse(result.plant_calibration_qualified)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_external_reproduction_only_reaches_review_state(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import assess_prospective_calibration

    result = assess_prospective_calibration(
      policy(), replace(evidence(), external_reproduction_established=True),
    )
    self.assertEqual(result.status, 'CALIBRATION_EVIDENCE_READY_FOR_REVIEW')
    self.assertEqual(result.blockers, ('QUALIFICATION_AUTHORITY_NOT_GRANTED',))
    self.assertTrue(result.prospective_revalidation_pass)
    self.assertFalse(result.plant_calibration_qualified)

  def test_manifest_timing_and_truth_requirements_fail_closed(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import assess_prospective_calibration

    cases = (
      (replace(evidence(), semantic_content_opened_before_manifest=True),
       'CONTENT_OPENED_BEFORE_MANIFEST_FREEZE'),
      (replace(evidence(), manifest_frozen_at_utc='2026-10-04T02:00:00+00:00'),
       'INVALID_EVIDENCE_TIMELINE'),
      (replace(evidence(), evaluation_started_at_utc='2026-10-04T03:00:00+00:00'),
       'INVALID_EVIDENCE_TIMELINE'),
      (replace(evidence(), independent_primary_position_truth=False),
       'PRIMARY_POSITION_TRUTH_NOT_INDEPENDENT'),
    )
    for mutation, blocker in cases:
      with self.subTest(blocker=blocker):
        result = assess_prospective_calibration(policy(), mutation)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn(blocker, result.blockers)

  def test_threshold_failure_names_failed_horizon(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import assess_prospective_calibration

    bad = replace(horizon_evidence()[2], path_endpoint_rmse_m=2.01)
    result = assess_prospective_calibration(
      policy(), replace(evidence(), horizons=horizon_evidence()[:2] + (bad,)),
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('HORIZON_THRESHOLD_FAILED', result.blockers)
    self.assertEqual(result.failed_horizons, (10.0,))

  def test_policy_binding_and_platform_identity_fail_closed(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import assess_prospective_calibration

    cases = (
      replace(evidence(), protocol_sha256=h('f')),
      replace(evidence(), target_vehicle='OTHER'),
      replace(evidence(), model_sha256=h('9')),
      replace(evidence(), adapter_sha256=h('9')),
      replace(evidence(), plant_builder_sha256=h('9')),
      replace(evidence(), validation_runner_sha256=h('9')),
    )
    for mutation in cases:
      with self.subTest(mutation=mutation):
        result = assess_prospective_calibration(policy(), mutation)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('EVIDENCE_BINDING_MISMATCH', result.blockers)

  def test_counts_stability_leakage_and_authority_fail_closed(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import assess_prospective_calibration

    cases = (
      (replace(evidence(), validation_route_count=3), 'INSUFFICIENT_VALIDATION_COVERAGE'),
      (replace(evidence(), validation_sequence_count=15), 'INSUFFICIENT_VALIDATION_COVERAGE'),
      (replace(evidence(), eligible_pose_samples=4999), 'INSUFFICIENT_VALIDATION_COVERAGE'),
      (replace(evidence(), stability_radius=0.981), 'UNSTABLE_MODEL'),
      (replace(evidence(), validation_refit_performed=True), 'VALIDATION_REFIT_DETECTED'),
      (replace(evidence(), candidate_outputs_used_for_model_selection=True), 'VALIDATION_SELECTION_LEAKAGE'),
      (replace(evidence(), real_vehicle_write=True), 'FORBIDDEN_AUTHORITY'),
      (replace(evidence(), performance_acceptance=True), 'FORBIDDEN_AUTHORITY'),
      (replace(evidence(), recommendation_authorized=True), 'FORBIDDEN_AUTHORITY'),
    )
    for mutation, blocker in cases:
      with self.subTest(blocker=blocker):
        result = assess_prospective_calibration(policy(), mutation)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn(blocker, result.blockers)

  def test_protocol_digest_is_deterministic_and_order_sensitive(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import protocol_sha256

    self.assertEqual(protocol_sha256(policy()), protocol_sha256(policy()))
    reordered = replace(policy(), horizons=tuple(reversed(thresholds())))
    self.assertNotEqual(protocol_sha256(policy()), protocol_sha256(reordered))

  def test_invalid_policy_and_evidence_types_fail_closed(self):
    from openpilot.tools.cyber_autotune.plant_calibration_protocol import assess_prospective_calibration

    for invalid_policy in (None, {}):
      with self.subTest(policy=invalid_policy):
        result = assess_prospective_calibration(invalid_policy, evidence())
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.blockers, ('INVALID_POLICY',))
        self.assertFalse(result.protocol_verified)

    for invalid_evidence in (None, {}):
      with self.subTest(evidence=invalid_evidence):
        result = assess_prospective_calibration(policy(), invalid_evidence)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.blockers, ('INVALID_EVIDENCE',))
        self.assertTrue(result.protocol_verified)

    for result in (
      assess_prospective_calibration(None, evidence()),
      assess_prospective_calibration(policy(), None),
    ):
      self.assertFalse(result.plant_calibration_qualified)
      self.assertFalse(result.runtime_accepted)
      self.assertFalse(result.promotable)


if __name__ == '__main__':
  unittest.main()
