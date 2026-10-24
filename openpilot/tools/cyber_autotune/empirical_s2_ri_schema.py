"""Closed aggregate result schemas; no extensible bag of private values."""
import re
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_identifiability_schema as s
from openpilot.tools.cyber_autotune import empirical_s2_ri_policy as policy
from openpilot.tools.cyber_autotune import empirical_s2_ri_math as m
from openpilot.tools.cyber_autotune import empirical_s2_ri_admission as admission

COUNT_KEYS = ('base_rows', 'causal_valid_rows', 'model_eligible_rows', 'grid_compliant_rows', 'grid_inconsistent_available_rows',
              'segments', 'causal_runs', 'excluded_pressed_rows', 'excluded_inactive_rows', 'excluded_fault_rows',
              'release_count', 'reengagement_count')
SUPPORT = {**dict.fromkeys(('eligible_rows', 'target_available_rows', 'target_zero_count', 'target_positive_count',
  'target_negative_count', 'unique_delta_level_count', 'contributing_segments', 'contributing_causal_runs', 'longest_eligible_history'), int),
  'target_zero_fraction': s.NUMBER, 'eligible_speed_bins': s.SPEED, 'target_speed_bins': s.SPEED,
  'history_support_L1_to_L45': [int]}


def digest(value):
  if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
    raise ValueError('OPAQUE_SHA256_REQUIRED')


