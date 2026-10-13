"""Verification of saved aggregate completeness without source reads or analysis."""

import math
from openpilot.tools.cyber_autotune.empirical_hurdle_attribution_math import require

ONE_CLASSES = (
  'ALL',
  'STATIC',
  'MOVE',
  'MOVE_POSITIVE',
  'MOVE_NEGATIVE',
  'ONE_TICK_MOVE',
  'MULTI_TICK_MOVE',
  'TN',
  'FP_PROJECTED_HOLD',
  'FP_PROJECTED_MOVE',
  'FN',
  'TP',
)
PATH_CLASSES = ('ALL', 'PATH_MOVED', 'PATH_FLAT', 'GATE_PERFECT_PATH_MOVED', 'GATE_ERROR_PATH_MOVED', 'NO_GATE_MISMATCH', 'FIRST_FP', 'FIRST_FN')
RELATIONS = ('gate_precedes_divergence', 'same_step', 'divergence_precedes_gate', 'gate_mismatch_only', 'divergence_only', 'neither')


def fields(value, names):
  require(isinstance(value, dict) and set(names) <= set(value), 'HURDLE_ATTRIBUTION_AGGREGATE_INCOMPLETE')


def metric(value, grid=False):
  fields(value, ('rmse', 'mae', 'p95', 'sae', 'sse'))
  require(all(isinstance(value[k], (int, float)) and math.isfinite(value[k]) and value[k] >= 0 for k in ('rmse', 'mae', 'p95', 'sae', 'sse')))
  if grid:
    fields(value, ('exact_hit_count', 'within_one_tick_count', 'exact_hit', 'within_one_tick'))
    require(0 <= value['exact_hit'] <= value['within_one_tick'] <= 1)


def pair(value, grid=False):
  fields(value, ('count', 'support_status', 'candidate', 'hold_last', 'delta_sae', 'delta_sse'))
  n = value['count']
  require(type(n) is int and n >= 0)
  require(value['support_status'] == ('EMPTY' if not n else 'SMALL_SUPPORT_DESCRIPTIVE_ONLY' if n < 201 else 'DESCRIPTIVE_ONLY'))
  if not n:
    require(all(value[k] is None for k in ('candidate', 'hold_last', 'delta_sae', 'delta_sse')))
  else:
    metric(value['candidate'], grid)
    metric(value['hold_last'], grid)
    require(
      value['delta_sae'] == value['candidate']['sae'] - value['hold_last']['sae']
      and value['delta_sse'] == value['candidate']['sse'] - value['hold_last']['sse']
    )


def event(value, n):
  fields(value, ('count', 'event_count', 'no_event_count', 'event_fraction', 'no_event_fraction', 'event_step_summary'))
  require(value['count'] == n and value['event_count'] + value['no_event_count'] == n)
  require(value['event_fraction'] == (value['event_count'] / n if n else None))
  require(value['no_event_fraction'] == (value['no_event_count'] / n if n else None))
  distribution(value['event_step_summary'], value['event_count'])


def distribution(value, n):
  fields(value, ('count', 'min', 'median', 'p95', 'max'))
  require(value['count'] == n)
  if not n:
    require(all(value[k] is None for k in ('min', 'median', 'p95', 'max')))
  else:
    require(all(isinstance(value[k], (int, float)) and math.isfinite(value[k]) for k in ('min', 'median', 'p95', 'max')))


def confusion(value, n):
  fields(
    value,
    (
      'counts',
      'count',
      'fractions',
      'true_move_fraction',
      'predicted_move_fraction',
      'false_move_rate',
      'missed_move_rate',
      'precision',
      'recall',
      'specificity',
      'balanced_accuracy',
    ),
  )
  require(set(value['counts']) == {'TN', 'FP', 'FN', 'TP'} and value['count'] == n)
  require(all(type(v) is int and v >= 0 for v in value['counts'].values()) and sum(value['counts'].values()) == n)

  require(set(value['fractions']) == {'TN', 'FP', 'FN', 'TP'})
  for k, v in value['counts'].items():
    require(value['fractions'][k] == (v / n if n else None))
  for k in ('true_move_fraction', 'predicted_move_fraction', 'false_move_rate', 'missed_move_rate', 'precision', 'recall', 'specificity', 'balanced_accuracy'):
    rate(value[k], nullable=True)


