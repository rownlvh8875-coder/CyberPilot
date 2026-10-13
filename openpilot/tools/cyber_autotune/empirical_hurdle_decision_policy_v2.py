"""Additive public-only threshold-objective design. Contains no numerical executor."""

import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

BASELINE = '13e1ac7c8b892d3bd61b5e2eab9deba8f4dc08d6'
POLICY = 'HURDLE_STAGE1_DECISION_POLICY_V2'
READY = POLICY + '_DESIGN_FROZEN'
CONFLICT = POLICY + '_DESIGN_CONFLICT'
SOURCE_MANIFEST = 'c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6'
ATTRIBUTION_MANIFEST = '07345517d3bca95e90962e0566a58e2b756a8aa6f5c658b8b312f02d4961f77d'
PINS = {
  'empirical-hurdle-family-contract-v1.json': {
    'file_sha256': 'cccaba738cb55c2506269976d1cb86510a90ba2d20f41004493d05f1aeab1d41',
    'receipt_sha256': 'c780fa1e75bdb3d13480f4863b6dabb7c7dbfe68797032fce582b7854d45dfe3',
  },
  'empirical-hurdle-feature-contract-v1.json': {
    'file_sha256': '8676c89bcfe629d6bcc60706172ca29f79ee42430e67893c8ee837a7da672488',
    'receipt_sha256': '517288519b2ae0ef9edaa4b2a0c5e5a1b296389e4381ac4af0a2bddfec41be3a',
  },
  'empirical-hurdle-training-population-v1.json': {
    'file_sha256': 'e7646168c73759c63cc78de43b57936be062f29c54b2afca3c449431409b8a24',
    'receipt_sha256': '98b9296594b087df720b626389438c76072148c7a4d5709b11bca4df04507a0c',
  },
  'empirical-hurdle-composition-contract-v1.json': {
    'file_sha256': '9c0f48ffada6ce8e905d85d9d72df21a3997f9ce6dc757bb96d9291218046948',
    'receipt_sha256': '046d0ba328c7a52421aedfff504ed20ad27114785d67054f6e78fd8547eccc67',
  },
  'empirical-hurdle-rollout-contract-v1.json': {
    'file_sha256': '772d5febe8894c189c8332836365149467c0c5870bd630d0db1be7372ebc3d04',
    'receipt_sha256': 'ae1b447a4abdc3c5ba4c34adcfa4c650d3ee35b9229d899a8d6ff557ce09bb92',
  },
  'empirical-hurdle-fitting-policy-v1.json': {
    'file_sha256': 'e1b566d18a55cc72fe9378d37f0763d3a5de107cff2b6ff884cebcd238b376d6',
    'receipt_sha256': '3824973d9851ebfffbfd47e9f95b9f49580326b75f652e55c1ca21808d624104',
  },
  'empirical-hurdle-stage1-fit-method-v1.json': {
    'file_sha256': '5d6246624f7a3e49701f6db62185ed97ff5e2b34b99f59faca29c6f54636283f',
    'receipt_sha256': '6c644678deb454008c3a3146cece0a24393642e2025707dbacbe47e3355a7b9a',
  },
  'empirical-hurdle-stage1-convergence-v1.json': {
    'file_sha256': '4014c3bbd0d47ed53ee05bde279e9c72f7f9c20e07b2bd1291f6278246f78ba3',
    'receipt_sha256': '4a2c377be5379c1a03d65dbb9c06070619d60cedee3ab6d4af331aba8426a82a',
  },
  'empirical-hurdle-threshold-policy-v1.json': {
    'file_sha256': '563ccf3805c33fa5eb588d210106aaf089c441d1fc5e35ca503ef66463a7cbd1',
    'receipt_sha256': '56c8ce9eeba90be17d5ec4bd73ec604447dfcc9463dce7b38b8f6a1769706841',
  },
  'empirical-hurdle-stage2-fit-method-v1.json': {
    'file_sha256': '7757e2b582a914f1fe802b6db1a731871c15d07c9e746ede84a7a3a6da53daaf',
    'receipt_sha256': '31761a5961b755f3d0ca719bb88355b560c8b47e8b00df5f6f04e17ad8b986b4',
  },
  'empirical-hurdle-stage-normalization-v1.json': {
    'file_sha256': 'd0cd13c7afa4d35e55ee2e1d9316474cbdb50099d7674de0da8ff6fde46a1b26',
    'receipt_sha256': '4704b839037042084da818cc72eecd651b7a1d7ac12fa5d74f1531bb2517e549',
  },
  'empirical-hurdle-candidate-set-v1.json': {
    'file_sha256': '7c337dd1fee7ca7947513788e91c88fe32092aa8c808213ac13787681a494b2b',
    'receipt_sha256': 'eff4ff37f74e06520e917f017c509175733a108df9399ebab8f2e93fa6a871f4',
  },
  'empirical-hurdle-route-cv-contract-v1.json': {
    'file_sha256': 'a40183e88f0ae7b830d353cdce3a692f56111d31a5c27cd1394d205d77e5e6f8',
    'receipt_sha256': '9e6bddd4f4d0e3dbe1cd02d7cfe2313a17da5459215f4fa397d42b098b406a4a',
  },
  'empirical-hurdle-metric-contract-v1.json': {
    'file_sha256': '82f88fac1d31d3e4a24dfa717877cfd1d60da62bff4108b8d58cfbba7c446639',
    'receipt_sha256': '98df562961a9c60cd43531694cd0dfbbde19b528c856bf6562ea6d5c6aad17e5',
  },
  'empirical-hurdle-comparator-contract-v1.json': {
    'file_sha256': '5bc595c87a5a146256f6c36bc581fcd6fdb19dbedcef9de590dc9313191c9461',
    'receipt_sha256': '80561a7f863363fa5ce6ed6710e2c29cae58ff985f2597bb0761faf86e27cf00',
  },
  'empirical-hurdle-acceptance-gate-v1.json': {
    'file_sha256': '606d5d3f46677d0107298f8b94e0a6d5a73da62f01db0164c4812a9fa2cccee1',
    'receipt_sha256': '1a5198475b7a3843381762078475915a389b2898e950effc171a3df58219ca60',
  },
  'empirical-hurdle-selection-rule-v1.json': {
    'file_sha256': 'aeb3e51e85039660be702517dfd79e4c932eb72bde0b1a9d9bdc4bbaad36586c',
    'receipt_sha256': '9622e7134b56f0c48153cba1a23dd690bdc6d578a433c6f77b34e3f7a3cf70f0',
  },
  'empirical-hurdle-fitting-policy-readiness-v1.json': {
    'file_sha256': '9a0811e62916b6f3dbadc579ce6e3db64f888cd07e68474da1265e6efa984195',
    'receipt_sha256': 'cde321da593da445d5df34a7a2a9212555209c7d66b2979b7ef01987c230cefb',
  },
  'empirical-hurdle-fit-cv-readiness-v1.json': {
    'file_sha256': '8613634aa79641de3f2512ce06882393cfa9c1a5d2749043631fa757cbf56499',
    'receipt_sha256': 'e00c9da0992fed899e77f9833d0ad04f333acc086e59846644ec164945b06861',
  },
  'empirical-hurdle-selection-result-v1.json': {
    'file_sha256': '3e1d72ec6d114c03e289dac3a8406126f17d6594fc73ebcbb7b2302c32beed46',
    'receipt_sha256': 'cac341f353befbf014726df964009525484e938abc1b5a5dc6d5de4e5a7a6df8',
  },
  'empirical-hurdle-failure-attribution-readiness-v1.json': {
    'file_sha256': '095ac7f7a02cb7178d1d47087a70a03ff7919d99eced7f56a3c75027589046bc',
    'receipt_sha256': 'dd03dedbab42fa3e4cdf262234bb24f4a62fb94c4dbbd8d9f203d5ec6506b7c6',
  },
  'empirical-hurdle-next-design-trigger-v1.json': {
    'file_sha256': 'c12dc439d4c0d5550ca57dd0dbd4eb127f37d3d4f984a825edc700da9f3668af',
    'receipt_sha256': '00566fbfac6d05929a17202aa9c6d889454449c4a7e7e9274128d6f85b92b320',
  },
  'empirical-hurdle-mechanism-summary-v1.json': {
    'file_sha256': 'eec5066f40a17818bb9e3da1ff7bd2bf40d8dd2711f35618956eedd20949911c',
    'receipt_sha256': '2d3d1763010ba6144e2318cd8b1377374c3bb22e101dbee6a381806e20294ca9',
  },
}

