"""V2 TRAIN/DEV authority. Source audit is pinned input, never regenerated."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_signal_policy as yaw
from openpilot.tools.cyber_autotune import empirical_source_publication as old

BASELINE = 'cfeb0fc293c8f3fd66b904504a9c5c728e8a48af'
CODE = ('empirical_v2_policy.py', 'empirical_v2_signals.py', 'empirical_v2_execution.py',
        'empirical_v2_generation.py', 'empirical_plant_policy.py', 'empirical_plant_model.py',
        'empirical_plant_signals.py', 'empirical_signal_reader.py', 'empirical_signal_crosscheck.py',
        'empirical_signal_policy.py', 'empirical_source_execution.py', 'empirical_source_metadata.py',
        'empirical_cross_root_inventory.py', 'empirical_additional_root_policy.py',
        'empirical_dataset_v2_inventory.py', 'empirical_dataset_v2_policy.py')

# Exact opaque bindings derived from the pinned prior private metadata inventory;
# no numeric payload was consulted. These are not inferred from folder names.
ROUTE_BINDINGS = {
 '7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677': {
  'source_commit':'18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29',
  'lineage_sha256':'0ea78123869aa75c41fbd9e950fde9b4394d91619be3b476867a800475fef926',
  'source_set_sha256':'76a56097dc818d75f7c88d7deac3a2195be93f0fcdd4fac5f5da8abfd7eb4f11'},
 '962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c': {
  'source_commit':'18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29',
  'lineage_sha256':'6d4f6eba35e6e1b58821b11a652067984e7ef520d4ab2a5be4f01339fe48e85e',
  'source_set_sha256':'e899bb90190b32fe8a4cf3ad54dc7963a96aa29c7dedcca27010e31275bac5d1'},
 'eda13cbea550fc80f6153a1d9951fb7f06ce0bb2c6bfc462b7383751512cfe77': {
  'source_commit':'6ca11a4aea8223ebfebb1140bd8094ef1b3c5b90',
  'lineage_sha256':'f0bf29f467e3bff3c64ce7b35e1fa556c7649d7bcc4a6f14a0d677f8520a14fa',
  'source_set_sha256':'29b6db79f88dbb414fa0fe16cfc172cd04342894358195bf6244a90c275f380d'},
}

SIGNALS = {
  'initData': ['params.entries.CustomSteerMax', 'params.entries.CustomSteerDeltaUp', 'params.entries.CustomSteerDeltaDown',
               'params.entries.CustomSteerDeltaUpLC', 'params.entries.CustomSteerDeltaDownLC'],
  'carOutput': ['actuatorsOutput.torqueOutputCan', 'actuatorsOutput.torque'],
  'carControl': ['actuators.torque', 'latActive'],
  'carState': ['vEgo', 'steeringAngleDeg', 'steeringRateDeg', 'steeringPressed', 'steeringTorque',
               'steerFaultTemporary', 'steerFaultPermanent', 'gearShifter', 'yawRate', 'wheelSpeeds'],
  'gyroscope': ['source', 'timestamp', 'gyroUncalibrated.v'],
}


def code_identity():
  return {name: p.sha(Path(__file__).with_name(name).read_bytes()) for name in CODE}


def policy():
  return p.seal({
    'schema': 'EMPIRICAL_PLANT_V2_TRAIN_DEV_POLICY_V1', 'baseline': BASELINE,
    'role_order': ['TRAIN', 'TRAIN', 'DEVELOPMENT'], 'role_ordering': 'OPAQUE_ROUTE_ID_CANONICAL_LEXICAL',
    'minimum_development_rows': 201, 'data_policy': p.policy(), 'alignment_policy': p.alignment_policy(),
    'metric_policy': p.metric_policy(), 'family_policy': p.family_policy(), 'yaw_policy': yaw.policy(),
    'signal_whitelist': SIGNALS, 'stage_a_command': 'SOURCE_CONFIRMED_RAW_CAN_POST_CONTROLLER',
    'yaw_additional_admission': 'EACH_ROUTE_POSITIVE_GYRO_AND_KINEMATIC_CORRELATION_AND_SELECTED_YAW_BEATS_ZERO_GYRO_RMSE_MAE_P95',
    'gyro_weak_association': 'DO_NOT_ADMIT_FROM_KINEMATIC_ONLY',
    'stage_c': 'NOT_RUN', 'holdout_opening_allowed': False, 'holdout_role': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
    'numeric_routes': 3, 'exact_metadata_route_bindings': ROUTE_BINDINGS, 'deduplication': 'ONE_STREAM_PER_ENVELOPE_SEGMENT_RLOG_BEFORE_QLOG_HASH_LEXICAL',
    'runtime_steer_max': 'RECORDED_CUSTOMSTEERMAX_METADATA_PLUS_SOURCE_BRANCH_NO_SCALE_SEARCH',
    'source_age_ns': 20_000_000,
    'break_accounting':'CONTIGUOUS_INVALID_REASON_INTERVAL_STARTS_INCLUDING_INITIAL_SEPARATE_FROM_MASKED_SAMPLE_COUNTS',
    'segment_accounting':'SEGMENT_RESET_COUNT_AND_ROUTE_SEGMENT_BOUNDARIES_SEPARATE',
    'privacy': 'PRIVATE_TRACES_COEFFICIENTS_PATHS_TIMESTAMPS_PUBLIC_AGGREGATES_ONLY',
    'solver': 'NUMPY_LSTSQ_RCOND_NONE_FLOAT64_SINGLE_THREAD_BLAS', 'randomness': 'NONE',
    'calibration_blockers': p.BLOCKERS,
  })


def split(public, bindings):
  for name, row in public.items():
    p.verify(row)
    if row['receipt_sha256'] != old.PINS[name]:
      raise ValueError('EXACT_SOURCE_AUDIT_INPUT_REQUIRED')
  reclass = public['empirical-source-route-reclassification-v1.json']
  pools = reclass['pools']['pools']
  if len(pools) != 1 or len(pools[0]['route_ids']) != 3 or set(bindings) != set(pools[0]['route_ids']):
    raise ValueError('EXACT_THREE_ADMITTED_ROUTES_ONLY')
  pool = pools[0]
  if bindings != ROUTE_BINDINGS:
    raise ValueError('EXACT_PRIOR_METADATA_ROUTE_BINDINGS_REQUIRED')
  classes = public['empirical-source-equivalence-classes-v1.json']
  cl = next(c for c in classes['classes'] if c['class_id'] == pool['semantic_class_id'])
  if cl['status'] != 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENT':
    raise ValueError('NO_PARTIAL_SOURCE_CLASS')
  routes = []
  for rid, role in zip(sorted(pool['route_ids']), policy()['role_order'], strict=True):
    row = next(x for x in reclass['routes'] if x['route_id'] == rid)
    binding = bindings[rid]
    if (row['classification'] != 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE'
        or not row['signal_semantics_complete'] or not row['profile_complete'] or row['v1_overlap']
        or row['full_carparams_sha256'] != pool['full_carparams_sha256']
        or binding['source_commit'] not in cl['members']):
      raise ValueError('EXACT_COMPLETE_NONDUPLICATE_POOL_REQUIRED')
    adapter = reclass['execution_binding']['adapters'][binding['source_commit']]
    routes.append({
      'route_id': rid, 'role': role, 'source_commit': binding['source_commit'],
      'adapter_sha256': adapter['receipt_sha256'], 'metadata_adapter_source_sha256': adapter['adapter_source_sha256'],
      'source_fingerprint_sha256': adapter['source_fingerprint_sha256'],
      'lineage_sha256': binding['lineage_sha256'], 'source_set_sha256': binding['source_set_sha256'],
      'full_carparams_sha256': pool['full_carparams_sha256'], 'empirical_profile_sha256': pool['empirical_profile_sha256'],
      'semantic_class_id': pool['semantic_class_id'], 'prior_analysis': row['prior_analysis'],
    })
  result = p.seal({'schema': 'EMPIRICAL_PLANT_V2_TRAIN_DEV_SPLIT_V1', 'routes': routes,
    'source_equivalence_sha256': classes['receipt_sha256'],
    'source_route_input_sha256': reclass['receipt_sha256'], 'role_policy_sha256': policy()['receipt_sha256'],
    'numeric_opened_before_split': False, 'holdout_allowed': False, 'v1_used': False})
  validate_split(result)
  return result


def validate_split(row):
  p.verify(row)
  routes = row['routes']
  if (len(routes) != 3 or [x['role'] for x in routes] != ['TRAIN', 'TRAIN', 'DEVELOPMENT']
      or [x['route_id'] for x in routes] != sorted({x['route_id'] for x in routes})
      or len({x['full_carparams_sha256'] for x in routes}) != 1
      or row.get('numeric_opened_before_split') is not False or row.get('holdout_allowed') is not False
      or row['role_policy_sha256'] != policy()['receipt_sha256']):
    raise ValueError('IMMUTABLE_LEXICAL_TWO_TRAIN_ONE_DEVELOPMENT')
  public=old.load()
  reclass=public['empirical-source-route-reclassification-v1.json']
  pool=reclass['pools']['pools'][0]
  if {x['route_id'] for x in routes}!=set(pool['route_ids']):
    raise ValueError('ONLY_PINNED_ADMITTED_ROUTE_IDS')
  for route in routes:
    expected=ROUTE_BINDINGS[route['route_id']]
    binding=reclass['execution_binding']['adapters'][expected['source_commit']]
    if (any(route[k]!=val for k,val in expected.items())
        or route['full_carparams_sha256']!=pool['full_carparams_sha256']
        or route['empirical_profile_sha256']!=pool['empirical_profile_sha256']
        or route['semantic_class_id']!=pool['semantic_class_id']
        or route['adapter_sha256']!=binding['receipt_sha256']
        or route['metadata_adapter_source_sha256']!=binding['adapter_source_sha256']
        or route['source_fingerprint_sha256']!=binding['source_fingerprint_sha256']
        or route['prior_analysis']!='ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN'):
      raise ValueError('PINNED_ADMITTED_METADATA_IDENTITY_REQUIRED')
  if (row['source_equivalence_sha256']!=public['empirical-source-equivalence-classes-v1.json']['receipt_sha256']
      or row['source_route_input_sha256']!=reclass['receipt_sha256']):
    raise ValueError('SOURCE_AUDIT_INPUT_DRIFT')
  return row


def authorization(split_receipt, sources):
  validate_split(split_receipt)
  if set(sources) != {x['route_id'] for x in split_receipt['routes']}:
    raise ValueError('EXACT_AUTHORIZED_ROUTE_SET')
  for row in split_receipt['routes']:
    if row['source_set_sha256'] != p.sha(p.canonical(sorted(sources[row['route_id']]))):
      raise ValueError('EXACT_ROUTE_SOURCE_SET_REQUIRED')
  return p.seal({'schema': 'EMPIRICAL_PLANT_V2_NUMERIC_AUTHORIZATION_V1',
    'split_sha256': split_receipt['receipt_sha256'], 'route_set_sha256': p.sha(p.canonical(sorted(sources))),
    'sources': sources, 'adapters': {r['route_id']: r['adapter_sha256'] for r in split_receipt['routes']},
    'policy': policy(), 'code_sha256': code_identity(), 'signal_whitelist': SIGNALS,
    'source_sha256': {r['route_id']: r['source_fingerprint_sha256'] for r in split_receipt['routes']},
    'execution_source_sha256': code_identity()['empirical_v2_execution.py'],
    'holdout_opening_allowed': False})


def require_open(store, route_id, source_sha, adapter_sha):
  store = Path(store)
  frozen = validate_split(p.verify(json.loads((store / 'split.json').read_bytes())))
  auth = p.verify(json.loads((store / 'authorization.json').read_bytes()))
  if (auth['split_sha256'] != frozen['receipt_sha256'] or auth['policy'] != policy()
      or auth['code_sha256'] != code_identity() or auth['signal_whitelist'] != SIGNALS
      or auth['holdout_opening_allowed'] is not False):
    raise ValueError('NUMERIC_AUTHORIZATION_DRIFT')
  expected_auth=authorization(frozen,auth['sources'])
  if auth!=expected_auth:
    raise ValueError('EXACT_AUTHORIZATION_SOURCE_SET_REQUIRED')
  route = next((r for r in frozen['routes'] if r['route_id'] == route_id), None)
  if (route is None or source_sha not in auth['sources'].get(route_id, ())
      or adapter_sha != route['adapter_sha256'] or auth['adapters'][route_id] != adapter_sha):
    raise ValueError('UNAUTHORIZED_ROUTE_SOURCE_OR_ADAPTER')
  return route, auth


def holdout_package(frozen, models, freeze_sha):
  validate_split(frozen)
  public = old.load()
  return p.seal({'schema': 'FUTURE_EMPIRICAL_PLANT_V2_HOLDOUT_EVALUATION_V1',
    'split_sha256': frozen['receipt_sha256'], 'model_freeze_sha256': freeze_sha, 'models': models,
    'source_equivalence_sha256': frozen['source_equivalence_sha256'],
    'empirical_profile_sha256': frozen['routes'][0]['empirical_profile_sha256'],
    'full_carparams_sha256': frozen['routes'][0]['full_carparams_sha256'],
    'command_yaw_policy_sha256': policy()['receipt_sha256'], 'metric_policy_sha256': p.metric_policy()['receipt_sha256'],
    'support_minimum': 201, 'holdout_admission_sha256': public['future-empirical-holdout-admission-v1.json']['receipt_sha256'],
    'one_time_opening_state': 'CLOSED', 'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
    'reselection_allowed': False, 'refit_allowed': False, 'threshold_change_allowed': False,
    'old_routes_holdout_allowed': False, 'evaluation_execution_authorized': False})