def one_step(value):
  fields(value, ('confusion', 'exact_hit', 'classes', 'static_fraction', 'fp', 'fn', 'oracle', 'accounting', 'transfer', 'historical_metric_reconciliation'))
  require(set(value['classes']) == set(ONE_CLASSES))
  for v in value['classes'].values():
    pair(v, grid=True)
  cls = value['classes']
  n = cls['ALL']['count']
  require(n > 0 and cls['STATIC']['count'] + cls['MOVE']['count'] == n)
  confusion(value['confusion'], n)
  fields(
    value['exact_hit'],
    (
      'static_hit_loss',
      'move_hit_gain',
      'net_hit_delta',
      'integer_accounting_exact',
      'static_loss_exceeds_move_gain',
      'candidate_static_hits',
      'hold_static_hits',
      'candidate_move_hits',
      'hold_move_hits',
      'candidate_total_hits',
      'hold_total_hits',
    ),
  )
  hits = value['exact_hit']
  require(hits['net_hit_delta'] == hits['move_hit_gain'] - hits['static_hit_loss'] and hits['integer_accounting_exact'])
  fields(value['fp'], ('stage2_invoked_count', 'projected_same_tick_count', 'projected_moved_count', 'exact_hit_count', 'within_one_tick_count'))
  fields(value['fn'], ('count', 'integrated_equals_hold', 'metrics', 'actual_delta_magnitude'))
  require(value['fn']['integrated_equals_hold'])
  fields(
    value['oracle'],
    (
      'role',
      'metrics',
      'sign_accuracy',
      'integrated',
      'hold_last',
      'oracle_to_integrated_delta_sae',
      'oracle_to_integrated_delta_sse',
      'tp_fn_accounting',
      'historical_grid_metrics',
      'grid_provenance',
    ),
  )
  metric(value['oracle']['metrics'])
  require(value['oracle']['role'] == 'DIAGNOSTIC_ONLY')
  fields(value['accounting'], ('row_partition_exact', 'count', 'classes_count', 'candidate', 'hold_last'))
  require(value['accounting']['row_partition_exact'] and value['accounting']['count'] == n)
  fields(value['transfer'], ('train', 'development', 'dev_minus_train', 'threshold_lineage', 'alternative_thresholds_evaluated', 'threshold_receipt_sha256'))
  confusion(value['transfer']['development'], n)
  confusion(value['transfer']['train'], value['transfer']['train']['count'])
  require(value['transfer']['alternative_thresholds_evaluated'] == 0 and value['historical_metric_reconciliation'] == 'EXACT')

  one_step_leaves(value)


def rollout(value, horizon):
  fields(
    value,
    (
      'count',
      'classes',
      'gate_confusion',
      'first_gate_mismatch',
      'first_projected_divergence',
      'first_event_relation',
      'path_flat',
      'count_distributions',
      'historical_metric_reconciliation',
    ),
  )
  n = value['count']
  require(n > 0 and set(value['classes']) == set(PATH_CLASSES))
  for v in value['classes'].values():
    pair(v)
  require(value['classes']['ALL']['count'] == n and value['classes']['PATH_FLAT']['count'] + value['classes']['PATH_MOVED']['count'] == n)
  confusion(value['gate_confusion'], n * horizon)
  event(value['first_gate_mismatch'], n)
  event(value['first_projected_divergence'], n)
  require(set(value['first_event_relation']) == set(RELATIONS) and sum(value['first_event_relation'].values()) == n)
  flat = value['path_flat']
  fields(flat, ('count', 'any_move_gate_count', 'any_projected_motion_count', 'first_false_gate', 'first_projected_false_move'))
  event(flat['first_false_gate'], flat['count'])
  event(flat['first_projected_false_move'], flat['count'])
  require(set(value['count_distributions']) == {'gate_fp_count', 'gate_fn_count', 'projected_move_count', 'observed_move_count'})
  for v in value['count_distributions'].values():
    distribution(v, n)
  require(value['historical_metric_reconciliation'] == 'EXACT')


