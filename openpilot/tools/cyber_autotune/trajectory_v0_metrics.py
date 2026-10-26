"""Frozen-policy descriptive metrics. No acceptance score, tuning or physical meter truth."""
import math
import numpy as np

from openpilot.tools.cyber_autotune.trajectory_v0_freeze import load

DT = .01


def distribution(values, total):
  if any(not math.isfinite(float(v)) for v in values) or total < len(values):
    raise ValueError('INVALID_METRIC_SUPPORT')
  n = len(values)
  return {'n': n, 'total': total, 'unavailable': total-n, 'small_support': n < 3,
          **dict(zip(('p50', 'p90', 'p95', 'maximum'),
                     map(float, (*np.quantile(values, [.5, .9, .95], method='linear'), max(values))) if n
                     else (None,)*4, strict=True))}


def distance_value(rows, distance, key):
  if not rows or any(b['pose_x'] <= a['pose_x'] for a, b in zip(rows, rows[1:], strict=False)):
    return None
  if not rows[0]['pose_x'] <= distance <= rows[-1]['pose_x']:
    return None
  return float(np.interp(distance, [r['pose_x'] for r in rows], [r[key] for r in rows]))


def lag(desired, actual):
  candidates = []
  n = len(desired)
  if n != len(actual):
    raise ValueError('LAG_SUPPORT_MISMATCH')
  for shift in range(-100, 101):
    x = np.array(desired[max(0, -shift):min(n, n-shift)], dtype=float)
    y = np.array(actual[max(0, shift):min(n, n+shift)], dtype=float)
    if len(x) < 3 or len(x) != len(y):
      continue
    x -= x.mean()
    y -= y.mean()
    denominator = np.linalg.norm(x)*np.linalg.norm(y)
    if denominator > 0:
      candidates.append((float(np.dot(x, y)/denominator), shift, len(x)))
  if not candidates:
    return {'lag_s': None, 'pairs': 0, 'status': 'FLAT_OR_INSUFFICIENT'}
  best = sorted(candidates, key=lambda row: (-row[0], abs(row[1]), row[1]))[0]
  tied = sum(row[0] == best[0] for row in candidates)
  return {'lag_s': best[1]*DT, 'pairs': best[2], 'correlation': best[0],
          'status': 'AMBIGUOUS_TIE' if tied > 1 else 'IDENTIFIED_DESCRIPTIVE'}


def eligible(row):
  return row['input']['active'] and not row['input']['steering_pressed']


def segments(rows):
  result, current = [], []
  for row in rows:
    if row['input']['dt_s'] != DT or not math.isfinite(row['input']['time_s']):
      raise ValueError('METRIC_TIMEBASE_REQUIRED')
    if any(not math.isfinite(row[k]) for k in ('requested', 'applied', 'curvature', 'heading', 'pose_x', 'pose_y')):
      raise ValueError('FINITE_METRIC_ROWS_REQUIRED')
    if not eligible(row):
      if current:
        result.append(current)
      current = []
      continue
    if current and (row['index'] != current[-1]['index']+1 or row['reset_events']
                    or not math.isclose(row['input']['time_s']-current[-1]['input']['time_s'], DT, rel_tol=0., abs_tol=1e-12)):
      result.append(current)
      current = []
    current.append(row)
  if current:
    result.append(current)
  return result


def derivative(parts, key):
  return [(b[key]-a[key])/DT for part in parts for a, b in zip(part, part[1:], strict=False)]


def sign_changes(parts, key):
  count = 0
  for part in parts:
    signs = [math.copysign(1., r[key]) for r in part if r[key] != 0.]
    count += sum(a != b for a, b in zip(signs, signs[1:], strict=False))
  return count


