"""Additive provenance policies. No historical actuator re-fit or vehicle authority."""

import math
from pathlib import Path
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as s

EXTRA_SOURCE = [
  'opendbc_repo/opendbc/car/hyundai/interface.py',
  'opendbc_repo/opendbc/car/interfaces.py',
  'openpilot/common/params_keys.h',
  'openpilot/system/sensord/sensord.py',
  'openpilot/system/sensord/sensors/lsm6ds3_gyro.py',
]
GATES = ['unit_supported', 'frozen_selection', 'source_complete', 'split_disjoint', 'train_dev_support', 'untouched_role']


def policy():
  return p.seal(
    {
      'schema': 'EMPIRICAL_YAW_HYPOTHESIS_POLICY_V1',
      'hypotheses': ['YAW_H1', 'YAW_H2', 'YAW_H3', 'YAW_H4'],
      'gyro_candidates': [{'axis': axis, 'sign': sign, 'lag_samples': lag} for axis in range(3) for sign in [-1, 1] for lag in [0, 1, 2, 5, 10, 20]],
      'lag_samples': [0, 1, 2, 5, 10, 20],
      'dt_ns': 10_000_000,
      'max_age_ns': 20_000_000,
      'gyro_clock': 'BOTH_SENSOR_AND_PUBLISH_MUST_PRECEDE_TARGET_MINUS_LAG',
      'gyro_source': 'lsm6ds3_OR_lsm6ds3trc_ONLY_GYROUNCALIBRATED',
      'gyro_unit': 'SOURCE_PRODUCER_RAD_PER_S',
      'gyro_bias': 'NO_CORRECTION_REPORT_BIAS',
      'continuous_scale_fit': False,
      'selection': 'DEVELOPMENT_KINEMATIC_HYPOTHESIS_RMSE_THEN_NAME_GYRO_RMSE_THEN_AXIS_SIGN_LAG',
      'unit_support': 'TRAIN_AND_DEVELOPMENT_STRICT_COMMON_SUPPORT_RMSE_MAE_P95_UNIT_GROUP_DOMINANCE_GYRO_AND_KINEMATIC',
      'minimum_support': 201,
      'common_support': 'ALL_36_GYRO_OPTIONS_AVAILABLE_SAME_TARGET',
      'metrics': ['MAE', 'RMSE', 'MEDIAN_ABS', 'P95_ABS', 'BIAS', 'CORRELATION', 'SCALE_RATIO_RMS_DIAGNOSTIC_ONLY'],
      'residual_lags': list(range(1, 21)),
      'stationary_bias_estimation': 'NOT_APPLIED_UNCALIBRATED_SENSOR_BIAS_OPEN',
      'mask': 'VALID_FINITE_FORWARD_SPEED_GE5_NO_DRIVER_NO_EPS_FAULT_LATERAL_ACTIVE',
      'diagnostic_subsets': ['LOW_SPEED', 'DRIVER_PRESSED', 'EPS_FAULT', 'INACTIVE', 'LIMIT_UNKNOWN'],
      'speed_bins': p.policy()['speed_bins'],
      'kinematic': 'SPEED_OVER_WHEELBASE_TAN_STEERING_DEG_TO_RAD_OVER_STEER_RATIO',
      'angle_offset': 'NO_LEARNED_OFFSET_APPLIED_OFFSET_PROVENANCE_PENDING',
      'vehicle_frame': 'UNVALIDATED_DEVICE_CORRESPONDENCE_ONLY',
      'old_holdout': 'COMMAND_BRIDGE_ONLY_NEVER_YAW_SELECTION',
      'new_yaw_holdout': 'OLD_EMBARGO_NUMERIC_UNOPENED_BEFORE_THIS_POLICY_NO_ROUTE_INDEPENDENCE',
      'physical_rigid_transform': None,
      'stage_a': 'EMPIRICAL_ACTUATOR_MODEL_ONLY_STRICT_GATE_FAILED',
      'stage_c_allowed': False,
      'yaw_model_candidates': p.family_policy()['candidates'],
      'yaw_metric_policy_sha256': p.metric_policy()['receipt_sha256'],
      'yaw_model_input': 'MEASURED_STEERING_AND_SPEED_KINEMATIC_RAD_PER_S_REGRESSOR_NOT_TRUTH',
      'conditional_fit_gates': GATES,
      'calibration_blockers': p.BLOCKERS,
    }
  )


