"""Future route numeric eligibility only. No fit, selection, or controller execution."""

import argparse
from collections import Counter
import math
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as s
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_signal_policy as q
from openpilot.tools.cyber_autotune import empirical_signal_reader as r
from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as inv


def open_gate(route, split):
  if route.get('v1_overlap') is not False:
    raise ValueError('V1_NUMERIC_REUSE_FORBIDDEN')
  p.verify(split)
  if split.get('status') != 'EMPIRICAL_DATASET_V2_SPLIT_FROZEN' or split.get('policy_sha256') != v.split_policy()['receipt_sha256']:
    raise ValueError('ROUTE_DISJOINT_SPLIT_REQUIRED_BEFORE_NUMERIC')
  assignments = split['routes']
  expected = v.split_routes([
    {'route_id': x['route_id'], 'status': 'ROUTE_METADATA_COMPATIBLE', 'v1_overlap': False} for x in assignments
  ])
  if split != expected:
    raise ValueError('EXACT_FROZEN_ROUTE_ASSIGNMENT_REQUIRED')
  matches = [x['role'] for x in assignments if x['route_id'] == route['route_id']]
  if len(matches) != 1:
    raise ValueError('ROUTE_NOT_IN_FROZEN_SPLIT')
  if matches[0] == 'HOLDOUT':
    # This auditor cannot create model freezes or open evaluation data.
    raise ValueError('HOLDOUT_CLOSED_DEFER_ELIGIBILITY_TO_ONE_TIME_FROZEN_MODEL_EVALUATION')
  return matches[0]


def gyro_readiness(rows):
  if not rows:
    return {'status': 'DIRECT_GYRO_UNAVAILABLE', 'count': 0, 'clock_failures': 0, 'rate_hz': None}
  failures = 0
  for i, row in enumerate(rows):
    if set(row) != {'time_ns', 'sensor_ns', 'xyz', 'valid'} or type(row['time_ns']) is not int or type(row['sensor_ns']) is not int:
      raise ValueError('EXACT_GYRO_CLOCK_FIELDS_REQUIRED')
    failures += int(
      row['sensor_ns'] > row['time_ns'] or row['time_ns'] - row['sensor_ns'] > 20_000_000
      or len(row['xyz']) != 3 or not all(math.isfinite(x) for x in row['xyz']) or not row['valid']
      or (i > 0 and (row['time_ns'] <= rows[i-1]['time_ns'] or row['sensor_ns'] <= rows[i-1]['sensor_ns']))
    )
  span = rows[-1]['sensor_ns'] - rows[0]['sensor_ns']
  return {
    'status': 'GYRO_CLOCK_READY_DEVICE_FRAME_ONLY' if failures == 0 else 'GYRO_UNAVAILABLE',
    'count': len(rows), 'clock_failures': failures,
    'rate_hz': (len(rows)-1)*1e9/span if span > 0 and len(rows) > 1 else None,
  }


def support(rows):
  fields = {'grid_time_ns', 'segment_id', 'diagnostic_valid', 'speed_bin', 'reasons', 'gyro_common_valid'}
  bins = {name: {'valid_samples': 0, 'design_rows': 0, 'gyro_common_design_rows': 0, 'longest_valid_window': 0}
          for name, _, _ in p.policy()['speed_bins']}
  gaps, masks, run, gyro_run, previous = 0, 0, 0, 0, None
  reasons = Counter()
  for row in rows:
    if set(row) != fields or type(row['grid_time_ns']) is not int or type(row['diagnostic_valid']) is not bool or type(row['gyro_common_valid']) is not bool:
      raise ValueError('EXACT_CAUSAL_COVERAGE_FIELDS_REQUIRED')
    v.hash_required(row['segment_id'])
    if row['speed_bin'] not in (*bins, None) or type(row['reasons']) is not list:
      raise ValueError('FROZEN_SPEED_BIN_AND_REASON_FIELDS_REQUIRED')
    same_segment = previous is not None and row['segment_id'] == previous['segment_id']
    if same_segment and row['grid_time_ns'] <= previous['grid_time_ns']:
      raise ValueError('INCREASING_GRID_REQUIRED_NO_REORDERING')
    continuous = same_segment and row['grid_time_ns'] - previous['grid_time_ns'] == 10_000_000 and row['speed_bin'] == previous['speed_bin']
    if not continuous:
      run, gyro_run = 0, 0
      gaps += int(same_segment and row['grid_time_ns'] - previous['grid_time_ns'] != 10_000_000)
    valid = row['diagnostic_valid'] and not row['reasons'] and row['speed_bin'] is not None
    if valid:
      run += 1
      gyro_run = gyro_run + 1 if row['gyro_common_valid'] else 0
      bucket = bins[row['speed_bin']]
      bucket['valid_samples'] += 1
      bucket['design_rows'] += int(run >= m.HISTORY)
      bucket['gyro_common_design_rows'] += int(gyro_run >= m.HISTORY)
      bucket['longest_valid_window'] = max(bucket['longest_valid_window'], run)
    else:
      run, gyro_run = 0, 0
      masks += 1
      reasons.update(row['reasons'])
    previous = row
  for bucket in bins.values():
    bucket['minimum_support_met'] = bucket['design_rows'] >= 201
    bucket['gyro_common_minimum_met'] = bucket['gyro_common_design_rows'] >= 201
  return {
    'potential_grid_samples': len(rows), 'valid_samples': sum(x['valid_samples'] for x in bins.values()),
    'gap_breaks': gaps, 'mask_breaks': masks, 'mask_reasons': dict(sorted(reasons.items())),
    'bins': bins, 'minimum_design_rows': 201,
    'design_basis': '44_PREVIOUS_PLUS_CURRENT_VALID_SAME_SEGMENT_BIN_COMMON_EIGHT_CONFIGS',
    'clean_primary_support': None,
  }


