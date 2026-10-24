import copy
import json
import unittest
from openpilot.tools.cyber_autotune import lane_reference_qualification as q
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestLaneReferenceQualification(unittest.TestCase):
  def policy(self):
    return json.loads(q.POLICY_PATH.read_text())

  def test_complete_execution_freeze_is_not_claimed(self):
    p = self.policy()
    frozen = q.freeze_protocol(p)
    self.assertEqual(frozen['selected_detector'], None)
    self.assertEqual(frozen['primary_reproduction_target'], 'CLRerNet')
    self.assertFalse(frozen['public_gt_semantics_opened'])
    self.assertFalse(frozen['private_frames_opened'])
    self.assertEqual([d['name'] for d in frozen['detectors']], ['CLRerNet', 'CLRNet', 'UFLDv2'])
    self.assertEqual(frozen['protocol_sha256'], digest(canonical(p)))
    self.assertTrue(all(d['inference_environment_sha256'] is None for d in frozen['detectors']))

  def test_unknown_fields_roster_and_threshold_changes_fail_closed(self):
    original = self.policy()
    variants = []
    p = copy.deepcopy(original)
    p['selected_detector'] = 'CLRerNet'
    variants.append(p)
    p = copy.deepcopy(original)
    p['detectors'].reverse()
    variants.append(p)
    p = copy.deepcopy(original)
    p['qualification_thresholds']['median_localization_px'] = 1
    variants.append(p)
    p = copy.deepcopy(original)
    p['candidate_outputs_used_for_reference'] = True
    variants.append(p)
    p = copy.deepcopy(original)
    p['detectors'][0]['weight_sha256'] = 'x' * 64
    variants.append(p)
    p = copy.deepcopy(original)
    p['private_frames_opened'] = True
    variants.append(p)
    for p in variants:
      with self.subTest(p=p):
        with self.assertRaises(ValueError):
          q.freeze_protocol(p)

  def test_all_missing_deliverables_have_null_measurements_and_blockers(self):
    frozen = q.freeze_protocol(self.policy())
    report = q.blocked_report(frozen, {'official_source_audit_sha256': 'a' * 64, 'calibration_audit_sha256': 'b' * 64})
    self.assertEqual(report['status'], 'REFERENCE_UNAVAILABLE')
    self.assertEqual(report['detector_state'], 'DETECTOR_UNVERIFIED')
    self.assertEqual(report['qualification_status'], 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE')
    self.assertEqual(len(report['deliverables']), 12)
    for key in ('public_gt_accuracy', 'comma10k_localization', 'private_coverage', 'private_human_validation', 'uncertainty_error_budget'):
      self.assertIsNone(report['deliverables'][key]['measurements'])
    for reason in (
      'DETECTOR_PROMOTION_THRESHOLDS_UNJUSTIFIED',
      'PUBLIC_BENCHMARK_NOT_REPRODUCED',
      'PRIVATE_HUMAN_HOLDOUT_UNAVAILABLE',
      'INDEPENDENT_CALIBRATION_UNAVAILABLE',
      'INDEPENDENT_DESIRED_PATH_REFERENCE_UNAVAILABLE',
      'INDEPENDENT_ROAD_FRAME_REGISTRATION_UNAVAILABLE',
    ):
      self.assertIn(reason, report['blockers'])
    self.assertFalse(report['sealed_reference_emitted'])
    self.assertFalse(report['vehicle_activation_allowed'])

  def test_report_repeatability_binding_and_no_caller_promotion(self):
    p = self.policy()
    f = q.freeze_protocol(p)
    hashes = {'official_source_audit_sha256': 'a' * 64, 'calibration_audit_sha256': 'b' * 64}
    first = q.blocked_report(f, hashes)
    self.assertEqual(first, q.blocked_report(f, hashes))
    hashes['calibration_audit_sha256'] = 'c' * 64
    self.assertNotEqual(first['receipt_sha256'], q.blocked_report(f, hashes)['receipt_sha256'])
    f['detectors'][0]['config_bundle_sha256'] = 'd' * 64
    with self.assertRaises(ValueError):
      q.blocked_report(f, hashes)

  def test_blocked_report_is_not_strict_reference_json(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_reference_input import _decode_payload, ReferenceEvidenceGrant
    from openpilot.tools.cyber_autotune.preflight import CoveragePolicy, REQUIRED_STRATA

    f = q.freeze_protocol(self.policy())
    report = q.blocked_report(f, {'official_source_audit_sha256': 'a' * 64, 'calibration_audit_sha256': 'b' * 64})
    raw = canonical(report)
    grant = ReferenceEvidenceGrant('/tmp', 'not-a-reference.json', len(raw), digest(raw), 'a' * 64, 'b' * 64, 'c' * 64)
    with self.assertRaises(ValueError):
      _decode_payload(raw, grant=grant, sample_count=1, coverage_policy=CoveragePolicy('d' * 64, tuple((name, 1) for name in sorted(REQUIRED_STRATA))))

  def test_invalid_audit_digest_and_extra_claims_rejected(self):
    f = q.freeze_protocol(self.policy())
    for hashes in (
      {},
      {'official_source_audit_sha256': 'a' * 64, 'calibration_audit_sha256': 'not-a-sha'},
      {'official_source_audit_sha256': 'a' * 64, 'calibration_audit_sha256': 'b' * 64, 'PUBLIC_GT_PASS': True},
    ):
      with self.assertRaises(ValueError):
        q.blocked_report(f, hashes)

  def test_boolean_version_is_not_integer_version(self):
    policy = self.policy()
    policy['schema_version'] = True
    with self.assertRaises(ValueError):
      q.freeze_protocol(policy)

  def test_published_blocker_receipt_reconstructs_from_exact_audit_files(self):
    root = q.POLICY_PATH.resolve().parents[3]
    records = root / 'docs/cyberpilot/changes'
    report = json.loads((records / 'public-lane-reference-blocked-report.json').read_text())
    bindings = {
      key: digest((records / file).read_bytes())
      for key, file in (
        ('official_source_audit_sha256', 'public-lane-reference-source-audit.json'),
        ('calibration_audit_sha256', 'public-lane-reference-calibration-audit.json'),
      )
    }
    self.assertEqual(report, q.blocked_report(q.freeze_protocol(self.policy()), bindings))
    for file in ('public-lane-reference-source-audit.json', 'public-lane-reference-calibration-audit.json'):
      record = json.loads((records / file).read_text())
      self.assertEqual(record['receipt_sha256'], digest(canonical({k: v for k, v in record.items() if k != 'receipt_sha256'})))
    self.assertTrue(all(item['qualified'] is False for item in report['deliverables'].values()))

  def test_official_audit_cannot_be_confused_with_measured_accuracy(self):
    root = q.POLICY_PATH.resolve().parents[3]
    audit = json.loads((root / 'docs/cyberpilot/changes/public-lane-reference-source-audit.json').read_text())
    self.assertEqual(audit['protocol_sha256'], q.freeze_protocol(self.policy())['protocol_sha256'])
    self.assertEqual(audit['comma10k']['road_images'], 11888)
    self.assertFalse(audit['comma10k']['ego_lane_association_gt'])
    self.assertFalse(audit['evaluation']['any_detector_inference'])
    for key in ('public_gt_accuracy', 'comma10k_localization', 'private_domain_gap'):
      self.assertIsNone(audit['evaluation'][key])
    for detector in audit['detector_notes'].values():
      self.assertIsNone(detector['measured_f1'])
    self.assertFalse(audit['evaluation']['private_frames_opened'])