LABELS = {
  'evidence': 'stage1-decision-policy-v2-design-evidence',
  'policy': 'stage1-decision-policy-v2',
  'candidates': 'stage1-v2-threshold-candidates',
  'feasibility': 'stage1-v2-feasibility-contract',
  'objective': 'stage1-v2-objective-contract',
  'tiebreak': 'stage1-v2-tiebreak-contract',
  'unchanged': 'stage1-v2-unchanged-components',
  'future': 'stage1-v2-future-execution-requirements',
  'readiness': 'stage1-decision-policy-v2-readiness',
  'validation': 'stage1-decision-policy-v2-validation',
}
STATES = [READY] + [
  'HURDLE_STAGE1_V2_' + suffix + '_FROZEN'
  for suffix in (
    'THRESHOLD_CANDIDATE_SET',
    'FEASIBILITY_CONSTRAINTS',
    'EXACT_HIT_OBJECTIVE',
    'STATIC_FALSE_MOVE_TIEBREAK',
    'WITHIN_ONE_TICK_TIEBREAK',
    'CONSERVATIVE_THRESHOLD_TIEBREAK',
  )
]


def filename(label):
  return 'empirical-hurdle-' + LABELS[label] + '.json'


def oldname(label):
  return 'empirical-hurdle-' + label + '-v1.json'