def job(value):
  fields(
    value,
    ('schema', 'candidate_id', 'fold', 'original_job_receipt_sha256', 'population_receipts', 'authorization_sha256', 'historical_gate', 'one_step', 'rollout'),
  )
  require(set(value['population_receipts']) == {'train', 'one-step', 'rollout-25', 'rollout-50', 'rollout-100', 'rollout-200'})
  for item in value['population_receipts'].values():
    sha(item)
  sha(value['original_job_receipt_sha256'])
  sha(value['authorization_sha256'])
  one_step(value['one_step'])
  require(set(value['rollout']) == {'25', '50', '100', '200'}, 'HURDLE_ATTRIBUTION_AGGREGATE_INCOMPLETE')
  for h, v in value['rollout'].items():
    rollout(v, int(h))
  fields(value['historical_gate'], ('clauses', 'failures', 'pass'))
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as analysis

  gate = value['historical_gate']
  require(len(gate['clauses']) == 32 and {c['id'] for c in gate['clauses']} == set(analysis.EXPECTED_FAILURES))
  for clause in gate['clauses']:
    fields(clause, ('id', 'pass', 'evaluated'))
    require(clause['evaluated'] is True and type(clause['pass']) is bool)
  require(gate['failures'] == [c['id'] for c in gate['clauses'] if not c['pass']])
  require(gate['pass'] == (not gate['failures']))


def sha(value):
  require(isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value))


def rate(value, nullable=False):
  require((nullable and value is None) or (type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1))


def accounting(value, counts, measures):
  fields(value, ('row_partition_exact', 'count', 'classes_count', 'candidate', 'hold_last'))
  require(value['row_partition_exact'] is True and value['classes_count'] == counts and value['count'] == sum(counts))
  for who in ('candidate', 'hold_last'):
    fields(value[who], ('sae', 'sse'))
    for name in ('sae', 'sse'):
      item = value[who][name]
      fields(item, ('original_anchor_order', 'partition_order', 'partition_minus_original', 'contribution_bytes_exact'))
      require(item['contribution_bytes_exact'] is True)
      require(all(type(item[k]) in (int, float) and math.isfinite(item[k]) for k in ('original_anchor_order', 'partition_order', 'partition_minus_original')))
      require(item['original_anchor_order'] == measures[who][name])
      require(item['partition_minus_original'] == item['partition_order'] - item['original_anchor_order'])