def split_roles(rows):
  mapping = {'TRAIN': 'TRAIN', 'DEVELOPMENT': 'DEVELOPMENT', 'HOLDOUT': 'COMMAND_BRIDGE_ONLY', 'EMBARGO': 'YAW_HOLDOUT'}
  if len({x['segment_id'] for x in rows}) != len(rows) or any(x['role'] not in mapping for x in rows):
    raise ValueError('EXACT_DISJOINT_HISTORICAL_ROLES_REQUIRED')
  return [{**x, 'original_role': x['role'], 'role': mapping[x['role']]} for x in rows]


def convert_yaw(value, hypothesis):
  if hypothesis not in ('YAW_H1', 'YAW_H2', 'YAW_H3', 'YAW_H4'):
    raise ValueError('ONLY_FOUR_DISCRETE_YAW_HYPOTHESES')
  factor = {'YAW_H1': math.pi / 180.0, 'YAW_H2': -math.pi / 180.0, 'YAW_H3': 1.0, 'YAW_H4': -1.0}[hypothesis]
  return value * factor


def yaw_verdict(gyro_available, unit_supported, common_support):
  if not gyro_available:
    return 'YAW_SIGNAL_UNUSABLE'
  if unit_supported and common_support:
    return 'YAW_UNIT_SUPPORTED_FRAME_PARTIAL'
  return 'YAW_UNIT_LIKELY_NOT_CONFIRMED'


def yaw_fit_allowed(gates):
  if type(gates) is not dict or set(gates) != set(GATES) or any(type(x) is not bool for x in gates.values()):
    raise ValueError('EXACT_YAW_FIT_GATES_REQUIRED')
  return all(gates.values())


def source_contract(root):
  prior = s.source_contract(root)
  root = Path(root)
  blobs = dict(prior['blobs'])
  for name in EXTRA_SOURCE:
    blob = subprocess.check_output(['git', '-c', f'safe.directory={root}', '-C', str(root), 'show', f'{s.RECORDED_COMMIT}:{name}'])
    if (root / name).read_bytes() != blob:
      raise ValueError('RECORDED_PROVENANCE_SOURCE_DRIFT')
    blobs[name] = p.sha(blob)
  return p.seal(
    {
      'schema': 'EMPIRICAL_PROVENANCE_SOURCE_V1',
      'repository': prior['repository'],
      'commit': s.RECORDED_COMMIT,
      'prior_source_sha256': prior['receipt_sha256'],
      'blobs': blobs,
      'default_steer_max_santa_fe_legacy': 409,
      'alt_limits_steer_max': 384,
      'runtime_override': 'CustomSteerMax_POSITIVE_REFRESH_EVERY_50_FRAMES',
      'command_relation': 'POST_OUTPUT_NORMALIZED_EQUALS_RAW_DIV_EFFECTIVE_STEER_MAX_FLOAT32_STORAGE',
      'request_linkage': 'CAROUTPUT_PUBLISHED_BEFORE_CURRENT_CONTROLS_UPDATE_PREVIOUS_OUTPUT',
      'yaw_dbc': {
        'start_bit': 40,
        'length': 13,
        'byte_order': 'LITTLE_ENDIAN',
        'signed': False,
        'scale': 0.01,
        'offset': -40.95,
        'minimum': -40.95,
        'maximum': 40.96,
        'unit': '',
      },
      'yaw_copy': 'ESP12_YAW_RATE_NO_CONVERSION',
      'gyro_conversion': 'SENSOR_RAW_8_75_MDPS_PER_COUNT_TIMES_PI_OVER_180',
      'gyro_axis_mapping': 'DEVICE_VECTOR_SENSOR_Y_NEG_SENSOR_X_SENSOR_Z',
      'gyro_frame': 'DEVICE_NOT_INDEPENDENTLY_VEHICLE_CALIBRATED',
      'wheelbase': 'CAR_SANTA_FE_SPECS_2_766_M_STATIC_PRIOR',
      'steer_ratio': 'CAR_SANTA_FE_SPECS_16_55_STATIC_PRIOR',
      'limitations': 'NO_PHYSICAL_UNIT_FROM_EMPTY_DBC_NO_RIGID_FRAME_ADMISSION',
    }
  )
