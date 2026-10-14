"""Public-only policy decision record. Never fit thresholds or execute models."""

import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_policy_review as r

BASELINE = 'cfea011d68f28a5c907a3cef17a76e1fa29bf58a'
PREFIX = 'empirical-hurdle-stage1-v4-'
# Exact public file and sealed-receipt hashes are filled from the startup-verified baseline.
PINS = {'empirical-hurdle-stage1-fixed-threshold-family-review': ('e3d7bb8f2d4713fa9a97ee17cbdb246dde2dfc03ef1a99b907174504cec8843a',
                                                           'c5c229cdf974a573fa03702874404f6f1d38603ddfe99a98fb359df273b9da5d'),
 'empirical-hurdle-stage1-v4-architecture-decision': ('e4b327accf0a4551038dc3af6fcd8a1b32207fc6914b50cd36e9ad2946485a93',
                                                      'e868bf09f5e823388b7464babdb2093dc7d822b4c30b3019bbd5ae8ab8542e35'),
 'empirical-hurdle-stage1-v4-architecture-options': ('daaa64c1273cde06021d6fa01e80961bcee160670062141a83f0b09f66138c89',
                                                     'b1014606100ba57f429c562e4fd9718ad9f9074f596c3f83625d74102ab2fb77'),
 'empirical-hurdle-stage1-v4-route-transfer-analysis': ('83629b829e911e55c184e3e63be91a65c99c1031521b83618dcf442bff6c3ba0',
                                                        '7791b7bd6c589a74516638df10691c2e4a7b54bd7cc52e8500519852fbaa0ae3'),
 'empirical-hurdle-stage1-v4-onset-continuation-support': ('d962e9a07ec9d79638a563cccccbda749312a2fe548239f139bb5b3b64f028c1',
                                                           '771e90d4f2e1336da3b853e8a01c7f1313f76bf8b32d53840eafd4141ab5c938'),
 'empirical-hurdle-stage1-v4-singleton-audit': ('c84b32de24fbbb4f74c66ce3f431d90bd5871471dc1652db7c49e134af741a27',
                                                'f491ce0ba4d593951eea631345bb4cd8d9da8035d644ff64d69472aad4a3bd97'),
 'empirical-hurdle-stage1-v4-two-context-feasibility-policy': ('57aabcb686cd239aff587d23c827355deb4d4368eb9b913e94e66743f4dba2f1',
                                                               '4efbf141a3574c7afc85e465d6a9bfabdd04ba442a27be500410e862352a74e7'),
 'empirical-hurdle-stage1-v4-causal-state-contract': ('bdcd62d3e2736a96e4118d1da070b5f0c77aa2a23d57a776888594a6a4db686c',
                                                      'd3df9b9c32043aa01df9f95c6adb126ceab76439bc72aac79c4c06fe86096e39'),
 'empirical-hurdle-stage1-v4-rollout-state-contract': ('efd06a9d9109ce326e96ecc29af480007f85cbbccf398f1c0750164ba266bada',
                                                       '1b503078ac9e5adda34f54650099309c7db718c5181ccdca5dc462d11899542f'),
 'empirical-hurdle-stage1-v4-two-context-exact-algorithm': ('ae1d95cb6a8fda8dafb1a2ab916a7c266316e815f161b6a8efe81ad9f4f227a1',
                                                            '6408ec14fd41ec02bb15d78a64ba0f6582c6f698351998dad39c7c556083f1ee'),
 'empirical-hurdle-stage1-v4-two-context-complexity-analysis': ('58a6fea693d97e7f94ff76adfebf38e82ce6cc50b7bd2edfbcdf562c1dfb630f',
                                                                '3283c00f1f2e9a3e101c250b5248525847a367bcc06d9570aa795ff0c9e0a015'),
 'empirical-hurdle-stage1-v4-two-context-separable-policy-review': ('2407e4192eee0e506b4fcc1039ef59e2875bb3c8680b7e2f3f961eae17f3d9e6',
                                                                    '06ce2bc737b5b07d720151baa01ce83e502dfa95890b1048eed39b0a7d64ea58'),
 'empirical-hurdle-stage1-v4-option-a-eligibility': ('79f511ab0fa72f111ba4beea99fbea37436c9e140f6657d9a312ffe869e095b6',
                                                     'd55c25fe04c9612d668a5ef88e21ecd3a202ed2068ae5b3f6d0959aa9b168171'),
 'empirical-hurdle-stage1-v4-two-context-validation': ('f2c7bc976749777e6a1e4c5e1b21fce45eaaba36a44f3474ecabfe6661720465',
                                                       'c969071df63cca8364228624f9c8e72baf995d55eaf5245ee45964fb819481bb'),
 'empirical-hurdle-stage1-v4-validation': ('2581ce34a3894bbbe71888cbf62ab1f253ea1eaca9c9a9d44c180d53c6d34ef2',
                                           '90083d3dce9e68e8bbece4f27a0f094bd4f8d0a09cf53981f2bfd37ca2a725c1'),
 'empirical-hurdle-stage1-v3-onset-continuation-ranking': ('74f56209a692d18798b7633eee7147c93722c6c863b4d0877bffde81731d69ba',
                                                           'b692752e967549f6bc6747de36fee64f01a79dded2c530176a450e092eb63877')}

