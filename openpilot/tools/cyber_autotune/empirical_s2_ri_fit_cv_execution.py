"""Authorized retrospective S2-RI execution; no raw logs, qlog or pooled refit."""
import argparse
import json
import os
from pathlib import Path

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_s2_ri_schema as derived_schema
from openpilot.tools.cyber_autotune import empirical_s2_ri_policy as design_policy
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_store as store
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_gates as gates

# Fixed before empirical execution; chunk size changes require invalidation/rerun.
ROLLOUT_CHUNK = 512


def load_routes(records,authorization):
  p.verify(authorization)
  if not authorization.get('retrospective_fit_cv_authorized') or authorization['array_access_before_seal']:
    raise ValueError('SEALED_EXECUTION_AUTHORIZATION_REQUIRED')
  denied = set(authorization['qlog_deny_content_sha256'])
  if any(s['segment_sha256'] in denied for _,s,_,_ in records):
    raise ValueError('QLOG_CAUSAL_ADMISSION_FORBIDDEN')
  routes = {rid:[] for rid in authorization['routes']}
  for base,segment,local_root,local in records:
    n = segment['arrays']['grid_time_ns']['shape'][0]
    derived_schema.validate_derived(local,local_root,design_policy.policy()['receipt_sha256'],segment['receipt_sha256'],n)
    d = {k:read.read_array(local_root/read.array_name(k),local['arrays'][k]) for k in (
      'angle_tick','streak_all','model_eligible','s2_ri_causal_run_id','within_s2_ri_causal_run_index')}
    a = {k:read.read_array(base/'arrays'/read.array_name(k),segment['arrays'][k])
         for k in ('command.normalized','state.speed_mps','grid_time_ns')}
    good = d['model_eligible']
    continuity = np.r_[False,(np.diff(a['grid_time_ns']) == 10_000_000)
      & (d['s2_ri_causal_run_id'][1:] == d['s2_ri_causal_run_id'][:-1])
      & (np.diff(d['within_s2_ri_causal_run_index']) == 1)]
    starts = good & ~(continuity & np.r_[False,good[:-1]])
    index = np.arange(n)
    latest_start = np.maximum.accumulate(np.where(starts,index,-1))
    expected_streak = np.where(good,index-latest_start+1,0)
    if not np.array_equal(expected_streak,d['streak_all']):
      raise ValueError('S2_RI_HISTORY_CONTINUITY_CONFLICT')
    routes[segment['route_id']].append({'segment_sha256':segment['segment_sha256'],
      'tick':d['angle_tick'],'streak':d['streak_all'],
      'command':a['command.normalized'],'speed':a['state.speed_mps']})
  return routes


def anchor_binding(segments,candidate,horizon):
  blocks = [(s,m.anchors(s,candidate,horizon)) for s in segments]
  digest = p.sha(p.canonical([{'segment_sha256':s['segment_sha256'],
    'count':len(ix),'indices_sha256':p.sha(ix.tobytes())} for s,ix in blocks]))
  return blocks,digest,sum(len(ix) for _,ix in blocks)


def design(segments,candidate):
  blocks,digest,n = anchor_binding(segments,candidate,1)
  _,length = m.parameters(candidate)
  x = np.concatenate([m.features(s,ix,candidate) for s,ix in blocks]) if n else np.empty((0,2*length+3))
  current = np.concatenate([s['tick'][ix] for s,ix in blocks])
  target = np.concatenate([s['tick'][ix+1] for s,ix in blocks])
  return x,current,target,digest


def save_arrays(root,arrays):
  return {k:storage.array_write(root/(k+'.npy'),np.ascontiguousarray(v)) for k,v in arrays.items()}


