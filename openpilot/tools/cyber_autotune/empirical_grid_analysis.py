"""One fixed source-grid observation diagnostic. No latent-state update or fit."""
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_stage_a_regime as regime

ARMS = ('HOLD_LAST_OUTPUT', 'CONTINUOUS_ARX', 'SOURCE_GRID_ARX')
BINS = ('LOW', 'MEDIUM', 'HIGH')
PRIMARY = ('RMSE', 'MAE', 'P95_ABS')
MINIMUM = 201


def grid_contract():
  return {'step_deg': .1, 'offset_deg': 0., 'range_deg': [-3276.8,3276.7],
          'code_range': [-32768,32767], 'tie_rule': 'ROUND_HALF_TO_EVEN',
          'dtype': 'float32', 'quotient_dtype': 'float64',
          'emission': 'FLOAT64_CODE_TIMES_FLOAT64_POINT_ONE_THEN_FLOAT32',
          'ties': 'EXACT_BINARY64_QUOTIENT_FRACTION_HALF_NO_EPSILON',
          'clipping': 'FORBIDDEN'}


def require_grid(facts):
  if facts != grid_contract():
    raise ValueError('EXACT_SOURCE_GRID_RULE_REQUIRED')
  return facts


def project(prediction):
  x = np.asarray(prediction)
  if x.ndim != 1 or x.dtype != np.float64 or not np.isfinite(x).all():
    raise ValueError('FINITE_FLOAT64_PREDICTION_REQUIRED')
  quotient = x / .1
  code = np.rint(quotient)
  if not np.isfinite(code).all() or np.any((code < -32768) | (code > 32767)):
    raise ValueError('SOURCE_GRID_RANGE_VIOLATION')
  codes = code.astype(np.int64)
  # This order matches source decoding followed by capnp Float32 storage.
  emitted = (codes.astype(np.float64) * .1).astype(np.float32)
  ties = np.abs(quotient - np.trunc(quotient)) == .5
  return codes, emitted, ties


def metrics(target, prediction):
  y, pred = np.asarray(target), np.asarray(prediction)
  if y.ndim != 1 or pred.shape != y.shape:
    raise ValueError('EXACT_SAME_SUPPORT_REQUIRED')
  e = pred.astype(np.float64) - y
  row = m.statistics(e,y)
  n=len(y)
  exact=int(np.sum(e == 0))
  half=int(np.sum(np.abs(e) < .05))
  one=int(np.sum(np.abs(e) <= .1))
  return {**row, 'exact_target_hit_count':exact, 'exact_target_hit_rate':exact/n if n else None,
          'error_below_half_quantum_count':half,'error_below_half_quantum_rate':half/n if n else None,
          'error_at_most_one_quantum_count':one,'error_at_most_one_quantum_rate':one/n if n else None,
          'MAX_ABS':float(np.max(np.abs(e))) if n else None,
          'coverage':{'valid':n,'total':n,'unavailable':0}}


def comparison(grid, continuous):
  delta={k:grid[k]-continuous[k] for k in PRIMARY}
  if all(x<=0 for x in delta.values()) and any(x<0 for x in delta.values()):
    state='GRID_IMPROVES_CONTINUOUS_ARX_ALL_PRIMARY_METRICS'
  elif delta['RMSE']>0 and delta['MAE']<0:
    state='GRID_TRADES_RMSE_FOR_MAE'
  elif delta['MAE']>0 and delta['RMSE']<0:
    state='GRID_TRADES_MAE_FOR_RMSE'
  elif all(x==0 for x in delta.values()):
    state='GRID_NO_MATERIAL_DIRECTIONAL_CHANGE'
  else:
    state='GRID_MIXED_PRIMARY_METRIC_DIRECTIONS'
  return {'state':state,'grid_minus_continuous':delta,
          'comparison_semantics':'EXACT_NO_PERCENTAGE_OR_MATERIALITY_EPSILON'}


