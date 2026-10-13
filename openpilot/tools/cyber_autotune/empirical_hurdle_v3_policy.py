"""Public-only V3 design and execution contracts. No private execution authority."""

from openpilot.tools.cyber_autotune import empirical_hurdle_v3_temporal as audit
from openpilot.tools.cyber_autotune.empirical_hurdle_v3_temporal_binding import PINS as TEMPORAL_PINS

p, io = audit.p, audit.io
POLICY = 'HURDLE_STAGE1_DECISION_POLICY_V3'
FAMILY = 'V1_TRAIN_TP_CONSTRAINED_FIXED_THRESHOLD'
STRATEGY = 'REUSE_BYTE_IDENTICAL_V1_FITTED_MODELS'
V1_THRESHOLD_SHA = '543dc8a06914d9ef5baaf9da73254429dba200c207310252a1b522ea6d16b389'
ORDER = [
  'CAUSAL_DEPLOYABLE',
  'NO_DEVELOPMENT_LABEL_DEPENDENCY',
  'PREVENTS_V2_EXTREME_MOVE_SUPPRESSION_BY_CONSTRUCTION',
  'PRESERVES_EXISTING_ABOVE_CHANCE_RANK_SIGNAL',
  'DIRECTLY_ADDRESSES_CROSS_ROUTE_CALIBRATION_OR_DECISION_FAILURE',
  'MINIMUM_NEW_FREE_PARAMETERS',
  'NO_NEW_MODEL_FIT',
  'UNCHANGED_FINAL_ACCEPTANCE',
  'LOWEST_IMPLEMENTATION_COMPLEXITY',
  'FAIL_CLOSED',
]


def filename(label):
  return 'empirical-hurdle-' + ('stage1-decision-policy-v3' if label == 'policy' else 'stage1-v3-' + label) + '.json'


def temporal_inputs():
  values = {}
  for name, pin in TEMPORAL_PINS.items():
    io.require(io.digest(p.PUBLIC / name) == pin['file_sha256'], 'V3_TEMPORAL_EVIDENCE_CONFLICT')
    row = io.read_json(p.PUBLIC / name, pin['receipt_sha256'])
    p.verify(row)
    io.require(row['receipt_sha256'] == pin['receipt_sha256'], 'V3_TEMPORAL_EVIDENCE_CONFLICT')
    io.require(row['schema'] == 'HURDLE_STAGE1_V3_TEMPORAL_PUBLIC' and row['baseline'] == audit.BASELINE)
    io.require(row['v1_manifest_sha256'] == io.SOURCE_SHA and row['v2_manifest_sha256'] == audit.v.V2_SHA)
    io.require(row['v3_performance'] == 'NOT_RUN' and row['execution_calls'] == audit.v.ZERO)
    io.require(row['holdout'] == 'CLOSED' and row['opening_count'] == 0 and row['vehicle_authority'] == 'NONE')
    values[name] = row
  io.require(len({r['private_manifest_sha256'] for r in values.values()}) == 1)
  trigger = values[filename('temporal-design-trigger')]
  repeat = trigger['repeatability']
  p.verify(repeat)
  io.require(repeat['status'] == 'BYTE_EXACT_PASS' and repeat['trapped_resume'] == 'PASS' and repeat['v3_performance'] == 'NOT_RUN')
  io.require(repeat['manifest_sha256'] == trigger['private_manifest_sha256'])
  return values


