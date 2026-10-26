"""E2 actual D2 evaluation, reusing frozen E1 math and immutable D0/D1 arms."""

import copy
import json
import math
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_evaluation as e1
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as decision

need = decision.need
HORIZONS = e1.HORIZONS
CLAUSE_IDS = (
  'ONE_STEP_RMSE',
  'ONE_STEP_MAE',
  'ONE_STEP_P95',
  'ONE_STEP_EXACT_HIT',
  'ONE_STEP_WITHIN_ONE_TICK',
  'MOVE_RMSE',
  'MOVE_MAE',
  'MOVE_P95',
  *(f'{population}_{horizon}_{metric}' for population in ('OVERALL', 'PATH_MOVED') for horizon in HORIZONS for metric in ('RMSE', 'MAE', 'P95')),
)
seal, sha, canonical = e1.seal, e1.sha, e1.canonical
FORBIDDEN = (
  'stage1_refit',
  'stage2_refit',
  'normalizer_refit',
  'calibration_fit',
  'additional_policy_search',
  'extra_policy_arm',
  'posthoc_threshold_tuning',
  'guard_relaxation',
  'candidate_grid_change',
  'pooled_refit',
  'composition',
  'raw_log_openings',
  'qlog_openings',
  'holdout_openings',
  'holdout_discovery',
  'controller_changes',
  'vehicle_activation',
  'source_writes',
)


def changed_lower_bound(first_vs_baseline, second_vs_baseline, *, exact_same_policy=False):
  need(type(first_vs_baseline) is int and type(second_vs_baseline) is int and min(first_vs_baseline, second_vs_baseline) >= 0)
  if exact_same_policy or first_vs_baseline == second_vs_baseline == 0:
    return 0
  difference = abs(first_vs_baseline - second_vs_baseline)
  return difference if difference else None


def rollout(segments, candidate, model, decisions, stage2, horizon, expected, old_error, old_D1, same_policy, counters):
  blocks, anchor, n = e1.data.binding(segments, candidate, horizon)
  need(anchor == expected['anchor_sha256'] and n == expected['count'], 'E2_ROLLOUT_ANCHOR_CONFLICT')
  need(old_error.dtype == np.float64 and old_error.shape == (n,), 'E2_D0_ERROR_ALIGNMENT_CONFLICT')
  delay, length = e1.frozen.m.parameters(candidate)
  endpoints, baseline_all, moved_all, gate_perfect, movement_perfect = [], [], [], [], []
  drift, failure, offset = {}, None, 0
  for segment, indices in blocks:
    for start in range(0, len(indices), e1.frozen.m.CHUNK):
      ix = indices[start : start + e1.frozen.m.CHUNK]
      initial = segment['tick'][ix[:, None] + np.arange(-length, 1)].astype(np.int64)
      command = segment['command'][ix[:, None] + np.arange(-delay - length + 1, horizon - delay)]
      speed = segment['speed'][ix[:, None] + np.arange(horizon)]
      path = None
      if failure is None:
        try:
          path, gate, context = e1.recursive(initial, command, speed, candidate, model, decisions, stage2, horizon, counters)
        except ValueError as exc:
          if not str(exc).startswith(('CANDIDATE_FOLD_NUMERICAL_FAILURE', 'HURDLE_NUMERICAL_FAILURE', 'V4_STAGE1_NUMERICAL_FAILURE')):
            raise
          failure = str(exc)
      observed = segment['tick'][ix[:, None] + np.arange(horizon + 1)].astype(np.int64)
      baseline_all.append((observed[:, 0] - observed[:, -1]).astype(np.float64))
      moved_all.append(e1.path_moved(observed))
      offset += len(ix)
      if path is None:
        continue
      endpoints.append((path[:, -1] - observed[:, -1]).astype(np.float64))
      chunk, pg, pm = e1.drift_chunk(initial, observed, path, gate, context, length)
      gate_perfect.append(pg)
      movement_perfect.append(pm)
      for key, value in chunk.items():
        drift[key] = drift.get(key, np.zeros_like(value)) + value
  need(offset == n, 'E2_ROLLOUT_ROW_COUNT_CONFLICT')
  baseline, moved = np.concatenate(baseline_all), np.concatenate(moved_all)
  need(e1.data.pair(old_error, baseline, anchor) == expected, 'E2_D0_SAVED_ROLLOUT_METRIC_CONFLICT')
  if failure:
    return {'overall': None, 'path_moved': None, 'status': 'NUMERICAL_FAILURE', 'failure': failure, 'state_drift': None}
  error = np.concatenate(endpoints)
  count_moved = int(np.count_nonzero(moved))
  changed = int(np.count_nonzero(error != old_error))
  changed_moved = int(np.count_nonzero((error != old_error) & moved))
  old_changed = old_D1['paired_changed_endpoint_rows']
  old_changed_moved = old_D1['paired_changed_path_moved_endpoint_rows']
  return {
    'overall': e1.data.pair(error, baseline, anchor) if n >= 201 else None,
    'path_moved': e1.data.pair(error[moved], baseline[moved], e1.data.subset_sha(anchor, moved)) if count_moved >= 201 else None,
    'path_moved_count': count_moved,
    'status': 'COMPLETE' if n >= 201 and count_moved >= 201 else 'V4_ROLLOUT_SUPPORT_FAILURE',
    'state_drift': {k: v.tolist() for k, v in drift.items()},
    'moved_gate_perfect': e1.subset_support(error, baseline, moved & np.concatenate(gate_perfect)),
    'moved_projected_movement_perfect': e1.subset_support(error, baseline, moved & np.concatenate(movement_perfect)),
    'paired_changed_endpoint_rows': changed,
    'paired_changed_path_moved_endpoint_rows': changed_moved,
    'D1_changed_endpoint_lower_bound': changed_lower_bound(old_changed, changed, exact_same_policy=same_policy),
    'D1_changed_path_moved_endpoint_lower_bound': changed_lower_bound(old_changed_moved, changed_moved, exact_same_policy=same_policy),
    'D0_D1_rollouts_reexecuted': False,
  }


