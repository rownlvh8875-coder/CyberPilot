"""Frozen V2 eligibility policies. No fitting, controllers, or private access on import."""

from pathlib import Path
import re

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as s
from openpilot.tools.cyber_autotune import empirical_signal_policy as q

BASELINE = '03ea6ba14f3e96b2d4cee9164e27cfeca385cdf2'
CARPARAMS = '3023ff6a4b49a67d3b4a85d5494773c3e061c0046b7685983a9c7b6d72e153da'
V1_INVENTORY = 'f1deef34e80dfcc5ddda846e19ce5d5ac3659d86c983d0738370a32c1982ec39'
V1_METADATA = 'd40ec0d1d7d2eb80a776576a59a151f9b9cbfc421dad125dfb59afef4c2a9f62'
ROOT_IDENTITY_SHA256 = 'f3ef71cc0c27a7fe8b106c6f09d43645c6b3919d1bac994e980350e8598b66d9'
HASH = re.compile(r'[0-9a-f]{64}')
REQUIRED_SIGNALS = [
  'torque_output_can', 'normalized_output', 'requested_torque', 'steer_max_provenance',
  'steering_angle', 'steering_rate', 'steering_pressed', 'driver_torque', 'eps_status',
  'esp12_yaw', 'direct_gyro', 'gyro_acquisition_time', 'wheel_speeds',
  'lateral_acceleration', 'speed', 'lat_active', 'forward_gear',
  'safety_limit', 'curvature_limit', 'publish_time', 'wheelbase', 'steer_ratio',
]


def hash_required(value):
  if type(value) is not str or HASH.fullmatch(value) is None:
    raise ValueError('EXACT_OPAQUE_SHA256_REQUIRED')
  return value


def no_alias(path):
  path = Path(path)
  if any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('PATH_ALIAS_REJECTED')
  return path


def approved_root(path):
  # No root discovery outside this exact recorded allowlist.
  path = no_alias(path)
  if p.sha(str(path).encode()) != ROOT_IDENTITY_SHA256:
    raise ValueError('ROOT_NOT_EXPLICITLY_APPROVED')
  return path.resolve(strict=True)


def root_policy():
  return p.seal({
    'schema': 'EMPIRICAL_DATASET_V2_ROOT_POLICY',
    'root_count': 1, 'root_identity_sha256': ROOT_IDENTITY_SHA256,
    'aliases': 'WINDOWS_WSL_SAME_STORAGE_NOT_TWO_ROOTS',
    'explicit_sibling_roots': 0, 'parent_scan': False, 'network_scan': False,
    'maximum_directory_depth': 4,
    'metadata_payloads': ['initData', 'carParams'],
    'envelope_only_other_messages': True,
    'image_video_opened': False, 'numeric_signal_values_opened': False,
    'v1_inventory_sha256': V1_INVENTORY, 'v1_role': 'PLANNING_CONTEXT_ONLY',
  })


def expected_generation():
  return {
    'source_commit': s.RECORDED_COMMIT, 'fingerprint': 'HYUNDAI_SANTA_FE_2022',
    'carparams_sha256': CARPARAMS, 'control_type': 'torque',
    'flags': 65928, 'os_version': '19.8-carrot-bt1',
    'software_profile_sha256': p.sha(p.canonical({
      'source': s.RECORDED_COMMIT, 'carparams': CARPARAMS, 'os': '19.8-carrot-bt1',
    })),
  }


def compatible(generation):
  if type(generation) is not dict or set(generation) != set(expected_generation()):
    raise ValueError('EXACT_GENERATION_FIELDS_REQUIRED')
  return generation == expected_generation()


def homogeneity_policy():
  return p.seal({
    'schema': 'EMPIRICAL_DATASET_V2_HOMOGENEITY_POLICY',
    'generation': expected_generation(),
    'runtime_steer_max': 'SOURCE_DEFAULT_409_OR_EXPLICIT_SOURCE_BOUND_OVERRIDE_VERIFIED_NUMERICALLY',
    'other_commit_requires_separate_source_audit': True,
    'angle_control_allowed': False, 'canfd_allowed': False,
    'route_identity': ['source_commit', 'fingerprint', 'carparams_sha256', 'software_profile_sha256',
                       'logger_start_sha256', 'segment_lineage_sha256', 'monotonic_group_sha256'],
    'ambiguous_route_identity': 'BLOCK_NOT_SPLIT',
    'duplicate_content': 'ONE_SEGMENT_ONE_ROUTE', 'v1_overlap': 'EXCLUDE_ENTIRE_ROUTE',
  })


