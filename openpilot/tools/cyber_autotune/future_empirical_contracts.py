"""Future-only empirical data contracts. No data discovery or model execution."""

import json
from functools import lru_cache
from copy import deepcopy
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_grid_publication as grid

BASELINE = '46e41ad2f2e11cd4aee926b47d037c46d226108c'
REQUIRED_MESSAGES = ('initData', 'carParams', 'carState', 'carOutput', 'carControl')
SIGNAL_FIELDS = (
  'requested_torque',
  'normalized_torque',
  'raw_command',
  'runtime_steer_max',
  'steeringAngleDeg',
  'steeringRateDeg',
  'steeringPressed',
  'driver_torque',
  'eps_temporary_fault',
  'eps_permanent_fault',
  'eps_status',
  'vEgo',
  'wheel_speeds',
  'gear',
  'latActive',
  'yaw_raw',
  'gyro_xyz',
  'gyro_source',
  'lateral_acceleration',
  'state_time_ns',
  'command_time_ns',
  'control_time_ns',
  'sensor_acquisition_time_ns',
  'sensor_publish_time_ns',
)
REQUIRED_STAGE_A_FIELDS = (
  'requested_torque',
  'normalized_torque',
  'raw_command',
  'runtime_steer_max',
  'steeringAngleDeg',
  'steeringRateDeg',
  'steeringPressed',
  'driver_torque',
  'eps_temporary_fault',
  'eps_permanent_fault',
  'vEgo',
  'gear',
  'latActive',
  'state_time_ns',
  'command_time_ns',
  'control_time_ns',
)
NAMES = (
  'future-empirical-generation-policy-v1.json',
  'empirical-causal-context-schema-v2.json',
  'future-route-admission-v1.json',
  'future-route-role-assignment-v1.json',
  'future-holdout-opening-contract-v1.json',
  'future-model-family-readiness-v1.json',
  'future-empirical-data-readiness-v1.json',
)


@lru_cache(maxsize=32)
def _verified(data):
  return p.verify(json.loads(data))


def read(name):
  return deepcopy(_verified((p.PUBLIC / name).read_bytes()))


def history_sha():
  return read('empirical-dataset-v2-cross-root-inventory-v1.json')['receipt_sha256']


def history_private_sha():
  return read('empirical-dataset-v2-cross-root-inventory-v1.json')['private_inventory_sha256']


def history_bindings():
  data = (p.PUBLIC / 'empirical-dataset-v2-cross-root-inventory-v1.json').read_bytes()
  return _history_bindings(data).copy()


@lru_cache(maxsize=4)
def _history_bindings(data):
  return {row['route_id']: row['identity_receipt_sha256'] for row in _verified(data)['routes']}


def known_profiles():
  data = (p.PUBLIC / 'empirical-source-route-reclassification-v1.json').read_bytes()
  return deepcopy(_profiles(data))


@lru_cache(maxsize=4)
def _profiles(data):
  return [{key: row[key] for key in ('semantic_class_id', 'empirical_profile_sha256', 'full_carparams_sha256')} for row in _verified(data)['pools']['pools']]


def known_sources():
  names = ('empirical-source-equivalence-classes-v1.json', 'empirical-source-semantic-fingerprints-v1.json', 'empirical-source-route-reclassification-v1.json')
  return deepcopy(_known(tuple((p.PUBLIC / name).read_bytes() for name in names)))


@lru_cache(maxsize=4)
def _known(snapshot):
  classes, sources, routes = (_verified(data) for data in snapshot)
  adapters = routes['execution_binding']['adapters']
  return [
    {
      'commit': commit,
      'class_sha256': group['class_id'],
      'fingerprint_sha256': next(x['receipt_sha256'] for x in sources['fingerprints'] if x['commit'] == commit),
      'adapter_sha256': adapters[commit]['receipt_sha256'],
    }
    for group in classes['classes']
    if group['status'] == 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENT'
    for commit in group['members']
    if commit in adapters
  ]


