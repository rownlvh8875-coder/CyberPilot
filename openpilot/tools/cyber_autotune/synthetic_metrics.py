"""Versioned aggregate metrics for generic synthetic traces, never vehicle truth.

No controller, profile store, Params, or actuator transport is imported. Null
denotes unavailable coverage, not a perfect result. These descriptive metrics do
not implement or relax an acceptance gate. v1 measurement/evidence is unchanged.
"""
import math

from openpilot.tools.cyber_autotune.contracts import finite_number
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


LATERAL_NUMBERS = (
  'lateral_error_m', 'heading_error_rad', 'desired_curvature_1pm', 'actual_curvature_1pm',
  'speed_mps', 'requested_command', 'applied_command', 'steering_angle_deg', 'desired_steering_angle_deg',
  'lane_half_width_m', 'vehicle_half_width_m',
)
LONG_NUMBERS = (
  'speed_mps', 'accel_mps2', 'target_accel_mps2', 'requested_accel_mps2',
  'lead_distance_m', 'lead_speed_mps', 'desired_distance_m', 'position_m', 'target_speed_mps',
)


def _validate(trace, dt_s, numbers, flags, *, longitudinal=False):
  if (type(trace) not in (tuple, list) or not 4 <= len(trace) <= 60_000 or
      not finite_number(dt_s) or not .001 <= dt_s <= .1):
    raise ValueError('INVALID_SYNTHETIC_TRACE')
  previous = None
  for row in trace:
    if type(row) is not dict:
      raise ValueError('INVALID_SYNTHETIC_ROW')
    for name in ('time_s', *numbers):
      if not finite_number(row.get(name)) or abs(row[name]) > 1e6:
        raise ValueError('INVALID_SYNTHETIC_VALUE')
    if any(type(row.get(name)) is not bool for name in flags):
      raise ValueError('INVALID_SYNTHETIC_FLAG')
    time = row['time_s']
    if time < 0 or (previous is not None and not math.isclose(time - previous, dt_s, rel_tol=0, abs_tol=1e-10)):
      raise ValueError('INVALID_SYNTHETIC_TIMEBASE')
    if not 0 <= row['speed_mps'] <= 80:
      raise ValueError('INVALID_SYNTHETIC_SPEED')
    if longitudinal:
      if row['stop_required'] and row.get('stop_target_m') is None:
        raise ValueError('REQUIRED_STOP_TARGET_UNAVAILABLE')
      if not (0 <= row['lead_speed_mps'] <= 80 and 0 <= row['target_speed_mps'] <= 80 and row['desired_distance_m'] >= 0):
        raise ValueError('INVALID_LONGITUDINAL_DOMAIN')
      if 'stop_target_m' not in row or (row['stop_target_m'] is not None and
                                      (not finite_number(row['stop_target_m']) or abs(row['stop_target_m']) > 1e6)):
        raise ValueError('INVALID_STOP_TARGET')
    elif (abs(row['requested_command']) > 1 or abs(row['applied_command']) > 1 or
          not 0 < row['vehicle_half_width_m'] < row['lane_half_width_m'] <= 10):
      raise ValueError('INVALID_LATERAL_DOMAIN')
    previous = time


def _rms(values):
  return math.sqrt(math.fsum(value * value for value in values) / len(values)) if values else None


def _derivative(values, dt_s):
  return tuple((right - left) / dt_s for left, right in zip(values, values[1:], strict=False))


def _third_derivative(values, dt_s):
  for _ in range(3):
    values = _derivative(values, dt_s)
  return values


def _crossings(values):
  signs = tuple(1 if value > 1e-9 else -1 for value in values if abs(value) > 1e-9)
  return sum(left != right for left, right in zip(signs, signs[1:], strict=False))


def _base(trace, dt_s):
  return {
    'metric_version': 'synthetic-metrics-v2', 'truth_scope': 'GENERIC_SYNTHETIC_ONLY',
    'sample_count': len(trace), 'dt_s': dt_s, 'trace_sha256': digest(canonical(trace)),
    'timebase_gap_count': 0, 'real_vehicle_verified': False, 'runtime_accepted': False,
    'active_profile_enabled': False, 'vehicle_write_enabled': False, 'can_write_enabled': False,
    'promotable_to_vehicle': False, 'vehicle_activation_allowed': False,
  }


def _recovery_delays(trace, released, recovered, within):
  delays = []
  unresolved = 0
  for index in range(1, len(trace)):
    if not released(trace[index - 1], trace[index]):
      continue
    end = next((j for j in range(index + 1, len(trace)) if not within(trace[j])), len(trace))
    recovery = next((row for row in trace[index:end] if recovered(row)), None)
    if recovery is None:
      unresolved += 1
    else:
      delays.append(recovery['time_s'] - trace[index]['time_s'])
  return (max(delays) if delays and not unresolved else None), unresolved