def metric_differences(arms):
  result = {}
  for first, second in (('D2', 'D0'), ('D2', 'D1'), ('D1', 'D0')):
    groups = {}
    for name in ('one_step', 'true_move'):
      a, b = arms[first][name], arms[second][name]
      need(a is None or b is None or (a['anchor_sha256'] == b['anchor_sha256'] and a['count'] == b['count']), 'E2_PAIRED_ANCHOR_CONFLICT')
      groups[name] = None if a is None or b is None else {m: a['candidate'][m] - b['candidate'][m] for m in ('rmse', 'mae', 'p95')}
    for h in HORIZONS:
      for name in ('overall', 'path_moved'):
        a, b = arms[first]['rollout'][str(h)][name], arms[second]['rollout'][str(h)][name]
        need(a is None or b is None or (a['anchor_sha256'] == b['anchor_sha256'] and a['count'] == b['count']), 'E2_PAIRED_ROLLOUT_ANCHOR_CONFLICT')
        groups[f'H{h}_{name}'] = None if a is None or b is None else {m: a['candidate'][m] - b['candidate'][m] for m in ('rmse', 'mae', 'p95')}
    result[first + '_MINUS_' + second] = groups
  return result


def one_step(segments, candidate, model, decisions, stage2, saved, expected, counters):
  _, anchor, x, current, target = e1.data.design(segments, candidate)
  current, target = current.astype(np.int64), target.astype(np.int64)
  actual, prior = target - current, x[:, -3].astype(np.int64)
  truth = actual != 0
  need(anchor == expected['anchor_sha256'] and len(x) == expected['count'], 'E_DEV_ANCHOR_CONFLICT')
  need(np.array_equal(saved['true_move'], truth) and np.array_equal(saved['prior_delta_tick'], prior), 'E_DEV_ROW_ALIGNMENT_CONFLICT')
  prob = e1.frozen.probability(x, model)
  decision.count(counters, 'stage1_inference_calls', len(x))
  need(decision.byte_equal(prob, saved['p_move']), 'E_FROZEN_STAGE1_SCORE_NOT_BYTE_EQUIVALENT')
  numerical_failure, output = None, None
  try:
    output = e1.integrated(x, current, model, decisions, stage2, counters, p_move=prob)
  except ValueError as exc:
    if not str(exc).startswith(('CANDIDATE_FOLD_NUMERICAL_FAILURE', 'HURDLE_NUMERICAL_FAILURE')):
      raise
    numerical_failure = str(exc)
  old_gate = saved['predicted_gate']
  old_delta, old_projected = saved['integrated_delta'], saved['projected_next_tick'].astype(np.int64)
  need(not np.any(~old_gate & (old_delta != 0)) and not np.any(~old_gate & (old_projected != current)), 'E_D0_STATIC_CONFLICT')
  if np.any(old_gate):
    reproduction = e1.frozen.m.predict_delta(np.ascontiguousarray(x[old_gate]), stage2)
    decision.count(counters, 'D0_stage2_equivalence_calls', int(np.count_nonzero(old_gate)))
    need(decision.byte_equal(reproduction, old_delta[old_gate]), 'E_D0_STAGE2_EQUIVALENCE_CONFLICT')
    need(np.array_equal(e1.frozen.m.project(current[old_gate].astype(np.float64) + reproduction), old_projected[old_gate]), 'E_D0_PROJECTION_CONFLICT')
    decision.count(counters, 'D0_projection_equivalence_calls', int(np.count_nonzero(old_gate)))
  need(np.array_equal(saved['candidate_error'], old_delta - actual), 'E_D0_SAVED_ERROR_CONFLICT')
  arms = {}
  for name, row in (('D0', {'gate': old_gate, 'delta': old_delta, 'projected': old_projected}), ('D2', output)):
    if row is None:
      arms[name] = {
        'status': 'DEVELOPMENT_OR_ROLLOUT_FAILURE',
        'failure': numerical_failure,
        'one_step': None,
        'true_move': None,
        'tick_diagnostics': None,
        'rollout': {},
      }
      continue
    error, baseline = row['delta'] - actual.astype(np.float64), -actual.astype(np.float64)
    arms[name] = {
      'status': 'EXECUTED_COMPLETE',
      'one_step': e1.data.pair(error, baseline, anchor, row['projected'], target, current),
      'true_move': e1.data.pair(error[truth], baseline[truth], e1.data.subset_sha(anchor, truth), row['projected'][truth], target[truth], current[truth]),
      'tick_diagnostics': e1.tick_diagnostics(current, target, prior, row),
      'rollout': {},
    }
  arms['D2']['paired_changes'] = (
    None
    if output is None
    else {
      'gate_rows': int(np.count_nonzero(output['gate'] != old_gate)),
      'projected_rows': int(np.count_nonzero(output['projected'] != old_projected)),
      'true_move_projected_rows': int(np.count_nonzero(truth & (output['projected'] != old_projected))),
      'true_move_continuous_rows': int(np.count_nonzero(truth & (output['delta'] != old_delta))),
      'continuous_rows': int(np.count_nonzero(output['delta'] != old_delta)),
    }
  )
  if output is not None:
    for label, mask in zip(e1.TRANSITIONS, ((prior == 0) & ~truth, (prior == 0) & truth, (prior != 0) & ~truth, (prior != 0) & truth), strict=True):
      arms['D2']['tick_diagnostics']['transitions'][label]['paired_changed_gate_rows'] = int(np.count_nonzero(mask & (output['gate'] != old_gate)))
  arms['D2']['score_diagnostics'] = e1.score_diagnostics(prob, truth, prior)
  return arms