def split_policy():
  return p.seal({
    'schema': 'EMPIRICAL_DATASET_V2_SPLIT_POLICY', 'minimum_routes': 3,
    'method': 'SHA256_ROUTE_ID_SORT_WHOLE_ROUTES',
    'fractions': [0.6, 0.2, 0.2],
    'allocation': 'DEV_MAX_1_FLOOR_N_DIV_5_HOLDOUT_SAME_TRAIN_REMAINDER',
    'quality_based_reassignment': False, 'before_numeric_inspection': True,
    'v1_role': 'PLANNING_CONTEXT_ONLY', 'v1_numeric_reuse': False,
    'holdout': 'ONE_OPEN_AFTER_MODEL_UNIT_METRIC_SUPPORT_FREEZE',
  })


def split_routes(routes):
  seen = set()
  for row in routes:
    if set(row) != {'route_id', 'status', 'v1_overlap'}:
      raise ValueError('EXACT_ROUTE_SPLIT_FIELDS_REQUIRED')
    hash_required(row['route_id'])
    if row['v1_overlap'] is not False:
      raise ValueError('V1_ROUTE_EXCLUDED')
    if row['route_id'] in seen or row['status'] != 'ROUTE_METADATA_COMPATIBLE':
      raise ValueError('UNIQUE_COMPATIBLE_ROUTE_REQUIRED')
    seen.add(row['route_id'])
  if len(routes) < 3:
    return p.seal({'schema': 'EMPIRICAL_DATASET_V2_SPLIT', 'status': 'ROUTE_DISJOINT_SPLIT_UNAVAILABLE',
                   'routes': [], 'policy_sha256': split_policy()['receipt_sha256']})
  n = len(routes)
  dev = max(1, n // 5)
  roles = ['TRAIN'] * (n - 2 * dev) + ['DEVELOPMENT'] * dev + ['HOLDOUT'] * dev
  return p.seal({
    'schema': 'EMPIRICAL_DATASET_V2_SPLIT', 'status': 'EMPIRICAL_DATASET_V2_SPLIT_FROZEN',
    'policy_sha256': split_policy()['receipt_sha256'],
    'routes': [{'route_id': key, 'role': role} for key, role in zip(sorted(seen), roles, strict=True)],
  })


def eligibility_policy():
  return p.seal({
    'schema': 'EMPIRICAL_ROUTE_ELIGIBILITY_POLICY', 'minimum_design_rows': 201,
    'candidates': p.family_policy()['candidates'],
    'family_policy_sha256': p.family_policy()['receipt_sha256'],
    'yaw_hypothesis_policy_sha256': q.policy()['receipt_sha256'],
    'yaw_hypotheses': q.policy()['hypotheses'],
    'metric_policy_sha256': p.metric_policy()['receipt_sha256'],
    'alignment_policy_sha256': p.alignment_policy()['receipt_sha256'],
    'dt_ns': 10_000_000, 'maximum_age_ns': 20_000_000,
    'common_history_samples': 45, 'speed_bins': p.policy()['speed_bins'],
    'signals': REQUIRED_SIGNALS,
    'missing': 'NULL_NEVER_FALSE_OR_ZERO', 'mask_unknown_limits': 'DIAGNOSTIC_ONLY',
    'gyro_failure': 'GYRO_UNAVAILABLE_ROUTE_OTHER_SIGNALS_RETAINED',
    'wheel_crosscheck': 'SOURCE_UNIT_SIGN_TRACK_WIDTH_REQUIRED_SUPPORTING_ONLY',
    'lateral_accel_crosscheck': 'SOURCE_UNIT_SIGN_FRAME_REQUIRED_SUPPORTING_ONLY',
    'vehicle_frame': 'UNVERIFIED_NO_DEVICE_AXIS_PROMOTION',
    'model_fitting': False, 'candidate_execution': False,
    'calibration_blockers': p.BLOCKERS,
  })
