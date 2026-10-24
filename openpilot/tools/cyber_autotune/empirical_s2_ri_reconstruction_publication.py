"""Closed aggregate publication after both full replay runs and trapped resume."""
import argparse
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_s2_ri_reconstruction as e
from openpilot.tools.cyber_autotune import empirical_s2_ri_reconstruction_math as r

PREFIX='empirical-s2-ri-'
STATES=['S2_RI_ATTRIBUTION_EVIDENCE_RECONSTRUCTED','FROZEN_MODEL_REPLAY_EXACT_MATCH',
        '32_FOLD_ATTRIBUTION_INPUTS_COMPLETE','FAILURE_ATTRIBUTION_V2_INPUT_READY']


def complete(fit,source,derived,output):
  e.check_environment()
  with r.firewall():
    auth,jobs,_,fm,pins=e.admit(fit,source,derived,output)
    first=e.verify_run(output/'repeat-1',jobs,auth)
    second=e.verify_run(output/'repeat-2',jobs,auth)
    if first!=second:
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_REPEATABILITY_FAILURE')
    # Verify-only resume: no source/model array decode or numerical replay.
    with ExitStack() as stack:
      for obj,names in ((e,('load_routes','load_model')), (e.read,('read_array',)),
                        (r,('one_step','rollout','recursive_path')), (e.m,('predict','project'))):
        for name in names:
          stack.enter_context(patch.object(obj,name,side_effect=AssertionError('RESUME_COMPUTE_FORBIDDEN')))
      resumed=e.run(fit,source,derived,output,'repeat-1')
    if resumed!=first:
      raise ValueError('ATTRIBUTION_RECONSTRUCTION_RESUME_FAILURE')
    e.verify_inputs(fit,source,derived,fm,pins)
    receipt=p.seal({'schema':'EMPIRICAL_S2_RI_RECONSTRUCTION_REPEATABILITY_V1',
      'authorization_sha256':auth['receipt_sha256'],'manifest_sha256':first['receipt_sha256'],
      'independent_runs':2,'run_manifests_byte_exact':True,'array_files_byte_exact':True,
      'receipts_byte_exact':True,'trapped_resume_exact':True,'input_bytes_unchanged':True,
      'raw_qlog_store_hash_claim':'NOT_MADE_UNOPENED','status':'PASS'})
    e.store.write_json(output/'repeatability.json',receipt)
    return build(output,auth,jobs,first,receipt)