def lateral_metrics(trace, dt_s: float) -> dict:
  """Nearest-rank absolute P95; derivatives at native trace dt; no gate decision.

  Positive lateral error is left of the reference; positive curvature turns left.
  Inside bias is error times curvature sign. Frequency is crossing-pair rate,
  not a spectral peak. Recovery requires |center|<=0.1m and |heading|<=0.01rad.
  """
  _validate(trace, dt_s, LATERAL_NUMBERS, ('saturated', 'rate_limited', 'active', 'steering_pressed'))
  errors = tuple(row['lateral_error_m'] for row in trace)
  absolute = sorted(abs(value) for value in errors)
  left = tuple(row['lateral_error_m'] for row in trace if row['desired_curvature_1pm'] > 1e-9)
  right = tuple(row['lateral_error_m'] for row in trace if row['desired_curvature_1pm'] < -1e-9)
  inside = (*left, *(-value for value in right))
  requested = tuple(row['requested_command'] for row in trace)
  applied = tuple(row['applied_command'] for row in trace)
  crossings = _crossings(requested)
  recovery, unresolved = _recovery_delays(
    trace, lambda a, b: (not a['active'] or a['steering_pressed']) and b['active'] and not b['steering_pressed'],
    lambda row: abs(row['lateral_error_m']) <= .1 and abs(row['heading_error_rad']) <= .01,
    lambda row: row['active'] and not row['steering_pressed'],
  )
  result = _base(trace, dt_s)
  result.update({
    'center_rms_m': _rms(errors), 'center_p95_abs_m': absolute[math.ceil(.95 * len(absolute)) - 1],
    'center_max_abs_m': absolute[-1], 'center_mean_m': math.fsum(errors) / len(errors),
    'left_curve_rms_m': _rms(left), 'right_curve_rms_m': _rms(right),
    'left_right_rms_asymmetry_m': abs(_rms(left) - _rms(right)) if left and right else None,
    'curve_inside_bias_m': math.fsum(inside) / len(inside) if inside else None,
    'lane_edge_minimum_margin_m': min(row['lane_half_width_m'] - row['vehicle_half_width_m'] - abs(row['lateral_error_m'])
                                      for row in trace),
    'heading_error_rms_rad': _rms(tuple(row['heading_error_rad'] for row in trace)),
    'curvature_tracking_rms_1pm': _rms(tuple(row['actual_curvature_1pm'] - row['desired_curvature_1pm'] for row in trace)),
    'yaw_tracking_rms_rps': _rms(tuple((row['actual_curvature_1pm'] - row['desired_curvature_1pm']) * row['speed_mps']
                                     for row in trace)),
    'command_derivative_rms_per_s': _rms(_derivative(requested, dt_s)),
    'requested_command_jerk_rms_per_s3': _rms(_third_derivative(requested, dt_s)),
    'applied_command_jerk_rms_per_s3': _rms(_third_derivative(applied, dt_s)),
    'steering_jerk_rms_deg_s3': _rms(_third_derivative(tuple(row['steering_angle_deg'] for row in trace), dt_s)),
    'steering_tracking_rms_deg': _rms(tuple(row['steering_angle_deg'] - row['desired_steering_angle_deg'] for row in trace)),
    'command_zero_crossings': crossings,
    'command_oscillation_pair_count': crossings // 2,
    'lane_loss_recovery_s': None,  # no lane-perception consumer in controller-core fixtures
    'command_crossing_pair_frequency_hz': crossings / (2 * (len(trace) - 1) * dt_s),
    'saturation_ratio': sum(row['saturated'] for row in trace) / len(trace),
    'saturation_duration_s': sum(row['saturated'] for row in trace) * dt_s,
    'rate_limited_duration_s': sum(row['rate_limited'] for row in trace) * dt_s,
    'override_frames': sum(row['steering_pressed'] for row in trace),
    'override_recovery_s': recovery, 'unresolved_recoveries': unresolved,
    'maximum_command_step': max(abs(b - a) for a, b in zip(requested, requested[1:], strict=False)),
  })
  canonical(result)
  return result


