"""Deterministic descriptions of stored evidence. No model or execution imports."""
import numpy as np

CHUNK = 512
CONFLICT = 'FAILURE_ATTRIBUTION_V2_INPUT_CONFLICT'


def require(value):
  if not value:
    raise ValueError(CONFLICT)


def rate(count, population):
  return count/population if population else None


def finite(values):
  x = np.ascontiguousarray(values, dtype=np.float64)
  require(x.ndim == 1 and bool(np.isfinite(x).all()))
  return x


def metrics(error):
  e = finite(error)
  n = len(e)
  if not n:
    return {'count': 0, 'sae': None, 'sse': None, 'rmse': None, 'mae': None, 'p95': None}
  absolute = np.abs(e)
  sae, sse = float(np.sum(absolute, dtype=np.float64)), float(np.sum(e*e, dtype=np.float64))
  require(np.isfinite(sae) and np.isfinite(sse))
  return {'count': n, 'sae': sae, 'sse': sse, 'rmse': float(np.sqrt(sse/n)), 'mae': sae/n,
              'p95': float(np.percentile(absolute, 95, method='linear'))}


def distribution(values):
  x = finite(values)
  if not len(x):
    return {'count': 0, 'minimum': None, 'median': None, 'p75': None, 'p90': None, 'p95': None, 'p99': None, 'maximum': None, 'mean': None}
  q = np.percentile(x, [50, 75, 90, 95, 99], method='linear')
  return {'count': len(x), 'minimum': float(np.min(x)), 'median': float(q[0]), 'p75': float(q[1]),
              'p90': float(q[2]), 'p95': float(q[3]), 'p99': float(q[4]), 'maximum': float(np.max(x)), 'mean': float(np.mean(x))}


def step_distribution(values, population):
  x = values[values > 0]
  return {'population':population, 'event_count':len(x), 'event_rate':rate(len(x), population),
          'no_event_count':population-len(x), 'no_event_rate':rate(population-len(x), population),
          'steps':distribution(x)}


def paired(error, hold_error, mask, projected=None, target=None, hold=None):
  c, h = metrics(error[mask]), metrics(hold_error[mask])
  n = c['count']
  out = {'count':n, 'candidate':c, 'hold_last':h,
         'delta_sae':c['sae']-h['sae'] if n else None, 'delta_sse':c['sse']-h['sse'] if n else None}
  if projected is not None:
    for name, pred in [('candidate_grid', projected), ('hold_last_grid', hold)]:
      difference = pred[mask]-target[mask]
      exact, within = int(np.count_nonzero(difference == 0)), int(np.count_nonzero(np.abs(difference) <= 1))
      out[name] = {'exact_count': exact, 'exact_hit_rate': rate(exact, n),
                       'within_one_tick_count': within, 'within_one_tick_rate': rate(within, n)}
    out['exact_hit_delta'] = (out['candidate_grid']['exact_hit_rate']-out['hold_last_grid']['exact_hit_rate']) if n else None
  return out


def confusion(actual, projected, mask):
  n = int(np.count_nonzero(mask))
  masks = {'STATIC_CORRECT_HOLD':~actual & ~projected, 'STATIC_FALSE_MOVE':~actual & projected,
           'MOVE_MISSED':actual & ~projected, 'MOVE_DETECTED':actual & projected}
  counts = {k:int(np.count_nonzero(v & mask)) for k,v in masks.items()}
  require(sum(counts.values()) == n)
  return {'count':n, 'counts':counts, 'rates':{k:rate(v,n) for k,v in counts.items()}}


def signs(actual, projected, mask):
  move = mask & (actual != 0)
  n = int(np.count_nonzero(move))
  counts = {'SIGN_CORRECT':int(np.count_nonzero(move & (projected != 0) & (np.sign(actual)==np.sign(projected)))),
            'SIGN_WRONG':int(np.count_nonzero(move & (projected != 0) & (np.sign(actual)!=np.sign(projected)))),
            'PREDICTED_ZERO':int(np.count_nonzero(move & (projected == 0)))}
  require(sum(counts.values()) == n)
  return {'count':n, 'counts':counts, 'rates':{k:rate(v,n) for k,v in counts.items()},
          'detected_sign_accuracy':rate(counts['SIGN_CORRECT'], n-counts['PREDICTED_ZERO']),
          'miss_rate':rate(counts['PREDICTED_ZERO'], n)}


def contexts(a):
  codes = a['speed_bin_code']
  require(bool(np.isin(codes, [1, 2, 3]).all()))
  return {'LOW':codes==1, 'MEDIUM':codes==2, 'HIGH':codes==3,
          'RAIL':a['rail'], 'NON_RAIL':~a['rail'],
          'PRIOR_STATIC':a['prior_delta_tick']==0, 'PRIOR_MOVING':a['prior_delta_tick']!=0}


