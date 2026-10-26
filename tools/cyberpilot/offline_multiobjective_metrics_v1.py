"""Pure F6 metric diagnostics; all performance thresholds remain unapproved.

Definitions are loaded byte-exact from the F6 proposal. Missing evidence is not replaced
by a performance threshold. F6 r2_attribution.py source SHA885897a4aa7fa9764f19edbdd590b4d64ed28c2f6270d7732ea629809369e688.
"""

import math
import numpy as np
from numpy.typing import NDArray

from tools.cyberpilot.offline_multiobjective_gates_v1 import DT, Frame, require, text, number as gates_number

Array = NDArray[np.float64]


def rms(a: Array) -> float:
  return float(np.sqrt(np.mean(a * a)))


def stats(a: Array) -> dict[str, float]:
  return {'rms': rms(a), 'p95': float(np.percentile(abs(a), 95)), 'max': float(np.max(abs(a)))}


def area(a: Array, dt: float) -> dict[str, object]:
  positive = float(np.sum(a[a > 0]) * dt)
  negative = float(np.sum(a[a < 0]) * dt)
  absolute = positive - negative
  net = positive + negative
  return {
    'positive': positive,
    'negative': negative,
    'absolute': absolute,
    'net': net,
    'cancellation_fraction': 1 - abs(net) / absolute if absolute else None,
    'rms': rms(a),
    'sequence_sha256': _array_sha(a),
    'interpretation': 'Signed cancellation does not qualify tracking accuracy',
  }


def _array_sha(a: Array) -> str:
  from tools.cyberpilot.offline_multiobjective_gates_v1 import sha

  return sha(a.astype('<f8').tobytes())


def reversals(a: Array) -> int:
  nonzero = np.sign(a[a != 0])
  return int(np.count_nonzero(nonzero[1:] != nonzero[:-1]))


def saturation(a: Array, dt: float) -> dict[str, object]:
  runs: list[dict[str, object]] = []
  start = 0
  prior = 0
  for i in range(len(a) + 1):
    sign = int(np.sign(a[i])) if i < len(a) and abs(a[i]) == 1 else 0
    if sign != prior:
      if prior:
        runs.append({'start_frame': start, 'end_frame_exclusive': i, 'sign': prior, 'frames': i - start, 'duration_s': (i - start) * dt})
      start, prior = i, sign
  duration = np.array([gates_number(r['duration_s']) for r in runs], dtype=np.float64)
  frames = int(np.count_nonzero(abs(a) == 1))
  return {
    'events': len(runs),
    'rail_sign_reversals': sum(a['sign'] != b['sign'] for a, b in zip(runs[:-1], runs[1:], strict=True)),
    'frames': frames,
    'denominator_frames': len(a),
    'occupancy': frames / len(a),
    'duration_s': frames * dt,
    'event_duration_p95_s': float(np.percentile(duration, 95)) if len(duration) else 0.0,
    'event_duration_max_s': float(np.max(duration)) if len(duration) else 0.0,
    'runs': runs,
    'definition': 'Contiguous exact +/-1 rail and sign; sign change starts a new episode',
    'qualification': 'PERFORMANCE_NOT_QUALIFIED',
  }


def spectrum(a: Array, dt: float) -> dict[str, object]:
  centered = a - np.mean(a)
  n = len(a)
  f = np.fft.rfftfreq(n, dt)
  transformed = np.fft.rfft(centered)
  amplitude = abs(transformed) / n
  amplitude[1 : -1 if n % 2 == 0 else None] *= 2
  power = abs(transformed) ** 2 / n**2
  power[1 : -1 if n % 2 == 0 else None] *= 2
  variance = float(np.mean(centered**2))
  require(math.isclose(float(sum(power)), variance, rel_tol=2e-12, abs_tol=2e-12), 'E_PARSEVAL', 'HG08')
  peak = int(np.argmax(power[1:]) + 1) if len(power) > 1 and variance else 0
  return {
    'mean': float(np.mean(a)),
    'sample_count': n,
    'dt_s': dt,
    'window': 'RECTANGULAR_FULL_HORIZON',
    'amplitude': amplitude.tolist(),
    'amplitude_normalization': 'abs(DFT)/N; interior positive bins doubled; DC and even Nyquist undoubled',
    'variance': variance,
    'frequency_hz': f.tolist(),
    'bin_power': power.tolist(),
    'psd': (power / (1 / (n * dt))).tolist(),
    'peak_hz': float(f[peak]) if peak else None,
    'parseval_residual': abs(float(sum(power)) - variance),
    'scope': 'Full supplied horizon; DC removed; one-sided periodogram, not vehicle stability margin',
  }