def evaluate(rows):
  policy = load()['metrics']
  parts = segments(rows)
  valid = [r for part in parts for r in part]
  errors = [abs(r['input']['desired_curvature_1pm']-r['input']['actual_curvature_1pm']) for r in valid]
  phases = {}
  for phase in ('STRAIGHT', 'ENTRY', 'APEX', 'EXIT', 'REVERSAL'):
    subset = [r for r in rows if r['phase'] == phase]
    v = [r for r in subset if eligible(r)]
    phase_parts = segments(subset)
    phases[phase] = {'tracking': distribution(
      [abs(r['input']['desired_curvature_1pm']-r['input']['actual_curvature_1pm']) for r in v], len(subset)),
      'lag_segments': [lag([r['input']['desired_curvature_1pm'] for r in part],
                           [r['input']['actual_curvature_1pm'] for r in part])
                       for part in phase_parts],
      'coverage': {'total': len(subset), 'eligible': len(v), 'ineligible': len(subset)-len(v),
                   'lag_total_segments': len(phase_parts),
                   'lag_minimum_pairs': 3, 'lag_total_samples': len(v)},
      'heading_abs': distribution([abs(r['heading']) for r in v], len(subset)),
      'pose_y_abs': distribution([abs(r['pose_y']) for r in v], len(subset)),
      'requested_derivative_abs': distribution(list(map(abs, derivative(phase_parts, 'requested'))), max(0, len(subset)-1)),
      'applied_derivative_abs': distribution(list(map(abs, derivative(phase_parts, 'applied'))), max(0, len(subset)-1)),
      'sign_reversal': {'count': sign_changes(phase_parts, 'requested'), 'eligible_samples': len(v), 'total_samples': len(subset)},
      'saturation_support': {'observed': sum(r['saturation'] is not None for r in v), 'eligible': len(v),
                             'saturated': sum(bool(r['saturation']) for r in v)}}
  saturation = [r for r in valid if r['saturation'] is not None]
  sat_errors = [abs(r['input']['desired_curvature_1pm']-r['input']['actual_curvature_1pm'])
                for r in saturation if r['saturation']]
  spectral = []
  for part in parts:
    if len(part) < 4:
      continue
    x = np.array([r['requested'] for r in part])
    frequencies = np.fft.rfftfreq(len(x), DT)
    fft = np.fft.rfft((x-x.mean())*np.hanning(len(x)))
    spectral.append(float(np.sum(np.abs(fft[(frequencies >= 1.2) & (frequencies <= 50.)])**2)/len(x)**2))
  events = []
  for row in rows:
    for event in row['reset_events']:
      if event not in ('STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT'):
        continue
      window = [r for r in rows if row['index'] <= r['index'] <= row['index']+99]
      events.append({'event': event, 'index': row['index'], 'support': len(window), 'expected': 100,
                     'peak_mask': 'ALL_FINITE_EVENT_WINDOW_ROWS_INCLUDING_PRESSED_AND_INACTIVE',
                     'peak_support': {'valid': len(window), 'total': 100, 'unavailable': 100-len(window)},
                     'requested_abs_peak': max(abs(r['requested']) for r in window),
                     'derivative_mask': 'ADJACENT_ACTIVE_NOT_PRESSED_NO_RESET_PAIRS_ONLY',
                     'boundary_jump_status': 'OUTSIDE_FROZEN_DERIVATIVE_ESTIMATOR_SUPPORT',
                     'requested_at_event': row['requested'],
                     'requested_before_event': rows[row['index']-1]['requested'] if row['index'] else None,
                     'requested_derivative': distribution(list(map(abs, derivative(segments(window), 'requested'))), max(0, len(window)-1))})
  return {
    'trajectory': {
      'tracking': distribution(errors, len(rows)), 'phases': phases,
      'heading_abs': distribution([abs(r['heading']) for r in valid], len(rows)),
      'pose_y_abs': distribution([abs(r['pose_y']) for r in valid], len(rows)),
      'saturation_tracking_loss': {**distribution(sat_errors, len(sat_errors)),
                                   'conditioning': {'observed': len(saturation), 'eligible': len(valid), 'total': len(rows),
                                                    'saturated': len(sat_errors), 'unsaturated': len(saturation)-len(sat_errors),
                                                    'observation_unavailable': len(valid)-len(saturation)},
                                   'empty_reason': 'NO_SATURATED_SUPPORT' if not sat_errors else None},
      'early_distance': {str(d): {'heading_rad': distance_value(rows, d, 'heading'),
                                 'pose_y_m': distance_value(rows, d, 'pose_y')}
                         for d in policy['distance']['queries_m']},
      'longer_horizon_descriptive_only': {'max_observed_x_m': max(r['pose_x'] for r in rows),
                                         'final_heading_rad': rows[-1]['heading'], 'final_pose_y_m': rows[-1]['pose_y']}},
    'smoothness': {
      'requested_derivative_abs': distribution(list(map(abs, derivative(parts, 'requested'))), max(0, len(rows)-1)),
      'applied_derivative_abs': distribution(list(map(abs, derivative(parts, 'applied'))), max(0, len(rows)-1)),
      'zero_crossing': {'count': sign_changes(parts, 'requested'), 'eligible_samples': len(valid), 'total_samples': len(rows)},
      'sign_reversal': {'count': sign_changes(parts, 'requested'), 'eligible_samples': len(valid), 'total_samples': len(rows)},
      'high_frequency_content': distribution(spectral, len(parts)),
      'saturation': {'observed': len(saturation), 'total': len(rows),
                     'occupancy': sum(r['saturation'] for r in saturation)/len(saturation) if saturation else None,
                     'eligible_adjacent_pairs': sum(len(p)-1 for p in parts),
                     'observed_adjacent_pairs': sum(a['saturation'] is not None and b['saturation'] is not None
                                                    for p in parts for a, b in zip(p, p[1:], strict=False)),
                     'transitions': sum(a['saturation'] != b['saturation'] for part in parts for a, b in zip(part, part[1:], strict=False)
                                        if a['saturation'] is not None and b['saturation'] is not None)},
      'event_transients': events},
    'coverage': {'eligible': len(valid), 'total': len(rows), 'unavailable': len(rows)-len(valid),
                 'contiguous_segments': len(parts), 'policy_sha256': policy['receipt_sha256']},
  }