def one_step_leaves(value):
  cls = value['classes']
  n, static, move = (cls[k]['count'] for k in ('ALL', 'STATIC', 'MOVE'))
  counts = value['confusion']['counts']
  require(cls['TN']['count'] == counts['TN'] and cls['FN']['count'] == counts['FN'] and cls['TP']['count'] == counts['TP'])
  require(cls['FP_PROJECTED_HOLD']['count'] + cls['FP_PROJECTED_MOVE']['count'] == counts['FP'])
  require(counts['TN'] + counts['FP'] == static and counts['FN'] + counts['TP'] == move)
  require(cls['MOVE_POSITIVE']['count'] + cls['MOVE_NEGATIVE']['count'] == move)
  require(cls['ONE_TICK_MOVE']['count'] + cls['MULTI_TICK_MOVE']['count'] == move)
  require(value['static_fraction'] == static / n)
  for name in ('MOVE', 'TP'):
    fields(cls[name], ('continuous_sign_accuracy', 'projected_sign_accuracy'))
    for key in ('continuous_sign_accuracy', 'projected_sign_accuracy'):
      rate(cls[name][key], nullable=cls[name]['count'] == 0)
      require((cls[name][key] is None) == (cls[name]['count'] == 0))
  hits = value['exact_hit']
  for prefix, who in (('candidate', 'candidate'), ('hold', 'hold_last')):
    for suffix, name in (('static', 'STATIC'), ('move', 'MOVE'), ('total', 'ALL')):
      require(hits[f'{prefix}_{suffix}_hits'] == cls[name][who]['exact_hit_count'])
  require(hits['static_hit_loss'] == hits['hold_static_hits'] - hits['candidate_static_hits'])
  require(hits['move_hit_gain'] == hits['candidate_move_hits'] - hits['hold_move_hits'])
  require(hits['net_hit_delta'] == hits['candidate_total_hits'] - hits['hold_total_hits'])
  require(hits['static_loss_exceeds_move_gain'] == (hits['static_hit_loss'] > hits['move_hit_gain']))
  fp = value['fp']
  require(fp['stage2_invoked_count'] == counts['FP'])
  require(fp['projected_same_tick_count'] == cls['FP_PROJECTED_HOLD']['count'] == fp['exact_hit_count'])
  require(fp['projected_moved_count'] == cls['FP_PROJECTED_MOVE']['count'])
  require(type(fp['within_one_tick_count']) is int and fp['exact_hit_count'] <= fp['within_one_tick_count'] <= counts['FP'])
  fn = value['fn']
  require(
    fn['count'] == counts['FN'] and fn['metrics'] == (None if not fn['count'] else {k: cls['FN']['candidate'][k] for k in ('rmse', 'mae', 'p95', 'sae', 'sse')})
  )
  if fn['count']:
    metric(fn['metrics'])
  distribution(fn['actual_delta_magnitude'], fn['count'])
  oracle = value['oracle']
  metric(oracle['integrated'], grid=True)
  metric(oracle['hold_last'], grid=True)
  require(oracle['integrated'] == cls['MOVE']['candidate'] and oracle['hold_last'] == cls['MOVE']['hold_last'])
  rate(oracle['sign_accuracy'])
  fields(oracle['historical_grid_metrics'], ('exact_hit', 'within_one_tick'))
  rate(oracle['historical_grid_metrics']['exact_hit'])
  rate(oracle['historical_grid_metrics']['within_one_tick'])
  require(oracle['grid_provenance'] == 'PINNED_ORIGINAL_JOB_AGGREGATE_NO_PROJECTION_EXECUTION')
  for name in ('sae', 'sse'):
    require(oracle[f'oracle_to_integrated_delta_{name}'] == oracle['integrated'][name] - oracle['metrics'][name])
  accounting(oracle['tp_fn_accounting'], [counts['TP'], counts['FN']], cls['MOVE'])
  accounting(value['accounting'], [static, move], cls['ALL'])
  transfer = value['transfer']
  names = ('false_move_rate', 'missed_move_rate', 'recall', 'specificity', 'balanced_accuracy')
  fields(transfer['dev_minus_train'], names)
  require(transfer['development'] == value['confusion'] and transfer['threshold_lineage'] == 'SAME_FROZEN_TRAIN_THRESHOLD')
  sha(transfer['threshold_receipt_sha256'])
  for name in names:
    require(transfer['dev_minus_train'][name] == transfer['development'][name] - transfer['train'][name])


