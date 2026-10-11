"""Immutable selected-array observation diagnostic; raw logs have no read path."""
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as read
from openpilot.tools.cyber_autotune import empirical_stage_a_attribution as old
from openpilot.tools.cyber_autotune import empirical_causal_publication as causal
from openpilot.tools.cyber_autotune import empirical_causal_recovery as recovery
from openpilot.tools.cyber_autotune import empirical_grid_analysis as g
from openpilot.tools.cyber_autotune.empirical_v3_cache import distinct_stores, tree_identity
from openpilot.tools.cyber_autotune.empirical_v3_models import save_array

NAMES=('v2','v3','attribution','causal')
CODE=('empirical_grid_analysis.py','empirical_grid_emission.py')


def stores(inputs,output):
  if set(inputs)!=set(NAMES):
    raise ValueError('EXACT_FOUR_HISTORICAL_STORES_REQUIRED')
  paths={n:distinct_stores(path,output)[0] for n,path in inputs.items()}
  for i,n in enumerate(NAMES):
    for other in NAMES[i+1:]:
      distinct_stores(paths[n],paths[other])
  return paths,distinct_stores(paths['v2'],output)[1]


def static_policy():
  public=causal.load()
  cp=public['empirical-stage-a-causal-recovery-policy-v1.json']
  cr=public['empirical-stage-a-causal-condition-results-v1.json']
  source=old.source_contract()
  if (source['step_deg'],source['offset_deg'],source['declared_range_deg'])!=(.1,0.,[-3276.8,3276.7]):
    raise ValueError('SOURCE_QUANTIZATION_CONFLICT')
  return {'schema':'EMPIRICAL_SOURCE_GRID_EMISSION_POLICY_V1',
    'baseline':'47f18dd0499c5230523b39b0191caf75305000ad',
    'v3_policy_sha256':cp['v3_policy_sha256'],'v3_fold_sha256':cp['v3_fold_sha256'],
    'v3_selected_result_sha256':cp['v3_result_sha256'],
    'causal_policy_sha256':cp['receipt_sha256'],'causal_result_sha256':cr['receipt_sha256'],
    'origin_map_sha256':public['empirical-stage-a-row-origin-map-v1.json']['receipt_sha256'],
    'source':source,'grid':g.grid_contract(),'source_dbc_sha256':source['dbc']['file_sha256'],
    'source_equivalence_sha256':cp['source_equivalence_sha256'],'empirical_profile_sha256':cp['empirical_profile_sha256'],
    'selected':old.selected(),'exact_array_binding':'NPY_SHA256_DTYPE_SHAPE_C_ORDER_BYTES_NO_TOLERANCE',
    'metric_policy_sha256':cp['metric_policy_sha256'],
    'metric_extension':{'arms':list(g.ARMS),'primary':list(g.PRIMARY),'minimum_support':201,
      'quantile':'NUMPY_LINEAR','half_quantum':'ABS_ERROR_STRICTLY_LT_FLOAT64_POINT_ZERO_FIVE',
      'one_quantum':'ABS_ERROR_LE_FLOAT64_POINT_ONE','correlation_constant':'NULL_WITH_SUPPORT',
      'primary_gate':'ALL_SIX_RMSE_STRICTLY_BELOW_HOLD_MAE_P95_NO_HIGHER_SAME_SUPPORT',
      'verdict':'SIX_PASS_REVIEW_FOUR_OR_MORE_FAIL_REJECT_OTHER_TRADEOFF',
      'direction':'EXACT_METRIC_NO_EPSILON','aggregation':'MEAN_ROUTE_METRICS_PER_BIN_SAMPLE_WEIGHTED_SUPPORTING_ONLY',
      'target_grid':'EXISTING_FLOAT32_SOURCE_GRID_TOLERANCE_NO_TARGET_REPLACEMENT',
      'outcome':'EXISTING_PARTITIONS_EXPLANATION_ONLY_NEVER_RULE_OR_GATE'},
    'projection_count':1,'projection_search':'PROHIBITED','arrays_deserialized_before_freeze':False,
    'executor_sha256':{n:p.sha(Path(__file__).with_name(n).read_bytes()) for n in CODE},
    'privacy_policy_sha256':p.sha(b'ONLY_AGGREGATES_SOURCE_FACTS_OPAQUE_IDS_RECEIPT_HASHES_NO_ROW_VALUES_PATHS_TIMESTAMPS'),
    'environment':{'python':sys.version,'numpy':np.__version__,'blas_threads':1,'solver':'NONE_NO_FIT','rng':'NONE'},
    'raw_opening_allowed':False,'fitting_allowed':False,'rollout_allowed':False,'selector_allowed':False,
    'holdout_opening_allowed':False,'search_allowed':False,'stage_b_analysis_allowed':False,
    'input_v2_use':'HASH_ONLY_NO_ALIGNED_ARRAY_DESERIALIZATION',
    'origin_use':'EXISTING_EXACT_PROOF_RECEIPT_PLUS_HASHED_ORIGIN_BYTES_NO_RECONSTRUCTION',
    'calibration_blockers':p.BLOCKERS}