def longitudinal_metrics(trace, dt_s: float) -> dict:
  """Supplied-plan/lead reference metrics, not a test of lead perception/planning.

  TTC is gap/closing speed only when closing; contact has TTC zero. No closing
  lead gives null. Stop error is the worst-absolute signed terminal error across
  independent required-stop episodes; any unresolved episode makes it null.
  """
  _validate(trace, dt_s, LONG_NUMBERS, ('lead_available', 'should_stop', 'stop_required', 'active', 'saturated'), longitudinal=True)
  lead = tuple(row for row in trace if row['lead_available'])
  ttc = tuple(0. if row['lead_distance_m'] <= 0 else row['lead_distance_m'] / (row['speed_mps'] - row['lead_speed_mps'])
              for row in lead if row['lead_distance_m'] <= 0 or row['speed_mps'] > row['lead_speed_mps'])
  episodes = []
  episode = []
  for row in trace:
    if row['stop_required']:
      episode.append(row)
    elif episode:
      episodes.append(episode)
      episode = []
  if episode:
    episodes.append(episode)
  stopping = tuple(row for episode in episodes for row in episode)
  stop_errors = tuple(episode[-1]['stop_target_m'] - episode[-1]['position_m']
                      for episode in episodes if episode[-1]['speed_mps'] < .1)
  unresolved_stops = len(episodes) - len(stop_errors)
  requested = tuple(row['requested_accel_mps2'] for row in trace)
  actual = tuple(row['accel_mps2'] for row in trace)
  recovery, unresolved = _recovery_delays(
    trace, lambda a, b: a['should_stop'] and not b['should_stop'] and b['active'],
    lambda row: row['speed_mps'] >= .5,
    lambda row: row['active'] and not row['should_stop'],
  )
  cut_in_delays = []
  cut_in_decels = []
  unresolved_cut_ins = 0
  for index in range(1, len(trace)):
    if trace[index - 1]['lead_available'] or not trace[index]['lead_available'] or not trace[index]['active']:
      continue
    end = next((j for j in range(index + 1, len(trace)) if not trace[j]['lead_available'] or not trace[j]['active']), len(trace))
    cut_in_decels.append(max(0., -min(row['accel_mps2'] for row in trace[index:end])))
    # Diagnostic response definition: at least 0.1 m/s^2 requested reduction
    # relative to the command immediately before synthetic lead acquisition.
    threshold = trace[index - 1]['requested_accel_mps2'] - .1
    response = next((row for row in trace[index:end] if row['requested_accel_mps2'] <= threshold), None)
    if response is None:
      unresolved_cut_ins += 1
    else:
      cut_in_delays.append(response['time_s'] - trace[index]['time_s'])
  result = _base(trace, dt_s)
  actual_jerk = sorted(abs(value) for value in _derivative(actual, dt_s))
  command_jerk = sorted(abs(value) for value in _derivative(requested, dt_s))
  result.update({
    'minimum_ttc_s': min(ttc) if ttc else None,
    'lead_distance_rms_m': _rms(tuple(row['lead_distance_m'] - row['desired_distance_m'] for row in lead)),
    'maximum_deceleration_mps2': max(0., -min(actual)),
    'acceleration_tracking_rms_mps2': _rms(tuple(row['accel_mps2'] - row['target_accel_mps2'] for row in trace)),
    'braking_overshoot_mps2': max(0., max(row['target_accel_mps2'] - row['accel_mps2'] for row in trace
                                        if row['target_accel_mps2'] < 0))
                            if any(row['target_accel_mps2'] < 0 for row in trace) else None,
    'actual_jerk_rms_mps3': _rms(_derivative(actual, dt_s)),
    'command_jerk_rms_mps3': _rms(_derivative(requested, dt_s)),
    'actual_jerk_p95_abs_mps3': actual_jerk[math.ceil(.95 * len(actual_jerk)) - 1],
    'actual_jerk_max_abs_mps3': actual_jerk[-1],
    'command_jerk_p95_abs_mps3': command_jerk[math.ceil(.95 * len(command_jerk)) - 1],
    'command_jerk_max_abs_mps3': command_jerk[-1],
    'cut_in_peak_deceleration_mps2': max(cut_in_decels) if cut_in_decels else None,
    'stopping_overshoot_m': max(0., max(row['position_m'] - row['stop_target_m'] for row in stopping)) if stopping else None,
    'stop_episode_count': len(episodes), 'unresolved_stops': unresolved_stops,
    'stopping_error_m': max(stop_errors, key=abs) if stop_errors and not unresolved_stops else None,
    'restart_delay_s': recovery, 'unresolved_restarts': unresolved,
    'cut_in_response_s': max(cut_in_delays) if cut_in_delays and not unresolved_cut_ins else None,
    'unresolved_cut_ins': unresolved_cut_ins,
    'false_stop_frames': sum(row['active'] and not row['stop_required'] and row['target_speed_mps'] > .5 and row['speed_mps'] < .1
                             for row in trace),
    'false_braking_frames': sum(row['active'] and row['should_stop'] and not row['stop_required'] and row['requested_accel_mps2'] < 0
                                for row in trace),
    'saturation_ratio': sum(row['saturated'] for row in trace) / len(trace),
    'maximum_acceleration_command_step_mps2': max(abs(b - a) for a, b in zip(requested, requested[1:], strict=False)),
  })
  result['false_stop_duration_s'] = result['false_stop_frames'] * dt_s
  canonical(result)
  return result
