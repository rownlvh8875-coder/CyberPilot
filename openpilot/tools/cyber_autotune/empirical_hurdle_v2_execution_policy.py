"""Public-only V2 execution policy. No private discovery or numerical executor."""

import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_hurdle_decision_policy_v2 as design
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

BASELINE = '32018c9cc4381c779c7001c51e0949b120185525'
POLICY = 'HURDLE_STAGE1_DECISION_POLICY_V2_EXECUTION_POLICY'
READY = POLICY + '_FROZEN'
CONFLICT = POLICY + '_CONFLICT'
AUTHORIZATION = 'e4eeaca2f891cc9fdb1370b7ae735d963287af6c09cca85dc689c8e9c560c6ea'
REPEATABILITY = '3b9e8e1f562972268a7a0543f72d3f98fe237a9f3e1c5e045b69e19f9c69949b'
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
  'empirical-hurdle-stage1-decision-policy-v2-design-evidence.json': {
    'file_sha256': '6cb3cc78425b3bc1d13df087ffe453eca08d71f0d4592813dd836a9d9187da07',
    'receipt_sha256': '1276f6851b07bb846b409d626a970d4d8ba9820ea6c6ed56c0908adad928d9f4',
  },
  'empirical-hurdle-stage1-decision-policy-v2.json': {
    'file_sha256': 'e358a8e99dbc2d2e8943ef0e6f326b74e1d3d623d5573218b22c6dac34c6a634',
    'receipt_sha256': '463ac0c2f34b59b67c1a1d7365c5662d717a49de328cabfd9101f185bff2bf19',
  },
  'empirical-hurdle-stage1-v2-threshold-candidates.json': {
    'file_sha256': '8dc88f8c66f1221e86e105894e876d029860ad9dffe5a25485df5d6c7f38dbb8',
    'receipt_sha256': '5d321ae32a134179b96debb66e2cadf7189a8c63bbe3daf5f764c61c5f279185',
  },
  'empirical-hurdle-stage1-v2-feasibility-contract.json': {
    'file_sha256': 'e0d0c351da44347fc2d097f7b3e91ab87964262348ba0c994719a4fcdbc58f91',
    'receipt_sha256': '2dc5e8fbbf1830a5f69309c9e742811fdf8fef19cdd0d0c59e5daa434170fadb',
  },
  'empirical-hurdle-stage1-v2-objective-contract.json': {
    'file_sha256': '20b8154153ade8601323b609f1637fb727702657afda3b9a122586ff6a13f5b7',
    'receipt_sha256': 'f12a268522064543252814842a3455a39c650531fdaa4f08c953e2ec9be025d9',
  },
  'empirical-hurdle-stage1-v2-tiebreak-contract.json': {
    'file_sha256': 'c7dd4c8bbe9df270a1154e2fc7bf5f30e61bf747761a2bba89a8c60014f9373f',
    'receipt_sha256': 'e38949c44f922eda04ad9424a7b06ad02faca50e92b2829e5ce2fa1a2a18d571',
  },
  'empirical-hurdle-stage1-v2-unchanged-components.json': {
    'file_sha256': 'bdaff0385c352ce17fa8fb8efcb39ef83f340d1504224fc085f5e1cebf9bcf9a',
    'receipt_sha256': '8bb8f8ac79f216c364b0d24340036851df4460aae8afe2fec5ce1cc95dde8e61',
  },
  'empirical-hurdle-stage1-v2-future-execution-requirements.json': {
    'file_sha256': '117b53a21fafce22afa0155cd9858f17fb779540f3b26d45b729f2c42114b7f5',
    'receipt_sha256': '52586eae8858a3cf31f54c74917dbb7df2d7b792a14a4e39567a5f2b057c74f9',
  },
  'empirical-hurdle-stage1-decision-policy-v2-readiness.json': {
    'file_sha256': 'bdc12b1891d64cadf0cf45e88383acd5544d77cf33326ed6c4ff2adde2568ca0',
    'receipt_sha256': '6963e8a3d0b3ae018a6612e7d07e18143db0f5147d7ccb5b75e90dbc77dc00e8',
  },
  'empirical-hurdle-stage1-decision-policy-v2-validation.json': {
    'file_sha256': 'f9a655493195108dc2b1128c2d7e58e580d382349c45104086edcb63ea88cf2b',
    'receipt_sha256': 'c4ae8f8a377578093582a4a60b12e08f1c8bccb95e81e458f3cefc542572e181',
  },
  'empirical-hurdle-fit-cv-authorization-v1.json': {
    'file_sha256': '54b879120e55c805df5f4094bf04637553bf6faafcfecef69f052d160a29ccb2',
    'receipt_sha256': 'd93d6bb418a958b998c0308e4ce71a605a4069286029b5539d80b38001a34c6b',
  },
  'empirical-hurdle-fit-cv-repeatability-v1.json': {
    'file_sha256': 'f734bd6fb3a956e62c883eb24b22d0df0a4626a6ae17a733ca43592f27c00e08',
    'receipt_sha256': '60c262b004f253f6de203404520f9edc8ab3d78c0dba51948dd62759003f35dc',
  },
}
LABELS = {
  'policy': 'execution-policy',
  'reuse': 'model-reuse-contract',
  'train': 'train-prediction-lineage',
  'stage2': 'stage2-train-inference-contract',
  'development': 'development-execution-contract',
  'rollout': 'rollout-execution-contract',
  'comparison': 'v1-comparison-contract',
  'storage': 'storage-contract',
  'repeatability': 'repeatability-contract',
  'resume': 'resume-contract',
  'readiness': 'execution-readiness',
  'validation': 'execution-policy-validation',
}
STATES = [READY] + [
  'HURDLE_STAGE1_V2_' + x + '_FROZEN'
  for x in (
    'V1_MODEL_REUSE',
    'NO_REFIT_EXECUTION',
    'TRAIN_PREDICTION_LINEAGE',
    'STAGE2_ALL_TRAIN_INFERENCE',
    'DEVELOPMENT_EXECUTION',
    'ROLLOUT_EXECUTION',
    'V1_DIRECT_COMPARISON',
    'STORAGE_POLICY',
    'REPEATABILITY_POLICY',
    'RESUME_POLICY',
  )
]


