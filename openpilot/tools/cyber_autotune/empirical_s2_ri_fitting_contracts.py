"""Declarative future S2-RI execution contracts. No data or model executor."""
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

OFFSETS = (0, 5, 10, 20)
HISTORIES = (1, 5, 15, 45)
PRIMARY = 'SCOPE_ALL_ACTIVE_NO_OVERRIDE'
DIAGNOSTIC = 'SCOPE_NON_RAIL_ACTIVE_NO_OVERRIDE'
AUTHORITY = dict.fromkeys((
  'private_array_access', 'raw_opening', 'fitting', 'normalizer_fitting', 'prediction', 'residual',
  'metric_execution', 'cv_scoring', 'selection', 'rollout', 'pooled_refit', 'qlog_support',
  'holdout_opening', 'candidate_execution', 'ta', 'sg', 'composition', 'production', 'device', 'vehicle'), False)


def sealed(schema, **body):
  return p.seal({'schema': schema, **body, 'authority': dict(AUTHORITY)})


def definitions(inputs):
  """Return sealed declarations only; arguments are verified public receipts."""
  def old(name):
    return inputs['empirical-s2-ri-'+name+'-v1.json']['receipt_sha256']

  layouts = {}
  for d in OFFSETS:
    for length in HISTORIES:
      cid = f'S2RI_D{d:02d}_L{length:02d}'
      columns = ['intercept']
      columns += [f'command_k_minus_{i}' for i in range(d+length-1, d-1, -1)]
      columns += [f'delta_k_minus_{j}' for j in range(length, 0, -1)]
      columns += ['angle_tick_k', 'speed_mps_k']
      layouts[cid] = {'columns': columns, 'parameter_count': 2*length+3,
        'required_prior_intervals': max(d+length-1, length),
        'history_rows_including_current': max(d+length, length+1),
        'column_order_sha256': p.sha(p.canonical(columns))}
  feature = sealed('EMPIRICAL_S2_RI_FITTING_FEATURE_CONTRACT_V1',
    family='S2_RI_V1', signal_contract_sha256=old('signal-contract'),
    history_contract_sha256=old('history-reset'), target_contract_sha256=old('target-contract'),
    causal_identity_sha256=old('causal-identity'), row_admission_sha256=old('row-admission'),
    order=['intercept', 'command_oldest_to_newest', 'delta_oldest_to_newest', 'angle_tick_k', 'speed_mps_k'],
    layouts=layouts, command='u[k-d-L+1..k-d]', past_increment='delta[k-L..k-1]',
    delta_definition='delta[j]=tick[j+1]-tick[j]', target='tick[k+1]-tick[k]',
    current_angle_unit='INTEGER_SOURCE_TICKS', speed_unit='M_PER_S', command_unit='NORMALIZED_LOGGED_COMMAND',
    historical_column_relation='EXPLICIT_WITHIN_HISTORY_PERMUTATION_NEWEST_FIRST_TO_OLDEST_FIRST_SAME_FEATURE_SET',
    historical_generic_causal_identity='RATE_DEPENDENT_IMMUTABLE_REFERENCE_ONLY',
    s2_ri_causal_identity='RATE_FREE_FAMILY_SPECIFIC_IDENTITY',
    history='SAME_ROUTE_RLOG_SEGMENT_S2_RI_RUN_AND_ELIGIBLE_STREAK_EXACT_10_MS_NO_PADDING',
    steering_rate_dependency='NONE', controller_request_dependency='NONE',
    raw_command='BRIDGE_PROVENANCE_ONLY_NOT_SECOND_FEATURE',
    mask_fields='CONTEXT_ONLY_NOT_FEATURE_COLUMNS',
    forbidden_features=['steeringRateDeg', 'controller_request', 'request_output_difference', 'raw_torqueOutputCan',
      'driver_torque', 'steeringPressed', 'EPS_faults', 'speed_bin_one_hot', 'command_times_speed', 'angle_polynomial',
      'future_command', 'future_angle', 'gyro', 'yaw', 'modelV2', 'planner', 'path', 'lane', 'qlog'],
    primary_scope=PRIMARY, diagnostic_scope=DIAGNOSTIC,
    diagnostic_scope_use='REPORT_ONLY_NEVER_ADMISSION_RANKING_SELECTION',
    reset='NO_INACTIVE_OVERRIDE_FAULT_GAP_REENGAGEMENT_OR_BOUNDARY_HISTORY_CARRY',
    source_age_max_ns=20_000_000, minimum_speed_mps=5.0, gear='drive',
    physical_eps='PHYSICAL_EPS_APPLICATION_UNAVAILABLE',
    command_offset_semantics='EMPIRICAL_COMMAND_HISTORY_OFFSET_NOT_PHYSICAL_EPS_DELAY',
    request_output_transaction='REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE')

  grid = sealed('EMPIRICAL_S2_RI_FITTING_GRID_CONTRACT_V1',
    historical_angle_grid_sha256=old('angle-grid'),
    historical_emission_policy_sha256=inputs['empirical-s2-ri-angle-grid-v1.json']['historical_emission_policy_sha256'],
    historical_verdict='SOURCE_GRID_OBSERVATION_REJECTED',
    amendment='USER_APPROVED_ADDITIVE_DIRECT_TICK_PROJECTION_HISTORICAL_DEGREE_ROUNDTRIP_UNCHANGED',
    bitwise_equivalent_to_historical_degree_roundtrip=False,
    input_coordinate='BINARY64_NEXT_ANGLE_TICKS', operation='DIRECT_ROUND_HALF_TO_EVEN_TO_INTEGER_TICK',
    tie_semantics='EXACT_BINARY64_HALF_NO_EPSILON', code_range=[-32768, 32767],
    range_check='FINITE_INPUT_AND_PROJECTED_INTEGER_IN_SIGNED16_RANGE',
    range_failure='CANDIDATE_FOLD_NUMERICAL_FAILURE_NO_CLIPPING_NO_ANCHOR_DROP',
    degree_display='FLOAT32_FLOAT64_INTEGER_TICK_TIMES_FLOAT64_POINT_ONE',
    primary_evaluation_coordinate='TICKS_NOT_FLOAT32_DEGREE_DISPLAY',
    recursive_state='PROJECTED_INTEGER_TICK', projection_calls_executed=0,
    synthetic_contract_counterexample={'input_tick': 14.5, 'direct_tick': 14, 'historical_roundtrip_tick': 15},
    physical_sensor_output_claim=False)

  normalizer = sealed('EMPIRICAL_S2_RI_NORMALIZATION_CONTRACT_V1',
    route_cv_sha256=old('route-cv-contract'), population='CANDIDATE_SPECIFIC_TRAIN_DESIGN_ANCHORS_ONLY',
    primary_scope=PRIMARY, dtype='float64', mean='TRAIN_POPULATION_MEAN_AXIS_0',
    std='TRAIN_POPULATION_STD_DDOF_0_AXIS_0', formula='(x-train_mean)/train_std',
    intercept='EXACT_ONE_UNSCALED', constant_detection='EXACT_TRAIN_STD_EQUALS_ZERO',
    constant='FROZEN_TRAIN_ZERO_COLUMN', development_constant_drift='DEVELOPMENT_CONSTANT_DRIFT_REPORT_ONLY',
    development_transform='APPLY_FROZEN_TRAIN_STATS_AND_CONSTANT_MASK_NO_REFIT',
    forbidden_statistics=['DEVELOPMENT', 'POOLED_TRAIN_DEVELOPMENT', 'HOLDOUT'],
    target_normalization='NONE', normalizer_fitting='NOT_RUN',
    finite_precondition='ALL_TRAIN_INPUTS_AND_STATS_FINITE_NO_EPSILON_SCALE_FLOOR',
    row_order='ROUTE_ID_THEN_SOURCE_SEGMENT_CONTENT_SHA256_THEN_ALIGNED_ROW_INDEX_ASCENDING',
    column_order='EXACT_FEATURE_LAYOUT',
    constant_solver_columns='DROP_TRAIN_CONSTANT_NONINTERCEPT_COLUMNS_BEFORE_RANK_AND_SOLVE',
    nominal_coefficient_mapping='CONSTANT_COLUMNS_FIXED_ZERO_BY_SCHEMA_NOT_POSTFIT_CLIPPING')

  method = sealed('EMPIRICAL_S2_RI_FIT_METHOD_V1',
    algorithm='DETERMINISTIC_FLOAT64_ORDINARY_LEAST_SQUARES', solver='numpy.linalg.lstsq',
    numpy_version='2.5.3', dtype='float64', rcond=None,
    rcond_semantics='FLOAT64_MACHINE_EPSILON_TIMES_MAX_M_N_OF_EFFECTIVE_STANDARDIZED_TRAIN_X',
    rcond_documentation='PINNED_NUMPY_2_5_3_NUMPY_LINALG_LSTSQ_DOCSTRING_DEFAULT_SINCE_2_0',
    required_environment={'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'},
    rng=False, regularization='NONE', normalizer_sha256=normalizer['receipt_sha256'],
    effective_rank='NONCONSTANT_TRAIN_COLUMNS_PLUS_UNSCALED_INTERCEPT',
    rank_method='NUMPY_MATRIX_RANK_SVD_DEFAULT_TOL_SMAX_TIMES_MAX_M_N_TIMES_FLOAT64_EPS',
    rank_gate='RANK_EQUALS_EFFECTIVE_COLUMN_COUNT',
    rank_failure='FIT_PRECONDITION_RANK_FAILURE_NO_SOLVE',
    solver_rank_recheck='RETURNED_LSTSQ_RANK_MUST_EQUAL_EFFECTIVE_COLUMN_COUNT_ELSE_INVALID_FOLD',
    conditioning='REPORT_ONLY_NO_ACCEPTANCE_THRESHOLD',
    unsupported_constant_or_nonfinite_scale='FIT_PRECONDITION_FAILURE_NO_RESCALING_WORKAROUND',
    forbidden=['RIDGE', 'LASSO', 'ELASTIC_NET', 'BAYESIAN_PRIOR', 'EARLY_STOPPING', 'GRADIENT_DESCENT',
      'OPTIMIZER', 'POSTFIT_PARAMETER_CLIPPING', 'SPARSIFICATION', 'RCOND_RETRY', 'PSEUDOINVERSE_FALLBACK'],
    coefficients='NOT_GENERATED', solver_calls=0,
    parameter_interpretation='EMPIRICAL_PREDICTIVE_PARAMETERS',
    closed_loop_bias='CLOSED_LOOP_IDENTIFICATION_BIAS_RISK')

  rollout = sealed('EMPIRICAL_S2_RI_ROLLOUT_CONTRACT_V1',
    feature_sha256=feature['receipt_sha256'], grid_policy_sha256=grid['receipt_sha256'],
    normalizer_sha256=normalizer['receipt_sha256'],
    name='LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT',
    dt_ns=10_000_000, horizons=[{'seconds': s, 'steps': h} for s, h in ((.25, 25), (.5, 50), (1., 100), (2., 200))],
    anchor='k_LAST_OBSERVED_ANGLE', first_step='FEATURES_AT_k_PREDICT_k_PLUS_1',
    endpoint='H_UPDATES_COMPARE_PROJECTED_TICK_AT_k_PLUS_H_TO_OBSERVED_TICK_AT_k_PLUS_H',
    initial_history='OBSERVED_ANGLE_TICKS_AND_PAST_DELTAS_THROUGH_k_ONLY',
    recursive_state='PROJECTED_SOURCE_GRID',
    transition_order=['BUILD_CAUSAL_FEATURES_AT_k_PLUS_h_MINUS_1',
      'APPLY_FROZEN_TRAIN_NORMALIZER', 'DECLARE_CONTINUOUS_DELTA_FROM_FROZEN_MODEL',
      'ADD_DELTA_TO_CURRENT_PROJECTED_TICK', 'DIRECT_TICK_HALF_TO_EVEN_PROJECTION',
      'APPEND_PROJECTED_TICK_DIFFERENCE_TO_DELTA_HISTORY', 'ADVANCE_ONE_GRID_STEP'],
    past_delta_update='PROJECTED_TICK_NEW_MINUS_PROJECTED_TICK_PREVIOUS',
    exogenous=['RECORDED_LOGGED_POST_CARCONTROLLER_NORMALIZED_COMMAND', 'RECORDED_VEGO'],
    command_index='u[k+h-1-d-i]_FOR_i_0_TO_L_MINUS_1',
    speed_index='vEgo[k+h-1]', exogenous_semantics='LOGGED_SEQUENCE_CONDITIONING_NOT_AUTONOMOUS_FUTURE_DRIVING',
    measured_future_angle='SCORING_ONLY_NEVER_RECURSIVE_FEATURE',
    measured_future_delta='FORBIDDEN', steering_rate='FORBIDDEN',
    continuous_feedback='FORBIDDEN', future_input_bound='COMMAND_AND_SPEED_SOURCE_TIME_AT_OR_BEFORE_EACH_RECORDED_STEP_STATE',
    support='EVERY_HISTORY_AND_HORIZON_ROW_SAME_ROUTE_SEGMENT_S2_RI_RUN_ELIGIBLE_EXACT_100HZ',
    start_after_reset='REBUILD_ALL_REQUIRED_HISTORY_NO_CARRY',
    boundary='ANCHOR_HORIZON_UNAVAILABLE_BEFORE_PREDICTION_NO_SHORT_PADDING',
    numerical_failure='INVALIDATE_CANDIDATE_FOLD_NO_CLIPPING_NO_SAMPLE_REMOVAL',
    state_ownership='INDEPENDENT_CANDIDATE_FOLD_ANCHOR_NO_CROSS_ANCHOR_STATE',
    execution='NOT_RUN')

  comparator = sealed('EMPIRICAL_S2_RI_COMPARATOR_CONTRACT_V1',
    name='HOLD_LAST_ANGLE', one_step='PREDICTED_NEXT_TICK_EQUALS_OBSERVED_TICK_k',
    one_step_delta='ZERO_INCREMENT',
    rollout='INITIAL_OBSERVED_TICK_k_CONSTANT_FOR_ALL_H_STEPS',
    anchors='EXACT_CANDIDATE_SPECIFIC_ELIGIBLE_ANCHOR_SET_FOR_EACH_FOLD_AND_HORIZON',
    support_identity='ORDERED_ROUTE_SEGMENT_ALIGNED_ANCHOR_INDEX_SET_SHA256_EQUAL',
    no_arm_specific_dropping=True, historical_ARX_FIR='NOT_AUTOMATIC_COMPARATOR',
    execution='NOT_RUN')

  metrics = sealed('EMPIRICAL_S2_RI_FITTING_METRIC_CONTRACT_V1',
    historical_metric_sha256=old('future-metric-contract'), comparator_sha256=comparator['receipt_sha256'],
    population='DEVELOPMENT_ROUTE_CANDIDATE_SPECIFIC_ELIGIBLE_ANCHORS',
    primary_scope=PRIMARY, diagnostic_scope='NON_RAIL_REPORT_ONLY',
    coordinate='FLOAT64_SOURCE_GRID_TICKS', delta_error='CONTINUOUS_DELTA_MINUS_FLOAT64_OBSERVED_DELTA_TICK',
    continuous_next_angle_error='EXACT_SAME_CANONICAL_ERROR_BUFFER_AS_DELTA_ERROR',
    equality='ALGEBRAIC_IDENTITY_NEXT_ANGLE_MINUS_TARGET_EQUALS_DELTA_ERROR_CANONICAL_SHARED_BUFFER',
    duplicated_metrics='ONE_STEP_DELTA_AND_NEXT_ANGLE_CONTINUOUS_ARE_EXPLICIT_ALIASES_NOT_INDEPENDENT_EVIDENCE',
    rmse='SQRT_FLOAT64_MEAN_SQUARED_ERROR', mae='FLOAT64_MEAN_ABSOLUTE_ERROR',
    p95='NUMPY_PERCENTILE_ABS_ERROR_95_METHOD_LINEAR',
    reduction_order='SOURCE_SEGMENT_CONTENT_SHA256_THEN_ALIGNED_ANCHOR_INDEX_ASCENDING_FIXED_CONTIGUOUS_FLOAT64_ARRAY',
    bias='NOT_AN_ADMISSION_OR_RANKING_METRIC',
    one_step=['RMSE', 'MAE', 'P95_ABSOLUTE'],
    source_grid={'EXACT_NEXT_ANGLE_HIT_RATE': 'COUNT_PROJECTED_INTEGER_EQUALS_TARGET_INTEGER_DIVIDE_N',
      'WITHIN_ONE_TICK_RATE': 'COUNT_ABS_INTEGER_DIFFERENCE_LE_1_DIVIDE_N'},
    rollout_metrics=['ANGLE_RMSE', 'ANGLE_MAE', 'ANGLE_P95_ABSOLUTE'],
    rollout_population='ENDPOINT_k_PLUS_H_ERRORS_ACROSS_ANCHORS_NOT_ALL_INTERMEDIATE_STEPS',
    optional_degree_display='CANONICAL_TICK_ERROR_TIMES_FLOAT64_POINT_ONE_SUPPORTING_ONLY',
    minimum_development_anchors_per_fold_and_horizon=201,
    minimum_support_origin='EXISTING_S2_RI_ROUTE_CV_MINIMUM_NOT_NEW_ACCEPTANCE_THRESHOLD',
    support='REPORT_COUNT_AND_ORDERED_ANCHOR_SHA_FOR_EACH_ARM_CANDIDATE_FOLD_HORIZON',
    insufficient_support='CANDIDATE_FOLD_INSUFFICIENT_SUPPORT_NOT_ADMISSIBLE',
    nonfinite='CANDIDATE_FOLD_NUMERICAL_FAILURE_NOT_DROP_OR_IGNORE',
    aggregation='FOLD_SPECIFIC_THEN_EQUAL_ROUTE_PRIMARY_SAMPLE_WEIGHTED_SUPPORTING_ONLY',
    cross_candidate_support='MAY_DIFFER_PREDECLARED_HISTORY_POPULATIONS_REPORT_COUNTS_NEVER_HIDE',
    metric_values='NOT_COMPUTED')

  gate = sealed('EMPIRICAL_S2_RI_ACCEPTANCE_GATE_V1',
    metric_sha256=metrics['receipt_sha256'], primary_scope=PRIMARY,
    folds=['FOLD_A', 'FOLD_B'], fold_quantifier='ALL', epsilon=None,
    prerequisites=['EXACT_HISTORY_AND_SOURCE_ADMISSION', 'TRAIN_EFFECTIVE_RANK_FULL',
      'FINITE_COEFFICIENTS_AND_OUTPUTS_AND_METRICS', 'NO_SOURCE_GRID_RANGE_VIOLATION',
      'IDENTICAL_COMPARATOR_ANCHORS', 'DEVELOPMENT_SUPPORT_AT_LEAST_201_EACH_POPULATION'],
    one_step_next_angle={'RMSE': '<', 'MAE': '<=', 'P95_ABSOLUTE': '<='},
    rollout_horizons_steps=[25, 50, 100, 200], horizon_quantifier='ALL',
    rollout={'ANGLE_RMSE': '<=', 'ANGLE_MAE': '<=', 'ANGLE_P95_ABSOLUTE': '<='},
    source_grid={'EXACT_NEXT_ANGLE_HIT_RATE': '>=', 'WITHIN_ONE_TICK_RATE': '>='},
    comparison='CANDIDATE_OPERATOR_HOLD_LAST_FINITE_COMPUTED_METRIC',
    strict_improvement='ONE_STEP_NEXT_ANGLE_RMSE_EACH_FOLD',
    all_ties='REJECT', non_rail_use='FORBIDDEN', pooled_gate='FORBIDDEN',
    admissible_state='S2_RI_CV_ADMISSIBLE', gate_execution='NOT_RUN')

  selection = sealed('EMPIRICAL_S2_RI_SELECTION_RULE_V1',
    admission_gate_sha256=gate['receipt_sha256'], input_set='ONLY_CANDIDATES_PASSING_BOTH_FOLDS_ALL_GATES',
    direction='LEXICOGRAPHIC_ASCENDING',
    keys=['WORST_ROLLOUT_RMSE_RATIO', 'WORST_ONE_STEP_P95_RATIO', 'PARAMETER_COUNT', 'L', 'd', 'CANDIDATE_ID'],
    worst_rollout='MAX_CANDIDATE_RMSE_OVER_HOLD_LAST_RMSE_ACROSS_TWO_FOLDS_FOUR_HORIZONS',
    worst_one_step='MAX_CANDIDATE_NEXT_ANGLE_P95_OVER_HOLD_LAST_NEXT_ANGLE_P95_ACROSS_TWO_FOLDS',
    ratio={'positive_denominator': 'FLOAT64_NUMERATOR_DIVIDE_DENOMINATOR',
      'zero_over_zero': 1.0, 'positive_over_zero': 'POSITIVE_INFINITY',
      'negative_or_nonfinite_input': 'REJECT_METRIC', 'json_infinity': 'POSITIVE_INFINITY_SYMBOL_NOT_NONSTANDARD_JSON_NUMBER'},
    equal='EXACT_COMPUTED_FLOAT_EQUALITY_NO_EPSILON',
    zero={'status': 'S2_RI_NO_ADMISSIBLE_CANDIDATE', 'selection': 'MODEL_SELECTION_FAILED_CLOSED', 'selected_candidate': None,
      'next_action': 'SEPARATE_REDESIGN_AUTHORIZATION_NO_GATE_RELAXATION_OR_CANDIDATE_EXPANSION'},
    one={'status': 'S2_RI_SINGLE_ADMISSIBLE_CANDIDATE', 'action': 'SOLE_ADMISSIBLE_ID_RETROSPECTIVE_ONLY'},
    multiple={'status': 'S2_RI_RETROSPECTIVE_CV_SELECTED', 'action': 'LEXICOGRAPHIC_MIN_OF_FROZEN_KEYS'},
    execution='NOT_RUN', selected_candidate=None, independent_validation=False,
    selection_output='FUTURE_SELECTED_CONFIGURATION_PLUS_TWO_FOLD_MODEL_RECEIPTS_NOT_FINAL_MODEL',
    pooled_refit='FINAL_POOLED_REFIT_NOT_AUTHORIZED', holdout_model_admission=False,
    forbidden=['SUBJECTIVE_GRAPH_CHOICE', 'ONE_FOLD_OVERRIDE', 'LOCAL_SEARCH', 'CANDIDATE_ADDITION',
      'METRIC_CHANGE', 'GATE_RELAXATION', 'TIE_BREAK_CHANGE', 'NON_RAIL_RANKING'])

  return {'fitting-feature-contract': feature, 'fitting-grid-contract': grid, 'normalization-contract': normalizer,
    'fit-method': method, 'rollout-contract': rollout, 'comparator-contract': comparator,
    'fitting-metric-contract': metrics, 'acceptance-gate': gate, 'selection-rule': selection}


