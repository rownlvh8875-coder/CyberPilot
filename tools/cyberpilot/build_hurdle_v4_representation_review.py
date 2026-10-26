"""Public-only representation architecture record, with immutable input locks."""

import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_representation_review as r

BASELINE = 'da23b158fa2ff6eecf1ca8d33ae5e2190fcba078'
PREFIX = 'empirical-hurdle-stage1-v4-'
ROOT = Path(__file__).resolve().parents[2]
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
                                                           'b692752e967549f6bc6747de36fee64f01a79dded2c530176a450e092eb63877'),
 'empirical-hurdle-stage1-v4-policy-decision': ('a594f45e4cdb3499f7e8a0075b077ec0b6df21d1f390d4cea03113a2346fe8f2',
                                                '613d3d70740047c4273ab1548345008d69fa64a34fbd5a247a5841cce6ff0636'),
 'empirical-hurdle-stage1-v4-next-architecture-trigger': ('8d193ab2c4bc61c0a2952918b62cbe390072b5957c943ff22ae58607a5ec4d01',
                                                          '2488ed929c9409473cfc0f8996bdabda26b898b29fbf3b115a424e150a92ab50'),
 'empirical-hurdle-stage1-v4-policy-review-validation': ('fff34d8fa48126136cb87d9dbda9a84a8d7adc568d1f19bbce4ed95976c5486a',
                                                         '39c896068d72ad4c1f2012f3d091f84f25624cb7c8dcdcc05aeba72282eb1d0d'),
 'empirical-hurdle-stage1-v4-state-ranking-limit': ('5130c2a72e415c998a65b4f058d340e2efd1379907a589445dfa11417e899bec',
                                                    'fe4b0a99e6507203d4437162bbb4634869e82a32b33f81508bfb2a9de55cba00')}
SOURCE_PINS = {'openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py': 'b410b2f0138848faf4e976094a1bd4f3cc3ac44418b54a24310717c6261e0e73',
 'openpilot/tools/cyber_autotune/empirical_s2_ri_fit_cv_math.py': 'a1c1203c8222df067064ff1891aafa82cdafd997338c7ca7687a321c66777f29',
 'openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_data.py': '9e104a83a928c6b997a914a606820f2d2190fa56917e4042856474f747b900ac',
 'openpilot/tools/cyber_autotune/empirical_causal_dataset_reader.py': '44aaf31270f7ea2e59869ba1a5fd8f486e114cfa071678792c62ba2d8caa6a82',
 'openpilot/tools/cyber_autotune/empirical_causal_dataset_execution.py': '2d15c63cd79dbaa6161921bcee58908c2558222d1a522f060b933fef5355c2bc',
 'openpilot/tools/cyber_autotune/empirical_hurdle_v4_state_contract.py': '3a21944b47ee82f4401b6742742924b7458741f17959e3ed2c2d41df67f68793'}


def locked_inputs():
  out = {}
  try:
    for name, (file_sha, receipt_sha) in PINS.items():
      raw = (p.PUBLIC / (name + '.json')).read_bytes()
      r.need(p.sha(raw) == file_sha)
      row = p.verify(json.loads(raw))
      r.need(row['receipt_sha256'] == receipt_sha)
      out[name] = row
    for path, expected in SOURCE_PINS.items():
      r.need(p.sha((ROOT / path).read_bytes()) == expected)
  except (ValueError, OSError, KeyError, TypeError) as error:
    raise ValueError('STAGE1_REPRESENTATION_REVIEW_INPUT_CONFLICT') from error
  return out


