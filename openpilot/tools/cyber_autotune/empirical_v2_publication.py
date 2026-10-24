"""Aggregate-only V2 evidence; raw signals and coefficients stay private."""

import copy
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_source_publication as old

PINS = {
  'empirical-plant-v2-command-bridge-v1.json': 'f248a6707aeb4610cb837ec4a6134ff43dc807ec2d2ea1ef51322f53849027e5',
  'empirical-plant-v2-execution-integrity-v1.json': '68a8e2b2c410d4bdad80d4a7f3170d81b92f699453f3e8c138d84015efb17b0b',
  'empirical-plant-v2-model-freeze-v1.json': '0182638b138d4fc1abe590641f294716bfa64d55e1eee3402abe12f51464af50',
  'empirical-plant-v2-numeric-authorization-v1.json': 'fcaee143ecbd280be1ff0c16c19c02b16d47d248b41a6b5b30220f91c680e17a',
  'empirical-plant-v2-route-coverage-v1.json': '960cddddab147cbd15188683a2bfe4331c6d66e0059d27ef16cd8ef7c3770f11',
  'empirical-plant-v2-stage-a-selection-v1.json': '8718bf0e0cbf0ce09f117745ee311fa222323b7f4aa4057f48b500b0459e23c8',
  'empirical-plant-v2-train-dev-readiness-v1.json': 'ef8e036fb6963e0461fd0878f4b30e3a2e32a36e6fd51feeb4495de8aff61f06',
  'empirical-plant-v2-train-dev-split-v1.json': '05bbdae01bcf22bab814ac2545514e18eff28afc346e77f1d1d0bceb8198c81f',
  'empirical-plant-v2-yaw-admission-v1.json': '941af7be79213d21e3fbcdaac78d86b769d12e9a674f74116c281d416c02c490',
  'future-empirical-plant-v2-holdout-evaluation-v1.json': '6119dd6a40700318cca9d151ece2effabdab1e850e0cabe807c568e02e2d1cd2',
}


def candidate(record):
  model=record['model']
  evaluation=copy.deepcopy(record.get('evaluation'))
  if evaluation and evaluation.get('one_step',{}):
    # Zero support is unavailable, not evidence of bounded validation. Keep raw private receipt unchanged.
    if evaluation['one_step']['model']['count']==0:
      evaluation['status']='UNAVAILABLE_NO_DEVELOPMENT_SUPPORT'
      evaluation['finite_horizon_bounded']=None
    for horizon in evaluation.get('rollout',{}).values():
      if horizon['model']['count']==0:
        horizon['finite_bounded']=None
  return {'config':model['config'],'train_support':model['count'],'fit_status':model['status'],
          'development':record['development'],'evaluation':evaluation,
          'parameter_count':len(model['coefficients']) if model['coefficients'] is not None else None}


def stage(table, name, models):
  return p.seal({'schema':'EMPIRICAL_PLANT_V2_'+name+'_SELECTION_V1', 'holdout_evaluated':False,
    'bins':{b:{'state':x['state'],'units':x['units'],'common_development_rows':x['common_development_rows'],
      'candidates':[candidate(row) for row in x['candidates']],
      'selected':candidate(x['selected']) if x['selected'] is not None else None,
      'selected_model_sha256':models.get(b)} for b,x in table.items()},
    'no_reselection_after_holdout':True,'minimum_development_support':201,
    'family_policy_sha256':p.family_policy()['receipt_sha256'],
    'metric_policy_sha256':p.metric_policy()['receipt_sha256']})


def readiness(result, frozen_sha, package_sha, historical):
  return p.seal({'schema':'EMPIRICAL_PLANT_V2_TRAIN_DEV_READINESS_V1',
    'status':'EMPIRICAL_PLANT_V2_TRAIN_DEV_GENERATION_COMPLETE',
    'numeric_route_count':len(result['routes']),'stage_a_pooling_allowed':result['stage_a_pooling_allowed'],
    'stage_a_states':{b:x['state'] for b,x in result['stage_a'].items()},
    'stage_a_state':'STAGE_A_MODEL_FROZEN_AWAITING_HOLDOUT' if any(x['selected'] for x in result['stage_a'].values())
      else 'STAGE_A_MODEL_SELECTION_BLOCKED',
    'stage_b_state':result['stage_b_state'],'yaw_state':result['yaw_admission']['state'],
    'model_freeze_sha256':frozen_sha,'holdout_package_sha256':package_sha,
    'future_holdout':'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED','one_time_opening_state':'CLOSED',
    'holdout_opened':False,'holdout_evaluated':False,'plant_ready':False,
    'stage_c':'NOT_RUN','candidate_evaluation':'NOT_RUN','ta_empirical_execution':'NOT_RUN','sg_empirical_execution':'NOT_RUN',
    'historical':historical['historical'],'calibration_blockers':p.BLOCKERS,
    'sealed_reference':'NOT_GENERATED','vehicle':['NOT_READY','REAL_VEHICLE_UNVERIFIED','VEHICLE_ACTIVATION_BLOCKED']})


