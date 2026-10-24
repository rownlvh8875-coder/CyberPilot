"""Current pending evidence DAG; no state can be promoted by declared software readiness."""

import copy
from pathlib import Path
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune import independent_lane_geometry as g
from openpilot.tools.cyber_autotune import private_lane_diagnostic_preparation as d
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune import lane_tail_blocker_plan as old
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.camera_calibration_evidence import seal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ROOT = Path(__file__).resolve().parents[3]
PRIOR_SHA = 'c588d848982d1f423812d8e9d7efeaa48c847ef2fc2e129e9fffe9397ec659e4'
LABEL_SHA = 'ceb9606170b4d6110ec98f35a5a2721345536b898e51b9c1b0daa0547a4696c7'
STATES = {
  'CALIBRATION': 'PENDING',
  'EGO_ASSOCIATION': 'VALIDATION_PENDING',
  'ROAD_REGISTRATION': 'BLOCKED',
  'PRIVATE_DIAGNOSTIC': 'PROPOSED_NOT_RUN',
  'REFERENCE': 'UNAVAILABLE',
}
POLICY = {
  'schema': 'REFERENCE_INFRASTRUCTURE_POLICY_V1',
  'states': STATES,
  'independent_measurement': 'PENDING_HUMAN_PHYSICAL_ARTIFACT_NO_DEFAULT_VALUES',
  'validation': 'STRUCTURAL_ADMISSION_IS_NOT_CALIBRATION_OR_EGO_VALIDATION',
  'private_execution': 'EXPLICITLY_PROHIBITED_THIS_INCREMENT',
  'sealed_reference': 'NOT_GENERATED',
  'allowed_states_design_only': {
    'CALIBRATION': ['PENDING', 'ADMITTED', 'REJECTED'],
    'EGO_ASSOCIATION': ['DEFINED', 'VALIDATION_PENDING', 'VALIDATED'],
    'ROAD_REGISTRATION': ['BLOCKED', 'STRUCTURALLY_READY', 'VALIDATED'],
    'PRIVATE_DIAGNOSTIC': ['PROPOSED', 'MANIFEST_READY', 'AUTHORIZED', 'RUN', 'COMPLETE'],
    'REFERENCE': ['UNAVAILABLE', 'INPUTS_READY', 'SEALED'],
  },
  'state_transitions': 'FUTURE_DECLARED_INDEPENDENT_VALIDATORS_AND_EXECUTION_AUTHORITY_REQUIRED; NO_AUTOMATIC_TRANSITIONS',
}


def identity():
  return digest(
    canonical({'source': digest(Path(__file__).read_bytes()), 'calibration': c.identity(), 'geometry': g.identity(), 'private': d.identity(), 'policy': POLICY})
  )


def calibration_protocol():
  return seal(
    {
      'schema': 'PHYSICAL_CALIBRATION_SUBMISSION_PROTOCOL_V1',
      'status': 'CALIBRATION_MEASUREMENT_PENDING',
      'target_device_family': 'comma4_mici_narrow_road',
      'actual_camera_identity': None,
      'static_sources': {'camera': c.CAMERA_SOURCE, 'camera_sha256': c.CAMERA_SHA, 'hardware_mapping': c.HARDWARE_SOURCE, 'hardware_sha256': c.HARDWARE_SHA},
      'measurement_fields': {key: {'unit': unit, 'value': None, 'uncertainty': None, 'method': None, 'provenance': None} for key, unit in c.UNITS.items()},
      'measurement_schema': c.SCHEMA,
      'schema_sha256': c.SCHEMA_SHA,
      'admission_tool_sha256': c.identity(),
      'operator_id': None,
      'measurement_timestamp': None,
      'ground_survey': None,
      'distortion_validation': None,
      'independence_limitation': 'DECLARED_ROLES_AND_HASHES_DO_NOT_VERIFY_REAL_INSTRUMENT_ACCURACY_OR_EXTERIOR_NONCONTAMINATION',
      'template_submittable': False,
      'reference_promotable': False,
    }
  )


