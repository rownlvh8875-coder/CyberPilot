"""Isolated D1 evaluator using frozen V4 math; no source I/O or refitting.

An independently reviewed caller supplies manifest-verified arrays/models only.
Observed future ticks are used by diagnostics, never by the recursive function.
"""

import hashlib
import json
import math

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as decision
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as frozen
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_c_math as descriptive

need = decision.need
HORIZONS = (25, 50, 100, 200)
TRANSITIONS = ('STATIC_HOLD', 'MOVE_ONSET', 'MOVE_TERMINATION', 'MOVE_CONTINUATION')


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
  return hashlib.sha256(raw).hexdigest()


def seal(value):
  return {**value, 'receipt_sha256': sha(canonical(value))}


def count(counters, key, rows=0):
  counters[key] = counters.get(key, 0) + 1
  if rows:
    counters[key + '_rows'] = counters.get(key + '_rows', 0) + rows


def ratio(top, bottom):
  return top / bottom if bottom else None


def score_diagnostics(p, truth, prior):
  decision.probability(p)
  need(truth.dtype == np.bool_ and prior.dtype == np.int64 and truth.shape == prior.shape == p.shape)
  previous = prior != 0
  rows = {}
  for name, mask in (('OVERALL', np.ones(len(p), bool)), ('PREVIOUS_STATIC', ~previous), ('PREVIOUS_MOVE', previous)):
    prob, y = p[mask], truth[mask]
    n, positive = len(prob), int(np.count_nonzero(y))
    mean = math.fsum(map(float, prob)) / n if n else None
    prevalence = ratio(positive, n)
    rows[name] = {
      'n': n,
      'positive': positive,
      'negative': n - positive,
      'auc': descriptive.auc(prob, y),
      'mean_probability': mean,
      'prevalence': prevalence,
      'brier': math.fsum(map(float, (prob - y) ** 2)) / n if n else None,
      'calibration_bias': mean - prevalence if n else None,
    }
  return rows


def score_transfer(train, dev):
  result = {}
  for context in ('OVERALL', 'PREVIOUS_STATIC', 'PREVIOUS_MOVE'):
    result[context] = {}
    for metric in ('auc', 'brier', 'calibration_bias', 'prevalence'):
      old = train[context]['auc']['value'] if metric == 'auc' else train[context][metric]
      new = dev[context]['auc']['value'] if metric == 'auc' else dev[context][metric]
      result[context][metric] = new - old if old is not None and new is not None else None
  return result


def integrated(x, current, model, decisions, stage2, counters, *, p_move=None):
  need(x.dtype == np.float64 and x.ndim == 2 and current.dtype == np.int64 and current.shape == (len(x),))
  if p_move is None:
    p = frozen.probability(x, model)
    count(counters, 'stage1_inference_calls', len(x))
  else:
    decision.probability(p_move)
    need(p_move.shape == current.shape)
    p = p_move
  prior = x[:, -3].astype(np.int64)
  need(np.array_equal(prior, x[:, -3]), 'E_PRIOR_DELTA_CONFLICT')
  gate = decision.gate(p, prior, decisions)
  count(counters, 'context_decision_application_calls', len(x))
  delta = np.zeros(len(x), np.float64)
  projected = current.copy()
  if np.any(gate):
    delta[gate] = frozen.m.predict_delta(np.ascontiguousarray(x[gate]), stage2)
    count(counters, 'stage2_inference_calls', int(np.count_nonzero(gate)))
    projected[gate] = frozen.m.project(current[gate].astype(np.float64) + delta[gate])
    count(counters, 'tick_projection_calls', int(np.count_nonzero(gate)))
  return {'delta': delta, 'projected': projected, 'p_move': p, 'gate': gate}


