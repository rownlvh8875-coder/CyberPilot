"""Separate SG smoothness and descriptive tracking metrics; frozen pre-run policy."""

import math
import numpy as np

from openpilot.tools.cyber_autotune import trajectory_v0_metrics as base
from openpilot.tools.cyber_autotune.smoothness_v0_freeze import load


def command_metrics(values):
  if any(not math.isfinite(v) for v in values):
    raise ValueError('FINITE_COMMAND_METRICS_REQUIRED')
  d = [(b - a) / 0.01 for a, b in zip(values, values[1:], strict=False)]
  signs = [v > 0 for v in values if v != 0.0]
  n = len(values)
  spectral = None
  if n >= 4:
    x = np.array(values)
    f = np.fft.rfftfreq(n, 0.01)
    fft = np.fft.rfft((x - x.mean()) * np.hanning(n))
    spectral = float(np.sum(np.abs(fft[(f >= 1.2) & (f <= 50.0)]) ** 2) / n**2)
  sat = [abs(v) == 1.0 for v in values]
  return {
    'derivative_abs': base.distribution(list(map(abs, d)), max(0, n - 1)),
    'derivative_rms': math.sqrt(sum(v * v for v in d) / len(d)) if d else None,
    'total_variation': math.fsum(abs(b - a) for a, b in zip(values, values[1:], strict=False)),
    'direct_zero_crossings': sum(a * b < 0.0 for a, b in zip(values, values[1:], strict=False)),
    'nonzero_sign_reversals': sum(a != b for a, b in zip(signs, signs[1:], strict=False)),
    'high_frequency_energy': spectral,
    'spectral_support': {'valid': n if spectral is not None else 0, 'total': n, 'unavailable': 0 if spectral is not None else n},
    'saturation': {
      'count': sum(sat),
      'occupancy': sum(sat) / n if n else None,
      'transitions': sum(a != b for a, b in zip(sat, sat[1:], strict=False)),
      'valid': n,
      'total': n,
      'unavailable': 0,
    },
    'count_coverage': {'valid': n, 'total': n, 'unavailable': 0},
    'adjacent_metric_coverage': {
      'derivative_RMS_TV_direct_crossing': {'valid': max(0, n - 1), 'total': max(0, n - 1), 'unavailable': 0},
      'nonzero_sign_reversal': {'nonzero_samples': len(signs), 'total_samples': n, 'unavailable': 0},
    },
  }


def settling(inputs, outputs):
  if len(inputs) != len(outputs):
    raise ValueError('PAIRED_COMMAND_SUPPORT_REQUIRED')
  start = len(inputs) - 1
  while start > 0 and inputs[start - 1] == inputs[-1]:
    start -= 1
  n = len(inputs) - start
  if n < 2:
    return {'settling_s': None, 'steady_bias': None, 'valid': 0, 'total': max(n, 0), 'unavailable': max(n, 0)}
  settled = next((i for i in range(start, len(inputs)) if all(v == inputs[-1] for v in outputs[i:])), None)
  return {
    'settling_s': (settled - start) * 0.01 if settled is not None else None,
    'steady_bias': math.fsum(b - a for a, b in zip(inputs[start:], outputs[start:], strict=True)) / n,
    'valid': n,
    'total': n,
    'unavailable': 0,
    'constant_run_start': start,
  }


def evaluate(rows):
  for i, row in enumerate(rows):
    if row['index'] != i or row['input']['dt_s'] != 0.01 or not math.isclose(row['input']['time_s'], i * 0.01, abs_tol=1e-12, rel_tol=0.0):
      raise ValueError('CONTIGUOUS_SG_METRICS_REQUIRED')
  # Existing trajectory routines are reused, with post-SG rail saturation explicitly relabeled.
  reused = base.evaluate(rows)
  reused['trajectory']['saturation_semantics'] = 'GOVERNOR_OUTPUT_RAIL_ONLY_NOT_NATIVE_PRELIMIT_INTENT'
  u = [r['pre'] for r in rows]
  y = [r['requested'] for r in rows]
  events = []
  for r in rows:
    for event in r['reset_events']:
      if event not in ('STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT', 'INACTIVE'):
        continue
      i = r['index']
      window = rows[i : i + 100]
      events.append(
        {
          'event': event,
          'index': i,
          'valid': len(window),
          'total': 100,
          'unavailable': 100 - len(window),
          'boundary_jump': y[i] - y[i - 1] if i else None,
          'pre_command_metrics': command_metrics([v['pre'] for v in window]),
          'post_command_metrics': command_metrics([v['requested'] for v in window]),
          'settling': settling([v['pre'] for v in window], [v['requested'] for v in window]),
        }
      )
  return {
    'trajectory': reused['trajectory'],
    'coverage': reused['coverage'],
    'eligible_secondary_smoothness': reused['smoothness'],
    'smoothness_primary': {
      'mask': 'ALL_CONTIGUOUS_SAMPLES_INCLUDING_EVENT_BOUNDARIES',
      'pre_governor': command_metrics(u),
      'requested': command_metrics(y),
      'applied': command_metrics([r['applied'] for r in rows]),
      'governor_limit': {
        'count': sum(r['pre'] != r['requested'] for r in rows),
        'occupancy': sum(r['pre'] != r['requested'] for r in rows) / len(rows),
        'valid': len(rows),
        'total': len(rows),
        'unavailable': 0,
      },
      'settling': settling(u, y),
      'event_transients': events,
    },
    'metric_policy_sha256': load()['metrics']['receipt_sha256'],
  }


def effects(baseline, candidate):
  result = base.effects(baseline, candidate)
  b = evaluate(baseline)
  c = evaluate(candidate)
  states = [s.replace('REQUESTED_OUTPUT_DIFFERENCE_PRESENT', 'GOVERNOR_OUTPUT_DIFFERENCE_PRESENT') for s in result['states']]
  for name, key in (('REQUESTED_DERIVATIVE_EFFECT_PRESENT', 'requested'), ('APPLIED_DERIVATIVE_EFFECT_PRESENT', 'applied')):
    if b['smoothness_primary'][key]['derivative_abs'] != c['smoothness_primary'][key]['derivative_abs']:
      states.append(name)
  if b['smoothness_primary']['requested']['nonzero_sign_reversals'] != c['smoothness_primary']['requested']['nonzero_sign_reversals']:
    states.append('REVERSAL_EFFECT_PRESENT')
  if b['smoothness_primary']['requested']['saturation'] != c['smoothness_primary']['requested']['saturation']:
    states.append('SATURATION_EFFECT_PRESENT')
  if c['trajectory']['tracking']['p95'] > b['trajectory']['tracking']['p95']:
    states.append('TRACKING_TRADEOFF_PRESENT')
  if not c['smoothness_primary']['event_transients']:
    states.append('EVENT_SUPPORT_UNAVAILABLE')
  return {**result, 'states': states, 'acceptance': False, 'tracking_hard_threshold': 'THRESHOLD_UNJUSTIFIED', 'feedback_loop_stability_evaluated': False}
