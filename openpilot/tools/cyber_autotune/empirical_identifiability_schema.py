"""Exact aggregate schemas. Unknown fields and contradictory execution claims fail."""
import math
import re
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_identifiability_math as numeric

NUMBER = (int, float, type(None))
COUNT = int


def shape(value, spec):
  if isinstance(spec, dict):
    if type(value) is not dict or set(value) != set(spec):
      raise ValueError('EXACT_AGGREGATE_KEYS_REQUIRED')
    for key, child in spec.items():
      shape(value[key], child)
  elif isinstance(spec, list):
    if type(value) is not list:
      raise ValueError('AGGREGATE_LIST_REQUIRED')
    for child in value:
      shape(child, spec[0])
  elif isinstance(spec, tuple):
    if type(value) not in spec or (type(value) is float and not math.isfinite(value)):
      raise ValueError('FINITE_NULLABLE_AGGREGATE_NUMBER_REQUIRED')
  elif isinstance(spec, type):
    if type(value) is not spec or (spec is int and value < 0):
      raise ValueError('EXACT_AGGREGATE_TYPE_REQUIRED')
  elif type(value) is not type(spec) or value != spec:
    raise ValueError('AGGREGATE_ENUM_CONFLICT')


def body(row, schema):
  p.verify(row)
  privacy(row)
  if row.get('schema') != schema:
    raise ValueError('EXACT_RESULT_SCHEMA_REQUIRED')
  return {k: v for k, v in row.items() if k not in {*p.FIREWALL, 'receipt_sha256', 'schema'}}


def vector(value, length):
  shape(value, [NUMBER])
  if len(value) != length or any(v is None for v in value):
    raise ValueError('EXACT_AGGREGATE_VECTOR_LENGTH_REQUIRED')


SPEED = dict.fromkeys(('LOW', 'MEDIUM', 'HIGH'), COUNT)
TARGET = dict.fromkeys(('count', 'zero', 'positive', 'negative', 'unique_float_delta_levels', 'unique_source_grid_delta_codes'), COUNT)
TARGET['usage'] = 'TARGET_AVAILABILITY_AND_EXCITATION_ONLY_NO_INPUT_RANK_OR_FEATURE_SELECTION'
RATE = {
  'status': 'EMPIRICAL_DIAGNOSTIC_ONLY_NOT_SOURCE_SEMANTIC_PROOF', 'source_semantics_promotable': False,
  'count': COUNT, 'rate_at': 'LATER_ADJACENT_STATE_SOURCE_TIME',
  'finite_difference_timebase': 'STRICTLY_POSITIVE_SELECTED_STATE_TIMESTAMP_DIFFERENCE',
  **dict.fromkeys(('rate_min', 'rate_max', 'correlation_signed_fd', 'correlation_absolute_fd'), NUMBER),
  **dict.fromkeys(('rate_negative', 'rate_zero', 'rate_positive', 'fd_negative', 'fd_zero', 'fd_positive', 'ratio_count',
                  'zero_rate_unchanged_angle', 'zero_rate_changed_angle', 'nonzero_rate_unchanged_angle', 'nonzero_rate_changed_angle'), COUNT),
  'rate_over_absolute_fd_quantiles_0_50_95_100': object}
EXCITATION = {
  'base_rows': COUNT, 'guard_admitted_rows': COUNT, 'adjacent_pairs': COUNT,
  'command': dict.fromkeys(('finite', 'unique_raw_levels', 'unique_normalized_levels', 'request_finite', 'zero_count',
                            'positive', 'negative', 'rail_count', 'transition_count', 'reversal_count'), COUNT),
  'angle': {**dict.fromkeys(('finite', 'unique_float_levels', 'unique_source_grid_codes', 'float32_source_grid_compliant',
                            'unchanged_adjacent_count', 'positive_delta', 'negative_delta'), COUNT),
            'unchanged_adjacent_fraction': NUMBER},
  'rate_native': {**dict.fromkeys(('finite', 'unique_levels', 'zero_count', 'nonzero_count', 'negative_count', 'positive_count'), COUNT),
                  'zero_fraction': NUMBER},
  'speed': {'bins': SPEED, 'unique_levels': COUNT, 'quantiles_0_50_95_100_mps': object},
  'delta_angle': TARGET, 'rate_diagnostic': RATE, 'target_by_speed': dict.fromkeys(SPEED, TARGET)}
