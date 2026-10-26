"""Descriptive plant displacement vs a declared, nonphysical resolution scale."""

import bisect

import numpy as np

from openpilot.tools.cyber_autotune.camera_calibration_evidence import seal as receipt
from openpilot.tools.cyber_autotune.native_protocol import finite
from openpilot.tools.cyber_autotune.curvature_yaw_attribution import MAGNITUDE_SPLIT_1PM

DISTANCES_M = (5.0, 10.0, 15.0, 20.0, 25.0, 30.0)
BASIS = {'units': 'm', 'frame': 'DESCRIPTIVE_PLANT_WORLD_X_FORWARD_Y_LATERAL', 'distance': 'POSE_X_M_PER_ARM', 'effect': 'LATERAL_POSITION'}
FIREWALL = dict.fromkeys(
  (
    'qualification_allowed',
    'reference_promotable',
    'sealed_reference_allowed',
    'vehicle_activation_allowed',
    'candidate_accepted',
    'detector_retuned',
    'candidate_retuned',
    'independent_ground_truth',
  ),
  False,
)


def seal(fields):
  return receipt(
    {
      **fields,
      **FIREWALL,
      'total_physical_bound_m': None,
      'sealed_reference': 'NOT_GENERATED',
      'hypotheses_exhaustive': False,
      'vehicle_status': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    }
  )


def sign(value):
  return 1 if value > 0 else -1 if value < 0 else 0


def stats(values):
  values = list(values)
  if not all(finite(v) for v in values):
    raise ValueError('FINITE_DIAGNOSTIC_STATISTICS_REQUIRED')
  return {
    'count': len(values),
    'median': float(np.median(values)) if values else None,
    'p90': float(np.percentile(values, 90)) if values else None,
    'p95': float(np.percentile(values, 95)) if values else None,
    'maximum': max(values) if values else None,
    'minimum': min(values) if values else None,
  }


def at_distance(samples, distance, basis):
  """Interpolate each arm on its own x, never equate integrated path length to x."""
  bad = {'status': 'UNCOMPARABLE_COORDINATE_BASIS'}
  if basis != BASIS or not finite(distance) or distance < 0:
    return bad
  if not samples:
    return {'status': 'COVERAGE_UNAVAILABLE'}
  fields = ('pose_x_m', 'pose_y_m', 'time_s', 'speed_mps', 'desired_curvature_1pm')
  if any(not isinstance(p, dict) or any(not finite(p.get(k)) for k in fields) or not isinstance(p.get('phase'), str) for p in samples):
    return bad
  xs = [p['pose_x_m'] for p in samples]
  ts = [p['time_s'] for p in samples]
  if any(b <= a for a, b in zip(xs, xs[1:], strict=False)) or any(b <= a for a, b in zip(ts, ts[1:], strict=False)):
    return bad
  if distance < xs[0] or distance > xs[-1]:
    return {'status': 'DISTANCE_NOT_REACHED'}
  hi = bisect.bisect_left(xs, distance)
  if xs[hi] == distance:
    p = samples[hi]
    return {'status': 'AVAILABLE', **{k: p[k] for k in fields}, 'phase': p['phase'], 'bracket_indexes': [hi, hi], 'phase_transition_bracket': False}
  lo = hi - 1
  f = (distance - xs[lo]) / (xs[hi] - xs[lo])
  p, q = samples[lo], samples[hi]
  return {
    'status': 'AVAILABLE',
    **{k: p[k] + f * (q[k] - p[k]) for k in fields},
    'phase': p['phase'],
    'bracket_indexes': [lo, hi],
    'phase_transition_bracket': p['phase'] != q['phase'],
  }


def classify(effect, minimum, maximum):
  if not all(finite(v) for v in (effect, minimum, maximum)) or minimum <= 0 or maximum < minimum:
    return 'COVERAGE_UNAVAILABLE'
  if abs(effect) < minimum:
    return 'EFFECT_BELOW_DECLARED_ENVELOPE'
  if abs(effect) > maximum:
    return 'EFFECT_EXCEEDS_DECLARED_ENVELOPE'
  return 'EFFECT_OVERLAPS_DECLARED_ENVELOPE'


def compare(baseline, candidate, current, envelope, repeatable):
  if repeatable is not True:
    return {'classification': 'REPEATABILITY_FAILED'}
  if not all(finite(v) for v in (baseline, candidate, current)):
    return {'classification': 'UNCOMPARABLE_COORDINATE_BASIS'}
  effect = candidate - baseline
  lo, hi = (envelope.get('minimum_p95_m'), envelope.get('maximum_p95_m')) if isinstance(envelope, dict) else (None, None)
  status = classify(effect, lo, hi)
  if status == 'COVERAGE_UNAVAILABLE':
    return {'classification': status}
  return {
    'classification': status,
    'baseline_lateral_m': baseline,
    'current_lateral_m': current,
    'candidate_lateral_m': candidate,
    'candidate_minus_baseline_m': effect,
    'candidate_minus_current_m': candidate - current,
    'absolute_effect_m': abs(effect),
    'effect_sign': sign(effect),
    'effect_to_min_envelope_ratio': abs(effect) / lo,
    'effect_to_max_envelope_ratio': abs(effect) / hi,
    'ratio_semantics': 'DIAGNOSTIC_EFFECT_TO_ENVELOPE_RATIO',
    'direction_semantics': 'SIGNED_PLANT_DISPLACEMENT_NOT_IMPROVEMENT',
  }


def direction_status(signs):
  nonzero = set(signs) - {0}
  if nonzero == {-1, 1}:
    return 'DIRECTIONALLY_INCONSISTENT_TRADEOFF'
  return 'ONE_DISPLACEMENT_DIRECTION_ONLY_NOT_IMPROVEMENT' if nonzero else 'NO_DISPLACEMENT'


def speed_bucket(speed):
  return 'LOW' if speed < 10 else 'MID' if speed < 20 else 'HIGH'


def curvature_bucket(curvature):
  return 'ZERO' if curvature == 0 else 'GENTLE' if abs(curvature) <= MAGNITUDE_SPLIT_1PM else 'SHARP'
