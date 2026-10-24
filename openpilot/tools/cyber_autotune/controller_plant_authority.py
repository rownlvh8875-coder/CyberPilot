"""Pure descriptive signal/geometry diagnostics. No controller or vehicle authority."""

import bisect
import math

from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


def number(value):
  if type(value) not in (int, float) or not math.isfinite(value):
    raise ValueError('FINITE_SCALAR_REQUIRED')
  return float(value)


def command(value, unit):
  value = number(value)
  if unit != 'NORMALIZED_TORQUE' or abs(value) > 1.:
    raise ValueError('NORMALIZED_COMMAND_REQUIRED')
  return value


def arc(k, s):
  k, s = number(k), number(s)
  angle = k * s
  # sin(a/2)^2 avoids catastrophic cancellation near zero curvature.
  return {'heading_rad': angle, 'pose_x_m': s if k == 0 else math.sin(angle) / k,
          'pose_y_m': 0. if k == 0 else 2 * math.sin(angle / 2) ** 2 / k}


def oracle(k, speed, duration, dt):
  k, speed, duration, dt = map(number, (k, speed, duration, dt))
  if speed <= 0 or dt <= 0 or duration <= 0:
    raise ValueError('POSITIVE_TIME_SPEED_REQUIRED')
  steps = round(duration / dt)
  if steps < 1 or not math.isclose(steps * dt, duration, rel_tol=1e-12):
    raise ValueError('EXACT_INTEGER_STEPS_REQUIRED')
  h = x = y = 0.
  for _ in range(steps):
    h += k * speed * dt
    x += speed * math.cos(h) * dt
    y += speed * math.sin(h) * dt
  truth = arc(k, speed * duration)
  error = math.hypot(x - truth['pose_x_m'], y - truth['pose_y_m'])
  # Right Riemann vector integral bound: |f'| <= |k|v², dt*T/2.
  bound = abs(k) * speed ** 2 * duration * dt / 2
  rounding = 64 * math.ulp(max(1., speed * duration)) * steps
  return {'analytic': truth, 'discrete': {'heading_rad': h, 'pose_x_m': x, 'pose_y_m': y},
          'position_error_m': error, 'riemann_bound_m': bound, 'roundoff_allowance_m': rounding,
          'within_riemann_bound': error <= bound + rounding}


def signal(values, dt):
  dt = number(dt)
  if dt <= 0:
    raise ValueError('POSITIVE_DT_REQUIRED')
  values = [number(x) for x in values]
  signs = [1 if x > 0 else -1 for x in values if x != 0]
  signed, absolute = math.fsum(values) * dt, math.fsum(map(abs, values)) * dt
  return {'count': len(values), 'maximum_absolute': max(map(abs, values), default=None),
          'signed_integral': signed, 'absolute_integral': absolute,
          'sign_changes': sum(x != y for x, y in zip(signs, signs[1:], strict=False)),
          'cancellation_ratio': None if absolute == 0 else 1 - abs(signed) / absolute,
          'maximum_derivative_per_s': max((abs(y - x) / dt for x, y in zip(values, values[1:], strict=False)), default=0.)}


def ratio(numerator, denominator):
  numerator, denominator = number(numerator), number(denominator)
  if denominator == 0:
    return {'value': None, 'status': 'ZERO_DENOMINATOR'}
  result = numerator / denominator
  return {'value': result if math.isfinite(result) else None,
          'status': 'AVAILABLE' if math.isfinite(result) else 'NONFINITE_RATIO'}


def query(samples, distance):
  distance = number(distance)
  xs = [number(p['pose_x_m']) for p in samples]
  if not xs or any(y <= x for x, y in zip(xs, xs[1:], strict=False)):
    return None
  if distance < xs[0] or distance > xs[-1]:
    return None
  hi = bisect.bisect_left(xs, distance)
  if xs[hi] == distance:
    return {k: v for k, v in samples[hi].items() if type(v) in (int, float)}
  lo = hi - 1
  weight = (distance - xs[lo]) / (xs[hi] - xs[lo])
  return {k: samples[lo][k] + weight * (v - samples[lo][k])
          for k, v in samples[hi].items() if type(v) in (int, float) and type(samples[lo].get(k)) in (int, float)}


def seal(row):
  row = {**row, **dict.fromkeys(('qualification_allowed', 'reference_promotable', 'sealed_reference_allowed',
                                        'vehicle_activation_allowed', 'candidate_acceptance_allowed'), False),
         'total_physical_bound_m': None, 'sealed_reference_status': 'NOT_GENERATED',
         'vehicle_status': 'NOT_READY', 'vehicle_verification': 'REAL_VEHICLE_UNVERIFIED',
         'vehicle_activation_status': 'VEHICLE_ACTIVATION_BLOCKED'}
  row.pop('receipt_sha256', None)
  return {**row, 'receipt_sha256': digest(canonical(row))}


def query_status(samples, distance):
  xs = [number(p['pose_x_m']) for p in samples]
  if not xs:
    return 'COVERAGE_UNAVAILABLE'
  if any(y <= x for x, y in zip(xs, xs[1:], strict=False)):
    return 'UNCOMPARABLE_COORDINATE_BASIS'
  return 'AVAILABLE' if xs[0] <= distance <= xs[-1] else 'DISTANCE_NOT_REACHED'