COVERAGE = {
  'segments': COUNT,
  'fields': dict.fromkeys(('control.requested', 'command.normalized', 'command.raw', 'state.angle_deg', 'state.rate',
                          'state.speed_mps', 'control.lat_active', 'state.driver_pressed', 'state.driver_torque', 'state.eps_fault'), COUNT),
  'context': dict.fromkeys(('active_rising', 'active_falling', 'pressed_rising', 'pressed_falling', 'run_boundary',
                           'segment_boundary', 'active', 'inactive', 'steering_pressed', 'eps_fault'), COUNT),
  'snapshot_set_sha256': str}
HISTORY = {'history': COUNT, 'eligible_windows': COUNT, 'next_state_available': COUNT, 'causal_runs_contributing': COUNT,
  'admitted_streaks_contributing': COUNT, 'segments_contributing': COUNT, 'usable_run_lengths_min_median_max': object,
  'windows_per_usable_run_min_median_max': object, 'speed_bins_at_window_endpoint': SPEED, 'minimum_route_support_pass': bool}


def nullable_vector(value, n):
  if value is not None:
    vector(value, n)


def aggregate_shape(value, spec):
  """Object slots are only fixed-length nullable aggregate vectors checked below."""
  if spec is object:
    if value is not None:
      shape(value, [NUMBER])
  elif isinstance(spec, list):
    if type(value) is not list:
      raise ValueError('AGGREGATE_LIST_REQUIRED')
    for item in value:
      aggregate_shape(item, spec[0])
  elif isinstance(spec, dict):
    if type(value) is not dict or set(value) != set(spec):
      raise ValueError('EXACT_AGGREGATE_KEYS_REQUIRED')
    for k in spec:
      aggregate_shape(value[k], spec[k])
  else:
    shape(value, spec)


def excitation_scopes(scopes, ids):
  aggregate_shape(scopes, dict.fromkeys([*ids, 'POOLED'], EXCITATION))
  for row in scopes.values():
    n, pairs = row['guard_admitted_rows'], row['adjacent_pairs']
    if n > row['base_rows'] or pairs > n or row['delta_angle']['count'] != pairs or row['rate_diagnostic']['count'] != pairs:
      raise ValueError('SUPPORT_ACCOUNTING_CONFLICT')
    for name in ('command', 'angle', 'rate_native'):
      if row[name]['finite'] != n:
        raise ValueError('FINITE_FEATURE_COVERAGE_CONFLICT')
    nullable_vector(row['speed']['quantiles_0_50_95_100_mps'], 4)
    nullable_vector(row['rate_diagnostic']['rate_over_absolute_fd_quantiles_0_50_95_100'], 4)
    for target in [row['delta_angle'], *row['target_by_speed'].values()]:
      if target['zero']+target['positive']+target['negative'] != target['count']:
        raise ValueError('TARGET_AVAILABILITY_ACCOUNTING_CONFLICT')
  for field in ('base_rows', 'guard_admitted_rows', 'adjacent_pairs'):
    if scopes['POOLED'][field] != sum(scopes[r][field] for r in ids):
      raise ValueError('POOLED_SUPPORT_RECONCILIATION_CONFLICT')


def history_scopes(scopes, ids):
  aggregate_shape(scopes, dict.fromkeys([*ids, 'POOLED'], [HISTORY]))
  for rows in scopes.values():
    if [r['history'] for r in rows] != list(numeric.HISTORIES):
      raise ValueError('COMPLETE_HISTORY_ENVELOPE_REQUIRED')
    for row in rows:
      nullable_vector(row['usable_run_lengths_min_median_max'], 3)
      nullable_vector(row['windows_per_usable_run_min_median_max'], 3)
      if row['next_state_available'] > row['eligible_windows'] or row['minimum_route_support_pass'] != (row['eligible_windows'] >= 201):
        raise ValueError('HISTORY_SUPPORT_GATE_CONFLICT')
  for i in range(45):
    for key in ('eligible_windows', 'next_state_available', 'causal_runs_contributing', 'admitted_streaks_contributing', 'segments_contributing'):
      if scopes['POOLED'][i][key] != sum(scopes[r][i][key] for r in ids):
        raise ValueError('POOLED_HISTORY_RECONCILIATION_CONFLICT')