def build(output,auth,jobs,manifest,repeatability):
  """Never copy an open dictionary of private values into public evidence."""
  rows=[]
  for job in jobs:
    root=output/'repeat-1/candidates'/job['candidate_id']/job['fold']
    receipt=e.verify_job(root,job,auth)
    populations={}
    for h in (1,*e.m.HORIZONS):
      name='one-step' if h==1 else f'rollout-{h}'
      v=e.read.read_json(root/name/'receipt.json')
      paths={}
      if h!=1:
        for key in ('observed_path','projected_path','hold_last_path','initial_tick','target_endpoint_tick'):
          paths[key]={'sha256':v['arrays'][key]['array_sha256'],'shape':v['arrays'][key]['shape']}
      populations[name]={'count':v['count'],'anchor_sha256':v['anchor_sha256'],
        'comparator_anchor_sha256':v['comparator_anchor_sha256'],
        'replay_equality':v['original_equality'],'metric_equality':v['metric_equality'],
        'paths':paths,'context_fields':list(e.CONTEXT_FIELDS),'context_complete':True,
        'context_set_sha256':p.sha(p.canonical({k:v['arrays'][k]['array_sha256'] for k in e.CONTEXT_FIELDS})),
        'receipt_sha256':v['receipt_sha256']}
    rows.append({'candidate_id':job['candidate_id'],'fold':job['fold'],
      'original_job_receipt_sha256':job['receipt_sha256'],'model_sha256':job['model_receipt_sha256'],
      'normalizer_sha256':job['normalizer_receipt_sha256'],'coefficient_sha256':job['coefficient_sha256'],
      'reconstruction_receipt_sha256':receipt['receipt_sha256'],'populations':populations,
      'historical_gate_preserved':True,'new_gate_evaluation':False})
  common={'authorization_sha256':auth['receipt_sha256'],'private_manifest_sha256':manifest['receipt_sha256'],
    'original_fit_manifest_sha256':e.historical.INPUT_SHA,'executor_sources':e.sources(),
    'historical_verdict':'S2_RI_NO_ADMISSIBLE_CANDIDATE','model_selection':'MODEL_SELECTION_FAILED_CLOSED',
    'failure_attribution':'NOT_RUN','hurdle_trigger':'NOT_EVALUATED','holdout':'CLOSED','opening_count':0,
    'model_refit_calls':0,'normalizer_refit_calls':0,'candidate_selection_calls':0,
    'raw_log_openings':0,'qlog_openings':0,'vehicle_authority':False,'pooled_refit':False}
  def seal(schema,**fields):
    return p.seal({'schema':schema,**common,**fields})
  bundle={
    'attribution-reconstruction-policy-v1':e.policy(),
    'attribution-reconstruction-authorization-v1':auth,
    'attribution-evidence-schema-v1':seal('EMPIRICAL_S2_RI_ATTRIBUTION_EVIDENCE_SCHEMA_V1',
      one_step_fields=[*e.ONE_FIELDS,*e.ONE_NEW,*e.CONTEXT_FIELDS],
      rollout_fields=[*e.ROLL_FIELDS,*e.ROLL_NEW,*e.CONTEXT_FIELDS],
      path_dtype='int64',path_shape='anchor_count x (horizon + 1)',object_dtype_allowed=False,
      observed_source='DIRECT_IMMUTABLE_DERIVED_TICKS',
      projected_source='FROZEN_FOLD_MODEL_AND_NORMALIZER_REPLAY',
      context_role='ATTRIBUTION_ONLY_NOT_MODEL_FEATURE_EXPANSION'),
    'attribution-replay-equivalence-v1':seal('EMPIRICAL_S2_RI_ATTRIBUTION_REPLAY_EQUIVALENCE_V1',
      jobs=rows,job_count=len(rows),status='FROZEN_MODEL_REPLAY_EXACT_MATCH'),
    'attribution-input-completeness-v2':seal('EMPIRICAL_S2_RI_ATTRIBUTION_INPUT_COMPLETENESS_V2',
      job_count=32,one_step_populations=32,rollout_populations=128,
      context_complete=True,full_paths_complete=True,status='32_FOLD_ATTRIBUTION_INPUTS_COMPLETE',
      old_insufficient_verdict='IMMUTABLE_HISTORICAL_INPUT',
      origin='ATTRIBUTION_EVIDENCE_RECONSTRUCTED_AFTER_SEPARATE_AUTHORIZATION'),
    'attribution-reconstruction-repeatability-v1':seal('EMPIRICAL_S2_RI_ATTRIBUTION_RECONSTRUCTION_REPEATABILITY_V1',
      verification_receipt_sha256=repeatability['receipt_sha256'],independent_runs=2,
      byte_exact=True,resume_exact=True,input_bytes_unchanged=True,status='PASS',
      hashed_input_scope='EXACT_FIT_MANIFEST_AND_FROZEN_SOURCE_DERIVED_FILE_PINS',
      raw_qlog_store_hash_claim='NOT_MADE_UNOPENED'),
    'attribution-reconstruction-readiness-v1':seal('EMPIRICAL_S2_RI_ATTRIBUTION_RECONSTRUCTION_READINESS_V1',
      status=e.SUCCESS,states=STATES,rate_dependency='NONE',attribution_v2_authorized=False,
      next_step='SEPARATELY_AUTHORIZED_READ_ONLY_FAILURE_ATTRIBUTION_V2'),
  }
  return {PREFIX+k+'.json':v for k,v in bundle.items()}


def publish(fit,source,derived,output):
  bundle=complete(fit,source,derived,output)
  for name,value in bundle.items():
    e.store.write_json(p.PUBLIC/name,value)
  return bundle


def main():
  parser=argparse.ArgumentParser(description=__doc__)
  for key in ('fit','source','derived','output'):
    parser.add_argument('--'+key,type=Path,required=True)
  args=parser.parse_args()
  bundle=publish(args.fit,args.source,args.derived,args.output)
  print('PUBLISHED',len(bundle))


if __name__=='__main__':
  main()