def recursive(initial, command, speed, candidate, model, decisions, stage2, horizon, counters):
  """Exact frozen full-state recursion, changing only context decision lookup."""
  _, length = frozen.m.parameters(candidate)
  n = len(initial)
  need(
    horizon in HORIZONS
    and initial.dtype == np.int64
    and initial.shape == (n, length + 1)
    and command.dtype == np.float64
    and command.shape == (n, length + horizon - 1)
    and speed.dtype == np.float64
    and speed.shape == (n, horizon),
    'E_ROLLOUT_CONTEXT_CONFLICT',
  )
  frozen.m.finite(initial, command, speed)
  current = initial[:, -1].copy()
  past = np.diff(initial, axis=1)
  path, gate_path, context = np.empty((n, horizon + 1), np.int64), np.empty((n, horizon), bool), np.empty((n, horizon), bool)
  path[:, 0] = current
  count(counters, 'recursive_chunk_calls', n)
  for step in range(horizon):
    x = np.ascontiguousarray(np.column_stack((np.ones(n), command[:, step : step + length], past, current, speed[:, step])), dtype=np.float64)
    context[:, step] = past[:, -1] != 0
    output = integrated(x, current, model, decisions, stage2, counters)
    new = output['projected']
    path[:, step + 1], gate_path[:, step] = new, output['gate']
    past[:, :-1] = past[:, 1:]
    past[:, -1] = new - current
    current = new
  return path, gate_path, context


def path_moved(observed):
  need(observed.dtype == np.int64 and observed.ndim == 2)
  return np.any(observed != observed[:, :1], axis=1)


def tick_diagnostics(current, target, prior, result):
  truth, previous = target != current, prior != 0
  gate, projected, delta = (result[k] for k in ('gate', 'projected', 'delta'))
  realized, hit = projected != current, projected == target
  false_move = ~truth & gate
  static_loss, move_gain = int(np.count_nonzero(~truth & ~hit)), int(np.count_nonzero(truth & hit))
  baseline_hits, candidate_hits = int(np.count_nonzero(~truth)), int(np.count_nonzero(hit))
  fp = int(np.count_nonzero(false_move))
  converted, harmful = int(np.count_nonzero(false_move & ~realized)), int(np.count_nonzero(~truth & realized))
  need(candidate_hits == baseline_hits - static_loss + move_gain and fp == converted + harmful, 'E_EXACT_HIT_IDENTITY_CONFLICT')
  need(not np.any(~gate & realized), 'E_STATIC_GATE_MOVEMENT_CONFLICT')
  populations = (~previous & ~truth, ~previous & truth, previous & ~truth, previous & truth)
  transitions = {}
  for label, mask in zip(TRANSITIONS, populations, strict=True):
    n, moved = int(np.count_nonzero(mask)), int(np.count_nonzero(mask & gate))
    tp_mask = mask & truth & gate
    transitions[label] = {
      'n': n,
      'move_gate': moved,
      'static_gate': n - moved,
      'move_gate_rate': ratio(moved, n),
      'realized_movement': int(np.count_nonzero(mask & realized)),
      'exact_hits': int(np.count_nonzero(mask & hit)),
      'harmful_movement': int(np.count_nonzero(mask & ~truth & realized)),
      'FP_projected_HOLD': int(np.count_nonzero(mask & false_move & ~realized)),
      'gate_TP_magnitude_residual': frozen.m.metrics(delta[tp_mask] - (target[tp_mask] - current[tp_mask])) if int(np.count_nonzero(tp_mask)) >= 201 else None,
      'gate_TP_projected_step_residual': frozen.m.metrics((projected[tp_mask] - current[tp_mask]) - (target[tp_mask] - current[tp_mask]))
      if int(np.count_nonzero(tp_mask)) >= 201
      else None,
      'gate_TP_magnitude_support': int(np.count_nonzero(tp_mask)),
    }
  return {
    'transitions': transitions,
    'confusion': {
      name: descriptive.confusion(truth[mask], gate[mask])
      for name, mask in (('OVERALL', np.ones(len(truth), bool)), ('PREVIOUS_STATIC', ~previous), ('PREVIOUS_MOVE', previous))
    },
    'gate_FP': fp,
    'FP_projected_HOLD': converted,
    'harmful_false_movement': harmful,
    'exact_hit': {
      'candidate_hits': candidate_hits,
      'hold_last_hits': baseline_hits,
      'static_hit_loss': static_loss,
      'move_hit_gain': move_gain,
      'net_delta': move_gain - static_loss,
    },
  }