SEPARABLE = {
  'DIRECT_FAILURE_RELEVANCE': None,
  'OBJECTIVE_JUSTIFIED_INDEPENDENTLY_OF_SPEED': True,
  'COMPENSATION_SACRIFICE_EXPLICIT_AND_ACCEPTABLE': None,
  'NO_ARBITRARY_CONTEXT_TARGET': True,
  'FINAL_GLOBAL_GATE_UNCHANGED': True,
  'ROUTE_LIMITATION_DOCUMENTED': True,
}


def locked_inputs():
  out = {}
  for name, (file_sha, receipt_sha) in PINS.items():
    raw = (p.PUBLIC / (name + '.json')).read_bytes()
    if p.sha(raw) != file_sha:
      raise ValueError('V4_POLICY_DECISION_INPUT_CONFLICT')
    row = p.verify(json.loads(raw))
    if row['receipt_sha256'] != receipt_sha:
      raise ValueError('V4_POLICY_DECISION_INPUT_CONFLICT')
    out[name] = row
  return out


def build():
  inputs = locked_inputs()
  def get(name):
    return inputs[PREFIX + name]
  prior = get('architecture-decision')
  r.need(prior['status'] == 'V4_ARCHITECTURE_REDESIGN_INCONCLUSIVE' and not prior['design_contract_frozen'])
  r.need(inputs['empirical-hurdle-stage1-fixed-threshold-family-review']['status'] ==
         'GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED')
  r.need(get('causal-state-contract')['status'] == 'V4_TWO_CONTEXT_CAUSAL_STATE_CONTRACT_ESTABLISHED')
  r.need(get('option-a-eligibility')['eligibility'] == 'OPTION_A_ALGORITHMIC_ELIGIBILITY_NOT_ESTABLISHED')
  r.need(get('option-a-eligibility')['fitting_result'] == 'V4_TWO_CONTEXT_EXACT_FITTING_EXACT_BUT_CARTESIAN_WORST_CASE')
  temporal, transfer = get('onset-continuation-support'), get('route-transfer-analysis')
  scores = inputs['empirical-hurdle-stage1-v3-onset-continuation-ranking']['jobs']
  jobs = transfer['jobs']
  identities = {(j['candidate_id'], j['fold']) for j in jobs}
  r.need(len(identities) == len(jobs) == len(scores) == 32)
  r.need(identities == {(j['candidate_id'], j['fold']) for j in scores})
  onset_majority = all(row['onset_count'] > row['continuation_count'] for row in temporal['routes'].values())
  above_chance = all(j['development']['scores']['previous_static']['auc_num2'] * 2 >
                     j['development']['scores']['previous_static']['auc_den2'] for j in scores)
  # The sixth condition is the supplied qualitative characterization plus exact
  # above-chance evidence, NOT an invented numeric 'good AUC' acceptance cutoff.
  representation = {
    'GLOBAL_THRESHOLD_TRACK_CLOSED': True, 'JOINT_PRACTICAL_BOUND_UNRESOLVED': True,
    'SEPARABILITY_HAS_NO_DIRECT_SHIFT_INVARIANCE': True, 'WITHIN_STATE_SCORE_ORDER_FIXED': True,
    'ONSET_MAJORITY_BOTH_ROUTES': onset_majority,
    'PUBLIC_PREVIOUS_STATIC_RANK_ABOVE_CHANCE_WITH_SUPPLIED_WEAK_CHARACTERIZATION': above_chance,
  }
  decision = r.decide(separable=tuple(SEPARABLE.values()), representation=tuple(representation.values()), closure_justified=None)
  r.need(decision['outcome'] == 'C')
  common = {'schema': 'HURDLE_STAGE1_V4_FITTING_POLICY_DECISION_REVIEW_V1', 'baseline': BASELINE,
    'scope': 'PUBLIC_STATIC_SYNTHETIC_POLICY_REVIEW_ONLY', 'actual_execution_authorized': False,
    'private_numeric_array_opens': 0, 'raw_log_openings': 0, 'qlog_openings': 0, 'holdout_openings': 0,
    'source_writes': 0, 'model_fit_calls': 0, 'normalizer_fit_calls': 0, 'prediction_replay_calls': 0,
    'threshold_fitting_calls': 0, 'actual_pair_search_calls': 0, 'rollout_calls': 0, 'model_selection_calls': 0,
    'holdout': 'CLOSED', 'opening_count': 0, 'holdout_discovery': 0, 'pooled_refit': 'NOT_AUTHORIZED',
    'vehicle_authority': 'NONE', 'historical_states_preserved': prior['historical_states_preserved'],
    'preserved_authority_states': prior['preserved_authority_states'],
    'prior_review_states_preserved': ['GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED',
      'V4_ARCHITECTURE_REDESIGN_INCONCLUSIVE', 'V4_TWO_CONTEXT_CAUSAL_STATE_CONTRACT_ESTABLISHED',
      'V4_TWO_CONTEXT_EXACT_FITTING_EXACT_BUT_CARTESIAN_WORST_CASE', 'OPTION_A_ALGORITHMIC_ELIGIBILITY_NOT_ESTABLISHED',
      'SEPARABLE_TWO_CONTEXT_FITTING_ALGORITHMICALLY_FEASIBLE_POLICY_UNFROZEN'],
    'v4': dict.fromkeys(('fitting', 'development', 'rollout', 'performance', 'selection'), 'NOT_RUN'),
    'architecture_frozen': False, 'fitting_policy_frozen': False,
    'hugging_face': {'setup': 'NOT_RUN', 'login': 'NOT_RUN', 'repo': 'NOT_CREATED', 'upload': 0, 'download': 0}}
  result = {}
  def add(component, body):
    result[PREFIX + component + '.json'] = p.seal({**common, 'component': component, **body})
  add('policy-decision-inputs', {'public_input_lock': {name + '.json': {'file_sha256': pair[0], 'receipt_sha256': pair[1]}
                                                     for name, pair in PINS.items()},
    'input_reconciliation': 'PASS', 'input_count': len(PINS), 'new_private_audit': False,
    'historical_public_audit_is_not_current_private_access': True})
  add('joint-vs-separable-policy', {
    'joint': {'parameters': 'ONE_PAIR(theta0,theta1)', 'fit_population': 'FULL_ORIGINAL_ORDER_TRAIN',
      'metrics': ['GLOBAL_RMSE_MAE_P95_EXACT_WITHIN_ONE', 'GLOBAL_TRUE_MOVE_METRICS', 'GLOBAL_COUNTS'], 'compensation': 'ALLOWED'},
    'separable': {'parameters': 'SAME_TWO_RUNTIME_CUTOFFS', 'fit_population': 'EACH_CONTEXT_ONLY',
      'compensation_during_fitting': 'DISALLOWED_FOR_CONTEXT_LOCAL_CONSTRAINTS', 'runtime_models_separate': False},
    'not_universally_inequivalent': 'UNCONSTRAINED_ADDITIVE_OBJECTIVES_CAN_SEPARATE_EXACTLY',
    'pooled_ba_identity': r.witnesses()['pooled_ba_separation'],
    'joint_retention_verdict': 'GLOBAL_FINAL_EVALUATION_ESSENTIAL_JOINT_TRAIN_OBJECTIVE_NOT_LOGICALLY_MANDATORY',
    'joint_practical_status': 'NOT_ESTABLISHED_NOT_IMPOSSIBLE',
    'surrogate_principles': ['TRAIN_ONLY', 'CAUSAL', 'DETERMINISTIC', 'NO_DEV_TUNING', 'NO_ARBITRARY_TARGET',
                           'INDEPENDENT_LOSS_ALIGNMENT_PRINCIPLE', 'UNCHANGED_FINAL_GATE'],
    'surrogate_adoption': 'UNFROZEN_ACCEPTABILITY_AND_TASK_ALIGNMENT_UNRESOLVED'})
  math = r.witnesses()
  add('cross-context-compensation', {'data_origin': r.SCOPE,
    'examples': {name: math[name] for name in ('rmse_compensation', 'pooled_p95', 'support_weighting', 'float_reduction')},
    'no_actual_policy_preference_or_real_winner': True,
    'loss_acceptability': 'UNKNOWN_NOT_NOT_ACCEPTABLE',
    'weighting_caveat': 'INDEPENDENT_MAXIMIZATION_OF_UNCONSTRAINED_ADDITIVE_COUNTS_IS_EQUIVALENT_NOT_A_COUNTEREXAMPLE'})
  def ranges(values):
    return {'min': min(values), 'max': max(values)}
  shift = {}
  for fold in ('FOLD_A', 'FOLD_B'):
    rows = [j for j in jobs if j['fold'] == fold]
    conditional = [j for j in scores if j['fold'] == fold]
    r.need(len(rows) == len(conditional) == 16)
    shift[fold] = {'historical_recall_and_auc': transfer['folds'][fold],
      'overall_mean_score_shift': ranges([j['score_mean_shift']['mean_probability'] for j in rows]),
      'conditional_mean_score_shifts': {z: ranges([j['development']['scores'][z]['mean_probability'] -
                                                   j['train']['scores'][z]['mean_probability'] for j in conditional])
                                        for z in ('previous_static', 'previous_move')}}
  add('route-shift-structural-analysis', {'folds': shift,
    'temporal_relevance': 'TEMPORAL_CONTEXT_PARTIALLY_RELEVANT_BUT_NOT_ROUTE_TRANSFER_EXPLANATION',
    'structural_robustness': 'NO_STRUCTURAL_CORRECTION', 'proof_scope': 'NO_INVARIANCE_TO_GENERAL_MONOTONIC_SCORE_SHIFT_NOT_NO_POSSIBLE_TRANSFER_GAIN',
    'reason': 'FIXED_TRAIN_ABSOLUTE_CONTEXT_CUTOFFS_NO_ONLINE_CALIBRATION_OR_TRANSPORT_RULE',
    'mean_shift_and_rank_degradation': 'COEXIST_NOT_CALIBRATION_ONLY_CAUSAL_PROOF',
    'stable_truth_transition_rates_do_not_imply_stable_conditional_score_distributions': True,
    'synthetic_shift_witness': math['fixed_shift']})
  add('state-ranking-limit', {'status': 'TWO_CONTEXT_FIXED_SCORE_CANNOT_IMPROVE_WITHIN_STATE_RANKING',
    'proof': 'FOR_FIXED_z_p_i<=p_j_AND_p_i>theta_z_IMPLIES_p_j>theta_z; SCORES_UNCHANGED',
    'hard_gate': 'MAY_COARSEN_TO_TIES_NOT_REVERSE_WITHIN_STATE_ORDER_NOT_A_BINARY_GATE_AUC_INVARIANCE_CLAIM',
    'across_context': 'DIFFERENT_CUTOFFS_CAN_CHANGE_DECISION_ORDER_BETWEEN_STATES',
    'impossibility_or_inadequacy_proof': False, 'conditional_dev_auc_ranges': temporal['auc_ranges']})
  add('onset-bottleneck-analysis', {'routes': {key: {name: row[name] for name in (
      'onset_count', 'continuation_count', 'move_count', 'onset_fraction', 'continuation_fraction', 'singleton_fragments', 'transitions')}
      for key, row in temporal['routes'].items()},
    'context_supports_from_public_transitions': {key: {
      'previous_static_count': row['transitions']['previous_static']['denominator'],
      'previous_move_count': row['transitions']['previous_move']['denominator'],
      'previous_static_fraction': row['transitions']['previous_static']['denominator'] / row['transitions']['count'],
      'previous_move_fraction': row['transitions']['previous_move']['denominator'] / row['transitions']['count']}
      for key, row in temporal['routes'].items()},
    'onset_majority_both_routes': onset_majority, 'previous_static_dev_above_chance_all_jobs': above_chance,
    'rank_description': 'WEAK_ABOVE_CHANCE_AS_SUPPLIED_CONTEXT_NO_NUMERIC_QUALITY_CUTOFF',
    'verdict': 'ONSET_MAJORITY_STRUCTURAL_LIMIT_ON_CONTINUATION_ONLY_CHANGES_NOT_PROVEN_DOMINANT_ERROR_CAUSE',
    'context_specific_failure_loss_attribution': 'NOT_ESTABLISHED_BY_LOCKED_INPUTS',
    'perfect_continuation_is_not_automatic_onset_solution': True, 'synthetic_partition': math['onset_heavy']})
  add('separable-objective-review', {'families': objective_review(), 'any_objective_adopted': False,
    'scientific_justification': 'PRINCIPLED_CLASSIFICATION_SURROGATE_EXISTS_TASK_ALIGNMENT_AND_COMPENSATION_ACCEPTABILITY_UNRESOLVED',
    'criteria': SEPARABLE,
    'stage1_vs_integrated': 'BOTH_LEGITIMATE_SCIENTIFIC_TARGETS_NEED_PREDECLARED_ALIGNMENT_RULE; V1_V2_V3_FAILURE_NOT_REFUTATION_OF_EITHER',
    'global_final_gate': 'UNCHANGED_POOLED_32_CLAUSES_BOTH_FOLDS',
    'no_hidden_defaults': ['NO_0_5_THRESHOLD', 'NO_LOCAL_TP_FLOOR', 'NO_CONTEXT_PREVALENCE_TARGET', 'NO_CONTEXT_WEIGHT_CHOSEN']})
  add('policy-decision-rule', {'lexicographic_priorities': list(r.RULE), 'separable_required_criteria': list(SEPARABLE),
    'tristate_semantics': 'TRUE_ESTABLISHED_FALSE_REFUTED_NULL_UNKNOWN; UNKNOWN_NEVER_BECOMES_FALSE',
    'b_requires': 'POSITIVE_PROJECT_PRIORITY_CLOSURE_JUSTIFICATION_PLUS_REPRESENTATION_REVIEW_SIGNAL',
    'b_not_implied_by': ['A_CRITERIA_UNRESOLVED', 'JOINT_PRACTICAL_BOUND_UNKNOWN', 'WEAK_AUC', 'COMPUTATIONAL_CONVENIENCE'],
    'conflicting_or_unresolved_first_priority': 'OUTCOME_C_LATER_SPEED_OR_COMPLEXITY_CANNOT_OVERRIDE',
    'no_empirical_performance_required_for_a': 'REVIEW_SUPPORT_NEEDS_A_JUSTIFIED_LOSS_PRINCIPLE_NOT_PROVEN_GAIN'})
  add('policy-decision', {**decision,
    'reason': 'A_DIRECT_FAILURE_LINK_AND_ACCEPTABLE_COMPENSATION_SACRIFICE_UNKNOWN; B_AFFIRMATIVE_PRIORITY_CLOSURE_NOT_ESTABLISHED',
    'two_context_family_refuted': False,
    'next_step': 'RESOLVE_LOSS_ALIGNMENT_AND_COMPENSATION_ACCEPTABILITY_WITH_EXPLICIT_PRINCIPLE_AND_CONTEXT_FAILURE_EVIDENCE_REQUIREMENTS',
    'no_auto_advance': True})
  add('next-architecture-trigger', {'conditions': representation, 'signal': 'NEW_STAGE1_REPRESENTATION_REVIEW_SUPPORTED',
    'signal_satisfied': decision['representation_review_signal'], 'signal_is_not_track_closure': True,
    'next_representation_review_automatically_started': False, 'architecture_family_ranked_or_selected': False,
    'minimum_model_principle': 'SMALLEST_CHANGE_CAPABLE_OF_CHANGING_WITHIN_STATE_RANKING_NOT_MOST_POWERFUL_MODEL',
    'possible_future_families_unranked': ['PREDECLARED_INTERACTION_LOGISTIC', 'BOUNDED_POLYNOMIAL_LOGISTIC',
                                       'SMALL_DETERMINISTIC_MLP', 'OTHER_BOUNDED_NONLINEAR_CLASSIFIER'],
    'registry_trigger': 'IF_LATER_MODEL_ARTIFACT_STAGE_AUTHORIZED_HUGGING_FACE_MODEL_REGISTRY_REVIEW_REQUIRED',
    'outcome_b_registry_trigger_now': False, 'future_hf_beginner_instructions_required': True})
  add('policy-review-validation', {'status': 'V4_TWO_CONTEXT_FITTING_POLICY_DECISION_REVIEW_COMPLETE',
    'checks': {'new_focused': {'passed': 28}, 'prior_v3_v4_two_context_focused': {'passed': 205},
      'combined_empirical': {'passed': 2001}, 'full_autotune_controls': {'passed': 4860}, 'lateral_replay': {'passed': 16},
      'ruff': 'PASS', 'compileall': 'PASS', 'json_files': {'passed': 690}, 'publication_privacy_authority': 'PASS',
      'git_diff_check': 'PASS', 'scons': 'PASS', 'research_policy_review': 'APPROVED', 'authority_logic_review': 'APPROVED'},
    'validation_environment': {'python': '3.12.13', 'numpy': '2.5.3', 'blas_threads': 1, 'temp': 'E_BACKED_WSL',
      'legacy_d_fixture_isolation': 'PRIVATE_MOUNT_NAMESPACE_TMPFS_NO_GLOBAL_ALIAS_OR_GUARD_CHANGE'},
    'review_corrections': ['SEPARATE_OPTIMIZATION_VS_LOCAL_POLICY_CHANGE', 'CLASSIFICATION_LOSS_VS_TASK_ALIGNMENT',
      'ELIGIBLE_OBSERVED_FRAGMENT_SCOPE', 'EMPIRICAL_AUC_NOT_SIGNIFICANCE_CLAIM'],
    'math_witnesses': 'PASS_NO_REAL_PERFORMANCE_PREDICTION',
    'input_lock': 'PASS', 'actual_v4_performance': 'NOT_RUN'})
  return result


