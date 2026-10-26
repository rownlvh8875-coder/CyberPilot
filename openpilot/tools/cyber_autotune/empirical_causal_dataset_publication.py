"""Publish only aggregate extraction evidence; private arrays never leave the store."""
from collections import Counter

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as policy
from openpilot.tools.cyber_autotune import empirical_causal_dataset_execution as execution
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_source_execution as previous
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as logs

FILES = (
  'empirical-causal-train-dev-policy-v1.json',
  'empirical-causal-train-dev-route-set-v1.json',
  'empirical-causal-numeric-authorization-v1.json',
  'empirical-causal-context-schema-v2-execution-v1.json',
  'empirical-causal-signal-provenance-v1.json',
  'empirical-causal-command-stages-v1.json',
  'empirical-causal-route-coverage-v1.json',
  'empirical-causal-h1-mapping-v1.json',
  'empirical-causal-legacy-reproduction-v1.json',
  'empirical-causal-train-dev-repeatability-v1.json',
  'empirical-causal-train-dev-readiness-v1.json',
)
FORBIDDEN = {'aligned', 'rows', 'targets', 'predictions', 'coefficients', 'residuals', 'local_path', 'path',
             'grid_time_ns', 'state_time_ns', 'control_time_ns', 'output_time_ns', 'raw_command', 'xyz', 'row_origin'}
SOURCE_PATH_EXEMPTION = 'files'


def validate_public(row):
  p.verify(row)
  def visit(x, source_files=False):
    if isinstance(x, dict):
      if set(x) & (FORBIDDEN - ({'path'} if source_files else set())):
        raise ValueError('PRIVATE_ROWS_OR_VALUES_NOT_PUBLISHABLE')
      for key, value in x.items():
        visit(value, source_files or key == SOURCE_PATH_EXEMPTION)
    elif isinstance(x, list):
      for value in x:
        visit(value, source_files)
    elif isinstance(x, str) and (x.startswith('/') or '\\' in x):
      raise ValueError('PRIVATE_PATH_NOT_PUBLISHABLE')
  visit(row)
  return row


def repeatability(store, v2_store, v3_store, source_store, roots):
  """Compare both complete immutable outputs and hash the exact source set again."""
  store = storage.safe(store)
  a, b = (policy.read(store/n/'manifest.json') for n in ('repeat-1', 'repeat-2'))
  trees = {n: storage.tree_identity(store/n) for n in ('repeat-1', 'repeat-2')}
  if a != b or trees['repeat-1'] != trees['repeat-2']:
    raise ValueError('INDEPENDENT_EXTRACTION_REPEATABILITY_CONFLICT')
  after = {'v2': storage.tree_identity(v2_store), 'v3': storage.tree_identity(v3_store), 'source': storage.tree_identity(source_store)}
  before = policy.read(store/'historical-trees-before.json')['trees']
  if before != after:
    raise ValueError('HISTORICAL_PRIVATE_STORE_MUTATION')
  approved = previous.approved_root_map(roots)
  manifest = policy.read(store/'source-manifest.json')
  count = 0
  for segments in manifest['routes'].values():
    for segment in segments:
      if logs.file_sha(previous.source_location(segment['location'], approved)) != segment['source_sha256']:
        raise ValueError('RAW_SOURCE_PRESERVATION_FAILURE')
      count += 1
  result = p.seal({'schema': 'EMPIRICAL_CAUSAL_TRAIN_DEV_REPEATABILITY_V1', 'repeats': 2, 'exact': True,
    'dataset_manifest_sha256': a['receipt_sha256'], 'replica_tree_sha256': trees['repeat-1'],
    'route_count': len(a['routes']), 'extracted_segment_count': count, 'raw_source_hashes_before_after_exact': True,
    'historical_store_trees_before': before, 'historical_store_trees_after': after,
    'array_dtype_shape_order_bytes': 'EXACT', 'row_origin_run_snapshot_config_receipts': 'EXACT',
    'second_execution_model_apis_patched_to_fail': True, 'source_hash_check_does_not_decode_events': True})
  p.persist(store/'repeatability.json', result)
  return result


