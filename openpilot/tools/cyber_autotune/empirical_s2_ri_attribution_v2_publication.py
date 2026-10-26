"""Closed aggregate publication; no per-anchor evidence or executable models."""
import argparse
from contextlib import ExitStack
import math
from pathlib import Path
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_s2_ri_attribution_v2 as e

AGGREGATE_KEYS = set("""
count sae sse rmse mae p95 minimum median p75 p90 p99 maximum mean
population event_count event_rate no_event_count no_event_rate steps
candidate hold_last delta_sae delta_sse candidate_grid hold_last_grid exact_count exact_hit_rate
within_one_tick_count within_one_tick_rate exact_hit_delta counts rates
STATIC_CORRECT_HOLD STATIC_FALSE_MOVE MOVE_MISSED MOVE_DETECTED SIGN_CORRECT SIGN_WRONG PREDICTED_ZERO
detected_sign_accuracy miss_rate ALL STATIC MOVE MOVE_POSITIVE MOVE_NEGATIVE ONE_TICK_MOVE MULTI_TICK_MOVE
static_count less_than_half_count exact_half_count greater_than_half_count half_tick_held half_tick_moved
half_tick_even_current half_tick_odd_current static_absolute_continuous_delta threshold_origin near_half_epsilon
metrics static_fraction confusion static_false_move_rate move_miss_rate sign LOW MEDIUM HIGH RAIL NON_RAIL
PRIOR_STATIC PRIOR_MOVING SAME_DIRECTION REVERSAL counts_exact float_reduction p95_additive
partition_sum_minus_direct_all move_fraction classes projection_boundary context partition_accounting
zero_transition_job_pattern static_false_move rate_in_static continuous_magnitude projected_magnitude
candidate_absolute_error absolute_command_current absolute_command_feature_newest context_counts
PATH_FLAT PATH_MOVED ENDPOINT_STATIC ENDPOINT_ONE_TICK ENDPOINT_MULTI_TICK PATH_MOVED_ENDPOINT_STATIC
fraction cutoff_p95 FALSE_MOTION ties_included interpretation PATH_FLAT_SSE_REGRESSION
PATH_MOVED_SSE_IMPROVEMENT PATH_MOVED_SSE_REGRESSION FALSE_MOTION_PRESENT MISSED_MOTION_PRESENT
horizon partition_counts_exact false_motion rate_in_path_flat projected_move_count_in_path_flat endpoint
missed_motion rate_in_path_moved first_divergence first_false_move path_distributions
observed_move_count projected_move_count observed_reversal_count projected_reversal_count
observed_net_displacement projected_net_displacement final_signed_error final_absolute_error
tail_composition mechanism_states path_partition endpoint_partition
""".split())
AGGREGATE_STRINGS = {
 'ORIGINAL_ANCHOR_ORDER_CONTIGUOUS_FLOAT64_PER_CLASS',
 'FROZEN_DIRECT_HALF_TO_EVEN_PROJECTION_BOUNDARY',
 'TAIL_COMPOSITION_NOT_ADDITIVE_P95_CONTRIBUTION',
}


def validate_aggregate(value):
  if isinstance(value,dict):
    if not set(value)<=AGGREGATE_KEYS:
      raise ValueError('PUBLIC_AGGREGATE_KEYS_REQUIRED')
    for item in value.values():
      validate_aggregate(item)
  elif isinstance(value,str):
    if value not in AGGREGATE_STRINGS:
      raise ValueError('PUBLIC_AGGREGATE_ENUM_REQUIRED')
  elif value is None or type(value) in (int,bool):
    return
  elif type(value) is float and math.isfinite(value):
    return
  else:
    raise ValueError('PUBLIC_AGGREGATE_SCALARS_ONLY')


