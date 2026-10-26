"""Remaining reference dependencies. Design-only private diagnostic; no acquisition path."""

from pathlib import Path

from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune import lane_tail_assisted_diagnostic as d
from openpilot.tools.cyber_autotune import lane_tail_second_review as b
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

PRIOR_SHA = 'e10ac47cb038ff1d767f02dba2d1387beed3e102e6702ea034196b167a0281cb'
ROOT = Path(__file__).resolve().parents[3]
POLICY = {
  'schema': 'NEXT_REFERENCE_BLOCKER_POLICY_V1',
  'state': 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
  'private': 'DESIGN_ONLY_NONQUALIFYING_PIXELS; THIS_INCREMENT_NOT_AUTHORIZED_TO_OPEN_PRIVATE_INPUT',
  'geometry': 'INDEPENDENT_EXTRINSICS_AND_UNCERTAINTY_BEFORE_METER_REGISTRATION; PATH_SOURCE_DEFINITION_CAN_RUN_IN_PARALLEL',
  'review': 'EXPOSED_FIRST_REVIEWER_CANNOT_REVIEW_SAME29_BLIND_BY_NEW_ID',
  'threshold': 'NO_NEW_DETECTOR_ACCEPTANCE_THRESHOLD_FROM_ASSISTED_OR_DIAGNOSTIC_RESULTS',
}
POLICY_SHA = digest(canonical(POLICY))


def validate_diagnostic(value):
  return d.validate_result(value)


def dependency_order(nodes):
  if type(nodes) is not list or len({n['code'] for n in nodes}) != len(nodes):
    raise ValueError('UNIQUE_DEPENDENCY_NODES_REQUIRED')
  lookup = {n['code']: n for n in nodes}
  if any(type(n['dependencies']) is not list or len(set(n['dependencies'])) != len(n['dependencies']) or set(n['dependencies']) - set(lookup) for n in nodes):
    raise ValueError('KNOWN_UNIQUE_DEPENDENCIES_REQUIRED')
  remaining, order = set(lookup), []
  while remaining:
    ready = sorted(code for code in remaining if set(lookup[code]['dependencies']) <= set(order))
    if not ready:
      raise ValueError('BLOCKER_DEPENDENCY_CYCLE')
    order.extend(ready)
    remaining.difference_update(ready)
  return order


def private_diagnostic_contract(diagnostic):
  validate_diagnostic(diagnostic)
  return seal(
    {
      'schema': 'PRIVATE_PIXEL_DIAGNOSTIC_ONLY_V1',
      'status': 'PROPOSED_NOT_RUN',
      'public_diagnostic_sha256': diagnostic['receipt_sha256'],
      'policy_sha256': POLICY_SHA,
      'execution_authorized_this_increment': False,
      'private_input_allowed': False,
      'qualification_allowed': False,
      'sealed_reference_allowed': False,
      'detector_reselection_allowed': False,
      'detector_config_mutation_allowed': False,
      'confidence_threshold_optimization_allowed': False,
      'modelv2_path_or_lane_allowed': False,
      'candidate_outputs_allowed': False,
      'raw_private_repository_publication_allowed': False,
      'reference_promotable': False,
      'unit': 'px',
      'meter_conversion_allowed': False,
      'future_requirements': [
        'SEPARATELY_DECLARED_DIAGNOSTIC_EXCEPTION_TO_EXISTING_PRIVATE_GATE',
        'EXACT_FROZEN_PUBLIC_DETECTOR_SOURCE_WEIGHT_CONFIG_ENVIRONMENT',
        'METADATA_SAMPLE_MANIFEST_FREEZE_BEFORE_FRAME_OR_DETECTOR_OUTPUT_OPEN',
        'PRIVATE_LOCAL_STORAGE_AND_PUBLICATION_REDACTION',
        'NO_PRIVATE_SELECTION_SEARCH_TRAINING_OR_QUALIFICATION',
        'INDEPENDENT_HUMAN_HOLDOUT_IS_A_SEPARATE_REQUIRED_VALIDATION_NOT_SYNTHESIZED',
      ],
      'official_benchmark_exception': 'NOT_A_PUBLIC_GT_PASS_OR_REFERENCE_CHAIN_BYPASS',
    }
  )


