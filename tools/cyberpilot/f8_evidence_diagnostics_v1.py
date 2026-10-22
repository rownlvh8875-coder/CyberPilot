"""F8 diagnostic sidecars, separate from the unchanged F7 metric/gate contract.

Local-tone/grid arithmetic follows pinned F8 f8_analysis.py SHA256
be47fee3704865c979d7c22a19a165a070d59c0da6c42b9c2882120543274db1.
Direct-sum oracle follows f8_frequency_oracle.py SHA256
404e2b4fc9cb4aa2f729117f4e7ff7704194a00d6e591b4ca1911cdd524259b4.
No excitation, controller, performance qualification, or candidate selection.
"""

import cmath
import math

import numpy as np

from tools.cyberpilot import offline_multiobjective_gates_v1 as g
from tools.cyberpilot import offline_multiobjective_metrics_v1 as m
from tools.cyberpilot.f8_evidence_reader_v1 import need


def tone(frames: tuple[g.Frame, ...], hz: float, window: str) -> dict[str, object]:
  need(hz in (0.25, 0.5, 1.0, 2.0) and window in ('periodic_hann', 'rectangular') and len(frames) == 4000, 'F8_TONE_CONTRACT')
  x = np.array([f.desired for f in frames[800:]])
  y = np.array([f.curvature for f in frames[800:]])
  size, hop = 800, 400
  w = np.ones(size) if window == 'rectangular' else np.hanning(size + 1)[:-1]
  xs, ys = [], []
  for start in range(0, len(x) - size + 1, hop):
    xx, yy = x[start : start + size], y[start : start + size]
    xs.append(np.fft.rfft((xx - np.mean(xx)) * w))
    ys.append(np.fft.rfft((yy - np.mean(yy)) * w))
  X, Y = np.array(xs), np.array(ys)
  pxx, pyy = np.mean(abs(X) ** 2, axis=0), np.mean(abs(Y) ** 2, axis=0)
  pxy = np.mean(np.conj(X) * Y, axis=0)
  k = int(round(hz * size / 100))
  need(float(pxx[k]) > 0 and float(pyy[k]) > 0, 'F8_TONE_ENERGY')
  h = pxy[k] / pxx[k]
  t = np.arange(len(x)) / 100
  design = np.column_stack((np.sin(2 * math.pi * hz * t), np.cos(2 * math.pi * hz * t), np.ones(len(t))))
  bx, by = np.linalg.lstsq(design, x, rcond=None)[0], np.linalg.lstsq(design, y, rcond=None)[0]
  ls = complex(by[0], by[1]) / complex(bx[0], bx[1])
  return {
    'hz': hz,
    'window': window,
    'segments': len(X),
    'gain': float(abs(h)),
    'phase_rad': float(np.angle(h)),
    'coherence': float(abs(pxy[k]) ** 2 / (pxx[k] * pyy[k])),
    'ls_gain': float(abs(ls)),
    'ls_phase_rad': float(np.angle(ls)),
    'discard_s': 8,
    'segment_s': 8,
    'overlap_fraction': 0.5,
    'scope': 'LOCAL_EXCITED_BIN_ONLY',
    'full_response_qualified': False,
  }


def _sum(values: list[complex]) -> complex:
  return complex(math.fsum(z.real for z in values), math.fsum(z.imag for z in values))


def direct_tone(frames: tuple[g.Frame, ...], hz: float, window: str) -> dict[str, float]:
  """Independent scalar summation: no FFT or least-squares solver."""
  x, y = [f.desired for f in frames[800:]], [f.curvature for f in frames[800:]]
  size, hop = 800, 400
  w = [1.0 if window == 'rectangular' else 0.5 - 0.5 * math.cos(2 * math.pi * n / size) for n in range(size)]
  terms = [cmath.exp(-2j * math.pi * hz * n / 100) for n in range(size)]
  xs, ys = [], []
  for start in range(0, len(x) - size + 1, hop):
    xx, yy = x[start : start + size], y[start : start + size]
    mx, my = math.fsum(xx) / size, math.fsum(yy) / size
    xs.append(_sum([(v - mx) * a * b for v, a, b in zip(xx, w, terms, strict=True)]))
    ys.append(_sum([(v - my) * a * b for v, a, b in zip(yy, w, terms, strict=True)]))
  pxx, pyy = math.fsum(abs(z) ** 2 for z in xs) / len(xs), math.fsum(abs(z) ** 2 for z in ys) / len(ys)
  pxy = _sum([a.conjugate() * b for a, b in zip(xs, ys, strict=True)]) / len(xs)
  h = pxy / pxx

  def projection(values: list[float]) -> complex:
    return (
      complex(
        math.fsum(v * math.sin(2 * math.pi * hz * n / 100) for n, v in enumerate(values)),
        math.fsum(v * math.cos(2 * math.pi * hz * n / 100) for n, v in enumerate(values)),
      )
      * 2
      / len(values)
    )

  ls = projection(y) / projection(x)
  return {'gain': abs(h), 'phase_rad': cmath.phase(h), 'coherence': abs(pxy) ** 2 / (pxx * pyy), 'ls_gain': abs(ls), 'ls_phase_rad': cmath.phase(ls)}


