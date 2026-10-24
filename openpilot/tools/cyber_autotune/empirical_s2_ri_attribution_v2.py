"""Pure read-only attribution of pinned reconstructed evidence, never execution."""
import argparse
import builtins
from contextlib import contextmanager, ExitStack
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as h
from openpilot.tools.cyber_autotune import empirical_s2_ri_attribution_v2_math as math

INPUT_SHA = '5452d24a4d72ee8680d3b98048c1095113ab934e9bf132f2b91740a0d3baa178'
REPEAT_SHA = 'aa47bac5a33e7c8add13c26c3b75ac638e4c9058b0b030d3c971512b4eb2cc95'
AUTH_SHA = '2af9f81cc7fbac585316aaf4ece5cb4b5ec1f6de368518ae0043be1c9744fa99'
CANDIDATES, HORIZONS = h.CANDIDATES, h.HORIZONS
READY_STATES = ('S2_RI_ATTRIBUTION_EVIDENCE_RECONSTRUCTED','FROZEN_MODEL_REPLAY_EXACT_MATCH',
                '32_FOLD_ATTRIBUTION_INPUTS_COMPLETE','FAILURE_ATTRIBUTION_V2_INPUT_READY')
PUBLIC_PINS = {
 'attribution-reconstruction-readiness-v1':'25c214f124e8d1652a6560dabf98641b8c468688878af5c442fd32f50cd7f141',
 'attribution-replay-equivalence-v1':'9fb00fa2d365df87ef7b2d54efa95a6c08e70690cd70cb033382f9d3cc79e58a',
 'attribution-input-completeness-v2':'9af587668a99df7b5f5c3ee73fbc78d4c48103d59a7b7522ffa5d65bbebe3856',
 'attribution-reconstruction-repeatability-v1':'110289a104d784018885e3d1b9c1fe6bca88899b49fec05e1ec16eff3e6c1685',
 'attribution-evidence-schema-v1':'c1ea3027c41d0973de97b08611b8a3b88e21e82c93e019814541ac5493df6675',
}
CONTEXT = ('anchor_route_id','anchor_segment_sha','anchor_index','anchor_order_index','speed_mps','speed_bin_code',
           'rail','model_eligible','prior_delta_tick','s2_ri_run_id','within_run_index',
           'command_current','command_feature_newest','command_history')
ONE = ('prediction','projected','error','comparator_error','current_tick','target_next_tick','actual_delta_tick',
       'predicted_next_tick_continuous','hold_last_next_tick')
ROLL = ('projected','error','comparator_error','initial_tick','target_endpoint_tick','observed_path','projected_path','hold_last_path')
MODULES = ('empirical_s2_ri_attribution_v2.py','empirical_s2_ri_attribution_v2_math.py','empirical_s2_ri_attribution_v2_publication.py')
SUCCESS = 'S2_RI_FAILURE_ATTRIBUTION_V2_COMPLETE'
FORBIDDEN = 'FAILURE_ATTRIBUTION_V2_EXECUTION_FORBIDDEN'
BLOCKED_SUFFIXES = ('empirical_s2_ri_fit_cv_execution','empirical_s2_ri_fit_cv_math','empirical_s2_ri_fit_cv_gates',
                    'empirical_s2_ri_reconstruction','empirical_s2_ri_reconstruction_math',
                    'empirical_s2_ri_reconstruction_publication','empirical_s2_ri_execution',
                    'empirical_identifiability_execution','empirical_causal_dataset_execution')
ROUTES = ('7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677',
          '962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c')


def forbidden(*args, **kwargs):
  raise ValueError(FORBIDDEN)


def blocked(name):
  return name.startswith(('scipy.optimize','openpilot.tools.lib.logreader','tools.lib.logreader')) or any(
    part in name.split('.') for part in BLOCKED_SUFFIXES)


