"""Separate authorization for frozen-model replay, never fit or attribution."""
import argparse
import io
import hashlib
import re
import json
import os
import platform
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_store as store
from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as historical
from openpilot.tools.cyber_autotune import empirical_s2_ri_policy as design
from openpilot.tools.cyber_autotune import empirical_s2_ri_execution as metadata
from openpilot.tools.cyber_autotune import empirical_s2_ri_schema as schema
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_s2_ri_reconstruction_math as replay

FIT_AUTH = '4080b8deed3ecef6de5af4da4385896eae0a269786d90029005d9407140e3943'
INPUT_PINS = 'e562497aa19edd592e567bc4c85a93033b616ae0dffabc77b5d8df23b24bb7f9'
MODULES = ('empirical_s2_ri_reconstruction.py','empirical_s2_ri_reconstruction_math.py',
           'empirical_s2_ri_reconstruction_publication.py')
SUCCESS = 'S2_RI_ATTRIBUTION_EVIDENCE_RECONSTRUCTED'
ONE_FIELDS = ('prediction','projected','error','comparator_error')
ROLL_FIELDS = ('projected','error','comparator_error')
CONTEXT_FIELDS = ('anchor_route_id','anchor_segment_sha','anchor_index','anchor_order_index','speed_mps',
  'speed_bin_code','rail','model_eligible','prior_delta_tick','s2_ri_run_id','within_run_index',
  'command_current','command_feature_newest','command_history')
ONE_NEW = ('current_tick','target_next_tick','actual_delta_tick','predicted_next_tick_continuous','hold_last_next_tick')
ROLL_NEW = ('initial_tick','target_endpoint_tick','observed_path','projected_path','hold_last_path')