def objective_review():
  return [
    {'family': 'CONTEXT_BALANCED_ACCURACY', 'non_arbitrary_basis': 'EQUAL_CLASS_RECALL_CRITERION_HISTORICAL_V1_CLASSIFICATION_TARGET',
     'protects': 'RECALL_AND_SPECIFICITY_PER_CONTEXT', 'global_gate_alignment': 'SURROGATE_NOT_EQUIVALENT_TO_PROJECTED_TASK',
     'new_numeric_target': False, 'normative_choice_remaining': 'CLASS_NORMALIZATION_GLOBAL_OR_LOCAL_AND_LOSS_ALIGNMENT',
     'imbalance': 'BALANCES_CLASSES_MAY_INCREASE_STATIC_FALSE_MOVEMENT', 'route_transfer': 'FIXED_CUTS_NOT_SHIFT_INVARIANT',
     'exactness': 'ADDITIVE_INTEGER_SWEEP_POSSIBLE_WITH_FROZEN_POSITIVE_DENOMINATORS'},
    {'family': 'CONTEXT_TASK_AWARE_EXACT_HIT', 'non_arbitrary_basis': 'COUNT_PROJECTED_TASK_HITS_HISTORICAL_V2_TARGET',
     'protects': 'PROJECTED_TICK_EXACTNESS', 'global_gate_alignment': 'ONE_FINAL_METRIC_ONLY_NO_RMSE_P95_ROLLOUT_GUARANTEE',
     'new_numeric_target': False, 'normative_choice_remaining': 'LOCAL_VS_GLOBAL_COUNTS_AND_CONSTRAINTS_NOT_SILENT_INHERITANCE',
     'imbalance': 'STATIC_DOMINANCE_CAN_REMAIN_ESPECIALLY_PREVIOUS_STATIC_CONTEXT', 'route_transfer': 'NO_STRUCTURAL_CORRECTION',
     'exactness': 'UNCONSTRAINED_ADDITIVE_COUNT_SWEEP_POSSIBLE'},
    {'family': 'CONTEXT_MOVE_PROTECTION_PLUS_EXACT_HIT', 'non_arbitrary_basis': 'HOLD_LAST_REFERENCED_TASK_CONSTRAINTS_HISTORICAL_V2_GLOBAL',
     'protects': 'CONTEXT_TRUE_MOVE_ERRORS_AND_PROJECTED_HITS', 'global_gate_alignment': 'PARTIAL_DIFFERENT_POOLED_FEASIBILITY',
     'new_numeric_target': False, 'normative_choice_remaining': 'LOCAL_CONSTRAINTS_ARE_NEW_POLICY_MAY_REJECT_JOINTLY_BENEFICIAL_PAIRS',
     'imbalance': 'SUPPORT_AND_UNDEFINED_MOVE_METRICS_NEED_FROZEN_RULES', 'route_transfer': 'NO_STRUCTURAL_CORRECTION',
     'exactness': 'CANONICAL_FLOAT_AND_P95_IMPLEMENTATION_PROOF_REQUIRED_NOT_INHERITED_FROM_INTEGER_BENCHMARK'},
    {'family': 'CONTEXT_CLASSIFICATION_PROPER_LOSS_DERIVED_THRESHOLD', 'non_arbitrary_basis': 'PROPER_LOSS_EVALUATES_PROBABILITIES',
     'protects': 'FIXED_SCORE_QUALITY_DIAGNOSTIC_ONLY', 'global_gate_alignment': 'NO_THRESHOLD_PARAMETER_IN_FIXED_SCORE_LOSS',
     'new_numeric_target': False, 'verdict': 'NOT_IDENTIFIABLE_AS_FIXED_SCORE_THRESHOLD_OBJECTIVE_WITHOUT_NEW_DECISION_UTILITY',
     'hard_decision_brier': 'ZERO_ONE_ERROR_DIFFERENT_DECISION_LOSS', 'hard_decision_log_loss': 'MISCLASSIFICATION_CAN_GIVE_INFINITY',
     'route_transfer': 'NO_NEW_CALIBRATION_FIT_ALLOWED'},
    {'family': 'REFERENCE_CONSTRAINED_CONTEXT_POLICY', 'non_arbitrary_basis': 'WOULD_REQUIRE_PREDECLARED_IMMUTABLE_CONTEXT_REFERENCE',
     'protects': 'REFERENCE_MOVE_COVERAGE_IF_JUSTIFIED', 'global_gate_alignment': 'V3_GLOBAL_FLOOR_DID_NOT_PROTECT_EXACT_OR_ROLLOUT',
     'new_numeric_target': 'NO_CONTEXT_REFERENCE_ADOPTED', 'normative_choice_remaining': 'GLOBAL_V1_TP_REFERENCES_ARE_NOT_CONTEXT_REFERENCES',
     'imbalance': 'CANNOT_ALLOCATE_GLOBAL_TP_BY_INVENTED_PROPORTION', 'route_transfer': 'NO_STRUCTURAL_CORRECTION',
     'exactness': 'ADDITIVE_COUNT_CONSTRAINT_CAN_BE_EXACT_BUT_POLICY_REFERENCE_UNFROZEN'},
  ]


def main():
  for name, row in build().items():
    p.persist(p.PUBLIC / name, row)
  print('SEALED_11_PUBLIC_POLICY_REVIEW_ARTIFACTS_NO_PRIVATE_ACCESS')


if __name__ == '__main__':
  main()
