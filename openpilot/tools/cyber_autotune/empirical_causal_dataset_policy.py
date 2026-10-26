"""Exact historical input admission for extraction only; no model authority."""
from pathlib import Path
import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_metadata as metadata

INPUT_PINS = {'cyber-lateral-observability-contract-v1.json': '2838621b5f9aa1acd7ed0b98de54cdb3a6e49349c5c04702ec2ac1ee2c5b5da0',
 'empirical-causal-context-schema-v2.json': 'b21f2b531dd719ba763c81594de82ac443e3ae9f9f3451fec67cb1065da52159',
 'empirical-plant-profiles-v1.json': 'd9e72f6cce395ff46d6323d8e166023c66d81e159f9b46666cc74a16da817b1b',
 'empirical-plant-v2-numeric-authorization-v1.json': 'fcaee143ecbd280be1ff0c16c19c02b16d47d248b41a6b5b30220f91c680e17a',
 'empirical-plant-v2-route-coverage-v1.json': '960cddddab147cbd15188683a2bfe4331c6d66e0059d27ef16cd8ef7c3770f11',
 'empirical-plant-v2-train-dev-split-v1.json': '05bbdae01bcf22bab814ac2545514e18eff28afc346e77f1d1d0bceb8198c81f',
 'empirical-plant-v3-folds-v1.json': '0b4e62a8e75519edaab900a274878daaac0893cfe9d903fd840a52c825da60ee',
 'empirical-plant-v3-route-coverage-v1.json': '208c67899cd0577b571848ae5f2ae48e8fc0635b36d20069c7507be003e92e75',
 'empirical-source-equivalence-classes-v1.json': '580fb04a697dc3bc0bf8f06e7cbec690137f0da7ac3d8185c2e11abe8789167e',
 'empirical-source-grid-emission-readiness-v1.json': '13da4be741d49a6303e8512c99f27be5728101c711cda21dac35549f453a0efe',
 'empirical-source-route-reclassification-v1.json': 'ecd5832bd3bc9c69914a7fe2c8508a8a0f792ee251371e75ebaab3481b4ba814',
 'empirical-stage-a-causal-recovery-policy-v1.json': '1f1f286f42371935d24081302a2214ec2389df0e1a92fe2b1d089a8ec6ac2ad8'}
MODULES = ('policy', 'reader', 'alignment', 'store', 'execution')
ROLE = 'RETROSPECTIVE_TRAIN_DEV_CV_POOL'
SETTINGS = ('CustomSteerMax', 'CustomSteerDeltaUp', 'CustomSteerDeltaDown', 'CustomSteerDeltaUpLC', 'CustomSteerDeltaDownLC')
WHITELIST = {
  'initData': ['gitCommit', 'gitRemote', 'gitBranch', 'version', 'dirty', 'osVersion', 'wallTimeNanos',
               'bootlogId', 'dongleId', 'params.entries.ALLOWLIST_ONLY'],
  'carParams': list(metadata.PROFILE_FIELDS),
  'carState': ['steeringAngleDeg', 'steeringRateDeg', 'steeringPressed', 'steeringTorque', 'steeringTorqueEps',
               'steerFaultTemporary', 'steerFaultPermanent', 'vEgo', 'wheelSpeeds.fl/fr/rl/rr', 'gearShifter', 'yawRate'],
  'carControl': ['actuators.torque', 'latActive'],
  'carOutput': ['actuatorsOutput.torque', 'actuatorsOutput.torqueOutputCan'],
  'gyroscope': ['source', 'timestamp', 'gyroUncalibrated.v'],
}
UNAVAILABLE = {
  'physical_eps_applied_torque': 'NO_PHYSICAL_EPS_ACKNOWLEDGEMENT',
  'actual_curvature': 'NO_SOURCE_BOUND_MEASUREMENT_OR_RECONSTRUCTION',
  'desired_curvature': 'NOT_IN_EXECUTION_WHITELIST',
  'safety_limited': 'SAFETY_LIMITED_UNAVAILABLE',
  'curvature_limited': 'CURVATURE_LIMITED_UNAVAILABLE',
  'rate_limit_reason': 'RATE_LIMIT_REASON_UNAVAILABLE',
  'driver_limit_reason': 'DRIVER_LIMIT_REASON_UNAVAILABLE',
  'live_alive': 'LIVE_SUBMASTER_HEALTH_NOT_LOGGED',
  'live_freqOk': 'LIVE_SUBMASTER_HEALTH_NOT_LOGGED',
  'live_updated': 'LIVE_SUBMASTER_HEALTH_NOT_LOGGED',
  'roll': 'NOT_IN_EXECUTION_WHITELIST',
  'source_control_transaction_id': 'REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE',
}