def policy():
  return p.seal({'schema':'EMPIRICAL_S2_RI_ATTRIBUTION_RECONSTRUCTION_POLICY_V1',
    'mode':'FROZEN_MODEL_DETERMINISTIC_REPLAY_FOR_EVIDENCE_COMPLETION',
    'fit_manifest_sha256':historical.INPUT_SHA,'fit_authorization_sha256':FIT_AUTH,
    'input_pins_sha256':INPUT_PINS,'fit_policy_sha256':store.POLICY_SHA,
    'candidate_order':list(m.CANDIDATES),'fold_order':['FOLD_A','FOLD_B'],'horizons':list(m.HORIZONS),
    'rollout_chunk':replay.CHUNK,'python_version':'3.12.13','numpy_version':'2.5.3',
    'thread_environment':{'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},
    'error_primitive':'PREDICTED_DELTA_MINUS_OBSERVED_DELTA',
    'projection':'DIRECT_ROUND_HALF_TO_EVEN_TO_INTEGER_TICK',
    'recursion':'PROJECTED_SOURCE_GRID',
    'exogenous':'LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT',
    'target_provenance':'DIRECT_DERIVED_ANGLE_TICK_NO_ERROR_INVERSION',
    'historical_verdict':'S2_RI_NO_ADMISSIBLE_CANDIDATE',
    'failure_attribution':'NOT_RUN','hurdle_trigger':'NOT_EVALUATED',
    'refit_authorized':False,'normalizer_refit_authorized':False,'selection_authorized':False,
    'raw_opening_authorized':False,'qlog_opening_authorized':False,'holdout':'CLOSED','opening_count':0,
    'pooled_refit_authorized':False,'rate_dependency':'NONE',
    'historical_insufficient_audit':'IMMUTABLE_POINT_IN_TIME_FACT',
    'new_evidence':'ATTRIBUTION_EVIDENCE_RECONSTRUCTED_AFTER_SEPARATE_AUTHORIZATION'})


def sources():
  return {n:historical.digest_file(Path(__file__).with_name(n)) for n in MODULES}


def check_environment():
  if (np.__version__ != '2.5.3' or platform.python_version() != '3.12.13'
      or any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS'))):
    raise ValueError('FROZEN_REPLAY_NUMERICAL_ENVIRONMENT_REQUIRED')


def admit(fit,source,derived,output):
  """Metadata and byte hashing only until the new authorization is persisted."""
  fit,source,derived=map(storage.safe,(fit,source,derived))
  output=storage.external(output,[fit.parent,source,derived,'/mnt/d/carrotlog','/mnt/d/CarrotLogs'])
  contracts=store.contracts()
  public=historical.public_inputs()
  fm=read.read_json(fit/'manifest.json')
  historical.require_manifest(fm)
  auth=read.read_json(fit.parent/'authorization.json')
  pins=read.read_json(fit.parent/'input-pins.json')
  if auth['receipt_sha256'] != FIT_AUTH or pins['receipt_sha256'] != INPUT_PINS:
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
  for name,digest in auth['executor_sources'].items():
    if historical.digest_file(Path(__file__).with_name(name)) != digest:
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_EXECUTOR_DRIFT')
  pol=design.policy()
  _,resolved,manifest,records,source_files=metadata.preflight(source,pol)
  index=read.read_json(derived/'repeat-1/derived-index.json')
  result=read.read_json(derived/'repeat-1/results.json')
  denied=set(pol['excluded_qlog_content_sha256'])
  contents=[s['content_sha256'] for s in index['segments']]
  if denied.intersection(contents):
    raise ValueError('QLOG_CAUSAL_ADMISSION_FORBIDDEN')
  if (len(contents) != 154 or len(set(contents)) != 154
      or set(contents) != {s['segment_sha256'] for _,s in records}
      or result['receipt_sha256'] != store.DERIVED_RESULT_SHA
      or store.derived_receipt_set(index) != result['derived_receipt_set_sha256']
      or manifest['receipt_sha256'] != auth['rlog_manifest_sha256']
      or index['receipt_sha256'] != auth['derived_index_sha256']
      or source_files != pins['source']
      or p.sha(p.canonical(pins['derived'])) != auth['derived_file_set_sha256']
      or resolved['final_dataset_status'] != 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL'):
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
  attached=[]
  index_pins={s['content_sha256']:s['receipt_sha256'] for s in index['segments']}
  for base,segment in sorted(records,key=lambda pair:(pair[1]['route_id'],pair[1]['segment_sha256'])):
    local_root=derived/'repeat-1/segments'/segment['segment_sha256']
    local=read.read_json(local_root/'receipt.json')
    if (local['receipt_sha256'] != index_pins[segment['segment_sha256']]
        or local['source_receipt_sha256'] != segment['receipt_sha256']
        or local['policy_sha256'] != pol['receipt_sha256']):
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
    attached.append((base,segment,local_root,local))
  results=read.read_json(fit/'results.json')
  historical.require_jobs(results['jobs'])
  if results['receipt_sha256'] != fm['results_sha256']:
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_JOB_SET_CONFLICT')
  for job,prior in zip(results['jobs'],public['fit-cv-results']['jobs'],strict=True):
    historical.verify_anchors(job)
    if job['receipt_sha256'] != prior['receipt_sha256'] or job['status'] != 'PASS':
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_JOB_SET_CONFLICT')
  # Hash all exact pinned files, never discover routes or open qlog/raw stores.
  verify_inputs(fit,source,derived,fm,pins)
  bound=p.seal({'schema':'EMPIRICAL_S2_RI_ATTRIBUTION_RECONSTRUCTION_AUTHORIZATION_V1',
    'policy_sha256':policy()['receipt_sha256'],'fit_manifest_sha256':fm['receipt_sha256'],
    'fit_authorization_sha256':auth['receipt_sha256'],'input_pins_sha256':pins['receipt_sha256'],
    'public_contracts':{n:v['receipt_sha256'] for n,v in contracts.items()},
    'fit_public_file_sha256':historical.PUBLIC_PINS,'historical_design_pins':auth['historical_design_pins'],
    'rlog_manifest_sha256':manifest['receipt_sha256'],'derived_index_sha256':index['receipt_sha256'],
    'source_files_sha256':p.sha(p.canonical(pins['source'])),'derived_files_sha256':p.sha(p.canonical(pins['derived'])),
    'routes':auth['routes'],'qlog_deny_content_sha256':sorted(denied),'executor_sources':sources(),
    'output_store_identity':p.sha(str(output).encode()),'array_open_before_seal':False,
    'frozen_replay_authorized':True,'refit_authorized':False,'normalizer_refit_authorized':False,
    'selection_authorized':False,'failure_attribution_authorized':False,
    'holdout':'CLOSED','opening_count':0})
  store.write_json(output/'authorization.json',bound)
  store.write_json(output/'policy.json',policy())
  return bound,results['jobs'],attached,fm,pins


def verify_inputs(fit,source,derived,manifest,pins):
  if read.read_json(fit/'manifest.json')['receipt_sha256'] != historical.INPUT_SHA:
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
  historical.verify_files(fit,manifest)
  read.verify_files(source,pins['source'])
  read.verify_files(derived,pins['derived'])
  if (read.read_json(fit.parent/'authorization.json')['receipt_sha256'] != FIT_AUTH
      or read.read_json(fit.parent/'input-pins.json')['receipt_sha256'] != INPUT_PINS):
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')


def load_routes(records,auth):
  p.verify(auth)
  if not auth.get('frozen_replay_authorized') or auth['array_open_before_seal']:
    raise ValueError('SEALED_REPLAY_AUTHORIZATION_REQUIRED')
  if any(s['segment_sha256'] in auth['qlog_deny_content_sha256'] for _,s,_,_ in records):
    raise ValueError('QLOG_CAUSAL_ADMISSION_FORBIDDEN')
  routes={rid:[] for rid in auth['routes']}
  for base,s,root,local in records:
    n=s['arrays']['grid_time_ns']['shape'][0]
    schema.validate_derived(local,root,design.policy()['receipt_sha256'],s['receipt_sha256'],n)
    d={k:read.read_array(root/read.array_name(k),local['arrays'][k]) for k in (
      'angle_tick','streak_all','model_eligible','rail','s2_ri_causal_run_id','within_s2_ri_causal_run_index')}
    a={k:read.read_array(base/'arrays'/read.array_name(k),s['arrays'][k])
       for k in ('command.normalized','state.speed_mps','grid_time_ns')}
    good=d['model_eligible']
    continuity=np.r_[False,(np.diff(a['grid_time_ns'])==10_000_000)
      & (d['s2_ri_causal_run_id'][1:]==d['s2_ri_causal_run_id'][:-1])
      & (np.diff(d['within_s2_ri_causal_run_index'])==1)]
    starts=good & ~(continuity & np.r_[False,good[:-1]])
    index=np.arange(n)
    expected=np.where(good,index-np.maximum.accumulate(np.where(starts,index,-1))+1,0)
    if not np.array_equal(expected,d['streak_all']):
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_CONTINUITY_CONFLICT')
    routes[s['route_id']].append({'route_id':s['route_id'],'segment_sha256':s['segment_sha256'],
      'tick':d['angle_tick'],'streak':d['streak_all'],'command':a['command.normalized'],'speed':a['state.speed_mps'],
      'rail':d['rail'],'eligible':good,'run':d['s2_ri_causal_run_id'],'within':d['within_s2_ri_causal_run_index']})
  return routes


def load_model(root,job):
  values={}
  for name in ('normalizer','model'):
    receipt=read.read_json(root/name/'receipt.json')
    if (receipt['receipt_sha256'] != job[name+'_receipt_sha256']
        or receipt['candidate_id'] != job['candidate_id'] or receipt['fold'] != job['fold']
        or receipt['train_route'] != job['train_route']):
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
    values[name]={k:read.read_array(root/name/read.array_name(k),b) for k,b in receipt['arrays'].items()}
  mr=read.read_json(root/'model/receipt.json')
  if (mr['normalizer_sha256'] != job['normalizer_receipt_sha256'] or mr['policy_sha256'] != store.POLICY_SHA
      or mr['arrays']['nominal_coefficients']['array_sha256'] != job['coefficient_sha256']
      or mr['numpy_version'] != '2.5.3' or mr['pooled_refit']):
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
  return {**values['model'],'normalizer':values['normalizer']}


def compare_original(root,buffers,hashes,manifest,label):
  result={}
  for key,digest in hashes.items():
    filename=key+'.npy'
    data=storage.safe(root/filename).read_bytes()
    if p.sha(data) != manifest[filename]:
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
    old=np.load(io.BytesIO(data),allow_pickle=False)
    if old.dtype.hasobject or p.sha(old.tobytes()) != digest:
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
    replay.exact(buffers[key],old,label)
    result[key]={'original_sha256':digest,'reconstructed_sha256':p.sha(buffers[key].tobytes()),'exact_equal':True}
  return result


def population(root,original,job_manifest,blocks,candidate,model,horizon,historical_metric,hashes):
  name='one-step' if horizon==1 else f'rollout-{horizon}'
  arrays,metric=(replay.one_step(blocks,candidate,model) if horizon==1 else replay.rollout(blocks,candidate,model,horizon))
  label='ONE_STEP' if horizon==1 else 'ROLLOUT'
  equality=compare_original(original/name,arrays,hashes,
    {k[len(name)+1:]:v for k,v in job_manifest['files'].items() if k.startswith(name+'/')},label)
  if metric != {k:historical_metric[k] for k in ('candidate','comparator')}:
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_METRIC_DIVERGENCE')
  bindings={k:storage.array_write(root/name/(k+'.npy'),np.ascontiguousarray(v)) for k,v in arrays.items()}
  receipt=p.seal({'schema':'EMPIRICAL_S2_RI_RECONSTRUCTED_POPULATION_V1',
    'horizon':horizon,'count':historical_metric['count'],'anchor_sha256':historical_metric['anchor_sha256'],
    'comparator_anchor_sha256':historical_metric['comparator_anchor_sha256'],'arrays':bindings,
    'original_equality':equality,'metric_equality':True,'context_complete':True,'path_complete':horizon!=1})
  store.write_json(root/name/'receipt.json',receipt)
  return receipt


def job_run(output,fit,job,segments,auth):
  prefix=Path('candidates')/job['candidate_id']/job['fold']
  root,original=output/prefix,fit/prefix
  if (root/'manifest.json').exists():
    return verify_job(root,job,auth)
  # Verify EVERY horizon before any prediction for this job.
  pops={h:replay.require_anchor(segments,job['candidate_id'],h,
    job['one_step'] if h==1 else job['rollout'][str(h)]) for h in (1,*m.HORIZONS)}
  model=load_model(original,job)
  jm=read.read_json(original/'manifest.json')
  receipts={}
  for h in (1,*m.HORIZONS):
    name='one-step' if h==1 else f'rollout-{h}'
    receipts[name]=population(root,original,jm,pops[h],job['candidate_id'],model,h,
      job['one_step'] if h==1 else job['rollout'][str(h)],
      job['one_step_buffers'] if h==1 else job['rollout_buffers'][str(h)])
  result=p.seal({'schema':'EMPIRICAL_S2_RI_ATTRIBUTION_EVIDENCE_V1',
    'candidate_id':job['candidate_id'],'fold':job['fold'],'original_job_receipt_sha256':job['receipt_sha256'],
    'model_sha256':job['model_receipt_sha256'],'normalizer_sha256':job['normalizer_receipt_sha256'],
    'coefficient_sha256':job['coefficient_sha256'],'authorization_sha256':auth['receipt_sha256'],
    'populations':{n:v['receipt_sha256'] for n,v in receipts.items()},
    'replay_equality':'FROZEN_MODEL_REPLAY_EXACT_MATCH','context_complete':True,'path_complete':True,
    'historical_gate':job['gate'],'gate_recomputed':False,'selection_run':False})
  store.write_json(root/'receipt.json',result)
  names=['receipt.json']
  for name,value in receipts.items():
    names.extend([name+'/receipt.json',*[name+'/'+k+'.npy' for k in value['arrays']]])
  store.finish(root,names,{'schema':'EMPIRICAL_S2_RI_RECONSTRUCTION_JOB_MANIFEST_V1',
    'job_receipt_sha256':result['receipt_sha256'],'authorization_sha256':auth['receipt_sha256']})
  return result



def verify_array_bytes(path,binding,original_sha=None):
  """NPY header plus opaque byte hashing; no numerical array loading on resume."""
  if set(binding) != {'dtype','shape','order','array_sha256','file_sha256'}:
    raise ValueError('EXACT_ARRAY_BINDING_REQUIRED')
  if (type(binding['dtype']) is not str or type(binding['shape']) is not list
      or not all(type(v) is int and v>=0 for v in binding['shape'])
      or binding['order']!='C'
      or any(type(binding[k]) is not str or re.fullmatch('[0-9a-f]{64}',binding[k]) is None
             for k in ('array_sha256','file_sha256'))):
    raise ValueError('EXACT_TYPED_ARRAY_BINDING_REQUIRED')
  with storage.safe(path).open('rb') as stream:
    version=np.lib.format.read_magic(stream)
    if version!=(1,0):
      raise ValueError('FROZEN_NPY_VERSION_REQUIRED')
    shape,fortran,dtype=np.lib.format.read_array_header_1_0(stream)
    if dtype.hasobject or fortran or dtype.str!=binding['dtype'] or list(shape)!=binding['shape']:
      raise ValueError('ARRAY_HEADER_BINDING_CONFLICT')
    digest=hashlib.sha256()
    size=0
    for block in iter(lambda:stream.read(1024*1024),b''):
      size+=len(block)
      digest.update(block)
    if size!=int(np.prod(shape,dtype=np.int64))*dtype.itemsize or digest.hexdigest()!=binding['array_sha256']:
      raise ValueError('ARRAY_PAYLOAD_BINDING_CONFLICT')
  if original_sha is not None and binding['array_sha256']!=original_sha:
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_REPLAY_DIVERGENCE')


def require_field_binding(key,binding,count,horizon,length):
  integer=set(ONE_NEW)-{'predicted_next_tick_continuous','hold_last_next_tick'}
  integer |= {'hold_last_next_tick','projected','initial_tick','target_endpoint_tick','observed_path','projected_path',
              'hold_last_path','anchor_index','anchor_order_index','prior_delta_tick','s2_ri_run_id','within_run_index'}
  expected_dtype=('<i8' if key in integer else '|S64' if key in ('anchor_route_id','anchor_segment_sha')
                  else '|b1' if key in ('rail','model_eligible') else '|i1' if key=='speed_bin_code' else '<f8')
  shape=[count,horizon+1] if key in ('observed_path','projected_path','hold_last_path') else (
    [count,length] if key=='command_history' else [count])
  if binding['dtype']!=expected_dtype or binding['shape']!=shape or binding['order']!='C':
    raise ValueError('EXACT_POPULATION_FIELD_SHAPE_REQUIRED')

def verify_job(root,job,auth):
  manifest=store.verify_manifest(root)
  receipt=read.read_json(root/'receipt.json')
  if (receipt['original_job_receipt_sha256'] != job['receipt_sha256']
      or receipt['authorization_sha256'] != auth['receipt_sha256']
      or manifest['job_receipt_sha256'] != receipt['receipt_sha256']
      or receipt['candidate_id'] != job['candidate_id'] or receipt['fold'] != job['fold']
      or receipt['model_sha256'] != job['model_receipt_sha256']
      or receipt['normalizer_sha256'] != job['normalizer_receipt_sha256']
      or receipt['historical_gate'] != job['gate']):
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
  if (receipt['replay_equality']!='FROZEN_MODEL_REPLAY_EXACT_MATCH'
      or receipt['context_complete'] is not True or receipt['path_complete'] is not True
      or receipt['gate_recomputed'] is not False or receipt['selection_run'] is not False
      or receipt['coefficient_sha256']!=job['coefficient_sha256']):
    raise ValueError('EXACT_REPLAY_RECEIPT_REQUIRED')
  names={'receipt.json'}
  for h in (1,*m.HORIZONS):
    name='one-step' if h==1 else f'rollout-{h}'
    value=read.read_json(root/name/'receipt.json')
    hist=job['one_step'] if h==1 else job['rollout'][str(h)]
    required=set(CONTEXT_FIELDS)|set(ONE_FIELDS if h==1 else ROLL_FIELDS)|set(ONE_NEW if h==1 else ROLL_NEW)
    if (set(value['arrays']) != required or value['anchor_sha256'] != hist['anchor_sha256']
        or value['comparator_anchor_sha256'] != hist['comparator_anchor_sha256']
        or value['count'] != hist['count'] or value['horizon'] != h
        or value['receipt_sha256'] != receipt['populations'][name] or value['metric_equality'] is not True
        or value['context_complete'] is not True or value['path_complete'] is not (h!=1)):
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_INCOMPLETE')
    originals=job['one_step_buffers'] if h==1 else job['rollout_buffers'][str(h)]
    if value['original_equality'] != {k:{'original_sha256':v,'reconstructed_sha256':v,'exact_equal':True} for k,v in originals.items()}:
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_REPLAY_DIVERGENCE')
    for key,b in value['arrays'].items():
      path=name+'/'+key+'.npy'
      if manifest['files'].get(path) != b['file_sha256']:
        raise ValueError('ATTRIBUTION_RECONSTRUCTION_INPUT_DRIFT')
      require_field_binding(key,b,value['count'],h,m.parameters(job['candidate_id'])[1])
      verify_array_bytes(root/path,b,originals.get(key))
      names.add(path)
    names.add(name+'/receipt.json')
  if set(manifest['files']) != names:
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INCOMPLETE')
  return receipt


def verify_run(root,jobs,auth):
  manifest=store.verify_manifest(root)
  receipts=[verify_job(root/'candidates'/j['candidate_id']/j['fold'],j,auth) for j in jobs]
  result=read.read_json(root/'results.json')
  if (manifest['authorization_sha256'] != auth['receipt_sha256']
      or manifest['results_sha256'] != result['receipt_sha256'] or result['jobs'] != receipts
      or len(receipts)!=32 or manifest['status']!=SUCCESS):
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INCOMPLETE')
  expected={'results.json'}
  for j in jobs:
    prefix=f"candidates/{j['candidate_id']}/{j['fold']}/"
    local=read.read_json(root/prefix/'manifest.json')
    expected.update(prefix+n for n in [*local['files'],'manifest.json'])
  if set(manifest['files'])!=expected:
    raise ValueError('ATTRIBUTION_RECONSTRUCTION_INCOMPLETE')
  return manifest


def run(fit,source,derived,output,replica):
  check_environment()
  if replica not in ('repeat-1','repeat-2'):
    raise ValueError('EXACT_TWO_INDEPENDENT_RUNS_REQUIRED')
  with replay.firewall():
    auth,jobs,records,fm,pins=admit(fit,source,derived,output)
    root=output/replica
    if (root/'manifest.json').exists():
      return verify_run(root,jobs,auth)
    routes=load_routes(records,auth)
    receipts=[]
    for job in jobs:
      receipts.append(job_run(root,fit,job,routes[job['development_route']],auth))
      print(json.dumps({'candidate':job['candidate_id'],'fold':job['fold'],'replay':'EXACT_MATCH'}),flush=True)
    verify_inputs(fit,source,derived,fm,pins)
    result=p.seal({'schema':'EMPIRICAL_S2_RI_RECONSTRUCTION_RESULTS_V1',
      'authorization_sha256':auth['receipt_sha256'],'jobs':receipts,'job_count':32,'status':SUCCESS,
      'input_bytes_unchanged':True,'rate_dependency':'NONE','model_refit_calls':0,
      'normalizer_refit_calls':0,'candidate_selection_calls':0,'raw_log_openings':0,'qlog_openings':0,
      'holdout_openings':0,'failure_attribution':'NOT_RUN','hurdle_trigger':'NOT_EVALUATED',
      'historical_verdict':'S2_RI_NO_ADMISSIBLE_CANDIDATE'})
    store.write_json(root/'results.json',result)
    names=['results.json']
    for job in jobs:
      prefix=f"candidates/{job['candidate_id']}/{job['fold']}/"
      local=read.read_json(root/prefix/'manifest.json')
      names.extend(prefix+n for n in [*local['files'],'manifest.json'])
    return store.finish(root,names,{'schema':'EMPIRICAL_S2_RI_RECONSTRUCTION_MANIFEST_V1',
      'authorization_sha256':auth['receipt_sha256'],'results_sha256':result['receipt_sha256'],
      'job_count':32,'status':SUCCESS})


def main():
  parser=argparse.ArgumentParser(description=__doc__)
  for key in ('fit','source','derived','output'):
    parser.add_argument('--'+key,type=Path,required=True)
  parser.add_argument('--replica',choices=('repeat-1','repeat-2'),required=True)
  args=parser.parse_args()
  result=run(args.fit,args.source,args.derived,args.output,args.replica)
  print(json.dumps({'status':result['status'],'manifest_sha256':result['receipt_sha256']}))


if __name__=='__main__':
  main()