def generation_policy():
  ready = read(grid.READY)
  if ready['receipt_sha256'] != grid.PINS[grid.READY]:
    raise ValueError('FINALIZED_CLOSURE_PIN_DRIFT')
  return p.seal(
    {
      'schema': 'FUTURE_EMPIRICAL_DATA_GENERATION_READINESS_POLICY_V1',
      'baseline': BASELINE,
      'closure': {
        'verdict': 'SOURCE_GRID_OBSERVATION_REJECTED',
        'track': 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
        'receipt_sha256': ready['receipt_sha256'],
        'no_model': 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
        'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
      },
      'scope': 'FUTURE_GENERATIONS_ONLY',
      'historical_regeneration_allowed': False,
      'numeric_extraction_allowed': False,
      'model_implementation_allowed': False,
      'model_fitting_allowed': False,
      'model_selection_allowed': False,
      'holdout_opening_allowed': False,
      'background_automation_allowed': False,
      'timebase': {
        'dt_ns': 10_000_000,
        'max_age_ns': 20_000_000,
        'method': 'LATEST_PAST_ONLY_NO_INTERPOLATION',
        'duplicate_or_regressing_clock': 'REJECT',
        'boundary': 'NO_ROUTE_SEGMENT_RUN_MASK_OR_SPEED_BIN_HISTORY_CROSSING',
      },
      'speed_bins': [['LOW', 5, 15], ['MEDIUM', 15, 25], ['HIGH', 25, None]],
      'minimum_support': 201,
      'source_template': {
        'status': 'SOURCE_AUDIT_PENDING',
        'exact_commit_required': True,
        'automatic_current_source_admission': False,
        'required': [
          'origin',
          'commit',
          'dirty_attestation',
          'logger_schema',
          'command_path',
          'CarState_DBC',
          'sensor_producer_units_axes_clocks',
          'CarParams_profile',
          'runtime_STEER_MAX',
          'reviewed_scoped_equivalence',
          'adapter',
        ],
        'outcomes': ['SOURCE_EQUIVALENT', 'SOURCE_ADAPTER_REQUIRED', 'SOURCE_INCOMPATIBLE', 'SOURCE_AUDIT_PENDING'],
      },
      'known_scoped_sources': known_sources(),
      'known_full_profiles': known_profiles(),
      'history_inventory_sha256': history_sha(),
      'source_signal_matrix_sha256': read('empirical-source-signal-matrix-v1.json')['receipt_sha256'],
      'executor_sha256': {
        name: p.sha(Path(__file__).with_name(name).read_bytes())
        for name in ('future_empirical_contracts.py', 'future_empirical_admission.py', 'future_empirical_context.py', 'future_empirical_cli.py')
      },
      'calibration_blockers': p.BLOCKERS,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle': 'VEHICLE_ACTIVATION_BLOCKED',
    }
  )


def context_schema():
  identity = (
    'generation',
    'route_id',
    'segment_receipt_sha256',
    'aligned_row_index',
    'run_id',
    'within_run_index',
    'design_row_index',
    'source_commit',
    'profile_sha256',
    'adapter_sha256',
    'policy_sha256',
    'role_receipt_sha256',
  )
  context = (
    'command_history',
    'angle_history',
    'command_at_rail',
    'requested_post_limit_difference',
    'safety_limited',
    'curvature_limited',
    'speed_bin',
    'active',
    'intervention_boundary',
    'mask_reasons',
    'gap_boundary',
    'prediction_time_ns',
    'grid_time_ns',
    'source_age_ns',
  )
  return p.seal(
    {
      'schema': 'EMPIRICAL_CAUSAL_CONTEXT_SCHEMA_V2',
      'base_sha256': read('empirical-causal-context-schema-v1.json')['receipt_sha256'],
      'scope': 'FUTURE_GENERATIONS_ONLY',
      'historical_regeneration_allowed': False,
      'fields': list(identity) + list(SIGNAL_FIELDS) + list(context),
      'actual_steeringRateDeg': 'PRESERVE_SAMPLE_VALUE_NOT_FINITE_COUNT',
      'missing': 'NULL_NOT_FALSE_OR_ZERO',
      'publication': 'PRIVATE_ROWS_NEVER_PUBLISHED',
      'source_adapter': 'EXACT_SOURCE_SPECIFIC_NO_GENERIC_FALLBACK',
      'history': 'SAME_ROUTE_SEGMENT_RUN_ONLY_STRICT_PAST',
      'timing': 'STATE_STRICTLY_BEFORE_PREDICTION_COMMAND_CONTROL_NO_LATER_THAN_STATE_MAX_SOURCE_AGE_20MS',
      'forbidden': [
        'target',
        'future_target',
        'modelV2',
        'planner',
        'path',
        'lane',
        'liveCalibration',
        'cameraOdometry',
        'liveLocationKalman',
        'fused_pose',
        'human_reference',
        'detector',
        'candidate_result',
        'residual',
        'arx_win',
      ],
      'provenance': {
        'metadata_source_matrix_sha256': read('empirical-source-signal-matrix-v1.json')['receipt_sha256'],
        'command': 'LOGGED_POST_CARCONTROLLER_NOT_EPS_ACK_RUNTIME_SCALE_REQUIRES_FUTURE_VERIFICATION',
        'steeringAngleDeg': 'SAS11.SAS_Angle_STEP_POINT_ONE_DEG_FLOAT32',
        'steeringRateDeg': 'CARSTATE_SAS11.SAS_Speed_ACTUAL_SAMPLE_SCHEMA_DEG_PER_S_PHYSICAL_UNIT_REVIEW_REQUIRED',
        'yaw_raw': 'ESP12.YAW_RATE_DBC_UNIT_EMPTY_NO_UNIT_FRAME_PROMOTION',
        'gyro_xyz': 'SOURCE_PRODUCER_RAD_PER_S_DEVICE_AXES_NOT_VEHICLE_FRAME',
        'lateral_acceleration': 'NULL_UNTIL_SOURCE_UNIT_SIGN_FRAME_PROVEN',
        'safety_curvature_limits': 'UNKNOWN_REMAINS_NULL',
      },
      'numeric_execution_allowed': False,
    }
  )