def one_step(a):
  current, target, delta = a['current_tick'], a['target_next_tick'], a['actual_delta_tick']
  prediction, projected = a['prediction'], a['projected']
  error, hold_error = a['error'], a['comparator_error']
  n = len(current)
  require(all(len(v)==n for v in a.values()))
  require(np.array_equal(target-current, delta))
  require(np.array_equal(a['hold_last_next_tick'], current))
  require(np.array_equal(error, prediction-delta))
  require(np.array_equal(hold_error, -delta.astype(np.float64)))
  for x in (prediction, error, hold_error):
    finite(x)
  static, move = delta==0, delta!=0
  pred_delta = projected-current
  predicted_move = pred_delta!=0
  all_rows = np.ones(n, dtype=bool)
  classes = {'ALL':all_rows, 'STATIC':static, 'MOVE':move,
             'MOVE_POSITIVE':delta>0, 'MOVE_NEGATIVE':delta<0,
             'ONE_TICK_MOVE':np.abs(delta)==1, 'MULTI_TICK_MOVE':np.abs(delta)>=2}
  require(np.array_equal(classes['MOVE_POSITIVE'] | classes['MOVE_NEGATIVE'], move))
  require(np.array_equal(classes['ONE_TICK_MOVE'] | classes['MULTI_TICK_MOVE'], move))
  def describe(mask):
    return paired(error, hold_error, mask, projected, target, current)
  summaries = {k:describe(v) for k,v in classes.items()}
  # Verify HOLD_LAST static behavior using real buffers, not fabricated perfect metrics.
  require(bool((hold_error[static]==0).all()) and bool((current[static]==target[static]).all()))
  c = confusion(move, predicted_move, all_rows)
  half = static & (np.abs(prediction)==0.5)
  boundary = {'static_count':int(static.sum()), 'less_than_half_count':int(np.count_nonzero(static & (np.abs(prediction)<0.5))),
              'exact_half_count':int(half.sum()), 'greater_than_half_count':int(np.count_nonzero(static & (np.abs(prediction)>0.5))),
              'half_tick_held':int(np.count_nonzero(half & ~predicted_move)),
              'half_tick_moved':int(np.count_nonzero(half & predicted_move)),
              'half_tick_even_current':int(np.count_nonzero(half & (current%2==0))),
              'half_tick_odd_current':int(np.count_nonzero(half & (current%2!=0))),
              'static_absolute_continuous_delta':distribution(np.abs(prediction[static])),
              'threshold_origin':'FROZEN_DIRECT_HALF_TO_EVEN_PROJECTION_BOUNDARY',
              'near_half_epsilon':None}
  false = static & predicted_move
  ctx = contexts(a)
  context = {}
  for name, mask in ctx.items():
    size = int(mask.sum())
    nc = confusion(move, predicted_move, mask)
    ns, nm = int(np.count_nonzero(mask & static)), int(np.count_nonzero(mask & move))
    context[name] = {'metrics':describe(mask), 'static_fraction':rate(ns,size), 'confusion':nc,
                     'static_false_move_rate':rate(nc['counts']['STATIC_FALSE_MOVE'],ns),
                     'move_miss_rate':rate(nc['counts']['MOVE_MISSED'],nm),
                     'STATIC':describe(mask & static), 'MOVE':describe(mask & move)}
  both = move & (a['prior_delta_tick']!=0)
  same = np.sign(delta)==np.sign(a['prior_delta_tick'])
  for name, mask in [('SAME_DIRECTION', both & same), ('REVERSAL', both & ~same)]:
    context[name] = {'metrics':describe(mask), 'sign':signs(delta,pred_delta,mask)}
  accounting = {'counts_exact':True, 'float_reduction':'ORIGINAL_ANCHOR_ORDER_CONTIGUOUS_FLOAT64_PER_CLASS',
                'p95_additive':False, 'partition_sum_minus_direct_all':{}}
  for side in ('candidate','hold_last'):
    accounting['partition_sum_minus_direct_all'][side] = {}
    for metric in ('sae','sse'):
      partition = sum(summaries[x][side][metric] or 0.0 for x in ('STATIC','MOVE'))
      accounting['partition_sum_minus_direct_all'][side][metric] = partition-summaries['ALL'][side][metric] if n else None
  pattern = bool(summaries['MOVE']['count'] and summaries['STATIC']['count']
                 and summaries['MOVE']['delta_sse']<0 and summaries['STATIC']['delta_sae']>0
                 and summaries['STATIC']['candidate_grid']['exact_hit_rate']<summaries['STATIC']['hold_last_grid']['exact_hit_rate'])
  result = {'count':n, 'static_fraction':rate(int(static.sum()),n), 'move_fraction':rate(int(move.sum()),n),
            'classes':summaries, 'confusion':c, 'sign':signs(delta,pred_delta,all_rows),
            'projection_boundary':boundary, 'context':context, 'partition_accounting':accounting,
            'zero_transition_job_pattern':pattern,
            'static_false_move':{'count':int(false.sum()), 'rate_in_static':rate(int(false.sum()),int(static.sum())),
              'continuous_magnitude':distribution(np.abs(prediction[false])),
              'projected_magnitude':distribution(np.abs(pred_delta[false])),
              'candidate_absolute_error':distribution(np.abs(error[false])),
              'absolute_command_current':distribution(np.abs(a['command_current'][false])),
              'absolute_command_feature_newest':distribution(np.abs(a['command_feature_newest'][false])),
              'context_counts':{k:int(np.count_nonzero(v & false)) for k,v in ctx.items()}}}
  arrays = {k.lower()+'_mask':np.ascontiguousarray(v) for k,v in classes.items()}
  arrays['confusion_code'] = np.where(static,np.where(predicted_move,1,0),np.where(predicted_move,3,2)).astype(np.int8)
  arrays['sign_code'] = np.where(~move,0,np.where(~predicted_move,3,np.where(np.sign(delta)==np.sign(pred_delta),1,2))).astype(np.int8)
  return result, arrays