def blocker_plan(diagnostic, blind_protocol):
  validate_diagnostic(diagnostic)
  b.validate_protocol(blind_protocol)
  if blind_protocol['manifest_sha256'] != diagnostic['manifest_sha256'] or blind_protocol['scope'] != diagnostic['manifest_scope']:
    raise ValueError('PLAN_MANIFEST_BINDING_MISMATCH')
  prior = s.read_json(ROOT / 'docs/cyberpilot/changes/comma10k-assisted-review-blockers-v1.json')
  unseal(prior)
  if prior['receipt_sha256'] != PRIOR_SHA:
    raise ValueError('IMMUTABLE_PREVIOUS_BLOCKER_REQUIRED')
  nodes = []
  for node in prior['children']:
    if node['code'] in ('COMMA10K_TAIL_HUMAN_REVIEW_PENDING', 'COMMA10K_ASSISTED_HUMAN_REVIEW_COMPLETE', 'TAIL_CAUSAL_ATTRIBUTION_UNRESOLVED'):
      continue
    path = ROOT / 'docs/cyberpilot/changes' / node['evidence_file']
    if path.name != node['evidence_file'] or digest(path.read_bytes()) != node['evidence_file_sha256']:
      raise ValueError('PRIOR_BLOCKER_EVIDENCE_FILE_DRIFT')
    code = 'PRIVATE_DOMAIN_VALIDATION_NOT_RUN' if node['code'] == 'PRIVATE_HUMAN_VALIDATION_NOT_RUN' else node['code']
    nodes.append(
      {
        'code': code,
        'status': node['status'],
        'evidence_sha256': node['evidence_file_sha256'],
        'evidence_kind': 'FILE_SHA256',
        'resolution_condition': node['resolution_condition'],
        'dependencies': node['dependencies'],
      }
    )
  nodes.extend(
    [
      {
        'code': 'COMMA10K_ASSISTED_HUMAN_REVIEW_COMPLETE',
        'status': 'TEST_ONLY' if diagnostic['status'] == 'TEST_ONLY_NOT_HUMAN_EVIDENCE' else 'PASS_SUPPORTING_DIAGNOSTIC_ONLY',
        'evidence_sha256': diagnostic['receipt_sha256'],
        'evidence_kind': 'RECEIPT_SHA256',
        'resolution_condition': 'Satisfied for assisted sample diagnostics only; does not resolve any blind/qualification gate',
        'dependencies': ['COMMA10K_FULL_EVALUATION_COMPLETE'],
      },
      {
        'code': 'INDEPENDENT_BLIND_HUMAN_REVIEW_NOT_AVAILABLE',
        'status': 'BLOCKED',
        'evidence_sha256': blind_protocol['receipt_sha256'],
        'evidence_kind': 'RECEIPT_SHA256',
        'resolution_condition': 'New uninformed reviewer with opaque ID and truthful prior-nonexposure attestation; all29 immutable separate rows',
        'dependencies': ['COMMA10K_FULL_EVALUATION_COMPLETE'],
      },
      {
        'code': 'CALIBRATION_MEASUREMENT_PENDING',
        'status': 'BLOCKED',
        'evidence_sha256': prior['receipt_sha256'],
        'evidence_kind': 'RECEIPT_SHA256',
        'resolution_condition': 'Independent physical pose/height/intrinsic and uncertainty measurements; model-derived live values are not truth',
        'dependencies': [],
      },
      {
        'code': 'INDEPENDENT_REFERENCE_UNAVAILABLE',
        'status': 'BLOCKED',
        'evidence_sha256': prior['receipt_sha256'],
        'evidence_kind': 'RECEIPT_SHA256',
        'resolution_condition': 'All evidence prerequisites + existing strict sealed reference admission; never promoted by diagnostic receipts',
        'dependencies': [],
      },
    ]
  )
  lookup = {n['code']: n for n in nodes}
  lookup['INDEPENDENT_EXTRINSICS_UNAVAILABLE']['dependencies'] = ['CALIBRATION_MEASUREMENT_PENDING']
  lookup['METRIC_CALIBRATION_UNAVAILABLE']['dependencies'] = ['INDEPENDENT_EXTRINSICS_UNAVAILABLE']
  lookup['ROAD_REGISTRATION_UNAVAILABLE']['dependencies'] = ['METRIC_CALIBRATION_UNAVAILABLE', 'COMMA10K_EGO_LANE_IDENTITY_UNAVAILABLE']
  lookup['DESIRED_PATH_REFERENCE_UNAVAILABLE']['dependencies'] = ['ROAD_REGISTRATION_UNAVAILABLE']
  lookup['PRIVATE_DOMAIN_VALIDATION_NOT_RUN']['dependencies'] = [
    'CULANE_OFFICIAL_REPRODUCTION_BLOCKED',
    'PUBLIC_PIXEL_QUALIFICATION_THRESHOLD_UNJUSTIFIED',
    'INDEPENDENT_BLIND_HUMAN_REVIEW_NOT_AVAILABLE',
  ]
  lookup['INDEPENDENT_REFERENCE_UNAVAILABLE']['dependencies'] = [n['code'] for n in nodes if n['code'] != 'INDEPENDENT_REFERENCE_UNAVAILABLE']
  contract = private_diagnostic_contract(diagnostic)
  return seal(
    {
      'schema': 'NEXT_BLOCKER_PLAN_V1',
      'status': POLICY['state'],
      'diagnostic_sha256': diagnostic['receipt_sha256'],
      'blind_protocol_sha256': blind_protocol['receipt_sha256'],
      'prior_blocker_sha256': prior['receipt_sha256'],
      'policy_sha256': POLICY_SHA,
      'source_sha256': digest(Path(__file__).read_bytes()),
      'nodes': nodes,
      'dependency_order': dependency_order(nodes),
      'answers': {
        'software_work_without_blind_reviewer': True,
        'public_validation_does_not_supply_ego_identity': True,
        'independent_geometry_is_meter_critical_path': True,
        'registration_before_coordinate_bound_desired_path': True,
        'desired_path_provenance_design_can_run_in_parallel': True,
        'private_pixel_diagnostic': 'WORTH_DESIGNING_NONQUALIFYING_ONLY_NOT_RUN',
      },
      'next_engineering_actions': [
        'IMPLEMENT_EVIDENCE_ADMISSION_FOR_EXISTING_INDEPENDENT_PHYSICAL_CALIBRATION_PROTOCOL_WITHOUT_INVENTING_MEASUREMENTS',
        'DEFINE_INDEPENDENT_EGO_ASSOCIATION_AND_ROAD_FRAME_REGISTRATION_WITH_DESIRED_PATH_PROVENANCE_IN_PARALLEL',
        'PREPARE_SEPARATELY_DECLARED_PRIVATE_PIXEL_DIAGNOSTIC_INPUT_MANIFEST_AND_PRIVACY_CONTRACT; DO_NOT_OPEN_INPUTS_YET',
        'AWAIT_NEW_BLIND_REVIEWER_AND_OFFICIAL_CULANE_ACCESS_WITHOUT_BYPASS',
      ],
      'private_diagnostic_contract': contract,
      'private_input_allowed': False,
      'sealed_reference_allowed': False,
      'reference_promotable': False,
      'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    }
  )
