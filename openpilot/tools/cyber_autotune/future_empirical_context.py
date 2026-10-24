"""Synthetic future extractor contract validator; no reader or persisted samples."""

import math
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import future_empirical_contracts as c
from openpilot.tools.cyber_autotune import future_empirical_admission as a

IDENTITY = ('route_id', 'segment_receipt_sha256', 'run_id', 'profile_sha256', 'adapter_sha256', 'policy_sha256', 'role_receipt_sha256')
INDICES = ('aligned_row_index', 'within_run_index', 'design_row_index')
TIMES = ('prediction_time_ns', 'grid_time_ns', 'state_time_ns', 'command_time_ns', 'control_time_ns', 'source_age_ns')
BOOLEANS = (
  'steeringPressed',
  'eps_temporary_fault',
  'eps_permanent_fault',
  'latActive',
  'active',
  'command_at_rail',
  'safety_limited',
  'curvature_limited',
  'intervention_boundary',
  'gap_boundary',
)
VECTORS = {'gyro_xyz': 3, 'wheel_speeds': 4}
TEXT = ('gear', 'gyro_source', 'eps_status', 'speed_bin')
NUMBERS = set(c.SIGNAL_FIELDS) | {'requested_post_limit_difference'}


def finite_number(value):
  return type(value) in (int, float) and math.isfinite(value)


def capture(values, roles):
  if roles is None:
    raise ValueError('ROLE_RECEIPT_BEFORE_CONTEXT')
  a.verify_roles(roles)
  schema = c.context_schema()
  if set(values) - set(schema['fields']):
    raise ValueError('CONTEXT_WHITELIST_FUTURE_TARGET_FIREWALL')
  row = dict.fromkeys(schema['fields'])
  row.update(values)
  if not isinstance(row['generation'], str) or not row['generation'].startswith('FUTURE_'):
    raise ValueError('FUTURE_ONLY_NO_HISTORICAL_REGENERATION')
  for key in IDENTITY:
    a.hash_required(row[key])
  if any(type(row[k]) is not int or row[k] < 0 for k in INDICES + TIMES):
    raise ValueError('EXACT_NONNEGATIVE_ROW_CLOCK_IDENTITY_REQUIRED')
  matches = [z for z in roles['routes'] if z['route_id'] == row['route_id']]
  if len(matches) != 1 or matches[0]['role'] not in ('TRAIN', 'DEVELOPMENT'):
    raise ValueError('ONLY_SYNTHETIC_TRAIN_DEV_CONTEXT_HOLDOUT_CLOSED')
  route = matches[0]
  expected = {
    'source_commit': route['source_commit'],
    'profile_sha256': route['empirical_profile_sha256'],
    'adapter_sha256': route['adapter_sha256'],
    'policy_sha256': c.generation_policy()['receipt_sha256'],
    'role_receipt_sha256': roles['receipt_sha256'],
  }
  if any(row[k] != v for k, v in expected.items()) or row['segment_receipt_sha256'] not in route['segment_receipts']:
    raise ValueError('CONTEXT_EXACT_SOURCE_PROFILE_ROUTE_SEGMENT_REQUIRED')
  state = row['state_time_ns']
  grid = row['grid_time_ns']
  target = row['prediction_time_ns']
  if not (
    row['command_time_ns'] <= state
    and row['control_time_ns'] <= state <= grid < target
    and grid % 10_000_000 == 0
    and grid - state == row['source_age_ns'] <= 20_000_000
    and grid - row['command_time_ns'] <= 20_000_000
    and grid - row['control_time_ns'] <= 20_000_000
  ):
    raise ValueError('LATEST_PAST_100HZ_NO_FUTURE_NO_GAP_INTERPOLATION')
  for key, value in row.items():
    if value is None or key in IDENTITY + INDICES + TIMES + ('generation', 'source_commit', 'command_history', 'angle_history', 'mask_reasons'):
      continue
    if key in BOOLEANS:
      if type(value) is not bool:
        raise ValueError('UNKNOWN_BOOL_MUST_BE_NULL')
    elif key in VECTORS:
      if type(value) is not list or len(value) != VECTORS[key] or not all(finite_number(v) for v in value):
        raise ValueError('FINITE_SOURCE_VECTOR_REQUIRED')
    elif key in TEXT:
      if type(value) is not str:
        raise ValueError('SOURCE_ENUM_REQUIRED')
    elif key in NUMBERS or key.endswith('_time_ns'):
      if not finite_number(value):
        raise ValueError('FINITE_SOURCE_VALUE_REQUIRED')
  if row['gyro_xyz'] is not None and (row['gyro_source'] is None or row['sensor_acquisition_time_ns'] is None or row['sensor_publish_time_ns'] is None):
    raise ValueError('DIRECT_GYRO_SOURCE_AND_CLOCKS_REQUIRED')
  if row['vEgo'] is not None and row['speed_bin'] is not None:
    speed = row['vEgo']
    expected = 'HIGH' if speed >= 25 else 'MEDIUM' if speed >= 15 else 'LOW' if speed >= 5 else None
    if row['speed_bin'] != expected:
      raise ValueError('EXACT_SPEED_BIN_POLICY')
  if row['sensor_acquisition_time_ns'] is not None or row['sensor_publish_time_ns'] is not None:
    acq, pub = row['sensor_acquisition_time_ns'], row['sensor_publish_time_ns']
    if type(acq) is not int or type(pub) is not int or not 0 <= acq <= pub <= state or pub - acq > 20_000_000 or grid - pub > 20_000_000:
      raise ValueError('GYRO_ACQUISITION_PUBLISH_ORDER_REQUIRED')
  for key in ('command_history', 'angle_history'):
    history = row[key]
    if history is None:
      continue
    if type(history) is not list:
      raise ValueError('EXPLICIT_HISTORY_REQUIRED')
    last = -1
    for h in history:
      if (
        set(h) != {'time_ns', 'value', 'route_id', 'segment_receipt_sha256', 'run_id'}
        or any(h[k] != row[k] for k in ('route_id', 'segment_receipt_sha256', 'run_id'))
        or type(h['time_ns']) is not int
        or not last < h['time_ns'] < state
        or not finite_number(h['value'])
      ):
        raise ValueError('CAUSAL_SAME_RUN_HISTORY_ONLY')
      last = h['time_ns']
  if row['mask_reasons'] is not None and (type(row['mask_reasons']) is not list or any(type(v) is not str for v in row['mask_reasons'])):
    raise ValueError('SOURCE_MASK_REASON_LIST_REQUIRED')
  return row