def first_step(events):
  return np.where(events.any(axis=1), np.argmax(events,axis=1)+1, 0).astype(np.int64)


def reversal_count(increments):
  previous = np.zeros(len(increments), dtype=np.int8)
  count = np.zeros(len(increments), dtype=np.int64)
  for col in increments.T:
    sign = np.sign(col).astype(np.int8)
    count += (sign!=0) & (previous!=0) & (sign!=previous)
    previous = np.where(sign!=0,sign,previous)
  return count


def path_arrays(a, chunk=CHUNK):
  observed, projected, hold = a['observed_path'], a['projected_path'], a['hold_last_path']
  require(observed.ndim==2 and observed.shape==projected.shape==hold.shape and observed.shape[1]>=2)
  n = len(observed)
  names = ('first_divergence','first_false_move','observed_move_count','projected_move_count',
           'observed_reversal_count','projected_reversal_count','observed_net_displacement','projected_net_displacement')
  out = {name:np.zeros(n,dtype=np.int64) for name in names}
  out.update({name:np.zeros(n,dtype=bool) for name in ('path_flat_mask','false_motion_mask','missed_motion_mask')})
  for start in range(0,n,chunk):
    s = slice(start,start+chunk)
    o, c, h = observed[s], projected[s], hold[s]
    require(bool((o[:,0]==c[:,0]).all()) and bool((h==o[:,:1]).all()))
    od, cd = np.diff(o,axis=1), np.diff(c,axis=1)
    flat = (o==o[:,:1]).all(axis=1)
    out['first_divergence'][s] = first_step(c[:,1:]!=o[:,1:])
    out['first_false_move'][s] = np.where(flat,first_step(cd!=0),0)
    out['observed_move_count'][s] = np.count_nonzero(od,axis=1)
    out['projected_move_count'][s] = np.count_nonzero(cd,axis=1)
    out['observed_reversal_count'][s] = reversal_count(od)
    out['projected_reversal_count'][s] = reversal_count(cd)
    out['observed_net_displacement'][s] = o[:,-1]-o[:,0]
    out['projected_net_displacement'][s] = c[:,-1]-c[:,0]
    out['path_flat_mask'][s] = flat
    out['false_motion_mask'][s] = flat & (cd!=0).any(axis=1)
    out['missed_motion_mask'][s] = ~flat & (c==o[:,:1]).all(axis=1)
  return out