def rollout(segments,candidate,model,horizon):
  blocks,digest,n = anchor_binding(segments,candidate,horizon)
  if n < m.MIN_SUPPORT:
    raise ValueError('CANDIDATE_FOLD_INSUFFICIENT_SUPPORT')
  d,length = m.parameters(candidate)
  predictions,initial,actual = [],[],[]
  for s,indices in blocks:
    for start in range(0,len(indices),ROLLOUT_CHUNK):
      ix = indices[start:start+ROLLOUT_CHUNK]
      ticks = s['tick'][ix[:,None]+np.arange(-length,1)]
      command = s['command'][ix[:,None]+np.arange(-d-length+1,horizon-d)]
      speed = s['speed'][ix[:,None]+np.arange(horizon)]
      predictions.append(m.recursive(ticks,command,speed,candidate,model,horizon))
      initial.append(s['tick'][ix])
      actual.append(s['tick'][ix+horizon])
  prediction,baseline,target = map(np.concatenate,(predictions,initial,actual))
  error = (prediction-target).astype(np.float64)
  comparator_error = (baseline-target).astype(np.float64)
  return {'count':n,'anchor_sha256':digest,'comparator_anchor_sha256':digest,
          'candidate':m.metrics(error),'comparator':m.metrics(comparator_error)}, {
    'projected':prediction,'error':error,'comparator_error':comparator_error}


def execute_job(root,candidate,fold,routes,auth):
  path = root/'candidates'/candidate/fold['name']
  if (path/'manifest.json').exists():
    return verify_job(path,candidate,fold,auth)[0]
  result = {'schema':'EMPIRICAL_S2_RI_FOLD_RESULT_V1','candidate_id':candidate,'fold':fold['name'],
    'train_route':fold['train'],'development_route':fold['development'],
    'authorization_sha256':auth['receipt_sha256'],'policy_sha256':store.POLICY_SHA,
    'status':'PASS','reason':None,'solver_executed':False,'one_step':None,'rollout':{},
    'normalizer_receipt_sha256':None,'model_receipt_sha256':None,'coefficient_sha256':None,'numerics':None}
  files = []
  try:
    x,train_current,train_target,train_sha = design(routes[fold['train']],candidate)
    result['train_count'],result['train_anchor_sha256'] = len(x),train_sha
    if len(x) < x.shape[1]:
      raise ValueError('CANDIDATE_FOLD_INSUFFICIENT_SUPPORT')
    model = m.fit(x,(train_target-train_current).astype(np.float64),role='TRAIN',
                  on_solve=lambda: result.update(solver_executed=True))
    norm = model['normalizer']
    norm_bindings = save_arrays(path/'normalizer',norm)
    norm_receipt = p.seal({'schema':'EMPIRICAL_S2_RI_TRAIN_NORMALIZER_V1','candidate_id':candidate,
      'fold':fold['name'],'train_route':fold['train'],'train_anchor_sha256':train_sha,
      'row_count':len(x),'arrays':norm_bindings,
      'effective_x_sha256':p.sha(model['effective_x'].tobytes()),'authorization_sha256':auth['receipt_sha256']})
    store.write_json(path/'normalizer/receipt.json',norm_receipt)
    files.extend(['normalizer/receipt.json',*[f'normalizer/{k}.npy' for k in norm_bindings]])
    model_bindings = save_arrays(path/'model',{k:model[k] for k in ('coefficients','nominal_coefficients')})
    model_receipt = p.seal({'schema':'EMPIRICAL_S2_RI_FOLD_MODEL_V1','candidate_id':candidate,'fold':fold['name'],
      'train_route':fold['train'],'normalizer_sha256':norm_receipt['receipt_sha256'],
      'policy_sha256':store.POLICY_SHA,'candidate_sha256':auth['candidate_pins'][candidate],
      'arrays':model_bindings,'rank':model['rank'],'numpy_version':np.__version__,
      'rcond':None,'interpretation':'EMPIRICAL_PREDICTIVE_PARAMETERS','pooled_refit':False})
    store.write_json(path/'model/receipt.json',model_receipt)
    files.extend(['model/receipt.json',*[f'model/{k}.npy' for k in model_bindings]])
    result.update(normalizer_receipt_sha256=norm_receipt['receipt_sha256'],model_receipt_sha256=model_receipt['receipt_sha256'],
      coefficient_sha256=model_bindings['nominal_coefficients']['array_sha256'],
      numerics={'nominal_columns':x.shape[1],'effective_columns':len(norm['effective']),
        'rank':model['rank'],'condition_number':model['condition'],'constant_column_count':int(norm['constant'].sum())})
    del x
    dev,current,target,dev_sha = design(routes[fold['development']],candidate)
    result['development_count'],result['development_anchor_sha256'] = len(dev),dev_sha
    if len(dev) < m.MIN_SUPPORT:
      raise ValueError('CANDIDATE_FOLD_INSUFFICIENT_SUPPORT')
    result['development_constant_drift_columns'] = int(sum(np.any(dev[:,j] != norm['mean'][j]) for j in np.flatnonzero(norm['constant'])))
    metric,buffers = m.one_step(dev,current,target,model)
    bindings = save_arrays(path/'one-step',buffers)
    files.extend(f'one-step/{k}.npy' for k in bindings)
    result['one_step_buffers'] = {k:v['array_sha256'] for k,v in bindings.items()}
    result['one_step'] = {'count':len(dev),'anchor_sha256':dev_sha,'comparator_anchor_sha256':dev_sha,**metric}
    del dev
    for horizon in m.HORIZONS:
      metric,buffers = rollout(routes[fold['development']],candidate,model,horizon)
      bindings = save_arrays(path/f'rollout-{horizon}',buffers)
      files.extend(f'rollout-{horizon}/{k}.npy' for k in bindings)
      result['rollout'][str(horizon)] = metric
      result.setdefault('rollout_buffers',{})[str(horizon)] = {k:v['array_sha256'] for k,v in bindings.items()}
  except (ValueError,np.linalg.LinAlgError,FloatingPointError) as error:
    reason = str(error)
    # Only explicitly classified numerical/precondition failures may continue.
    if not any(k in reason for k in ('RANK','NUMERICAL','INSUFFICIENT_SUPPORT','SVD did not converge')):
      raise
    result['reason'] = reason
    result['status'] = ('INSUFFICIENT_SUPPORT' if 'INSUFFICIENT_SUPPORT' in reason else
                        'PRECONDITION_FAILURE' if 'PRECONDITION' in reason else 'NUMERICAL_FAILURE')
  result['gate'] = gates.fold_gate(result)
  receipt = p.seal(result)
  store.write_json(path/'receipt.json',receipt)
  store.finish(path,[*files,'receipt.json'],{'schema':'EMPIRICAL_S2_RI_JOB_MANIFEST_V1','receipt_sha':receipt['receipt_sha256']})
  return receipt