def summary(value):
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as analysis

  fields(value, ('schema', 'status', 'one_step', 'folds', 'rollout', 'historical_failure_counts', 'historical_selection', 'model_selection', 'execution_calls'))
  require(value['schema'] == 'EMPIRICAL_HURDLE_FAILURE_MECHANISM_SUMMARY_V1' and value['status'] == analysis.SUCCESS)
  require(value['historical_failure_counts'] == analysis.EXPECTED_FAILURES and value['execution_calls'] == analysis.ZERO_CALLS)
  require(value['historical_selection'] == 'HURDLE_NO_ADMISSIBLE_CANDIDATE' and value['model_selection'] == 'MODEL_SELECTION_FAILED_CLOSED')
  one = value['one_step']
  fields(
    one,
    (
      'job_counts',
      'exact_hit_state',
      'stage1_design_review',
      'authority',
      'implementation_authorized',
      'fitting_authorized',
      'stage2_implementation_authorized',
    ),
  )
  names = ('move_protection_pass', 'exact_hit_fail', 'static_loss_exceeds_gain', 'projected_false_move')
  require(set(one['job_counts']) == set(names))
  require(all(type(v) is int and 0 <= v <= 32 for v in one['job_counts'].values()))
  exact = one['job_counts']['exact_hit_fail'] == one['job_counts']['static_loss_exceeds_gain'] == 32
  require(one['exact_hit_state'] == ('HURDLE_EXACT_HIT_STATIC_LOSS_ALL_JOBS' if exact else 'HURDLE_EXACT_HIT_MECHANISM_MIXED'))
  supported = all(v == 32 for v in one['job_counts'].values())
  require(one['stage1_design_review'] == ('STAGE1_GATE_REDESIGN_REVIEW_SUPPORTED' if supported else 'STAGE1_GATE_REDESIGN_REVIEW_NOT_FULLY_SUPPORTED'))
  require(
    one['authority'] == 'DESIGN_REVIEW_ONLY'
    and all(one[k] is False for k in ('implementation_authorized', 'fitting_authorized', 'stage2_implementation_authorized'))
  )
  require(set(value['folds']) == {'FOLD_A', 'FOLD_B'})
  for fold in value['folds'].values():
    fields(fold, ('job_count', 'historical_failure_counts', 'ranges'))
    require(fold['job_count'] == 16 and set(fold['historical_failure_counts']) == set(analysis.EXPECTED_FAILURES))
    require(all(type(v) is int and 0 <= v <= 16 for v in fold['historical_failure_counts'].values()))
    require(set(fold['ranges']) == {'false_move_rate', 'missed_move_rate', 'balanced_accuracy', 'static_hit_loss', 'move_hit_gain'})
    for item in fold['ranges'].values():
      fields(item, ('min', 'max'))
      require(
        type(item['min']) in (int, float)
        and type(item['max']) in (int, float)
        and math.isfinite(item['min'])
        and math.isfinite(item['max'])
        and item['min'] <= item['max']
      )
  for key, count in analysis.EXPECTED_FAILURES.items():
    require(sum(f['historical_failure_counts'][key] for f in value['folds'].values()) == count)
  require(set(value['rollout']) == {'25', '50', '100', '200'})
  keys = (
    'gate_perfect_path_moved_support_jobs',
    'small_support_jobs',
    'candidate_sse_less_hold_jobs',
    'candidate_sse_greater_hold_jobs',
    'candidate_p95_nonworse_jobs',
    'candidate_p95_worse_jobs',
  )
  for item in value['rollout'].values():
    fields(item, (*keys, 'gate_mismatch_relations', 'interpretation'))
    require(all(type(item[k]) is int and 0 <= item[k] <= 32 for k in keys))
    support = item['gate_perfect_path_moved_support_jobs']
    require(item['small_support_jobs'] <= support and item['candidate_sse_less_hold_jobs'] + item['candidate_sse_greater_hold_jobs'] <= support)
    require(item['candidate_p95_nonworse_jobs'] + item['candidate_p95_worse_jobs'] == support)
    require(set(item['gate_mismatch_relations']) == set(RELATIONS))
    require(all(type(v) is int and v >= 0 for v in item['gate_mismatch_relations'].values()))
    require(item['interpretation'] == 'DESCRIPTIVE_ASSOCIATION_NOT_CAUSAL; POPULATIONS_OVERLAP_ACROSS_STRUCTURES')


def readiness(value, summary_value):
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as analysis
  from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io

  fields(
    value,
    (
      'schema',
      'status',
      'states',
      'job_count',
      'one_step_populations',
      'rollout_populations',
      'summary_sha256',
      'execution_calls',
      'source_manifest_sha256',
      'source_manifest_listed_bytes_unchanged',
      'source_write_count',
      'source_fallback',
      'holdout',
      'opening_count',
      'vehicle_authority',
    ),
  )
  require(value['schema'] == 'EMPIRICAL_HURDLE_ATTRIBUTION_READINESS_V1' and value['status'] == analysis.SUCCESS)
  require(
    value['states']
    == [
      'READ_ONLY_ATTRIBUTION_COMPLETE',
      'NO_NEW_MODEL_FIT',
      'NO_THRESHOLD_RESELECTION',
      'NO_MODEL_REPLAY',
      'NO_MODEL_SELECTION',
      'NO_POLICY_CHANGE',
      'HURDLE_NO_ADMISSIBLE_CANDIDATE_PRESERVED',
    ]
  )
  require((value['job_count'], value['one_step_populations'], value['rollout_populations']) == (32, 32, 128))
  require(value['summary_sha256'] == summary_value['receipt_sha256'] and value['execution_calls'] == analysis.ZERO_CALLS)
  require(value['source_manifest_sha256'] == io.SOURCE_SHA and value['source_manifest_listed_bytes_unchanged'] is True)
  require(
    value['source_write_count'] == value['opening_count'] == 0
    and value['source_fallback'] is False
    and value['holdout'] == 'CLOSED'
    and value['vehicle_authority'] == 'NONE'
  )