def complete(source,output):
  e.environment()
  first,second = e.resume(output/'repeat-1'),e.resume(output/'repeat-2')
  if first!=second:
    raise ValueError('FAILURE_ATTRIBUTION_V2_REPEATABILITY_FAILURE')
  auth = e.verify_authorization(output,first)
  e.verify_authorization(output,second)
  if auth['input_identity_sha256']!=e.verify_source(source):
    raise ValueError('FAILURE_ATTRIBUTION_V2_INPUT_IMMUTABILITY_FAILURE')
  with ExitStack() as stack, e.firewall(()):
    for obj,names in ((e,('open_array','load_population','metadata_admission','population')),
                      (e.math,('one_step','rollout','path_arrays'))):
      for name in names:
        stack.enter_context(patch.object(obj,name,side_effect=AssertionError('RESUME_ANALYSIS_FORBIDDEN')))
    resumed = e.run(source,output,'repeat-1')
  if resumed!=first:
    raise ValueError('FAILURE_ATTRIBUTION_V2_RESUME_FAILURE')
  receipt = e.p.seal({'schema':'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_REPEATABILITY_V2',
    'status':'PASS','input_manifest_sha256':e.INPUT_SHA,'output_manifest_sha256':first['receipt_sha256'],
    'independent_runs':2,'byte_exact_arrays':True,'byte_exact_receipts':True,'byte_exact_manifests':True,
    'trapped_resume_exact':True,'input_bytes_unchanged':True,
    'hashed_input_scope':'BOTH_SEALED_RECONSTRUCTION_RUNS_AND_ROOT_AUTHORIZATION_REPEATABILITY',
    'original_fit_causal_qlog_store_hash_claim':'NOT_MADE_UNOPENED'})
  e.write(output/'repeatability.json',receipt)
  return build(output,first,receipt)