def validate_result(value, pol, receipt):
  b = s.body(value, 'EMPIRICAL_S2_RI_AUDIT_RESULTS_V1')
  expected = {'policy_sha256', 'admission_sha256', 'derived_receipt_set_sha256', 'stream_count', 'counts', 'support', 'forms',
    'rate_dependency', 'request_dependency', 'rate_views', 'generic_id_and_snapshot_overlays',
    'adversarial_derived_arrays_and_X_bytes_exact', 'adversarial_rank_executions_per_form', 'input_bytes_unchanged',
    'qlog_arrays_opened', 'raw_logs_opened', 'authority'}
  if set(b) != expected:
    raise ValueError('EXACT_COMPLETE_S2_RI_RESULT_REQUIRED')
  ids = pol['route_ids']
  if (b['policy_sha256'] != pol['receipt_sha256'] or b['admission_sha256'] != receipt['receipt_sha256']
      or b['authority'] != policy.AUTHORITY or any(v is not False for v in b['authority'].values())):
    raise ValueError('EXECUTOR_ADMISSION_AUTHORITY_CONFLICT')
  for k in ('policy_sha256', 'admission_sha256', 'derived_receipt_set_sha256'):
    digest(b[k])
  for k in ('qlog_arrays_opened', 'raw_logs_opened'):
    if type(b[k]) is not int or b[k] != 0:
      raise ValueError('NO_RAW_OR_QLOG_ACCESS')
  if (b['rate_dependency'] != 'NONE' or b['request_dependency'] != 'NONE'
      or b['rate_views'] != ['ORIGINAL', 'DELETED', 'ALL_NAN_UNAVAILABLE', 'ARBITRARY_FINITE_AVAILABLE']
      or b['generic_id_and_snapshot_overlays'] != 'EXACT_INVARIANT_NOT_GATES'
      or b['adversarial_derived_arrays_and_X_bytes_exact'] is not True or b['input_bytes_unchanged'] is not True
      or type(b['adversarial_rank_executions_per_form']) is not int or b['adversarial_rank_executions_per_form'] != 3
      or type(b['stream_count']) is not int or b['stream_count'] != 154):
    raise ValueError('EXACT_IMMUTABLE_RATE_FREE_154_STREAM_EXECUTION_REQUIRED')
  a = s.body(receipt, 'EMPIRICAL_S2_RI_INPUT_ADMISSION_V1')
  if (set(a) != {'policy_sha256', 'manifest_sha256', 'segment_receipts', 'segment_bindings', 'input_file_set_sha256', 'array_access_before_admission'}
      or a['policy_sha256'] != pol['receipt_sha256']
      or a['manifest_sha256'] != pol['resolution']['rlog_dataset_manifest_sha256']
      or a['array_access_before_admission'] is not False
      or len(a['segment_receipts']) != 154 or len(set(a['segment_receipts'])) != 154):
    raise ValueError('EXACT_PRE_ARRAY_ADMISSION_REQUIRED')
  bindings = a['segment_bindings']
  if (len(bindings) != 154 or [v['receipt_sha256'] for v in bindings] != a['segment_receipts']
      or len({v['content_sha256'] for v in bindings}) != 154):
    raise ValueError('UNIQUE_EXACT_SEGMENT_BINDINGS_REQUIRED')
  for v in bindings:
    s.shape(v, {'content_sha256': str, 'receipt_sha256': str, 'route_id': str, 'rows': int})
    for k in ('content_sha256', 'receipt_sha256', 'route_id'):
      digest(v[k])
    if v['route_id'] not in ids or v['rows'] < 1:
      raise ValueError('ADMITTED_ROUTE_AND_ROWS_REQUIRED')
  for rid in ids:
    contents = sorted(v['content_sha256'] for v in bindings if v['route_id'] == rid)
    pin = pol['source_segment_sets'][rid]
    if len(contents) != pin['count'] or p.sha(p.canonical(contents)) != pin['set_sha256']:
      raise ValueError('EXACT_AUTHORIZED_CONTENT_SET_REQUIRED')
  digest(a['input_file_set_sha256'])
  for v in a['segment_receipts']:
    digest(v)
  s.aggregate_shape(b['counts'], dict.fromkeys([*ids, 'POOLED'], dict.fromkeys(COUNT_KEYS, int)))
  s.aggregate_shape(b['support'], dict.fromkeys([*ids, 'POOLED'], dict.fromkeys(m.SCOPES, SUPPORT)))
  for k in COUNT_KEYS:
    if b['counts']['POOLED'][k] != sum(b['counts'][r][k] for r in ids):
      raise ValueError('ROUTE_COUNTS_RECONCILIATION_CONFLICT')
  if b['counts']['POOLED']['segments'] != 154 or b['counts']['POOLED']['base_rows'] != 916535:
    raise ValueError('EXACT_RLOG_BASE_SET_REQUIRED')
  for rid in [*ids, 'POOLED']:
    count = b['counts'][rid]
    if not 0 <= count['model_eligible_rows'] <= count['causal_valid_rows'] <= count['base_rows']:
      raise ValueError('CAUSAL_MODEL_LAYER_CONFLICT')
    for scope in m.SCOPES:
      v = b['support'][rid][scope]
      if (v['target_zero_count']+v['target_positive_count']+v['target_negative_count'] != v['target_available_rows']
          or not 0 <= v['target_available_rows'] <= v['eligible_rows'] <= count['model_eligible_rows']
          or sum(v['eligible_speed_bins'].values()) != v['eligible_rows']
          or sum(v['target_speed_bins'].values()) != v['target_available_rows']
          or len(v['history_support_L1_to_L45']) != 45):
        raise ValueError('SUPPORT_TARGET_ACCOUNTING_CONFLICT')
      expected_fraction = v['target_zero_count']/v['target_available_rows'] if v['target_available_rows'] else None
      if v['target_zero_fraction'] != expected_fraction:
        raise ValueError('TARGET_FRACTION_CONFLICT')
      h = v['history_support_L1_to_L45']
      if any(y > x for x, y in zip([v['target_available_rows'], *h[:-1]], h, strict=True)):
        raise ValueError('HISTORY_SUPPORT_MUST_NOT_INCREASE')
    if b['support'][rid][m.SCOPES[0]]['eligible_rows'] != count['model_eligible_rows']:
      raise ValueError('BASE_SCOPE_ACCOUNTING_CONFLICT')
  for scope in m.SCOPES:
    pooled = b['support']['POOLED'][scope]
    for key in ('eligible_rows', 'target_available_rows', 'target_zero_count', 'target_positive_count', 'target_negative_count',
                'contributing_segments', 'contributing_causal_runs'):
      if pooled[key] != sum(b['support'][r][scope][key] for r in ids):
        raise ValueError('POOLED_SUPPORT_CONFLICT')
    if pooled['history_support_L1_to_L45'] != [sum(b['support'][r][scope]['history_support_L1_to_L45'][i] for r in ids) for i in range(45)]:
      raise ValueError('POOLED_HISTORY_CONFLICT')
  if len(b['forms']) != 8:
    raise ValueError('ALL_BOUNDARY_FORMS_REQUIRED')
  for row, (scope, form) in zip(b['forms'], [(q, f) for q in m.SCOPES for f in m.FORMS], strict=True):
    if set(row) != {'scope', 'form', 'diagnostics'} or row['scope'] != scope or row['form'] != list(form):
      raise ValueError('PREDECLARED_BOUNDARY_ORDER_REQUIRED')
    if set(row['diagnostics']) != {*ids, 'POOLED'}:
      raise ValueError('BOTH_ROUTES_AND_POOLED_REQUIRED')
    empty = {'tick': np.array([], dtype=np.int64), 'command': np.array([]), 'speed': np.array([]), 'streak': np.array([], dtype=np.int64)}
    names = m.feature_matrix(empty, np.array([], dtype=np.int64), form)[1]
    for rid, rank in row['diagnostics'].items():
      s.rank_scope(rank, names)
      s.privacy(rank)
      if rank['rows'] != rank['next_state_available'] or rank['rows'] > b['support'][rid][scope]['target_available_rows']:
        raise ValueError('FORM_TARGET_SUPPORT_CONFLICT')
    if row['diagnostics']['POOLED']['rows'] != sum(row['diagnostics'][r]['rows'] for r in ids):
      raise ValueError('FORM_POOLED_SUPPORT_CONFLICT')
  return value