def position_components(actual: Array, reference: Array) -> dict[str, dict[str, float]]:
  dx, dy = actual[:, 0] - reference[:, 0], actual[:, 1] - reference[:, 1]
  normal = -dx * np.sin(reference[:, 2]) + dy * np.cos(reference[:, 2])
  along = dx * np.cos(reference[:, 2]) + dy * np.sin(reference[:, 2])
  return {'normal': stats(normal), 'along': stats(along), 'euclidean': stats(np.hypot(dx, dy))}


def polyline_distance(actual: Array, reference: Array) -> dict[str, object]:
  # One point against O(n) segments at a time; never allocate an n*n matrix.
  xy = np.vstack(([0.0, 0.0], reference[:, :2]))
  starts = xy[:-1]
  delta = np.diff(xy, axis=0)
  norm = np.sum(delta**2, axis=1)
  require(bool(np.all(norm > 0)), 'E_REFERENCE_SEGMENT', 'HG02')
  distances = []
  for point in actual[:, :2]:
    t = np.sum((point - starts) * delta, axis=1) / norm
    closest = starts + np.clip(t, 0, 1)[:, None] * delta
    distances.append(math.sqrt(float(np.min(np.sum((closest - point) ** 2, axis=1)))))
  return {**stats(np.array(distances, dtype=np.float64)), 'scope': 'Auxiliary finite reference polyline; no substitution or time shift'}


def prefix_crossings(left: Array, right: Array, dt: float) -> list[float]:
  require(len(left) == len(right) and len(left) > 0, 'E_COMPARISON_LENGTH', 'HG02')
  signs = np.sign(np.cumsum(left**2) - np.cumsum(right**2))
  nonzero = np.flatnonzero(signs)
  return [float((b + 1) * dt) for a, b in zip(nonzero[:-1], nonzero[1:], strict=True) if signs[a] != signs[b]]


def arrays(frames: tuple[Frame, ...]) -> dict[str, Array]:
  require(bool(frames), 'E_EMPTY', 'HG02')
  out = {
    key: np.array([getattr(f, key) for f in frames], dtype=np.float64)
    for key in ('speed', 'desired', 'curvature', 'yaw', 'command', 'applied', 'native', 'actual', 'reference', 'roll')
  }
  require(all(bool(np.all(np.isfinite(a))) for a in out.values()), 'E_NONFINITE', 'HG02')
  return out


def prefix_metrics(frames: tuple[Frame, ...], seconds: float) -> dict[str, object]:
  n = round(seconds / DT)
  require(0 < n <= len(frames) and math.isclose(n * DT, seconds, abs_tol=1e-12), 'E_HORIZON', 'HG02')
  a = arrays(frames[:n])
  positions = position_components(a['actual'], a['reference'])
  return {
    'horizon_s': seconds,
    'frames': n,
    'curvature_rmse': rms(a['curvature'] - a['desired']),
    'normal_rms': positions['normal']['rms'],
    'euclidean_rms': positions['euclidean']['rms'],
    'heading_end': float(a['actual'][-1, 2] - a['reference'][-1, 2]),
  }


