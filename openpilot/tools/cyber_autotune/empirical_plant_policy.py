"""Read-only empirical identification policies; raw evidence is private."""

from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re

PUBLIC = Path(__file__).resolve().parents[3] / 'docs/cyberpilot/changes'
FIREWALL = {
  'qualification_allowed': False,
  'reference_promotable': False,
  'sealed_reference_allowed': False,
  'vehicle_activation_allowed': False,
  'production_authority': False,
  'ta_execution': False,
  'sg_execution': False,
  'composition_authorized': False,
  'candidate_search_authorized': False,
  'publication_raw_data': False,
}
BLOCKERS = [
  'CALIBRATION_UNCERTAINTY_PENDING',
  'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
  'PIXEL_GEOMETRY_REGISTRATION_PENDING',
  'METRIC_CALIBRATION_UNAVAILABLE',
  'INDEPENDENT_REFERENCE_UNAVAILABLE',
]


def canonical(row):
  return json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
  return hashlib.sha256(data).hexdigest()


def seal(row):
  body = {**row, **FIREWALL}
  return {**body, 'receipt_sha256': sha(canonical(body))}


def verify(row):
  if type(row) is not dict or row.get('receipt_sha256') != sha(canonical({k: v for k, v in row.items() if k != 'receipt_sha256'})):
    raise ValueError('EMPIRICAL_RECEIPT_CORRUPT')
  if any(row.get(k) is not v for k, v in FIREWALL.items()):
    raise ValueError('EMPIRICAL_AUTHORITY_FIREWALL')
  return row