@contextmanager
def firewall(allowed):
  """Trap execution imports/cached APIs and restrict numpy decoding to exact evidence paths."""
  paths = {str(storage.safe(x)) for x in allowed}
  original_load, original_import, original_import_module = np.load, builtins.__import__, importlib.import_module
  def load(file, *args, **kwargs):
    if not isinstance(file,(str,Path)) or str(storage.safe(file)) not in paths:
      forbidden()
    if args or kwargs != {'mmap_mode':'r','allow_pickle':False}:
      forbidden()
    return original_load(file, **kwargs)
  def importing(name, global_scope=None, local_scope=None, fromlist=(), level=0):
    if blocked(name) or any(blocked(name+'.'+x) for x in fromlist or ()):
      forbidden()
    return original_import(name,global_scope,local_scope,fromlist,level)
  def importing_module(name, package=None):
    if blocked(name):
      forbidden()
    return original_import_module(name,package)
  with ExitStack() as stack:
    for name in ('lstsq','solve','pinv'):
      stack.enter_context(patch.object(np.linalg,name,forbidden))
    for name, mod in tuple(sys.modules.items()):
      if mod is not None and blocked(name):
        for attr in ('fit','normalizer','predict','rollout','recursive','recursive_path','one_step','run','select','load_routes','load_model','LogReader'):
          if callable(getattr(mod,attr,None)):
            stack.enter_context(patch.object(mod,attr,forbidden))
    stack.enter_context(patch.object(np,'load',load))
    stack.enter_context(patch.object(builtins,'__import__',importing))
    stack.enter_context(patch.object(importlib,'import_module',importing_module))
    yield


def require_jobs(jobs):
  if [(x['candidate_id'],x['fold']) for x in jobs] != [(c,f) for c in CANDIDATES for f in ('FOLD_A','FOLD_B')]:
    raise ValueError('32_JOBS_REQUIRED')


def require_manifest(value):
  p.verify(value)
  if value['receipt_sha256']!=INPUT_SHA or value.get('job_count')!=32:
    raise ValueError('EXACT_RECONSTRUCTION_MANIFEST_REQUIRED')


def require_readiness(value):
  if value.get('status')!=READY_STATES[0] or value.get('states')!=list(READY_STATES):
    raise ValueError('FAILURE_ATTRIBUTION_V2_INPUT_NOT_READY')


def public_inputs():
  values = {}
  for name,digest in PUBLIC_PINS.items():
    path = p.PUBLIC/('empirical-s2-ri-'+name+'.json')
    if h.digest_file(path)!=digest:
      raise ValueError('FAILURE_ATTRIBUTION_V2_PUBLIC_INPUT_DRIFT')
    values[name] = h.read_json(path)
  require_readiness(values['attribution-reconstruction-readiness-v1'])
  complete = values['attribution-input-completeness-v2']
  math.require(complete['job_count']==32 and complete['one_step_populations']==32
               and complete['rollout_populations']==128 and complete['context_complete'] and complete['full_paths_complete'])
  for value in values.values():
    math.require(value['private_manifest_sha256']==INPUT_SHA)
  values['historical'] = h.public_inputs()  # Public metadata only, never original private fit buffers.
  return values