def signal_matrix(streams, setting_known):
  result = dict.fromkeys(v.REQUIRED_SIGNALS)
  if streams.get('state'):
    for field in ('steering_angle', 'steering_pressed', 'driver_torque', 'eps_status', 'esp12_yaw',
                  'speed', 'forward_gear', 'publish_time'):
      result[field] = 'SOURCE_BOUND_FIELD_OBSERVED'
  if streams.get('command'):
    result['torque_output_can'] = result['normalized_output'] = 'SOURCE_BOUND_FIELD_OBSERVED'
  if streams.get('control'):
    result['requested_torque'] = result['lat_active'] = 'SOURCE_BOUND_FIELD_OBSERVED'
  if streams.get('gyro'):
    result['direct_gyro'] = result['gyro_acquisition_time'] = 'DIRECT_DEVICE_SENSOR_OBSERVED_NOT_FRAME_CALIBRATED'
  if setting_known:
    result['steer_max_provenance'] = 'SOURCE_AND_RUNTIME_SETTING_PRESENT'
  # Optional direct fields are never inferred from schema defaults or models.
  for field in ('steering_rate', 'wheel_speeds'):
    if streams.get('additional', {}).get(field):
      result[field] = 'SOURCE_BOUND_FIELD_OBSERVED'
  result['wheelbase'] = result['steer_ratio'] = 'STATIC_CARPARAMS_PRIOR_NOT_MEASUREMENT'
  return result


def optional_crosschecks(source):
  return {
    'wheel_speed_yaw': 'SUPPORTING_ONLY' if all(source.get(k) is True for k in
      ('wheel_units_proven', 'wheel_sign_proven', 'track_width_proven')) else 'BLOCKED_SOURCE_UNITS_SIGN_TRACK_WIDTH',
    'lateral_accel_yaw': 'SUPPORTING_ONLY' if all(source.get(k) is True for k in
      ('accel_units_proven', 'accel_sign_proven', 'accel_frame_proven')) else 'BLOCKED_SOURCE_UNITS_SIGN_FRAME',
    'continuous_scale_fit': False,
  }


def contiguous_duration(times, valid):
  if len(times) != len(valid) or any(type(x) is not int for x in times) or any(type(x) is not bool for x in valid):
    raise ValueError('EXACT_DURATION_CLOCK_MASK_REQUIRED')
  total = 0
  for i in range(1, len(times)):
    delta = times[i] - times[i-1]
    if delta <= 0:
      raise ValueError('INCREASING_DURATION_CLOCK_REQUIRED')
    if delta <= 20_000_000 and valid[i-1] and valid[i]:
      total += delta
  return total * 1e-9


def audit_segment(streams, segment_id, profile):
  gyro = gyro_readiness(streams['gyro'])
  # Invalid gyro clocks do not discard otherwise useful steering/command data.
  clean = {k: value for k, value in streams.items() if k != 'additional'}
  if gyro['status'] == 'GYRO_UNAVAILABLE':
    clean = {**clean, 'gyro': []}
  aligned = r.aligned(clean)
  rows = [{k: row[k] for k in ('grid_time_ns', 'diagnostic_valid', 'speed_bin', 'reasons', 'gyro_common_valid')}
          | {'segment_id': segment_id} for row in aligned['rows']]
  settings = clean['settings']
  known = bool(settings) and all('CustomSteerMax' in x for x in settings) and len({x['CustomSteerMax'] for x in settings}) == 1
  maximum, _ = r.effective_steer_max(profile, settings[0] if known else {})
  bridge = r.command_bridge([{k: x[k] for k in ('raw', 'normalized', 'valid')} for x in clean['command']], maximum, known)
  state = clean['state']
  return {
    'support': support(rows), 'gyro': gyro, 'signals': signal_matrix(streams, known), 'command_bridge': bridge,
    'active_driving_s': contiguous_duration([x['time_ns'] for x in clean['control']], [x['lat_active'] and x['valid'] for x in clean['control']]),
    'no_driver_override_s': contiguous_duration([x['time_ns'] for x in state], [not x['driver_pressed'] and x['valid'] for x in state]),
    'duration_basis': 'PAST_CONTIGUOUS_VALID_PUBLISH_INTERVALS_MAX_20MS_NO_GAP_FILL_OR_ENDPOINT_EXTENSION',
    'optional_crosschecks': optional_crosschecks({}), 'fitting_performed': False,
  }