def build():
  inputs = locked_inputs()
  def get(name):
    return inputs[PREFIX + name]
  prior = get('policy-decision')
  r.need(prior['status'] == 'V4_TWO_CONTEXT_POLICY_DECISION_INCONCLUSIVE' and not prior['two_context_track_closed'])
  r.need(get('next-architecture-trigger')['signal_satisfied'])
  r.need(inputs['empirical-hurdle-stage1-fixed-threshold-family-review']['status'] ==
         'GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED')
  r.need(get('causal-state-contract')['status'] == 'V4_TWO_CONTEXT_CAUSAL_STATE_CONTRACT_ESTABLISHED')
  r.need(get('option-a-eligibility')['fitting_result'] == 'V4_TWO_CONTEXT_EXACT_FITTING_EXACT_BUT_CARTESIAN_WORST_CASE')
  dimensions = [r.counts(c) for c in r.old.CANDIDATES]
  decision = r.select(r.options())
  r.need(decision['selected_option'] == 'C')
  common = {
    'schema': 'BOUNDED_STAGE1_REPRESENTATION_ARCHITECTURE_REVIEW_V1', 'baseline': BASELINE,
    'scope': 'PUBLIC_STATIC_SYNTHETIC_ARCHITECTURE_ONLY', 'actual_execution_authorized': False,
    'private_numeric_array_opens': 0, 'raw_log_openings': 0, 'qlog_openings': 0, 'holdout_openings': 0,
    'model_fit_calls': 0, 'normalizer_fit_calls': 0, 'threshold_search_calls': 0, 'prediction_replay_calls': 0,
    'actual_rollout_calls': 0, 'source_writes': 0, 'model_selection_calls': 0,
    'holdout': 'CLOSED', 'opening_count': 0, 'holdout_discovery': 0, 'pooled_refit': 'NOT_AUTHORIZED',
    'vehicle_authority': 'NONE', 'historical_states_preserved': prior['historical_states_preserved'],
    'preserved_authority_states': prior['preserved_authority_states'],
    'prior_review_states_preserved': prior['prior_review_states_preserved'] + ['V4_TWO_CONTEXT_POLICY_DECISION_INCONCLUSIVE'],
    'v4': dict.fromkeys(('fitting', 'cv', 'development', 'rollout', 'performance', 'selection'), 'NOT_RUN'),
    'architecture_frozen': True, 'fitting_policy_frozen': False, 'actual_model': 'NOT_FIT',
    'hugging_face': {'setup': 'NOT_RUN', 'login': 'NOT_RUN', 'repo': 'NOT_CREATED', 'upload': 0, 'download': 0},
  }
  out = {}
  def add(name, body):
    out[PREFIX + name + '.json'] = p.seal({**common, 'component': name, **body})
  add('representation-review-inputs', {
    'public_input_lock': {name + '.json': {'file_sha256': pair[0], 'receipt_sha256': pair[1]} for name, pair in PINS.items()},
    'source_code_lock': SOURCE_PINS, 'input_reconciliation': 'PASS', 'new_private_audit': False,
    'current_public_counts': {'full': 4860, 'combined': 2001, 'lateral': 16},
    'fixed_threshold_closure_kind': 'EMPIRICAL_PROJECT_POLICY_CLOSURE_NOT_MATHEMATICAL_IMPOSSIBILITY'})
  add('current-feature-contract', {
    'source_trace': {
      'hurdle_delegation': 'openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py:parameters,anchors,features',
      'construction': 'openpilot/tools/cyber_autotune/empirical_s2_ri_fit_cv_math.py:features,transform',
      'data_mapping': 'openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_data.py:load_route,design',
      'command_reader': 'openpilot/tools/cyber_autotune/empirical_causal_dataset_reader.py:numeric',
      'angle_rate_contract': 'openpilot/tools/cyber_autotune/empirical_causal_dataset_execution.py:source_proof',
      'causal_state': 'openpilot/tools/cyber_autotune/empirical_hurdle_v4_state_contract.py:observed_context,ProjectedContext'},
    'ordered_vector': ['1', 'command[k-d-L+1..k-d]', 'tick[k-L+1..k]-tick[k-L..k-1]', 'tick[k]', 'vEgo[k]'],
    'P': '2*L+3_INCLUDING_INTERCEPT', 'dimensions': dimensions,
    'feature_names_by_candidate': {c: r.feature_names(c) for c in r.old.CANDIDATES},
    'last_delta_zero_based_index': '2*L=P-3', 'ordering': 'GROUP_ORDER_AS_VECTOR; HISTORY_OLDEST_FIRST',
    'dtype': 'float64', 'order': 'C',
    'command_semantics': 'POST_CARCONTROLLER_NORMALIZED_COMMAND_NOT_PHYSICAL_APPLIED_EPS_TORQUE',
    'angle_source': 'SAS11.SAS_Angle', 'delta_semantics': 'SOURCE_GRID_TICK_INCREMENT_NOT_PHYSICAL_EPS_MOVEMENT',
    'rate': 'SOURCE_NATIVE_RATE_CODE_ONLY; RATE_SOURCE_CONTRACT_PARTIAL; NO_NEW_RATE_DEPENDENCY',
    'old_equation': 'sigmoid(dot(beta,transform(x,V1_TRAIN_normalizer)))',
    'old_normalizer': 'TRAIN_ONLY_MEAN_STD_DDOF0; CONSTANT_COLUMNS_DROPPED_EXCEPT_INTERCEPT; ASCENDING_EFFECTIVE_INDICES',
    'old_effective_dimension': 'DATA_DEPENDENT_P_EFF_LE_P_NOT_MEASURED_HERE',
    'anchor_requirement': 'R=max(d+L,L+1)>=2; SAME_EXISTING_ELIGIBLE_HISTORY_AND_HORIZON; NO_ANCHOR_CHANGE',
    'target': 'tick[k+1]_TRAIN_LABEL_ONLY_IN_FUTURE_AUTHORIZED_FIT; DEV_ROLLOUT_SCORING_ONLY; NEVER_CAUSAL_INPUT'})
  math = r.witnesses()
  add('representation-equivalence', {
    'negative_controls': {key: math[key] for key in ('state_intercept', 'state_affine')},
    'two_threshold_equivalence': 'sigmoid(old_eta+b_z)>tau iff old_eta>logit(tau)-b_z, 0<tau<1',
    'positive_affine': 'a_z>0 => same strict ordering within z; zero slope constant; negative slope reverses but usefulness unsupported',
    'global_or_per_state_nondecreasing_calibration': 'PRESERVES_OR_COARSENS_WITHIN_STATE_ORDER_NOT_NEW_RANK_INFORMATION',
    'dual_head_vs_full_interaction': 'w_base=w_static; w_delta=w_move-w_static; SAME_REAL_LOGITS',
    'dual_head_not_fixed_score_two_threshold': 'CONTEXT_SPECIFIC_FEATURE_COEFFICIENTS_CAN_CHANGE_WITHIN_CONTEXT_ORDER',
    'ordinary_global_linear_refit': 'SAME_FUNCTION_CLASS_AS_EXISTING_LOGISTIC; NEW_FITTING_POLICY_NOT_NEW_ARCHITECTURE',
    'floating_caveat': 'REAL_MATH_EQUIVALENCE_NOT_BIT_EXACT_TRANSFORM_EVALUATION; SIGMOID_SATURATION_CAN_CREATE_TIES'})
  add('representation-expressivity', {'data_origin': r.SCOPE,
    'witnesses': {key: math[key] for key in ('dual_head', 'quadratic', 'mlp')},
    'what_is_proved': 'EXISTENCE_OF_DIFFERENT_ORDER_WITH_SAME_CAUSAL_CONTEXT',
    'what_is_not_proved': 'REAL_DATA_GAIN_OR_ROUTE_TRANSFER_IMPROVEMENT',
    'mlp_one_unit_caveat': 'RELU_SCORE_IS_NONLINEAR; ITS_THRESHOLD_GATES_ARE_HALFSPACES_OR_CONSTANTS; NO_FALSE_LINEAR_SCORE_CLAIM'})
  add('model-options', {'options': json.loads(p.canonical(r.options())), 'eligibility_fields': list(r.ELIGIBILITY),
    'C_vs_D': 'C_ONE_SUPPORTED_CONTEXT_INTERACTION_ASSUMPTION; D_UNRESTRICTED_ALL_PAIR_CURVATURE; C_ALSO_FEWER_GENERIC_PARAMETERS_FOR_ALL_P',
    'E': 'ALL_STATE_X_TERMS_IS_C_ALIAS; SMALLER_SUBSET_NEEDS_UNSUPPORTED_SELECTION',
    'F_G': 'CAN_CHANGE_ORDER_BUT_WIDTH_ACTIVATION_INITIALIZATION_OPTIMIZER_REGULARIZATION_CONVERGENCE_UNRESOLVED',
    'H': 'NO_EXISTING_DECLARED_AUTOTUNE_TREE_FITTING_PATH_IDENTIFIED; NO_DEPENDENCY_ADDED',
    'unreviewed_possible_models': 'NOT_CLAIMED_DOMINATED_OR_IMPOSSIBLE'})
  add('parameter-complexity', {'structures': dimensions,
    'dual': {'nominal': '2P', 'generic_identifiable_upper': '2P-1', 'actual': 'r_static+r_move_UNKNOWN',
      'new_generic_directions_over_full_rank_global': 'P-1',
      'proof': '(1-z)*delta_prev=0; IN_[x,z*x]_delta_prev=z*delta_prev',
      'shared_centered_proof': 'q=(delta-mu)/s; q-z*q+(mu/s)*(1-z)=0',
      'basis_or_gauge_selected': False, 'inference': 'SELECT_ONE_HEAD_P_DOT_PLUS_SIGMOID_O(P)',
      'training_dense_design_bytes': '8*N*P_IF_CONTEXT_SPLIT; 8*N*2P_IF_ZERO_PADDED',
      'hessian_time': 'O(N*P^2+P^3)_PER_NEWTON_UPDATE', 'hessian_memory': 'O(P^2)'},
    'quadratic': {'q': 'P-1', 'products': 'q*(q+1)/2', 'total': 'P*(P+1)/2',
      'intercept_products': 'EXCLUDED_AS_DUPLICATE_LINEAR_TERMS', 'design_bytes': '8*N*M', 'hessian_bytes': '8*M*M',
      'fit_time': 'O(N*M^2+M^3)_PER_NEWTON_UPDATE', 'conditioning': 'PRODUCT_SCALING_COLLINEARITY_AND_SEPARATION_RISK'},
    'mlp': {'input_nonintercept_count': 'P-1', 'global': 'H*(P+1)+1', 'state_concat': 'H*(P+2)+1',
      'dual': '2*(H*(P+1)+1)', 'actual_H': 'NOT_SELECTED', 'illustrative_H2_only': {str(p0): r.mlp_counts(p0, 2) for p0 in (5, 13, 33, 93)}},
    'no_private_design_matrix_allocated': True})
  add('training-feasibility', {
    'algebra': math['training_algebra'], 'mean_stopping_counterexample': math['mean_stopping'],
    'separation_counterexample': math['separation'],
    'independent_equivalence_conditions': ['UNCOUPLED_UNREGULARIZED_SUM_LIKELIHOOD_SEPARATES_BY_CONTEXT',
      'NONEMPTY_CONTEXTS', 'UNCOUPLED_PARAMETER_DOMAINS', 'HEAD_ARGMIN_SETS_EXIST'],
    'global_mean': 'n0/N*L0_mean+n1/N*L1_mean; SAME_MATHEMATICAL_ARGMIN_IF_POSITIVE_WEIGHTS_AND_NO_COUPLED_PENALTY',
    'finite_unique_mle': 'REQUIRES_IDENTIFIABLE_EFFECTIVE_BASIS_AND_NONSEPARATION_EACH_HEAD_NOT_JUST_CLASS_SUPPORT',
    'regularization': 'NOT_CHOSEN; COUPLED_PENALTIES_BREAK_SEPARATION; LOCAL_MEAN_PENALTIES_REQUIRE_WEIGHT_SCALING',
    'current_solver': {'function': 'empirical_hurdle_fit_cv_math.newton', 'loss': 'UNREGULARIZED_MEAN_LOG_LOSS',
      'initialization': 'ZERO_FLOAT64', 'max_updates': r.old.MAX_UPDATES, 'maxabs_gradient_tolerance': r.old.GRADIENT_TOLERANCE,
      'armijo_c': r.old.ARMIJO_C, 'trial_exponents': list(r.old.TRIAL_EXPONENTS),
      'support_each_class': r.old.SUPPORT, 'linear_solver': 'numpy.linalg.solve'},
    'current_defaults_are_future_policy': False,
    'solver_reuse': 'DETERMINISTIC_LOGISTIC_METHOD_AVAILABLE_CONDITIONAL_ON_FUTURE_IDENTIFIABLE_BASIS_SUPPORT_SEPARATION_AND_STOPPING_CONTRACT',
    'byte_equivalence_not_claimed': ['CONTEXT_FLOAT_REDUCTION_ORDER', 'MEAN_GRADIENT_SCALE',
      'SHARED_VS_INDEPENDENT_ARMIJO', 'REPARAMETERIZATION', 'REGULARIZATION'],
    'normalization_options': [
      {'option': 'REUSE_SHARED_V1_TRAIN_NORMALIZER', 'pros': 'BYTE_IDENTITY_NO_NORMALIZER_REFIT',
       'risk': 'STATIC_HEAD_LAST_DELTA_COLLINEAR_WITH_INTERCEPT; BASIS_REQUIRED'},
      {'option': 'SEPARATE_CONTEXT_TRAIN_NORMALIZERS', 'pros': 'LOCAL_CONSTANT_DROP_AND_SCALING',
       'risk': 'NEW_NORMALIZER_POLICY_AND_IDENTITIES; NOT_AUTHORIZED_OR_CHOSEN'},
      {'option': 'RAW_INPUTS_IDENTIFIABLE_BASIS', 'pros': 'NO_NEW_NORMALIZER', 'risk': 'SCALING_CONDITIONING_AND_CONSTANT_COLUMNS'}],
    'normalizer_selected': None, 'support_threshold_selected': None,
    'actual_effective_ranks': 'UNKNOWN_NO_PRIVATE_ACCESS', 'fit_calls': 0})
  add('route-transfer-relevance', {
    'source_aggregates': get('route-transfer-analysis')['folds'],
    'conditional_auc_ranges': get('onset-continuation-support')['auc_ranges'],
    'onset_support': get('onset-continuation-support')['routes'],
    'ranking_capability': 'CAN_CHANGE_WITHIN_STATE_RANKING_INCLUDING_MAJORITY_ONSET_CONTEXT',
    'route_invariance': 'NOT_INHERENTLY_ROUTE_CALIBRATION_INVARIANT',
    'claim': 'REPRESENTATION_REVIEW_SUPPORTED_NOT_REAL_TRANSFER_GAIN_PREDICTED',
    'existing_rank_description': 'WEAK_ABOVE_CHANCE_NOT_RANDOM_NOT_VALIDATED_GOOD_CLASSIFIER',
    'new_representation_does_not_remove_decision_policy_requirement': True})
  add('artifact-lifecycle-review', {
    'selected_family': decision['selected_family'], 'model_size': 'COMPACT_LOGISTIC_COEFFICIENTS',
    'registry_status': 'HUGGING_FACE_NOT_REQUIRED_FOR_MODEL_SIZE',
    'private_artifact_plan': 'E_EXTERNAL_SSD_MODEL_COEFFICIENT_NPY_OR_JSON_PLUS_NORMALIZER_MANIFEST_HASHES_AND_CAUSAL_CONTRACT',
    'public_artifact_plan': 'DESIGN_AGGREGATES_RECEIPTS_ONLY_NO_COEFFICIENTS_OR_NORMALIZERS',
    'future_neural_family': 'DEDICATED_MODEL_REGISTRY_AND_EXPORT_PARITY_REVIEW_IF_AUTHORIZED; HF_BEGINNER_GUIDANCE_REQUIRED',
    'model_artifact_generated': False, 'onnx_export': 'NOT_RUN'})
  add('representation-selection-rule', {
    'eligibility': list(r.ELIGIBILITY), 'lexicographic': list(r.RULE),
    'unknown_eligibility': 'NOT_ELIGIBLE_NOW_NOT_PROVEN_IMPOSSIBLE',
    'first_priority_categories': {'0': 'POSITIVE_FIXED_SCORE_CONTROLS_FAIL_RANK; NEGATIVE_SLOPE_VARIANT_NOT_ADOPTED',
      '1': 'ALL_X_BY_SINGLE_SUPPORTED_CONTEXT_BIT',
      '2': 'UNRESTRICTED_FULL_PAIRWISE_CURVATURE', '3': 'UNRESOLVED_SUBSET_NEURAL_TREE_ARCHITECTURE'},
    'category_basis': 'EXPLICIT_STRUCTURAL_ASSUMPTIONS_NOT_PERFORMANCE_OR_NUMERIC_COST_WEIGHTS',
    'parameter_order': 'C_GENERIC_2P-1<D_P(P+1)/2_FOR_EVERY_P_IN_16_STRUCTURES',
    'if_assumption_tier_C_D_tied': 'C_STILL_WINS_PARAMETER_COUNT_FOR_ALL_STRUCTURES',
    'tie': 'INCONCLUSIVE_NO_ARBITRARY_ID_TIE_BREAK', 'scope': 'REVIEWED_FULLY_SPECIFIED_FAMILIES_NOT_ALL_CONCEIVABLE_MODELS'})
  add('representation-decision', {**decision, 'design_status': 'HURDLE_STAGE1_V4_REPRESENTATION_DESIGN_FROZEN',
    'why': 'MINIMUM_SUPPORTED_CONTEXT_FEATURE_INTERACTION_WITH_NO_SUBSET_WIDTH_OR_NEW_SENSOR; CHANGES_WITHIN_STATE_ORDER',
    'new_state_information_bits': 1, 'new_recurrent_hidden_state': 0, 'state_already_in_existing_history': True,
    'nominal_coefficients_by_L': {'1': 10, '5': 26, '15': 66, '45': 186},
    'generic_identifiable_upper_by_L': {'1': 9, '5': 25, '15': 65, '45': 185},
    'stage1_model_change': 'FUTURE_NEW_CONTEXT_CONDITIONAL_COEFFICIENT_MODEL_NOT_FIT',
    'stage2': 'UNCHANGED', 'normalizers': 'FUTURE_POLICY_UNRESOLVED_NO_REFIT',
    'threshold_policy': 'UNRESOLVED_NO_SEARCH', 'two_context_threshold_track_closed': False, 'no_auto_advance': True})
  add('representation-design-contract', {
    'status': 'HURDLE_STAGE1_V4_REPRESENTATION_DESIGN_FROZEN', 'family': decision['selected_family'],
    'inputs': 'EXACT_EXISTING_RAW_CAUSAL_x_PLUS_z_DERIVED_BEFORE_ANY_NORMALIZATION',
    'logit': '(1-z)*dot(w_static,x)+z*dot(w_move,x)', 'probability': 'sigmoid(logit)',
    'equivalent_parameterization': 'dot(w_base,x)+z*dot(w_delta,x); w_base=w_static; w_delta=w_move-w_static',
    'equation_semantics': 'REAL_FUNCTION_CLASS; NUMERIC_EFFECTIVE_BASIS_AND_NORMALIZATION_DEFERRED_TO_FITTING_POLICY',
    'fixed': ['EXISTING_16_d_L_STRUCTURES', 'EXACT_EXISTING_FEATURE_GROUPS_ORDER_AND_ANCHORS', 'BINARY_z_NO_SIGN_OR_MAGNITUDE',
      'FLOAT64_C_ORDER', 'STAGE2_UNCHANGED', 'NO_RATE_INPUT', 'NO_NEW_SENSOR'],
    'fitted': 'TWO_HEAD_COEFFICIENT_FUNCTIONS_UNFIT; REPRESENTATIVES_NEED_IDENTIFIABILITY_CONTRACT',
    'candidate_model_parameters': 'CONTINUOUS_REAL_COEFFICIENT_FAMILY_NOT_A_DISCRETE_WEIGHT_SEARCH; NO_COEFFICIENT_VALUES_CHOSEN',
    'new_free_architecture_hyperparameters': [], 'decision_cutoff': 'FITTING_POLICY_UNRESOLVED',
    'regularization': 'FITTING_POLICY_UNRESOLVED', 'normalization': 'FITTING_POLICY_UNRESOLVED',
    'one_step_z': '1[tick[k]-tick[k-1]!=0]; TARGET_NOT_CAUSAL_INPUT; FUTURE_TRAIN_TARGET_LABEL_ONLY',
    'rollout_initial_z': 'RELATIVE_TIME_1[observed_tick_at_0-observed_tick_at_minus1!=0]; HISTORY_ARRAY_LAST_MINUS_PENULTIMATE',
    'rollout_recursive_z': '1[projected_tick[h]-projected_tick[h-1]!=0], h>=1',
    'gate_is_not_state': 'MOVE_GATE_CAN_PROJECT_HOLD_AND_NEXT_z=0',
    'model_hidden_state': 'NONE; EXTERNAL_CONTEXT_ONLY',
    'boundaries': 'ROUTE_SEGMENT_CAUSAL_RUN_ELIGIBILITY_GRID_BREAK_INVALIDATES_CONTEXT',
    'predecessor_admission': 'SAME_ROUTE_SEGMENT_RUN; SOURCE_AND_WITHIN_CAUSAL_RUN_INDICES_PLUS_1; GRID_PLUS_10000000_NS; BOTH_ELIGIBLE; STREAK_PLUS_1',
    'initial_history_array_indices': 'LAST[-1]_MINUS_PENULTIMATE[-2]; RELATIVE_TIME_0_MINUS_MINUS1_NOT_ARRAY_0_MINUS_LAST',
    'missing_or_nonfinite': 'FAIL_CLOSED_NO_PADDING_NO_STATIC_DEFAULT_NO_OTHER_HEAD_FALLBACK',
    'state_equality': 'EXACT_DELTA_NE_ZERO_NO_EPSILON',
    'future_gate_equality': 'NOT_FROZEN_WITH_THRESHOLD_POLICY',
    'support_minimum': 'FITTING_POLICY_UNRESOLVED_NO_SILENT_201_PER_HEAD',
    'no_feasible_or_fit_failure': 'FAIL_CLOSED_NO_OLD_MODEL_THRESHOLD_OR_HEAD_FALLBACK',
    'no_execution_interface': True, 'coefficient_generation_authorized': False,
    'future_truth_use': 'FUTURE_MEASURED_DEV_ROLLOUT_TRUTH_SCORING_ONLY; FUTURE_AUTHORIZED_TRAIN_TARGET_y_LABEL_ALLOWED; NEVER_CAUSAL_CONTEXT_OR_COVARIATE'})
  add('future-fitting-requirements-v2', {
    'next_increment': 'FREEZE_CONTEXT_CONDITIONAL_LOGISTIC_FITTING_POLICY_ONLY',
    'required_freezes': ['NORMALIZATION_SHARED_VS_CONTEXT_LOCAL_VS_RAW', 'IDENTIFIABLE_EFFECTIVE_BASIS_OR_GAUGE',
      'PER_HEAD_CLASS_SUPPORT_AND_RANK', 'COMPLETE_QUASI_SEPARATION_FAILURE_CERTIFICATE',
      'OPTIMIZER_INITIALIZATION_LOSS_SCALING_CONVERGENCE_LINE_SEARCH', 'REGULARIZATION_OR_NONE_WITH_JUSTIFICATION',
      'DECISION_THRESHOLD_OBJECTIVE_FEASIBILITY_FINITE_DOMAIN_EQUALITY_TOTAL_TIE_RULE',
      '16_STRUCTURES_EXACT_FOLDS_ANCHORS', 'NO_DEV_LABEL_FITTING',
      'E_EXTERNAL_SSD_AUTHORIZATION_STORAGE_CAPACITY_MODEL_LIFECYCLE',
      'TWO_RUN_BYTE_REPEATABILITY_VERIFY_ONLY_RESUME', 'UNCHANGED_FINAL_GATE_AND_SELECTION_BINDING'],
    'future_execution_authorization_separate': True, 'current_stage1_executor_cannot_fit_this_architecture': True,
    'not_started': ['POLICY_FREEZE', 'FIT', 'CV', 'DEV', 'ROLLOUT', 'HF', 'HOLDOUT', 'VEHICLE']})
  add('representation-validation', {
    'status': 'BOUNDED_STAGE1_REPRESENTATION_ARCHITECTURE_REVIEW_COMPLETE',
    'checks': {'new_focused': {'passed': 31}, 'prior_focused': {'passed': 233},
      'combined_empirical': {'passed': 2032}, 'full_autotune_controls': {'passed': 4891}, 'lateral_replay': {'passed': 16},
      'ruff': 'PASS', 'compileall': 'PASS', 'json_files': {'passed': 704}, 'publication_privacy_authority': 'PASS',
      'git_diff_check': 'PASS', 'scons': 'PASS', 'research_review': 'APPROVED', 'numeric_causal_authority_review': 'APPROVED'},
    'validation_environment': {'python': '3.12.13', 'numpy': '2.5.3', 'blas_threads': 1, 'temp': 'E_BACKED_WSL',
      'legacy_d_fixture_isolation': 'PRIVATE_MOUNT_NAMESPACE_TMPFS_NO_GLOBAL_GUARD_CHANGE'},
    'full_source_stability_sha256': 'd433c8b064aa418d6a2b665e548420a65908ae8ced5dab6a398ad6d843be8083',
    'initial_full_attempt': {'passed': 4890, 'failed': 1, 'reason': 'EXISTING_SYNTHETIC_WORKER_FAILED_DURING_CONCURRENT_REVIEW_EDITS',
      'exact_worker_internal_reason': 'NOT_EXPOSED', 'isolated_retry': 'PASS', 'no_test_or_gate_change': True},
    'final_full_attempt': {'passed': 4891, 'failed': 0, 'source_binding_before_equals_after': True},
    'synthetic_algebra': 'PASS_NO_FITTING', 'input_lock': 'PASS', 'actual_v4_performance': 'NOT_RUN'})
  return out


def main():
  for name, row in build().items():
    p.persist(p.PUBLIC / name, row)
  print('SEALED_14_PUBLIC_REPRESENTATION_ARTIFACTS_NO_PRIVATE_ACCESS')


if __name__ == '__main__':
  main()