def admission_contract():
  return p.seal(
    {
      'schema': 'FUTURE_ROUTE_ADMISSION_V1',
      'known_sources': known_sources(),
      'required_stage_a_field_presence': list(REQUIRED_STAGE_A_FIELDS),
      'identity': [
        'source_commit',
        'os_version',
        'vehicle_fingerprint',
        'full_carparams_sha256',
        'empirical_profile_sha256',
        'logger_start_sha256',
        'segments',
        'adapter_sha256',
        'source_class_sha256',
        'source_fingerprint_sha256',
        'envelopes',
        'prior_analysis',
        'numeric_opened',
      ],
      'metadata_reader': 'SOURCE_SPECIFIC_SEALED_METADATA_RECEIPTS_ONLY_NO_RAW_READER_IN_THIS_INCREMENT',
      'history_registry': 'COMPLETE_HASH_BOUND_PRIVATE_LOGGER_AND_SEGMENT_REGISTRY_REQUIRED',
      'directory_name_identity': False,
      'required_messages': list(REQUIRED_MESSAGES),
      'allowed_private_roots': ['CARROTLOG', 'CARROT_LOGS'],
      'root_aliases': 'EXACT_WINDOWS_WSL_ALIASES_SAME_STORAGE',
      'opening_allowed': False,
      'numeric_coverage': None,
    }
  )


def role_contract():
  return p.seal(
    {
      'schema': 'FUTURE_ROUTE_ROLE_ASSIGNMENT_V1',
      'roles': ['TRAIN', 'DEVELOPMENT', 'HOLDOUT', 'REJECTED', 'METADATA_ONLY_PENDING'],
      'order': ['METADATA', 'SOURCE_PROFILE', 'DISTINCTNESS', 'PRIOR_ANALYSIS', 'ASSIGN', 'IMMUTABLE_RECEIPT', 'FUTURE_AUTHORIZED_OPENING'],
      'minimum_routes': 3,
      'preferred_routes': 5,
      'allocation': 'LEXICAL_WHOLE_ROUTE_FLOOR_60_20_REMAINDER_MIN_ONE_EACH',
      'one_route_one_role': True,
      'history_splitting_allowed': False,
      'quality_based_reassignment': False,
      'role_receipt_overwrite_allowed': False,
      'numeric_opening_allowed': False,
    }
  )


def holdout_contract():
  return p.seal(
    {
      'schema': 'FUTURE_HOLDOUT_OPENING_CONTRACT_V1',
      'base_sha256': read('future-empirical-holdout-admission-v1.json')['receipt_sha256'],
      'default': 'CLOSED',
      'opening_allowed': False,
      'one_time': True,
      'unknown_requirement_passes': False,
      'requirements': [
        'NEW_LOGGER_IDENTITY',
        'COMPLETE_DISTINCT_LINEAGE',
        'EXACT_SOURCE_PROFILE_ADAPTER',
        'NUMERIC_PREVIOUSLY_UNOPENED',
        'NO_PRIOR_ANALYSIS',
        'ROLE_RECEIPT_BEFORE_NUMERIC',
        'REQUIRED_MESSAGES',
        'FROZEN_FAMILY_CONFIG_MODEL_METRICS_SUPPORT',
        'ONE_TIME_OPENING_RECEIPT',
        'SEPARATE_EXPLICIT_AUTHORIZATION',
      ],
      'after_opening': ['NO_REFIT', 'NO_RESELECTION', 'NO_THRESHOLD_CHANGE', 'NO_FAMILY_CHANGE'],
      'actual_opening': 'NOT_IMPLEMENTED_OR_AUTHORIZED_HERE',
    }
  )


