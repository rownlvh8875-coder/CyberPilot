"""Publish V4 design review from sealed aggregate inputs only; never fit a policy."""

import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_review as r

RULE = [
  'NOT_EQUIVALENT_TO_CLOSED_FAMILY', 'CAUSAL_DEPLOYABLE', 'NO_DEVELOPMENT_LABEL_DEPENDENCY',
  'DIRECTLY_ADDRESSES_OBSERVED_V1_V2_V3_FAILURE', 'HAS_EMPIRICAL_SUPPORT_FOR_ALL_NEW_INPUTS',
  'BOUNDED_EXACT_FUTURE_FITTING_FEASIBLE', 'MINIMUM_NEW_STATE', 'MINIMUM_NEW_FREE_PARAMETERS',
  'MINIMUM_NEW_MODEL_COMPLEXITY', 'NO_NEW_SENSOR_SEMANTICS', 'NO_RATE_SIGNAL_DEPENDENCY', 'FAIL_CLOSED',
]
PREFIX = 'empirical-hurdle-stage1-v4-'


def build(lock, audit):
  inputs = r.verify_inputs(lock)
  repeated_audit = audit
  audit = r.validate_audit(repeated_audit, lock['receipt_sha256'])
  def get(name):
    return inputs[name + '.json']
  old = get('empirical-hurdle-selection-result-v1')
  v2 = get('empirical-hurdle-stage1-v2-selection-result')
  v3 = get('empirical-hurdle-stage1-v3-selection-result')
  for row in (old, v2, v3):
    r.require(row['selection']['admissible_count'] == 0 and row['selection']['selected_candidate'] is None)
  ready = get('empirical-hurdle-stage1-v3-retrospective-execution-readiness')
  summary = ready['summary']
  mechanism = get('empirical-hurdle-stage1-v2-mechanism-summary')['summary']
  r.require(all(mechanism[k] == 32 for k in ('extreme_move_suppression_jobs', 'rank_above_chance_jobs', 'rank_transfer_decreased_jobs')))
  r.require(summary['job_status_counts'] == {'EXECUTED_COMPLETE': 31, 'NO_FEASIBLE_THRESHOLD': 1})
  r.require(summary['v2_exact_hit_change_job_counts'] == {'worse': 31} and summary['v2_missed_move_improved_job_count'] == 31)
  r.require(all(summary['folds'][fold]['complete_gate_pass_count'] == 0 for fold in ('FOLD_A', 'FOLD_B')))
  states = [old['selection']['status'], v2['selection']['status'], v3['selection']['status'],
            'S2_RI_NO_ADMISSIBLE_CANDIDATE', 'MODEL_SELECTION_FAILED_CLOSED', 'STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS']
  preserved = ready['preserved_authority_states']
  common = {'baseline': r.BASELINE, 'scope': 'RESEARCH_DESIGN_REVIEW_ONLY', 'historical_states_preserved': states,
            'preserved_authority_states': preserved, 'holdout': 'CLOSED', 'opening_count': 0, 'holdout_discovery': 0,
            'vehicle_authority': 'NONE', 'v4_performance': 'NOT_RUN', 'actual_execution_authorized': False}
  result = {}
  def add(component, body, filename=None):
    result[filename or PREFIX + component + '.json'] = p.seal({'schema': 'STAGE1_V4_ARCHITECTURE_REVIEW_V1',
                                                            'component': component, **common, **body})
  facts = {'v1_admissible_count': 0, 'v2_admissible_count': 0, 'v3_admissible_count': 0,
           'v2_extreme_suppression_jobs': 32, 'v2_extreme_suppression_denominator': 32,
           'v3_comparable_jobs': 31, 'v3_no_feasible_jobs': 1, 'v3_exact_hit_worsened_jobs': 31,
           'v3_missed_move_improved_jobs': 31, 'v3_fold_pass_counts': {'FOLD_A': 0, 'FOLD_B': 0},
           'v3_gate_accounting_denominator': 32, 'historical_v3_summary': summary,
           'v2_mechanism_states': {k: mechanism[k] for k in ('rank_state', 'rank_transfer_state', 'decision_state',
                                                          'threshold_review', 'classifier_review', 'stage2_review')}}
  add('architecture-inputs', {'public_inputs': lock['public_inputs'], 'facts': facts,
                            'public_input_lock_sha256': lock['receipt_sha256'], 'receipt_and_file_hash_reconciliation': 'PASS'})
  add('fixed-threshold-family-review', {
    'family': 'SINGLE_GLOBAL_THRESHOLD_OVER_FIXED_STAGE1_SCORE',
    'definition': 'SAME_CANDIDATE_FOLD_FIXED_SCALAR_SCORE; MOVE_IFF_SCORE_STRICTLY_GREATER_THAN_ONE_TRAIN_THRESHOLD',
    'same_models_features_score': True,
    'policies': [{'version': name, 'threshold_policy': objective, 'selection_receipt_sha256': row['receipt_sha256']}
                 for name, objective, row in [('V1', 'TRAIN_BALANCED_ACCURACY', old),
                                             ('V2', 'TRAIN_TASK_EXACT_HIT_WITH_MOVE_AND_ALL_RMSE_PROTECTION', v2),
                                             ('V3', 'V2_PLUS_IMMUTABLE_V1_TRAIN_TP_FLOOR', v3)]],
    'status': 'GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED',
    'closure_scope': 'EMPIRICAL_PROJECT_POLICY_CLOSURE_CURRENT_DATA_FIXED_SCORE_HURDLE_COMPOSITION_FROZEN_FINAL_GATE',
    'mathematical_impossibility_claim': False,
    'not_proven': ['ALL_POSSIBLE_THRESHOLDS_FAIL', 'ALL_THRESHOLD_OBJECTIVES_FAIL', 'ALL_STAGE1_MODELS_FAIL'],
    'reason': 'THREE_DISTINCT_TRAIN_POLICY_SELECTIONS_NO_ADMISSIBLE; V2_SUPPRESSION_V3_COVERAGE_STATIC_TRADEOFF_OBSERVED',
    'research_priority': 'STOP_ADDITIONAL_GLOBAL_THRESHOLD_OBJECTIVE_TWEAKING_WITHOUT_NEW_STRUCTURAL_EVIDENCE',
    'v2_v3_comparison_denominator': 31,
  }, 'empirical-hurdle-stage1-fixed-threshold-family-review.json')
  add('equivalence-analysis', {
    'strict_increasing': 'f(p)>c IS_AN_UPPER_SET; FOR_c_IN_RANGE_USE_p>f_inverse(c); ENDPOINT_EMPTY_OR_ALL_HANDLED_SEPARATELY',
    'weak_increasing_finite_support': 'SORT_DISTINCT_SCORES; IDENTICAL_SCORES_CANNOT_SPLIT; REJECTED_PREFIX_ENDS_AT_MAX_REJECTED_SCORE',
    'weak_increasing_continuum_caveat': 'JUMP_WITH_ACCEPTED_BOUNDARY_CAN_GIVE_p>=a_NOT_p>a; NO_UNQUALIFIED_CONTINUUM_EQUIVALENCE',
    'flat_mapping': 'CAN_REMOVE_CUTS_NEVER_CREATE_NON_UPPER_SETS_ON_FIXED_FINITE_SUPPORT',
    'endpoint_caveat': 'ALL_MOVE_INCLUDING_p=0_NEEDS_NEGATIVE_CUT; HISTORICAL_0_TO_1_CANDIDATES_CANNOT_REPRESENT_THIS',
    'equality': 'STRICT_GREATER_THAN_WITH_TIES_AT_TRANSFORMED_CUTOFF_STATIC; NO_EPSILON_OR_PROBABILITY_ROUNDING',
    'global_examples': ['POSITIVE_SLOPE_PLATT', 'POSITIVE_TEMPERATURE', 'NONDECREASING_ISOTONIC', 'FROZEN_GLOBAL_ECDF_FIXED_PERCENTILE'],
    'global_verdict': 'NO_NEW_CONTEXTUAL_BOUNDARY; SAME_FINITE_SCORE_UPPER_CUTS_SUBJECT_TO_ENDPOINT_DOMAIN_CAVEAT',
    'decreasing_mapping': 'REVERSES_ORDER_NOT_EQUIVALENT_TO_UPPER_CUT_FAMILY',
    'state_monotone_calibration': 'WITHIN_STATE_INCREASING_TRANSFORM_PLUS_COMMON_CUTOFF_IS_TWO_STATE_THRESHOLDS_OPTION_A',
    'state_logistic': 'FIXED_ORIGINAL_LOGIT_WITH_POSITIVE_SLOPE_AND_BINARY_STATE_INTERCEPT_PLUS_CUTOFF_IS_OPTION_A',
    'state_witness': 'EQUAL_SCORE_DIFFERENT_CAUSAL_STATE_CAN_RECEIVE_DIFFERENT_DECISIONS_IF_TWO_CUTOFFS_DIFFER',
    'binary_state_representation': 'NONAFFINE_ZERO_VS_NONZERO_TRANSFORM_OF_EXISTING_SIGNED_INCREMENT_NOT_NEW_MEASURED_INFORMATION',
  })
  transitions = get('empirical-hurdle-stage1-v3-transition-statistics')['routes']
  ranking = get('empirical-hurdle-stage1-v3-onset-continuation-ranking')['jobs']
  routes = {}
  for route, row in transitions.items():
    counts = row['transitions']['counts']
    move = counts['SM'] + counts['MM']
    r.require(route in audit['routes'] and audit['routes'][route]['anchor_sha256'] == row['anchor_sha256'])
    routes[route] = {'onset_count': counts['SM'], 'continuation_count': counts['MM'], 'move_count': move,
                     'onset_fraction': counts['SM'] / move, 'continuation_fraction': counts['MM'] / move,
                     'transitions': row['transitions'], 'singleton_fragments': audit['routes'][route]}
  def ranges(vals):
    return {'min': min(vals), 'max': max(vals)}
  conditional = {}
  for fold in ('FOLD_A', 'FOLD_B'):
    jobs = [j for j in ranking if j['fold'] == fold]
    conditional[fold] = {pop: {context: ranges([j[pop]['scores'][context]['auc'] for j in jobs])
                               for context in ('previous_static', 'previous_move', 'onset', 'continuation')}
                          for pop in ('train', 'development')}
  add('onset-continuation-support', {'routes': routes, 'auc_ranges': conditional,
      'route_scope': 'HRI_D00_L01_ONE_STEP_POPULATION_ONE_PER_ROUTE_NOT_POOLED_CANDIDATES',
      'conditional_auc_interpretation': 'STATE_CONDITIONAL_previous_static_AND_previous_move; onset_AND_continuation_USE_ALL_STATIC_NEGATIVES',
      'audit_receipt_sha256': audit['receipt_sha256'], 'audit_independent_runs': 2,
      'audit_byte_exact_aggregate_repeatability': 'PASS', 'unique_numeric_arrays_per_run': 12, 'total_numeric_array_decodes': 24,
      'source_member_count': audit['source_member_count'], 'source_members_unchanged_sha256': audit['source_members_unchanged_sha256'],
      'source_immutability_scope': audit['immutability_scope'], 'source_writes': 0,
      'run_length_caveat': 'BOUNDARY_CENSORED_ELIGIBLE_FRAGMENTS; NOT_UNINTERRUPTED_RAW_ROUTE_RUN_DISTRIBUTION'})
  add('singleton-audit', {'audit': repeated_audit,
                        'initial_unpublished_diagnostic_decodes': 24,
                        'authoritative_two_run_decodes': 24,
                        'total_task_numeric_array_decodes': 48,
                        'no_numeric_v4_performance': True})
  scores = get('empirical-hurdle-stage1-v2-score-ranking')['jobs']
  refs = get('empirical-hurdle-stage1-v3-training-policy')['references']
  dev = get('empirical-hurdle-stage1-v3-development-results')['jobs']
  train = get('empirical-hurdle-stage1-v3-train-results')['jobs']
  transfer = []
  for score, reference, development, training in zip(scores, refs, dev, train, strict=True):
    identity = {k: score[k] for k in ('candidate_id', 'fold')}
    r.require(all(all(row[k] == v for k, v in identity.items()) for row in (reference, development, training)))
    refrecall = reference['reference_tp'] / reference['positive_count']
    rec = development.get('stage1_diagnostics', {}).get('recall')
    transfer.append({**identity, 'train': score['train'], 'development': score['development'],
      'auc_dev_minus_train': score['development']['auc'] - score['train']['auc'],
      'score_mean_shift': {k: score['development'][k] - score['train'][k] for k in ('static_score_mean', 'move_score_mean', 'mean_probability')},
      'train_reference_recall': refrecall, 'v3_train_recall': (training.get('train_metrics') or {}).get('stage1', {}).get('recall'),
      'v3_dev_recall': rec, 'v3_dev_minus_reference_recall': rec - refrecall if rec is not None else None,
      'status': development['status'], 'interpretation': 'FACTUAL_ROUTE_TRANSFER_REPORT_ONLY_NOT_CAUSAL_IDENTIFICATION'})
  folds = {fold: {key: ranges([j[key] for j in transfer if j['fold'] == fold and j[key] is not None])
                 for key in ('train_reference_recall', 'v3_train_recall', 'v3_dev_recall', 'v3_dev_minus_reference_recall', 'auc_dev_minus_train')}
           for fold in ('FOLD_A', 'FOLD_B')}
  add('route-transfer-analysis', {'jobs': transfer, 'folds': folds,
      'score_identity': 'V1_REUSED_FOR_V2_V3_SAME_CANDIDATE_FOLD_ANCHORS',
      'interpretation': 'MEAN_SHIFT_AND_AUC_DECLINE_COEXIST; NOT_PROOF_OF_CAUSAL_CALIBRATION_MECHANISM'})
  options = [
    {'id': 'A', 'family': 'CAUSAL_PREVIOUS_STATE_TWO_THRESHOLD_GATE', 'equivalent_to_global': False,
     'state_bits': 1, 'effective_decision_parameters': 2, 'new_model_fit': False,
     'function': 'z=1[prior_source_grid_delta!=0]; MOVE_IFF_score>theta_z',
     'support': 'PERSISTENCE_BOTH_ROUTES_AND_STATE_CONDITIONAL_SCORE_RANKING',
     'risks': ['ONSET_IS_MAJORITY_OF_TRUE_MOVE', 'WITHIN_STATE_RANK_STILL_WEAK', 'OBSERVED_TO_PROJECTED_STATE_DISTRIBUTION_SHIFT'],
     'blocking': ['EXACT_PRACTICALLY_BOUNDED_TWO_THRESHOLD_OPTIMIZER_NOT_ESTABLISHED', 'TWO_THRESHOLD_TOTAL_TIE_ORDER_UNRESOLVED',
                  'TRAIN_OBJECTIVE_AND_FEASIBILITY_MUST_BE_PREDECLARED_NOT_ASSUMED_INHERITED'], 'eligible': False, 'cost': [1, 2, 0]},
    {'id': 'B', 'family': 'CAUSAL_SCORE_RECALIBRATION_LAYER', 'equivalent_to_global': 'IF_GLOBAL_INCREASING',
     'state_bits': '1_IF_BINARY_CONTEXT', 'effective_decision_parameters': '2_IF_WITHIN_STATE_MONOTONE_OTHERWISE_UNSPECIFIED',
     'new_model_fit': 'IF_CALIBRATION_COEFFICIENTS_FITTED',
     'blocking': ['MONOTONE_BINARY_CONTEXT_FORM_REPARAMETERIZES_A', 'OTHER_TRANSFORM_OR_INTERACTION_UNSUPPORTED_UNSPECIFIED'],
     'eligible': False, 'cost': None},
    {'id': 'C', 'family': 'EXPLICIT_TEMPORAL_STAGE1_LOGISTIC_V4', 'equivalent_to_global': False,
     'state_bits': '1_BINARY_INPUT', 'effective_decision_parameters': 'UNFROZEN_DEPENDS_ON_WEIGHT_REUSE_AND_INTERACTIONS',
     'new_model_fit': True, 'blocking': ['FIXED_SCORE_STATE_INTERCEPT_FORM_EQUIVALENT_TO_A',
       'REFITTED_WEIGHTS_OR_INTERACTIONS_NEED_REPRESENTATION_AND_FITTING_CONTRACT_NOT_JUSTIFIED_AS_MINIMUM'],
     'eligible': False, 'cost': None},
    {'id': 'D', 'family': 'BOUNDED_NONLINEAR_STAGE1_V4', 'equivalent_to_global': False,
     'state_bits': 'UNSPECIFIED', 'effective_decision_parameters': 'UNSPECIFIED', 'new_model_fit': True,
     'blocking': ['NO_EVIDENCE_IDENTIFIES_MINIMUM_NONLINEAR_FAMILY_OR_TERMS', 'HYPERPARAMETER_OPTIMIZER_SUPPORT_UNFROZEN'],
     'eligible': False, 'cost': None},
    {'id': 'E', 'family': 'ONLINE_UNLABELED_ADAPTIVE_GATE', 'equivalent_to_global': False,
     'state_bits': 'BOUNDED_WINDOW_NOT_DEFINED', 'effective_decision_parameters': 'UNSPECIFIED', 'new_model_fit': False,
     'blocking': ['ARBITRARY_WINDOW_TARGET_RESET_UPDATE_REQUIRED', 'UNLABELED_SCORE_SHIFT_DOES_NOT_IDENTIFY_LABEL_CONDITIONAL_SHIFT'],
     'eligible': False, 'cost': None},
    {'id': 'F', 'family': 'STATEFUL_HYSTERESIS_GATE', 'equivalent_to_global': False,
     'state_bits': 1, 'effective_decision_parameters': 2, 'new_model_fit': False,
     'blocking': ['OBSERVED_PERSISTENCE_IS_NOT_PREDICTED_GATE_PERSISTENCE_EVIDENCE', 'ERROR_FEEDBACK_AND_ONSET_ENTRY_RISK',
                  'EXACT_STATE_DEPENDENT_FITTING_NOT_ESTABLISHED'], 'eligible': False, 'cost': [1, 2, 0]},
  ]
  add('architecture-options', {'options': options, 'dominance_scope': 'STRUCTURAL_REPRESENTATION_COMPLEXITY_NOT_EMPIRICAL_PERFORMANCE',
      'no_best_candidate_or_actual_v4_performance_ranking': True})
  add('architecture-selection-rule', {'lexicographic_rule': RULE,
      'eligibility': 'ALL_FIRST_SIX_AND_LAST_THREE_REQUIREMENTS_PROVEN_BEFORE_COMPLEXITY_MINIMIZATION',
      'unknown_is_pass': False, 'tie': 'INCONCLUSIVE_NO_ARBITRARY_ID_TIEBREAK',
      'architecture_selection_is_not_model_candidate_selection': True})
  outcome = r.design_outcome(options)
  r.require(outcome['status'] == r.INCONCLUSIVE)
  add('architecture-decision', {'status': outcome['status'], 'selected_architecture': outcome['selected'], 'reason': outcome['reason'],
      'design_contract_frozen': False, 'leading_structural_question': 'OPTION_A_EXACT_FITTING_FEASIBILITY_NOT_AN_ARCHITECTURE_SELECTION',
      'new_state_count_committed': 0, 'new_fitted_parameter_count_committed': 0, 'new_free_parameter_count_committed': 0,
      'no_fallback_to_larger_model': True})
  add('future-fitting-requirements', {
      'status': 'REQUIRES_SEPARATE_DESIGN_FEASIBILITY_INCREMENT_NOT_A_FITTING_POLICY',
      'next_step': 'SYNTHETIC_ONLY_EXACT_TWO_CONTEXT_FITTING_FEASIBILITY_AND_CAUSAL_STATE_CONTRACT_REVIEW',
      'option_a': {'must_resolve': ['EXACT_OBJECTIVE_FEASIBILITY_AND_TOTAL_TWO_PARAMETER_TIE_ORDER',
                   'FINITE_CONTEXT_SPECIFIC_TRAIN_SCORE_SUPPORTS_AND_ENDPOINT_SEMANTICS',
                   'ORIGINAL_ROW_ORDER_FLOAT64_REDUCTION_EQUIVALENCE', 'POOLED_LINEAR_P95_EXACTNESS',
                   'CERTIFIED_SAFE_PRUNING_AND_PRACTICAL_WORST_CASE_TIME_MEMORY',
                   'INITIAL_OBSERVED_STATE_THEN_RECURSIVE_PROJECTED_DELTA_STATE_NO_FUTURE_MEASURED_FEEDBACK',
                   'MISSING_NONFINITE_BOUNDARY_SUPPORT_FAILURE_NO_STATIC_PADDING'],
                   'cartesian': 'O(T_STATIC*T_MOVE)_NOT_ACCEPTED_AS_DEFERRED_OPTIMIZATION',
                   'non_solution': 'SEPARATE_CONTEXT_P95_OR_SSE_SUMS_NOT_CANONICAL_POOLED_NUMPY_METRICS',
                   'research_candidate_algorithm': ('CERTIFIED_RECTANGLE_BRANCH_AND_BOUND_WITH_EXACT_INTEGER_BOUNDS_' +
                                                    'CONSERVATIVE_ORDERED_FLOAT_BOUNDS_CANONICAL_LEAVES'),
                   'algorithm_status': 'EXACT_ON_CERTIFIED_COMPLETION_ONLY_WORST_CASE_CARTESIAN_NOT_YET_ELIGIBLE',
                   'resource_exhaustion': 'INCONCLUSIVE_RESOURCE_BOUND_NEVER_BEST_SO_FAR_NEVER_NO_FEASIBLE',
                   'no_feasible': 'ONLY_AFTER_ENTIRE_FINITE_DOMAIN_CERTIFIED_INFEASIBLE'},
      'all_families': ['TRAIN_ONLY_NO_DEV_LABELS_OR_RESULT_TUNING', 'SAME_TWO_ROUTE_FOLDS',
                      'NO_STAGE2_OR_NORMALIZER_REFIT', 'FROZEN_32_CLAUSE_FINAL_GATE_BOTH_FOLDS', 'FROZEN_MODEL_SELECTION_RULE',
                      'INITIALIZATION_OPTIMIZER_CONVERGENCE_REGULARIZATION_IF_NEW_FIT',
                      'SUPPORT_DTYPE_FLOAT64_IDENTITY_TWO_RUN_REPEATABILITY_RESUME_PRIVACY_AUTHORIZATION'],
      'source_grid_semantics': 'PREVIOUS_OBSERVED_DELTA_IS_TICK_INCREMENT_NOT_PHYSICAL_EPS_MOVEMENT',
      'command_semantics': 'POST_CARCONTROLLER_NORMALIZED_COMMAND_NOT_PHYSICAL_APPLIED_TORQUE',
      'rate': ['SOURCE_NATIVE_RATE_CODE_ONLY', 'RATE_SOURCE_CONTRACT_PARTIAL', 'NO_NEW_RATE_DEPENDENCY'],
      'registry': 'NOT_NEEDED_FOR_THIS_REVIEW; NEW_FITTED_B_C_D_REQUIRES_SEPARATE_MODEL_ARTIFACT_LIFECYCLE_REGISTRY_REVIEW',
      'hf_user_guidance': 'EXPLAIN_USAGE_TO_BEGINNER_IF_A_NEW_MODEL_ARTIFACT_STAGE_IS_AUTHORIZED; NO_SETUP_NOW',
      'actual_execution_authorization': 'SEPARATE_REQUIRED_E_EXTERNAL_SSD_ONLY',
  })
  add('design-readiness', {'status': r.INCONCLUSIVE,
      'states': ['STAGE1_V4_ARCHITECTURE_REDESIGN_REVIEW_COMPLETE', 'GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVE_REVIEW_COMPLETE', r.INCONCLUSIVE],
      'stage1_model_change': 'NONE_IMPLEMENTED', 'stage2_model_change': 'NONE_IMPLEMENTED',
      'v4': dict.fromkeys(('performance', 'fitting', 'cv', 'development', 'rollout', 'selection'), 'NOT_RUN'),
      'v4_parameter_selection': 'NOT_RUN', 'fitting_policy_implemented': False, 'design_contract_frozen': False,
      'execution_calls': dict.fromkeys(('model_fit', 'normalizer_fit', 'prediction', 'threshold_search', 'development', 'rollout',
                                       'model_selection', 'raw_log', 'qlog', 'holdout', 'source_write'), 0),
      'private_access_scope': 'ONLY_12_UNIQUE_V1_STORED_TRUTH_CONTINUITY_REFERENCE_ARRAYS_PER_AUDIT_RUN_NO_MODEL_OR_SCORE_OPEN',
      'storage': 'E_EXTERNAL_SSD', 'no_auto_advance': True})
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--locked-inputs', required=True, type=Path)
  parser.add_argument('--singleton-audit', required=True, type=Path)
  args = parser.parse_args()
  # These are sealed JSON aggregate receipts, never source roots or NPY payloads.
  bundle = build(p.verify(json.loads(args.locked_inputs.read_bytes())), p.verify(json.loads(args.singleton_audit.read_bytes())))
  for name, body in bundle.items():
    p.persist(p.PUBLIC / name, body)
  print(json.dumps({'artifact_count': len(bundle), 'status': r.INCONCLUSIVE}))


if __name__ == '__main__':
  main()
