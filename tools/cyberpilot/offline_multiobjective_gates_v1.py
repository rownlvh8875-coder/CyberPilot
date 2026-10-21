"""Checked historical-trace boundary. Arithmetic adapted from the independently verified F6 Oracle.

F6 audit_core.py SHA256 871ba09c9c0c31ba94d594df2c861f43139c31b4dda36176e116007cc757682a.
No controller imports/calls. Rate arithmetic below verifies recorded output; it emits no command.
"""

from dataclasses import dataclass
import hashlib
import json
import math

DT = 0.01
TIME_NS = 10_000_000
ORACLE_TOLERANCE = 2e-12  # F6 arithmetic comparison only; not a performance threshold.
RESET_FRAME = 800  # Pinned F5 f5_scenarios.py, CONTROLLER_RESET case only.
ARMS = ('A0', 'A2', 'A3', 'SG-A', 'A3-R1', 'A3-R2')
INPUT_KEYS = frozenset(
  (
    'sequence',
    'time_ns',
    'speed_mps',
    'actual_curvature_1pm',
    'desired_curvature_1pm',
    'roll_rad',
    'active',
    'steering_pressed',
    'safety_limited',
    'curvature_limited',
  )
)
ROW_KEYS = frozenset(
  (
    'sequence',
    't_start_s',
    't_end_s',
    'input',
    'native_input',
    'native_request',
    'raw_candidate',
    'delivered',
    'applied',
    'actual_applied_before',
    'plant_before',
    'plant_after',
    'native_state_before',
    'native_state_after',
    'pose_before',
    'pose_after',
    'reference_pose',
    'curvature_error_1pm',
    'heading_error_rad',
    'reference_normal_deviation_m',
    'reset_events',
    'explicit_controller_reset',
    'policy_measured_yaw_rad_s',
    'policy_sha256',
    'source_sha256',
    'candidate_state_after',
    'previous_candidate_before',
    'delivery_gate',
    'source_result',
    'curvature_times_speed2_mps2',
    'yaw_times_speed_mps2',
    'input_sha256',
    'previous_receipt_sha256',
    'receipt_sha256',
  )
)
PLANT = {
  'command_gain_1pm': 0.004,
  'command_inv_speed_gain_per_s': 0.002,
  'command_limit': 1.0,
  'command_speed_gain_s_per_m2': 0.0002,
  'curvature_ar': 0.92,
  'curvature_intercept_1pm': 0.0,
  'delay_steps': 2,
  'dt_s': DT,
  'max_speed_mps': 30.0,
  'min_speed_mps': 2.5,
  'roll_gain_1pm_per_rad': 0.001,
  'yaw_ar': 0.75,
  'yaw_bias_rad_s': 0.0,
}


class EvidenceError(ValueError):
  def __init__(self, code: str, gate: str = 'HG01'):
    super().__init__(code)
    self.code = code
    self.gate = gate


def require(condition: bool, code: str, gate: str = 'HG01') -> None:
  if not condition:
    raise EvidenceError(code, gate)


def mapping(value: object) -> dict[str, object]:
  require(isinstance(value, dict), 'E_RECORD')
  out: dict[str, object] = {}
  if isinstance(value, dict):
    for key, item in value.items():
      require(isinstance(key, str), 'E_KEY')
      if isinstance(key, str):
        out[key] = item
  return out


def sequence(value: object) -> list[object]:
  if not isinstance(value, list):
    raise EvidenceError('E_ARRAY')
  return list(value)


def number(value: object) -> float:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    raise EvidenceError('E_FINITE_NUMBER', 'HG02')
  try:
    finite = math.isfinite(value)
    result = float(value)
  except OverflowError as exc:
    raise EvidenceError('E_FINITE_NUMBER', 'HG02') from exc
  require(finite, 'E_FINITE_NUMBER', 'HG02')
  return result


def integer(value: object) -> int:
  if type(value) is not int:
    raise EvidenceError('E_INTEGER', 'HG02')
  return value