def read(path):
  path = Path(path)
  if not path.is_absolute() or '..' in path.parts or any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('NO_ALIAS_OR_TRAVERSAL_RECEIPT')
  return p.verify(json.loads(path.read_bytes()))


def inputs():
  result = {name: read(p.PUBLIC / name) for name in INPUT_PINS}
  if any(result[name]['receipt_sha256'] != digest for name, digest in INPUT_PINS.items()):
    raise ValueError('HISTORICAL_PUBLIC_PIN_DRIFT')
  return result


def resolve_routes(evidence=None):
  x = inputs() if evidence is None else evidence
  split = x['empirical-plant-v2-train-dev-split-v1.json']
  folds = x['empirical-plant-v3-folds-v1.json']['folds']
  routes = sorted((r for r in split['routes'] if r['role'] == 'TRAIN'), key=lambda r: r['route_id'])
  ids = {r['route_id'] for r in routes}
  if len(routes) != 2 or len(ids) != 2 or len(folds) != 2:
    raise ValueError('EXACT_TWO_HISTORICAL_TRAIN_ROUTES_REQUIRED')
  if [{f['train_route'], f['development_route']} for f in folds] != [ids, ids] or folds[0]['train_route'] != folds[1]['development_route']:
    raise ValueError('EXACT_V3_ROUTE_INVERSION_REQUIRED')
  corrected = {r['route_id']: r for r in x['empirical-source-route-reclassification-v1.json']['routes']}
  coverage = {r['route_id']: r for r in x['empirical-plant-v3-route-coverage-v1.json']['routes']}
  result = []
  for r in routes:
    c, v = corrected[r['route_id']], coverage[r['route_id']]
    if (c['classification'] != 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE' or c['v1_overlap']
        or not c['signal_semantics_complete'] or not c['profile_complete']
        or v['bridge']['status'] != 'ROUTE_COMMAND_BRIDGE_CONFIRMED' or v['bridge']['steer_max'] != 409
        or any(v['coverage']['bins'][b]['common_design_rows'] < 201 for b in ('LOW', 'MEDIUM', 'HIGH'))):
      raise ValueError('SOURCE_COMPLETE_HIGH_SUPPORT_NON_V1_ROUTES_ONLY')
    cls = next((v for v in x['empirical-source-equivalence-classes-v1.json']['classes'] if v['class_id'] == c['semantic_class_id']), None)
    if cls is None or cls['status'] != 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENT' or r['source_commit'] not in cls['members']:
      raise ValueError('PARTIAL_OR_UNADMITTED_SOURCE_CLASS')
    result.append({**r, 'role': ROLE, 'historical_role': 'TRAIN', 'historical_numeric_use': 'USED_NUMERIC_TRAIN_AND_RETROSPECTIVE_DEVELOPMENT',
                   'holdout_allowed': False, 'independent_validation_allowed': False,
                   'semantic_class_id': c['semantic_class_id'], 'empirical_profile_sha256': c['empirical_profile_sha256']})
  for key in ('source_commit', 'full_carparams_sha256', 'empirical_profile_sha256', 'semantic_class_id', 'adapter_sha256'):
    if len({r[key] for r in result}) != 1:
      raise ValueError('EXACT_SOURCE_PROFILE_CLASS_ADAPTER_REQUIRED')
  return result


