"""Whitelist source hashes and aggregate readiness; private blobs stay local."""

from collections import Counter
from pathlib import Path
import re
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_policy as policy
from openpilot.tools.cyber_autotune import empirical_source_dependencies as dependencies
from openpilot.tools.cyber_autotune import empirical_source_metadata as adapter
from openpilot.tools.cyber_autotune import empirical_source_execution as execution
from openpilot.tools.cyber_autotune import empirical_cross_root_publication as historical

PINS = {'empirical-plant-profiles-v1.json': 'd9e72f6cce395ff46d6323d8e166023c66d81e159f9b46666cc74a16da817b1b',
 'empirical-source-audit-readiness-v1.json': '575bd220977b541bdbbe72a5549a9aae1459fdfc0659f3a3252c8106ad500ac8',
 'empirical-source-audit-selection-v1.json': '9317b4b5a8a573b0b7268c973096f3d4163346b63c1eaa28bf1b950a89fcdbc8',
 'empirical-source-audit-triage-policy-v1.json': '43966d3f7a1416653da32907137c8dd223184af252aab97112b2dd37b6f8dd2f',
 'empirical-source-equivalence-classes-v1.json': '580fb04a697dc3bc0bf8f06e7cbec690137f0da7ac3d8185c2e11abe8789167e',
 'empirical-source-manifest-v1.json': '9ad1fa7b5c9121170254b12558231535b168e29cc81d4f4602e615ea96259777',
 'empirical-source-route-reclassification-v1.json': 'ecd5832bd3bc9c69914a7fe2c8508a8a0f792ee251371e75ebaab3481b4ba814',
 'empirical-source-semantic-fingerprints-v1.json': '96f61f8ae72963aad671989a4c1fcb80717355d5421ef322a147d6e101ad756d',
 'empirical-source-signal-matrix-v1.json': '67773d7c89d8900dd6760a7c9bd43a78a437708f05b61b6abb9b98ede6ed57ab',
 'future-empirical-holdout-admission-v1.json': '965490f3ea177f45261e5354c96ad8d89af29e07f56e49d29be7308a5f968fd7'}


def schema_signal_fields(data):
  targets = ('carOutput', 'carControl', 'carState', 'gyroscope', 'sensorEvents',
             'torqueOutputCan', 'torque', 'steeringAngleDeg', 'steeringRateDeg',
             'yawRate', 'wheelSpeeds', 'vEgo', 'latActive', 'steeringPressed',
             'steerFaultTemporary', 'steerFaultPermanent', 'gyroUncalibrated', 'timestamp')
  result = {}
  for name in targets:
    result[name] = re.findall(r'\b' + name + r'\s*@\s*(\d+)\s*:\s*([A-Za-z0-9_.()]+)', data.decode('utf-8-sig'))
  return result


def dbc_signal_definitions(data):
  names = ('YAW_RATE', 'SAS_Angle', 'SAS_Speed', 'WHL_SPD_FL', 'WHL_SPD_FR',
           'WHL_SPD_RL', 'WHL_SPD_RR', 'LAT_ACCEL', 'CR_Mdps_StrColTq', 'CR_Mdps_OutTq',
           'CF_Mdps_ToiUnavail', 'CF_Mdps_ToiFlt')
  rows = {}
  message = None
  for line in data.decode().splitlines():
    header = re.match(r'BO_\s+(\d+)\s+(\w+)\s*:', line)
    if header:
      message = (header[2], int(header[1]), line)
    match = re.match(r'\s*SG_\s+(\w+)\s*:', line)
    if match and match[1] in names and message:
      key = message[0] + '.' + match[1]
      if key in rows:
        raise ValueError('DUPLICATE_DBC_MESSAGE_SIGNAL')
      rows[key] = {'message': message[0], 'address': message[1], 'signal': match[1],
                   'definition': line.strip(), 'source_slice_sha256': p.sha((message[2]+'\n'+line).encode())}
  return rows


