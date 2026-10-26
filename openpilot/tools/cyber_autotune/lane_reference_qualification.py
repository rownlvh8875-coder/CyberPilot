"""Offline feasibility receipts only; no detector execution or truth promotion.

This v1 intentionally represents an incomplete execution freeze and unjustified
promotion thresholds. Source/config hashes are not authenticated provenance.
Missing measurements are null, not fabricated perfect scores. A future evaluated
protocol requires a new version; this one cannot authorize private frame reads.
"""

import copy
from pathlib import Path

from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

POLICY_PATH = Path(__file__).with_name('public_lane_reference_policy.json')
PROTOCOL_SHA256 = '113d5bc94b11fb11aee24986cf1ef2b78d4c0f9a26742959382d2df3274cdb3c'
ROSTER = ('CLRerNet', 'CLRNet', 'UFLDv2')
STATES = (
  'DETECTOR_UNVERIFIED',
  'PUBLIC_GT_PASS',
  'PUBLIC_GT_REJECTED',
  'PRIVATE_DOMAIN_VALIDATION_PENDING',
  'PRIVATE_DOMAIN_VALIDATED',
  'REFERENCE_ESTIMATOR_READY',
  'REFERENCE_UNAVAILABLE',
)
BLOCKERS = (
  'DETECTOR_PROMOTION_THRESHOLDS_UNJUSTIFIED',
  'PUBLIC_BENCHMARK_NOT_REPRODUCED',
  'DETECTOR_EXECUTION_ENVIRONMENT_UNFROZEN',
  'COMMA10K_GEOMETRY_ADAPTER_UNFROZEN',
  'PRIVATE_HUMAN_HOLDOUT_UNAVAILABLE',
  'PRIVATE_DOMAIN_GAP_NOT_MEASURED',
  'CONFIDENCE_CALIBRATION_UNVALIDATED',
  'INDEPENDENT_CALIBRATION_UNAVAILABLE',
  'METRIC_REFERENCE_ERROR_BUDGET_UNDEFINED',
  'INDEPENDENT_DESIRED_PATH_REFERENCE_UNAVAILABLE',
  'INDEPENDENT_ROAD_FRAME_REGISTRATION_UNAVAILABLE',
  'SEALED_REFERENCE_PRODUCER_UNAVAILABLE',
)
DELIVERABLES = (
  'detector_comparison',
  'selected_detector_receipt',
  'public_gt_accuracy',
  'comma10k_localization',
  'metric_dataset_audit',
  'calibration_provenance',
  'uncertainty_error_budget',
  'private_coverage',
  'private_human_validation',
  'human_review_frame_manifest',
  'sealed_reference_json',
  'blocked_report',
)


def freeze_protocol(policy: dict) -> dict:
  """Bind this audit protocol exactly; caller mutations do not update the freeze."""
  # This phase has no generic threshold override or caller-asserted PASS path.
  import json

  declared = json.loads(POLICY_PATH.read_text())
  if type(policy) is not dict or canonical(policy) != canonical(declared) or digest(canonical(declared)) != PROTOCOL_SHA256:
    raise ValueError('PROTOCOL_V1_DECLARATION_MISMATCH')
  if (
    tuple(d['name'] for d in policy['detectors']) != ROSTER
    or any(policy['qualification_thresholds'].values())
    or policy['threshold_status'] != 'BLOCKED_UNJUSTIFIED'
  ):
    raise ValueError('INCOMPLETE_PROTOCOL_REQUIRED')
  for detector in policy['detectors']:
    if (
      not is_sha256(detector['config_bundle_sha256'])
      or digest(canonical(detector['config_bundle'])) != detector['config_bundle_sha256']
      or (detector['weight_sha256'] is not None and not is_sha256(detector['weight_sha256']))
    ):
      raise ValueError('DETECTOR_IDENTITY_INVALID')
  frozen = copy.deepcopy(policy)
  frozen['protocol_sha256'] = digest(canonical(policy))
  return frozen


def blocked_report(frozen: dict, audit_hashes: dict) -> dict:
  """Build a blocker report; it is incompatible with strict reference evidence."""
  if type(frozen) is not dict or 'protocol_sha256' not in frozen:
    raise ValueError('FROZEN_PROTOCOL_REQUIRED')
  policy = {k: v for k, v in frozen.items() if k != 'protocol_sha256'}
  if freeze_protocol(policy) != frozen:
    raise ValueError('FROZEN_PROTOCOL_DRIFT')
  keys = {'official_source_audit_sha256', 'calibration_audit_sha256'}
  if type(audit_hashes) is not dict or set(audit_hashes) != keys or not all(is_sha256(v) for v in audit_hashes.values()):
    raise ValueError('EXACT_AUDIT_BINDINGS_REQUIRED')
  deliverables = {}
  for name in DELIVERABLES:
    implemented = name in ('detector_comparison', 'metric_dataset_audit', 'calibration_provenance', 'blocked_report')
    deliverables[name] = {'status': 'AUDIT_ONLY' if implemented else 'BLOCKED_NOT_RUN', 'measurements': None, 'qualified': False}
  report = {
    'schema_version': 1,
    'scope': 'FEASIBILITY_AUDIT_NOT_EVIDENCE_ADMISSION',
    'producer_source_sha256': digest(Path(__file__).read_bytes()),
    'status': 'REFERENCE_UNAVAILABLE',
    'detector_state': 'DETECTOR_UNVERIFIED',
    'protocol_sha256': frozen['protocol_sha256'],
    'source_audits': copy.deepcopy(audit_hashes),
    'detector_identity_sha256': [digest(canonical(d)) for d in frozen['detectors']],
    'selected_detector': None,
    'blockers': list(BLOCKERS),
    'deliverables': deliverables,
    'qualification_status': 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
    'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    'private_frames_opened': False,
    'candidate_outputs_used_for_reference': False,
    'openpilot_path_lane_used_for_reference': False,
    'sealed_reference_emitted': False,
    'runtime_accepted': False,
    'promotable': False,
    'vehicle_activation_allowed': False,
  }
  if any(d['weight_sha256'] is None for d in frozen['detectors']):
    report['blockers'].append('DECLARED_DETECTOR_WEIGHT_UNAVAILABLE')
  report['receipt_sha256'] = digest(canonical(report))
  return report
