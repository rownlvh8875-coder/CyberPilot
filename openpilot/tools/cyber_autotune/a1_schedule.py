"""Whole-schedule admission for fixed SYNTHETIC A1 experiments, not vehicle bounds.

No live caller, IO, candidate search, fallback/clamp or mutable controller state.
Factor units: (m/s^2)/normalized command; friction: normalized command.
Bounds are software-test coordinates, deliberately not a public tune policy API.
"""
import struct

from openpilot.selfdrive.controls.lib.cyber_lateral.speed_aware_tune import SpeedAwareTuneTable, evaluate_speed_aware_tune
from openpilot.tools.cyber_autotune.native_protocol import MAX_FRAMES, finite


RANGES = ((3.5, 4.5), (0., .25))
MAX_BASELINE_DELTAS = (1 / 16, 1 / 128)
MAX_FRAME_DELTAS = (1 / 64, 1 / 1024)  # per native 10 ms, not per second


def float32(value):
  if not finite(value):
    raise ValueError('INVALID_A1_NUMBER')
  try:
    result = struct.unpack('<f', struct.pack('<f', value))[0]
  except (OverflowError, struct.error) as exc:
    raise ValueError('A1_WIRE_OVERFLOW') from exc
  if not finite(result):
    raise ValueError('A1_WIRE_OVERFLOW')
  return result


def _check_values(values, baseline):
  for value, initial, (lower, upper), delta in zip(values, baseline, RANGES, MAX_BASELINE_DELTAS, strict=True):
    if not finite(value) or not lower <= value <= upper or abs(value - initial) > delta:
      raise ValueError('OUTSIDE_SYNTHETIC_A1_BOUNDS')


def prepare_schedule(table, speeds, baseline_factor, baseline_friction):
  """Return immutable (wire speed, requested factor/friction, wire factor/friction).

  Validate every knot and transition, including baseline->first frame, before any
  controller is run. Actual native storage must subsequently equal wire values.
  """
  baseline = (baseline_factor, baseline_friction)
  if not all(finite(value) for value in baseline):
    raise ValueError('INVALID_A1_BASELINE')
  _check_values(baseline, baseline)
  if type(table) is not SpeedAwareTuneTable or type(speeds) is not tuple or not 0 < len(speeds) <= MAX_FRAMES:
    raise ValueError('INVALID_A1_SCHEDULE')
  for point in table.points:
    if not finite(point.steering_response) or point.steering_response != 1.:
      raise ValueError('UNSUPPORTED_STEERING_RESPONSE')
    _check_values((point.lat_accel_factor, point.friction), baseline)
    _check_values((float32(point.lat_accel_factor), float32(point.friction)), baseline)
  rows = []
  previous = baseline
  for speed in speeds:
    effective_speed = float32(speed)
    # Reject raw domain exits too: rounding must not repair an invalid request.
    if not table.points[0].speed_mps <= speed <= table.points[-1].speed_mps:
      raise ValueError('OUTSIDE_A1_SPEED_DOMAIN')
    evaluated = evaluate_speed_aware_tune(table, effective_speed, *baseline, 1.)
    if not evaluated.valid:
      raise ValueError('OUTSIDE_A1_SPEED_DOMAIN')
    requested = (evaluated.lat_accel_factor, evaluated.friction)
    _check_values(requested, baseline)
    effective = tuple(float32(value) for value in requested)
    _check_values(effective, baseline)
    if any(abs(value - old) > maximum for value, old, maximum in zip(effective, previous, MAX_FRAME_DELTAS, strict=True)):
      raise ValueError('A1_TRANSITION_EXCEEDED')
    rows.append((effective_speed, *requested, *effective))
    previous = effective
  return tuple(rows)