def build():
  binding = audit.public_inputs()
  temporal = temporal_inputs()[filename('temporal-design-trigger')]
  v1 = io.read_json(p.PUBLIC / 'empirical-hurdle-threshold-results-v1.json', V1_THRESHOLD_SHA)
  models = io.read_json(p.PUBLIC / 'empirical-hurdle-stage1-results-v1.json')
  references = []
  for expected, row, model in zip(io.JOBS, v1['jobs'], models['jobs'], strict=True):
    io.require((row['candidate_id'], row['fold']) == expected)
    io.require((model['candidate_id'], model['fold']) == expected)
    c = row['threshold']
    io.require(0 < c['TP'] <= c['P'] and 20 * c['TP'] > c['P'])
    io.require(c['P'] == model['train_move_count'] and c['N'] == model['train_static_count'])
    references.append(
      {
        'candidate_id': expected[0],
        'fold': expected[1],
        'reference_tp': c['TP'],
        'positive_count': c['P'],
        'negative_count': c['N'],
        'v1_confusion_receipt_sha256': c['receipt_sha256'],
        'train_anchor_sha256': model['stage1']['train_anchor_sha256'],
        'stage1_model_sha256': model['stage1']['model_receipt_sha256'],
        'stage1_coefficient_sha256': model['stage1']['coefficient_sha256'],
        'stage1_normalizer_sha256': model['stage1']['normalizer_receipt_sha256'],
      }
    )
  pins = binding['public_inputs']

  def receipt(name):
    return pins['empirical-hurdle-' + name + '.json']['receipt_sha256']

  preserved = io.read_json(p.PUBLIC / 'empirical-hurdle-stage1-v2-retrospective-execution-readiness.json')['preserved_authority']
  common = {
    'schema': 'HURDLE_STAGE1_V3_DECLARATIVE_CONTRACT',
    'baseline': audit.BASELINE,
    'family': 'HURDLE_RI_V1',
    'decision_policy': POLICY,
    'policy_family': FAMILY,
    'change_scope': 'DECISION_POLICY_ONLY',
    'model_strategy': STRATEGY,
    'v3_private_execution': 'NOT_RUN',
    'actual_execution_authorized': False,
    'holdout': 'CLOSED',
    'opening_count': 0,
    'holdout_discovery': 0,
    'vehicle_authority': 'NONE',
    'historical_v1': 'HURDLE_NO_ADMISSIBLE_CANDIDATE',
    'historical_v2': 'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE',
    'historical_selection': 'MODEL_SELECTION_FAILED_CLOSED',
    'input_binding_sha256': binding['receipt_sha256'],
    'preserved_authority': preserved,
  }
  training = {
    'population': 'CANDIDATE_FOLD_TRAIN_ONLY_EXACT_V1_ORDERED_ANCHORS',
    'reference': 'IMMUTABLE_V1_TRAIN_CONFUSION_TP_NOT_THRESHOLD_VALUE',
    'reference_receipt_sha256': V1_THRESHOLD_SHA,
    'references': references,
    'reference_guard': 'PYTHON_INT_20_TIMES_REFERENCE_TP_STRICTLY_GREATER_THAN_P',
    'reference_guard_rationale': 'COMPLEMENT_OF_EXISTING_MISSED_MOVE_GREATER_THAN_0.95_STATE_NO_NEW_TUNING_CONSTANT',
    'reference_binding': ['candidate', 'fold', 'train_anchor_sha256', 'positive_count', 'negative_count', 'stage1_model_sha256', 'v1_confusion_receipt_sha256'],
    'recall_constraint': 'TP_V3_TRAIN>=TP_V1_TRAIN',
    'feasibility': ['TRUE_MOVE_RMSE<=HOLD', 'TRUE_MOVE_MAE<=HOLD', 'TRUE_MOVE_P95<=HOLD', 'ALL_RMSE<HOLD', 'TP>=REFERENCE_TP'],
    'objective': ['MAX_PROJECTED_EXACT_HIT_COUNT', 'MIN_STATIC_PROJECTED_FALSE_MOVE_COUNT', 'MAX_WITHIN_ONE_TICK_COUNT', 'MAX_THRESHOLD'],
    'count_type': 'PYTHON_INT',
    'epsilon': 0,
    'metric_semantics_sha256': receipt('metric-contract-v1'),
    'p95': 'NUMPY_PERCENTILE_ABSOLUTE_ERROR_95_METHOD_LINEAR_OR_BYTE_EXACT_EQUIVALENT',
    'reduction': 'C_ORDER_FLOAT64_ORIGINAL_ROW_ORDER_NUMPY_REDUCTIONS',
    'integrated_error': 'BRANCH_DELTA_MINUS_ACTUAL_DELTA_FLOAT64',
    'projection': 'DIRECT_BINARY64_CURRENT_PLUS_DELTA_ROUND_HALF_TO_EVEN_SIGNED16_NO_FORCED_MOTION',
    'support': 'V1_TRAIN_STATIC_AND_MOVE_EACH_GE_201; SYNTHETIC_FIXTURES_DO_NOT_AUTHORIZE_SMALL_REAL_POPULATIONS',
    'no_feasible': 'V3_NO_FEASIBLE_THRESHOLD',
    'reference_conflict': 'V3_REFERENCE_CONFLICT',
    'fallback': 'NONE',
    'undefined_nonfinite_out_of_range': 'WHOLE_FOLD_FAIL_NO_ROW_DROP_NO_CLIP',
    'balanced_accuracy': 'REPORT_ONLY',
    'all_move_constraint': 'NONE_NO_ALL_MOVE_EXCLUSION_GUARANTEE',
    'guarantee': 'RETURN_OR_FAIL_TRAIN_TP_GE_REFERENCE_ONLY',
    'development_guarantee': 'NONE_CROSS_ROUTE_SCORE_SHIFT_UNCORRECTED',
    'forbidden_inputs': ['DEVELOPMENT', 'HOLDOUT', 'V1_V2_DEV_METRICS', 'ATTRIBUTION_CANDIDATE_OUTCOMES', 'ROLLOUT_METRICS'],
  }
  options = {
    'A': {
      'family': 'RECALL_CONSTRAINED_FIXED_THRESHOLD',
      'chosen': True,
      'fitted_scalars': 1,
      'new_tunable_constants': 0,
      'reason': 'DIRECT_TRAIN_TP_LOWER_BOUND_USING_EXACT_NONARBITRARY_V1_TRAIN_REFERENCE',
      'dev_calibration_correction': False,
    },
    'B': {
      'family': 'PREVALENCE_CONSTRAINED_FIXED_THRESHOLD',
      'chosen': False,
      'fitted_scalars': 1,
      'new_tunable_constants': 0,
      'reason': 'PREDICTED_COUNT_CAN_BE_ALL_FALSE_POSITIVES_DOES_NOT_BOUND_TRUE_MOVE_RECALL',
    },
    'C': {
      'family': 'CAUSAL_TWO_STATE_HYSTERESIS_GATE',
      'chosen': False,
      'review_eligible': temporal['persistence_state'] == 'TEMPORAL_MOVE_PERSISTENCE_PRESENT_BOTH_ROUTES',
      'reason': 'PERSISTENCE_DOES_NOT_PREVENT_CLOSED_ENTRY; TWO_THRESHOLDS_STATE_RESET_AND_RECURSIVE_FEEDBACK_EXCEED_A',
    },
    'D': {
      'family': 'CAUSAL_RANK_ADAPTIVE_GATE',
      'chosen': False,
      'reason': 'BOUNDED_WINDOW_INITIALIZATION_UPDATE_AND_TIE_RULES_ADD_UNJUSTIFIED_FREE_PARAMETERS',
    },
    'E': {
      'family': 'STAGE1_CLASSIFIER_V3',
      'chosen': False,
      'reason': 'PREDECLARED_RANK_COLLAPSE_CONDITION_NOT_MET_DECISION_ONLY_OPTION_STRUCTURALLY_AVAILABLE',
    },
  }
  bodies = {
    'design-options': {'options': options, 'v3_empirical_option_search': 'NOT_RUN'},
    'design-selection-rule': {
      'ordered_criteria': ORDER,
      'no_weighted_score': True,
      'criterion_3_scope': 'TRAIN_RETURN_OR_FAIL_GUARANTEE_NOT_UNIVERSAL_DEV_GUARANTEE',
      'criterion_5_scope': 'ADDRESS_DECISION_OBJECTIVE_TP_SACRIFICE_NO_CALIBRATION_CORRECTION',
      'causal_deployable_meaning': 'FUTURE_FREE_INFERENCE_INTERFACE_NOT_VEHICLE_QUALIFICATION',
    },
    'design-decision': {
      'selected_option': 'A',
      'reason': 'FIRST_DISTINGUISHING_CRITERION_3_DIRECT_TRUE_MOVE_TP_BOUND',
      'a_vs_b_parameters': 'EQUAL_ONE_THRESHOLD_ZERO_NEW_TUNABLE_SCALARS',
      'c_persistence_not_performance': True,
      'architecture_review': 'APPROVED_WITH_TRAIN_ONLY_GUARANTEE_AND_RESIDUAL_TRANSFER_RISK',
      'temporal_trigger_sha256': temporal['receipt_sha256'],
    },
    'design-evidence': {
      'public_inputs': pins,
      'temporal_trigger_sha256': temporal['receipt_sha256'],
      'evidence_role': 'DESIGN_RATIONALE_ONLY_NOT_NUMERICAL_V3_THRESHOLD_INPUT',
      'stage2_caveat': 'STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS',
    },
    'policy': {
      'status': POLICY + '_DESIGN_FROZEN',
      'selected_option': 'A',
      'decision': 'MOVE_IFF_P_MOVE_STRICTLY_GREATER_THAN_THRESHOLD',
      'all_static_prevention': 'POSITIVE_SOURCE_TP_FLOOR_ON_TRAIN_OR_FAIL',
      'all_move_prevention': 'NOT_GUARANTEED_NO_NEW_CONSTRAINT',
      'stage1': 'UNCHANGED',
      'stage2': 'UNCHANGED',
      'features': 'UNCHANGED',
      'structures': list(io.CANDIDATES),
      'route_folds': 'UNCHANGED',
      'interpretation': 'RETROSPECTIVE_DECISION_POLICY_DESIGN_NO_PERFORMANCE_CLAIM',
    },
    'feature-input-contract': {
      'inference_inputs': ['IMMUTABLE_V1_STAGE1_P_MOVE', 'FOLD_LOCAL_FROZEN_V3_THRESHOLD'],
      'threshold_training_inputs': [
        'TRAIN_CURRENT_TICK',
        'TRAIN_TARGET_TICK',
        'TRAIN_ACTUAL_DELTA',
        'TRAIN_P_MOVE',
        'IMMUTABLE_STAGE2_ALL_TRAIN_DELTA',
        'EXACT_V1_TRAIN_TP_REFERENCE',
      ],
      'rate_dependency': 'NONE',
      'new_features': [],
      'true_label_inference_branch': False,
    },
    'state-contract': {
      'state': 'STATELESS_FIXED_THRESHOLD',
      'initialization': 'LOAD_VERIFIED_FOLD_LOCAL_PARAMETER_AFTER_TRAIN_FINALIZATION',
      'reset': 'NO_DYNAMIC_GATE_STATE_TO_CARRY; ROUTE_OR_FOLD_CHANGE_REQUIRES_MATCHING_MODEL_AND_PARAMETER_LINEAGE',
      'history_reset': 'UNCHANGED_V1_SEGMENT_RUN_ELIGIBLE_STREAK_BOUNDARIES_NO_PADDING',
    },
    'causality-contract': {
      'timing': 'FEATURES_THROUGH_K_PREDICT_DELTA_K_TO_K_PLUS_1',
      'rollout_state': 'PROJECTED_INTEGER_TICK_AND_PROJECTED_DELTA_HISTORY',
      'future_exogenous': ['LOGGED_COMMAND', 'VEGO'],
      'future_truth': 'SCORING_ONLY',
      'development_access': 'AFTER_IMMUTABLE_TRAIN_PARAMETER_FINALIZATION',
      'holdout_access': 'FORBIDDEN',
    },
    'parameter-contract': {
      'fitted_parameter': 'ONE_PRIVATE_THRESHOLD_PER_CANDIDATE_FOLD',
      'count': 32,
      'candidate_set': 'SORTED_UNIQUE_UNION_0_1_FINITE_TRAIN_P_MOVE',
      'decision_operator': '>',
      'static_operator': '<=',
      'reference_parameter': 'IMMUTABLE_V1_TRAIN_TP_INTEGER_NOT_TUNED',
      'new_tunable_hyperparameters': [],
      'window': 'NONE',
      'hysteresis_gap': 'NONE',
      'debounce': 'NONE',
      'probability_transform': 'NONE',
      'actual_parameters': 'NOT_COMPUTED',
    },
    'training-policy': training,
    'fitting-policy': {
      'status': POLICY + '_FITTING_POLICY_FROZEN',
      'training_contract': training,
      'stage1_refit': 'FORBIDDEN',
      'stage2_refit': 'FORBIDDEN',
      'normalizer_refit': 'FORBIDDEN',
      'warm_start': 'NOT_APPLICABLE',
    },
    'acceptance-binding': {
      'gate': 'UNCHANGED_V1_32_CLAUSES_PER_FOLD',
      'gate_sha256': receipt('acceptance-gate-v1'),
      'selection_sha256': receipt('selection-rule-v1'),
      'candidate_sha256': receipt('candidate-set-v1'),
      'route_sha256': receipt('route-cv-contract-v1'),
      'comparator_sha256': receipt('comparator-contract-v1'),
      'both_folds_required': True,
      'epsilon': 0,
      'pooling_rescue': False,
      'early_performance_stop': False,
      'selection_order': [
        'WORST_PATH_MOVED_ROLLOUT_RMSE_RATIO',
        'WORST_OVERALL_ROLLOUT_RMSE_RATIO',
        'WORST_INTEGRATED_ONE_STEP_P95_RATIO',
        'TOTAL_NOMINAL_PARAMETER_COUNT',
        'L',
        'd',
        'candidate_id',
      ],
    },
    'future-execution-requirements': {
      'next_increment': POLICY + '_RETROSPECTIVE_EXECUTION',
      'status': 'REQUIRES_SEPARATE_AUTHORIZATION',
      'before_numeric_open': [
        'EXACT_CURRENT_HEAD',
        'EXACT_DESIGN_FITTING_EXECUTION_RECEIPTS',
        'EXACT_V1_SUCCESSFUL_SOURCE_ROOT',
        'SOURCE_MANIFEST_MODEL_NORMALIZER_AND_ANCHOR_SHA',
        'D_OUTPUT_IDENTITY',
        'FREE_SPACE_PREFLIGHT',
        'EXECUTOR_SHA',
        'PYTHON_NUMPY_BLAS_IDENTITY',
        'NO_REFIT_FIREWALL',
      ],
      'implementation_remaining': [
        'AUTHORIZED_PRIVATE_ORCHESTRATOR_NOT_IMPLEMENTED',
        'BOUNDED_EXACT_SWEEP_MUST_MATCH_CANONICAL_REFERENCE',
        'SOURCE_AVAILABILITY_AND_CAPACITY_CHECK_ONLY_WITH_FUTURE_AUTHORIZATION',
      ],
      'unfrozen_architecture_parameters': [],
      'actual_v3_performance': 'NOT_RUN',
    },
    'model-reuse-contract': {
      'v1_manifest_sha256': io.SOURCE_SHA,
      'stage1': 'BYTE_IDENTICAL',
      'stage2': 'BYTE_IDENTICAL',
      'normalizers': 'BYTE_IDENTICAL_SEPARATE_V1_STAGE_NORMALIZERS',
      'fit_calls': 0,
      'required_identity': ['MODEL_RECEIPT', 'COEFFICIENT_CONTENT', 'NORMALIZER_RECEIPT', 'NORMALIZER_CONTENT'],
      'mismatch': 'V3_MODEL_IDENTITY_CONFLICT',
    },
    'data-lineage': {
      'source': 'FINAL_SUCCESSFUL_V1_MANIFEST_ONLY',
      'v1_manifest_sha256': io.SOURCE_SHA,
      'stage1_train': 'PREDICTION_ONLY_REPLAY_BYTE_COMPARE_SAVED_V1_TRAIN_P_MOVE_IF_PRESENT',
      'stage2_train': 'ALL_CANDIDATE_SPECIFIC_TRAIN_ANCHORS_IMMUTABLE_MOVE_ONLY_NORMALIZER',
      'anchors': 'TRAIN_DEV_AND_EACH_ROLLOUT_HORIZON_EXACT_V1_SHA_COUNT_ORDER_NO_ROW_DRIFT',
      'reference_tp': 'EXACT_V1_TRAIN_CONFUSION_PUBLIC_RECEIPT_CROSSCHECK_PRIVATE_SUCCESSFUL_RECEIPT',
      'raw_qlog_rebuild': 'FORBIDDEN',
      'v1_threshold': 'COMPARISON_ONLY_AFTER_V3_FINALIZATION_NEVER_PARAMETER_SELECTION',
    },
    'execution-policy': {
      'status': POLICY + '_EXECUTION_POLICY_FROZEN',
      'job_order': [list(j) for j in io.JOBS],
      'environment': {
        'python': '3.12.13',
        'numpy': '2.5.3',
        'OPENBLAS_NUM_THREADS': 1,
        'OMP_NUM_THREADS': 1,
        'RNG': 'NONE',
        'blas_sha256': '704bde2afe24c22d171cc7d2508517db81b7db455743b2cb0e5de9dda88da7a2',
      },
      'sequence': [
        'VERIFY_AUTHORIZATION_AND_IDENTITIES',
        'TRAIN_REPLAY',
        'TRAIN_PARAMETER_FINALIZATION',
        'DEVELOPMENT',
        'ROLLOUT',
        'FROZEN_GATE',
        'FROZEN_SELECTION',
      ],
      'all_32_accounted': True,
      'no_feasible': 'FOLD_FAIL_CONTINUE_OTHER_JOBS',
      'identity_conflict': 'WHOLE_EXECUTION_INVALID',
      'development': 'SAME_V1_MODELS_ANCHORS_NEW_V3_GATE',
      'rollout': 'UNCHANGED_LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT',
      'horizons': [25, 50, 100, 200],
      'no_pooled_refit': True,
      'comparison': 'V1_V2_V3_REPORT_ONLY_AFTER_V3_FINALIZATION',
    },
    'storage-contract': {
      'volume': 'D_ONLY_VERIFY_BACKING_VOLUME',
      'source': 'READ_ONLY',
      'overwrite': 'FORBIDDEN',
      'no_symlinks_traversal_overlap': True,
      'capacity': 'RUN1_PLUS_RUN2_PLUS_ATOMIC_PEAK_PLUS_MANIFESTS_PLUS_DECLARED_RESERVE_BEFORE_OPEN',
      'compression': {'format': 'C_ORDER_NPY_GZIP', 'level': 1, 'mtime': 0, 'filename': ''},
      'hashes': ['COMPRESSED_FILE_SHA256', 'DECODED_NPY_SHA256', 'ARRAY_CONTENT_SHA256', 'DTYPE', 'SHAPE', 'C_ORDER'],
      'no_duplicate': ['V1_MODELS', 'V1_NORMALIZERS', 'TRUTH', 'HOLD_LAST', 'EXOGENOUS'],
      'references': ['SOURCE_MANIFEST', 'RELATIVE_MEMBER', 'RECEIPT_SHA', 'CONTENT_SHA'],
      'v3_payload': [
        'PRIVATE_THRESHOLD',
        'TRAIN_GATE_PROJECTED_TICK',
        'TRAIN_PROBABILITY_AND_STAGE2_PREDICTION_HASH',
        'DEV_PROBABILITY_GATE_PREDICTION_ERRORS',
        'ROLLOUT_PROJECTED_PATH_GATE_PATH_ENDPOINT_ERRORS',
      ],
      'commit_order': ['ATOMIC_MEMBERS', 'RECEIPT_LAST', 'JOB_MANIFEST_LAST', 'RUN_MANIFEST_LAST'],
      'public': 'AGGREGATES_AND_OPAQUE_HASHES_ONLY_NO_PRIVATE_THRESHOLD_COEFFICIENT_NORMALIZER_ROW_OR_PATH_VALUES',
    },
    'repeatability-contract': {
      'runs': 2,
      'independent': True,
      'run1_cache_reuse_in_run2': False,
      'equality': 'BYTE_EXACT',
      'scope': [
        'INPUT_MODELS',
        'ANCHORS',
        'TRAIN_REPLAY',
        'REFERENCE_TP',
        'THRESHOLD',
        'OBJECTIVE',
        'DEV',
        'ROLLOUT',
        'GATES',
        'SELECTION',
        'LOGICAL_MANIFESTS',
      ],
      'failure': 'V3_REPEATABILITY_FAILURE_SELECTED_NULL_KEEP_SCRATCH',
      'run2_cleanup': 'ONLY_AFTER_COMPLETE_BYTE_EQUALITY_AND_DURABLE_RUN2_MANIFEST_RECEIPT_COMPARISON_THRESHOLD_AND_RESULT_IDENTITIES',
    },
    'resume-contract': {
      'strategy': 'VERIFY_PERSISTED_STORE_ONLY',
      'trapped': ['MODEL_LOADER', 'SOURCE_LOADER', 'PREDICTOR', 'PARAMETER_SELECTOR', 'DEVELOPMENT', 'ROLLOUT', 'SCORER', 'SELECTOR'],
      'compute_calls': 0,
      'same_manifest_readiness': True,
    },
    'design-readiness': {
      'status': POLICY + '_DESIGN_FROZEN',
      'stage1_model': 'UNCHANGED',
      'stage2_model': 'UNCHANGED',
      'structures': '16_UNCHANGED',
      'features': 'UNCHANGED',
      'route_folds': 'UNCHANGED',
      'acceptance': 'UNCHANGED',
      'selection': 'UNCHANGED',
      'actual_v3_threshold': 'NOT_COMPUTED',
      'performance': 'NOT_RUN',
    },
    'execution-readiness': {
      'status': POLICY + '_EXECUTION_POLICY_FROZEN',
      'scaffold': 'SYNTHETIC_ONLY_SCAFFOLD_READY',
      'actual_private_executor': 'NOT_IMPLEMENTED_FUTURE_AUTHORIZATION_REQUIRED',
      'execution_states': dict.fromkeys(
        ('V3_PRIVATE_EXECUTION', 'V3_THRESHOLD_OR_STATE_PARAMETER_SELECTION', 'V3_DEVELOPMENT', 'V3_ROLLOUT', 'V3_MODEL_SELECTION'), 'NOT_RUN'
      ),
    },
  }
  return {filename(k): p.seal({**common, **value}) for k, value in bodies.items()}


def validate(bundle):
  if bundle != build():
    raise ValueError('V3_POLICY_CONFLICT')
  for row in bundle.values():
    p.verify(row)
  return bundle


def publish():
  bundle = build()
  validate(bundle)
  for name, row in bundle.items():
    p.persist(p.PUBLIC / name, row)
  return bundle


if __name__ == '__main__':
  publish()