def source_signal_matrix(source, schema_fields, dbc_definitions, reviewed=False):
  required_dbc = {'ESP12.YAW_RATE', 'SAS11.SAS_Angle', 'SAS11.SAS_Speed',
                  'WHL_SPD11.WHL_SPD_FL', 'WHL_SPD11.WHL_SPD_FR', 'WHL_SPD11.WHL_SPD_RL', 'WHL_SPD11.WHL_SPD_RR'}
  field_names = {name for fields in schema_fields.values() for name, values in fields.items() if values}
  if reviewed and (not required_dbc <= set(dbc_definitions) or
                   not {'torqueOutputCan', 'torque', 'steeringAngleDeg', 'yawRate', 'carOutput'} <= field_names):
    raise ValueError('REVIEWED_SIGNAL_SCHEMA_INCOMPLETE')
  result = {
    'commit': source['commit'], 'source_fingerprint_sha256': source['receipt_sha256'],
    'field_ids_and_types': schema_fields, 'dbc_signal_definitions': dbc_definitions,
    'signals': {
      'torqueOutputCan': 'AVAILABLE_BY_SOURCE_NOT_RUNTIME_VERIFIED',
      'normalized_output_torque': 'AVAILABLE_BY_SOURCE_RUNTIME_BRIDGE_NOT_RUN',
      'requested_torque': 'AVAILABLE_BY_SOURCE',
      'steering_angle': 'AVAILABLE_BY_SOURCE_SAS11_DEGREES',
      'steering_rate': 'AVAILABLE_BY_SOURCE_SAS11',
      'yaw': 'SEMANTICS_PENDING_DBC_UNIT_EMPTY',
      'wheel_speeds': 'AVAILABLE_BY_SOURCE',
      'lateral_acceleration': 'SEMANTICS_PENDING',
      'direct_gyro': 'AVAILABLE_BY_SOURCE_RAD_PER_S_DEVICE_AXES',
      'active_driver_fault_context': 'AVAILABLE_BY_SOURCE',
      'safety_curvature_limit_reason': 'SEMANTICS_PENDING_NO_FALSE_DEFAULT',
      'acquisition_publish_age': 'SEMANTICS_PENDING',
    },
    'gyro_producer': 'LSM6DS3_8_75_MDPS_PER_LSB_TIMES_PI_OVER_180_AXES_Y_NEG_X_Z_IRQ_TIMESTAMP',
    'gyro_frame': 'DEVICE_AXIS_MAPPING_NOT_INDEPENDENT_VEHICLE_FRAME_CALIBRATION',
    'command': 'POST_CARCONTROLLER_LOGGED_REPRESENTATION_NOT_EPS_ACK',
    'card_order': 'STATE_UPDATE_PUBLISHES_PREVIOUS_LAST_ACTUATORS_THEN_CURRENT_CONTROLS_UPDATE',
    'static_steer_max': 'STATIC_STEER_MAX_SOURCE_BOUND_PROFILE_BRANCH_REVIEW_REQUIRED',
    'runtime_steer_max': 'RUNTIME_STEER_MAX_UNAVAILABLE_NUMERIC_CONFIRMATION_PENDING',
    'carstate_selected_dbc': sorted(required_dbc & set(dbc_definitions)),
  }
  if not reviewed:
    result['signals'] = dict.fromkeys(result['signals'], 'SEMANTICS_PENDING_SOURCE_DIFF_NOT_REVIEWED')
    result['signals']['yaw'] = 'SEMANTICS_PENDING_DBC_UNIT_EMPTY'
    result['gyro_producer'] = 'SEMANTICS_PENDING_SOURCE_DIFF_NOT_REVIEWED'
    result['card_order'] = 'SEMANTICS_PENDING_SOURCE_DIFF_NOT_REVIEWED'
  return result