def verify_job(path,candidate,fold,auth):
  manifest = store.verify_manifest(path)
  receipt = read.read_json(path/'receipt.json')
  if (manifest['schema'] != 'EMPIRICAL_S2_RI_JOB_MANIFEST_V1' or manifest.get('receipt_sha') != receipt['receipt_sha256']
      or receipt['schema'] != 'EMPIRICAL_S2_RI_FOLD_RESULT_V1' or receipt['candidate_id'] != candidate
      or receipt['fold'] != fold['name'] or receipt['train_route'] != fold['train']
      or receipt['development_route'] != fold['development'] or receipt['authorization_sha256'] != auth['receipt_sha256']
      or receipt['policy_sha256'] != store.POLICY_SHA or receipt['gate'] != gates.fold_gate(receipt)):
    raise ValueError('EXACT_RESUME_JOB_IDENTITY_REQUIRED')
  expected = {'receipt.json'}
  for name in ('normalizer','model'):
    digest = receipt[name+'_receipt_sha256']
    if digest is not None:
      value = read.read_json(path/name/'receipt.json')
      if value['receipt_sha256'] != digest:
        raise ValueError('EXACT_RESUME_MODEL_LINEAGE_REQUIRED')
      expected.add(name+'/receipt.json')
      for field,binding in value['arrays'].items():
        filename = name+'/'+read.array_name(field)
        if manifest['files'].get(filename) != binding['file_sha256']:
          raise ValueError('EXACT_RESUME_ARRAY_BINDING_REQUIRED')
        expected.add(filename)
  for name,bindings in [('one-step',receipt.get('one_step_buffers',{})),
                        *[(f'rollout-{h}',b) for h,b in receipt.get('rollout_buffers',{}).items()]]:
    expected.update(name+'/'+read.array_name(k) for k in bindings)
  if set(manifest['files']) != expected:
    raise ValueError('EXACT_COMPLETE_JOB_FILE_SET_REQUIRED')
  return receipt,manifest


