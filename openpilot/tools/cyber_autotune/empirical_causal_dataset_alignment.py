"""All-row causal alignment and legacy accounting. No design matrix or solver."""
from collections import Counter
import math
import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

DT = 10_000_000
AGE = 20_000_000
BINS = ('LOW', 'MEDIUM', 'HIGH')
REASONS = ('MISSING_OR_GAP', 'REPEATED_OUTPUT_EVENT', 'SOURCE_EVENT_GAP', 'NONFINITE', 'INVALID_MESSAGE',
           'INACTIVE', 'DRIVER_OVERRIDE', 'EPS_FAULT', 'NON_FORWARD_GEAR', 'LOW_SPEED', 'RAW_CAN_DOMAIN')
STATE = ('speed_mps', 'angle_deg', 'rate', 'driver_pressed', 'driver_torque', 'torque_eps',
         'fault_temporary', 'fault_permanent', 'eps_fault', 'gear', 'yaw_raw', 'wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr')
COMMAND = ('raw', 'normalized')
CONTROL = ('requested', 'lat_active')
REQUIRED = ('state.speed_mps', 'state.angle_deg', 'state.rate', 'state.driver_pressed', 'state.driver_torque',
            'state.gear', 'state.fault_temporary', 'state.fault_permanent', 'command.raw', 'command.normalized',
            'control.requested', 'control.lat_active')


def finite(v):
  return v is not None and (isinstance(v, str) or math.isfinite(v))


def validate_clock(rows, key='time_ns'):
  values = [x[key] for x in rows]
  if any(type(x) is not int or x < 0 for x in values) or any(b <= a for a, b in zip(values, values[1:], strict=False)):
    raise ValueError('UNIQUE_INCREASING_SOURCE_TIME_REQUIRED')


def run_ids(valid, bins=None):
  ids = np.full(len(valid), -1, dtype='<i8')
  within = np.full(len(valid), -1, dtype='<i8')
  count, index, previous = -1, 0, None
  for i, good in enumerate(valid):
    if good:
      if i == 0 or not valid[i-1] or (bins is not None and bins[i] != previous):
        count += 1
        index = 0
      ids[i], within[i] = count, index
      index += 1
    previous = None if bins is None else bins[i]
  return ids, within