def publish(store, repeat, resume=None):
  store = storage.safe(store)
  private_policy, route_set, auth, manifest = (policy.read(store/n) for n in ('policy.json', 'route-set.json', 'authorization.json', 'repeat-1/manifest.json'))
  if private_policy != policy.policy() or repeat['dataset_manifest_sha256'] != manifest['receipt_sha256']:
    raise ValueError('PUBLICATION_POLICY_DATASET_DRIFT')
  routes = manifest['routes']
  route_counts = []
  for r in routes:
    route_counts.append({k: r[k] for k in ('route_id', 'source_commit', 'full_carparams_sha256', 'empirical_profile_sha256',
      'config_sha256', 'segment_count', 'historical_segment_count', 'coverage', 'required_field_coverage', 'bins',
      'mask_reason_counts', 'causal_run_length_distribution', 'field_coverage', 'transitions', 'source_age',
      'request_output_order', 'longest_causal_run', 'bridge', 'status')})
  lineage_complete = all(not r['excluded_sources'] for r in route_set['routes'])
  exact_legacy = all(r['legacy_reproduction_exact'] for r in routes)
  ready = lineage_complete and exact_legacy and all(r['status'] == 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY' for r in routes)
  outputs = {}
  outputs[FILES[0]] = private_policy
  outputs[FILES[1]] = route_set
  outputs[FILES[2]] = p.seal({'schema': 'EMPIRICAL_CAUSAL_NUMERIC_AUTHORIZATION_PUBLIC_V1',
    'private_authorization_sha256': auth['receipt_sha256'], 'route_set_sha256': route_set['receipt_sha256'],
    'policy_sha256': private_policy['receipt_sha256'], 'source_fingerprint_sha256': auth['source_fingerprint_sha256'],
    'numeric_adapter_sha256': auth['numeric_adapter_sha256'], 'recorded_adapter_sha256': auth['recorded_adapter_sha256'],
    'source_schema_sha256': auth['source_schema_sha256'], 'segment_sets': {
      rid: {'count': len(digests), 'set_sha256': p.sha(p.canonical(digests))} for rid, digests in auth['segments'].items()},
    'excluded_qlog_count': sum(len(x) for x in auth['excluded_sources'].values()),
    'raw_kind_allowlist': ['rlog.zst'], 'holdout_opening_allowed': False})
  outputs[FILES[3]] = p.seal({'schema': 'EMPIRICAL_CAUSAL_CONTEXT_SCHEMA_V2_EXECUTION_V1',
    'base_sha256': policy.INPUT_PINS['empirical-causal-context-schema-v2.json'],
    'execution_scope': 'ONLY_NEW_EXPLICITLY_AUTHORIZED_RETROSPECTIVE_GENERATION',
    'historical_regeneration': False, 'array_format': 'NUMPY_ALLOW_PICKLE_FALSE_C_ORDER_DTYPE_SHAPE_SHA256',
    'missing_encoding': 'EXPLICIT_AVAILABILITY_MASK_NAN_OR_NEGATIVE_INDEX_SENTINEL_EQUALS_NULL_NEVER_FALSE_ZERO',
    'actual_steering_rate_preserved': True, 'required_fields': list(execution.alignment.REQUIRED),
    'constant_row_identity': 'ROUTE_SEGMENT_SOURCE_PROFILE_CONFIG_POLICY_RECEIPTS_BOUND_BY_SEGMENT_MANIFEST',
    'variable_row_identity': ['segment_ordinal', 'aligned_row_index', 'route_global_row_index',
       'causal_run_id', 'within_causal_run_index', 'legacy_run_id', 'within_legacy_run_index', 'source_message_indices'],
    'source_timing_preserved_privately': True, 'snapshot_digest_per_row': True,
    'future_model_history': 'STRICT_PAST_SAME_ROUTE_SEGMENT_CAUSAL_RUN_ONLY_NO_MODEL_DESIGN_OR_TARGET_IN_THIS_DATASET',
    'unavailable_fields': policy.UNAVAILABLE})
  outputs[FILES[4]] = policy.read(store/'source-provenance.json')
  outputs[FILES[5]] = p.seal({'schema': 'EMPIRICAL_CAUSAL_COMMAND_STAGES_V1', 'routes': [
    {'route_id': r['route_id'], 'bridge': r['bridge'], 'request_output_order': r['request_output_order'],
     'source_age': r['source_age']} for r in routes],
    'request': 'CONTROLLER_REQUESTED_NORMALIZED_CARCONTROL_ACTUATORS_TORQUE',
    'post_controller': 'LOGGED_POST_CARCONTROLLER_NORMALIZED_CAROUTPUT_ACTUATORSOUTPUT_TORQUE',
    'raw_can_representation': 'LOGGED_RAW_CAROUTPUT_TORQUEOUTPUTCAN_NOT_TRANSMISSION_ACK',
    'physical_eps_application': None, 'linkage': 'REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE',
    'difference_name': 'PUBLISH_ALIGNED_REQUEST_OUTPUT_DIFFERENCE', 'limiter_cause': None})
  outputs[FILES[6]] = p.seal({'schema': 'EMPIRICAL_CAUSAL_ROUTE_COVERAGE_V1', 'routes': route_counts,
    'all_aligned_rows_preserved': True, 'source_rate_unit': 'DBC_UNIT_EMPTY_PHYSICAL_RATE_SEMANTICS_UNRESOLVED',
    'numeric_model_coverage_scoring': 'NOT_RUN', 'yaw_gyro_analysis': 'NOT_RUN'})
  outputs[FILES[7]] = p.seal(execution.mapping())
  outputs[FILES[8]] = p.seal({'schema': 'EMPIRICAL_CAUSAL_LEGACY_REPRODUCTION_V1',
    'status': 'LEGACY_ALIGNMENT_REPRODUCED' if exact_legacy else 'LEGACY_ALIGNMENT_REPRODUCTION_CONFLICT',
    'full_historical_segment_set_preserved': lineage_complete,
    'routes': [{'route_id': r['route_id'], 'checks': r['aggregate_legacy_checks'],
      'extracted_segment_count': r['segment_count'], 'historical_segment_count': r['historical_segment_count'],
      'per_extracted_segment_exact': r['per_segment_legacy_reproduction_exact'],
      'excluded_sources': r['excluded_sources']} for r in routes],
    'history': 45, 'minimum_support': 201, 'historical_results_rewritten': False,
    'scope': 'COUNT_AND_ALIGNMENT_ACCOUNTING_ONLY_NO_MODEL_FIT_OR_DESIGN_ARRAYS'})
  outputs[FILES[9]] = repeat
  if resume is not None:
    outputs[FILES[9]] = p.seal({**{k: v for k, v in repeat.items() if k != 'receipt_sha256'}, 'resume_receipt_sha256': resume['receipt_sha256']})
  counts = Counter()
  for r in routes:
    counts.update(r['coverage'])
  outputs[FILES[10]] = p.seal({'schema': 'EMPIRICAL_CAUSAL_TRAIN_DEV_READINESS_V1',
    'status': 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY' if ready else 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_BLOCKED',
    'dataset_manifest_sha256': manifest['receipt_sha256'], 'policy_sha256': private_policy['receipt_sha256'],
    'route_set_sha256': route_set['receipt_sha256'], 'authorization_sha256': auth['receipt_sha256'],
    'repeatability_sha256': outputs[FILES[9]]['receipt_sha256'], 'coverage_sha256': outputs[FILES[6]]['receipt_sha256'],
    'legacy_reproduction_sha256': outputs[FILES[8]]['receipt_sha256'],
    'route_count': len(routes), 'rlog_segment_count': sum(r['segment_count'] for r in routes),
    'excluded_qlog_count': sum(len(r['excluded_sources']) for r in route_set['routes']),
    'total_aligned_rows': counts['total_grid_samples'], 'field_extraction': 'CAUSAL_CONTEXT_V2_EXTRACTED_FOR_AUTHORIZED_RLOG_SUBSET',
    'actual_rate': 'ACTUAL_STEERING_RATE_PRESERVED', 'command_provenance': 'THREE_STAGE_COMMAND_PROVENANCE_READY_FOR_EXTRACTED_RLOG_SUBSET',
    'h1_mapping': 'H1_OBSERVABILITY_MAPPING_READY', 'model_fitting': 'MODEL_FITTING_NOT_RUN', 'model_selection': 'NOT_RUN',
    'blockers': [] if ready else ['HISTORICAL_QLOG_SEGMENTS_OUTSIDE_RAW_REOPENING_AUTHORIZATION',
                                'LEGACY_ALIGNMENT_REPRODUCTION_CONFLICT'],
    'historical_track': 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
    'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED', 'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0, 'reservation': 'NONE',
    'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED', 'no_model': 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
    'ta': 'TA_STANDALONE_TRADEOFF_ONLY', 'sg': 'SG_CLOSED_LOOP_TRADEOFF_ONLY',
    'composition': 'COMPOSITION_NOT_RECOMMENDED', 'composition_authority': 'COMPOSITION_NOT_AUTHORIZED',
    'search': 'SEARCH_NOT_AUTHORIZED', 'frozen_evaluation': 'FROZEN_EVALUATION_NOT_AUTHORIZED',
    'calibration_blockers': p.BLOCKERS, 'sealed_reference': 'NOT_GENERATED', 'vehicle': 'NOT_READY',
    'real_vehicle': 'REAL_VEHICLE_UNVERIFIED', 'vehicle_activation': 'VEHICLE_ACTIVATION_BLOCKED'})
  for name, row in outputs.items():
    validate_public(row)
    p.persist(p.PUBLIC/name, row)
  return outputs



def validate_chain(rows):
  if set(rows) != set(FILES):
    raise ValueError('EXACT_PUBLIC_DATASET_ARTIFACT_SET_REQUIRED')
  for row in rows.values():
    validate_public(row)
  pol, route_set, auth, repeat, ready = (rows[FILES[i]] for i in (0, 1, 2, 9, 10))
  if pol != policy.policy():
    raise ValueError('PUBLIC_EXECUTION_POLICY_DRIFT')
  links = {'policy_sha256': pol, 'route_set_sha256': route_set, 'coverage_sha256': rows[FILES[6]],
           'repeatability_sha256': repeat, 'legacy_reproduction_sha256': rows[FILES[8]]}
  if any(ready[key] != value['receipt_sha256'] for key, value in links.items()):
    raise ValueError('PUBLIC_DATASET_CHAIN_DRIFT')
  if (auth['private_authorization_sha256'] != ready['authorization_sha256']
      or auth['route_set_sha256'] != route_set['receipt_sha256'] or auth['policy_sha256'] != pol['receipt_sha256']
      or route_set['policy_sha256'] != pol['receipt_sha256']
      or auth['source_fingerprint_sha256'] != rows[FILES[4]]['source_fingerprint_sha256']
      or auth['numeric_adapter_sha256'] != pol['executor_sources']['reader']):
    raise ValueError('PUBLIC_AUTHORIZATION_SOURCE_CHAIN_DRIFT')
  if (repeat['dataset_manifest_sha256'] != ready['dataset_manifest_sha256'] or repeat['exact'] is not True
      or repeat['repeats'] != 2 or repeat['historical_store_trees_before'] != repeat['historical_store_trees_after']
      or repeat['raw_source_hashes_before_after_exact'] is not True):
    raise ValueError('PUBLIC_EXTRACTION_REPEATABILITY_DRIFT')
  expected_ids = [r['route_id'] for r in policy.resolve_routes()]
  if [r['route_id'] for r in route_set['routes']] != expected_ids or [r['route_id'] for r in rows[FILES[6]]['routes']] != expected_ids:
    raise ValueError('PUBLIC_EXACT_ROUTE_SET_DRIFT')
  if any(r['role'] != policy.ROLE or r['holdout_allowed'] is not False for r in route_set['routes']):
    raise ValueError('PUBLIC_EXPOSED_ROUTE_ROLE_DRIFT')
  excluded = sum(len(r['excluded_sources']) for r in route_set['routes'])
  segment_count = sum(r['segment_count'] for r in route_set['routes'])
  if (ready['excluded_qlog_count'] != excluded or auth['excluded_qlog_count'] != excluded
      or ready['rlog_segment_count'] != segment_count or repeat['extracted_segment_count'] != segment_count
      or ready['route_count'] != 2):
    raise ValueError('PUBLIC_EXTRACTION_COUNT_DRIFT')
  if excluded and (ready['status'] != 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_BLOCKED'
                   or rows[FILES[8]]['status'] != 'LEGACY_ALIGNMENT_REPRODUCTION_CONFLICT'):
    raise ValueError('PUBLIC_INCOMPLETE_LINEAGE_PROMOTION')
  if (ready['holdout'] != 'HOLDOUT_OPENING_CLOSED' or ready['opening_count'] != 0 or ready['reservation'] != 'NONE'
      or ready['model_selection'] != 'NOT_RUN' or ready['model_fitting'] != 'MODEL_FITTING_NOT_RUN'
      or ready['stage_b'] != 'STAGE_B_SIGNAL_ADMISSION_BLOCKED' or ready['calibration_blockers'] != p.BLOCKERS):
    raise ValueError('UNAUTHORIZED_DATASET_PROMOTION')
  return rows


PINS = {'empirical-causal-command-stages-v1.json': '251a7d82325773534a1f55e86edbd27b922d39d1f5086806515806bcb0cf3e10',
 'empirical-causal-context-schema-v2-execution-v1.json': '9992b4d67db40484acd642419b6a4cccb776bbc749ea29b0b5291c6969281b31',
 'empirical-causal-h1-mapping-v1.json': '0998cb9fbd072127d022a54c9417e5b6823864734f5e145309f6f3eaba74219e',
 'empirical-causal-legacy-reproduction-v1.json': 'b7b22ff622a094f0017b7945ccfdcc03274bab43dc912461730e5843a895ea70',
 'empirical-causal-numeric-authorization-v1.json': 'c16b154c4780d9d28199d7a502295dad0396cc48e5bbfc7017890910316c89d2',
 'empirical-causal-route-coverage-v1.json': 'd2f4166bd51ee9e134c5c8126aafe485cd92ee50e48a386f911a65f478c994e1',
 'empirical-causal-signal-provenance-v1.json': 'a9df216a7766b073f5fe55734e679fa3f4bbae029727b0d31227e9f7cde5a719',
 'empirical-causal-train-dev-policy-v1.json': '661d0dc9d5bdf79e70f69ef9aeb589314ef82fd0c845ac13d72ce208346182fb',
 'empirical-causal-train-dev-readiness-v1.json': 'bb70eee36c9b426e6d04ee4cceca0cd57cabeb8bee39e7736a7c43c37207fecf',
 'empirical-causal-train-dev-repeatability-v1.json': '51f525ed7b3b560b856fe62018471613935892554b0d86f8ebddb58400b886ad',
 'empirical-causal-train-dev-route-set-v1.json': 'e1b55f689677f46eabe96e4b0a0b3482543266a3abde3f680459dfaa78fd13d8'}


def load():
  rows = {n: validate_public(policy.read(p.PUBLIC/n)) for n in FILES}
  if any(rows[name]['receipt_sha256'] != digest for name, digest in PINS.items()) or set(PINS) != set(FILES):
    raise ValueError('PUBLIC_CAUSAL_DATASET_PIN_DRIFT')
  return validate_chain(rows)