def classify_route(original, rows, semantic_class, scope_complete):
  expected = set(original['source_hashes'])
  relevant = {r['source_sha256']: r for r in rows if r['source_sha256'] in expected}
  infos = [r['metadata'] for r in relevant.values() if r['metadata'] is not None]
  all_present = expected == set(relevant) and len(infos) == len(expected)
  origins = {x['init']['origin_status'] for x in infos}
  origin_ok = origins == {'SOURCE_COMMIT_PUBLICLY_AVAILABLE'}
  profile_hashes = {x['profile']['full_carparams_sha256'] for x in infos}
  subset_hashes = {x['profile']['empirical_profile_sha256'] for x in infos}
  profiles_ok = (profile_hashes == {original['generation']['carparams_sha256']} and len(subset_hashes) == 1)
  profile = infos[0]['profile'] if infos else None
  applicable = bool(profile and profile['fields']['carFingerprint'] == 'HYUNDAI_SANTA_FE_2022'
                    and profile['fields']['steerControlType'] == 'torque'
                    and not (profile['fields']['flags'] & 8192))
  classification = adapter.route_classification(original, all_present and profiles_ok,
                                                'SOURCE_COMMIT_PUBLICLY_AVAILABLE' if origin_ok else 'SOURCE_REMOTE_AMBIGUOUS')
  return {
    'route_id': original['route_id'], 'generation_id': p.sha(p.canonical(original['generation'])),
    'original_status': original['status'], 'classification': classification,
    'semantic_class_id': semantic_class, 'signal_semantics_complete': bool(scope_complete and applicable and origin_ok),
    'profile_complete': bool(profiles_ok and applicable),
    'empirical_profile_sha256': next(iter(subset_hashes)) if len(subset_hashes) == 1 else None,
    'full_carparams_sha256': next(iter(profile_hashes)) if len(profile_hashes) == 1 else None,
    'source_origin_states': sorted(origins), 'metadata_source_count': len(expected),
    'revalidated_source_count': len(infos), 'segment_count': original['segment_count'],
    'prior_analysis': original['prior_analysis'], 'v1_overlap': original['v1_overlap'],
    'untouched': False, 'holdout_allowed': False, 'maximum_future_role': 'TRAIN_DEV_CANDIDATE_ONLY',
    'numeric_coverage': None,
  }


def publishable_route(row):
  fields = ('route_id', 'generation_id', 'original_status', 'classification', 'semantic_class_id',
            'signal_semantics_complete', 'profile_complete', 'empirical_profile_sha256',
            'full_carparams_sha256', 'source_origin_states', 'metadata_source_count',
            'revalidated_source_count', 'segment_count', 'prior_analysis', 'v1_overlap',
            'untouched', 'holdout_allowed', 'maximum_future_role', 'numeric_coverage')
  result = {k: row[k] for k in fields}
  for name in ('route_id', 'generation_id', 'semantic_class_id', 'empirical_profile_sha256', 'full_carparams_sha256'):
    if result[name] is not None and not re.fullmatch('[0-9a-f]{64}', result[name]):
      raise ValueError('OPAQUE_PUBLIC_HASH_REQUIRED')
  if result['untouched'] is not False or result['holdout_allowed'] is not False or result['numeric_coverage'] is not None:
    raise ValueError('METADATA_ONLY_AUTHORITY_VIOLATION')
  if result['maximum_future_role'] != 'TRAIN_DEV_CANDIDATE_ONLY':
    raise ValueError('OLD_ROUTE_ROLE_VIOLATION')
  return result


def verified_blob(repo, source, role):
  row = source['files'][role]
  data = subprocess.check_output(['git', '-c', f'safe.directory={repo}', '-C', str(repo),
                                  'show', f"{source['commit']}:{row['path']}"])
  if p.sha(data) != row['file_sha256']:
    raise ValueError('PUBLIC_SIGNAL_SOURCE_DRIFT')
  return data


