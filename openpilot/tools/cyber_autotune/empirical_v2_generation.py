"""TRAIN fits, DEVELOPMENT selects; future holdout is never opened."""

import os
import platform
from pathlib import Path
import sys
import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_signal_crosscheck as cross
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_v2_policy as v
from openpilot.tools.cyber_autotune import empirical_v2_signals as signals


def environment():
  keys=('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')
  if any(os.environ.get(k) != '1' for k in keys):
    raise ValueError('FIXED_SINGLE_THREAD_BLAS_REQUIRED_BEFORE_PROCESS_START')
  return {'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),
          'blas':{k:os.environ[k] for k in keys},'solver':v.policy()['solver']}


def pooling_allowed(bridges):
  return len(bridges)==3 and all(x['status']=='ROUTE_COMMAND_BRIDGE_CONFIRMED' for x in bridges)


def select_stage(roles, stage, units):
  if set(roles)!={'TRAIN','DEVELOPMENT'} or stage not in ('STAGE_A','STAGE_B'):
    raise ValueError('TRAIN_DEVELOPMENT_ONLY_NO_HOLDOUT')
  selection=m.select(roles,p.family_policy()['candidates'])
  for record in selection['candidates']:
    model=record['model']
    record['evaluation']=signals.checked_rollout(
      m.evaluate(roles['DEVELOPMENT'],model,selection['static_gain'],selection['train_amplitude_quartiles']),
      sum(len(x['y']) for x in roles['DEVELOPMENT']))
  if selection['selected'] is not None:
    selection['selected']=next(x for x in selection['candidates'] if x['model']==selection['selected']['model'])
  support=len(m.design(roles['DEVELOPMENT'],p.family_policy()['candidates'][0])[1])
  return {**selection, 'stage':stage,'units':units,'common_development_rows':support,
          'state':stage+'_MODEL_FROZEN_AWAITING_HOLDOUT' if selection['selected'] else stage+'_MODEL_SELECTION_BLOCKED',
          'validated':False,'holdout_evaluated':False}


def compact(receipt):
  aligned=receipt['aligned']
  # Preserve all grid indices/gaps for residual diagnostics; discard unrelated Stage A fields.
  rows=[]
  for x in aligned['rows']:
    if x['diagnostic_valid'] and x['gyro_common_valid']:
      rows.append({k:x[k] for k in ('diagnostic_valid','gyro_common_valid','yaw_raw','angle_deg','speed_mps','speed_bin','grid_time_ns')})
    else:
      rows.append({'diagnostic_valid':False,'gyro_common_valid':False,'grid_time_ns':x['grid_time_ns']})
  return {'segment_id':receipt['segment_id'],'aligned':{'rows':rows,'gyro_options':aligned['gyro_options']}}


def yaw_admission(roles, by_route, profile):
  selection=cross.select(roles,profile)
  if selection['hypothesis'] is None:
    return {'state':'YAW_SIGNAL_UNUSABLE','admitted':False,'selection':selection,'route_diagnostics':[]}
  h,c=selection['hypothesis'],selection['gyro_candidate']
  diagnostics=[]
  admitted=selection['unit_supported']
  for rid, receipts in by_route.items():
    diag=cross.analyze(receipts,h,c,profile)
    vectors=cross._vectors(receipts,profile)
    gyro=vectors['gyro'][str(c['lag_samples'])][:,c['axis']]*c['sign']
    zero=m.statistics(-gyro,gyro)
    association=(
      diag['coverage']['valid']>=201
      and diag['gyro']['CORRELATION'] is not None and diag['gyro']['CORRELATION']>0
      and diag['kinematic']['CORRELATION'] is not None and diag['kinematic']['CORRELATION']>0
      and all(diag['gyro'][key]<zero[key] for key in ('RMSE','MAE','P95_ABS')))
    admitted &= association
    diagnostics.append({'route_id':rid,'metrics':diag,'zero_gyro_reference':zero,'association_admitted':bool(association)})
  return {'state':'YAW_UNIT_SUPPORTED_FRAME_PARTIAL' if admitted else 'YAW_UNIT_LIKELY_NOT_CONFIRMED',
          'admitted':bool(admitted),'selection':selection,'route_diagnostics':diagnostics,
          'frame':'DEVICE_AXIS_CORRESPONDENCE_ONLY_NO_INDEPENDENT_RIGID_TRANSFORM',
          'kinematic_support_only':True,'continuous_scale_fitted':False}