def analyze(one):
  if one.ndim!=2 or one.shape[1]!=5 or not len(one) or one.dtype!=np.float64 or not np.isfinite(one).all():
    raise ValueError('EXACT_FINITE_SELECTED_FIVE_COLUMN_ARRAY_REQUIRED')
  y,continuous,hold=one[:,0],one[:,1],one[:,3]
  _,_,compliant=regime.grid_arrays(y,.1,0.)
  if not compliant.all():
    raise ValueError('SOURCE_TARGET_GRID_CONFLICT')
  codes,emitted,ties=project(continuous)
  predictions=dict(zip(ARMS,(hold,continuous,emitted.astype(np.float64)),strict=True))
  arms={name:metrics(y,x) for name,x in predictions.items()}
  target_codes=np.rint(y/.1)
  hold_codes=np.rint(hold/.1)
  delta=np.abs(target_codes-hold_codes)
  masks={'TARGET_UNCHANGED':y==hold,
         'TARGET_ONE_QUANTUM_CHANGE':(y!=hold)&(delta==1),
         'TARGET_MULTI_QUANTUM_CHANGE':(y!=hold)&(delta>=2),
         'TARGET_SIGN_REVERSAL':y*hold<0,
         'TARGET_LARGE_TRANSITION':(y!=hold)&(delta>=2)}
  if not np.all(sum(masks[k] for k in regime.PARTITION)==1):
    raise ValueError('SOURCE_OUTCOME_PARTITION_CONFLICT')
  result={'count':len(y),'arms':arms,
          'target_grid':regime.grid(y,.1,0.),'previous_grid':regime.grid(hold,.1,0.),
          'outcome_role':'EXPLANATION_ONLY_NEVER_RULE_SELECTION_OR_GATE',
          'outcome':{name:{'count':int(mask.sum()),'fraction':float(np.mean(mask)),
                     'arms':{arm:metrics(y[mask],pred[mask]) for arm,pred in predictions.items()}}
                     for name,mask in masks.items()},
          'emission':{'continuous_already_source_grid_count':int(np.sum(continuous==emitted.astype(float))),
                      'prediction_value_changed_by_projection_count':int(np.sum(continuous!=emitted.astype(float))),
                      'code_change_interpretation':'CONTINUOUS_VALUES_HAVE_NO_INTEGER_CODE_COMPARE_EMITTED_VALUE',
                      'projection_delta_abs':regime.distribution(np.abs(emitted.astype(float)-continuous)),
                      'tie_count':int(ties.sum()),'source_range_violation_count':0,
                      'emitted_exact_hit_count':arms['SOURCE_GRID_ARX']['exact_target_hit_count'],
                      **comparison(arms['SOURCE_GRID_ARX'],arms['CONTINUOUS_ARX'])}}
  return result,codes,emitted


def gate(row):
  reasons=[]
  if set(row['arms'])!=set(ARMS):
    return {'passed':False,'failures':['EXACT_THREE_ARMS_REQUIRED']}
  count=row['count']
  for name,x in row['arms'].items():
    if count<MINIMUM or x['count']!=count or x['coverage']!={'valid':count,'total':count,'unavailable':0}:
      reasons.append(name+':SUPPORT_OR_COVERAGE')
    if any(x.get(k) is None or not np.isfinite(x[k]) for k in (*PRIMARY,'MEDIAN_ABS','BIAS','MAX_ABS')):
      reasons.append(name+':NONFINITE_METRIC')
    if x.get('CORRELATION') is not None and not np.isfinite(x['CORRELATION']):
      reasons.append(name+':NONFINITE_CORRELATION')
  if row['emission']['source_range_violation_count']:
    reasons.append('SOURCE_GRID_RANGE_VIOLATION')
  if not reasons:
    g,h=row['arms']['SOURCE_GRID_ARX'],row['arms']['HOLD_LAST_OUTPUT']
    for key in PRIMARY:
      if not (g[key]<h[key] if key=='RMSE' else g[key]<=h[key]):
        reasons.append(key+':HOLD_LAST_GATE')
  return {'passed':not reasons,'failures':reasons}