def rank_scope(row, names):
  base = {'rows': COUNT, 'columns': len(names), 'feature_names': [str], 'fitting_admission': False,
    'conditioning_status': 'CONDITION_NUMBER_REPORTED_NO_ACCEPTANCE_THRESHOLD',
    'rank_meaning': 'NUMERICAL_RANK_NOT_SYMBOLIC_STRUCTURAL_IDENTIFIABILITY_PROOF',
    'numerical_rank': NUMBER, 'singular_values': [NUMBER], 'condition_number': NUMBER, 'status': str,
    'constant_columns': [str], 'duplicate_columns': [[str]], 'next_state_available': COUNT,
    'speed_bins_at_feature_endpoint': SPEED, 'feature_order_sha256': p.sha(p.canonical(names))}
  if row.get('rows', 0):
    base.update({'numpy_default_tolerance': NUMBER, 'condition_undefined_reason': (str, type(None)),
      'population_feature_variances': [NUMBER], 'standardized_input_second_moment_sha256': str,
      'input_correlation_pair_count': COUNT, 'max_absolute_input_correlation': NUMBER, 'max_correlation_features': (list, type(None)),
      'constant_correlation': 'UNDEFINED_NOT_ZERO_FILLED'})
  aggregate_shape(row, base)
  if row['feature_names'] != names or row['next_state_available'] > row['rows']:
    raise ValueError('EXACT_FEATURE_LAYOUT_AND_TARGET_AVAILABILITY_REQUIRED')
  if not row['rows']:
    if row['numerical_rank'] is not None or row['singular_values'] or row['status'] != 'NO_ADMITTED_FEATURE_ROWS':
      raise ValueError('EMPTY_RANK_CANNOT_PASS')
    return
  if type(row['numerical_rank']) is not int or not 0 <= row['numerical_rank'] <= min(row['rows'], len(names)):
    raise ValueError('NUMERICAL_RANK_DIMENSION_CONFLICT')
  vector(row['singular_values'], min(row['rows'], len(names)))
  vector(row['population_feature_variances'], len(names))
  import numpy as np
  expected_tolerance = row['singular_values'][0]*max(row['rows'], len(names))*np.finfo(np.float64).eps
  if (row['numpy_default_tolerance'] != expected_tolerance
      or row['numerical_rank'] != sum(v > expected_tolerance for v in row['singular_values'])):
    raise ValueError('NUMPY_RANK_TOLERANCE_CONFLICT')
  expected = 'FULL_RANK_DIAGNOSTIC' if row['numerical_rank'] == len(names) else 'RANK_DEFICIENT'
  if row['status'] != expected or any(x not in names for x in row['constant_columns']):
    raise ValueError('RANK_STATUS_OR_CONSTANT_COLUMN_CONFLICT')
  for pair in row['duplicate_columns']:
    if len(pair) != 2 or any(n not in names for n in pair):
      raise ValueError('EXACT_DUPLICATE_FEATURE_PAIR_REQUIRED')
  if row['condition_undefined_reason'] != ('ZERO_SMALLEST_SINGULAR_VALUE_OR_NONFINITE_RATIO' if row['condition_number'] is None else None):
    raise ValueError('EXACT_CONDITION_UNAVAILABLE_REASON_REQUIRED')
  pair = row['max_correlation_features']
  if pair is not None and (len(pair) != 2 or any(n not in names for n in pair)):
    raise ValueError('INPUT_CORRELATION_FEATURE_PAIR_REQUIRED')


def forms(rows, family, ids):
  envelope = numeric.LAGS if family == 'S1' else numeric.HISTORIES
  parameter = 'lag' if family == 'S1' else 'history'
  if type(rows) is not list or [r.get(parameter) for r in rows] != list(envelope):
    raise ValueError('COMPLETE_PREDECLARED_FORMS_REQUIRED')
  for row in rows:
    if set(row) != {parameter, 'scopes', 'both_routes_next_state_support_at_least_201'} or set(row['scopes']) != {*ids, 'POOLED'}:
      raise ValueError('EXACT_ROUTE_AND_POOLED_FORM_SCOPES_REQUIRED')
    value = row[parameter]
    names = (['angle_k', 'rate_native_k', f'command_lag_{value}', 'speed_k', 'intercept'] if family == 'S1' else
             [f'{key}_lag_{offset}' for key in ('command', 'angle') for offset in range(value-1, -1, -1)]+['rate_native_k', 'speed_k'])
    for scope in row['scopes'].values():
      rank_scope(scope, names)
    support = [row['scopes'][r]['next_state_available'] for r in ids]
    if row['both_routes_next_state_support_at_least_201'] != numeric.support_gate(support):
      raise ValueError('BOTH_ROUTE_SUPPORT_GATE_CONFLICT')
    for key in ('rows', 'next_state_available'):
      if row['scopes']['POOLED'][key] != sum(row['scopes'][r][key] for r in ids):
        raise ValueError('POOLED_FORM_SUPPORT_CONFLICT')