def effects(baseline, candidate):
  if len(baseline) != len(candidate) or any(a['input']['time_s'] != b['input']['time_s'] for a, b in zip(baseline, candidate, strict=True)):
    raise ValueError('PAIRED_TIMEBASE_REQUIRED')
  keys = ('requested', 'applied', 'curvature', 'heading', 'pose_y')
  delta = {key: [b[key]-a[key] for a, b in zip(baseline, candidate, strict=True)] for key in keys}
  names = ('REQUESTED_OUTPUT_DIFFERENCE_PRESENT', 'APPLIED_OUTPUT_DIFFERENCE_PRESENT',
           'CURVATURE_EFFECT_PRESENT', 'HEADING_EFFECT_PRESENT', 'POSE_EFFECT_PRESENT')
  states = [name for key, name in zip(keys, names, strict=True) if any(v != 0. for v in delta[key])]
  states = states or ['NO_OUTPUT_DIFFERENCE']
  if any(r['saturation'] for r in candidate):
    states.append('OUTPUT_LIMITED')
  absolute = sum(abs(v)*DT for v in delta['requested'])
  signed = sum(v*DT for v in delta['requested'])
  if absolute and signed == 0.:
    states.append('TEMPORALLY_CANCELED')
  distances = {}
  for d in load()['metrics']['distance']['queries_m']:
    b = distance_value(baseline, d, 'pose_y')
    c = distance_value(candidate, d, 'pose_y')
    distances[str(d)] = {'delta_pose_y_m': c-b if c is not None and b is not None else None,
                         'status': 'DESCRIPTIVE_ONLY' if c is not None and b is not None else 'DISTANCE_NOT_REACHED'}
  if any(r['status'] == 'DISTANCE_NOT_REACHED' for r in distances.values()):
    states.append('DISTANCE_NOT_REACHED')
  signs = [math.copysign(1., v) for v in delta['requested'] if v]
  return {'states': states, 'same_time_peak_absolute_delta': {k: max(map(abs, v)) for k, v in delta.items()},
          'same_time_signed_final_delta': {k: v[-1] for k, v in delta.items()},
          'requested_delta_sign_changes': sum(a != b for a, b in zip(signs, signs[1:], strict=False)),
          'requested_delta_abs_integral': absolute, 'requested_delta_signed_integral': signed,
          'cancellation_ratio': 1-abs(signed)/absolute if absolute else None,
          'early_distance_effect': distances, 'physical_performance_claim': False}