def calculate(frames: tuple[Frame, ...], plant: dict[str, object], arm: str, definitions: list[dict[str, object]]) -> dict[str, dict[str, object]]:
  del plant  # Frame boundary already validated the exact pinned F6 mathematical Plant.
  with np.errstate(over='raise', invalid='raise', divide='raise'):
    a = arrays(frames)
    dt = DT
    error = a['curvature'] - a['desired']
    yaw_error = a['yaw'] + a['speed'] * a['desired']
    heading = a['actual'][:, 2] - a['reference'][:, 2]
    pos = position_components(a['actual'], a['reference'])
    delta = np.diff(np.r_[0.0, a['command']])
    applied_delta = np.diff(np.r_[0.0, a['applied']])
    sat = saturation(a['command'], dt)
    prefix = [prefix_metrics(frames, h) for h in (10.0, 20.0, 40.0, 80.0) if round(h / dt) <= len(frames)]
    values: dict[str, object] = {
      'curvature_rmse': rms(error),
      'curvature_p95': float(np.percentile(abs(error), 95)),
      'curvature_max': float(max(abs(error))),
      'signed_curvature_area': {**area(error, dt), 'yaw_error': area(yaw_error, dt)},
      'heading_error': {**stats(heading), 'end': float(heading[-1]), 'yaw_integral_rad': float(sum(yaw_error) * dt)},
      'normal_position': pos['normal'],
      'along_position': pos['along'],
      'euclidean_position': pos['euclidean'],
      'geometric_polyline_distance': polyline_distance(a['actual'], a['reference']),
      'command_magnitude': {'delivered': stats(a['command']), 'applied': stats(a['applied'])},
      'command_variation': float(sum(abs(delta))),
      'command_derivative': {'delivered': stats(delta / dt), 'applied': stats(applied_delta / dt), 'previous_command': 0.0},
      'direction_reversals': {'command': reversals(a['command']), 'curvature': reversals(a['curvature']), 'yaw': reversals(a['yaw'])},
      'oscillation_spectrum': {'command': spectrum(a['command'], dt), 'curvature_error': spectrum(error, dt), 'yaw_error': spectrum(yaw_error, dt)},
      'saturation_fraction': {'value': sat['occupancy'], 'frames': sat['frames'], 'denominator_frames': len(frames), 'rail': 1.0},
      'saturation_events': sat,
      'rate_contract_scope': {
        'arm': arm,
        'applicable_source_checked': 'HG06',
        'A3_optional_rate_is_not_global_safety_rate': True,
        'downstream_vehicle_rate': 'METRIC_UNAVAILABLE',
      },
      'lateral_acceleration': {
        'curvature_speed2': stats(a['curvature'] * a['speed'] ** 2),
        'yaw_speed': stats(a['yaw'] * a['speed']),
        'scope': 'Synthetic sign convention, no vehicle acceptance threshold',
      },
      'actuator_delay': {'physical_steps': 2, 'seconds': 2 * dt, 'queue_check': 'HG05', 'controller_prediction': 'METRIC_UNAVAILABLE'},
      'reset_behavior': {
        'event_frames': [f.sequence for f in frames if f.reset],
        'inactive_frames': sum(not f.active for f in frames),
        'driver_frames': sum(f.driver for f in frames),
        'source_derived_event_check': 'HG05',
      },
      'horizon_sensitivity': {
        'prefixes': prefix,
        'missing_horizons_s': [h for h in (10.0, 20.0, 40.0, 80.0) if round(h / dt) > len(frames)],
        'qualification': 'PERFORMANCE_NOT_QUALIFIED',
      },
      'long_term_accumulation': {
        'horizon_s': len(frames) * dt,
        'signed_curvature': area(error, dt),
        'heading': stats(heading),
        'normal': pos['normal'],
        'euclidean': pos['euclidean'],
      },
    }
    missing = {
      'frequency_response': 'FULL_RESPONSE_EXCITATION_UNAVAILABLE',
      'settling_time': 'THRESHOLD_APPROVAL_REQUIRED',
      'transition_and_s_curve': 'SCENARIO_COVERAGE_EVIDENCE_REQUIRED',
      'speed_and_disturbance': 'VARYING_SPEED_AND_UNCERTAINTY_EVIDENCE_REQUIRED',
      'initial_state_coverage': 'NONZERO_INITIAL_STATE_EVIDENCE_UNAVAILABLE',
      'measurement_robustness': 'NOISE_BIAS_LATENCY_FRESHNESS_EVIDENCE_UNAVAILABLE',
    }
    out = {}
    for definition in definitions:
      name = text(definition['name'])
      require(name in values or name in missing, 'E_UNKNOWN_METRIC')
      out[name] = {
        'definition': definition,
        'status': 'METRIC_COMPUTED' if name in values else 'METRIC_UNAVAILABLE',
        'value': values.get(name),
        'reason': missing.get(name),
        'threshold_status': 'THRESHOLD_APPROVAL_REQUIRED',
        'performance_status': 'PERFORMANCE_NOT_QUALIFIED',
      }
    return out


