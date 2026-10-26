"""Version 2 synthetic inputs; does not replace frozen v1 catalogs/evidence.

Lane visibility, supplied path bias and supplied stop/lead targets are fixtures,
not perception/planner implementations. Consumers must report which fields they
actually exercise. Delay variants are separate reset epochs, never concatenated.
"""
from dataclasses import asdict, dataclass, replace
import math

from openpilot.tools.cyber_autotune.contracts import finite_number
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


LATERAL_CASES = (
  'straight', 'constant_left', 'constant_right', 'increasing_left', 'increasing_right',
  's_curve', 'ramp', 'edge_bias', 'asymmetry', 'abrupt_curvature', 'lane_loss',
  'laneless_transition', 'override_recovery', 'speed_sweep', 'delay_sweep', 'rate_limit',
  'saturation', 'friction_gain', 'pose_jitter', 'sensor_dropout', 'out_of_order',
  'nonfinite', 'long_straight_entry', 'curve_exit', 'low_speed_alley', 'provided_avoidance',
)
LONGITUDINAL_CASES = (
  'stopped_lead', 'lead_deceleration', 'cut_in', 'cut_out', 'hard_braking_lead',
  'congestion', 'stop_start', 'signal_stop', 'false_stop', 'plan_dropout', 'radar_model_disagreement',
  'speed_limit', 'grade', 'delay_sweep', 'stale', 'invalid_timestamp', 'nonfinite', 'emergency_fallback',
)
FAULT_CODES = {
  'lat_sensor_dropout': 'INVALID_SENSOR', 'lat_out_of_order': 'INVALID_TIMEBASE', 'lat_nonfinite': 'NONFINITE_INPUT',
  'long_plan_dropout': 'INVALID_SENSOR', 'long_stale': 'INVALID_TIMEBASE',
  'long_invalid_timestamp': 'INVALID_TIMEBASE', 'long_nonfinite': 'NONFINITE_INPUT',
}


@dataclass(frozen=True)
class StressCase:
  case_id: str
  axis: str
  duration_s: float = 6.
  dt_s: float = .01
  physical_delays_s: tuple[float, ...] = (.03,)
  expected_input_status: str = 'VALID'


@dataclass(frozen=True)
class StressFrame:
  time_ns: int
  speed_mps: float = 18.
  curvature: float = .002
  path_bias_m: float = 0.
  friction_scale: float = 1.
  gain_scale: float = 1.
  pose_yaw_bias: float = 0.
  lane_visible: bool = True
  active: bool = True
  steering_pressed: bool = False
  valid: bool = True
  lead_available: bool = True
  lead_speed_mps: float = 10.
  lead_distance_reset_m: float | None = None
  supplied_accel_mps2: float = 0.
  target_speed_mps: float = 10.
  stop_target_m: float | None = None
  should_stop: bool = False
  stop_required: bool = False
  grade_accel: float = 0.
  radar_model_disagreement: bool = False


def catalog() -> tuple[StressCase, ...]:
  cases = []
  for axis, prefix, names in (('lateral', 'lat_', LATERAL_CASES), ('longitudinal', 'long_', LONGITUDINAL_CASES)):
    for name in names:
      case_id = prefix + name
      cases.append(StressCase(case_id, axis,
                              duration_s=12. if name in ('long_straight_entry', 'stop_start', 'congestion') else 6.,
                              physical_delays_s=(0., .03, .15, .30) if name == 'delay_sweep' else (.03,),
                              expected_input_status=FAULT_CODES.get(case_id, 'VALID')))
  return tuple(cases)


def catalog_digest() -> str:
  return digest(canonical({'version': 'synthetic-stress-v2',
                           'cases': [{'spec': asdict(case), 'input_sha256': input_digest(case)} for case in catalog()]}))


def input_digest(case: StressCase) -> str:
  """Bind actual generated fields, including explicit JSON-safe invalid markers."""
  return frame_digest(frames(case))


def frame_digest(rows: tuple[StressFrame, ...]) -> str:
  payload = []
  for row in rows:
    values = asdict(row)
    for key, value in values.items():
      if type(value) is float and not math.isfinite(value):
        values[key] = {'invalid_float': repr(value)}
    payload.append(values)
  return digest(canonical(payload))