def safe(path):
  path = Path(path).absolute()
  if '..' in path.parts or any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError(CONFLICT)
  return path


def check_inputs(inputs):
  try:
    if set(inputs) != set(PINS):
      raise ValueError('input set')
    for name, value in inputs.items():
      p.verify(value)
      if value['receipt_sha256'] != PINS[name]['receipt_sha256']:
        raise ValueError('receipt drift')
    r = inputs[oldname('failure-attribution-readiness')]
    if (
      r['status'] != 'HURDLE_FAILURE_ATTRIBUTION_V1_COMPLETE'
      or r['source_manifest_sha256'] != SOURCE_MANIFEST
      or r['attribution_manifest_sha256'] != ATTRIBUTION_MANIFEST
      or r['historical_verdict'] != 'HURDLE_NO_ADMISSIBLE_CANDIDATE'
      or r['historical_selection'] != 'MODEL_SELECTION_FAILED_CLOSED'
    ):
      raise ValueError('evidence state')
    m = r['mechanism_states']
    if (
      m['exact_hit_state'] != 'HURDLE_EXACT_HIT_STATIC_LOSS_ALL_JOBS'
      or m['stage1_design_review'] != 'STAGE1_GATE_REDESIGN_REVIEW_SUPPORTED'
      or m['job_counts'] != {'exact_hit_fail': 32, 'move_protection_pass': 32, 'projected_false_move': 32, 'static_loss_exceeds_gain': 32}
    ):
      raise ValueError('trigger')
    return inputs
  except (KeyError, TypeError, ValueError) as exc:
    raise ValueError(CONFLICT) from exc


def load_inputs():
  # Closed public allowlist; no user-supplied source root or private loader.
  try:
    inputs = {}
    for name, pin in PINS.items():
      raw = safe(p.PUBLIC / name).read_bytes()
      if p.sha(raw) != pin['file_sha256']:
        raise ValueError('file drift')
      inputs[name] = json.loads(raw)
    return check_inputs(inputs)
  except (ValueError, OSError, TypeError) as exc:
    raise ValueError(CONFLICT) from exc


def sealed(label, **body):
  return p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_' + LABELS[label].upper().replace('-', '_'),
      'family': 'HURDLE_RI_V1',
      'decision_policy': POLICY,
      'change_scope': 'THRESHOLD_OBJECTIVE_ONLY',
      'authority': 'DECLARATIVE_DESIGN_AND_SYNTHETIC_TESTS_ONLY',
      'actual_execution_authorized': False,
      **body,
    }
  )