def build(output,manifest,repeatability):
  e.verify_authorization(output,manifest)
  summary = e.h.read_json(output/'repeat-1/summary.json')
  e.math.require(summary['receipt_sha256']==manifest['summary_sha256'])
  e.require_jobs(summary['jobs'])
  one,confusion,decomposition,boundary,rollout,divergence,context = [],[],[],[],[],[],[]
  for job in summary['jobs']:
    e.math.require(job['candidate_id'] in e.CANDIDATES and job['fold'] in ('FOLD_A','FOLD_B'))
    root = output/'repeat-1/jobs'/job['candidate_id']/job['fold']
    lineage = {}
    for name in ('one-step',*(f'rollout-{h}' for h in e.HORIZONS)):
      pop = e.h.read_json(root/name/'receipt.json')
      e.math.require(pop['receipt_sha256']==job['population_receipts'][name])
      lineage[name] = {'input_receipt_sha256':pop['input_receipt_sha256'],
        'anchor_sha256':pop['anchor_sha256'],'comparator_anchor_sha256':pop['comparator_anchor_sha256'],
        'stored_input_array_sha256':pop['input_arrays_sha256'],
        'derived_class_arrays_sha256':{k:v['array_sha256'] for k,v in pop['derived_arrays'].items()},
        'attribution_receipt_sha256':pop['receipt_sha256']}
    common = {'candidate_id':job['candidate_id'],'fold':job['fold'],
      'input_job_receipt_sha256':job['input_job_receipt_sha256'],'model_receipt_sha256':job['original_model_sha256'],
      'normalizer_receipt_sha256':job['original_normalizer_sha256'],'lineage':lineage}
    value = job['one_step']
    validate_aggregate(value)
    for value_roll in job['rollout'].values():
      validate_aggregate(value_roll)
    one.append({**common,**{k:value[k] for k in ('count','static_fraction','move_fraction','classes','zero_transition_job_pattern')}})
    confusion.append({**common,**{k:value[k] for k in ('confusion','sign','static_false_move')}})
    decomposition.append({**common,'classes':value['classes'],'partition_accounting':value['partition_accounting']})
    boundary.append({**common,'projection_boundary':value['projection_boundary']})
    rollout.append({**common,'horizons':{h:{k:v[k] for k in ('count','classes','false_motion','missed_motion','mechanism_states','partition_accounting')}
                                       for h,v in job['rollout'].items()}})
    divergence.append({**common,'horizons':{h:{k:v[k] for k in ('first_divergence','first_false_move','path_distributions',
      'final_signed_error','final_absolute_error','tail_composition')} for h,v in job['rollout'].items()}})
    context.append({**common,'one_step':value['context'],'rollout':{h:v['context'] for h,v in job['rollout'].items()}})
  common = {'input_manifest_sha256':e.INPUT_SHA,'output_manifest_sha256':manifest['receipt_sha256'],
    'reconstruction_repeatability_sha256':e.REPEAT_SHA,'executor_sources':e.sources(),
    'historical_verdict':'S2_RI_NO_ADMISSIBLE_CANDIDATE','model_selection':'MODEL_SELECTION_FAILED_CLOSED',
    'historical_family_verdict':'FROZEN_S2_RI_LINEAR_FAMILY_FAILED_RETROSPECTIVE_DIRECTIONAL_GATE',
    'model_refit_calls':0,'normalizer_refit_calls':0,'model_replay_calls':0,'selection_calls':0,
    'raw_log_openings':0,'qlog_openings':0,'holdout_openings':0,'holdout':'CLOSED','opening_count':0,
    'gate_reevaluation':False,'candidate_ranking':False,'pooled_refit_authorized':False,
    'hurdle_implementation_authorized':False,'hurdle_fitting_authorized':False,'vehicle_authority':False,
    'origin':'RECONSTRUCTED_EVIDENCE_AFTER_SEPARATE_AUTHORIZATION'}
  def seal(schema,**fields):
    return e.p.seal({'schema':schema,**common,**fields})
  trigger = {k:summary['mechanisms'][k] for k in ('pattern_jobs','total_jobs','one_step_outcome','hurdle_state',
             'hurdle_design_review_supported','hurdle_implementation_authorized','hurdle_fitting_authorized')}
  bundles = {
    'failure-attribution-policy':e.policy(),
    'one-step-attribution':seal('EMPIRICAL_S2_RI_ONE_STEP_ATTRIBUTION_V2',jobs=one),
    'movement-confusion':seal('EMPIRICAL_S2_RI_MOVEMENT_CONFUSION_V2',jobs=confusion),
    'error-decomposition':seal('EMPIRICAL_S2_RI_ERROR_DECOMPOSITION_V2',jobs=decomposition,
                             sign_convention='NEGATIVE_IMPROVEMENT_POSITIVE_REGRESSION',p95_additive=False),
    'projection-boundary':seal('EMPIRICAL_S2_RI_PROJECTION_BOUNDARY_V2',jobs=boundary),
    'rollout-attribution':seal('EMPIRICAL_S2_RI_ROLLOUT_ATTRIBUTION_V2',jobs=rollout),
    'rollout-divergence':seal('EMPIRICAL_S2_RI_ROLLOUT_DIVERGENCE_V2',jobs=divergence),
    'context-attribution':seal('EMPIRICAL_S2_RI_CONTEXT_ATTRIBUTION_V2',jobs=context,context_use='DESCRIPTIVE_ONLY'),
    'mechanism-summary':seal('EMPIRICAL_S2_RI_MECHANISM_SUMMARY_V2',**summary['mechanisms']),
    'hurdle-design-trigger':seal('EMPIRICAL_S2_RI_HURDLE_DESIGN_TRIGGER_V2',**trigger,meaning='DESIGN_REVIEW_ONLY'),
    'failure-attribution-repeatability':seal('EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_PUBLIC_REPEATABILITY_V2',
      repeatability_receipt_sha256=repeatability['receipt_sha256'],independent_runs=2,
      exact_arrays=True,exact_manifests=True,trapped_resume_exact=True,input_bytes_unchanged=True),
    'failure-attribution-readiness':seal('EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_READINESS_V2',status=e.SUCCESS,
      states=[e.SUCCESS,'READ_ONLY_ATTRIBUTION_COMPLETE','NO_NEW_MODEL_FIT','NO_MODEL_REPLAY','NO_MODEL_SELECTION',
              'NO_POLICY_CHANGE','S2_RI_NO_ADMISSIBLE_CANDIDATE_PRESERVED'],
      one_step_populations=32,rollout_populations=128,**trigger),
  }
  return {'empirical-s2-ri-'+name+'-v2.json':v for name,v in bundles.items()}


def publish(source,output):
  bundles = complete(source,output)
  for name,value in bundles.items():
    e.write(e.p.PUBLIC/name,value)
  return bundles


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source',required=True,type=Path)
  parser.add_argument('--output',required=True,type=Path)
  args = parser.parse_args()
  print('PUBLISHED',len(publish(args.source,args.output)))


if __name__=='__main__':
  main()