def require_scopes(rows):
  expected={(f,b) for f in ('FOLD_A','FOLD_B') for b in BINS}
  if len(rows)!=6 or {(x['fold'],x['speed_bin']) for x in rows}!=expected:
    raise ValueError('EXACT_SIX_SCOPES_REQUIRED')
  ids={f:{x['route_id'] for x in rows if x['fold']==f} for f in ('FOLD_A','FOLD_B')}
  if any(len(s)!=1 for s in ids.values()) or ids['FOLD_A']==ids['FOLD_B']:
    raise ValueError('EXACT_TWO_ROUTE_FOLD_BINDING_REQUIRED')


def adjudicate(rows):
  require_scopes(rows)
  gates=[gate(x) for x in rows]
  passes=sum(x['passed'] for x in gates)
  hard=any(x['emission']['source_range_violation_count'] for x in rows)
  verdict=('SOURCE_GRID_OBSERVATION_REJECTED' if hard else 'SOURCE_GRID_OBSERVATION_REVIEW_POSSIBLE' if passes==6 else
           'SOURCE_GRID_OBSERVATION_REJECTED' if 6-passes>3 else 'SOURCE_GRID_OBSERVATION_TRADEOFF_ONLY')
  return {'verdict':verdict,'strict_pass_scopes':passes,'total_scopes':6,
          'track_status':'REVIEW_ONLY_NO_MODEL_ADMISSION' if passes==6 else 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
          'closure_scope':'CURRENT_ARX1_FIR25_FIXED_SOURCE_GRID_AND_PREDECLARED_SINGLE_CONDITION_TRACK_ONLY',
          'all_actuator_or_nonlinear_or_state_space_models_closed':False}


def aggregate(rows):
  fields=PRIMARY+('MEDIAN_ABS','BIAS','CORRELATION','MAX_ABS','exact_target_hit_rate',
                  'error_below_half_quantum_rate','error_at_most_one_quantum_rate')
  def avg(arm,key,weighted):
    values=[x['arms'][arm][key] for x in rows]
    if any(v is None for v in values):
      return None
    return float(np.average(values,weights=[x['count'] for x in rows] if weighted else None))
  return {'primary':'EQUAL_ROUTE_MEAN_OF_SCOPE_METRICS_NOT_POOLED_QUANTILES',
          'scope_count':len(rows),
          'equal_route_mean':{a:{k:avg(a,k,False) for k in fields} for a in ARMS},
          'sample_weighted_supporting_mean':{a:{k:avg(a,k,True) for k in fields} for a in ARMS}}


def architecture(decision,policy_sha):
  if decision['verdict']!='SOURCE_GRID_OBSERVATION_REVIEW_POSSIBLE' or decision.get('strict_pass_scopes')!=6:
    raise ValueError('V4_CONTRACT_REQUIRES_SIX_STRICT_PASSES')
  return p.seal({'schema':'EMPIRICAL_STAGE_A_V4_OBSERVATION_ARCHITECTURE_CONTRACT_V1',
    'policy_sha256':policy_sha,'roles':['LATENT_CONTINUOUS_DYNAMIC_MODEL','SOURCE_GRID_OBSERVATION_EMISSION'],
    'source_grid':grid_contract(),'model':'EXISTING_SELECTED_ARX1_DELAY5_ONLY',
    'allowed_inputs':['PAST_SOURCE_BOUND_COMMAND','PAST_MEASURED_ANGLE','SOURCE_PROFILE','CAUSAL_TIMESTAMPS'],
    'causal_timing':'PRIOR_FULLY_OBSERVED_ROWS_ONLY_NO_FUTURE_TARGET',
    'state_ownership':'FUTURE_LATENT_STATE_OWNER_SEPARATE_FROM_OBSERVATION_EMISSION',
    'reset':'FUTURE_POLICY_REQUIRED_ROUTE_SEGMENT_RUN_MASK_SPEED_CONFIG_BOUNDARIES',
    'future_rollout_semantics':'PENDING_LATENT_VERSUS_EMITTED_RECURSION_POLICY',
    'actual_algorithm_implemented':False,'model_fitted':False,'rollout_semantics_frozen':False,
    'execution_allowed':False,'search_allowed':False,'holdout_opening_allowed':False,
    'future_holdout':'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED'})