def filename(label):
  return 'empirical-hurdle-stage1-v2-' + LABELS[label] + '.json'


def load_inputs():
  # Fixed public allowlist only. No path arguments, private metadata, or discovery.
  try:
    inputs = {}
    for name, pin in PINS.items():
      raw = design.safe(p.PUBLIC / name).read_bytes()
      if p.sha(raw) != pin['file_sha256']:
        raise ValueError('public file drift')
      value = json.loads(raw)
      p.verify(value)
      if value['receipt_sha256'] != pin['receipt_sha256']:
        raise ValueError('receipt drift')
      inputs[name] = value
    auth = inputs[design.oldname('fit-cv-authorization')]
    repeat = inputs[design.oldname('fit-cv-repeatability')]
    if (
      auth['authorization_sha256'] != AUTHORIZATION
      or repeat['repeatability']['receipt_sha256'] != REPEATABILITY
      or auth['private_manifest_sha256'] != design.SOURCE_MANIFEST
      or repeat['private_manifest_sha256'] != design.SOURCE_MANIFEST
    ):
      raise ValueError('successful source binding')
    if inputs[design.filename('readiness')]['status'] != design.READY:
      raise ValueError('design status')
    return inputs
  except (ValueError, OSError, KeyError, TypeError) as exc:
    raise ValueError(CONFLICT) from exc


def sealed(label, **body):
  return p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_STAGE1_V2_' + LABELS[label].upper().replace('-', '_'),
      'family': 'HURDLE_RI_V1',
      'decision_policy': design.POLICY,
      'change_scope': 'THRESHOLD_OBJECTIVE_ONLY',
      'authority': 'PUBLIC_POLICY_AND_SYNTHETIC_TESTS_ONLY',
      'actual_execution_authorized': False,
      **body,
    }
  )