def settling(frames: tuple[g.Frame, ...], spec: dict[str, object]) -> list[dict[str, object]]:
  """The historical explanatory 2/5/10%, .5/1/2s grid; never an acceptance rule."""
  name = g.text(spec['id'])
  if spec['group'] == 'frequency' or 'ramp' in name or 's_curve' in name:
    return []
  target = np.array([f.desired for f in frames])
  y = np.array([f.curvature for f in frames])
  changes = np.flatnonzero(np.diff(target) != 0) + 1
  out: list[dict[str, object]] = []
  for pos, start in enumerate(changes):
    end = int(changes[pos + 1]) if pos + 1 < len(changes) else len(frames)
    delta = target[start] - target[start - 1]
    error = abs(y[start:end] - target[start])
    for pct in (0.02, 0.05, 0.10):
      inside = error <= pct * abs(delta)
      for sustained in (0.5, 1.0, 2.0):
        count = int(round(sustained * 100)) + 1
        first = None
        for j in range(max(0, len(inside) - count + 1)):
          if bool(np.all(inside[j : j + count])):
            first = (j + 1) * 0.01
            break
        outside = np.flatnonzero(~inside)
        last = int(outside[-1]) + 1 if len(outside) else 0
        permanent = (last + 1) * 0.01 if len(inside) - last >= count else None
        direction = 1 if delta > 0 else -1
        out.append(
          {
            'step_start_s': int(start) * 0.01,
            'segment_end_s': end * 0.01,
            'tolerance_fraction_of_step': pct,
            'sustained_s': sustained,
            'first_hold_s': first,
            'permanent_to_segment_end_s': permanent,
            'overshoot_1pm': max(0.0, float(max(direction * (y[start:end] - target[start])))),
            'saturation_frames': sum(abs(f.command) == 1 for f in frames[start:end]),
            'status': 'DEFINITION_APPROVAL_REQUIRED',
          }
        )
  return out


def scalar_metrics(frames: tuple[g.Frame, ...]) -> dict[str, object]:
  """Small reconciliation view of unchanged F7 arithmetic."""
  a = m.arrays(frames)
  error = a['curvature'] - a['desired']
  pos = m.position_components(a['actual'], a['reference'])
  sat = m.saturation(a['command'], g.DT)
  return {
    'curvature_rmse': m.rms(error),
    'heading_rms': m.rms(a['actual'][:, 2] - a['reference'][:, 2]),
    'normal_rms': pos['normal']['rms'],
    'xy_rms': pos['euclidean']['rms'],
    'signed_area': float(np.sum(error) * g.DT),
    'saturation_frames': sat['frames'],
    'saturation_fraction': sat['occupancy'],
  }


def initial_aware_derivative(frames: tuple[g.Frame, ...], initial_applied: float) -> dict[str, object]:
  applied = np.array([f.applied for f in frames])
  derivative = np.diff(np.r_[initial_applied, applied]) / g.DT
  return {
    'physical_applied_derivative': m.stats(derivative),
    'prior_applied': initial_applied,
    'F7_convention_preserved': 'F7 prepends zero for both delivered and applied; not a physical initial-state claim',
  }


def reset_window(raw: object, spec: dict[str, object]) -> list[dict[str, object]]:
  rows = g.sequence(raw)
  at = spec['reset_sequence']
  if at is None:
    return []
  n = g.integer(at)
  out = []
  for i in (n - 1, n, n + 1):
    r = g.mapping(rows[i])
    src = g.mapping(g.mapping(r['candidate'])['source_result'])
    out.append(
      {
        'sequence': i,
        'native_before_sha256': g.sha(g.canonical(r['native_state_before'])),
        'governor_before': src.get('state_before'),
        'governor_after': src.get('state_after'),
        'governor_events': src.get('reset_events'),
        'governor_action': src.get('action'),
        'command': r['command'],
        'curvature': g.mapping(r['plant_after'])['curvature_1pm'],
        'yaw': g.mapping(r['plant_after'])['yaw_rate_rad_s'],
        'pose': r['pose_after'],
        'physical_before_sha256': g.sha(g.canonical(r['plant_before'])),
        'physical_after_sha256': g.sha(g.canonical(r['plant_after'])),
      }
    )
  return out