def evaluate_job(segments, candidate, fold, model, decisions, stage2, provider, expected, old, clauses, counters):
  need((candidate, fold) == (old['candidate_id'], old['fold']) and set(old['arms']) == {'D0', 'D1'})
  computed = one_step(segments, candidate, model, decisions, stage2, provider.one_step(candidate, fold), expected['one_step'], counters)
  for group in ('one_step', 'true_move', 'tick_diagnostics'):
    need(computed['D0'][group] == old['arms']['D0'][group], 'E2_D0_SAVED_ONE_STEP_IDENTITY_CONFLICT')
  arms = copy.deepcopy(old['arms'])
  arms['D2'] = computed['D2']
  D1_values = tuple(old['TRAIN']['contexts'][k]['decision'] for k in decision.CONTEXTS)
  same_policy = decisions == D1_values
  if arms['D2']['paired_changes'] is not None:
    arms['D2']['D1_changed_lower_bounds'] = {
      k: changed_lower_bound(arms['D1']['paired_changes'][k], n, exact_same_policy=same_policy) for k, n in arms['D2']['paired_changes'].items()
    }
    for state, transition in arms['D2']['tick_diagnostics']['transitions'].items():
      transition['D1_changed_gate_lower_bound'] = changed_lower_bound(
        arms['D1']['tick_diagnostics']['transitions'][state]['paired_changed_gate_rows'], transition['paired_changed_gate_rows'], exact_same_policy=same_policy
      )
  for horizon in HORIZONS:
    public = expected['rollout'][str(horizon)]
    need(arms['D0']['rollout'][str(horizon)] == public, 'E2_D0_ROLLOUT_REFERENCE_CONFLICT')
    old_error = provider.baseline_error(candidate, fold, horizon)
    row = rollout(
      segments, candidate, model, decisions, stage2, horizon, public['overall'], old_error, arms['D1']['rollout'][str(horizon)], same_policy, counters
    )
    arms['D2']['rollout'][str(horizon)] = row
    if row['status'] == 'NUMERICAL_FAILURE':
      arms['D2']['status'] = 'DEVELOPMENT_OR_ROLLOUT_FAILURE'
    elif row['status'] != 'COMPLETE' and arms['D2']['status'] != 'DEVELOPMENT_OR_ROLLOUT_FAILURE':
      arms['D2']['status'] = 'ROLLOUT_SUPPORT_FAILURE'
  for arm in ('D0', 'D1'):
    need(e1.gates.fold_gate(arms[arm], clauses) == arms[arm]['gate'], 'E2_IMMUTABLE_ARM_ACCEPTANCE_CONFLICT')
  arms['D2']['gate'] = e1.gates.fold_gate(arms['D2'], clauses)
  decision.count(counters, 'D2_acceptance_evaluation_calls')
  decision.count(counters, 'D2_scientific_job_evaluation_calls')
  return {'candidate_id': candidate, 'fold': fold, 'arms': arms, 'paired_metric_differences': metric_differences(arms)}