def derive(store):
  store=Path(store)
  public=old.load()
  split=prior.read(store/'split.json')
  auth=prior.read(store/'authorization.json')
  result=prior.read(store/'train-dev-results.json')
  freeze=prior.read(store/'model-freeze.json')
  package=prior.read(store/'holdout-package.json')
  repeat=prior.read(store/'repeatability.json')
  if (result['split_sha256']!=split['receipt_sha256'] or result['authorization_sha256']!=auth['receipt_sha256']
      or freeze['result_sha256']!=result['receipt_sha256'] or package['model_freeze_sha256']!=freeze['receipt_sha256']
      or repeat['result_sha256']!=result['receipt_sha256'] or not repeat['exact_result_chain_match']):
    raise ValueError('V2_PUBLIC_CHAIN_DRIFT')
  outputs={
    'empirical-plant-v2-train-dev-split-v1.json':split,
    'empirical-plant-v2-execution-integrity-v1.json':repeat,
    'empirical-plant-v2-numeric-authorization-v1.json':auth,
    'empirical-plant-v2-route-coverage-v1.json':p.seal({'schema':'EMPIRICAL_PLANT_V2_ROUTE_COVERAGE_V1',
      'split_sha256':split['receipt_sha256'],'routes':result['coverage'],
      'splits':{role:{b:{k:sum(row['bins'][b][k] for row in result['coverage'] if row['role']==role) for k in
          ('total_grid_samples','diagnostic_valid','unavailable','contiguous_45_sample_windows','common_design_rows','ARX1_design_rows','FIR25_design_rows')}
          for b in ('LOW','MEDIUM','HIGH')} for role in ('TRAIN','DEVELOPMENT')},
      'limits_unknown_not_false':True,'minimum_development_rows':201}),
    'empirical-plant-v2-command-bridge-v1.json':p.seal({'schema':'EMPIRICAL_PLANT_V2_COMMAND_BRIDGE_V1',
      'routes':result['bridges'],'pooling_allowed':result['stage_a_pooling_allowed'],
      'semantics':'LOGGED_POST_CONTROLLER_REPRESENTATION_NOT_EPS_ACKNOWLEDGEMENT'}),
    'empirical-plant-v2-yaw-admission-v1.json':p.seal({'schema':'EMPIRICAL_PLANT_V2_YAW_ADMISSION_V1',**result['yaw_admission']}),
    'empirical-plant-v2-stage-a-selection-v1.json':stage(result['stage_a'],'STAGE_A',freeze['models'].get('STAGE_A',{})),
    'empirical-plant-v2-model-freeze-v1.json':freeze,
    'future-empirical-plant-v2-holdout-evaluation-v1.json':package,
    'empirical-plant-v2-train-dev-readiness-v1.json':readiness(result,freeze['receipt_sha256'],package['receipt_sha256'],
      public['empirical-source-audit-readiness-v1.json']),
  }
  if result['stage_b']:
    outputs['empirical-plant-v2-stage-b-selection-v1.json']=stage(result['stage_b'],'STAGE_B',freeze['models'].get('STAGE_B',{}))
  for row in outputs.values():
    p.verify(row)
  return outputs


def load():
  old.load()
  if not PINS:
    raise ValueError('V2_PUBLIC_RECEIPTS_NOT_PINNED')
  outputs={}
  for name,digest in PINS.items():
    row=prior.read(p.PUBLIC/name)
    if row['receipt_sha256']!=digest:
      raise ValueError('V2_PUBLIC_RECEIPT_DRIFT')
    outputs[name]=row
  return outputs