# Allowed aggregate contract keys, derived from the complete synthetic schema (no private input).
PUBLIC_KEYS = frozenset(
  [
    '100',
    '200',
    '25',
    '50',
    'ALL',
    'FIRST_FN',
    'FIRST_FP',
    'FN',
    'FOLD_A',
    'FOLD_B',
    'FP',
    'FP_PROJECTED_HOLD',
    'FP_PROJECTED_MOVE',
    'GATE_ERROR_PATH_MOVED',
    'GATE_PERFECT_PATH_MOVED',
    'MOVE',
    'MOVE_MAE',
    'MOVE_NEGATIVE',
    'MOVE_P95',
    'MOVE_POSITIVE',
    'MOVE_RMSE',
    'MULTI_TICK_MOVE',
    'NO_GATE_MISMATCH',
    'ONE_STEP_EXACT_HIT',
    'ONE_STEP_MAE',
    'ONE_STEP_P95',
    'ONE_STEP_RMSE',
    'ONE_STEP_WITHIN_ONE_TICK',
    'ONE_TICK_MOVE',
    'OVERALL_100_MAE',
    'OVERALL_100_P95',
    'OVERALL_100_RMSE',
    'OVERALL_200_MAE',
    'OVERALL_200_P95',
    'OVERALL_200_RMSE',
    'OVERALL_25_MAE',
    'OVERALL_25_P95',
    'OVERALL_25_RMSE',
    'OVERALL_50_MAE',
    'OVERALL_50_P95',
    'OVERALL_50_RMSE',
    'PATH_FLAT',
    'PATH_MOVED',
    'PATH_MOVED_100_MAE',
    'PATH_MOVED_100_P95',
    'PATH_MOVED_100_RMSE',
    'PATH_MOVED_200_MAE',
    'PATH_MOVED_200_P95',
    'PATH_MOVED_200_RMSE',
    'PATH_MOVED_25_MAE',
    'PATH_MOVED_25_P95',
    'PATH_MOVED_25_RMSE',
    'PATH_MOVED_50_MAE',
    'PATH_MOVED_50_P95',
    'PATH_MOVED_50_RMSE',
    'S1',
    'S2',
    'S3',
    'STATIC',
    'TN',
    'TP',
    'accounting',
    'actual_delta_magnitude',
    'all_file_hashes_exact',
    'alternative_thresholds',
    'alternative_thresholds_evaluated',
    'any_move_gate_count',
    'any_projected_motion_count',
    'array_or_path_output',
    'attribution_manifest_sha256',
    'authority',
    'balanced_accuracy',
    'baseline',
    'browser',
    'calibration_blockers',
    'candidate',
    'candidate-gates',
    'candidate_id',
    'candidate_move_hits',
    'candidate_p95_nonworse_jobs',
    'candidate_p95_worse_jobs',
    'candidate_ranking',
    'candidate_search_authorized',
    'candidate_sse_greater_hold_jobs',
    'candidate_sse_less_hold_jobs',
    'candidate_static_hits',
    'candidate_total_hits',
    'canonical_one_step_error',
    'causal_claim',
    'causal_source_openings',
    'checks',
    'chunk_rows',
    'classes',
    'classes_count',
    'closed_loop_bias',
    'composition',
    'composition_authorized',
    'confusion',
    'continuous_sign_accuracy',
    'contribution_bytes_exact',
    'count',
    'count_distributions',
    'counterfactual_admission',
    'counts',
    'dataset',
    'delta_sae',
    'delta_sse',
    'dev_minus_train',
    'development',
    'divergence_only',
    'divergence_precedes_gate',
    'empty_subset',
    'event_count',
    'event_fraction',
    'event_step_summary',
    'exact_hit',
    'exact_hit_count',
    'exact_hit_fail',
    'exact_hit_state',
    'execution_calls',
    'expected_historical_failure_counts',
    'false_move_rate',
    'family_verdict',
    'final_pooled_refit',
    'first_event',
    'first_event_relation',
    'first_false_gate',
    'first_gate_mismatch',
    'first_projected_divergence',
    'first_projected_false_move',
    'fit-cv-authorization',
    'fit-cv-job-manifest',
    'fit-cv-readiness',
    'fit-cv-repeatability',
    'fit-cv-results',
    'fit-cv-validation',
    'fitting_authorized',
    'fn',
    'fold',
    'fold_summaries',
    'folds',
    'fp',
    'fractions',
    'future_holdout',
    'gate_confusion',
    'gate_fn_count',
    'gate_fp_count',
    'gate_mismatch_only',
    'gate_mismatch_relations',
    'gate_perfect',
    'gate_perfect_path_moved_support_jobs',
    'gate_precedes_divergence',
    'grid_provenance',
    'historical_attribution',
    'historical_design_trigger',
    'historical_failure_counts',
    'historical_grid_metrics',
    'historical_metric_reconciliation',
    'historical_rollout_failures',
    'historical_s2_ri_verdict',
    'historical_selection',
    'historical_track',
    'historical_verdict',
    'hold_last',
    'hold_move_hits',
    'hold_static_hits',
    'hold_total_hits',
    'holdout',
    'holdout_openings',
    'holdout_state',
    'horizons',
    'implementation_authorized',
    'independent_review',
    'independent_runs',
    'integer_accounting_exact',
    'integrated',
    'integrated_equals_hold',
    'interpretation',
    'job_count',
    'job_counts',
    'job_order',
    'jobs',
    'limitations',
    'mae',
    'max',
    'mechanism_states',
    'median',
    'metrics',
    'min',
    'missed_move_rate',
    'model_refit_calls',
    'model_replay_calls',
    'move_hit_gain',
    'move_protection_pass',
    'neither',
    'net_hit_delta',
    'no_event_count',
    'no_event_fraction',
    'no_model_admitted',
    'normalizer_refit_calls',
    'observed_move_count',
    'one_step',
    'one_step_populations',
    'opening_count',
    'oracle',
    'oracle_to_integrated_delta_sae',
    'oracle_to_integrated_delta_sse',
    'original_anchor_order',
    'original_job_receipt_sha256',
    'output_volume',
    'p95',
    'p95_is_additive',
    'paired_route_transfer_directions',
    'partition_minus_original',
    'partition_order',
    'partition_reconciliation',
    'path_flat',
    'path_truth',
    'policy_sha256',
    'precision',
    'predicted_move_fraction',
    'private_repeatability_receipt_sha256',
    'production_authority',
    'projected_false_move',
    'projected_move_count',
    'projected_moved_count',
    'projected_same_tick_count',
    'projected_sign_accuracy',
    'public_input_receipts',
    'publication_raw_data',
    'purpose',
    'qlog_openings',
    'qualification_allowed',
    'ranges',
    'ranking_performed',
    'raw_log_openings',
    'recall',
    'receipt_sha256',
    'receipts_exact',
    'redesign_implementation_authorized',
    'reference_promotable',
    'review_authority',
    'rmse',
    'role',
    'rollout',
    'rollout_populations',
    'row_partition_exact',
    'sae',
    'same_step',
    'schema',
    'sealed_reference',
    'sealed_reference_allowed',
    'search',
    'selection-result',
    'selection_calls',
    'sg',
    'sg_execution',
    'sign_accuracy',
    'small_subset',
    'small_support_jobs',
    'source_fallback',
    'source_manifest_listed_bytes_unchanged',
    'source_manifest_sha256',
    'source_repeatability_sha256',
    'source_write_count',
    'specificity',
    'sse',
    'stage1-results',
    'stage1_design_review',
    'stage1_review_trigger',
    'stage2-diagnostics',
    'stage2_implementation_authorized',
    'stage2_invoked_count',
    'stage_b',
    'states',
    'static_fraction',
    'static_hit_loss',
    'static_loss_exceeds_gain',
    'static_loss_exceeds_move_gain',
    'status',
    'storage',
    'support_status',
    'ta',
    'ta_execution',
    'threshold-results',
    'threshold_lineage',
    'threshold_policy_change',
    'threshold_receipt_sha256',
    'threshold_reselection_calls',
    'tp_fn_accounting',
    'train',
    'transfer',
    'trapped_resume_exact',
    'true_move_fraction',
    'vehicle',
    'vehicle_activation_allowed',
    'vehicle_authority',
    'within_one_tick',
    'within_one_tick_count',
  ]
)
