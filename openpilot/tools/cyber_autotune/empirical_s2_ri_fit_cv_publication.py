"""Aggregate-only publication from two fully verified immutable executions."""
import argparse
from collections import Counter
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_store as store
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_execution as execution
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_gates as gates
from openpilot.tools.cyber_autotune import empirical_s2_ri_fitting_policy as frozen

JOB_FIELDS = ('candidate_id','fold','train_route','development_route','status','reason','solver_executed',
              'normalizer_receipt_sha256','model_receipt_sha256','coefficient_sha256','numerics',
              'one_step','rollout','gate','receipt_sha256')
OPTIONAL_JOB_FIELDS = ('train_count','train_anchor_sha256','development_count','development_anchor_sha256',
                       'development_constant_drift_columns')


def check_metrics(pop,grid=False):
  gates.population(pop,grid)


def public_job(value):
  if any(k not in value for k in JOB_FIELDS):
    raise ValueError('COMPLETE_FOLD_RECEIPT_REQUIRED')
  numerics = value['numerics']
  if numerics is not None:
    expected = {'nominal_columns','effective_columns','rank','condition_number','constant_column_count'}
    if set(numerics) != expected or any(type(v) not in (int,float) for v in numerics.values()):
      raise ValueError('AGGREGATE_NUMERICAL_DIAGNOSTICS_ONLY')
  for pop in value['rollout'].values() if value['rollout'] is not None else ():
    check_metrics(pop)
  if value['one_step'] is not None:
    check_metrics(value['one_step'],True)
  # Never copy model/normalizer array payloads or arbitrary receipt extensions.
  result = {k:value[k] for k in JOB_FIELDS}
  result.update({k:value[k] for k in OPTIONAL_JOB_FIELDS if k in value})
  return result


def same_manifests(first,second):
  if p.canonical(first) != p.canonical(second):
    raise ValueError('S2_RI_FIT_CV_REPEATABILITY_FAILURE')