def label_completeness_audit():
  value = s.read_json(ROOT / 'docs/cyberpilot/changes/comma10k-tail-annotation-provenance.json')
  unseal(value)
  if value['receipt_sha256'] != LABEL_SHA:
    raise ValueError('IMMUTABLE_LABEL_PROVENANCE_REQUIRED')
  if (
    value['full_pairs'] != 11888
    or value['imgs2_masks'] != 2000
    or value['repeated_shared_mask_count'] != 1400
    or value['imgs2_masks'] - value['repeated_shared_mask_count'] + 1 != value['imgs2_unique_mask_blobs']
    or value['original119_shared_mask_pred_to_gt_samples'] != 0
    or value['GT_semantic_quality_verified'] is not False
  ):
    raise ValueError('ORIGINAL_LABEL_PROVENANCE_COUNTS_CHANGED')
  return seal(
    {
      'schema': 'LABEL_COMPLETENESS_DEPENDENCY_AUDIT_V1',
      'status': 'COMMA10K_LABEL_COMPLETENESS_UNVERIFIED',
      'source_receipt_sha256': LABEL_SHA,
      'dataset_commit': value['dataset_commit'],
      'repeated_shared_mask_count': value['repeated_shared_mask_count'],
      'mask_sha256': value['repeated_shared_mask_sha256'],
      'known_mask_category': 'ALL_UNDRIVABLE',
      'lane_absence_verified': False,
      'filter_applied': False,
      'legacy_metric_invalidated': False,
      'metadata_consistency_checked': True,
      'new_mask_or_image_opened': False,
      'resolution_condition': 'INDEPENDENT_PER_FRAME_LABEL_COMPLETION_PROVENANCE; IDENTICAL_MASK_BYTES_ARE_NOT_LANE_ABSENCE_TRUTH',
      'reference_promotable': False,
    }
  )