def validate_source(route, source, adapter, origin=None):
  if (source.get('commit') != route.get('source_commit') or source.get('complete') is not True
      or source.get('repository') != 'https://github.com/ajouatom/openpilot'
      or source.get('receipt_sha256') != route.get('source_fingerprint_sha256')):
    raise ValueError('EXACT_PUBLIC_SOURCE_REQUIRED')
  if (origin is None or origin.get('receipt_sha256') != 'cdc34c85bbd3f7f255ee96d19e70b61bd96c3c21c723f10972ffc38ec5f5637d'
      or source['commit'] not in origin.get('commits', [])
      or origin.get('repository') != source['repository']):
    raise ValueError('EXACT_PUBLIC_SOURCE_REQUIRED')
  p.verify(origin)
  metadata.validate_adapter(adapter, source)
  if adapter['receipt_sha256'] != route['adapter_sha256']:
    raise ValueError('EXACT_RECORDED_ADAPTER_REQUIRED')


def code_identity():
  directory = Path(__file__).parent
  return {name: p.sha((directory / ('empirical_causal_dataset_' + name + '.py')).read_bytes()) for name in MODULES}


def policy():
  return p.seal({
    'schema': 'EMPIRICAL_CAUSAL_TRAIN_DEV_POLICY_V1', 'generation': 'EMPIRICAL_CAUSAL_TRAIN_DEV_GENERATION_V1',
    'scope': 'RETROSPECTIVE_DATA_EXTRACTION_PROVENANCE_CAUSAL_CONTEXT_ONLY',
    'preflight_blocker_receipt_sha256': 'a7da791f8e7fe735fb980ec2dfcf6b2acd43e4f061877136dad39d9fc8dc41d1',
    'historical_inputs': INPUT_PINS, 'executor_sources': code_identity(), 'role': ROLE,
    'dt_ns': 10_000_000, 'max_age_ns': 20_000_000,
    'alignment': 'INTEGER_GRID_STATE_TARGET_LATEST_PAST_NO_INTERPOLATION',
    'nonmonotonic': 'REJECT_SEGMENT', 'all_aligned_rows_preserved': True,
    'raw_kind_allowlist': ['rlog.zst'],
    'historical_qlog_policy': 'METADATA_BOUND_EXCLUSION_NO_NUMERIC_OPENING_HARD_BLOCK_FULL_REPRODUCTION',
    'unavailable': 'NULL_VALIDITY_MASK_NO_ZERO_OR_FALSE_FILL',
    'settings_allowlist': list(SETTINGS), 'signal_whitelist': WHITELIST,
    'causal_runs': 'SEGMENT_GAP_REQUIRED_FIELD_UNAVAILABLE_RESET_NOT_SPEED_OR_INTERVENTION',
    'legacy_runs': 'DIAGNOSTIC_VALID_SAME_SPEED_BIN_SEGMENT_LOCAL_HISTORY_45',
    'command_linkage': 'PUBLISH_ALIGNED_REQUEST_OUTPUT_DIFFERENCE',
    'transaction_link': 'REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE',
    'unavailable_fields': UNAVAILABLE, 'holdout_opening': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0,
    'reservation': 'NONE', 'model_fitting': 'NOT_RUN', 'model_selection': 'NOT_RUN', 'candidate_execution': 'NOT_RUN',
    'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED', 'historical_track': 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
    'calibration_blockers': p.BLOCKERS,
    'privacy': 'AGGREGATES_HASHES_OPAQUE_IDS_ONLY_NO_ROWS_VALUES_PATHS_TIMESTAMPS',
    'repeatability': 'TWO_INDEPENDENT_RAW_EXTRACTIONS_EXACT_BYTES_SINGLE_THREAD_NO_RNG',
    'schema_base_sha256': INPUT_PINS['empirical-causal-context-schema-v2.json'],
    'h1_base_sha256': INPUT_PINS['cyber-lateral-observability-contract-v1.json'],
  })


def require_segment(auth, rid, digest):
  if rid not in auth['segments'] or digest not in auth['segments'][rid]:
    raise ValueError('EXACT_ROUTE_AND_SEGMENT_ALLOWLIST_REQUIRED')