def result(value, pol, source, admission):
  b = body(value, 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_RESULTS_V1')
  expected = {'policy_sha256', 'admission_sha256', 'source_contract_sha256', 'coverage', 'excitation',
              'history_support', 'families', 'historical_inputs_byte_identical', 'qlog_arrays_opened', 'raw_logs_opened', 'authority'}
  if (set(b) != expected or b['policy_sha256'] != pol['receipt_sha256'] or b['source_contract_sha256'] != source['receipt_sha256']
      or b['authority'] != pol['authority'] or any(v is not False for v in b['authority'].values()) or b['historical_inputs_byte_identical'] is not True
      or type(b['qlog_arrays_opened']) is not int or b['qlog_arrays_opened'] != 0
      or type(b['raw_logs_opened']) is not int or b['raw_logs_opened'] != 0):
    raise ValueError('EXACT_COMPLETE_UNMODIFIED_NO_MODEL_EXECUTION_REQUIRED')
  ids = pol['route_ids']
  aggregate_shape(b['coverage'], dict.fromkeys(ids, COVERAGE))
  excitation_scopes(b['excitation'], ids)
  history_scopes(b['history_support'], ids)
  if set(b['families']) != {'S1', 'S2'}:
    raise ValueError('EXACT_S1_S2_ONLY')
  for family in ('S1', 'S2'):
    forms(b['families'][family], family, ids)
  a = body(admission, 'EMPIRICAL_IDENTIFIABILITY_INPUT_ADMISSION_V1')
  if (set(a) != {'policy_sha256', 'manifest_sha256', 'source_contract_sha256', 'segment_receipts',
                 'input_file_set_sha256', 'array_access_before_admission'}
      or a['policy_sha256'] != pol['receipt_sha256'] or a['manifest_sha256'] != pol['resolution']['rlog_dataset_manifest_sha256']
      or a['source_contract_sha256'] != source['receipt_sha256'] or a['array_access_before_admission'] is not False
      or b['admission_sha256'] != admission['receipt_sha256'] or len(a['segment_receipts']) != 154
      or len(set(a['segment_receipts'])) != 154 or b['excitation']['POOLED']['base_rows'] != 916535
      or sum(c['segments'] for c in b['coverage'].values()) != 154):
    raise ValueError('EXACT_154_SEGMENT_ADMISSION_CHAIN_REQUIRED')


def public(value):
  from openpilot.tools.cyber_autotune import empirical_identifiability_policy as policy
  pol = policy.policy()
  source = policy.source_contract()
  name = value.get('schema')
  b = body(value, name)
  ids = pol['route_ids']
  if name == pol['schema']:
    if value != pol:
      raise ValueError('EXACT_POLICY_REQUIRED')
  elif name == source['schema']:
    policy.validate_source(value)
  elif name == 'EMPIRICAL_S3_SOURCE_MECHANISM_V1':
    if b != {'source_contract_sha256': source['receipt_sha256'], **source['s3']}:
      raise ValueError('EXACT_SOURCE_MECHANISM_REQUIRED')
  elif name == 'EMPIRICAL_IDENTIFIABILITY_LEAKAGE_RESET_CONTRACT_V1':
    if value != policy.leakage_reset():
      raise ValueError('EXACT_RESET_CONTRACT_REQUIRED')
  elif name == 'EMPIRICAL_IDENTIFIABILITY_EXCITATION_V1':
    if set(b) != {'policy_sha256', 'coverage', 'scopes'} or b['policy_sha256'] != pol['receipt_sha256']:
      raise ValueError('EXACT_EXCITATION_REQUIRED')
    aggregate_shape(b['coverage'], dict.fromkeys(ids, COVERAGE))
    excitation_scopes(b['scopes'], ids)
  elif name == 'EMPIRICAL_IDENTIFIABILITY_HISTORY_SUPPORT_V1':
    shape({k: v for k, v in b.items() if k != 'scopes'},
          {'policy_sha256': pol['receipt_sha256'], 'selected_history': None, 'threshold': 201,
           'threshold_meaning': 'ROUTE_DEVELOPMENT_AVAILABILITY_NOT_MODEL_ACCEPTANCE'})
    history_scopes(b['scopes'], ids)
  elif name in ('EMPIRICAL_S1_STRUCTURAL_DIAGNOSTICS_V1', 'EMPIRICAL_S2_STRUCTURAL_DIAGNOSTICS_V1'):
    shape({k: v for k, v in b.items() if k != 'forms'}, {'policy_sha256': pol['receipt_sha256'],
      'source_contract_sha256': source['receipt_sha256'], 'selected_form': None, 'target_fitting': 'NOT_RUN',
      'physical_rate_semantics': 'SOURCE_SEMANTICS_BLOCKED'})
    forms(b['forms'], name.split('_')[1], ids)
  elif name == 'EMPIRICAL_IDENTIFIABILITY_REPEATABILITY_V1':
    shape(b, {'executions': 2, 'exact': True, 'policy_sha256': pol['receipt_sha256'], 'result_sha256': str,
      'readiness_sha256': str, 'historical_inputs_byte_identical': True, 'array_read_only': True,
      'raw_logs_opened': 0, 'qlog_arrays_opened': 0, 'receipt_and_aggregate_bytes_exact': True, 'model_operations': 'NOT_RUN'})
  elif name == 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_READINESS_V1':
    from openpilot.tools.cyber_autotune.empirical_identifiability_publication import INPUT_NAMES
    shape(b, {
      'status': 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_AUDIT_COMPLETE', 'inputs': dict.fromkeys(INPUT_NAMES, str),
      'dataset_completeness': pol['resolution']['final_dataset_status'], 'legacy_reproduction': 'PASS',
      'qlog_reconciliation': 'COMPLETE', 'rlog_stream_count': 154, 'qlog_support': 0, 'qlog_arrays_opened': 0,
      'family_states': {'S1': str, 'S2': str, 'S3': 'S3_SOURCE_MECHANISM_BLOCKED'},
      'rate_contract': source['rate']['contract'], 'signed_physical_rate_proven': False,
      'both_routes_support_for_all_forms': {'S1': bool, 'S2': bool}, 'symbolic_identifiability_established': False,
      'fitting_admission': False, 'closed_loop_bias': 'CLOSED_LOOP_IDENTIFICATION_BIAS_RISK',
      'transaction': pol['transaction'], 'physical_eps': pol['physical_eps'], 'authority': policy.AUTHORITY,
      'model_fitting': 'NOT_RUN', 'model_selection': 'NOT_RUN', 'cv_scoring': 'NOT_RUN', 'family_selected': None,
      'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0, 'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED', 'historical_track': 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
      'ta': 'TA_STANDALONE_TRADEOFF_ONLY', 'sg': 'SG_CLOSED_LOOP_TRADEOFF_ONLY',
      'composition': [str],
      'calibration_blockers': [str], 'sealed_reference': 'NOT_GENERATED',
      'vehicle': [str]})
    if any(not re.fullmatch('[0-9a-f]{64}', v) for v in b['inputs'].values()):
      raise ValueError('EXACT_INPUT_RECEIPT_DIGEST_REQUIRED')
    if b['composition'] != ['COMPOSITION_NOT_RECOMMENDED', 'COMPOSITION_NOT_AUTHORIZED'] or b['calibration_blockers'] != p.BLOCKERS:
      raise ValueError('EXACT_HISTORICAL_BLOCKERS_REQUIRED')
    if b['vehicle'] != ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED']:
      raise ValueError('NO_VEHICLE_AUTHORITY')
    for family in ('S1', 'S2'):
      supported = b['both_routes_support_for_all_forms'][family]
      state = ('S1_NUMERIC_STRUCTURE_AVAILABLE_BUT_RATE_SEMANTICS_BLOCKED' if family == 'S1' else
               'S2_STRUCTURAL_SUPPORT_PRESENT_RATE_SEMANTICS_BLOCKED') if supported else family+'_SUPPORT_INSUFFICIENT_RATE_SEMANTICS_BLOCKED'
      if b['family_states'][family] != state:
        raise ValueError('SUPPORT_CLAIM_CONFLICT')
  else:
    raise ValueError('UNKNOWN_PUBLIC_SCHEMA')



def privacy(value, key=''):
  if isinstance(value, dict):
    for k, v in value.items():
      privacy(v, k)
  elif isinstance(value, list):
    for v in value:
      privacy(v, key)
  elif isinstance(value, str):
    if value.startswith(('/', '\\\\')) or re.match(r'^[A-Za-z]:[\\\\/]', value):
      raise ValueError('PRIVATE_PATH_NOT_PUBLISHABLE')
    if key.endswith('sha256') and not re.fullmatch('[0-9a-f]{64}', value):
      raise ValueError('EXACT_SHA256_REQUIRED')