def one_step(segments, candidate, model, decisions, stage2, saved, expected, counters):
  _, anchor, x, current, target = data.design(segments, candidate)
  current, target = current.astype(np.int64), target.astype(np.int64)
  actual, prior = target - current, x[:, -3].astype(np.int64)
  truth = actual != 0
  need(anchor == expected['anchor_sha256'] and len(x) == expected['count'], 'E_DEV_ANCHOR_CONFLICT')
  need(np.array_equal(saved['true_move'], truth) and np.array_equal(saved['prior_delta_tick'], prior), 'E_DEV_ROW_ALIGNMENT_CONFLICT')
  prob = frozen.probability(x, model)
  count(counters, 'stage1_inference_calls', len(x))
  need(np.array_equal(prob, saved['p_move']), 'E_FROZEN_STAGE1_SCORE_NOT_BYTE_EQUIVALENT')
  numerical_failure, output = None, None
  try:
    output = integrated(x, current, model, decisions, stage2, counters, p_move=prob)
  except ValueError as exc:
    if not str(exc).startswith(('CANDIDATE_FOLD_NUMERICAL_FAILURE', 'HURDLE_NUMERICAL_FAILURE')):
      raise
    numerical_failure = str(exc)
  old_gate = saved['predicted_gate']
  old_delta, old_projected = saved['integrated_delta'], saved['projected_next_tick'].astype(np.int64)
  need(not np.any(~old_gate & (old_delta != 0)) and not np.any(~old_gate & (old_projected != current)), 'E_D0_STATIC_CONFLICT')
  if np.any(old_gate):
    reproduction = frozen.m.predict_delta(np.ascontiguousarray(x[old_gate]), stage2)
    count(counters, 'D0_stage2_equivalence_calls', int(np.count_nonzero(old_gate)))
    need(np.array_equal(reproduction, old_delta[old_gate]), 'E_D0_STAGE2_EQUIVALENCE_CONFLICT')
    need(np.array_equal(frozen.m.project(current[old_gate].astype(np.float64) + reproduction), old_projected[old_gate]), 'E_D0_PROJECTION_CONFLICT')
    count(counters, 'D0_projection_equivalence_calls', int(np.count_nonzero(old_gate)))
  need(np.array_equal(saved['candidate_error'], old_delta - actual), 'E_D0_SAVED_ERROR_CONFLICT')
  arms = {}
  for name, row in (('D0', {'gate': old_gate, 'delta': old_delta, 'projected': old_projected}), ('D1', output)):
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
      'one_step': data.pair(error, baseline, anchor, row['projected'], target, current),
      'true_move': data.pair(error[truth], baseline[truth], data.subset_sha(anchor, truth), row['projected'][truth], target[truth], current[truth]),
      'tick_diagnostics': tick_diagnostics(current, target, prior, row),
      'rollout': {},
    }
  arms['D1']['paired_changes'] = (
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
    for label, mask in zip(TRANSITIONS, ((prior == 0) & ~truth, (prior == 0) & truth, (prior != 0) & ~truth, (prior != 0) & truth), strict=True):
      arms['D1']['tick_diagnostics']['transitions'][label]['paired_changed_gate_rows'] = int(np.count_nonzero(mask & (output['gate'] != old_gate)))
  arms['D1']['score_diagnostics'] = score_diagnostics(prob, truth, prior)
  return arms


def drift_chunk(initial, observed, path, gate, context, length):
  """Private descriptive associations only; no intervention or causal share."""
  horizon = gate.shape[1]
  movement, truth = np.diff(path, axis=1) != 0, np.diff(observed, axis=1) != 0
  truth_context = np.column_stack((initial[:, -1] != initial[:, -2], truth[:, :-1]))
  need(np.array_equal(context[:, 1:], movement[:, :-1]), 'E_NEXT_CONTEXT_LAG_CONFLICT')
  predicted_history = np.column_stack((initial, path[:, 1:]))
  observed_history = np.column_stack((initial, observed[:, 1:]))
  events = {
    'gate_error': gate != truth,
    'movement_mismatch': movement != truth,
    'context_mismatch': context != truth_context,
    'tick_mismatch': path[:, 1:] != observed[:, 1:],
  }
  out = {key: np.count_nonzero(value, axis=0) for key, value in events.items()}
  out['full_history_input_mismatch'] = np.array(
    [
      np.count_nonzero(np.any(predicted_history[:, step : step + length + 1] != observed_history[:, step : step + length + 1], axis=1))
      for step in range(horizon)
    ],
    np.int64,
  )
  out['gate_MOVE'] = np.count_nonzero(gate, axis=0)
  out['gate_MOVE_realized_HOLD'] = np.count_nonzero(gate & ~movement, axis=0)
  out['next_context_mismatch_after_movement_mismatch'] = np.r_[
    np.count_nonzero((context[:, 1:] != truth_context[:, 1:]) & events['movement_mismatch'][:, :-1], axis=0), 0
  ]
  for key, value in events.items():
    first = np.where(np.any(value, axis=1), np.argmax(value, axis=1), horizon)
    out['first_' + key] = np.bincount(first, minlength=horizon + 1)
  return out, ~np.any(events['gate_error'], axis=1), ~np.any(events['movement_mismatch'], axis=1)


def subset_support(error, baseline, mask):
  n = int(np.count_nonzero(mask))
  return {
    'count': n,
    'support': 'FULL' if n >= 201 else 'SMALL' if n else 'EMPTY',
    'candidate': frozen.m.metrics(error[mask]) if n >= 201 else None,
    'hold_last': frozen.m.metrics(baseline[mask]) if n >= 201 else None,
    'causal_interpretation': 'DESCRIPTIVE_SELECTION_NOT_STAGE2_ONLY_CAUSAL_PROOF',
  }


def rollout(segments, candidate, model, decisions, stage2, horizon, saved, expected, counters):
  blocks, anchor, n = data.binding(segments, candidate, horizon)
  need(anchor == expected['anchor_sha256'] and n == expected['count'], 'E_ROLLOUT_ANCHOR_CONFLICT')
  need(saved['projected_path'].shape == (n, horizon + 1) and saved['predicted_gate_path'].shape == (n, horizon), 'E_D0_PATH_SHAPE_CONFLICT')
  delay, length = frozen.m.parameters(candidate)
  endpoints, moved_all, old_errors, baseline_all = [], [], [], []
  drift, gate_perfect, movement_perfect = {}, [], []
  offset, numerical_failure, changed_paths = 0, None, 0
  for segment, indices in blocks:
    for start in range(0, len(indices), frozen.m.CHUNK):
      ix = indices[start : start + frozen.m.CHUNK]
      initial = segment['tick'][ix[:, None] + np.arange(-length, 1)].astype(np.int64)
      command = segment['command'][ix[:, None] + np.arange(-delay - length + 1, horizon - delay)]
      speed = segment['speed'][ix[:, None] + np.arange(horizon)]
      path = None
      if numerical_failure is None:
        try:
          path, gate, context = recursive(initial, command, speed, candidate, model, decisions, stage2, horizon, counters)
        except ValueError as exc:
          if not str(exc).startswith(('CANDIDATE_FOLD_NUMERICAL_FAILURE', 'HURDLE_NUMERICAL_FAILURE', 'V4_STAGE1_NUMERICAL_FAILURE')):
            raise
          numerical_failure = str(exc)
      # Truth becomes visible only to this diagnostic, never to recursive().
      observed = segment['tick'][ix[:, None] + np.arange(horizon + 1)].astype(np.int64)
      old = saved['projected_path'][offset : offset + len(ix)].astype(np.int64)
      old_gate = saved['predicted_gate_path'][offset : offset + len(ix)]
      need(np.array_equal(old[:, 0], initial[:, -1]) and not np.any(~old_gate & (np.diff(old, axis=1) != 0)), 'E_D0_ROLLOUT_CONFLICT')
      old_errors.append((old[:, -1] - observed[:, -1]).astype(np.float64))
      baseline_all.append((observed[:, 0] - observed[:, -1]).astype(np.float64))
      moved_all.append(path_moved(observed))
      offset += len(ix)
      if path is None:
        continue  # Entire D1 horizon is nonpass; never drop failed rows from metrics.
      endpoints.append((path[:, -1] - observed[:, -1]).astype(np.float64))
      changed_paths += int(np.count_nonzero(np.any(path != old, axis=1)))
      chunk_drift, perfect_gate, perfect_movement = drift_chunk(initial, observed, path, gate, context, length)
      gate_perfect.append(perfect_gate)
      movement_perfect.append(perfect_movement)
      for key, value in chunk_drift.items():
        drift[key] = drift.get(key, np.zeros_like(value)) + value
  need(offset == n, 'E_ROLLOUT_ROW_COUNT_CONFLICT')
  old_error, baseline, moved = map(np.concatenate, (old_errors, baseline_all, moved_all))
  need(np.array_equal(old_error, saved['candidate_error']), 'E_D0_ROLLOUT_ERROR_CONFLICT')
  results = {}
  arm_errors = [('D0', old_error)]
  if numerical_failure is None:
    arm_errors.append(('D1', np.concatenate(endpoints)))
  for name, e in arm_errors:
    results[name] = {
      'overall': data.pair(e, baseline, anchor) if n >= 201 else None,
      'path_moved': data.pair(e[moved], baseline[moved], data.subset_sha(anchor, moved)) if int(np.count_nonzero(moved)) >= 201 else None,
      'path_moved_count': int(np.count_nonzero(moved)),
      'status': 'COMPLETE' if n >= 201 and int(np.count_nonzero(moved)) >= 201 else 'V4_ROLLOUT_SUPPORT_FAILURE',
    }
  if numerical_failure is not None:
    results['D1'] = {
      'overall': None,
      'path_moved': None,
      'status': 'NUMERICAL_FAILURE',
      'failure': numerical_failure,
      'state_drift': None,
      'partial_diagnostics_not_published': True,
    }
  else:
    results['D1']['state_drift'] = {key: v.tolist() for key, v in drift.items()}
    error = np.concatenate(endpoints)
    results['D1']['moved_gate_perfect'] = subset_support(error, baseline, moved & np.concatenate(gate_perfect))
    results['D1']['moved_projected_movement_perfect'] = subset_support(error, baseline, moved & np.concatenate(movement_perfect))
    results['D1']['paired_changed_endpoint_rows'] = int(np.count_nonzero(np.concatenate(endpoints) != old_error))
    results['D1']['paired_changed_path_moved_endpoint_rows'] = int(np.count_nonzero((np.concatenate(endpoints) != old_error) & moved))
    results['D1']['paired_changed_path_rows'] = changed_paths
  return results


def evaluate_job(segments, candidate, fold, model, decisions, stage2, provider, expected, clauses, counters):
  """provider supplies only authenticated D0 saved results for the same job."""
  arms = one_step(segments, candidate, model, decisions, stage2, provider.one_step(candidate, fold), expected['one_step'], counters)
  need(arms['D0']['one_step'] == expected['one_step'] and arms['D0']['true_move'] == expected['true_move'], 'E_D0_ONE_STEP_METRIC_CONFLICT')
  for horizon in HORIZONS:
    saved = provider.rollout(candidate, fold, horizon)
    results = rollout(segments, candidate, model, decisions, stage2, horizon, saved, expected['rollout'][str(horizon)]['overall'], counters)
    for name in arms:
      arms[name]['rollout'][str(horizon)] = results[name]
      if name == 'D0':
        need(results[name] == expected['rollout'][str(horizon)], 'E_D0_FROZEN_ROLLOUT_METRIC_CONFLICT')
      if results[name]['status'] == 'NUMERICAL_FAILURE':
        arms[name]['status'] = 'DEVELOPMENT_OR_ROLLOUT_FAILURE'
      elif results[name]['status'] != 'COMPLETE' and arms[name]['status'] != 'DEVELOPMENT_OR_ROLLOUT_FAILURE':
        arms[name]['status'] = 'ROLLOUT_SUPPORT_FAILURE'

  for name in arms:
    arms[name]['gate'] = gates.fold_gate(arms[name], clauses)
    count(counters, 'frozen_acceptance_evaluation_calls')
  return {'candidate_id': candidate, 'fold': fold, 'arms': arms}


FORBIDDEN_OPERATIONS = (
  'stage1_model_refit',
  'stage2_model_refit',
  'normalizer_refit',
  'calibration_fit',
  'additional_policy_search',
  'posthoc_threshold_tuning',
  'additional_candidate_generation',
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


def stored_pair(pair):
  need(
    type(pair) is dict and type(pair['count']) is int and pair['count'] >= 201 and pair['anchor_sha256'] == pair['comparator_anchor_sha256'],
    'E_STORED_METRIC_SUPPORT',
  )
  for group in ('candidate', 'comparator'):
    need(
      all(type(pair[group][m]) in (int, float) and math.isfinite(pair[group][m]) and pair[group][m] >= 0 for m in ('rmse', 'mae', 'p95')),
      'E_STORED_METRIC_SCHEMA',
    )


def validate_stored(value, protocol_sha256, *, head=None):
  need(
    type(value) is dict and value.get('receipt_sha256') == sha(canonical({k: v for k, v in value.items() if k != 'receipt_sha256'})), 'E_STORED_SEAL_CONFLICT'
  )
  need(value.get('schema') == 'V4_E_CANONICAL_RESULT_V1' and value.get('protocol_sha256') == protocol_sha256, 'E_RESUME_BINDING_CONFLICT')
  need(head is None or value.get('head') == head, 'E_RESUME_HEAD_CONFLICT')
  need(tuple((r['candidate_id'], r['fold']) for r in value['jobs']) == decision.JOBS, 'E_STORED_32_JOBS_REQUIRED')
  need(
    value.get('selected_candidate') is None
    and value.get('selected_policy') is None
    and value.get('holdout') == 'CLOSED'
    and value.get('vehicle_authority') == 'NONE',
    'E_STORED_AUTHORITY_CONFLICT',
  )
  need(
    set(value['forbidden_operation_counters']) == set(FORBIDDEN_OPERATIONS)
    and all(type(v) is int and v == 0 for v in value['forbidden_operation_counters'].values())
    and value['mixed_carrier_openings'] == value['original_D0_threshold_readings'] == 0,
    'E_STORED_FORBIDDEN_COUNTER_CONFLICT',
  )
  need(
    value['operation_counters']['TRAIN_context_decision_selection_calls'] == 64 and value['operation_counters']['E_scientific_job_evaluation_calls'] == 32,
    'E_STORED_EXECUTION_INCOMPLETE',
  )
  for row in value['jobs']:
    train = row['TRAIN']
    need(
      (train['candidate_id'], train['fold']) == (row['candidate_id'], row['fold'])
      and type(train['count']) is int
      and train['count'] > 0
      and set(train['contexts']) == {'PREVIOUS_STATIC', 'PREVIOUS_MOVE'},
      'E_STORED_TRAIN_SCHEMA',
    )
    for context in train['contexts'].values():
      need(
        type(context['decision']) is float
        and math.isfinite(context['decision'])
        and 0 <= context['decision'] <= 1
        and all(type(context[k]) is int and context[k] >= 0 for k in ('BA_NUM', 'TP', 'TN', 'positive', 'negative', 'count', 'candidate_count'))
        and context['positive'] > 0
        and context['negative'] > 0
        and context['candidate_count'] >= 2
        and context['positive'] + context['negative'] == context['count'],
        'E_STORED_TRAIN_CONTEXT_SCHEMA',
      )
    need(sum(c['count'] for c in train['contexts'].values()) == train['count'])
    need(set(row['arms']) == {'D0', 'D1'})
    for arm in row['arms'].values():
      need(arm['status'] in ('EXECUTED_COMPLETE', 'ROLLOUT_SUPPORT_FAILURE', 'DEVELOPMENT_OR_ROLLOUT_FAILURE'))
      for group in ('one_step', 'true_move'):
        if arm[group] is not None:
          stored_pair(arm[group])
        else:
          need(arm['status'] == 'DEVELOPMENT_OR_ROLLOUT_FAILURE', 'E_STORED_MISSING_ONE_STEP')
      need(set(arm['rollout']) == {str(h) for h in HORIZONS}, 'E_STORED_HORIZONS_INCOMPLETE')
      for roll in arm['rollout'].values():
        need(roll['status'] in ('COMPLETE', 'V4_ROLLOUT_SUPPORT_FAILURE', 'NUMERICAL_FAILURE'))
        for group in ('overall', 'path_moved'):
          if roll[group] is not None:
            stored_pair(roll[group])
          else:
            need(roll['status'] != 'COMPLETE', 'E_STORED_MISSING_ROLLOUT')
      gate = arm['gate']
      need(type(gate['pass']) is bool and len(gate['clauses']) == 32 and len({r['id'] for r in gate['clauses']}) == 32)
      need(all(type(r['pass']) is bool and type(r['evaluated']) is bool for r in gate['clauses']))
      need(
        gate['failures'] == [r['id'] for r in gate['clauses'] if not r['pass']]
        and gate['pass'] == (arm['status'] == 'EXECUTED_COMPLETE' and not gate['failures']),
        'E_STORED_GATE_SCHEMA',
      )
  return value


def verify_only(raw, expected_digest, protocol_sha256, *, head=None):
  need(sha(raw) == expected_digest, 'E_RESUME_DIGEST_CONFLICT')
  validate_stored(json.loads(raw), protocol_sha256, head=head)
  return {'status': 'E_VERIFY_ONLY_PASS', 'source_rereads': 0, 'inference_calls': 0, 'recompute_calls': 0, 'source_writes': 0}