def compare(left: tuple[Frame, ...], right: tuple[Frame, ...]) -> dict[str, object]:
  require(len(left) == len(right), 'E_COMPARISON_LENGTH', 'HG02')
  la, ra = arrays(left), arrays(right)
  le = -((la['actual'][:, 0] - la['reference'][:, 0]) * np.sin(la['reference'][:, 2])) + (la['actual'][:, 1] - la['reference'][:, 1]) * np.cos(
    la['reference'][:, 2]
  )
  re = -((ra['actual'][:, 0] - ra['reference'][:, 0]) * np.sin(ra['reference'][:, 2])) + (ra['actual'][:, 1] - ra['reference'][:, 1]) * np.cos(
    ra['reference'][:, 2]
  )
  lxy = np.linalg.norm(la['actual'][:, :2] - la['reference'][:, :2], axis=1)
  rxy = np.linalg.norm(ra['actual'][:, :2] - ra['reference'][:, :2], axis=1)
  normals = prefix_crossings(le, re, DT)
  xy = prefix_crossings(lxy, rxy, DT)
  # F6 reports the nontrivial >=10s crossings; early identities remain recorded separately.
  crossing = {'normal_s': [t for t in normals if t > 10], 'euclidean_s': [t for t in xy if t > 10], 'all_normal_s': normals, 'all_euclidean_s': xy}
  lp, rp = position_components(la['actual'], la['reference']), position_components(ra['actual'], ra['reference'])
  lv = [rms(la['curvature'] - la['desired']), lp['normal']['rms'], lp['euclidean']['rms'], rms(np.diff(np.r_[0.0, la['command']]) / DT)]
  rv = [rms(ra['curvature'] - ra['desired']), rp['normal']['rms'], rp['euclidean']['rms'], rms(np.diff(np.r_[0.0, ra['command']]) / DT)]
  labels = ['LOWER_OBSERVED' if b < a else 'HIGHER_OBSERVED' if b > a else 'IDENTICAL_OBSERVED' for a, b in zip(lv, rv, strict=True)]
  tradeoff = 'LOWER_OBSERVED' in labels and 'HIGHER_OBSERVED' in labels
  return {
    'status': 'TRADEOFF_OBSERVED' if tradeoff else 'PERFORMANCE_NOT_QUALIFIED',
    'horizon_status': 'HORIZON_DEPENDENT_TRADEOFF' if crossing['normal_s'] or crossing['euclidean_s'] else 'PERFORMANCE_NOT_QUALIFIED',
    'crossings': crossing,
    'metric_order': ['curvature_rmse', 'normal_rms', 'euclidean_rms', 'command_derivative_rms'],
    'descriptive_change': labels,
    'performance_status': 'PERFORMANCE_NOT_QUALIFIED',
    'selected_candidate': None,
  }


def compare_metrics(left: dict[str, dict[str, object]], right: dict[str, dict[str, object]]) -> dict[str, object]:
  """Numerical differences across every metric slot, never a weighted score or ranking."""

  def leaves(value: object, path: str = '') -> dict[str, float]:
    if type(value) in (int, float):
      return {path: gates_number(value)}
    result = {}
    if isinstance(value, dict):
      for key, item in value.items():
        if isinstance(key, str):
          result.update(leaves(item, path + '.' + key))
    elif isinstance(value, list) and path == '.prefixes':
      # Compare matched horizon records; retain full spectra/event vectors only once per trace.
      for i, item in enumerate(value):
        result.update(leaves(item, path + '[' + str(i) + ']'))
    return result

  ordered = {
    'curvature_rmse',
    'curvature_p95',
    'curvature_max',
    'normal_position',
    'along_position',
    'euclidean_position',
    'geometric_polyline_distance',
    'command_magnitude',
    'command_variation',
    'command_derivative',
    'saturation_fraction',
  }
  out = {}
  for name, a in left.items():
    b = right[name]
    fields = {}
    if a['status'] == 'METRIC_COMPUTED' and b['status'] == 'METRIC_COMPUTED':
      av, bv = leaves(a['value']), leaves(b['value'])
      for path, x in av.items():
        if path not in bv:
          continue
        y = bv[path]
        change = 'IDENTICAL_OBSERVED' if y == x else 'LOWER_OBSERVED' if y < x else 'HIGHER_OBSERVED'
        fields[path] = {'left': x, 'right': y, 'difference': y - x, 'change': change if name in ordered else 'NUMERICAL_DIFFERENCE_NOT_ORDERED'}
    out[name] = {
      'status': 'METRIC_COMPUTED' if fields else 'METRIC_UNAVAILABLE',
      'fields': fields,
      'comparison_scope': 'SCALAR_SUMMARIES_AND_MATCHED_HORIZON_PREFIXES; full vectors retained per trace',
      'performance_status': 'PERFORMANCE_NOT_QUALIFIED',
      'threshold_status': 'THRESHOLD_APPROVAL_REQUIRED',
    }
  return out