def _lateral(kind: str, index: int, count: int) -> StressFrame:
  phase = index / (count - 1)
  frame = StressFrame(index * 10_000_000)
  envelope = min(1., phase * 6., (1. - phase) * 6.)
  if kind == 'straight':
    frame = replace(frame, curvature=0.)
  elif kind in ('constant_left', 'constant_right'):
    frame = replace(frame, curvature=.002 if kind.endswith('left') else -.002)
  elif kind in ('increasing_left', 'increasing_right'):
    frame = replace(frame, curvature=.006 * phase * (1 if kind.endswith('left') else -1))
  elif kind in ('s_curve', 'low_speed_alley'):
    frame = replace(frame, curvature=.004 * math.sin(2 * math.pi * phase), speed_mps=5. if kind == 'low_speed_alley' else 18.)
  elif kind == 'provided_avoidance':
    # Supplied 0.6 m lane-relative bump; small-angle curvature of that path.
    # This is a fixture, not obstacle detection or a runtime centering offset.
    duration = (count - 1) * .01
    frame = replace(frame, path_bias_m=.6 * math.sin(math.pi * phase) ** 2,
                    curvature=1.2 * math.pi ** 2 * math.cos(2 * math.pi * phase) / (duration ** 2 * frame.speed_mps ** 2))
  elif kind == 'ramp':
    frame = replace(frame, curvature=.008 * envelope, speed_mps=24.)
  elif kind == 'edge_bias':
    frame = replace(frame, curvature=.002 * envelope, path_bias_m=.25 * math.sin(math.pi * phase))
  elif kind == 'asymmetry':
    frame = replace(frame, curvature=.004 * math.sin(2 * math.pi * phase), gain_scale=.8 if phase < .5 else 1.2)
  elif kind == 'abrupt_curvature':
    frame = replace(frame, curvature=.006 if phase >= .5 else 0.)
  elif kind in ('lane_loss', 'laneless_transition'):
    visible = not (.3 <= phase <= .7) if kind == 'lane_loss' else phase < .5
    frame = replace(frame, lane_visible=visible, curvature=.002 * envelope)
  elif kind == 'override_recovery':
    pressed = .3 <= phase <= .5
    frame = replace(frame, active=not (.3 <= phase <= .55), steering_pressed=pressed)
  elif kind == 'speed_sweep':
    frame = replace(frame, speed_mps=5. + 25. * phase)
  elif kind == 'rate_limit':
    frame = replace(frame, curvature=.008 * math.sin(12 * math.pi * phase))
  elif kind == 'saturation':
    frame = replace(frame, speed_mps=30., curvature=.014 * envelope)
  elif kind == 'friction_gain':
    frame = replace(frame, friction_scale=.6 if phase < .5 else 1.4, gain_scale=.8 if phase < .5 else 1.2)
  elif kind == 'pose_jitter':
    frame = replace(frame, pose_yaw_bias=.005 * math.sin(index * 2. * math.pi / 7.))
  elif kind == 'long_straight_entry':
    frame = replace(frame, curvature=0. if phase < .8 else .004 * (phase - .8) / .2)
  elif kind == 'curve_exit':
    frame = replace(frame, curvature=.004 * max(0., 1. - phase * 2.))
  return frame