def families():
  return p.seal(
    {
      'schema': 'FUTURE_MODEL_FAMILY_READINESS_V1',
      'implementation_allowed': False,
      'fitting_allowed': False,
      'selection': 'NOT_RUN',
      'families': [
        {
          'family': 'S1',
          'name': 'SECOND_ORDER_LATENT_STATE_SPACE',
          'rationale': 'Separate angle and rate dynamics from quantized observation',
          'fields': ['raw_command', 'steeringAngleDeg', 'steeringRateDeg', 'vEgo'],
          'states': ['angle', 'rate'],
          'reset': 'NEW_ROUTE_SEGMENT_RUN_INTERVENTION_POLICY_MUST_BE_FROZEN',
          'parameter_count': 'UNFROZEN_A_2X2_B_2X1_PLUS_OBSERVATION_AND_BIAS_CHOICES',
          'failure_modes': ['pole instability', 'quantized measurement bias', 'closed-loop identification bias'],
          'fitting_complexity': 'small constrained linear/state estimation; method not selected',
          'holdout_risk': 'route transfer and recursive drift',
        },
        {
          'family': 'S2',
          'name': 'DELTA_ANGLE_CAUSAL_MODEL',
          'rationale': 'Model motion separately from unchanged quantized samples',
          'fields': ['command_history', 'steeringRateDeg', 'vEgo', 'angle_history'],
          'states': ['past motion'],
          'reset': 'NO_CROSS_ROUTE_SEGMENT_RUN_HISTORY',
          'parameter_count': 'UNFROZEN_DEPENDS_ON_FUTURE_TAP_POLICY',
          'failure_modes': ['integrated bias', 'incorrect derivative timing', 'deadzone ambiguity'],
          'fitting_complexity': 'low-order regression; tap count not selected',
          'holdout_risk': 'accumulated angle drift',
        },
        {
          'family': 'S3',
          'name': 'BOUNDED_PIECEWISE_AFFINE_ACTUATOR',
          'rationale': 'Potential source-defined deadzone/hysteresis mechanism',
          'fields': ['raw_command', 'steeringRateDeg', 'vEgo', 'source_proven_deadzone_hysteresis'],
          'states': ['source-defined regime memory'],
          'reset': 'FUTURE_SOURCE_BOUND_RESET_REQUIRED',
          'parameter_count': 'UNFROZEN_NO_REGIME_COUNT_OR_BOUNDARIES_SELECTED',
          'failure_modes': ['switch chatter', 'unsupported physical deadzone', 'overfit regimes'],
          'fitting_complexity': 'bounded small affine fits only after source mechanism audit',
          'holdout_risk': 'rare regime coverage',
        },
      ],
    }
  )


def artifacts():
  pol = generation_policy()
  ready = p.seal(
    {
      'schema': 'FUTURE_EMPIRICAL_DATA_READINESS_V1',
      'policy_sha256': pol['receipt_sha256'],
      'states': [
        'FUTURE_EMPIRICAL_DATA_PIPELINE_READY',
        'EMPIRICAL_CAUSAL_CONTEXT_V2_DEFINED',
        'FUTURE_ROUTE_ADMISSION_READY',
        'FUTURE_HOLDOUT_CONTRACT_READY',
        'NO_NEW_ROUTE_ADMITTED',
        'NO_NUMERIC_EXTRACTION',
        'NO_MODEL_FITTING',
        'NO_MODEL_SELECTED',
        'HOLDOUT_OPENING_CLOSED',
        'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      ],
      'scope': 'CONTRACT_AND_SYNTHETIC_VALIDATION_READY_NOT_RAW_EXTRACTOR_OR_MODEL_READINESS',
      'new_route_count': 0,
      'numeric_coverage': None,
      'fitting': 'NOT_RUN',
      'selection': 'NOT_RUN',
      'holdout_opening': 'CLOSED',
      'model_package': 'CLOSED_MISSING_ADMISSIBLE_MODEL',
      'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
      'calibration_blockers': p.BLOCKERS,
    }
  )
  return dict(zip(NAMES, (pol, context_schema(), admission_contract(), role_contract(), holdout_contract(), families(), ready), strict=True))