def build(root):
  bundle = store.contracts()
  auth = read.read_json(root/'authorization.json')
  if auth['policy_sha256'] != store.POLICY_SHA:
    raise ValueError('FROZEN_POLICY_BINDING_REQUIRED')
  folds = bundle[frozen.filename('fitting-policy')]['folds']
  first,second = [execution.verify_run(root/replica,auth,folds) for replica in ('repeat-1','repeat-2')]
  same_manifests(first,second)
  resume = read.read_json(root/'resume-verification.json')
  if (resume['manifest_sha256'] != first['receipt_sha256'] or resume['compute_path_traps_pass'] is not True
      or resume['authorization_sha256'] != auth['receipt_sha256']):
    raise ValueError('ACTUAL_VERIFY_ONLY_RESUME_REQUIRED')
  result = read.read_json(root/'repeat-1/results.json')
  selection = read.read_json(root/'repeat-1/selection.json')
  jobs = [public_job(j) for j in result['jobs']]
  readiness = frozen.load_inputs()[frozen.filename('readiness')]
  preserve_keys = ('dataset','S1','S2','S3','historical_track','historical_grid_verdict','stage_b','ta','sg',
                   'composition','future_holdout','calibration_blockers','sealed_reference','vehicle','closed_loop_bias')
  common = {'authorization_sha256':auth['receipt_sha256'],'policy_sha256':store.POLICY_SHA,
            'private_manifest_sha256':first['receipt_sha256']}
  values = {
    'fit-cv-authorization':p.seal({'schema':'EMPIRICAL_S2_RI_FIT_CV_PUBLIC_AUTHORIZATION_V1',**common,
      'contract_receipts':auth['public_contracts'],'historical_design_pins':auth['historical_design_pins'],
      'rlog_manifest_sha256':auth['rlog_manifest_sha256'],'derived_result_sha256':auth['derived_result_sha256'],
      'source_file_set_sha256':auth['source_file_set_sha256'],'derived_file_set_sha256':auth['derived_file_set_sha256'],
      'executor_sources':auth['executor_sources'],'retrospective_execution_authorized':True,
      'authorization_sealed_before_array_access':True,'metric_clarification':auth['metric_clarification'],
      'qlog_support':0,'holdout':'CLOSED','opening_count':0,'pooled_refit_authorized':False}),
    'fit-cv-job-manifest':p.seal({'schema':'EMPIRICAL_S2_RI_PUBLIC_JOB_MANIFEST_V1',**common,
      'jobs':[{'candidate_id':j['candidate_id'],'fold':j['fold'],'receipt_sha256':j['receipt_sha256'],
               'status':j['status']} for j in jobs],'job_count':32,'candidate_count':16,'fold_count':2,
      'solver_executed_jobs':result['solver_executed_jobs'],'status_counts':dict(Counter(j['status'] for j in jobs))}),
    'fit-cv-results':p.seal({'schema':'EMPIRICAL_S2_RI_PUBLIC_FIT_CV_RESULTS_V1',**common,'jobs':jobs,
      'metric_unit':'SOURCE_GRID_TICKS','continuous_delta_and_next_angle':'SAME_CANONICAL_DELTA_ERROR_BUFFER',
      'interpretation':'RETROSPECTIVE_ROUTE_LEVEL_DEVELOPMENT_ONLY','coefficients':'PRIVATE_ONLY',
      'rollout':'LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT','recursive_state':'PROJECTED_SOURCE_GRID'}),
    'candidate-gates':p.seal({'schema':'EMPIRICAL_S2_RI_CANDIDATE_GATES_V1',**common,
      'candidates':selection['candidates'],'admissible_count':selection['admissible_count'],
      'inadmissible_count':selection['inadmissible_count'],'both_folds_required':True,'epsilon':None}),
    'selection-result':p.seal({'schema':'EMPIRICAL_S2_RI_PUBLIC_SELECTION_RESULT_V1',**common,
      'status':selection['status'],'multiplicity':selection['multiplicity'],'selected_candidate':selection['selected_candidate'],
      'candidates':selection['candidates'],'admissible_count':selection['admissible_count'],
      'final_pooled_refit':'NOT_AUTHORIZED','interpretation':'RETROSPECTIVE_ROUTE_LEVEL_DEVELOPMENT_SELECTION',
      'future_holdout_model_admitted':False}),
    'fit-cv-repeatability':p.seal({'schema':'EMPIRICAL_S2_RI_FIT_CV_REPEATABILITY_V1',**common,
      'status':'FIT_CV_EXACT_REPEATABILITY_PASS','independent_replicas':2,'fold_jobs_per_replica':32,
      'replica_manifest_sha256':[first['receipt_sha256'],second['receipt_sha256']],
      'all_model_normalizer_prediction_rollout_files_exact':True,'all_receipts_metrics_gates_selection_exact':True,
      'input_bytes_unchanged':first['input_bytes_unchanged'],'resume_receipt_sha256':resume['receipt_sha256'],
      'compute_trapped_resume_pass':True}),
    'fit-cv-readiness':p.seal({'schema':'EMPIRICAL_S2_RI_FIT_CV_READINESS_V1',**common,
      'status':'S2_RI_RETROSPECTIVE_FIT_AND_CV_COMPLETE','states':['32_FOLD_JOBS_ACCOUNTED',
        'FIT_CV_EXACT_REPEATABILITY_PASS',selection['status'],selection['multiplicity']],
      'selected_candidate':selection['selected_candidate'],'model_fitting':'RUN_RETROSPECTIVE_ONLY',
      'model_selection':'RETROSPECTIVE_ONLY','admissible_count':selection['admissible_count'],
      'final_pooled_refit':'NOT_RUN_NOT_AUTHORIZED','holdout':'HOLDOUT_OPENING_CLOSED','opening_count':0,
      'no_model_admitted_for_future_holdout':True,'steering_rate_dependency':'NONE','qlog_model_support':0,
      'physical_eps_application':'UNAVAILABLE','search':'SEARCH_NOT_AUTHORIZED',
      **{k:readiness[k] for k in preserve_keys}})}
  return {f'empirical-s2-ri-{k}-v1.json':v for k,v in values.items()}


def publish(root,output):
  values = build(root)
  for name,value in values.items():
    store.write_json(frozen.safe(output/name),value)
  return values


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--store',type=Path,required=True)
  parser.add_argument('--output',type=Path,required=True)
  args = parser.parse_args()
  print('published',len(publish(args.store,args.output)))


if __name__ == '__main__':
  main()