def persist(path, row):
  verify(row)
  path = Path(path)
  if any(part.is_symlink() for part in (path, *path.parents)):
    raise ValueError("NO_SYMLINK_STORE")
  path.parent.mkdir(parents=True, exist_ok=True)
  if path.is_symlink():
    raise ValueError('NO_SYMLINK_STORE')
  if path.exists():
    if json.loads(path.read_bytes()) != row:
      raise ValueError('IMMUTABLE_RECEIPT_CONFLICT')
    return
  temporary = path.with_name(path.name + '.atomic')
  if temporary.is_symlink():
    raise ValueError('NO_SYMLINK_STORE')
  if temporary.exists():
    try:
      old = verify(json.loads(temporary.read_bytes()))
    except (ValueError, TypeError, KeyError) as e:
      raise ValueError('CORRUPT_ATOMIC_RECEIPT') from e
    if old != row:
      raise ValueError('STALE_ATOMIC_RECEIPT')
    os.link(temporary, path)
    temporary.unlink()
    return
  with temporary.open('xb') as f:
    f.write(json.dumps(row, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n')
    f.flush()
    os.fsync(f.fileno())
  os.link(temporary, path)
  temporary.unlink()


def policy():
  return seal(
    {
      'schema': 'EMPIRICAL_PLANT_DATA_POLICY_V1',
      'dt_ns': 10_000_000,
      'max_age_ns': 20_000_000,
      'alignment': 'INTEGER_GRID_LATEST_PAST_ONLY_NO_INTERPOLATION',
      'duplicates': 'REJECT_SEGMENT',
      'gaps': 'MASK_AND_BREAK_ALL_HISTORY',
      'boundaries': 'NO_SEGMENT_OR_MASK_CROSSING',
      'minimum_speed_mps': 5.0,
      'speed_bins': [['LOW', 5.0, 15.0], ['MEDIUM', 15.0, 25.0], ['HIGH', 25.0, None]],
      'speed_basis': 'PREDECLARED_ROUND_MPS_REGIMES_NOT_RESULT_SELECTED',
      'allowed_payloads': ['initData', 'carParams', 'carState', 'carOutput', 'carControl', 'pandaStates'],
      'forbidden_payloads': [
        'modelV2',
        'liveCalibration',
        'livePose',
        'cameraOdometry',
        'lateralPlan',
        'gpsLocationExternal',
        'gpsLocation',
        'roadCameraState',
        'narrowRoadCameraState',
      ],
      'mask': ['finite', 'valid', 'lat_active', 'no_driver_override', 'no_eps_fault', 'forward_drive', 'supported_command_domain'],
      'unobserved_limits': 'DIAGNOSTIC_MASK_ONLY_NO_CLEAN_PRIMARY_OR_READY',
      'command': 'carOutput.actuatorsOutput.torqueOutputCan',
      'command_units': 'SIGNED_RAW_CAN_AUTHORITY_NO_384_NORMALIZATION',
      'steering': 'carState.steeringAngleDeg',
      'steering_units': 'DEGREES_SOURCE_SAS11',
      'yaw': 'SOURCE_PROVEN_UNIT_AND_FRAME_REQUIRED_OTHERWISE_STAGE_BLOCKED',
      'rollouts_samples': [25, 50, 100, 200],
      'residual_lags': list(range(1, 21)),
      'minimum_support': 'MAX_201_OR_10_TIMES_PARAMETER_COUNT',
      'solver': 'NUMPY_LSTSQ_RCOND_NONE_FLOAT64_SINGLE_BLAS_THREAD',
      'repeatability': 'TWO_EXACT_RUNS_HOLDOUT_ONE_OPENING_NO_RESELECTION',
      'holdout_payload_gate': 'MODEL_FROZEN_RECEIPT_REQUIRED',
      'calibration_blockers': BLOCKERS,
      'historical': {
        'current': 'BASELINE_EXACT',
        'v1': 'TRADEOFF_ONLY',
        'v2': 'REJECTED',
        'v2_violations': 37,
        'ta': 'TA_STANDALONE_TRADEOFF_ONLY',
        'sg': 'SG_CLOSED_LOOP_TRADEOFF_ONLY',
      },
      'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
    }
  )


def family_policy():
  return seal(
    {
      'schema': 'EMPIRICAL_PLANT_FAMILY_POLICY_V1',
      'candidates': [
        {'family': family, 'delay_samples': delay, 'input_taps': 1 if family == 'ARX1' else 25, 'output_lags': 1 if family == 'ARX1' else 0, 'intercept': True}
        for family in ('ARX1', 'FIR25')
        for delay in (0, 5, 10, 20)
      ],
      'maximum_candidates': 8,
      'regularization': None,
      'training': 'TRAIN_ONLY',
      'selection': 'DEVELOPMENT_RMSE_THEN_PARAMETER_COUNT_THEN_FAMILY_DELAY',
      'pole_gate': 'ABS_POLE_STRICTLY_LESS_THAN_ONE',
      'holdout_reselection': False,
      'naive': ['ZERO_RESPONSE', 'HOLD_LAST_OUTPUT', 'TRAIN_STATIC_GAIN'],
      'closed_loop_bias': 'OLS_NOT_CAUSAL_INTERVENTION_OR_PHYSICAL_TRUTH',
    }
  )


def inventory(root):
  root = Path(root).resolve(strict=True)
  rows, types = [], Counter()
  for path in sorted(root.rglob('*')):
    if path.is_symlink():
      raise ValueError('PRIVATE_SOURCE_SYMLINK')
    if not path.is_file():
      continue
    types[path.name] += 1
    if path.name != 'rlog.zst':
      continue
    match = re.fullmatch(r'(.+)--([0-9]+)', path.parent.name)
    if not match:
      raise ValueError('UNKNOWN_SEGMENT_STRUCTURE')
    relative = path.relative_to(root).as_posix()
    route = str(path.parent.parent.relative_to(root)) + '/' + match[1]
    rows.append(
      {
        'route_id': sha(route.encode()),
        'ordinal': int(match[2]),
        'segment_id': sha(str(path.parent.relative_to(root)).encode()),
        'source_sha256': sha(path.read_bytes()),
        'bytes': path.stat().st_size,
        'source_key': relative,
      }
    )
  return seal({'schema': 'EMPIRICAL_PRIVATE_INVENTORY_V1', 'root': str(root), 'file_types': dict(types), 'segments': rows, 'image_or_video_opened': False})


def split(rows):
  required = {'route_id', 'ordinal', 'segment_id', 'source_sha256', 'bytes', 'source_key'}
  seen, routes = set(), defaultdict(list)
  for row in rows:
    if set(row) != required or row['segment_id'] in seen or type(row['ordinal']) is not int or row['ordinal'] < 0:
      raise ValueError('EXACT_UNIQUE_METADATA_ONLY')
    seen.add(row['segment_id'])
    routes[row['route_id']].append(row)
  blocks = []
  for route, members in sorted(routes.items()):
    members = sorted(members, key=lambda r: r['ordinal'])
    if len({r['ordinal'] for r in members}) != len(members):
      raise ValueError('DUPLICATE_ORDINAL')
    for start in range(0, len(members), 10):
      group = members[start : start + 10]
      key = sha(canonical({'route': route, 'ordinals': [r['ordinal'] for r in group]}))
      blocks.append((key, group))
  ordered = sorted(blocks)
  n = len(ordered)
  roles = ['TRAIN'] * (n * 6 // 10) + ['DEVELOPMENT'] * (n * 2 // 10) + ['HOLDOUT'] * (n - n * 6 // 10 - n * 2 // 10)
  assignments = []
  for (block_id, group), role in zip(ordered, roles, strict=True):
    for i, row in enumerate(group):
      assignments.append({**row, 'block_id': block_id, 'role': 'EMBARGO' if i in (0, len(group) - 1) else role})
  return seal(
    {
      'schema': 'EMPIRICAL_PLANT_SPLIT_V1',
      'method': 'HASH_SORT_TEN_SEGMENT_TEMPORAL_BLOCKS_EDGE_EMBARGO',
      'fractions_by_block': [0.6, 0.2, 0.2],
      'route_independent': False,
      'block_count': n,
      'split_before_numeric_inspection': True,
      'segments': sorted(assignments, key=lambda r: (r['route_id'], r['ordinal'])),
    }
  )


def metric_policy():
  return seal(
    {
      'schema': 'EMPIRICAL_PLANT_METRIC_EXECUTION_POLICY_V1',
      'common_history_samples': 45,
      'selection_target': 'ONE_STEP_OUTPUT_RMSE',
      'aggregation': 'POOLED_SSE_AND_COUNT_NO_SEGMENT_WEIGHT',
      'selection_scope': 'SEPARATE_STAGE_AND_SPEED_BIN',
      'common_support': 'ALL_45_HISTORY_SAMPLES_VALID_SAME_SEGMENT_SAME_BIN',
      'candidate_unstable': 'EXCLUDE_AND_REPORT_NO_HOLDOUT_RESELECTION',
      'minimum_samples': 201,
      'rank': 'FULL_COLUMN_RANK_REQUIRED',
      'one_step': ['MAE', 'RMSE', 'MEDIAN_ABS', 'P95_ABS', 'BIAS', 'CORRELATION'],
      'quantile': 'NUMPY_LINEAR',
      'rollout_samples': [25, 50, 100, 200],
      'rollout_origins': 'EVERY_COMMON_SUPPORT_INDEX_WITH_COMPLETE_VALID_HORIZON',
      'rollout_metric': 'ENDPOINT_OUTPUT_RESIDUAL_AFTER_H_RECURSIVE_STEPS',
      'rollout_input': 'OBSERVED_EXOGENOUS_COMMAND_OVER_HORIZON_NOT_FEEDBACK_TO_MODEL',
      'rollout_initialization': 'OBSERVED_HISTORY_ONCE_THEN_RECURSIVE_PREDICTED_OUTPUT',
      'ready_primary_horizon_samples': 100,
      'ready_primary_metrics': ['MAE', 'RMSE', 'P95_ABS'],
      'ready_rule': 'STRICTLY_BETTER_THAN_EACH_NAIVE_ON_ONE_STEP_AND_100_STEP_ENDPOINT_COMMON_SUPPORT',
      'ready_other_gates': ['MEASURED_UNITS_FRAME_PROVEN', 'CLEAN_LIMIT_MASK_OBSERVABLE', 'EXACT_REPEATABILITY', 'STABLE_MODEL', 'SUPPORT_201_MINIMUM'],
      'correlation_constant': 'NULL_WITH_SUPPORT_COUNT',
      'amplitude_subsets': 'INPUT_ZERO_POSITIVE_NEGATIVE_AND_TRAIN_ABS_QUARTILES',
      'time_blocks': 'FOUR_EQUAL_INDEX_BLOCKS_PER_SEGMENT_NO_POSTHOC_SELECTION',
      'unavailable': 'NULL_NEVER_ZERO_OR_IMPUTED',
      'physical_delay_interpretation': 'INCLUDES_SOURCE_PUBLISH_ALIGNMENT_AGE_NOT_PHYSICAL_DELAY_TRUTH',
    }
  )


def alignment_policy():
  return seal(
    {
      'schema': 'EMPIRICAL_PLANT_ALIGNMENT_POLICY_V1',
      'grid': '100HZ_INTEGER_NS',
      'target': 'LATEST_PAST_CARSTATE_PUBLISH_EVENT',
      'command_context_query': 'TARGET_SELECTED_EVENT_TIME_NOT_GRID_TIME',
      'forbid_command_after_target_event': True,
      'save_actual_selected_event_times': True,
      'age_bound_ns': 20_000_000,
      'repeated_output_event': 'MASK_NOT_NEW_MEASUREMENT',
      'source_gap': 'SELECTED_EVENT_PREDECESSOR_DELTA_GT_20MS_MASK_AND_HISTORY_BREAK',
      'duplicates_or_regression': 'REJECT_SEGMENT',
      'sensor_measurement_time': 'NOT_IDENTIFIED_PUBLISH_CLOCK_ONLY',
      'delay': 'PUBLISH_TIME_EMPIRICAL_LAG_NOT_PHYSICAL_DELAY_VALIDATION',
    }
  )