def read_numeric(iterator):
  # Source-pinned reader handles only permitted fields; optional direct CAN-derived
  # carState values are captured without raw CAN/GPS/model payload access.
  additional = {'steering_rate': [], 'wheel_speeds': []}
  def events():
    for event in iterator:
      if event.which() == 'carState':
        x = event.carState
        additional['steering_rate'].append(float(x.steeringRateDeg))
        wheels = x.wheelSpeeds
        additional['wheel_speeds'].append([float(wheels.fl), float(wheels.fr), float(wheels.rl), float(wheels.rr)])
      yield event
  return {**r.read_numeric(events(), True), 'additional': additional}



def exact_source(root, segment):
  path = v.no_alias(Path(root) / segment['source_key'])
  if not path.resolve().is_relative_to(Path(root).resolve()) or path.name != 'rlog.zst':
    raise ValueError('SOURCE_OUTSIDE_APPROVED_ROOT_OR_LOG_TYPE')
  if p.sha(path.read_bytes()) != segment['source_sha256']:
    raise ValueError('SOURCE_CHANGED_DURING_NUMERIC_ELIGIBILITY')
  return path


def run(root, store, route_id, recorded_source):
  root = v.approved_root(root)
  store = v.no_alias(store)
  record = inv.read(store / 'route-inventory.json')
  binding = inv.read(store / 'metadata-binding.json')
  if record.get('binding_sha256') != binding['receipt_sha256'] or binding.get('reader_sha256') != p.sha(Path(inv.__file__).read_bytes()):
    raise ValueError('STALE_V2_INVENTORY_BINDING')
  if binding.get('eligibility_policy_sha256') != v.eligibility_policy()['receipt_sha256']:
    raise ValueError('ELIGIBILITY_POLICY_CHANGED')
  if q.source_contract(recorded_source)['receipt_sha256'] != binding['source_sha256']:
    raise ValueError('SOURCE_IDENTITY_MISMATCH')
  if inv.scan_tree(root) != record['snapshot']:
    raise ValueError('SOURCE_CHANGED_AFTER_SPLIT')
  route = next((x for x in record['routes'] if x['route_id'] == route_id), None)
  if route is None or route['status'] != 'ROUTE_METADATA_COMPATIBLE':
    raise ValueError('ONLY_UNTOUCHED_COMPATIBLE_ROUTE')
  role = open_gate(route, record['split'])
  schema = s.schema(recorded_source)
  results = []
  for segment in record['snapshot']['segments']:
    if segment['source_sha256'] not in route['segments']:
      continue
    raw_path = exact_source(root, segment)
    expected = p.sha(p.canonical({
      'metadata_binding': binding['receipt_sha256'], 'source': segment['source_sha256'],
      'split': record['split']['receipt_sha256'], 'role': role,
      'auditor': p.sha(Path(__file__).read_bytes()), 'policy': v.eligibility_policy()['receipt_sha256'],
    }))
    destination = store / 'eligibility' / (segment['source_sha256'] + '.json')
    result = inv.cached(destination, expected)
    if result is None:
      first = read_numeric(s.events(raw_path, schema))
      second = read_numeric(s.events(raw_path, schema))
      exact_source(root, segment)
      if first != second:
        raise ValueError('NUMERIC_ELIGIBILITY_NOT_REPEATABLE')
      profile = {'steer_control_type': 'torque', 'flags': v.expected_generation()['flags']}
      value = audit_segment(first, segment['source_sha256'], profile)
      if value != audit_segment(second, segment['source_sha256'], profile):
        raise ValueError('ELIGIBILITY_METRICS_NOT_REPEATABLE')
      result = p.seal({'schema': 'EMPIRICAL_ROUTE_SEGMENT_ELIGIBILITY_V2',
                       'binding_sha256': expected, 'route_id': route_id, 'role': role, **value})
      p.persist(destination, result)
    exact_source(root, segment)
    results.append(result)
  if inv.scan_tree(root) != record['snapshot']:
    raise ValueError('SOURCE_CHANGED_DURING_ROUTE_AUDIT')
  output = p.seal({
    'schema': 'EMPIRICAL_ROUTE_ELIGIBILITY_V2', 'route_id': route_id, 'role': role,
    'split_sha256': record['split']['receipt_sha256'], 'segments': results,
    'status': 'ROUTE_SIGNAL_READY' if any(x['support']['valid_samples'] for x in results) else 'ROUTE_CONTIGUOUS_SUPPORT_PARTIAL',
    'fitting_performed': False, 'holdout_opened': False,
  })
  p.persist(store / 'eligibility' / (route_id + '.json'), output)
  return output


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--private-root', required=True)
  parser.add_argument('--private-store', required=True)
  parser.add_argument('--route-id', required=True)
  parser.add_argument('--recorded-source', required=True)
  args = parser.parse_args()
  row = run(args.private_root, args.private_store, args.route_id, args.recorded_source)
  print(row['schema'], row['receipt_sha256'], row['status'])


if __name__ == '__main__':
  main()