def derive(store, historical_store, source_repo):
  store = Path(store)
  historical.load()
  inventory = execution.read(Path(historical_store) / 'combined-inventory.json')
  if inventory['receipt_sha256'] != policy.INVENTORY_SHA:
    raise ValueError('HISTORICAL_INVENTORY_DRIFT')
  selected = execution.read(store / 'selection.json')
  if selected != policy.selection(inventory['generation_buckets']):
    raise ValueError('TRIAGE_SELECTION_DRIFT')
  origins = execution.read(store / 'public-origin.json')
  sources = {c: execution.read(store / 'fingerprints' / (c + '.json')) for c in origins['commits']}
  deps = {c: execution.read(store / 'dependencies' / (c + '.json')) for c in sources}
  closures = {c: execution.read(store / 'logical-closure' / (c + '.json')) for c in sources}
  review = execution.read(store / 'reviewed-differences.json')
  a, b = dependencies.PAIR
  dependencies.verify_review(review, sources[a], sources[b], deps[a], deps[b])
  closure_review = execution.read(store / 'logical-closure-review-deterministic.json')
  dependencies.verify_closure(closures[a], closures[b], closure_review)
  class_id = p.sha(p.canonical({'scope': review['scope'], 'review_sha256': review['receipt_sha256'],
                              'closure_review_sha256': closure_review['receipt_sha256']}))
  classes = [{
    'class_id': class_id, 'members': sorted(dependencies.PAIR),
    'status': 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENT', 'scope': review['scope'],
    'review_sha256': review['receipt_sha256'], 'closure_review_sha256': closure_review['receipt_sha256'], 'global_behavior_equivalent': False,
    'physical_runtime_equivalent': False, 'unsupported': ['PHYSICAL_YAW_UNIT', 'RUNTIME_STEER_MAX', 'ACQUISITION_AGE', 'VEHICLE_GYRO_FRAME'],
  }]
  for c in sources:
    if c not in dependencies.PAIR:
      classes.append({'class_id': p.sha(c.encode()), 'members': [c], 'status': 'SOURCE_AUDIT_PARTIAL',
                      'scope': 'EXACT_FILES_AND_SOURCE_METADATA_IDENTITY_REVIEWED_UNREVIEWED_SIGNAL_DIFFERENCES',
                      'unsupported': ['COMPLETE_RELEVANT_DIFF_REVIEW_TO_OTHER_SELECTED_COMMITS']})
  matrices = []
  for commit, source in sources.items():
    fields = {role: schema_signal_fields(verified_blob(source_repo, source, role))
              for role in ('schema_car', 'schema_log', 'schema_deprecated')}
    matrix = source_signal_matrix(source, fields, dbc_signal_definitions(verified_blob(source_repo, source, 'dbc')), commit in dependencies.PAIR)
    result = execution.read(store / 'metadata-results' / (commit + '.json'))
    counts = Counter()
    for row in result['rows']:
      if row['metadata'] is not None:
        counts.update(row['metadata']['envelope_counts'])
    # Required event presence only: never publish arbitrary event names or body values.
    matrix['metadata_message_presence'] = {name: counts[name] > 0 for name in
      ('carOutput', 'carControl', 'carState', 'carParams', 'initData', 'sensorEvents', 'gyroscope')}
    matrix['source_roles'] = {role: {'path': row['path'], 'file_sha256': row['file_sha256']}
                              for role, row in source['files'].items()}
    matrices.append(matrix)
  run_binding = p.seal({
    'schema': 'EMPIRICAL_SOURCE_METADATA_EXECUTION_BINDING_V1',
    'inventory_sha256': inventory['receipt_sha256'],
    'file_map_sha256': execution.read(store / 'selected-file-map.json')['receipt_sha256'],
    'source_results': {c: execution.read(store / 'metadata-results' / (c + '.json'))['receipt_sha256'] for c in sources},
    'adapters': {c: execution.read(store / 'adapters-final' / (c + '.json')) for c in sources},
    'numeric_payloads_opened': False, 'metadata_only': True,
  })
  rows, profiles = [], {}
  selected_ids = set(selected['primary'])
  for route in inventory['routes']:
    generation_id = p.sha(p.canonical(route['generation']))
    if generation_id not in selected_ids:
      continue
    commit = route['generation']['source_commit']
    result = execution.read(store / 'metadata-results' / (commit + '.json'))
    binding = execution.read(store / 'adapters-final' / (commit + '.json'))
    adapter.validate_adapter(binding, sources[commit])
    if result['binding_sha256'] != binding['receipt_sha256']:
      raise ValueError('ADAPTER_RESULT_IDENTITY_DRIFT')
    pair_member = commit in dependencies.PAIR
    classified = classify_route(route, result['rows'], class_id if pair_member else p.sha(commit.encode()), pair_member)
    rows.append(classified)
    for item in result['rows']:
      info = item['metadata']
      if info is not None:
        pr = info['profile']
        profiles[(pr['empirical_profile_sha256'], pr['full_carparams_sha256'])] = {
          'empirical_profile_sha256': pr['empirical_profile_sha256'], 'full_carparams_sha256': pr['full_carparams_sha256'],
          'schema': 'EMPIRICAL_PLANT_PROFILE_V1', 'relevant_fields': list(adapter.PROFILE_FIELDS),
          'fingerprint': pr['fields']['carFingerprint'], 'control_type': pr['fields']['steerControlType'],
          'runtime_steer_max': None, 'runtime_status': pr['steer_max_status'],
          'bus_configuration': 'LEGACY_SOURCE_BOUND_PT_BUS_0_CAM_BUS_2_PENDING_RUNTIME_SIGNAL_CONFIRMATION', 'numeric_bridge': 'NOT_RUN',
        }
  pool = adapter.train_dev_pool(rows)
  execution_ids = policy.execution_set(selected, max((len(x['route_ids']) for x in pool['pools']), default=0))
  if set(execution_ids) != selected_ids:
    raise ValueError('CONDITIONAL_SECONDARY_AUDIT_REQUIRED_BEFORE_COMPLETION')
  common = {'historical_inventory_sha256': inventory['receipt_sha256'], 'numeric_payloads_opened': False,
            'numeric_coverage': None, 'support_rows': None, 'command_numeric_check': 'NOT_RUN',
            'yaw_crosscheck': 'NOT_RUN', 'gyro_correlation': None, 'fitting': 'NOT_RUN',
            'model_selection': 'NOT_RUN', 'holdout_opened': False, 'model_metrics': None}
  outputs = {
    'empirical-source-audit-triage-policy-v1.json': policy.triage_policy(),
    'empirical-source-audit-selection-v1.json': p.seal({**common, 'schema': 'EMPIRICAL_SOURCE_AUDIT_SELECTED_EXECUTION_V1',
      'predeclared_selection': selected, 'executed_primary': selected['primary'], 'executed_secondary': [], 'executed_tertiary': [],
      'public_source_commits': sorted(sources), 'unavailable_commits': [],
      'primary_pool_count': sum(len(x['route_ids']) for x in pool['pools']), 'total_audited_generations': len(selected['primary'])}),
    'empirical-source-manifest-v1.json': p.seal({'schema': 'EMPIRICAL_SOURCE_MANIFEST_WITH_RESOLUTION_V1',
      'base': policy.manifest(), 'supplement': dependencies.dependency_policy(), 'logical_closure': dependencies.closure_policy(),
      'path_resolution': ['SENSOR_MAIN_CPP_TO_PYTHON', 'COMMON_CRC_TO_CAR_CRC'], 'dropped_required_roles': []}),
    'empirical-source-semantic-fingerprints-v1.json': p.seal({'schema': 'EMPIRICAL_SOURCE_SEMANTIC_FINGERPRINTS_V1',
      'fingerprints': list(sources.values()), 'supplemental_dependencies': list(deps.values()),
      'public_origin': origins, 'reviewed_differences': review, 'logical_closures': list(closures.values()), 'logical_closure_review': closure_review}),
    'empirical-source-equivalence-classes-v1.json': p.seal({'schema': 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENCE_CLASS_V1',
      'classes': classes, 'scope_restriction': 'SOURCE_CONTENT_LOGICAL_PUBLICATION_NOT_PHYSICAL_RUNTIME'}),
    'empirical-plant-profiles-v1.json': p.seal({'schema': 'EMPIRICAL_PLANT_PROFILES_V1', 'profiles': list(profiles.values()),
      'full_carparams_required_for_pool': True, 'subset_alone_can_merge': False}),
    'empirical-source-signal-matrix-v1.json': p.seal({'schema': 'EMPIRICAL_SOURCE_SIGNAL_MATRIX_V1',
      'matrices': matrices, 'runtime_numeric_verification': 'NOT_RUN'}),
    'empirical-source-route-reclassification-v1.json': p.seal({**common, 'schema': 'EMPIRICAL_SOURCE_ROUTE_RECLASSIFICATION_V1',
      'routes': [publishable_route(x) for x in rows], 'pools': pool, 'execution_binding': run_binding,
      'resolved_ambiguous_routes': 0, 'remaining_original_ambiguous_routes': 77,
      'original_incomplete_route_groups_unchanged': 95, 'unselected_routes_not_reclassified': len(inventory['routes']) - len(rows)}),
    'future-empirical-holdout-admission-v1.json': policy.future_holdout_contract(),
    'empirical-source-audit-readiness-v1.json': p.seal({**common, 'schema': 'EMPIRICAL_SOURCE_AUDIT_READINESS_V1',
      'status': 'SOURCE_SEMANTICS_EQUIVALENCE_AUDIT_COMPLETE', 'pool_status': pool['status'],
      'partial_source_classes': sum(c['status'] == 'SOURCE_AUDIT_PARTIAL' for c in classes),
      'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'old_route_pool_count': sum(len(x['route_ids']) for x in pool['pools']),
      'full_route_split_available': False, 'numeric_split_created': False,
      'state_counts': dict(Counter(x['classification'] for x in rows)),
      'calibration_blockers': p.BLOCKERS, 'sealed_reference': 'NOT_GENERATED',
      'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
      'historical': {'command_bridge': 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED',
                     'stage_a': 'EMPIRICAL_ACTUATOR_MODEL_ONLY', 'yaw': 'EMPIRICAL_YAW_MODEL_BLOCKED',
                     'yaw_signal': 'EMPIRICAL_YAW_SIGNAL_PARTIAL', 'yaw_unit': 'YAW_UNIT_LIKELY_NOT_CONFIRMED',
                     'ta': 'TA_STANDALONE_TRADEOFF_ONLY', 'sg': 'SG_CLOSED_LOOP_TRADEOFF_ONLY',
                     'v1': 'TRADEOFF_ONLY', 'v2': 'REJECTED', 'v2_violations': 37,
                     'current': 'BASELINE_EXACT', 'composition': 'COMPOSITION_NOT_AUTHORIZED',
                     'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
                     'search': 'SEARCH_NOT_AUTHORIZED', 'frozen_evaluation': 'FROZEN_EVALUATION_NOT_AUTHORIZED'}}),
  }
  return outputs


def load():
  historical.load()
  if not PINS:
    raise ValueError('PUBLIC_SOURCE_AUDIT_NOT_PINNED')
  result = {}
  for name, digest in PINS.items():
    row = execution.read(p.PUBLIC / name)
    if row['receipt_sha256'] != digest:
      raise ValueError('SOURCE_PUBLIC_EVIDENCE_DRIFT')
    result[name] = row
  return result