def validate_stored(value, protocol_sha256, *, head=None):
  need(
    type(value) is dict and value.get('receipt_sha256') == sha(canonical({k: v for k, v in value.items() if k != 'receipt_sha256'})), 'E2_RESULT_SEAL_CONFLICT'
  )
  need(value['schema'] == 'V4_E2_CANONICAL_RESULT_V1' and value['protocol_sha256'] == protocol_sha256)
  need(head is None or value['head'] == head)
  need(tuple((r['candidate_id'], r['fold']) for r in value['jobs']) == decision.JOBS)
  need(value['selected_candidate'] is None and value['selected_policy'] is None and value['holdout'] == 'CLOSED' and value['vehicle_authority'] == 'NONE')
  need(set(value['forbidden_operation_counters']) == set(FORBIDDEN) and all(type(v) is int and v == 0 for v in value['forbidden_operation_counters'].values()))
  need(value['mixed_carrier_openings'] == value['original_D0_threshold_readings'] == 0, 'E2_STORED_FORBIDDEN_COUNTER')
  need(value['original_TRAIN_gate'] == 'NOT_SAVED' and value['original_replica'] == 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED')
  need(value['operation_counters']['TRAIN_numerical_qualification_jobs'] == 32 and value['operation_counters']['D0_TRAIN_reconstruction_calls'] == 32)
  need(value['operation_counters']['D2_context_decision_selection_calls'] == 64 and value['operation_counters']['D2_scientific_job_evaluation_calls'] == 32)
  for row in value['jobs']:
    train = row['TRAIN']
    need(set(row['arms']) == {'D0', 'D1', 'D2'} and set(train['contexts']) == set(decision.CONTEXTS))
    need((train['candidate_id'], train['fold']) == (row['candidate_id'], row['fold']))
    need(type(train['count']) is int and train['count'] > 0 and sum(c['count'] for c in train['contexts'].values()) == train['count'])
    for context in train['contexts'].values():
      need(type(context['decision']) is float and math.isfinite(context['decision']) and 0 <= context['decision'] <= 1)
      need(
        context['witness_verified'] is True
        and set(context['guards']) == {'TRUE_MOVE_TP', 'TRUE_MOVE_SSE', 'TRUE_MOVE_SAE', 'HARMFUL_STATIC'}
        and all(v is True for v in context['guards'].values())
      )
      need(
        all(
          type(context[k]) is int and context[k] >= 0
          for k in ('count', 'positive', 'negative', 'candidate_count', 'feasible_count', 'TRUE_MOVE_TP', 'harmful_static')
        )
      )
      need(context['positive'] > 0 and context['negative'] > 0 and context['count'] == context['positive'] + context['negative'])
      need(context['candidate_count'] >= 2 and 0 < context['feasible_count'] <= context['candidate_count'])
      p, n = context['positive'], context['negative']
      baseline = context['D0_reference']
      need(0 <= context['TRUE_MOVE_TP'] <= p and 0 <= context['harmful_static'] <= n)
      need(type(context['net_exact_hit_gain']) is int and -n <= context['net_exact_hit_gain'] <= p)
      need(all(type(baseline[k]) is int for k in ('TP', 'harmful_static', 'net_exact_hit_gain')))
      need(0 <= baseline['TP'] <= p and 0 <= baseline['harmful_static'] <= n and -n <= baseline['net_exact_hit_gain'] <= p)
      need(all(type(baseline[k]) is float and math.isfinite(baseline[k]) and baseline[k] >= 0 for k in ('TRUE_MOVE_SSE', 'TRUE_MOVE_SAE')))
      need(
        context['TRUE_MOVE_TP'] >= baseline['TP']
        and context['TRUE_MOVE_SSE'] <= baseline['TRUE_MOVE_SSE']
        and context['TRUE_MOVE_SAE'] <= baseline['TRUE_MOVE_SAE']
        and context['harmful_static'] <= baseline['harmful_static']
        and context['net_exact_hit_gain'] >= baseline['net_exact_hit_gain'],
        'E2_STORED_GUARD_CONTRADICTION',
      )

      need(
        all(
          type(context[k]) is float and math.isfinite(context[k]) and context[k] >= 0
          for k in ('continuous_sse', 'continuous_sae', 'TRUE_MOVE_SSE', 'TRUE_MOVE_SAE')
        )
      )
    for arm in row['arms'].values():
      need(arm['status'] in ('EXECUTED_COMPLETE', 'ROLLOUT_SUPPORT_FAILURE', 'DEVELOPMENT_OR_ROLLOUT_FAILURE'))
      need(set(arm['rollout']) == {str(h) for h in HORIZONS})
      for pair in (arm['one_step'], arm['true_move']):
        if pair is None:
          need(arm['status'] == 'DEVELOPMENT_OR_ROLLOUT_FAILURE')
        else:
          e1.stored_pair(pair)
      for roll in arm['rollout'].values():
        need(roll['status'] in ('COMPLETE', 'V4_ROLLOUT_SUPPORT_FAILURE', 'NUMERICAL_FAILURE'))
        for name in ('overall', 'path_moved'):
          if roll[name] is None:
            need(roll['status'] != 'COMPLETE')
          else:
            e1.stored_pair(roll[name])
      gate = arm['gate']
      need(type(gate['pass']) is bool and tuple(r['id'] for r in gate['clauses']) == CLAUSE_IDS)
      need(all(type(r['pass']) is bool and type(r['evaluated']) is bool for r in gate['clauses']))
      need(all(not r['pass'] or r['evaluated'] for r in gate['clauses']), 'E2_UNEVALUATED_CLAUSE_CANNOT_PASS')
      need(gate['failures'] == [r['id'] for r in gate['clauses'] if not r['pass']])
      need(gate['pass'] == (arm['status'] == 'EXECUTED_COMPLETE' and not gate['failures']), 'E2_STORED_GATE_SCHEMA')
  return value


def verify_only(raw, expected_digest, protocol_sha256, *, head=None):
  need(sha(raw) == expected_digest, 'E2_VERIFY_ONLY_DIGEST_CONFLICT')
  validate_stored(json.loads(raw), protocol_sha256, head=head)
  return {'status': 'E2_VERIFY_ONLY_PASS', 'source_rereads': 0, 'inference_calls': 0, 'recompute_calls': 0, 'source_writes': 0}