def flag(value: object) -> bool:
  if type(value) is not bool:
    raise EvidenceError('E_BOOL', 'HG02')
  return value


def text(value: object) -> str:
  if not isinstance(value, str):
    raise EvidenceError('E_TEXT')
  return value


def canonical(value: object) -> bytes:
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw: bytes) -> str:
  return hashlib.sha256(raw).hexdigest()


def sealed(value: dict[str, object], key: str) -> None:
  require(value.get(key) == sha(canonical({k: v for k, v in value.items() if k != key})), 'E_RECEIPT')


def point(value: object) -> tuple[float, float, float]:
  values = sequence(value)
  require(len(values) == 3, 'E_POSE', 'HG05')
  return number(values[0]), number(values[1]), number(values[2])


def near(a: object, b: object, gate: str = 'HG05') -> None:
  if type(a) in (int, float) and type(b) in (int, float):
    require(math.isclose(number(a), number(b), abs_tol=ORACLE_TOLERANCE, rel_tol=ORACLE_TOLERANCE), 'E_RECURRENCE', gate)
  elif isinstance(a, dict) and isinstance(b, dict):
    require(a.keys() == b.keys(), 'E_STATE_KEYS', gate)
    for k in a:
      near(a[k], b[k], gate)
  elif isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
    require(len(a) == len(b), 'E_STATE_LENGTH', gate)
    for x, y in zip(a, b, strict=True):
      near(x, y, gate)
  else:
    require(type(a) is type(b) and a == b, 'E_STATE', gate)


def rate_step(request: float, previous: float) -> float:
  """Independent Oracle of existing 3/384 rise, 7/384 fall per .01s source contract."""
  old, target = abs(previous), abs(request)
  if request != 0 and previous != 0 and request * previous < 0:
    magnitude = max(0.0, old - 7 / 384)
    return math.copysign(magnitude, previous) if magnitude else 0.0
  if target > old:
    return math.copysign(min(target, old + 3 / 384), request)
  return math.copysign(max(target, old - 7 / 384), request if request else previous)


def required_static_command(curvature: float, speed: float, roll: float, plant: dict[str, object]) -> float:
  gain = number(plant['command_gain_1pm']) + number(plant['command_speed_gain_s_per_m2']) * speed + number(plant['command_inv_speed_gain_per_s']) / speed
  return abs(
    ((1 - number(plant['curvature_ar'])) * curvature - number(plant['curvature_intercept_1pm']) - number(plant['roll_gain_1pm_per_rad']) * roll) / gain
  )


@dataclass(frozen=True)
class Frame:
  sequence: int
  time_s: float
  speed: float
  desired: float
  curvature: float
  yaw: float
  command: float
  applied: float
  native: float
  actual: tuple[float, float, float]
  reference: tuple[float, float, float]
  roll: float
  active: bool
  driver: bool
  reset: bool