def build():
  inputs = load_inputs()
  d = {k: inputs[design.filename(k)] for k in design.LABELS}
  unchanged = d['unchanged']
  source = {Path(__file__).name: p.sha(Path(__file__).read_bytes())}
  model_fields = [
    'stage1_model_receipt_sha256',
    'stage1_coefficient_sha256',
    'stage1_normalizer_receipt_sha256',
    'stage2_model_receipt_sha256',
    'stage2_coefficient_sha256',
    'stage2_normalizer_receipt_sha256',
  ]
  b = {}
  b['reuse'] = sealed(
    'reuse',
    model_strategy='REUSE_BYTE_IDENTICAL_V1_FITTED_MODELS',
    purpose='ISOLATE_THRESHOLD_POLICY_EFFECT',
    rejected_strategy='CLEAN_32_JOB_REFIT_WITH_FROZEN_V1_ALGORITHMS',
    refit=dict.fromkeys(('stage1', 'stage2', 'normalizer'), 'FORBIDDEN'),
    fitting_calls=dict.fromkeys(('logistic', 'OLS', 'normalizer', 'numpy.linalg.solve', 'numpy.linalg.lstsq'), 0),
    warm_start='NOT_APPLICABLE',
    model_replacement=False,
    model_identity_fields=model_fields,
    identity='EXACT_RECEIPTS_AND_COEFFICIENT_NORMALIZER_BYTES_PER_CANDIDATE_FOLD',
    successful_source_manifest=design.SOURCE_MANIFEST,
    mismatch='V2_V1_MODEL_IDENTITY_CONFLICT',
    v1_threshold='HISTORICAL_COMPARISON_LINEAGE_ONLY_NOT_V2_SELECTION_INPUT',
    v2_threshold='NEW_PRIVATE_FOLD_LOCAL_TRAIN_ONLY_OUTPUT',
    unchanged_components=unchanged['bindings'],
    candidates=unchanged['candidates'],
    folds=unchanged['folds'],
    acceptance_clauses=unchanged['acceptance_clauses'],
    selection_rule=unchanged['selection_rule'],
    structures=16,
    expected_jobs=32,
    steering_rate_dependency='NONE',
    overrides=[],
  )
  b['train'] = sealed(
    'train',
    strategy='PREDICTION_ONLY_REPLAY_FROM_IMMUTABLE_V1_MODELS',
    stage1='PREDICTION_ONLY_REPLAY_FROM_IMMUTABLE_V1_MODEL',
    inputs=['V1_STAGE1_COEFFICIENTS', 'V1_STAGE1_NORMALIZER', 'EXACT_V1_ORDERED_TRAIN_FEATURES'],
    source='EXACT_V1_CANDIDATE_SPECIFIC_TRAIN_FEATURE_TARGET_ARRAYS_BOUND_TO_SUCCESSFUL_DERIVED_LINEAGE',
    source_array_sha='EXACT_V1_ARRAY_SHA_REQUIRED',
    anchors='V2_EQUALS_V1_ORDERED_TRAIN_ANCHOR_SHA',
    no_row_drift=['ADD', 'DROP', 'REORDER', 'HISTORY', 'ELIGIBILITY', 'SUPPORT_FILTER'],
    saved_v1_p_move='IF_RECEIPT_BOUND_ARRAY_EXISTS_REQUIRE_BYTE_EXACT_REPLAY_EQUALITY',
    canonical='MODEL_REPLAY_OUTPUT_NOT_BLIND_SAVED_ARRAY_REUSE',
    mismatch='V2_STAGE1_TRAIN_PREDICTION_IDENTITY_FAILURE',
    missing_input='FAIL_CLOSED_NO_REBUILD_NO_RAW_REEXTRACTION',
    forbidden_sources=['RAW_RLOG', 'QLOG', 'NEW_CAUSAL_REBUILD', 'POOLED_A_B', 'HOLDOUT'],
    dtype='FLOAT64_C_ORDER',
    environment={
      'python': '3.12.13',
      'numpy': '2.5.3',
      'OPENBLAS_NUM_THREADS': '1',
      'OMP_NUM_THREADS': '1',
      'blas_identity_sha256': inputs[design.oldname('fit-cv-authorization')]['blas_build_identity_sha256'],
      'rng': 'NONE',
      'prediction_reduction': 'V1_EXACT_OPERATION_ORDER_AND_BATCHING_NO_REASSOCIATION',
    },
    threshold_input_allowlist=d['policy']['allowed_selection_inputs'],
    threshold_input_forbidden=d['policy']['forbidden_selection_inputs'] + ['V1_THRESHOLD_VALUE', 'ROLLOUT_RESULT'],
    threshold_api='EXACT_ALLOWLIST_TRAIN_ONLY_NO_EXTRA_ARGUMENTS',
    threshold_contracts={k: d[k] for k in ('candidates', 'feasibility', 'objective', 'tiebreak')},
    composition={
      'branch': 'p_move > threshold',
      'static_delta': 0.0,
      'static_tick': 'CURRENT_TICK_NO_PROJECTION',
      'move_delta': 'FIXED_STAGE2_ALL_TRAIN_DELTA',
      'move_tick': d['policy']['move_projection'],
      'canonical_error': d['policy']['canonical_error'],
      'true_label': 'MASK_CONSTRAINT_DIAGNOSTIC_ONLY',
      'soft_blending': False,
      'forced_movement': False,
    },
    evaluator={
      'canonical_reference': 'ONE_THRESHOLD_AT_A_TIME_BRUTE_FORCE_V1_ORDERED_FLOAT64_REDUCTIONS',
      'memory': 'O_N_WORKSPACE_NO_N_BY_THRESHOLD_PAYLOAD_OR_FULL_ARRAY_COPIES_PER_THRESHOLD_RETAINED',
      'optimization': 'OPTIONAL_SORTED_SWEEP_ONLY_AFTER_SYNTHETIC_BYTE_EXACT_REFERENCE_EQUIVALENCE',
      'equivalence': 'EVERY_THRESHOLD_METRIC_FEASIBILITY_COUNT_OBJECTIVE_AND_SELECTED_VALUE',
      'reduction': 'CUMULATIVE_SAE_SSE_REASSOCIATION_NOT_ASSUMED_EQUIVALENT; CANONICAL_REDUCTION_REQUIRED',
      'p95': 'np.percentile(abs(error), 95, method="linear")',
      'forbidden': ['APPROXIMATE_QUANTILE', 'HISTOGRAM_BINNING', 'EPSILON', 'ROUNDING', 'PROBABILITY_QUANTIZATION'],
      'failure': 'REJECT_NON_EQUIVALENT_OPTIMIZATION_USE_CANONICAL_REFERENCE_NO_POLICY_CHANGE',
    },
    threshold_visibility='PRIVATE',
    publication=d['policy']['public_future_fields'] + ['SELECTED_OBJECTIVE_COUNTS'],
  )
  b['stage2'] = sealed(
    'stage2',
    population='ALL_CANDIDATE_SPECIFIC_TRAIN_ANCHORS',
    includes_true_static=True,
    fitting_population='V1_TRUE_MOVE_TRAIN_ONLY_UNCHANGED',
    normalizer='EXACT_IMMUTABLE_V1_STAGE2_MOVE_ONLY_TRAIN_NORMALIZER',
    normalization_recalculation=False,
    coefficient_change=False,
    inference='PRECOMPUTE_FIXED_STAGE2_DELTA_FOR_EVERY_TRAIN_ROW',
    branch='PREDICTED_STAGE1_P_MOVE_GT_THRESHOLD_ONLY',
    true_label_branch=False,
    why='TRUE_STATIC_ROWS_CAN_BE_PREDICTED_MOVE_AND_REQUIRE_STAGE2_BRANCH_OUTPUT',
    prediction_sha='C_ORDER_FLOAT64_EXACT_ARRAY_IDENTITY_RECEIPT',
  )
  b['development'] = sealed(
    'development',
    prerequisite='IMMUTABLY_PUBLISHED_TRAIN_THRESHOLD_FINALIZATION_RECEIPT_BEFORE_ANY_DEV_OPEN',
    no_feasible_threshold='FOLD_DECISION_POLICY_FAILURE_NO_DEV_RESCUE',
    strategy='SAME_ANCHORS_NEW_V2_GATE',
    models='EXACT_V1_STAGE1_AND_STAGE2_REPLAY_NO_REFIT',
    anchors='V2_EQUALS_V1_ORDERED_DEVELOPMENT_ANCHOR_SHA',
    branch='PREDICTED_GATE_ONLY_P_MOVE_GT_V2_THRESHOLD',
    stage2='CANDIDATE_DELTA_REPLAY_ONLY_SELECTED_MOVE_ROWS_INTEGRATE; STATIC_EXACT_HOLD',
    metrics=[
      'ALL_RMSE',
      'ALL_MAE',
      'ALL_P95',
      'ALL_EXACT_HIT',
      'ALL_WITHIN_ONE_TICK',
      'TRUE_MOVE_INTEGRATED_RMSE',
      'TRUE_MOVE_INTEGRATED_MAE',
      'TRUE_MOVE_INTEGRATED_P95',
    ],
    diagnostics='V1_STAGE1_AND_STAGE2_ORACLE_REPORT_ONLY_UNCHANGED',
    comparator='HOLD_LAST_ANGLE_EXACT_SAME_ORDERED_ANCHORS',
    metric_contract=unchanged['bindings']['metric-contract'],
    support_and_definedness='V1_UNCHANGED_FAIL_CLOSED',
    gate='UNCHANGED_V1_32_CLAUSES_PER_FOLD_BOTH_FOLDS_AND',
    gate_receipt=unchanged['bindings']['acceptance-gate'],
    selection_receipt=unchanged['bindings']['selection-rule'],
    selection='ONLY_ADMISSIBLE_CANDIDATES_V1_RULE_NO_V1_METRIC_INPUT',
  )
  b['rollout'] = sealed(
    'rollout',
    strategy='SAME_ANCHORS_NEW_V2_GATE',
    contract_receipt=unchanged['bindings']['rollout-contract'],
    anchors='V2_EQUALS_V1_ORDERED_ANCHOR_SHA_FOR_EACH_HORIZON',
    horizons=[25, 50, 100, 200],
    frequency_hz=100,
    state='PROJECTED_INTEGER_TICK_AND_PROJECTED_DELTA_HISTORY',
    steps=[
      'BUILD_PROJECTED_STATE_HISTORY_FEATURES',
      'IMMUTABLE_V1_STAGE1_NORMALIZER_MODEL',
      'P_MOVE_GT_FROZEN_V2_THRESHOLD',
      'STATIC_EXACT_HOLD_WITHOUT_STAGE2',
      'MOVE_IMMUTABLE_V1_STAGE2_NORMALIZER_MODEL_AND_DIRECT_HALF_EVEN_PROJECTION',
      'UPDATE_PROJECTED_DELTA_HISTORY',
      'ADVANCE_LOGGED_COMMAND_AND_VEGO',
    ],
    exogenous='LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT',
    truth='FUTURE_OBSERVED_ANGLE_DELTA_MOVE_LABEL_SCORING_ONLY_NOT_FEATURE_OR_BRANCH',
    forbidden=['REFIT', 'ADAPTIVE_THRESHOLD', 'HYSTERESIS', 'ONLINE_NORMALIZER_UPDATE', 'FORCED_MINIMUM_MOVEMENT'],
    gate='OVERALL_AND_PATH_MOVED_RMSE_MAE_P95_NONWORSE_ALL_FOUR_HORIZONS_BOTH_FOLDS',
  )
  b['comparison'] = sealed(
    'comparison',
    authority='REPORT_ONLY',
    identity=['candidate_id', 'fold', 'ordered_anchor_sha256'],
    mismatch='V2_V1_COMPARISON_IDENTITY_CONFLICT',
    train=[
      'THRESHOLD_RECEIPT_ID',
      'THRESHOLD_CANDIDATE_COUNT',
      'PREDICTED_MOVE_FRACTION',
      'TP',
      'TN',
      'FP',
      'FN',
      'FALSE_MOVE_RATE',
      'MISSED_MOVE_RATE',
      'BALANCED_ACCURACY',
      'ALL_RMSE',
      'ALL_EXACT_HIT',
      'ALL_WITHIN_ONE_TICK',
      'STATIC_PROJECTED_FALSE_MOVE_COUNT',
      'TRUE_MOVE_RMSE',
      'TRUE_MOVE_MAE',
      'TRUE_MOVE_P95',
    ],
    development=b['development']['metrics'] + ['FALSE_MOVE_RATE', 'MISSED_MOVE_RATE', 'PREDICTED_MOVE_FRACTION', 'BALANCED_ACCURACY'],
    rollout={'horizons': [25, 50, 100, 200], 'populations': ['OVERALL', 'PATH_MOVED'], 'metrics': ['RMSE', 'MAE', 'P95', 'CLAUSE_PASS_FAIL']},
    clauses=['CLAUSES_RECOVERED', 'CLAUSES_NEWLY_FAILED', 'CLAUSES_UNCHANGED_PASS', 'CLAUSES_UNCHANGED_FAIL'],
    candidate_admissibility='V1_AND_V2_FACTUAL_RESULTS_ONLY_NO_COUNTERFACTUAL_GATE',
    v1_train_metrics='USE_RECEIPT_BOUND_AGGREGATES_OR_COMPARISON_ONLY_FIXED_V1_THRESHOLD_ON_SAME_REPLAY_AFTER_V2_FINALIZATION',
    v1_threshold_compartment='READ_ONLY_COMPARISON_AFTER_V2_FINALIZATION_NEVER_SELECTOR_INPUT',
    missing_comparison_lineage='FAIL_CLOSED_NO_INVENTED_AGGREGATES_NO_REBUILD_NO_THRESHOLD_SEARCH',
    actual_threshold_publication=False,
    v1_metrics_selection_authority=False,
    descriptive_states=['V2_EXACT_HIT_IMPROVED', 'V2_STATIC_PROJECTED_FALSE_MOVE_REDUCED', 'V2_TRUE_MOVE_PROTECTION_PRESERVED', 'V2_LONG_HORIZON_IMPROVED'],
    interpretation='RETROSPECTIVE_DEVELOPMENT_THRESHOLD_EFFECT_ISOLATION_NOT_INDEPENDENT_CAUSAL_VALIDATION',
    automatic_design_success=False,
  )
  b['storage'] = sealed(
    'storage',
    volume='D_ONLY',
    c_result_directory=False,
    path_discovery_this_increment=0,
    future_root='EXPLICIT_EXTERNAL_D_ROOT_CONFIRMED_BY_SEPARATE_EXECUTION_AUTHORIZATION',
    source='SUCCESSFUL_C4DE_MANIFEST_ONLY_NO_INCOMPLETE_OR_INVALID_RUN',
    reference_only=['V1_STAGE1_MODEL', 'V1_STAGE2_MODEL', 'V1_NORMALIZERS', 'V1_TRUTH', 'V1_HOLD_LAST_PATH', 'V1_ANCHORS', 'V1_EXOGENOUS_INPUTS'],
    reference_schema=['successful_manifest_sha256', 'relative_member', 'receipt_sha256', 'content_sha256'],
    reference_rule='REUSE_EXISTING_IMMUTABLE_REFERENCE_NO_REDUNDANT_PAYLOAD',
    train_payload=[
      'PRIVATE_V2_THRESHOLD',
      'THRESHOLD_RECEIPT',
      'P_MOVE_SHA',
      'STAGE2_ALL_TRAIN_DELTA_SHA',
      'SELECTED_GATE',
      'PROJECTED_NEXT_TICK',
      'TRAIN_OBJECTIVE_AGGREGATES',
      'SAME_ANCHOR_RECEIPT',
    ],
    development_payload=['P_MOVE_GATE_IDENTITY', 'INTEGRATED_PREDICTION', 'PROJECTED_NEXT_TICK', 'ERRORS'],
    rollout_payload=['V2_PROJECTED_PATH', 'V2_GATE_PATH', 'ENDPOINT_ERRORS'],
    compression={
      'format': 'C_ORDER_NPY_GZIP',
      'level': 1,
      'mtime': 0,
      'filename': '',
      'hashes': ['COMPRESSED_FILE_SHA256', 'DECODED_NPY_SHA256', 'ARRAY_CONTENT_SHA256'],
      'metadata': ['DTYPE', 'SHAPE', 'C_ORDER'],
      'lossless': True,
    },
    path_guards=[
      'ABSOLUTE_D_VOLUME_PROOF',
      'NO_SOURCE_OR_RAW_DERIVED_OVERLAP',
      'NO_SYMLINK_COMPONENT',
      'NO_TRAVERSAL',
      'NO_OVERWRITE',
      'ATOMIC_WRITES',
      'FREE_SPACE_GUARD',
    ],
    windows_and_wsl='D_DRIVE_OR_VERIFIED_D_BACKED_WSL_OUTPUT_ONLY_NO_C_RESULTS',
    commits=['PAYLOAD', 'RECEIPT_LAST', 'JOB_MANIFEST_LAST', 'RUN_MANIFEST_LAST'],
    run1='COMPLETE_AUTHORITATIVE_PERSISTENT_V2_EVIDENCE',
    run2='INDEPENDENT_D_SCRATCH_LARGE_PAYLOAD_OPTIONALLY_REMOVED_ONLY_AFTER_EXACT_VERIFICATION',
    run2_cleanup_requires=[
      'COMPLETE_BOTH_RUNS',
      'EXACT_ALL_CONTENT_DECODED_FILE_HASHES_AND_MANIFESTS',
      'DURABLE_RUN2_MANIFEST_RECEIPT',
      'DURABLE_COMPARISON_AND_EQUALITY_SUMMARY',
      'DURABLE_SELECTED_THRESHOLD_RECEIPT_AND_FINAL_RESULT_IDENTITY',
      'RESOLVED_SCRATCH_WITHIN_AUTHORIZED_D_ROOT_NO_SYMLINK_NO_SOURCE_OVERLAP',
    ],
    cleanup_failure='KEEP_SCRATCH_NO_DELETION',
    deletion_this_increment=False,
    retained=[
      'RUN2_MANIFEST',
      'RUN2_RECEIPT',
      'COMPARISON_MANIFEST',
      'FILE_HASH_EQUALITY_SUMMARY',
      'SELECTED_THRESHOLD_RECEIPT_IDENTITY',
      'FINAL_RESULT_IDENTITY',
    ],
    public_forbidden=[
      'ACTUAL_THRESHOLD',
      'COEFFICIENTS',
      'NORMALIZER_VALUES',
      'PER_ROW_PROBABILITY',
      'PER_ROW_GATE',
      'PREDICTIONS',
      'PATHS',
      'TICKS',
      'COMMANDS',
      'TIMESTAMPS',
      'PRIVATE_PATHS',
      'GPS',
    ],
  )
  b['repeatability'] = sealed(
    'repeatability',
    runs=2,
    independent='REPLAY_AND_V2_THRESHOLD_DEV_ROLLOUT_GATE_SELECTION_FROM_BEGINNING_NO_RUN1_CACHE_REUSE',
    scope=[
      'INPUT_MODEL_RECEIPTS',
      'TRAIN_ANCHOR_SHA',
      'STAGE1_P_MOVE_BYTES',
      'STAGE2_ALL_TRAIN_DELTA_BYTES',
      'THRESHOLD_CANDIDATE_COUNT',
      'FEASIBLE_COUNT',
      'PRIVATE_THRESHOLD_BYTES',
      'TRAIN_OBJECTIVE_METRICS',
      'DEVELOPMENT_PREDICTIONS',
      'ROLLOUT_PROJECTED_PATHS',
      'GATE_PATHS',
      'METRICS',
      'CLAUSES',
      'ADMISSIBLE_SET',
      'SELECTED_CANDIDATE',
      'PUBLIC_AGGREGATES',
      'RECEIPTS',
      'MANIFESTS',
    ],
    equality='BYTE_EXACT_NO_TOLERANCE',
    manifest_identity='CANONICAL_LOGICAL_RELATIVE_NAMES_NO_RUN_NUMBER_ROOT_TIMING_OR_HOST_METADATA',
    operational_metadata='RUN_ROLE_AND_SCRATCH_LIFECYCLE_IN_SEPARATE_NON_NUMERICAL_AUDIT_RECEIPT',
    scratch_compare='ALL_CORRESPONDING_FILE_CONTENT_DECODED_HASHES_BEFORE_OPTIONAL_CLEANUP',
    failure='HURDLE_STAGE1_V2_REPEATABILITY_FAILURE',
    failure_selected_candidate=None,
    failure_result='INVALID_HOLDOUT_CLOSED',
  )
  b['resume'] = sealed(
    'resume',
    mode='VERIFY_ONLY_SAVED_V2_STORE',
    prerequisite='COMPLETE_AUTHORITATIVE_RUN1_MANIFEST',
    traps=['V1_MODEL_LOADER', 'SOURCE_FEATURE_LOADER', 'PREDICTION_REPLAY', 'THRESHOLD_EVALUATOR', 'DEVELOPMENT_EVALUATOR', 'ROLLOUT', 'SCORER', 'SELECTOR'],
    compute_calls=0,
    source_open_calls=0,
    verification='VERIFY_PERSISTED_V2_PAYLOAD_HASHES_RECEIPTS_MANIFEST_AND_READINESS_CHAIN',
    external_reference_verification='SAVED_SEALED_LINEAGE_ONLY_NO_DEREFERENCE_NO_CURRENT_SOURCE_BYTE_CLAIM',
    outputs=['SAME_MANIFEST', 'SAME_READINESS'],
    incomplete='FAIL_CLOSED_NO_RECOMPUTATION',
  )
  b['policy'] = sealed(
    'policy',
    status=READY,
    baseline=BASELINE,
    public_inputs=PINS,
    references={
      'v1_baseline': 'f5ed849bd27287084efc81ba3dd0275ebfc5ca0a',
      'v1_manifest': design.SOURCE_MANIFEST,
      'v1_authorization': AUTHORIZATION,
      'v1_repeatability': REPEATABILITY,
      'attribution_baseline': design.BASELINE,
      'attribution_manifest': design.ATTRIBUTION_MANIFEST,
      'v2_design_policy': d['policy']['receipt_sha256'],
      'v2_design_readiness': d['readiness']['receipt_sha256'],
      'v2_future_requirements': d['future']['receipt_sha256'],
    },
    execution_order='LEXICAL_CANDIDATE_THEN_FOLD_A_THEN_FOLD_B',
    jobs=32,
    performance_early_stop=False,
    every_job_receipt=True,
    fold_failures=[
      'MODEL_IDENTITY',
      'SOURCE_ANCHOR',
      'PREDICTION_BYTE_IDENTITY',
      'NO_FEASIBLE_THRESHOLD',
      'NONFINITE_METRIC',
      'PROJECTION',
      'SUPPORT',
      'DIAGNOSTIC_UNDEFINEDNESS',
      'ROLLOUT',
    ],
    bad_row_drop=False,
    fallbacks=[],
    outcomes=[
      'V2_NO_FEASIBLE_THRESHOLD_FOR_ONE_OR_MORE_FOLDS',
      'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE',
      'HURDLE_STAGE1_V2_SINGLE_ADMISSIBLE_CANDIDATE',
      'HURDLE_STAGE1_V2_MULTIPLE_ADMISSIBLE_CANDIDATES',
    ],
    zero_candidates='MODEL_SELECTION_FAILED_CLOSED',
    selected_state='HURDLE_STAGE1_V2_RETROSPECTIVE_CV_SELECTED',
    no_feasible_scope='AFFECTED_FOLD_FAILS_OTHER_JOBS_STILL_ACCOUNTED',
    future_prerequisites=[
      'SEPARATE_EXECUTION_AUTHORIZATION',
      'EXACT_SUCCESSFUL_V1_SOURCE_PATH',
      'EXPLICIT_D_OUTPUT_ROOT',
      'FREE_SPACE_GUARD',
      'SOURCE_MANIFEST',
      'MODEL_RECEIPTS',
      'EXACT_SOURCE_ARRAY_AND_ANCHOR_LINEAGE',
      'PINNED_EXECUTION_ENVIRONMENT',
    ],
    availability_probing=False,
    next_increment='HURDLE_STAGE1_DECISION_POLICY_V2_RETROSPECTIVE_EXECUTION',
    next_increment_status='REQUIRES_SEPARATE_AUTHORIZATION',
    auto_start=False,
    contract_receipts={k: v['receipt_sha256'] for k, v in b.items()},
    source_sha256=source,
  )
  prior = d['readiness']
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
      'stage2_residual_risk',
    )
  }
  b['readiness'] = sealed(
    'readiness',
    status=READY,
    states=STATES,
    model_strategy=b['reuse']['model_strategy'],
    stage1_refit='FORBIDDEN',
    stage2_refit='FORBIDDEN',
    normalizer_refit='FORBIDDEN',
    train_prediction_strategy=b['train']['strategy'],
    stage2_train_prediction_population=b['stage2']['population'],
    threshold_policy=design.POLICY,
    development='SAME_ANCHORS_NEW_V2_GATE',
    rollout='SAME_ANCHORS_NEW_V2_GATE',
    acceptance='UNCHANGED_V1_GATE',
    selection='UNCHANGED_V1_RULE',
    private_access=0,
    actual_execution='NOT_RUN',
    actual_v2_threshold='NOT_COMPUTED',
    path_discovery=0,
    private_manifest_opening=0,
    holdout_discovery=0,
    execution_states=dict.fromkeys(
      (
        'V2_STAGE1_REFIT',
        'V2_STAGE2_REFIT',
        'V2_TRAIN_PREDICTION_REPLAY',
        'V2_THRESHOLD_SELECTION',
        'V2_DEVELOPMENT_PREDICTION',
        'V2_ROLLOUT',
        'V2_CV_SCORING',
        'V2_MODEL_SELECTION',
      ),
      'NOT_RUN',
    ),
    V2_PRIVATE_SOURCE_ACCESS=0,
    next_increment=b['policy']['next_increment'],
    next_increment_status='REQUIRES_SEPARATE_AUTHORIZATION',
    policy_sha256=b['policy']['receipt_sha256'],
    **preserved,
  )
  b['validation'] = sealed(
    'validation',
    status='PUBLIC_EXECUTION_POLICY_AND_SHA_CHAIN_VALIDATED',
    source_sha256=source,
    input_pins=PINS,
    artifact_receipts={k: v['receipt_sha256'] for k, v in b.items()},
    private_access=0,
    actual_execution='NOT_RUN',
    actual_threshold='NOT_COMPUTED',
    checks=[
      'EXACT_PUBLIC_REFERENCE_CHAIN',
      'BYTE_IDENTICAL_MODEL_REUSE',
      'NO_REFIT',
      'STAGE2_ALL_TRAIN',
      'TRAIN_ONLY',
      'SAME_ANCHORS',
      'UNCHANGED_GATES_SELECTION',
      'REPORT_ONLY_COMPARISON',
      'D_ONLY_COMPACT_STORAGE',
      'EXACT_REPEATABILITY',
      'VERIFY_ONLY_RESUME',
      'NO_PRIVATE_DISCOVERY_OR_EXECUTOR_API',
    ],
    regression_evidence='CHANGE_RECORD_VALIDATION_SECTION',
    preservation='TRACKED_HISTORICAL_INPUTS_UNCHANGED_PRIVATE_NOT_ACCESSED_NO_GLOBAL_BYTE_CLAIM',
  )
  return {filename(k): v for k, v in b.items()}


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
  except (ValueError, KeyError, TypeError) as exc:
    raise ValueError(CONFLICT) from exc


def publish(output):
  root = design.safe(output)
  bundle = validate(build())
  encoded = {n: json.dumps(v, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n' for n, v in bundle.items()}
  for name, data in encoded.items():
    for target in (root / name, root / (name + '.atomic')):
      path = design.safe(target)
      if path.exists() and (not path.is_file() or path.read_bytes() != data):
        raise ValueError('HURDLE_STAGE1_V2_EXECUTION_IMMUTABLE_OUTPUT_CONFLICT')
  for name in sorted(bundle, key=lambda n: (n == filename('validation'), n)):
    p.persist(design.safe(root / name), bundle[name])
  return bundle


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', required=True, type=Path)
  args = parser.parse_args()
  bundle = publish(args.output)
  print(json.dumps({'status': READY, 'artifacts': len(bundle), 'private_access': 0, 'actual_execution': 'NOT_RUN'}))


if __name__ == '__main__':
  main()