def freeze(inputs,output):
  paths,output=stores(inputs,output)
  pol=static_policy()
  public=causal.load()
  cp=read.read(paths['causal']/'policy.json')
  cr=read.read(paths['causal']/'results.json')
  if cp!=public['empirical-stage-a-causal-recovery-policy-v1.json'] or cr!=public['empirical-stage-a-causal-condition-results-v1.json']:
    raise ValueError('CAUSAL_PUBLIC_PRIVATE_IDENTITY_CONFLICT')
  v3=read.read(paths['v3']/'results.json')
  att=read.read(paths['attribution']/'results.json')
  trees={n:tree_identity(path) for n,path in paths.items()}
  if any(trees[n]!=cp['input_tree_sha256'][n] for n in ('v2','v3','attribution')):
    raise ValueError('HISTORICAL_TREE_DRIFT')
  if v3['receipt_sha256']!=pol['v3_selected_result_sha256'] or att['receipt_sha256']!=cp['attribution_result_sha256']:
    raise ValueError('HISTORICAL_RESULT_CHAIN_DRIFT')
  bindings=[{k:x[k] for k in ('route_id','fold','speed_bin','count','origin_manifest_sha256','private_array_sha256')}
            for x in cr['route_fold_speed_results']]
  result=p.seal({**pol,'input_tree_sha256':trees,'origin_bindings':bindings})
  p.persist(output/'policy.json',result)
  return result


def require_frozen(inputs,output):
  paths,output=stores(inputs,output)
  pol=read.read(output/'policy.json')
  if any(pol.get(k)!=v for k,v in static_policy().items()):
    raise ValueError('GRID_FROZEN_POLICY_SOURCE_CODE_DRIFT')
  if pol['input_tree_sha256']!={n:tree_identity(path) for n,path in paths.items()}:
    raise ValueError('GRID_IMMUTABLE_INPUT_DRIFT')
  return paths,output,pol


def raw_guard(event,args):
  if event in ('open','os.scandir','os.listdir') and args and isinstance(args[0],(str,bytes)):
    name=str(args[0]).lower().replace('\\','/')
    if name.startswith(('/mnt/d/','d:/')) or any(s in name for s in ('rlog','qlog')):
      raise AssertionError('RAW_LOG_REOPENING_PROHIBITED')


