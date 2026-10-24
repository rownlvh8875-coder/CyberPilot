"""Whitelisted numeric provenance reader. No decoded media, fused pose or actuation."""

from bisect import bisect_right
import math

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_plant_signals as s
from openpilot.tools.cyber_autotune import empirical_signal_policy as q

SETTINGS = {'CustomSteerMax', 'CustomSteerDeltaUp', 'CustomSteerDeltaDown', 'CustomSteerDeltaUpLC', 'CustomSteerDeltaDownLC'}
STATE_FIELDS = {'time_ns', 'valid', 'speed_mps', 'angle_deg', 'driver_pressed', 'driver_torque', 'eps_fault', 'gear', 'yaw_raw'}


def effective_steer_max(profile, settings):
  if profile['steer_control_type'] != 'torque' or profile['flags'] & ((1 << 24) | (1 << 13)):
    raise ValueError('ONLY_SOURCE_BOUND_LEGACY_TORQUE_PROFILE')
  value = settings.get('CustomSteerMax')
  if value is not None and (type(value) is not int or value < 0):
    raise ValueError('EXACT_RECORDED_INTEGER_SETTING_REQUIRED')
  default = 384 if profile['flags'] & (1 << 4) else 409
  return (value if value is not None and value > 0 else default), value is not None


def command_bridge(rows, steer_max, runtime_setting_known):
  if type(steer_max) is not int or steer_max <= 0:
    raise ValueError('POSITIVE_SOURCE_BOUND_STEER_MAX_REQUIRED')
  if any(set(x) != {'raw', 'normalized', 'valid'} for x in rows):
    raise ValueError('EXACT_SAME_MESSAGE_COMMAND_PAIR_REQUIRED')
  valid = [x for x in rows if x['valid'] and math.isfinite(x['raw']) and math.isfinite(x['normalized'])]
  raw = np.asarray([x['raw'] for x in valid], dtype=np.float64)
  norm = np.asarray([x['normalized'] for x in valid], dtype=np.float64)
  expected = raw / steer_max
  residual = norm - expected
  exact = int(np.sum(norm == expected))
  rounded = int(np.sum(norm == expected.astype(np.float32).astype(np.float64)))
  signs = int(np.sum(np.sign(raw) != np.sign(norm)))
  domain = int(np.sum((abs(raw) > steer_max) | (abs(norm) > 1.0) | (raw != np.rint(raw))))
  if not len(valid):
    status = 'RAW_TO_NORMALIZED_COMMAND_UNAVAILABLE'
  elif rounded != len(valid) or signs or domain:
    status = 'RAW_TO_NORMALIZED_COMMAND_CONFLICT'
  else:
    status = 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED' if runtime_setting_known else 'RAW_TO_NORMALIZED_COMMAND_PARTIAL'
  return {
    'status': status,
    'total': len(rows),
    'eligible': len(valid),
    'invalid': len(rows) - len(valid),
    'steer_max': steer_max,
    'runtime_setting_known': runtime_setting_known,
    'exact_ratio_match_count': exact,
    'float32_expected_exact_count': rounded,
    'sign_conflicts': signs,
    'domain_conflicts': domain,
    'raw_saturated_count': int(np.sum(abs(raw) == steer_max)),
    'normalized_saturated_count': int(np.sum(abs(norm) == 1.0)),
    'residual': {**m.statistics(residual, expected), 'MAX_ABS': float(max(abs(residual))) if len(residual) else None},
    'mismatch_taxonomy': {'FLOAT32_RELATION': len(valid) - rounded, 'SIGN': signs, 'SOURCE_DOMAIN': domain, 'INVALID_OR_NONFINITE': len(rows) - len(valid)},
    'physical_applied_command_acknowledged': False,
  }


def validate_times(rows, key='time_ns'):
  times = [x[key] for x in rows]
  if any(type(x) is not int for x in times) or any(b <= a for a, b in zip(times, times[1:], strict=False)):
    raise ValueError('UNIQUE_INCREASING_SOURCE_TIME_REQUIRED')


def past_gyro(rows, target_ns, lag_samples):
  if lag_samples not in q.policy()['lag_samples']:
    raise ValueError('FROZEN_NONNEGATIVE_LAG_REQUIRED')
  query = target_ns - lag_samples * 10_000_000
  index = bisect_right([x['time_ns'] for x in rows], query) - 1
  if index < 0:
    return None
  row = rows[index]
  if row['sensor_ns'] > row['time_ns'] or not row['valid'] or not 0 <= query - row['time_ns'] <= 20_000_000 or not 0 <= query - row['sensor_ns'] <= 20_000_000:
    return None
  if index > 0 and (row['time_ns'] - rows[index - 1]['time_ns'] > 20_000_000 or row['sensor_ns'] - rows[index - 1]['sensor_ns'] > 20_000_000):
    return None
  return row if np.isfinite(row['xyz']).all() else None