def verify_run(path,auth,folds):
  manifest = store.verify_manifest(path)
  results = read.read_json(path/'results.json')
  selection = read.read_json(path/'selection.json')
  if (manifest['schema'] != 'EMPIRICAL_S2_RI_FIT_CV_MANIFEST_V1'
      or manifest.get('authorization_sha256') != auth['receipt_sha256']
      or results.get('authorization_sha256') != auth['receipt_sha256']
      or results.get('policy_sha256') != store.POLICY_SHA or manifest.get('job_count') != 32
      or manifest.get('results_sha256') != results['receipt_sha256']
      or manifest.get('selection_sha256') != selection['receipt_sha256']):
    raise ValueError('EXACT_RESUME_EXECUTION_IDENTITY_REQUIRED')
  expected = {'results.json','selection.json'}
  jobs = []
  for candidate in m.CANDIDATES:
    for fold in folds:
      relative = f"candidates/{candidate}/{fold['name']}/"
      job,local = verify_job(path/relative,candidate,fold,auth)
      jobs.append(job)
      expected.update(relative+n for n in [*local['files'],'manifest.json'])
  computed_selection = p.seal({'schema':'EMPIRICAL_S2_RI_SELECTION_RESULT_V1',**gates.select(jobs)})
  if (set(manifest['files']) != expected or jobs != results['jobs']
      or selection != computed_selection or results['job_count'] != 32
      or results['solver_executed_jobs'] != sum(j['solver_executed'] for j in jobs)):
    raise ValueError('EXACT_COMPLETE_RESUME_RESULT_REQUIRED')
  return manifest


def run(source,derived,output,replica):
  if replica not in ('repeat-1','repeat-2'):
    raise ValueError('EXACT_TWO_REPLICAS_REQUIRED')
  if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')) or np.__version__ != '2.5.3':
    raise ValueError('FROZEN_SINGLE_THREAD_NUMPY_ENVIRONMENT_REQUIRED')
  auth,bundle,records,source_files,derived_files = store.admit(source,derived,output)
  path = output/replica
  read.verify_files(source,source_files)
  read.verify_files(derived,derived_files)
  if (path/'manifest.json').exists():
    return verify_run(path,auth,bundle['empirical-s2-ri-fitting-policy-v1.json']['folds'])
  routes = load_routes(records,auth)
  jobs = []
  for candidate in m.CANDIDATES:
    for fold in bundle['empirical-s2-ri-fitting-policy-v1.json']['folds']:
      result = execute_job(path,candidate,fold,routes,auth)
      jobs.append(result)
      print(json.dumps({'candidate':candidate,'fold':fold['name'],'status':result['status'],
                        'gate':result['gate']['pass']}),flush=True)
  selection = p.seal({'schema':'EMPIRICAL_S2_RI_SELECTION_RESULT_V1',**gates.select(jobs)})
  summary = p.seal({'schema':'EMPIRICAL_S2_RI_FIT_CV_RESULTS_V1','authorization_sha256':auth['receipt_sha256'],
    'policy_sha256':store.POLICY_SHA,'jobs':jobs,'selection_sha256':selection['receipt_sha256'],
    'solver_executed_jobs':sum(j['solver_executed'] for j in jobs),'job_count':len(jobs),
    'qlog_support':0,'rate_dependency':'NONE','raw_logs_opened':0,'holdout_openings':0,'pooled_refit':False})
  store.write_json(path/'results.json',summary)
  store.write_json(path/'selection.json',selection)
  read.verify_files(source,source_files)
  read.verify_files(derived,derived_files)
  names = ['results.json','selection.json']
  for candidate in m.CANDIDATES:
    for fold in ('FOLD_A','FOLD_B'):
      job_root = path/'candidates'/candidate/fold
      manifest = store.verify_manifest(job_root)
      prefix = job_root.relative_to(path).as_posix()+'/'
      names.extend(prefix+n for n in [*manifest['files'],'manifest.json'])
  return store.finish(path,names,{'schema':'EMPIRICAL_S2_RI_FIT_CV_MANIFEST_V1',
    'authorization_sha256':auth['receipt_sha256'],'results_sha256':summary['receipt_sha256'],
    'selection_sha256':selection['receipt_sha256'],'job_count':32,
    'input_bytes_unchanged':True,'status':'S2_RI_RETROSPECTIVE_FIT_AND_CV_COMPLETE'})


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  for name in ('source','derived','output'):
    parser.add_argument('--'+name,type=Path,required=True)
  parser.add_argument('--replica',choices=('repeat-1','repeat-2'),required=True)
  args = parser.parse_args()
  result = run(args.source,args.derived,args.output,args.replica)
  print(json.dumps({'status':result['status'],'manifest_sha256':result['receipt_sha256']}))


if __name__ == '__main__':
  main()
