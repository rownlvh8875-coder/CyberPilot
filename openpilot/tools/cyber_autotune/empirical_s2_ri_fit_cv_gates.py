"""Exact frozen gates and complete retrospective candidate selection."""
import math

from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m


def ratio(numerator,denominator):
  if not all(type(v) in (float,int) and math.isfinite(v) and v >= 0 for v in (numerator,denominator)):
    raise ValueError('FINITE_NONNEGATIVE_METRIC_REQUIRED')
  return numerator/denominator if denominator else (1. if numerator == 0 else float('inf'))


def population(pop,grid):
  fields = {'rmse','mae','p95'} | ({'exact_hit','within_one_tick'} if grid else set())
  if (set(pop) != {'count','anchor_sha256','comparator_anchor_sha256','candidate','comparator'}
      or type(pop['count']) is not int or pop['count'] < m.MIN_SUPPORT
      or pop['anchor_sha256'] != pop['comparator_anchor_sha256']):
    raise ValueError('IDENTICAL_SUPPORTED_ANCHOR_POPULATION_REQUIRED')
  for side in ('candidate','comparator'):
    if set(pop[side]) != fields:
      raise ValueError('EXACT_FROZEN_METRIC_SET_REQUIRED')
    for k,v in pop[side].items():
      if type(v) is not float or not math.isfinite(v) or v < 0 or (k in ('exact_hit','within_one_tick') and v > 1):
        raise ValueError('VALID_FINITE_METRIC_REQUIRED')


def fold_gate(job):
  if job['status'] != 'PASS':
    return {'pass':False,'failed':['EXECUTION_'+job['status']]}
  if set(job['rollout']) != {str(h) for h in m.HORIZONS}:
    raise ValueError('ALL_FOUR_HORIZONS_REQUIRED')
  failed = []
  population(job['one_step'],True)
  a,b = job['one_step']['candidate'],job['one_step']['comparator']
  for key in ('rmse','mae','p95','exact_hit','within_one_tick'):
    ok = a[key] < b[key] if key == 'rmse' else (a[key] >= b[key] if key in ('exact_hit','within_one_tick') else a[key] <= b[key])
    if not ok:
      failed.append('ONE_STEP_'+key.upper())
  for h in m.HORIZONS:
    pop = job['rollout'][str(h)]
    population(pop,False)
    for key in ('rmse','mae','p95'):
      if pop['candidate'][key] > pop['comparator'][key]:
        failed.append(f'ROLLOUT_{h}_'+key.upper())
  return {'pass':not failed,'failed':failed}


def ranking(pair):
  d,length = m.parameters(pair[0]['candidate_id'])
  rollout = max(ratio(p['candidate']['rmse'],p['comparator']['rmse']) for j in pair for p in j['rollout'].values())
  p95 = max(ratio(j['one_step']['candidate']['p95'],j['one_step']['comparator']['p95']) for j in pair)
  return (rollout,p95,2*length+3,length,d,pair[0]['candidate_id'])


def select(jobs):
  expected = [(c,f) for c in m.CANDIDATES for f in ('FOLD_A','FOLD_B')]
  if [(j['candidate_id'],j['fold']) for j in jobs] != expected:
    raise ValueError('EXACT_32_ORDERED_JOBS_REQUIRED')
  summaries, keys = [], []
  for i,candidate in enumerate(m.CANDIDATES):
    pair = jobs[2*i:2*i+2]
    gates = [fold_gate(j) for j in pair]
    admitted = all(v['pass'] for v in gates)
    key = ranking(pair) if admitted else None
    if key is not None:
      keys.append(key)
    summaries.append({'candidate_id':candidate,'admissible':admitted,'fold_gates':gates,
                      'ranking_key':[('POSITIVE_INFINITY' if v == float('inf') else v) for v in key] if key else None})
  keys.sort()
  return {'status':'S2_RI_RETROSPECTIVE_CV_SELECTED' if keys else 'S2_RI_NO_ADMISSIBLE_CANDIDATE',
          'multiplicity':('S2_RI_MULTIPLE_ADMISSIBLE_CANDIDATES' if len(keys)>1 else
                          'S2_RI_SINGLE_ADMISSIBLE_CANDIDATE' if keys else 'MODEL_SELECTION_FAILED_CLOSED'),
          'selected_candidate':keys[0][-1] if keys else None,'admissible_count':len(keys),
          'inadmissible_count':16-len(keys),'candidates':summaries,
          'final_pooled_refit':'NOT_AUTHORIZED','no_model_admitted_for_future_holdout':True}