def run(store):
  store=Path(store)
  env=environment()
  frozen=v.validate_split(prior.read(store/'split.json'))
  auth=prior.read(store/'authorization.json')
  if auth['code_sha256']!=v.code_identity() or auth['policy']!=v.policy():
    raise ValueError('FROZEN_EXECUTION_IDENTITY_DRIFT')
  stage_roles={b:{'TRAIN':[],'DEVELOPMENT':[]} for b in ('LOW','MEDIUM','HIGH')}
  yaw_roles={'TRAIN':[],'DEVELOPMENT':[]}
  by_route={}
  bridges,coverage,routes=[],[],[]
  all_ok=True
  profile=None
  for route in frozen['routes']:
    rid,role=route['route_id'],route['role']
    receipt=prior.read(store/'routes'/(rid+'.json'))
    if receipt['role']!=role or receipt['split_sha256']!=frozen['receipt_sha256']:
      raise ValueError('ROUTE_ROLE_OR_SPLIT_DRIFT')
    segments=[]
    failures=[]
    for segment in receipt['segments']:
      x=prior.read(store/'segments'/rid/(segment['source_sha256']+'.json'))
      if x['receipt_sha256']!=segment['receipt_sha256'] or x['route_id']!=rid or x['role']!=role:
        raise ValueError('NUMERIC_SEGMENT_IDENTITY_DRIFT')
      v.require_open(store,rid,x['source_sha256'],route['adapter_sha256'])
      if x['status']!='EXTRACTED':
        failures.append({'segment_id':x['segment_id'],'reason_code':x['reason_code']})
        continue
      segments.append(x)
      if profile is None:
        profile=x['profile']
      elif profile != x['profile']:
        raise ValueError('MODEL_PROFILE_MISMATCH')
      for b in stage_roles:
        stage_roles[b][role].extend(signals.actuator_runs([x],b))
      compacted=compact(x)
      yaw_roles[role].append(compacted)
      by_route.setdefault(rid,[]).append(compacted)
    bridge=signals.route_bridge(segments) if segments else {'status':'ROUTE_COMMAND_BRIDGE_UNAVAILABLE'}
    if failures:
      bridge['status']='ROUTE_COMMAND_BRIDGE_PARTIAL'
    bridges.append({'route_id':rid,'role':role,**bridge})
    aggregate={'route_id':rid,'role':role,'segment_count':len(receipt['segments']),
      'extracted_segment_count':len(segments),'rejected_segments':failures,
      'bins':{},'total_grid_samples':sum(x['coverage']['total_grid_samples'] for x in segments),
      'diagnostic_valid':sum(x['coverage']['diagnostic_valid'] for x in segments)}
    aggregate['unavailable']=aggregate['total_grid_samples']-aggregate['diagnostic_valid']
    for b in stage_roles:
      rows=[x['coverage']['bins'][b] for x in segments]
      aggregate['bins'][b]={k:sum(x[k] for x in rows) for k in
        ('total_grid_samples','diagnostic_valid','unavailable','continuous_valid_duration_s','contiguous_45_sample_windows',
         'common_design_rows','ARX1_design_rows','FIR25_design_rows','contiguous_runs')}
      aggregate['bins'][b]['longest_contiguous_samples']=max((x['longest_contiguous_samples'] for x in rows),default=0)
    for key in ('gap_breaks','mask_breaks','speed_bin_breaks','intervention_breaks','segment_boundary_breaks','segment_reset_count',
                'gap_masked_samples','mask_invalid_samples','intervention_masked_samples','gyro_common_valid'):
      aggregate[key]=sum(x['coverage'][key] for x in segments)
    aggregate['segment_boundary_breaks']=max(0,len(segments)-1)
    aggregate['auxiliary_coverage']={}
    for x in segments:
      for key,n in x.get('auxiliary_coverage',{}).items():
        aggregate['auxiliary_coverage'][key]=aggregate['auxiliary_coverage'].get(key,0)+n
    aggregate['safety_limited']=None
    aggregate['curvature_limited']=None
    aggregate['clean_primary_valid']=0
    aggregate['mask_reason_counts_overlapping']={}
    for x in segments:
      for key,n in x['coverage']['mask_reason_counts_overlapping'].items():
        aggregate['mask_reason_counts_overlapping'][key]=aggregate['mask_reason_counts_overlapping'].get(key,0)+n
    coverage.append(aggregate)
    routes.append({'route_id':rid,'receipt_sha256':receipt['receipt_sha256']})
    all_ok &= not failures
    del segments
  allowed=all_ok and pooling_allowed(bridges)
  stage_a={b:select_stage(roles,'STAGE_A','STEERING_WHEEL_ANGLE_DEGREES') for b,roles in stage_roles.items()} if allowed else {}
  admission=yaw_admission(yaw_roles,by_route,profile) if all_ok and profile else {'state':'YAW_SIGNAL_UNUSABLE','admitted':False}
  stage_b={}
  if allowed and admission['admitted']:
    for b in stage_roles:
      roles={role:cross.yaw_runs(receipts,admission['selection']['hypothesis'],profile,b) for role,receipts in yaw_roles.items()}
      stage_b[b]=select_stage(roles,'STAGE_B','YAW_RAD_PER_S_CONDITIONAL_DEVICE_FRAME')
  result=p.seal({'schema':'EMPIRICAL_PLANT_V2_PRIVATE_TRAIN_DEV_RESULTS_V1',
    'split_sha256':frozen['receipt_sha256'],'authorization_sha256':auth['receipt_sha256'],
    'environment':env,'execution_code':v.code_identity(),'routes':routes,'coverage':coverage,'bridges':bridges,
    'stage_a_pooling_allowed':allowed,'stage_a':stage_a,'yaw_admission':admission,'stage_b':stage_b,
    'stage_b_state':'STAGE_B_SIGNAL_ADMISSION_BLOCKED' if not admission['admitted'] else
       ('STAGE_B_MODEL_FROZEN_AWAITING_HOLDOUT' if any(x['selected'] for x in stage_b.values()) else 'STAGE_B_MODEL_SELECTION_BLOCKED'),
    'holdout_opened':False,'stage_c':'NOT_RUN','ta_sg_execution':'NOT_RUN'})
  p.persist(store/'train-dev-results.json',result)
  models={}
  for stage,table in (('STAGE_A',stage_a),('STAGE_B',stage_b)):
    models[stage]={}
    for b,x in table.items():
      if x['selected'] is None:
        continue
      model=p.seal({'schema':'EMPIRICAL_PLANT_V2_PRIVATE_FROZEN_MODEL_V1','stage':stage,'speed_bin':b,
        'model':x['selected']['model'],'units':x['units'],'split_sha256':frozen['receipt_sha256'],
        'source_equivalence_sha256':frozen['source_equivalence_sha256'],
        'full_carparams_sha256':frozen['routes'][0]['full_carparams_sha256'],
        'empirical_profile_sha256':frozen['routes'][0]['empirical_profile_sha256'],
        'timebase_policy_sha256':p.alignment_policy()['receipt_sha256'],'mask_policy_sha256':p.policy()['receipt_sha256'],
        'metric_policy_sha256':p.metric_policy()['receipt_sha256'],'command_yaw_policy_sha256':v.policy()['receipt_sha256'],
        'environment':env,'code_sha256':v.code_identity(),'holdout_evaluated':False})
      p.persist(store/'models'/(stage+'-'+b+'.json'),model)
      models[stage][b]=model['receipt_sha256']
  freeze=p.seal({'schema':'EMPIRICAL_PLANT_V2_MODEL_FREEZE_V1','models':models,
    'result_sha256':result['receipt_sha256'],'split_sha256':frozen['receipt_sha256'],
    'future_holdout':'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED','holdout_opened':False})
  p.persist(store/'model-freeze.json',freeze)
  package=v.holdout_package(frozen,models,freeze['receipt_sha256'])
  p.persist(store/'holdout-package.json',package)
  return result,freeze,package