def read_numeric(iterator, yaw_allowed):
  result = {'state': [], 'command': [], 'control': [], 'gyro': [], 'settings': [], 'gyro_rejected': 0}
  for event in iterator:
    kind = event.which()
    if kind not in ('initData', 'carState', 'carControl', 'carOutput', 'gyroscope') or (kind == 'gyroscope' and not yaw_allowed):
      continue
    if kind == 'initData':
      setting = {}
      for entry in event.initData.params.entries:
        if entry.key in SETTINGS:
          value = bytes(entry.value).decode('ascii')
          if not value.lstrip('-').isdigit():
            raise ValueError('RECORDED_CONTROL_SETTING_NOT_INTEGER')
          setting[entry.key] = int(value)
      result['settings'].append(setting)
      continue
    base = {'time_ns': int(event.logMonoTime), 'valid': bool(event.valid)}
    if kind == 'carState':
      x = event.carState
      result['state'].append(
        {
          **base,
          'speed_mps': float(x.vEgo),
          'angle_deg': float(x.steeringAngleDeg),
          'driver_pressed': bool(x.steeringPressed),
          'driver_torque': float(x.steeringTorque),
          'eps_fault': bool(x.steerFaultTemporary or x.steerFaultPermanent),
          'gear': str(x.gearShifter),
          'yaw_raw': float(x.yawRate) if yaw_allowed else None,
        }
      )
    elif kind == 'carOutput':
      x = event.carOutput.actuatorsOutput
      result['command'].append({**base, 'raw': float(x.torqueOutputCan), 'normalized': float(x.torque)})
    elif kind == 'carControl':
      x = event.carControl
      result['control'].append({**base, 'requested': float(x.actuators.torque), 'lat_active': bool(x.latActive)})
    else:
      x = event.gyroscope
      if str(x.source) not in ('lsm6ds3', 'lsm6ds3trc') or x.which() != 'gyroUncalibrated' or len(x.gyroUncalibrated.v) != 3:
        result['gyro_rejected'] += 1
        continue
      result['gyro'].append({**base, 'sensor_ns': int(x.timestamp), 'xyz': [float(v) for v in x.gyroUncalibrated.v]})
  return result


def limit_verdict(observed):
  return {
    'status': 'POST_CONTROLLER_LIMITING_ONLY_OBSERVABLE' if observed else 'LIMIT_MASK_UNAVAILABLE',
    'reason': 'LIMIT_REASON_UNOBSERVED',
    'safety_limited': None,
    'curvature_limited': None,
    'driver_limited': None,
    'rate_limited': None,
    'request_output_linkage': 'CAUSAL_PUBLISH_ALIGNMENT_NOT_EXACT_REQUEST_TRANSACTION_ID',
    'difference_includes_quantization_and_timing': True,
    'historical_clean_primary_valid': 0,
  }


def aligned(streams):
  if set(streams) != {'state', 'command', 'control', 'gyro', 'settings', 'gyro_rejected'}:
    raise ValueError('EXACT_NUMERIC_STREAMS_REQUIRED')
  fields = {
    'state': STATE_FIELDS,
    'command': {'time_ns', 'valid', 'raw', 'normalized'},
    'control': {'time_ns', 'valid', 'requested', 'lat_active'},
    'gyro': {'time_ns', 'valid', 'sensor_ns', 'xyz'},
  }
  if any(set(row) != fields[name] for name in fields for row in streams[name]) or any(set(row) - SETTINGS for row in streams['settings']):
    raise ValueError('EXACT_NUMERIC_ROW_FIELDS_REQUIRED')
  for name in fields:
    validate_times(streams[name])
  validate_times(streams['gyro'], 'sensor_ns')
  ordinary = {
    'state': [{k: x[k] for k in STATE_FIELDS} for x in streams['state']],
    'command': [{'time_ns': x['time_ns'], 'valid': x['valid'], 'command_raw': x['raw']} for x in streams['command']],
    'control': [{'time_ns': x['time_ns'], 'valid': x['valid'], 'lat_active': x['lat_active']} for x in streams['control']],
  }
  rows = s.align(ordinary)['rows']
  bytime = {x['time_ns']: x for x in streams['state']}
  for row in rows:
    row['yaw_raw'] = bytime[row['state_time_ns']]['yaw_raw']
    if row['yaw_raw'] is None or not math.isfinite(row['yaw_raw']):
      row['diagnostic_valid'] = False
      row['reasons'] = sorted({*row['reasons'], 'YAW_UNAVAILABLE'})
  target = np.asarray([x['state_time_ns'] for x in rows], dtype=np.int64)
  gyro = streams['gyro']
  times = np.asarray([x['time_ns'] for x in gyro], dtype=np.int64)
  sensor = np.asarray([x['sensor_ns'] for x in gyro], dtype=np.int64)
  values = np.asarray([x['xyz'] for x in gyro], dtype=np.float64).reshape(-1, 3)
  valid = np.asarray([x['valid'] for x in gyro], dtype=bool)
  options, support = {}, np.ones(len(rows), dtype=bool)
  for lag in q.policy()['lag_samples']:
    query = target - lag * 10_000_000
    index = np.searchsorted(times, query, side='right') - 1
    good = index >= 0
    selected = np.maximum(index, 0)
    output = np.full((len(rows), 3), np.nan)
    if len(times):
      good &= valid[selected] & np.isfinite(values[selected]).all(axis=1) & (sensor[selected] <= times[selected])
      good &= (query - times[selected] >= 0) & (query - times[selected] <= 20_000_000)
      good &= (query - sensor[selected] >= 0) & (query - sensor[selected] <= 20_000_000)
      previous = np.maximum(selected - 1, 0)
      good &= (selected == 0) | ((times[selected] - times[previous] <= 20_000_000) & (sensor[selected] - sensor[previous] <= 20_000_000))
      output[good] = values[selected[good]]
    else:
      good[:] = False
    options[str(lag)] = [[float(v) for v in vector] if ok else None for vector, ok in zip(output, good, strict=True)]
    support &= good
  for row, good in zip(rows, support, strict=True):
    row['gyro_common_valid'] = bool(good)
  return {'rows': rows, 'gyro_options': options}