def eligibility(rows, roles):
  # Contract fixtures only. A future reader needs separate explicit authorization.
  from openpilot.tools.cyber_autotune import empirical_route_eligibility as existing

  captured = [capture(row, roles) for row in rows]
  aligned = []
  previous = None
  seen_scopes = set()
  for row in captured:
    scope = (row['route_id'], row['segment_receipt_sha256'])
    if previous is None or scope != (previous['route_id'], previous['segment_receipt_sha256']):
      if scope in seen_scopes:
        raise ValueError('GROUPED_ROUTE_SEGMENT_ORDER_NO_SCOPE_REENTRY')
      seen_scopes.add(scope)
    if previous and row['route_id'] == previous['route_id'] and row['segment_receipt_sha256'] == previous['segment_receipt_sha256']:
      if row['grid_time_ns'] <= previous['grid_time_ns'] or row['aligned_row_index'] <= previous['aligned_row_index']:
        raise ValueError('STRICTLY_INCREASING_SOURCE_ROWS_NO_REORDERING')
      sources = {
        'state_time_ns': (
          'steeringAngleDeg',
          'steeringRateDeg',
          'steeringPressed',
          'driver_torque',
          'eps_temporary_fault',
          'eps_permanent_fault',
          'vEgo',
          'gear',
        ),
        'command_time_ns': ('raw_command', 'normalized_torque', 'runtime_steer_max'),
        'control_time_ns': ('requested_torque', 'latActive'),
        'sensor_acquisition_time_ns': ('gyro_xyz', 'gyro_source'),
        'sensor_publish_time_ns': ('gyro_xyz', 'gyro_source', 'sensor_acquisition_time_ns'),
      }
      for clock, fields in sources.items():
        now, before = row[clock], previous[clock]
        if now is not None and before is not None:
          if now < before or (now == before and any(row[k] != previous[k] for k in fields)):
            raise ValueError('SOURCE_CLOCK_REGRESSION_OR_CHANGED_REUSED_SAMPLE')
    speed = row['vEgo']
    bucket = (
      'HIGH' if speed is not None and speed >= 25 else 'MEDIUM' if speed is not None and speed >= 15 else 'LOW' if speed is not None and speed >= 5 else None
    )
    observed = (
      row['latActive'] is True
      and row['steeringPressed'] is False
      and row['eps_temporary_fault'] is False
      and row['eps_permanent_fault'] is False
      and row['gear'] == 'drive'
      and row['raw_command'] is not None
      and row['steeringAngleDeg'] is not None
      and row['runtime_steer_max'] is not None
    )
    reasons = list(row['mask_reasons'] or [])
    for key in ('gap_boundary', 'intervention_boundary'):
      if row[key] is not False:
        reasons.append(key.upper() + '_OR_UNAVAILABLE')
    if row['mask_reasons'] is None:
      reasons.append('MASK_REASONS_UNAVAILABLE')
    if not observed:
      reasons.append('REQUIRED_CONTEXT_UNAVAILABLE_OR_INVALID')
    aligned.append(
      {
        'grid_time_ns': row['grid_time_ns'],
        'segment_id': p.sha(p.canonical([row[k] for k in ('route_id', 'segment_receipt_sha256', 'run_id')])),
        'diagnostic_valid': observed and not reasons,
        'speed_bin': bucket,
        'reasons': reasons,
        'gyro_common_valid': row['gyro_xyz'] is not None,
      }
    )
    previous = row
  return p.seal(
    {
      'schema': 'FUTURE_SYNTHETIC_CONTEXT_ELIGIBILITY_V1',
      'synthetic_contract_only': True,
      'available_samples': {key: sum(row[key] is not None for row in captured) for key in c.SIGNAL_FIELDS},
      'support': existing.support(aligned),
      'fitting_performed': False,
      'numeric_extraction_performed': False,
    }
  )
