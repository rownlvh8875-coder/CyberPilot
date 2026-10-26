"""Frozen 32-clause gate and retrospective-only candidate selection."""

import math
import operator
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m

OPS = {'<': operator.lt, '<=': operator.le, '>=': operator.ge}


def fold_gate(job, clauses):
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_store as store
  from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
  from openpilot.tools.cyber_autotune import empirical_plant_policy as p

  frozen = read.read_json(p.PUBLIC / 'empirical-hurdle-acceptance-gate-v1.json')
  if frozen['receipt_sha256'] != store.PINS['acceptance-gate'] or clauses != frozen['clauses'] or len(clauses) != 32:
    raise ValueError('EXACT_32_GATE_CLAUSES_REQUIRED')
  checks = []
  for clause in clauses:
    population = clause['population']
    if population == 'ALL_ONE_STEP':
      value = job.get('one_step')
    elif population == 'TRUE_MOVE_ONE_STEP_INTEGRATED':
      value = job.get('true_move')
    else:
      group = 'overall' if population == 'OVERALL_ROLLOUT' else 'path_moved'
      value = job.get('rollout', {}).get(str(clause['horizon_steps']), {}).get(group)
    passed = False
    if value is not None:
      if value['anchor_sha256'] != value['comparator_anchor_sha256']:
        raise ValueError('HURDLE_COMPARATOR_ANCHOR_CONFLICT')
      metric = clause['metric'].lower()
      left, right = value['candidate'][metric], value['comparator'][metric]
      if any(not math.isfinite(v) or v < 0 for v in (left, right)):
        raise ValueError('HURDLE_INVALID_METRIC')
      if metric in ('exact_hit', 'within_one_tick') and max(left, right) > 1:
        raise ValueError('HURDLE_INVALID_GRID_METRIC')
      passed = value['count'] >= m.SUPPORT and OPS[clause['operator']](left, right)
    checks.append({'id': clause['id'], 'pass': bool(passed), 'evaluated': value is not None})
  return {
    'pass': job['status'] == 'EXECUTED_COMPLETE' and all(c['pass'] for c in checks),
    'clauses': checks,
    'failures': [c['id'] for c in checks if not c['pass']],
  }


def ratio(numerator, denominator):
  if any(not math.isfinite(v) or v < 0 for v in (numerator, denominator)):
    raise ValueError('HURDLE_INVALID_SELECTION_METRIC')
  if denominator == 0:
    return 1.0 if numerator == 0 else math.inf
  result = float(numerator / denominator)
  if not math.isfinite(result):
    raise ValueError('HURDLE_INVALID_SELECTION_RATIO')
  return result


def selection_key(candidate, jobs):
  d, length = m.parameters(candidate)

  def worst(group):
    return max(ratio(j['rollout'][str(h)][group]['candidate']['rmse'], j['rollout'][str(h)][group]['comparator']['rmse']) for j in jobs for h in m.HORIZONS)

  return (
    worst('path_moved'),
    worst('overall'),
    max(ratio(j['one_step']['candidate']['p95'], j['one_step']['comparator']['p95']) for j in jobs),
    2 * (2 * length + 3),
    length,
    d,
    candidate,
  )


def select(jobs, clauses):
  expected = [(c, f) for c in m.CANDIDATES for f in ('FOLD_A', 'FOLD_B')]
  if [(j['candidate_id'], j['fold']) for j in jobs] != expected:
    raise ValueError('EXACT_32_ORDERED_HURDLE_JOBS_REQUIRED')
  ranking = []
  for number, candidate in enumerate(m.CANDIDATES):
    pair = jobs[2 * number : 2 * number + 2]
    for job in pair:
      if fold_gate(job, clauses) != job['gate']:
        raise ValueError('HURDLE_GATE_RECEIPT_CONFLICT')
    if all(j['gate']['pass'] for j in pair):
      ranking.append((selection_key(candidate, pair), candidate))
  ranking.sort()
  count = len(ranking)
  return {
    'admissible_count': count,
    'selected_candidate': ranking[0][1] if ranking else None,
    'status': 'HURDLE_RETROSPECTIVE_CV_SELECTED' if count else 'HURDLE_NO_ADMISSIBLE_CANDIDATE',
    'states': (
      ['HURDLE_SINGLE_ADMISSIBLE_CANDIDATE' if count == 1 else 'HURDLE_MULTIPLE_ADMISSIBLE_CANDIDATES', 'HURDLE_RETROSPECTIVE_CV_SELECTED']
      if count
      else ['HURDLE_NO_ADMISSIBLE_CANDIDATE', 'MODEL_SELECTION_FAILED_CLOSED']
    ),
    'ranking': [{'candidate_id': candidate, 'keys': ['POSITIVE_INFINITY' if v == math.inf else v for v in key]} for key, candidate in ranking],
    'interpretation': 'RETROSPECTIVE_CONFIGURATION_ONLY',
    'pooled_refit': False,
    'model_admission': 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
    'holdout': 'CLOSED',
    'opening_count': 0,
    'vehicle_authority': 'NONE',
  }