def snapshot():
  prior = s.read_json(ROOT / 'docs/cyberpilot/changes/comma10k-next-blocker-plan-v1.json')
  unseal(prior)
  if prior['receipt_sha256'] != PRIOR_SHA:
    raise ValueError('IMMUTABLE_PREVIOUS_NEXT_BLOCKER_PLAN_REQUIRED')
  calibration = c.admit(None)
  ego = g.ego_contract()
  private = d.pending()
  budget = c.projection_budget(calibration, None)
  registration = g.registration_gate(calibration, None)
  center = g.lane_center_gate(registration)
  protocol = calibration_protocol()
  labels = label_completeness_audit()
  nodes = copy.deepcopy(prior['nodes'])
  lookup = {n['code']: n for n in nodes}
  lookup['CALIBRATION_MEASUREMENT_PENDING']['evidence_sha256'] = calibration['receipt_sha256']

  def add(code, status, evidence, dependencies, resolution):
    node = {
      'code': code,
      'status': status,
      'evidence_sha256': evidence['receipt_sha256'],
      'evidence_kind': 'RECEIPT_SHA256',
      'dependencies': dependencies,
      'resolution_condition': resolution,
    }
    nodes.append(node)
    lookup[code] = node

  add(
    'CALIBRATION_ADMISSION_CONTRACT_DEFINED',
    'PASS_STRUCTURAL_ONLY',
    protocol,
    [],
    'Submission schema and immutable admission exist; actual physical artifact still pending',
  )
  add(
    'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
    'BLOCKED',
    calibration,
    ['CALIBRATION_MEASUREMENT_PENDING'],
    'Independent instrument/target/holdout review and observed device geometry, not merely positive schema validation',
  )
  add(
    'PROJECTION_UNCERTAINTY_BUDGET_UNAVAILABLE',
    'BLOCKED',
    budget,
    ['INDEPENDENT_CALIBRATION_VALIDATION_PENDING'],
    'Independently justified detector/intrinsic/extrinsic/distortion/road-plane bounds and certified nonlinear remainder over actual domain',
  )
  add(
    'INDEPENDENT_EGO_ASSOCIATION_CONTRACT_DEFINED',
    'PASS_STRUCTURAL_ONLY',
    ego,
    [],
    'Proposal algorithm and ambiguity gate defined; no nearest-side selection or ego-GT validation',
  )
  add(
    'EGO_ASSOCIATION_VALIDATION_PENDING',
    'BLOCKED',
    ego,
    ['INDEPENDENT_EGO_ASSOCIATION_CONTRACT_DEFINED', 'COMMA10K_EGO_LANE_IDENTITY_UNAVAILABLE'],
    'Independent left/right association GT and frozen domain validation, not all-paint mask or detector self-agreement',
  )
  add(
    'ROAD_REGISTRATION_CONTRACT_DEFINED',
    'PASS_STRUCTURAL_ONLY',
    registration,
    [],
    'Known-geometry transformations tested; no real metric registration performed',
  )
  add(
    'INDEPENDENT_LANE_CENTER_REFERENCE_UNAVAILABLE',
    'BLOCKED',
    center,
    ['ROAD_REGISTRATION_UNAVAILABLE', 'DESIRED_PATH_REFERENCE_UNAVAILABLE'],
    'Both validated registered boundaries, common covered samples and independently reviewed center-reference definition; not optimal driving path',
  )
  add(
    'PRIVATE_METADATA_PREPARATION_CONTRACT_DEFINED',
    'PASS_STRUCTURAL_ONLY',
    private,
    [],
    'Metadata/private/publication contract exists, actual inventory and separate execution authority absent',
  )
  add(
    'PRIVATE_HUMAN_HOLDOUT_PENDING',
    'BLOCKED',
    private,
    ['PRIVATE_METADATA_PREPARATION_CONTRACT_DEFINED'],
    'Freeze independent holdout before detector output; actual human boundary/ambiguity annotations, never training/selection',
  )
  lookup['INDEPENDENT_EXTRINSICS_UNAVAILABLE']['dependencies'] += ['INDEPENDENT_CALIBRATION_VALIDATION_PENDING']
  lookup['METRIC_CALIBRATION_UNAVAILABLE']['dependencies'] += ['INDEPENDENT_CALIBRATION_VALIDATION_PENDING', 'PROJECTION_UNCERTAINTY_BUDGET_UNAVAILABLE']
  lookup['ROAD_REGISTRATION_UNAVAILABLE']['dependencies'] += ['EGO_ASSOCIATION_VALIDATION_PENDING', 'ROAD_REGISTRATION_CONTRACT_DEFINED']
  lookup['PRIVATE_DOMAIN_VALIDATION_NOT_RUN']['dependencies'] += ['PRIVATE_HUMAN_HOLDOUT_PENDING']
  lookup['INDEPENDENT_REFERENCE_UNAVAILABLE']['dependencies'] = [n['code'] for n in nodes if n['code'] != 'INDEPENDENT_REFERENCE_UNAVAILABLE']
  return seal(
    {
      'schema': 'NEXT_BLOCKER_PLAN_V2_REFERENCE_INFRASTRUCTURE',
      'status': 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
      'prior_plan_sha256': PRIOR_SHA,
      'states': STATES,
      'state_machine_policy': POLICY,
      'nodes': nodes,
      'dependency_order': old.dependency_order(nodes),
      'critical_path': [
        'CALIBRATION_MEASUREMENT_PENDING',
        'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
        'METRIC_CALIBRATION_UNAVAILABLE',
        'ROAD_REGISTRATION_UNAVAILABLE',
        'INDEPENDENT_LANE_CENTER_REFERENCE_UNAVAILABLE',
      ],
      'parallel_prerequisites': [
        'EGO_ASSOCIATION_VALIDATION_PENDING',
        'DESIRED_PATH_REFERENCE_UNAVAILABLE',
        'INDEPENDENT_BLIND_HUMAN_REVIEW_NOT_AVAILABLE',
        'CULANE_OFFICIAL_REPRODUCTION_BLOCKED',
      ],
      'calibration_protocol': protocol,
      'calibration': calibration,
      'ego_contract': ego,
      'projection_budget': budget,
      'road_registration': registration,
      'lane_center': center,
      'private_preparation': private,
      'label_completeness_audit': labels,
      'private_comma4': 'NOT_OPENED',
      'sealed_reference': 'NOT_GENERATED',
      'private_input_allowed': False,
      'reference_promotable': False,
      'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
      'tool_sha256': identity(),
    }
  )


def validate_snapshot(value):
  unseal(value)
  if value != snapshot():
    raise ValueError('EXACT_PENDING_CURRENT_REFERENCE_SNAPSHOT_REQUIRED')