def build():
  inputs = load_inputs()
  source = {Path(__file__).name: p.sha(Path(__file__).read_bytes())}
  prior = inputs[oldname('failure-attribution-readiness')]
  mechanism = inputs[oldname('mechanism-summary')]
  unchanged_labels = (
    'family-contract',
    'feature-contract',
    'training-population',
    'composition-contract',
    'rollout-contract',
    'stage1-fit-method',
    'stage1-convergence',
    'stage2-fit-method',
    'stage-normalization',
    'candidate-set',
    'route-cv-contract',
    'metric-contract',
    'comparator-contract',
    'acceptance-gate',
    'selection-rule',
  )
  bundle = {}
  bundle['evidence'] = sealed(
    'evidence',
    baseline=BASELINE,
    historical_inputs=PINS,
    source_manifest_sha256=SOURCE_MANIFEST,
    attribution_manifest_sha256=ATTRIBUTION_MANIFEST,
    historical_states=prior['mechanism_states'],
    historical_verdict=prior['historical_verdict'],
    historical_selection=prior['historical_selection'],
    historical_family_verdict=prior['family_verdict'],
    historical_failure_counts=mechanism['historical_failure_counts'],
    fold_transfer=mechanism['folds'],
    gate_perfect_rollout=mechanism['rollout'],
    rationale='REDUCE_STATIC_PROJECTED_HIT_LOSS_WHILE_PROTECTING_INTEGRATED_MOVE_BENEFIT',
    evidence_usage='POLICY_DESIGN_RATIONALE_ONLY_NEVER_THRESHOLD_NUMERICAL_INPUT',
    small_support='SMALL_SUPPORT_DESCRIPTIVE_ONLY_NOT_STAGE2_VALIDATION_OR_REDESIGN_AUTHORIZATION',
  )
  bundle['candidates'] = sealed(
    'candidates',
    population='CANDIDATE_FOLD_TRAIN_ONLY',
    expression='SORTED_UNION_OF_0_1_AND_UNIQUE_FINITE_TRAIN_P_MOVE',
    boundary_candidates=[0.0, 1.0],
    probability_domain='FINITE_BINARY64_CLOSED_INTERVAL_0_1',
    move_operator='>',
    static_operator='<=',
    default_threshold='NONE',
    fixed_grid=False,
    epsilon=0,
    midpoints=False,
    neighborhood_search=False,
    calibration='NONE',
    temperature_scaling='NONE',
    isotonic='NONE',
    platt_scaling='NONE',
    probability_transform='NONE',
    source_policy_sha256=inputs[oldname('threshold-policy')]['receipt_sha256'],
    scope='THRESHOLD_VALUES_WITHIN_EACH_CANDIDATE_FOLD_NOT_NEW_STRUCTURAL_CANDIDATES',
  )
  bundle['feasibility'] = sealed(
    'feasibility',
    clauses=[
      ['MOVE_RMSE', '<=', 'HOLD_MOVE_RMSE'],
      ['MOVE_MAE', '<=', 'HOLD_MOVE_MAE'],
      ['MOVE_P95', '<=', 'HOLD_MOVE_P95'],
      ['ALL_RMSE', '<', 'HOLD_ALL_RMSE'],
    ],
    conjunction='ALL_FOUR',
    population='SAME_ORDERED_TRAIN_ANCHORS',
    move_subset='ACTUAL_DELTA_TICK_NE_ZERO',
    output='INTEGRATED_PREDICTED_GATE_NOT_ORACLE',
    metric_contract_sha256=inputs[oldname('metric-contract')]['receipt_sha256'],
    metric_semantics='V1_CANONICAL_DELTA_ERROR_REDUCTION_AND_LINEAR_P95_UNCHANGED',
    finite_required=True,
    epsilon=0,
    additional_constraints=[],
    empty_state='STAGE1_DECISION_POLICY_V2_NO_FEASIBLE_THRESHOLD',
    failure_scope='CANDIDATE_FOLD_DECISION_POLICY',
    fallback='NONE',
    forbidden_fallbacks=['V1_THRESHOLD', 'BALANCED_ACCURACY', 'DEFAULT_0_5', 'NEAREST', 'RELAXATION'],
    all_static='EXCLUDED_BY_STRICT_ALL_RMSE; MOVE_NONWORSE_ALONE_DOES_NOT_EXCLUDE',
    minimum_predicted_move_fraction='NOT_SPECIFIED_NO_ADDED_CONSTRAINT',
  )
  bundle['objective'] = sealed(
    'objective',
    target='PROJECTED_NEXT_TICK_EXACTNESS',
    comparison='EXACT_INTEGER_COUNTS_ON_FIXED_POPULATION',
    exact_hit_count='np.count_nonzero(projected == target)',
    maximize_keys=['ALL_PROJECTED_EXACT_HIT_COUNT', 'NEGATIVE_STATIC_PROJECTED_FALSE_MOVE_COUNT', 'ALL_WITHIN_ONE_TICK_COUNT', 'threshold'],
    selection='LEXICOGRAPHIC_MAX_OVER_FEASIBLE_THRESHOLDS_ONLY',
    extra_keys=[],
    balanced_accuracy_authority=False,
    classification_accuracy_authority=False,
    continuous_exactness_authority=False,
    rounded_probability_authority=False,
  )
  bundle['tiebreak'] = sealed(
    'tiebreak',
    ordered_rules=[
      ['STATIC_PROJECTED_FALSE_MOVE_COUNT', 'MINIMIZE'],
      ['ALL_WITHIN_ONE_TICK_COUNT', 'MAXIMIZE'],
      ['threshold', 'MAXIMIZE'],
    ],
    static_false_move_count='np.count_nonzero((delta == 0) & (projected != current))',
    within_one_tick_count='np.count_nonzero(np.abs(projected - target) <= 1)',
    integer_arithmetic='WIDEN_TICKS_BEFORE_SUBTRACTION_NO_SIGNED16_OVERFLOW',
    false_move_basis='PROJECTED_MOTION_NOT_PREDICTED_GATE',
    final_tie='SAME_NUMERIC_THRESHOLD',
    epsilon=0,
  )
  bundle['unchanged'] = sealed(
    'unchanged',
    bindings={label: inputs[oldname(label)]['receipt_sha256'] for label in unchanged_labels},
    stage1='DETERMINISTIC_FLOAT64_UNREGULARIZED_LOGISTIC_NEWTON',
    stage2='DETERMINISTIC_FLOAT64_MOVE_ONLY_OLS',
    candidates=inputs[oldname('candidate-set')]['candidates'],
    folds=inputs[oldname('route-cv-contract')]['folds'],
    acceptance_clauses=inputs[oldname('acceptance-gate')]['clauses'],
    selection_rule=inputs[oldname('selection-rule')],
    stage1_stage2_context='TIED_D_AND_L',
    exact_structures=16,
    expected_future_jobs=32,
    steering_rate_dependency='NONE',
    overrides=[],
    historical_v1_threshold='TRAIN_ONLY_BALANCED_ACCURACY_FROZEN',
    historical_v1_policy_sha256=inputs[oldname('fitting-policy')]['receipt_sha256'],
    historical_v1_threshold_sha256=inputs[oldname('threshold-policy')]['receipt_sha256'],
    preservation='V1_FILES_MODELS_THRESHOLDS_GATES_VERDICTS_UNMODIFIED; NEW_POLICY_ADDITIVE_ONLY',
  )
  bundle['future'] = sealed(
    'future',
    next_increment='HURDLE_STAGE1_DECISION_POLICY_V2_EXECUTION_POLICY',
    status='REQUIRES_SEPARATE_AUTHORIZATION',
    model_strategy='UNRESOLVED',
    alternatives_requiring_predeclaration=['REUSE_BYTE_IDENTICAL_V1_FITTED_MODELS', 'CLEAN_32_JOB_REFIT_WITH_FROZEN_V1_ALGORITHMS'],
    stage2_train_prediction_lineage='UNRESOLVED',
    repeatability_store_resume='UNRESOLVED',
    v1_v2_direct_comparison_method='UNRESOLVED',
    auto_start=False,
    dependency='STAGE2_TRAIN_SIDE_FIXED_MODEL_OUTPUT_REQUIRED_BEFORE_TASK_OBJECTIVE_CAN_BE_EVALUATED',
    current_increment='NO_AVAILABILITY_PROBING_NO_PRIVATE_ACCESS_NO_STRATEGY_CHOICE',
  )
  bundle['policy'] = sealed(
    'policy',
    status=READY,
    interpretation='TRAIN_ONLY_TASK_AWARE_HARD_HURDLE_THRESHOLD_POLICY',
    threshold_population='TRAIN',
    scope='CANDIDATE_X_FOLD_LOCAL_ONLY',
    allowed_selection_inputs=['TRAIN_P_MOVE', 'TRAIN_FIXED_STAGE2_DELTA', 'TRAIN_CURRENT_TICK', 'TRAIN_TARGET_TICK', 'EXACT_TRAIN_ANCHOR_IDENTITIES'],
    forbidden_selection_inputs=[
      'DEVELOPMENT',
      'HOLDOUT',
      'POOLED_A_B',
      'ROLLOUT_DEVELOPMENT',
      'FUTURE_UNTOUCHED_ROUTE',
      'V1_ATTRIBUTION_CANDIDATE_RESULTS',
      'V1_DEVELOPMENT_METRICS',
      'V1_FOLD_FAILURE_COUNTS',
    ],
    gate_expression='p_move > threshold',
    static_delta=0.0,
    static_projection='CURRENT_TICK_EXACT_NO_PROJECTION_CALL',
    move_projection='np.rint(np.float64(current_tick) + np.float64(stage2_delta))',
    projection_name='DIRECT_ROUND_HALF_TO_EVEN_TO_INTEGER_TICK',
    projection_range='SIGNED16_INTEGER_FAIL_CLOSED_NO_CLIPPING',
    stage2='FIXED_WITHIN_CANDIDATE_FOLD_THRESHOLD_CANNOT_MODIFY_COEFFICIENTS',
    stage2_training='TRUE_MOVE_TRAIN_ONLY_UNCHANGED',
    branch='PREDICTED_STAGE1_GATE_ONLY',
    true_label_usage=['POPULATION_MASK', 'CONSTRAINT_METRIC', 'DIAGNOSTIC'],
    stage2_integration='ONLY_MOVE_BRANCH_NO_FORCED_MINIMUM_MOVEMENT',
    soft_blending=False,
    comparator='HOLD_LAST_ANGLE',
    comparator_delta=0,
    comparator_projected='CURRENT_TICK',
    anchor_identity='CANDIDATE_COMPARATOR_EXACT_SAME_ORDERED_TRAIN_ANCHORS',
    canonical_error='INTEGRATED_DELTA_MINUS_FLOAT64_ACTUAL_DELTA',
    normalizers='SEPARATE_STAGE1_ALL_TRAIN_AND_STAGE2_MOVE_TRAIN_UNCHANGED',
    balanced_accuracy='REPORT_ONLY',
    train_diagnostics=['TP', 'TN', 'FP', 'FN', 'BALANCED_ACCURACY', 'PRECISION', 'RECALL', 'SPECIFICITY', 'FALSE_MOVE_RATE', 'MISSED_MOVE_RATE'],
    diagnostics_ranking_authority=False,
    development_rescue=False,
    final_acceptance='V1_32_CLAUSES_EACH_FOLD_BOTH_FOLDS_AND_UNCHANGED',
    final_selection='V1_FROZEN_RULE_UNCHANGED_ADMISSIBLE_ONLY',
    public_future_fields=[
      'THRESHOLD_POLICY_RECEIPT',
      'CANDIDATE_THRESHOLD_COUNT',
      'FEASIBLE_THRESHOLD_COUNT',
      'SELECTED_THRESHOLD_RECEIPT_SHA',
      'TRAIN_AGGREGATE_CONFUSION',
      'TRAIN_AGGREGATE_TASK_METRICS',
    ],
    actual_threshold_visibility='PRIVATE_NOT_COMPUTED_THIS_INCREMENT',
    stage2_residual_risk='STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS',
    contract_sha256={k: v['receipt_sha256'] for k, v in bundle.items()},
    source_sha256=source,
  )
  preserved = {
    k: prior[k]
    for k in (
      'dataset',
      'S1',
      'S2',
      'S3',
      'historical_track',
      'stage_b',
      'ta',
      'sg',
      'composition',
      'future_holdout',
      'calibration_blockers',
      'sealed_reference',
      'vehicle',
      'closed_loop_bias',
      'historical_verdict',
      'historical_selection',
      'historical_s2_ri_verdict',
      'historical_attribution',
      'historical_design_trigger',
      'no_model_admitted',
      'search',
      'final_pooled_refit',
      'holdout',
      'holdout_state',
      'opening_count',
      'vehicle_authority',
    )
  }
  bundle['readiness'] = sealed(
    'readiness',
    status=READY,
    states=STATES,
    **dict.fromkeys(('stage1_model', 'stage2_model', 'features', 'route_folds', 'rollout', 'acceptance_gate', 'selection_rule'), 'UNCHANGED'),
    structures='16_UNCHANGED',
    actual_v2_threshold='NOT_COMPUTED',
    private_access=0,
    execution_states={
      'V2_' + k: 'NOT_RUN'
      for k in (
        'STAGE1_REFIT',
        'STAGE2_REFIT',
        'THRESHOLD_SELECTION',
        'PREDICTION',
        'ROLLOUT',
        'CV_SCORING',
        'MODEL_SELECTION',
      )
    },
    openings=dict.fromkeys(
      (
        'private_hurdle_store',
        'd_drive_private_results',
        'threshold_values',
        'coefficients',
        'prediction_arrays',
        'full_paths',
        'raw_logs',
        'qlogs',
        'holdout',
      ),
      0,
    ),
    stage2_residual_risk='STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS',
    next_increment=bundle['future']['next_increment'],
    next_increment_status='REQUIRES_SEPARATE_AUTHORIZATION',
    policy_sha256=bundle['policy']['receipt_sha256'],
    **preserved,
  )
  bundle['validation'] = sealed(
    'validation',
    status='PUBLIC_DESIGN_CONTRACT_AND_SHA_CHAIN_VALIDATED',
    input_pins=PINS,
    source_sha256=source,
    artifact_receipts={k: v['receipt_sha256'] for k, v in bundle.items()},
    private_access=0,
    actual_fitting='NOT_RUN',
    actual_threshold='NOT_COMPUTED',
    prediction='NOT_RUN',
    rollout='NOT_RUN',
    selection='NOT_RUN',
    checks=[
      'EXACT_PUBLIC_EVIDENCE_BINDING',
      'UNCHANGED_V1_COMPONENTS',
      'FOUR_FEASIBILITY_CLAUSES',
      'PROJECTED_INTEGER_COUNT_OBJECTIVE',
      'EXACT_TIEBREAK_ORDER',
      'TRAIN_ONLY',
      'NO_EXECUTOR_API',
    ],
    regression_evidence='CHANGE_RECORD_VALIDATION_SECTION',
    private_preservation='NOT_ACCESSED_NO_FILESYSTEM_WIDE_BYTE_IDENTITY_CLAIM',
  )
  return {filename(k): v for k, v in bundle.items()}