def verify_frames(raw: object, item: dict[str, object]) -> tuple[Frame, ...]:
  rows = [mapping(r) for r in sequence(raw)]
  require(0 < len(rows) <= 20_000 and len(rows) == integer(item['frames']), 'E_FRAME_COUNT', 'HG02')
  arm = text(item['arm'])
  require(arm in ARMS, 'E_ARM')
  near(mapping(item['plant']), PLANT, 'HG04')
  k = yaw = 0.0
  pose = (0.0, 0.0, 0.0)
  reference = (0.0, 0.0, 0.0)
  queue = [0.0, 0.0]
  prior_receipt = '0' * 64
  native_before: object = None
  prior_active = prior_driver = None
  previous_rate = previous_sg = previous_selected = previous_k = None
  prior_selection = None
  debt = 0.0
  until = -1
  applied_before = 0.0
  out = []
  for i, r in enumerate(rows):
    require(set(r) == ROW_KEYS | ({'remediation'} if arm.startswith('A3-R') else set()), 'E_FRAME_KEYS', 'HG02')
    require(integer(r['sequence']) == i, 'E_SEQUENCE', 'HG02')
    x = mapping(r['input'])
    require(set(x) == INPUT_KEYS, 'E_INPUT_KEYS', 'HG02')
    require(integer(x['sequence']) == i and integer(x['time_ns']) == i * TIME_NS, 'E_TIMEBASE', 'HG02')
    near(r['t_start_s'], i * DT, 'HG02')
    near(r['t_end_s'], (i + 1) * DT, 'HG02')
    v, desired, roll = number(x['speed_mps']), number(x['desired_curvature_1pm']), number(x['roll_rad'])
    active, driver = flag(x['active']), flag(x['steering_pressed'])
    flag(x['safety_limited'])
    flag(x['curvature_limited'])
    require(2.5 <= v <= 30.0, 'E_PLANT_SPEED', 'HG04')
    require(r['source_sha256'] == item['source_sha256'] and r['policy_sha256'] == item['policy_sha256'], 'E_SOURCE_BINDING')
    require(r['input_sha256'] == sha(canonical(x)), 'E_INPUT_SHA')
    require(r['previous_receipt_sha256'] == prior_receipt, 'E_RECEIPT_CHAIN')
    sealed(r, 'receipt_sha256')
    prior_receipt = text(r['receipt_sha256'])
    events = []
    if i == 0:
      events.append('EXPERIMENT_START')
    if not active and (i == 0 or prior_active):
      events.append('INACTIVE')
    if driver and (i == 0 or not prior_driver):
      events.append('STEERING_PRESSED')
    if i > 0 and prior_driver and not driver:
      events.append('RELEASE')
    if i > 0 and not prior_active and active:
      events.append('REENGAGEMENT')
    explicit = item['case_id'] == 'controller_reset' and i == RESET_FRAME
    require(flag(r['explicit_controller_reset']) == explicit, 'E_EXPLICIT_RESET', 'HG05')
    if explicit:
      events.append('CONTROLLER_RESET')
    require(sequence(r['reset_events']) == events, 'E_RESET_EVENTS', 'HG05')
    prior_active, prior_driver = active, driver
    near(number(x['actual_curvature_1pm']), k)
    near(r['plant_before'], {'curvature_1pm': k, 'yaw_rate_rad_s': yaw, 'command_history': queue})
    near(r['pose_before'], pose)
    ni = {key: x[key] for key in INPUT_KEYS if key not in ('sequence', 'time_ns')}
    ni.update(dt_s=DT, time_s=i * DT)
    near(r['native_input'], ni)
    if i == 0 or explicit:
      # Pinned F5 NativeBaseline reset creates a fresh controller and empty reference buffer.
      near(
        r['native_state_before'],
        {
          'jerk_filter_initialized': True,
          'jerk_filter_x': 0.0,
          'pending_events': ['SCENARIO_BOUNDARY' if explicit else 'EXPERIMENT_START'],
          'pid': [0.0] * 5,
          'prior_input': None,
          'reference_buffer': [0.0] * 100,
          'sat_time': 0.0,
        },
      )
    elif native_before is not None:
      near(r['native_state_before'], native_before)
    native_before = r['native_state_after']
    near(r['actual_applied_before'], applied_before)
    near(r['policy_measured_yaw_rad_s'], yaw)
    native = number(r['native_request'])
    raw_candidate = number(r['raw_candidate'])
    command = number(r['delivered'])
    require(all(abs(u) <= 1 for u in (native, raw_candidate, command, number(r['applied']))), 'E_COMMAND_RANGE', 'HG03')
    reset = bool(events) or not active
    expected = native
    if arm == 'A2':
      require(5 <= v <= 10, 'E_ENVELOPE_SPEED', 'HG06')
      cap = 0.3 + (v - 5) / 5 * (0.2 - 0.3)
      expected = max(-cap, min(cap, native))
    elif arm == 'A3':
      anchor = applied_before if reset or previous_rate is None else previous_rate
      expected = rate_step(native, anchor)
      previous_rate = expected
    elif arm.startswith('A3-R'):
      reset = reset or driver
      if reset:
        previous_selected = previous_k = None
        until = -1
        debt = 0.0
      anchor = applied_before if previous_selected is None else previous_selected
      limited = rate_step(native, anchor)
      err = yaw + desired * v
      if active and not driver:
        debt += err * DT
      transition = desired != (0.0 if previous_k is None else previous_k)
      if transition:
        until = i + 2 + math.ceil(math.log(0.01) / math.log(0.92)) - 1
      expected, selection = limited, 'ORIGINAL_RATE'
      if not active:
        expected, selection = 0.0, 'INACTIVE_ZERO'
      elif driver:
        expected, selection = native, 'STOCK_DRIVER_OBSERVATION'
      elif arm == 'A3-R1' and i <= until:
        expected, selection = native, 'STOCK_TRANSITION'
      elif arm == 'A3-R2' and debt * err > 0 and (native - limited) * err < 0:
        expected, selection = native, 'STOCK_GROWING_ERROR'
      meta = mapping(r['remediation'])
      near(meta['rate_anchor'], anchor, 'HG06')
      near(meta['rate_output'], limited, 'HG06')
      near(meta['heading_debt_rad'], debt, 'HG06')
      require(
        meta['selection'] == selection and flag(meta['selection_changed']) == (prior_selection is not None and prior_selection != selection),
        'E_SELECTION',
        'HG06',
      )
      require(integer(meta['transition_until_sequence']) == until and flag(meta['transition_detected']) == transition, 'E_TRANSITION', 'HG06')
      previous_selected = expected if active and not driver else None
      previous_k, prior_selection = desired, selection
    elif arm == 'SG-A':
      s = mapping(r['source_result'])
      near(s['state_before'], previous_sg, 'HG06')
      require(sequence(s['reset_events']) == events, 'E_SG_RESET', 'HG06')
      if not active:
        previous_sg = None
      elif driver or events or previous_sg is None:
        previous_sg = native
      else:
        expected = max(previous_sg - 1, min(previous_sg + 1, native))
        previous_sg = expected
      near(s['state_after'], previous_sg, 'HG06')
    near(raw_candidate, expected, 'HG06')
    near(command, expected if active else 0.0, 'HG03')
    delayed = queue[0]
    queue = queue[1:] + [-command]
    applied = -delayed
    near(r['applied'], applied)
    knew = 0.92 * k + 0.004 * delayed + 0.0002 * delayed * v + 0.002 * delayed / v + 0.001 * roll
    ynew = -knew * v + 0.75 * (yaw + k * v)
    heading = pose[2] + ynew * DT
    pose = (pose[0] + v * math.cos(heading) * DT, pose[1] + v * math.sin(heading) * DT, heading)
    rh = reference[2] - desired * v * DT
    reference = (reference[0] + v * math.cos(rh) * DT, reference[1] + v * math.sin(rh) * DT, rh)
    normal = -(pose[0] - reference[0]) * math.sin(rh) + (pose[1] - reference[1]) * math.cos(rh)
    near(r['plant_after'], {'curvature_1pm': knew, 'yaw_rate_rad_s': ynew, 'command_history': queue})
    near(r['pose_after'], pose)
    near(r['reference_pose'], reference)
    near(r['curvature_error_1pm'], knew - desired)
    near(r['heading_error_rad'], heading - rh)
    near(r['reference_normal_deviation_m'], normal)
    near(r['curvature_times_speed2_mps2'], knew * v * v)
    near(r['yaw_times_speed_mps2'], ynew * v)
    out.append(Frame(i, (i + 1) * DT, v, desired, knew, ynew, command, applied, native, pose, reference, roll, active, driver, bool(events)))
    k, yaw, applied_before = knew, ynew, applied
  require(prior_receipt == item['final_frame_receipt'], 'E_FINAL_RECEIPT')
  return tuple(out)
