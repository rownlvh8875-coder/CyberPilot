"""Public synthetic tests for negative real-reference audit reports."""
from dataclasses import FrozenInstanceError, replace
import json
import unittest


FAMILIES = (
  'MODEL_GEOMETRY', 'PIXEL_DIAGNOSTIC', 'RECORDED_REPLAY',
  'INITIAL_STATE', 'GPS_POSE', 'D3Y_CALIBRATION',
)


def inventory():
  from openpilot.tools.cyber_autotune.curvature_yaw_source_audit import SourceAuditInventory, SourceAuditRecord
  return SourceAuditInventory(
    version=1,
    source_head='1' * 40,
    scope_sha256='a' * 64,
    review_sha256='b' * 64,
    records=tuple(
      SourceAuditRecord(
        family=family,
        artifact_sha256=('c' if index % 2 else 'd') * 64,
        producer_source_sha256='e' * 64,
        role='DEVELOPMENT',
        candidate_outputs_used=None,
        semantic_opened_before_freeze=None,
      )
      for index, family in enumerate(FAMILIES)
    ),
  )


class TestCurvatureYawSourceAudit(unittest.TestCase):
  def assess(self, value=None, expected=None):
    from openpilot.tools.cyber_autotune.curvature_yaw_source_audit import assess_source_inventory, source_inventory_sha256
    value = inventory() if value is None else value
    return assess_source_inventory(
      value, expected_inventory_sha256=source_inventory_sha256(value) if expected is None else expected,
    )

  def test_known_sources_do_not_become_metric_truth(self):
    result = self.assess()
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('REAL_REFERENCE_UNAVAILABLE_IN_AUDITED_SCOPE', result.blockers)
    reasons = {finding.family: finding.blockers for finding in result.findings}
    for family, reason in (
      ('MODEL_GEOMETRY', 'MODEL_OUTPUT_NOT_INDEPENDENT_TRUTH'),
      ('PIXEL_DIAGNOSTIC', 'PIXEL_GEOMETRY_NOT_METRIC_ROAD_REFERENCE'),
      ('RECORDED_REPLAY', 'REPLAY_IDENTITY_DOES_NOT_SUPPLY_ROAD_TRUTH'),
      ('INITIAL_STATE', 'INITIAL_STATE_DOES_NOT_SUPPLY_ROAD_TRUTH'),
      ('GPS_POSE', 'POSE_DOES_NOT_SUPPLY_LANE_GEOMETRY'),
      ('D3Y_CALIBRATION', 'D3Y_POSITION_TRUTH_NOT_INDEPENDENT'),
    ):
      self.assertIn(reason, reasons[family])
    self.assertFalse(result.reference_producer_allowed)
    self.assertFalse(result.comparison_execution_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)
    self.assertFalse(result.vehicle_activation_allowed)

  def test_incomplete_inventory_cannot_claim_scoped_unavailability(self):
    value = inventory()
    for records in ((), value.records[:-1], (value.records[0],) * 6):
      with self.subTest(records=len(records)):
        result = self.assess(replace(value, records=records))
        self.assertIn('AUDIT_SCOPE_INCOMPLETE_OR_DUPLICATE', result.blockers)
        self.assertNotIn('REAL_REFERENCE_UNAVAILABLE_IN_AUDITED_SCOPE', result.blockers)

  def test_bound_metadata_changes_invalidate_report(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_source_audit import source_inventory_sha256
    value = inventory()
    frozen = source_inventory_sha256(value)
    for changed in (
      replace(value, source_head='2' * 40),
      replace(value, scope_sha256='f' * 64),
      replace(value, review_sha256='f' * 64),
      replace(value, records=tuple(reversed(value.records))),
      replace(value, records=(replace(value.records[0], artifact_sha256='f' * 64), *value.records[1:])),
      replace(value, records=(replace(value.records[0], producer_source_sha256='f' * 64), *value.records[1:])),
    ):
      self.assertIn('AUDIT_INVENTORY_BINDING_MISMATCH', self.assess(changed, frozen).blockers)

  def test_unknown_is_not_false_for_leakage_and_open_order(self):
    result = self.assess()
    for finding in result.findings:
      self.assertIn('CANDIDATE_LEAKAGE_UNVERIFIED', finding.blockers)
      self.assertIn('SEMANTIC_OPEN_ORDER_UNVERIFIED', finding.blockers)

  def test_false_claims_cannot_upgrade_known_sources(self):
    value = inventory()
    records = tuple(replace(record, candidate_outputs_used=False, semantic_opened_before_freeze=False) for record in value.records)
    result = self.assess(replace(value, records=records))
    self.assertIn('REAL_REFERENCE_UNAVAILABLE_IN_AUDITED_SCOPE', result.blockers)
    self.assertTrue(all(finding.blockers for finding in result.findings))
    self.assertFalse(result.reference_producer_allowed)

  def test_leakage_and_prior_semantic_open_are_explicit_blockers(self):
    value = inventory()
    records = tuple(replace(record, candidate_outputs_used=True, semantic_opened_before_freeze=True) for record in value.records)
    result = self.assess(replace(value, records=records))
    for finding in result.findings:
      self.assertIn('CANDIDATE_OUTPUT_LEAKAGE', finding.blockers)
      self.assertIn('SEMANTIC_CONTENT_PRECEDES_REFERENCE_FREEZE', finding.blockers)

  def test_independent_role_label_is_not_independence_review(self):
    value = inventory()
    record = replace(value.records[0], role='INDEPENDENT_REFERENCE')
    result = self.assess(replace(value, records=(record, *value.records[1:])))
    self.assertIn('INDEPENDENT_ROLE_NOT_SUBSTANTIATED', result.findings[0].blockers)
    self.assertFalse(result.reference_producer_allowed)

  def test_new_external_geometry_cannot_be_admitted_by_this_negative_audit(self):
    value = inventory()
    external = replace(value.records[0], family='EXTERNAL_GEOMETRY', role='INDEPENDENT_REFERENCE',
                       candidate_outputs_used=False, semantic_opened_before_freeze=False)
    result = self.assess(replace(value, records=(*value.records, external)))
    self.assertIn('EXTERNAL_GEOMETRY_REQUIRES_SEPARATE_PRODUCER_REVIEW', result.blockers)
    self.assertNotIn('REAL_REFERENCE_UNAVAILABLE_IN_AUDITED_SCOPE', result.blockers)
    self.assertFalse(result.reference_producer_allowed)

  def test_malformed_metadata_fails_closed(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_source_audit import assess_source_inventory
    value = inventory()
    for changed in (None, {}, replace(value, version=True), replace(value, version=2),
                    replace(value, source_head='x' * 40), replace(value, records=list(value.records)),
                    replace(value, records=(replace(value.records[0], artifact_sha256='bad'), *value.records[1:])),
                    replace(value, records=(replace(value.records[0], candidate_outputs_used=0), *value.records[1:])),
                    replace(value, records=(replace(value.records[0], semantic_opened_before_freeze=1), *value.records[1:])),
                    replace(value, records=(replace(value.records[0], role='HOLDOUT'), *value.records[1:])),
                    replace(value, records=(replace(value.records[0], family='/private/path'), *value.records[1:]))):
      with self.subTest(value=type(changed).__name__):
        result = assess_source_inventory(changed, expected_inventory_sha256='a' * 64)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn('INVALID_SOURCE_AUDIT_INVENTORY', result.blockers)
        self.assertFalse(result.reference_producer_allowed)

  def test_arm_identity_variation_does_not_define_real_arm_semantics(self):
    result = self.assess()
    self.assertIn('UPSTREAM_BASELINE_PROFILE_AND_SOURCE_NOT_FROZEN', result.arm_blockers)
    self.assertIn('CYBER_CURRENT_NATIVE_CORE_EQUALS_BASELINE', result.arm_blockers)
    self.assertIn('CYBER_CANDIDATE_FEEDBACK_BOUND_IMPLEMENTATION_NOT_FROZEN', result.arm_blockers)
    self.assertIn('A3_REJECTION_REMAINS_IN_FORCE', result.arm_blockers)

  def test_report_is_immutable_deterministic_and_not_reference_document(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_source_audit import encode_source_audit_report
    result = self.assess()
    payload = encode_source_audit_report(result)
    self.assertEqual(payload, encode_source_audit_report(self.assess()))
    document = json.loads(payload)
    self.assertEqual(document['purpose'], 'CURVATURE_YAW_SOURCE_AUDIT_ONLY')
    self.assertNotIn('desired_path_offset_m', document)
    self.assertNotIn('lane_center_path_offset_m', document)
    self.assertNotIn('independent_primary_position_truth', document)
    with self.assertRaises(FrozenInstanceError):
      result.reference_producer_allowed = True
    with self.assertRaises(ValueError):
      replace(result, vehicle_activation_allowed=True)


  def test_encoder_rejects_forged_or_private_report_content(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_source_audit import encode_source_audit_report
    result = self.assess()
    for changed in (replace(result, blockers=('/private/raw/log',)),
                    replace(result, arm_blockers=()),
                    replace(result, inventory_sha256='f' * 64),
                    replace(result, findings=(replace(result.findings[0], blockers=()), *result.findings[1:])),
                    replace(result, source_head='invalid')):
      with self.subTest(report=changed.inventory_sha256):
        with self.assertRaisesRegex(ValueError, 'INVALID_SOURCE_AUDIT_REPORT'):
          encode_source_audit_report(changed)

  def test_audit_report_is_rejected_by_strict_reference_admission(self):
    from pathlib import Path
    import hashlib
    import tempfile
    from openpilot.tools.cyber_autotune.curvature_yaw_reference_input import ReferenceEvidenceGrant, retain_reference_evidence
    from openpilot.tools.cyber_autotune.curvature_yaw_source_audit import encode_source_audit_report
    payload = encode_source_audit_report(self.assess())
    with tempfile.TemporaryDirectory() as directory:
      Path(directory, 'audit.json').write_bytes(payload)
      grant = ReferenceEvidenceGrant(directory, 'audit.json', len(payload), hashlib.sha256(payload).hexdigest(),
                                     'a' * 64, 'b' * 64, 'c' * 64)
      with self.assertRaisesRegex(ValueError, 'INVALID_REFERENCE_FIELDS'):
        with retain_reference_evidence(grant, sample_count=1, coverage_policy=None):
          self.fail('negative report admitted as independent reference')


if __name__ == '__main__':
  unittest.main()