def validate(bundle):
  expected = build()
  try:
    if type(bundle) is not dict or set(bundle) != set(expected):
      raise ValueError('artifact set')
    for name, value in bundle.items():
      p.verify(value)
      if p.canonical(value) != p.canonical(expected[name]):
        raise ValueError('contract drift')
    return bundle
  except (ValueError, TypeError, KeyError) as exc:
    raise ValueError(CONFLICT) from exc


def publish(output):
  root = safe(output)
  bundle = validate(build())
  encoded = {name: json.dumps(v, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n' for name, v in bundle.items()}
  for name, data in encoded.items():
    for target in (root / name, root / (name + '.atomic')):
      path = safe(target)
      if path.exists() and (not path.is_file() or path.read_bytes() != data):
        raise ValueError('HURDLE_STAGE1_V2_IMMUTABLE_OUTPUT_CONFLICT')
  for name in sorted(bundle, key=lambda n: (n == filename('validation'), n)):
    p.persist(safe(root / name), bundle[name])
  return bundle


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', required=True, type=Path)
  args = parser.parse_args()
  bundle = publish(args.output)
  print(json.dumps({'status': READY, 'artifacts': len(bundle), 'private_access': 0, 'actual_threshold': 'NOT_COMPUTED'}))


if __name__ == '__main__':
  main()