def _longitudinal(kind: str, index: int, count: int) -> StressFrame:
  phase = index / (count - 1)
  frame = StressFrame(index * 10_000_000, speed_mps=10., curvature=0.)
  braking = kind in ('stopped_lead', 'lead_deceleration', 'hard_braking_lead', 'signal_stop')
  if braking:
    hard = kind == 'hard_braking_lead'
    lead_speed = 0. if kind in ('stopped_lead', 'signal_stop') else max(0., 10. - phase * (20. if hard else 6.))
    frame = replace(frame, lead_speed_mps=lead_speed, supplied_accel_mps2=(-3. if hard else -2.) if phase >= .2 else 0.,
                    should_stop=phase >= .65, stop_required=True, stop_target_m=30., target_speed_mps=0.,
                    lead_available=kind != 'signal_stop')
  elif kind in ('cut_in', 'cut_out'):
    available = phase >= .3 if kind == 'cut_in' else phase < .3
    frame = replace(frame, lead_available=available, lead_speed_mps=6.,
                    lead_distance_reset_m=12. if index == math.ceil(.3 * (count - 1)) else None,
                    supplied_accel_mps2=-2. if available else 0.)
  elif kind in ('congestion', 'stop_start'):
    stop = phase < .45 or (.65 <= phase <= .8 and kind == 'congestion')
    frame = replace(frame, speed_mps=2., should_stop=stop, supplied_accel_mps2=-1.5 if stop else 1.,
                    stop_required=stop, target_speed_mps=0. if stop else 4., lead_speed_mps=0. if stop else 4.,
                    stop_target_m=4. if stop else None)
  elif kind == 'false_stop':
    stop = .2 <= phase <= .7
    frame = replace(frame, speed_mps=.3, should_stop=stop, supplied_accel_mps2=-1. if stop else 1.,
                    target_speed_mps=2., lead_speed_mps=4., stop_required=False)
  elif kind == 'radar_model_disagreement':
    frame = replace(frame, radar_model_disagreement=.3 <= phase <= .7, supplied_accel_mps2=-1. if phase >= .3 else 0.)
  elif kind == 'speed_limit':
    frame = replace(frame, target_speed_mps=6. if phase >= .4 else 10., supplied_accel_mps2=-1. if phase >= .4 else 0.)
  elif kind == 'grade':
    frame = replace(frame, grade_accel=.6 * math.sin(2 * math.pi * phase))
  elif kind == 'emergency_fallback':
    frame = replace(frame, active=phase < .5, supplied_accel_mps2=-3.)
  else:
    frame = replace(frame, supplied_accel_mps2=.5 * math.sin(2 * math.pi * phase))
  return frame


def frames(case: StressCase) -> tuple[StressFrame, ...]:
  """Generate only declared cases; no arbitrary duration or unseen case accepted."""
  if type(case) is not StressCase or case not in catalog():
    raise ValueError('UNDECLARED_STRESS_CASE')
  count = round(case.duration_s / case.dt_s)
  make = _lateral if case.axis == 'lateral' else _longitudinal
  kind = case.case_id.split('_', 1)[1]
  rows = [make(kind, index, count) for index in range(count)]
  index = count // 2
  if kind in ('sensor_dropout', 'plan_dropout'):
    rows[index] = replace(rows[index], valid=False)
  elif kind in ('stale', 'out_of_order', 'invalid_timestamp'):
    time_ns = -1 if kind == 'invalid_timestamp' else rows[index - 1].time_ns - (1 if kind == 'out_of_order' else 0)
    rows[index] = replace(rows[index], time_ns=time_ns)
  elif kind == 'nonfinite':
    rows[index] = replace(rows[index], curvature=float('nan'))
  return tuple(rows)


def validate_frames(rows, dt_s: float) -> str:
  """Inspect actual inputs independently of catalog expected outcomes."""
  if type(rows) is not tuple or not 4 <= len(rows) <= 60_000 or dt_s != .01:
    return 'INVALID_FRAME_CONTRACT'
  previous = None
  flags = ('lane_visible', 'active', 'steering_pressed', 'valid', 'lead_available', 'should_stop', 'stop_required', 'radar_model_disagreement')
  optional = ('lead_distance_reset_m', 'stop_target_m')
  for row in rows:
    if type(row) is not StressFrame or any(type(getattr(row, key)) is not bool for key in flags):
      return 'INVALID_FRAME_CONTRACT'
    if type(row.time_ns) is not int or not 0 <= row.time_ns < 2 ** 63 or (previous is not None and row.time_ns - previous != 10_000_000):
      return 'INVALID_TIMEBASE'
    for key, value in asdict(row).items():
      if key in flags or key == 'time_ns' or (key in optional and value is None):
        continue
      if not finite_number(value):
        return 'NONFINITE_INPUT'
    if not row.valid:
      return 'INVALID_SENSOR'
    if not (0 <= row.speed_mps <= 40 and abs(row.curvature) <= .05 and abs(row.path_bias_m) <= 1 and
            .2 <= row.friction_scale <= 2 and .2 <= row.gain_scale <= 2 and abs(row.pose_yaw_bias) <= .1 and
            0 <= row.lead_speed_mps <= 40 and -3.5 <= row.supplied_accel_mps2 <= 2 and
            0 <= row.target_speed_mps <= 40 and abs(row.grade_accel) <= 2):
      return 'INVALID_FRAME_DOMAIN'
    if any(getattr(row, key) is not None and not 0 <= getattr(row, key) <= 1e6 for key in optional):
      return 'INVALID_FRAME_DOMAIN'
    previous = row.time_ns
  return 'VALID'