def rollout(a, chunk=CHUNK):
  out = path_arrays(a,chunk)
  observed, projected, hold = a['observed_path'], a['projected_path'], a['hold_last_path']
  require(np.array_equal(a['initial_tick'],observed[:,0]))
  require(np.array_equal(a['target_endpoint_tick'],observed[:,-1]))
  require(np.array_equal(a['projected'],projected[:,-1]))
  require(np.array_equal(a['error'],(projected[:,-1]-observed[:,-1]).astype(np.float64)))
  require(np.array_equal(a['comparator_error'],(hold[:,-1]-observed[:,-1]).astype(np.float64)))
  error, hold_error = a['error'], a['comparator_error']
  finite(error)
  finite(hold_error)
  n = len(error)
  net, flat = out['observed_net_displacement'], out['path_flat_mask']
  classes = {'ALL':np.ones(n,dtype=bool),'PATH_FLAT':flat,'PATH_MOVED':~flat,
             'ENDPOINT_STATIC':net==0,'ENDPOINT_ONE_TICK':np.abs(net)==1,'ENDPOINT_MULTI_TICK':np.abs(net)>=2,
             'PATH_MOVED_ENDPOINT_STATIC':~flat & (net==0)}
  require(bool((hold_error[flat]==0).all()))
  summaries = {name:paired(error,hold_error,mask) for name,mask in classes.items()}
  accounting = {'p95_additive':False}
  for name, members in [('path_partition',('PATH_FLAT','PATH_MOVED')),
                         ('endpoint_partition',('ENDPOINT_STATIC','ENDPOINT_ONE_TICK','ENDPOINT_MULTI_TICK'))]:
    require(sum(summaries[key]['count'] for key in members)==n)
    accounting[name] = {side:{metric:(sum(summaries[key][side][metric] or 0.0 for key in members)
      - summaries['ALL'][side][metric]) if n else None for metric in ('sae','sse')} for side in ('candidate','hold_last')}
  false, missed = out['false_motion_mask'], out['missed_motion_mask']
  nflat, nmoved = int(flat.sum()), int((~flat).sum())
  cutoff = metrics(error)['p95']
  tail = np.abs(error)>=cutoff if n else np.zeros(0,dtype=bool)
  tail_counts = {name:int(np.count_nonzero(mask & tail)) for name,mask in classes.items() if name!='ALL'}
  tail_counts.update({'count':int(tail.sum()),'fraction':rate(int(tail.sum()),n),'cutoff_p95':cutoff,
                      'FALSE_MOTION':int(np.count_nonzero(false & tail)),
                      'ties_included':True,'interpretation':'TAIL_COMPOSITION_NOT_ADDITIVE_P95_CONTRIBUTION'})
  states = {'PATH_FLAT_SSE_REGRESSION':bool(nflat and summaries['PATH_FLAT']['delta_sse']>0),
            'PATH_MOVED_SSE_IMPROVEMENT':bool(nmoved and summaries['PATH_MOVED']['delta_sse']<0),
            'PATH_MOVED_SSE_REGRESSION':bool(nmoved and summaries['PATH_MOVED']['delta_sse']>0),
            'FALSE_MOTION_PRESENT':bool(false.any()),'MISSED_MOTION_PRESENT':bool(missed.any())}
  result = {'count':n,'horizon':observed.shape[1]-1,'classes':summaries,'partition_counts_exact':True,'partition_accounting':accounting,
            'false_motion':{'count':int(false.sum()),'rate_in_path_flat':rate(int(false.sum()),nflat),
              'projected_move_count_in_path_flat':distribution(out['projected_move_count'][flat]),
              'endpoint':paired(error,hold_error,false)},
            'missed_motion':{'count':int(missed.sum()),'rate_in_path_moved':rate(int(missed.sum()),nmoved)},
            'first_divergence':step_distribution(out['first_divergence'],n),
            'first_false_move':step_distribution(out['first_false_move'][flat],nflat),
            'path_distributions':{name:distribution(out[name]) for name in
              ('observed_move_count','projected_move_count','observed_reversal_count','projected_reversal_count',
               'observed_net_displacement','projected_net_displacement')},
            'final_signed_error':distribution(error),'final_absolute_error':distribution(np.abs(error)),
            'tail_composition':tail_counts,'mechanism_states':states}
  if 'speed_bin_code' in a:
    result['context'] = {name:paired(error,hold_error,mask) for name,mask in contexts(a).items()}
  out.update({name.lower()+'_mask':np.ascontiguousarray(mask) for name,mask in classes.items()})
  out['tail_mask'] = tail
  return result, out


def trigger(patterns):
  if len(patterns)!=32 or any(type(x) is not bool for x in patterns):
    raise ValueError('32_JOBS_REQUIRED')
  count = sum(patterns)
  suffix = 'STRICT' if count==32 else 'MIXED' if count else 'NOT_OBSERVED'
  state = ('HURDLE_FAMILY_DESIGN_REVIEW_SUPPORTED' if count==32 else
           'HURDLE_FAMILY_DESIGN_REVIEW_INCONCLUSIVE' if count else 'HURDLE_FAMILY_DESIGN_REVIEW_NOT_SUPPORTED_BY_V2')
  return {'pattern_jobs':count,'total_jobs':32,'one_step_outcome':'ZERO_STATIC_TRANSITION_TRADEOFF_'+suffix,
          'hurdle_state':state,'hurdle_design_review_supported':True if count==32 else None if count else False,
          'hurdle_implementation_authorized':False,'hurdle_fitting_authorized':False,
          'candidate_search_authorized':False,'holdout_authorized':False,'vehicle_authorized':False}