def policy():
  return p.seal({'schema':'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_POLICY_V2',
    'mode':'PURE_READ_ONLY_FAILURE_ATTRIBUTION','input_manifest_sha256':INPUT_SHA,
    'repeatability_receipt_sha256':REPEAT_SHA,'public_file_sha256':PUBLIC_PINS,
    'candidate_order':list(CANDIDATES),'fold_order':['FOLD_A','FOLD_B'],'horizons':list(HORIZONS),
    'analysis_chunk_size':math.CHUNK,'numpy_version':'2.5.3','dtype':'float64',
    'required_environment':{'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},
    'one_step_classes':['STATIC','MOVE','MOVE_POSITIVE','MOVE_NEGATIVE','ONE_TICK_MOVE','MULTI_TICK_MOVE'],
    'error_source':'STORED_CANONICAL_ERROR_ONLY',
    'reduction':'ORIGINAL_ANCHOR_ORDER_CONTIGUOUS_FLOAT64_PER_CLASS',
    'partition_accounting':'EXACT_COUNTS_AND_REPORTED_FLOAT_PARTITION_SUM_MINUS_DIRECT_ALL_NO_TOLERANCE_GATE',
    'p95':'numpy.percentile(abs(error),95,method=linear)','p95_additive':False,
    'projection_boundary':0.5,'projection_boundary_equality':'EXACT_BINARY64_NO_EPSILON',
    'trigger':'ALL_32_JOBS_MOVE_DELTA_SSE_LT_ZERO_AND_STATIC_DELTA_SAE_GT_ZERO_AND_STATIC_EXACT_HIT_REGRESSION',
    'tail':'ABS_ENDPOINT_ERROR_GE_EXISTING_P95_TIES_INCLUDED_NO_DOMINANCE_THRESHOLD',
    'reversal':'SUCCESSIVE_NONZERO_INCREMENT_SIGN_CHANGES_ZERO_IGNORED',
    'missing_input':'FAILURE_ATTRIBUTION_V2_INPUT_CONFLICT_NO_FALLBACK',
    'candidate_ranking':False,'gate_reevaluation':False,'counterfactual_admission':False,
    'hurdle_implementation_authorized':False,'hurdle_fitting_authorized':False,
    'holdout':'CLOSED','opening_count':0,'vehicle_authority':False})


def sources():
  return {name:h.digest_file(Path(__file__).parent/name) for name in MODULES}


def environment():
  if np.__version__!='2.5.3' or any(os.environ.get(k)!='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
    raise ValueError('EXACT_SINGLE_THREAD_NUMERICAL_ENVIRONMENT_REQUIRED')


def write(path,value):
  p.verify(value)
  storage.atomic_bytes(path,json.dumps(value,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n')


def finish(root,names,fields):
  if len(names)!=len(set(names)):
    raise ValueError('DUPLICATE_OUTPUT_FILE')
  value = p.seal({**fields,'files':{name:h.digest_file(h.relative_file(root,name)) for name in sorted(names)}})
  write(root/'manifest.json',value)
  return value


def resume(root):
  value = h.read_json(root/'manifest.json')
  h.verify_files(root,value)
  if 'summary_sha256' in value:
    math.require(h.read_json(root/'summary.json')['receipt_sha256']==value['summary_sha256'])
  return value


def require_fields(fields,horizon):
  math.require(set(fields)==set(CONTEXT)|set(ONE if horizon==1 else ROLL))


def require_binding(key,b,count,horizon,length):
  integer = {'projected','current_tick','target_next_tick','actual_delta_tick','hold_last_next_tick',
    'initial_tick','target_endpoint_tick','observed_path','projected_path','hold_last_path','anchor_index',
    'anchor_order_index','prior_delta_tick','s2_ri_run_id','within_run_index'}
  dtype = '<i8' if key in integer else '|S64' if key in ('anchor_route_id','anchor_segment_sha') else (
    '|b1' if key in ('rail','model_eligible') else '|i1' if key=='speed_bin_code' else '<f8')
  shape = [count,horizon+1] if key in ('observed_path','projected_path','hold_last_path') else (
    [count,length] if key=='command_history' else [count])
  math.require(set(b)=={'dtype','shape','order','file_sha256','array_sha256'}
               and b['dtype']==dtype and b['shape']==shape and b['order']=='C')
  for name in ('file_sha256','array_sha256'):
    math.require(type(b[name]) is str and len(b[name])==64 and all(c in '0123456789abcdef' for c in b[name]))


def metadata_admission(source):
  """Resolve only reconstruction metadata; validate every population before any decode."""
  source = storage.safe(source)
  public = public_inputs()
  run = source/'repeat-1'
  manifest = h.read_json(run/'manifest.json')
  require_manifest(manifest)
  repeat = h.read_json(source/'repeatability.json')
  math.require(repeat['receipt_sha256']==REPEAT_SHA and repeat['manifest_sha256']==INPUT_SHA
               and repeat['input_bytes_unchanged'] and repeat['trapped_resume_exact'])
  math.require(h.read_json(source/'authorization.json')['receipt_sha256']==AUTH_SHA)
  results = h.read_json(run/'results.json')
  math.require(results['receipt_sha256']==manifest['results_sha256'])
  jobs = results['jobs']
  require_jobs(jobs)
  equivalent = public['attribution-replay-equivalence-v1']['jobs']
  require_jobs(equivalent)
  records, expected = [], {'results.json'}
  for job, published, old in zip(jobs,equivalent,public['historical']['fit-cv-results']['jobs'],strict=True):
    prefix = f"candidates/{job['candidate_id']}/{job['fold']}/"
    root = run/prefix
    local = h.read_json(root/'manifest.json')
    math.require(h.read_json(root/'receipt.json')==job and local['job_receipt_sha256']==job['receipt_sha256'])
    math.require(job['receipt_sha256']==published['reconstruction_receipt_sha256']
                 and job['original_job_receipt_sha256']==old['receipt_sha256']
                 and job['historical_gate']==old['gate'] and job['selection_run'] is False
                 and job['gate_recomputed'] is False and job['context_complete'] and job['path_complete']
                 and job['model_sha256']==old['model_receipt_sha256']
                 and job['normalizer_sha256']==old['normalizer_receipt_sha256']
                 and job['coefficient_sha256']==old['coefficient_sha256'])
    expected.add(prefix+'manifest.json')
    local_expected = {'receipt.json'}
    for horizon in (1,*HORIZONS):
      name = 'one-step' if horizon==1 else f'rollout-{horizon}'
      pop = h.read_json(root/name/'receipt.json')
      hist = old['one_step'] if horizon==1 else old['rollout'][str(horizon)]
      require_fields(pop['arrays'],horizon)
      math.require(pop['receipt_sha256']==job['populations'][name]
                   and pop['receipt_sha256']==published['populations'][name]['receipt_sha256']
                   and pop['horizon']==horizon and pop['count']==hist['count']
                   and pop['anchor_sha256']==pop['comparator_anchor_sha256']==hist['anchor_sha256']
                   and pop['context_complete'] and pop['metric_equality']
                   and pop['path_complete'] is (horizon!=1))
      for field,b in pop['arrays'].items():
        require_binding(field,b,pop['count'],horizon,int(job['candidate_id'][-2:]))
        math.require(local['files'].get(name+'/'+field+'.npy')==b['file_sha256'])
        local_expected.add(name+'/'+field+'.npy')
      local_expected.add(name+'/receipt.json')
      records.append({'candidate_id':job['candidate_id'],'fold':job['fold'],'name':name,
                      'horizon':horizon,'root':root/name,'population':pop,'job':job})
    math.require(set(local['files'])==local_expected)
    for name,digest in local['files'].items():
      h.relative_file(root,name)
      math.require(manifest['files'].get(prefix+name)==digest)
      expected.add(prefix+name)
  math.require(set(manifest['files'])==expected and len(records)==160)
  return public,manifest,records


def verify_source(source):
  """Opaque hashing of both sealed reconstruction runs and root receipts, no other store."""
  identities = {}
  for name in ('repeat-1','repeat-2'):
    root = source/name
    value = h.read_json(root/'manifest.json')
    require_manifest(value)
    identities[name] = {'manifest_file_sha256':h.digest_file(root/'manifest.json'),
                        'files_identity_sha256':h.verify_files(root,value)}
  for name,expected in (('authorization.json',AUTH_SHA),('repeatability.json',REPEAT_SHA)):
    math.require(h.read_json(source/name)['receipt_sha256']==expected)
    identities[name] = h.digest_file(source/name)
  return p.sha(p.canonical(identities))


def open_array(path,binding,allowed):
  path = storage.safe(path)
  math.require(path in allowed and h.digest_file(path)==binding['file_sha256'])
  a = np.load(path,mmap_mode='r',allow_pickle=False)
  math.require(a.dtype.str==binding['dtype'] and list(a.shape)==binding['shape']
               and a.flags.c_contiguous and not a.flags.writeable and not a.dtype.hasobject)
  digest = hashlib.sha256()
  view = memoryview(a).cast('B')
  for i in range(0,len(view),1024*1024):
    digest.update(view[i:i+1024*1024])
  math.require(digest.hexdigest()==binding['array_sha256'])
  return a


def load_population(record):
  pop, root = record['population'],record['root']
  paths = tuple(root/(key+'.npy') for key in pop['arrays'])
  arrays = {key:open_array(root/(key+'.npy'),b,paths) for key,b in pop['arrays'].items()}
  n = pop['count']
  math.require(bool(arrays['model_eligible'].all()))
  math.require(np.array_equal(arrays['anchor_order_index'],np.arange(n,dtype=np.int64)))
  route = ROUTES[1] if record['fold']=='FOLD_A' else ROUTES[0]
  math.require(bool((arrays['anchor_route_id']==route.encode()).all()))
  segment, index = arrays['anchor_segment_sha'],arrays['anchor_index']
  math.require(bool(((segment[1:]>segment[:-1])|((segment[1:]==segment[:-1]) & (index[1:]>index[:-1]))).all()))
  math.require(bool((arrays['s2_ri_run_id']>=0).all()) and bool((arrays['within_run_index']>=0).all()))
  return arrays


def array_identity(arrays):
  return {k:p.sha(np.ascontiguousarray(v).tobytes()) for k,v in sorted(arrays.items())}


def population(root,record):
  a = load_population(record)
  result, arrays = math.one_step(a) if record['horizon']==1 else math.rollout(a)
  inputs = record['population']
  bindings = {key:storage.array_write(root/(key+'.npy'),v) for key,v in sorted(arrays.items())}
  receipt = p.seal({'schema':'EMPIRICAL_S2_RI_ATTRIBUTION_POPULATION_V2','candidate_id':record['candidate_id'],
    'fold':record['fold'],'horizon':record['horizon'],'input_receipt_sha256':inputs['receipt_sha256'],
    'anchor_sha256':inputs['anchor_sha256'],'comparator_anchor_sha256':inputs['comparator_anchor_sha256'],
    'input_arrays_sha256':{k:b['array_sha256'] for k,b in inputs['arrays'].items()},
    'derived_arrays':bindings,'analysis':result})
  write(root/'receipt.json',receipt)
  finish(root,['receipt.json',*[k+'.npy' for k in bindings]],
         {'schema':'EMPIRICAL_S2_RI_ATTRIBUTION_POPULATION_MANIFEST_V2','receipt_sha':receipt['receipt_sha256']})
  return receipt


def family_summary(jobs):
  require_jobs(jobs)
  patterns = [j['one_step']['zero_transition_job_pattern'] for j in jobs]
  result = math.trigger(patterns)
  result['rollout_by_horizon'] = {}
  state_names = ('PATH_FLAT_SSE_REGRESSION','PATH_MOVED_SSE_IMPROVEMENT','PATH_MOVED_SSE_REGRESSION',
                 'FALSE_MOTION_PRESENT','MISSED_MOTION_PRESENT')
  for horizon in HORIZONS:
    counts = {s:sum(j['rollout'][str(horizon)]['mechanism_states'][s] for j in jobs) for s in state_names}
    result['rollout_by_horizon'][str(horizon)] = {'jobs':32,'state_counts':counts,
      'path_flat_sse_state':'PATH_FLAT_SSE_REGRESSION_ALL_JOBS' if counts['PATH_FLAT_SSE_REGRESSION']==32 else 'MIXED'}
  groups = {}
  for key,values in [('d',(0,5,10,20)),('L',(1,5,15,45))]:
    groups[key] = {}
    for value in values:
      subset = [j for j in jobs if int(j['candidate_id'][6:8] if key=='d' else j['candidate_id'][-2:])==value]
      groups[key][str(value)] = {'jobs':len(subset),
        'pattern_jobs':sum(j['one_step']['zero_transition_job_pattern'] for j in subset),
        'static_sae_regression_jobs':sum((j['one_step']['classes']['STATIC']['delta_sae'] or 0)>0 for j in subset),
        'move_sse_improvement_jobs':sum((j['one_step']['classes']['MOVE']['delta_sse'] or 0)<0 for j in subset),
        'static_false_move_present_jobs':sum(j['one_step']['static_false_move']['count']>0 for j in subset),
        'rollout_state_counts':{str(horizon):{s:sum(j['rollout'][str(horizon)]['mechanism_states'][s] for j in subset)
          for s in state_names} for horizon in HORIZONS}}
  result['descriptive_groups'] = groups
  result['historical_failure_counts'] = h.EXPECTED_FAILURES
  return result


def verify_authorization(output,manifest):
  try:
    auth = h.read_json(output/'authorization.json')
    frozen_policy = h.read_json(output/'policy.json')
  except (OSError,ValueError,KeyError) as exc:
    raise ValueError(math.CONFLICT) from exc
  math.require(auth['receipt_sha256']==manifest['authorization_sha256']
               and frozen_policy==policy()
               and auth['input_manifest_sha256']==manifest['input_manifest_sha256']==INPUT_SHA
               and auth['policy_sha256']==manifest['policy_sha256']==frozen_policy['receipt_sha256']
               and auth['executor_sources']==manifest['executor_sources']==sources()
               and auth['public_file_sha256']==PUBLIC_PINS
               and auth['output_store_identity']==p.sha(str(storage.safe(output)).encode()))
  return auth


def run(source,output,replica):
  environment()
  source = storage.safe(source)
  output = storage.external(output,[source])
  if replica not in ('repeat-1','repeat-2'):
    raise ValueError('EXACT_TWO_RUNS_REQUIRED')
  root = output/replica
  if (root/'manifest.json').exists():
    existing = resume(root)
    verify_authorization(output,existing)
    math.require(existing['input_manifest_sha256']==INPUT_SHA and existing['policy_sha256']==policy()['receipt_sha256']
                 and existing['executor_sources']==sources())
    return existing
  public,manifest,records = metadata_admission(source)
  print('METADATA_ADMITTED_32_JOBS_160_POPULATIONS',flush=True)
  before = verify_source(source)
  auth = p.seal({'schema':'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_AUTHORIZATION_V2',
    'input_manifest_sha256':manifest['receipt_sha256'],'input_identity_sha256':before,
    'policy_sha256':policy()['receipt_sha256'],'executor_sources':sources(),
    'output_store_identity':p.sha(str(output).encode()),'public_file_sha256':PUBLIC_PINS})
  write(output/'authorization.json',auth)
  write(output/'policy.json',policy())
  allowed = tuple(r['root']/(k+'.npy') for r in records for k in r['population']['arrays'])
  jobs, files = [], []
  with firewall(allowed):
    for candidate in CANDIDATES:
      for fold in ('FOLD_A','FOLD_B'):
        selected = [r for r in records if r['candidate_id']==candidate and r['fold']==fold]
        prefix = f'jobs/{candidate}/{fold}/'
        jobroot = root/prefix
        pops = {}
        for record in selected:
          name = record['name']
          poproot = jobroot/name
          if (poproot/'manifest.json').exists():
            m = resume(poproot)
            receipt = h.read_json(poproot/'receipt.json')
            math.require(m['receipt_sha']==receipt['receipt_sha256']
                         and receipt['input_receipt_sha256']==record['population']['receipt_sha256'])
          else:
            receipt = population(poproot,record)
          pops[name] = receipt
          local = h.read_json(poproot/'manifest.json')
          files.extend(prefix+name+'/'+n for n in [*local['files'],'manifest.json'])
        job = p.seal({'schema':'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_JOB_V2','candidate_id':candidate,'fold':fold,
          'input_job_receipt_sha256':selected[0]['job']['receipt_sha256'],
          'original_model_sha256':selected[0]['job']['model_sha256'],
          'original_normalizer_sha256':selected[0]['job']['normalizer_sha256'],
          'population_receipts':{name:v['receipt_sha256'] for name,v in pops.items()},
          'one_step':pops['one-step']['analysis'],
          'rollout':{str(horizon):pops[f'rollout-{horizon}']['analysis'] for horizon in HORIZONS}})
        write(jobroot/'receipt.json',job)
        files.append(prefix+'receipt.json')
        jobs.append(job)
        print(json.dumps({'candidate':candidate,'fold':fold,'status':'READ_ONLY_ANALYZED'}),flush=True)
  math.require(h.failure_counts(public['historical']['fit-cv-results']['jobs'])==h.EXPECTED_FAILURES)
  after = verify_source(source)
  math.require(before==after)
  summary = p.seal({'schema':'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_SUMMARY_V2',
    'status':SUCCESS,'jobs':jobs,'job_count':32,'one_step_populations':32,'rollout_populations':128,
    'mechanisms':family_summary(jobs),'input_manifest_sha256':INPUT_SHA,'input_identity_sha256':before,
    'input_bytes_unchanged':True,'model_refit_calls':0,'normalizer_refit_calls':0,'model_replay_calls':0,
    'selection_calls':0,'raw_log_openings':0,'qlog_openings':0,'holdout_openings':0,
    'historical_verdict':'S2_RI_NO_ADMISSIBLE_CANDIDATE','model_selection':'MODEL_SELECTION_FAILED_CLOSED',
    'holdout':'CLOSED','opening_count':0,'vehicle_authority':False,'hurdle_implementation_authorized':False})
  write(root/'summary.json',summary)
  files.append('summary.json')
  return finish(root,files,{'schema':'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_MANIFEST_V2',
    'status':SUCCESS,'summary_sha256':summary['receipt_sha256'],'authorization_sha256':auth['receipt_sha256'],
    'input_manifest_sha256':INPUT_SHA,'policy_sha256':policy()['receipt_sha256'],'executor_sources':sources()})


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source',required=True,type=Path)
  parser.add_argument('--output',required=True,type=Path)
  parser.add_argument('--replica',required=True,choices=('repeat-1','repeat-2'))
  args = parser.parse_args()
  result = run(args.source,args.output,args.replica)
  print(json.dumps({'status':result['status'],'manifest_sha256':result['receipt_sha256']}))


if __name__=='__main__':
  main()