def candidate_set(contracts, inputs):
  c = contracts
  rows = []
  for d in OFFSETS:
    for length in HISTORIES:
      cid = f'S2RI_D{d:02d}_L{length:02d}'
      rows.append(sealed('EMPIRICAL_S2_RI_CANDIDATE_V1',
        candidate_id=cid, family='S2_RI_V1', d=d, L=length, Lu=length, Ldelta=length,
        parameter_count=2*length+3, primary_scope=PRIMARY,
        command_offset_ms=10*d, offset_semantics='EMPIRICAL_COMMAND_HISTORY_OFFSET_NOT_PHYSICAL_EPS_DELAY',
        feature_schema_sha256=c['fitting-feature-contract']['receipt_sha256'],
        column_order_sha256=c['fitting-feature-contract']['layouts'][cid]['column_order_sha256'],
        target_schema_sha256=inputs['empirical-s2-ri-target-contract-v1.json']['receipt_sha256'],
        grid_policy_sha256=c['fitting-grid-contract']['receipt_sha256'],
        route_cv_sha256=inputs['empirical-s2-ri-route-cv-contract-v1.json']['receipt_sha256'],
        fit_method_sha256=c['fit-method']['receipt_sha256'],
        normalizer_sha256=c['normalization-contract']['receipt_sha256'],
        metric_sha256=c['fitting-metric-contract']['receipt_sha256'],
        admission_gate_sha256=c['acceptance-gate']['receipt_sha256'],
        rollout_sha256=c['rollout-contract']['receipt_sha256']))
  return sealed('EMPIRICAL_S2_RI_CANDIDATE_SET_V1', status='S2_RI_FINITE_CANDIDATE_SET_FROZEN',
    count=16, candidates=rows, ordered_candidate_set_sha256=p.sha(p.canonical(rows)),
    execution_order=[{'candidate_id': r['candidate_id'], 'fold': f} for r in rows for f in ('FOLD_A', 'FOLD_B')],
    fold_jobs=32, complete_accounting='ALL_32_JOBS_RECEIPTED_INCLUDING_PRECONDITION_FAILURES_NO_PERFORMANCE_EARLY_STOP',
    configuration_expansion_allowed=False, candidate_selection='NOT_RUN')