def build(streams, config_sha, ordinal, route_offset):
  for kind in ('state', 'command', 'control', 'gyro'):
    validate_clock(streams[kind])
  gyro_clock_failures = 0
  if streams['gyro']:
    acquisition = [x['sensor_ns'] for x in streams['gyro']]
    gyro_clock_failures = sum(b <= a for a, b in zip(acquisition, acquisition[1:], strict=False))
  if not streams['state']:
    raise ValueError('REQUIRED_STATE_STREAM_UNAVAILABLE')
  times = {k: np.asarray([x['time_ns'] for x in streams[k]], dtype='<i8') for k in ('state', 'command', 'control', 'gyro')}
  first, last = times['state'][0], times['state'][-1]
  grid = np.arange(((first+DT-1)//DT)*DT, last+1, DT, dtype='<i8')
  n = len(grid)
  selected = {'state': np.searchsorted(times['state'], grid, side='right')-1}
  state_time = times['state'][selected['state']]
  for kind in ('command', 'control', 'gyro'):
    selected[kind] = np.searchsorted(times[kind], state_time, side='right')-1
  arrays = {'grid_time_ns': grid, 'aligned_row_index': np.arange(n, dtype='<i8'),
            'route_global_row_index': np.arange(route_offset, route_offset+n, dtype='<i8'),
            'segment_ordinal': np.full(n, ordinal, dtype='<i8'), 'config_sequence': np.zeros(n, dtype='<i8')}
  fresh, gap = {}, {}
  for kind, indices in selected.items():
    present = indices >= 0
    t = np.full(n, -1, dtype='<i8')
    event_valid = np.zeros(n, dtype=bool)
    event_gap = np.zeros(n, dtype=bool)
    if len(times[kind]):
      t[present] = times[kind][indices[present]]
      event_valid[present] = np.asarray([x['valid'] for x in streams[kind]])[indices[present]]
      previous = np.maximum(indices-1, 0)
      event_gap[present] = (indices[present] > 0) & (t[present]-times[kind][previous[present]] > AGE)
    age = np.where(present, (grid if kind == 'state' else state_time)-t, -1)
    fresh[kind] = present & (age >= 0) & (age <= AGE)
    gap[kind] = event_gap
    arrays[kind+'.time_ns'] = t
    arrays[kind+'.age_ns'] = age
    arrays[kind+'.present'] = present
    arrays[kind+'.fresh'] = fresh[kind]
    arrays[kind+'.event_valid'] = np.where(present, event_valid.astype(np.int8), -1).astype('i1')
    arrays[kind+'.new_event_since_grid'] = present & np.r_[True, t[1:] != t[:-1]]
    arrays[kind+'.gap'] = event_gap
    arrays[kind+'.message_index'] = indices.astype('<i8')
  for kind, fields in (('state', STATE), ('command', COMMAND), ('control', CONTROL)):
    indices = selected[kind]
    for field in fields:
      string = field == 'gear'
      values = np.full(n, '' if string else np.nan, dtype='<U16' if string else '<f8')
      available = np.zeros(n, dtype=bool)
      for i, index in enumerate(indices):
        if index < 0:
          continue
        value = streams[kind][index].get(field)
        if fresh[kind][i] and finite(value):
          values[i], available[i] = value, True
      arrays[kind+'.'+field] = values
      arrays[kind+'.'+field+'.available'] = available
  gyro_values = np.full((n, 3), np.nan, dtype='<f8')
  gyro_acquisition = np.full(n, -1, dtype='<i8')
  gyro_source = np.full(n, '', dtype='<U16')
  gyro_good = np.zeros(n, dtype=bool)
  for i, index in enumerate(selected['gyro']):
    if index < 0:
      continue
    g = streams['gyro'][index]
    gyro_acquisition[i], gyro_source[i] = g['sensor_ns'], g['source']
    good = (not gyro_clock_failures and fresh['gyro'][i] and g['valid'] and not gap['gyro'][i]
            and g['sensor_ns'] <= g['time_ns'] and 0 <= state_time[i]-g['sensor_ns'] <= AGE and np.isfinite(g['xyz']).all())
    if good:
      gyro_values[i], gyro_good[i] = g['xyz'], True
  arrays.update({'gyro.xyz': gyro_values, 'gyro.xyz.available': gyro_good, 'gyro.acquisition_time_ns': gyro_acquisition,
                 'gyro.source': gyro_source, 'gyro.acquisition_age_ns': np.where(gyro_acquisition >= 0, state_time-gyro_acquisition, -1)})
  reasons, bins, legacy = [], [], []
  for i, index in enumerate(selected['state']):
    state = streams['state'][index]
    ci, ri = selected['command'][i], selected['control'][i]
    command = streams['command'][ci] if ci >= 0 else None
    control = streams['control'][ri] if ri >= 0 else None
    r = set()
    if not all(fresh[k][i] for k in ('state', 'command', 'control')):
      r.add('MISSING_OR_GAP')
    if i and state_time[i] == state_time[i-1]:
      r.add('REPEATED_OUTPUT_EVENT')
    if any(gap[k][i] for k in ('state', 'command', 'control')):
      r.add('SOURCE_EVENT_GAP')
    if any(not finite(state.get(k)) for k in ('speed_mps', 'angle_deg', 'driver_torque')) or (command and not finite(command.get('raw'))):
      r.add('NONFINITE')
    if not state['valid'] or (command and not command['valid']) or (control and not control['valid']):
      r.add('INVALID_MESSAGE')
    if control and not control['lat_active']:
      r.add('INACTIVE')
    if state['driver_pressed']:
      r.add('DRIVER_OVERRIDE')
    if state['eps_fault']:
      r.add('EPS_FAULT')
    if state['gear'] != 'drive':
      r.add('NON_FORWARD_GEAR')
    speed = state['speed_mps']
    if speed is not None and speed < 5:
      r.add('LOW_SPEED')
    if command and finite(command['raw']) and not -1024 <= command['raw'] <= 1023:
      r.add('RAW_CAN_DOMAIN')
    b = 'LOW' if finite(speed) and 5 <= speed < 15 else 'MEDIUM' if finite(speed) and 15 <= speed < 25 else 'HIGH' if finite(speed) and speed >= 25 else ''
    bins.append(b)
    reasons.append(sorted(r))
    legacy.append(not r)
  arrays['speed_bin'] = np.asarray(bins, dtype='<U6')
  arrays['legacy_diagnostic_valid'] = np.asarray(legacy, dtype=bool)
  arrays['legacy_reason_bits'] = np.asarray([sum(1 << REASONS.index(r) for r in rs) for rs in reasons], dtype='<u4')
  required = np.logical_and.reduce([arrays[k+'.available'] for k in REQUIRED])
  causal_good = required & np.logical_and.reduce([arrays[k+'.event_valid'] == 1 for k in ('state', 'command', 'control')])
  causal_good &= ~np.logical_or.reduce([gap[k] for k in ('state', 'command', 'control')])
  causal_good &= ~np.r_[False, state_time[1:] == state_time[:-1]]
  arrays['causal_required_valid'] = causal_good
  arrays['causal_run_id'], arrays['within_causal_run_index'] = run_ids(causal_good)
  arrays['legacy_run_id'], arrays['within_legacy_run_index'] = run_ids(np.asarray(legacy) & (arrays['speed_bin'] != ''), bins)
  for key, field in (('active', 'control.lat_active'), ('pressed', 'state.driver_pressed')):
    value = arrays[field]
    usable = arrays[field+'.available']
    previous_good = usable & np.r_[False, usable[:-1]]
    change = previous_good & (value != np.r_[np.nan, value[:-1]])
    arrays[key+'_transition'] = change
    arrays[key+'_rising'] = change & (value == 1)
    arrays[key+'_falling'] = change & (value == 0)
  arrays['run_boundary'] = arrays['within_causal_run_index'] == 0
  arrays['segment_boundary'] = np.arange(n) == 0
  arrays['command_rail'] = np.where(arrays['command.raw.available'], (abs(arrays['command.raw']) == 409).astype(float), np.nan)
  arrays['normalized_rail'] = np.where(arrays['command.normalized.available'], (abs(arrays['command.normalized']) == 1).astype(float), np.nan)
  arrays['publish_aligned_request_output_difference'] = arrays['control.requested']-arrays['command.normalized']
  snapshots = []
  for i in range(n):
    # Base causal observation, not a supervised target. No future/prediction/result field.
    snap = {'config_sha256': config_sha, 'segment_ordinal': ordinal, 'grid_time_ns': int(grid[i]), 'selected': {}}
    for kind in ('state', 'command', 'control', 'gyro'):
      index = int(selected[kind][i])
      values = streams[kind][index] if index >= 0 else None
      snap['selected'][kind] = {'message_index': index if index >= 0 else None, 'time_ns': int(arrays[kind+'.time_ns'][i]) if index >= 0 else None,
                               'age_ns': int(arrays[kind+'.age_ns'][i]) if index >= 0 else None, 'fresh': bool(fresh[kind][i]),
                               'values': sanitize(values), 'availability': 'PRESENT' if fresh[kind][i] else 'MISSING_OR_STALE'}
    snapshots.append(p.sha(p.canonical(snap)))
  arrays['consumed_input_snapshot_sha256'] = np.asarray(snapshots, dtype='S64')
  lengths = Counter(int(x) for x in arrays['causal_run_id'] if x >= 0)
  bybin = {}
  for b in BINS:
    ix = arrays['speed_bin'] == b
    ids = arrays['legacy_run_id'][ix & arrays['legacy_diagnostic_valid']]
    runs = Counter(int(x) for x in ids if x >= 0)
    bybin[b] = {'total_grid_samples': int(ix.sum()), 'diagnostic_valid': int(np.sum(ix & arrays['legacy_diagnostic_valid'])),
                'contiguous_runs': len(runs), 'common_design_rows': sum(max(0, count-44) for count in runs.values()),
                'longest_contiguous_samples': max(runs.values(), default=0)}
  coverage = {k: int(arrays[k+'.available'].sum()) for k in REQUIRED}
  stats = {'total_grid_samples': n, 'diagnostic_valid': sum(legacy), 'bins': bybin, 'required_field_coverage': coverage,
           'causal_required_valid': int(causal_good.sum()), 'causal_runs': len(lengths),
           'longest_causal_run': max(lengths.values(), default=0),
           'causal_run_length_distribution': {str(k): v for k, v in sorted(Counter(lengths.values()).items())},
           'mask_reason_counts': dict(Counter(r for rs in reasons for r in rs)),
           'gyro_xyz_available': int(gyro_good.sum()), 'gyro_acquisition_clock_failures': gyro_clock_failures,
           'gyro_rejected': streams.get('gyro_rejected', 0),
           'source_age': {k: distribution(arrays[k+'.age_ns'][arrays[k+'.present']]) for k in ('state', 'command', 'control', 'gyro')},
           'request_output_order': dict(Counter('REQUEST_BEFORE_OUTPUT' if a < b else 'REQUEST_AFTER_OUTPUT' if a > b else 'SAME_PUBLISH_TIME_NOT_TRANSACTION'
                                             for a, b in zip(arrays['control.time_ns'], arrays['command.time_ns'], strict=True) if a >= 0 and b >= 0)),
           'simultaneous_command_coverage': int(np.sum(arrays['control.requested.available'] &
             arrays['command.raw.available'] & arrays['command.normalized.available']))}
  stats['field_coverage'] = {k.removesuffix('.available'): int(v.sum()) for k, v in arrays.items() if k.endswith('.available')}
  stats['transitions'] = {k: int(arrays[k].sum()) for k in (
    'active_transition', 'active_rising', 'active_falling', 'pressed_transition', 'pressed_rising', 'pressed_falling', 'run_boundary')}
  stats['source_message_counts'] = {k: len(streams[k]) for k in ('state', 'command', 'control', 'gyro')}
  stats['source_rate_finite_count'] = sum(finite(x.get('rate')) for x in streams['state'])
  return arrays, stats


def sanitize(x):
  if isinstance(x, dict):
    return {k: sanitize(v) for k, v in x.items()}
  if isinstance(x, list):
    return [sanitize(v) for v in x]
  if isinstance(x, float) and not math.isfinite(x):
    return None
  return x


def distribution(values):
  return {'count': len(values), 'median_ns': float(np.median(values)) if len(values) else None,
          'p95_ns': float(np.percentile(values, 95)) if len(values) else None,
          'maximum_ns': int(np.max(values)) if len(values) else None}