def public(value):
  p.verify(value)
  s.privacy(value)
  static = [*policy.contracts().values(), admission.identity_contract(), admission.row_contract()]
  if value.get('schema') in {v['schema'] for v in static}:
    if value not in static:
      raise ValueError('STATIC_CONTRACT_DRIFT')
    return value
  if value.get('schema') == 'EMPIRICAL_S2_RI_DESIGN_POLICY_V1' and value == policy.policy():
    return value
  # Dynamic artifacts only emitted by publication.build after complete result validation.
  raise ValueError('DYNAMIC_PUBLICATION_REQUIRES_COMPLETE_EXECUTION_BUNDLE')


def validate_derived(local, root, policy_sha, source_receipt_sha, n):
  from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
  value = s.body(local, 'EMPIRICAL_S2_RI_DERIVED_SEGMENT_V1')
  if (set(value) != {'policy_sha256', 'source_receipt_sha256', 'arrays', 'rate_and_request_adversarial_exact'}
      or value['policy_sha256'] != policy_sha or value['source_receipt_sha256'] != source_receipt_sha
      or value['rate_and_request_adversarial_exact'] is not True):
    raise ValueError('EXACT_DERIVED_SOURCE_AND_ADVERSARIAL_PROOF_REQUIRED')
  boolean = {'s2_ri_causal_valid', 'model_eligible', 'angle_grid_valid', 'rail', 'base_regime',
             'target_available_all', 'target_available_non_rail'}
  integer = {'s2_ri_causal_run_id', 'within_s2_ri_causal_run_index', 'angle_tick', 'streak_all', 'streak_non_rail',
             'delta_tick_all', 'delta_tick_non_rail'}
  if set(value['arrays']) != boolean | integer:
    raise ValueError('COMPLETE_EXACT_DERIVED_ARRAY_SET_REQUIRED')
  arrays = {}
  for name, binding in value['arrays'].items():
    if set(binding) != {'dtype', 'shape', 'order', 'array_sha256', 'file_sha256'}:
      raise ValueError('EXACT_DERIVED_ARRAY_BINDING_REQUIRED')
    expected = np.dtype(bool).str if name in boolean else np.dtype(np.int64).str
    if binding['dtype'] != expected or binding['shape'] != [n] or binding['order'] != 'C':
      raise ValueError('EXACT_DERIVED_DTYPE_SHAPE_ORDER_REQUIRED')
    for key in ('array_sha256', 'file_sha256'):
      digest(binding[key])
    arrays[name] = read.read_array(root/read.array_name(name), binding)
  for label in ('all', 'non_rail'):
    ix = m.target_indices({'streak': arrays['streak_'+label]})
    mask = np.zeros(n, bool)
    mask[ix] = True
    delta = np.zeros(n, dtype=np.int64)
    delta[ix] = arrays['angle_tick'][ix+1]-arrays['angle_tick'][ix]
    if not np.array_equal(mask, arrays['target_available_'+label]) or not np.array_equal(delta, arrays['delta_tick_'+label]):
      raise ValueError('EXACT_DERIVED_TARGET_PROOF_REQUIRED')
  return local