def run(inputs,output):
  paths,output,pol=require_frozen(inputs,output)
  if any(os.environ.get(n)!='1' for n in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')):
    raise ValueError('EXACT_SINGLE_THREAD_REQUIRED')
  historical=read.read(paths['causal']/'results.json')
  if historical['receipt_sha256']!=pol['causal_result_sha256']:
    raise ValueError('CAUSAL_RESULT_DRIFT')
  rows=[]
  for expected in pol['selected']:
    b,f=expected['speed_bin'],expected['fold']
    matches=[x for x in historical['route_fold_speed_results'] if x['speed_bin']==b and x['fold']==f]
    if len(matches)!=1:
      raise ValueError('EXACT_ORIGIN_SCOPE_REQUIRED')
    origin=matches[0]
    if origin['route_id']!=expected['development_route'] or not origin['target_design_prediction_previous_order_exact']:
      raise ValueError('EXACT_ORIGIN_MAPPING_REQUIRED')
    folder=paths['v3']/'folds'/'STAGE_A'/b/'ARX1-5'/f
    receipt=read.read(folder/'receipt.json')
    if receipt['receipt_sha256']!=expected['private_result_sha256'] or receipt['config']!=expected['config']:
      raise ValueError('FROZEN_SELECTED_FOLD_IDENTITY')
    for key in ('train_route','development_route','fold'):
      if receipt[key]!=expected[key]:
        raise ValueError('EXACT_FOLD_ROUTE_ORDER_REQUIRED')
    design=old.load_array(folder/'design.npy',expected['array_sha256']['design'])
    one=old.load_array(folder/'one_step.npy',expected['array_sha256']['one_step'])
    old.validate_pair(design,one)
    mapped=paths['causal']/'recovered'/b/f
    proof=read.read(mapped/'receipt.json')
    if proof['receipt_sha256']!=origin['origin_manifest_sha256']:
      raise ValueError('EXACT_ORIGIN_RECEIPT_REQUIRED')
    # Validate existing origin-array SHA and row count without republishing rows.
    origins=old.load_array(mapped/'origin.npy',origin['private_array_sha256']['origin'])
    if len(origins)!=len(one) or origin['count']!=len(one):
      raise ValueError('EXACT_ORIGIN_SUPPORT_REQUIRED')
    result,codes,emitted=g.analyze(one)
    for arm,key in (('CONTINUOUS_ARX','model'),('HOLD_LAST_OUTPUT','HOLD_LAST_OUTPUT')):
      actual=result['arms'][arm]
      old_metrics=expected['evaluation']['one_step'][key]
      if any(actual[k]!=v for k,v in old_metrics.items()):
        raise ValueError('UNCHANGED_SELECTED_METRICS_REQUIRED')
    if result['count']!=expected['evaluation']['coverage']['one_step']['valid']:
      raise ValueError('EXACT_FROZEN_SUPPORT_REQUIRED')
    local=output/'projected'/b/f
    digests={'codes':save_array(local/'codes.npy',codes),'emitted':save_array(local/'emitted.npy',emitted)}
    rows.append({'route_id':expected['development_route'],'fold':f,'speed_bin':b,
                 'selected_array_sha256':expected['array_sha256']['one_step'],
                 'origin_manifest_sha256':origin['origin_manifest_sha256'],
                 'private_projection_sha256':digests,'exact_same_support':True,**result,'gate':g.gate(result)})
  # Public order is route, fold, then frozen speed-bin order.
  rows.sort(key=lambda x:(x['route_id'],x['fold'],g.BINS.index(x['speed_bin'])))
  decision=g.adjudicate(rows)
  after={n:tree_identity(path) for n,path in paths.items()}
  if after!=pol['input_tree_sha256']:
    raise ValueError('HISTORICAL_STORE_MUTATION')
  result=p.seal({'schema':'EMPIRICAL_SOURCE_GRID_EMISSION_RESULTS_V1','policy_sha256':pol['receipt_sha256'],
    'scopes':rows,'decision':decision,
    'equal_route_by_speed':{b:g.aggregate([x for x in rows if x['speed_bin']==b]) for b in g.BINS},
    'input_trees_before_sha256':pol['input_tree_sha256'],'input_trees_after_sha256':after,
    'refit':'NOT_RUN','selector':'NOT_RUN','rollout':'NOT_RUN','raw_opening':'NOT_RUN','stage_b':'NOT_RUN'})
  p.persist(output/'results.json',result)
  return result


def readiness(decision,policy_sha,result_sha,repeat_sha):
  historical=recovery.v3_readiness()
  return p.seal({'schema':'EMPIRICAL_SOURCE_GRID_EMISSION_READINESS_V1',**decision,
    'policy_sha256':policy_sha,'result_sha256':result_sha,'repeatability_sha256':repeat_sha,
    'model_admission':'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
    'package_status':'CLOSED_MISSING_ADMISSIBLE_MODEL','holdout_opening':'HOLDOUT_OPENING_CLOSED',
    'future_holdout':'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED','stage_b':'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
    'historical':historical['historical'],
    'historical_additive_states':{'v3':'STAGE_A_CV_TRADEOFF_ONLY','attribution':'STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED',
      'causal_recovery':'CAUSAL_CONTEXT_RECOVERED_PARTIAL'},
    'refit':'NOT_RUN','selector':'NOT_RUN','rollout':'NOT_RUN','ta_sg_execution':'NOT_RUN',
    'calibration_blockers':p.BLOCKERS,'sealed_reference':'NOT_GENERATED','vehicle':historical['vehicle']})


def validate_public(row):
  recovery.validate_public(row)
  banned={'grid_predictions','grid_codes','emitted_values','origins','design_arrays','per_sample_errors','private_coefficients'}
  def walk(x):
    if isinstance(x,dict):
      if set(x)&banned:
        raise ValueError('PRIVATE_GRID_ROWS_FORBIDDEN')
      for v in x.values():
        walk(v)
    elif isinstance(x,list):
      for v in x:
        walk(v)
  walk(row)
  return row


def outputs(output):
  pol=read.read(output/'policy.json')
  result=read.read(output/'results.json')
  repeat=read.read(output/'repeatability.json')
  if any(pol.get(k)!=v for k,v in static_policy().items()) or result['policy_sha256']!=pol['receipt_sha256']:
    raise ValueError('GRID_PUBLIC_POLICY_RESULT_DRIFT')
  old.validate_repeatability(repeat,result['receipt_sha256'])
  if result['decision']!=g.adjudicate(result['scopes']):
    raise ValueError('GRID_PUBLIC_DECISION_DRIFT')
  ready=readiness(result['decision'],pol['receipt_sha256'],result['receipt_sha256'],repeat['receipt_sha256'])
  rows={'empirical-source-grid-emission-policy-v1.json':pol,
        'empirical-source-grid-emission-results-v1.json':result,
        'empirical-source-grid-emission-readiness-v1.json':ready,
        'empirical-source-grid-emission-repeatability-v1.json':repeat}
  if result['decision']['verdict']=='SOURCE_GRID_OBSERVATION_REVIEW_POSSIBLE':
    rows['empirical-stage-a-v4-observation-architecture-contract-v1.json']=g.architecture(result['decision'],pol['receipt_sha256'])
  for row in rows.values():
    validate_public(row)
  return rows


def run_twice(inputs,output):
  # Force existing raw APIs to fail, and guard all filesystem raw-root opens.
  from openpilot.tools.cyber_autotune import empirical_plant_signals as signals
  from openpilot.tools.cyber_autotune import empirical_signal_reader as reader
  enabled=True
  def audit(event,args):
    if enabled:
      raw_guard(event,args)
  sys.addaudithook(audit)
  try:
    with ExitStack() as stack:
      stack.enter_context(patch.object(signals,'events',side_effect=AssertionError('RAW_DECODER_FORBIDDEN')))
      stack.enter_context(patch.object(reader,'read_numeric',side_effect=AssertionError('RAW_READER_FORBIDDEN')))
      first=run(inputs,output)
      second=run(inputs,output)
      if first!=second:
        raise ValueError('GRID_EXACT_REPEATABILITY_FAILURE')
      repeat=p.seal({'schema':'EMPIRICAL_SOURCE_GRID_EMISSION_REPEATABILITY_V1',
        'runs':2,'exact_repeatability':True,'result_sha256':first['receipt_sha256'],
        'compared':['SOURCE_GRID_CODES','FLOAT32_EMISSION_BYTES','METRICS','COUNTS','VERDICT','RECEIPT_SHA','HISTORICAL_TREES'],
        'raw_decoder_forced_exception':True,'raw_path_forced_exception':True,'whole_process_succeeded':True})
      p.persist(output/'repeatability.json',repeat)
      return first
  finally:
    enabled=False


def main():
  cli=argparse.ArgumentParser(description=__doc__)
  cli.add_argument('mode',choices=('freeze','run','publish'))
  for n in NAMES:
    cli.add_argument('--'+n+'-store',type=Path,required=True)
  cli.add_argument('--store',type=Path,required=True)
  args=cli.parse_args()
  inputs={n:getattr(args,n+'_store') for n in NAMES}
  if args.mode=='freeze':
    print(freeze(inputs,args.store)['receipt_sha256'])
  elif args.mode=='run':
    print(run_twice(inputs,args.store)['decision'])
  else:
    require_frozen(inputs,args.store)
    for name,row in outputs(args.store).items():
      p.persist(p.PUBLIC/name,row)
    print('aggregate grid publication complete')


if __name__=='__main__':
  main()
