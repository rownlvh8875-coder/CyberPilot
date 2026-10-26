"""Checked F8-to-F7 Frame mapping; historical data is never executed as code."""

import math
from typing import Literal

from tools.cyberpilot import offline_multiobjective_gates_v1 as g
from tools.cyberpilot.f8_evidence_reader_v1 import F8Error, need

ARMS = ('A0', 'A2', 'A3', 'SG-A')
ResetMode = Literal['RESET_MODE_A', 'RESET_MODE_B', 'SOURCE_DEFINED_OPTIMIZER_EVENT_RESET', 'NO_EXPLICIT_RESET']
ROW_KEYS = frozenset(
  (
    'sequence',
    'time_ns',
    'source_sha256',
    'input',
    'measurement',
    'native_input',
    'native_request',
    'command',
    'candidate',
    'applied_before',
    'applied',
    'plant_before',
    'plant_after',
    'pose_before',
    'pose_after',
    'reference_pose',
    'native_state_before',
    'native_state_after',
    'reset_events',
    'previous_receipt_sha256',
    'receipt_sha256',
  )
)


def near(actual: object, expected: object) -> None:
  try:
    g.near(actual, expected)
  except g.EvidenceError as exc:
    raise F8Error('F8_RECURRENCE') from exc


def fresh_native(event: str) -> dict[str, object]:
  return {
    'jerk_filter_initialized': True,
    'jerk_filter_x': 0.0,
    'pending_events': [event],
    'pid': [0.0] * 5,
    'prior_input': None,
    'reference_buffer': [0.0] * 100,
    'sat_time': 0.0,
  }


def mathematical_domain(spec: dict[str, object], arm: str) -> dict[str, object]:
  need(arm in ARMS and spec.get('dt_s') == g.DT and spec.get('performance_qualified') is False, 'F8_INPUT_CONTRACT')
  frames = [g.mapping(x) for x in g.sequence(spec['frames'])]
  need(0 < len(frames) <= 4000, 'F8_FRAME_BOUND')
  required = []
  a2_valid = True
  for n, f in enumerate(frames):
    need(g.integer(f['sequence']) == n and g.integer(f['time_ns']) == n * g.TIME_NS, 'F8_INPUT_TIME')
    v, k, roll = g.number(f['speed_mps']), g.number(f['desired_curvature_1pm']), g.number(f['roll_rad'])
    need(2.5 <= v <= 30 and abs(k) <= 0.1, 'F8_MATHEMATICAL_DOMAIN')
    g.flag(f['active'])
    g.flag(f['steering_pressed'])
    need(abs(g.number(f['noise_unit'])) <= 1, 'F8_NOISE_INPUT')
    request = g.required_static_command(k, v, roll, g.mapping(g.PLANT))
    required.append(request)
    if arm == 'A2':
      a2_valid &= 5 <= v <= 10 and request <= 0.3 + (v - 5) / 5 * (0.2 - 0.3)
  need(max(required) <= 1, 'F8_PLANT_STATIC_DOMAIN')
  return {
    'mathematical_status': 'MATHEMATICAL_DOMAIN_VALID',
    'scope': 'DECLARED_INPUT_AND_SYNTHETIC_PLANT',
    'candidate_domain_admitted': a2_valid,
    'max_required_static_command': max(required),
    'dynamic_status': 'DYNAMIC_FEASIBILITY_UNQUALIFIED',
    'physical_vehicle_status': 'REAL_VEHICLE_UNVERIFIED',
  }


def verify_trace(raw: object, item: dict[str, object], spec: dict[str, object], mode: ResetMode, expected_source: str) -> tuple[g.Frame, ...]:
  try:
    return _verify(raw, item, spec, mode, expected_source)
  except g.EvidenceError as exc:
    raise F8Error('F8_' + exc.code) from exc
  except (KeyError, TypeError) as exc:
    raise F8Error('F8_TRACE_SCHEMA') from exc


def _verify(raw: object, item: dict[str, object], spec: dict[str, object], mode: ResetMode, expected_source: str) -> tuple[g.Frame, ...]:
  rows = g.sequence(raw)
  inputs = g.sequence(spec['frames'])
  arm = g.text(item['arm'])
  need(len(rows) == len(inputs) == g.integer(item['frames']) and 0 < len(rows) <= 4000, 'F8_FRAME_COUNT')
  need(item['source_sha256'] == expected_source, 'F8_SOURCE_IDENTITY')
  near(item['plant'], g.PLANT)
  need(mathematical_domain(spec, arm)['candidate_domain_admitted'] is True, 'F8_CANDIDATE_DOMAIN')
  need(item.get('status') == 'EXECUTED_DIAGNOSTIC_ONLY', 'F8_EXECUTION_STATUS')
  calls = g.mapping(item['calls'])
  for key in ('native_update', 'stock_update', 'plant_step', 'governor' if arm == 'SG-A' else 'optimizer'):
    need(g.integer(calls[key]) == len(rows), 'F8_CONTROLLER_PROVENANCE')
  native_identity = g.mapping(item['native_identity'])
  need(native_identity.get('role') == 'UNCHANGED_NATIVE_BASELINE', 'F8_NATIVE_IDENTITY')
  initial = g.mapping(spec['initial'])
  state = g.mapping(item['initial_state'])
  near(state['physical'], initial)
  need(state['candidate'] is None, 'F8_CROSS_ARM_INITIAL_STATE')
  near(state['native'], fresh_native('EXPERIMENT_START'))
  near(state['reference_pose'], [0.0, 0.0, 0.0])
  need(item['initial_state_sha256'] == g.sha(g.canonical(state)), 'F8_INITIAL_SHA')
  need(item['input_sha256'] == g.sha(g.canonical(spec)), 'F8_INPUT_SHA')
  k, yaw = g.number(initial['curvature_1pm']), g.number(initial['yaw_rate_rad_s'])
  need(abs(k) <= 0.1, 'F8_INITIAL_DOMAIN')
  queue = [g.number(x) for x in g.sequence(initial['command_history'])]
  need(len(queue) == 2 and all(abs(x) <= 1 for x in queue), 'F8_INITIAL_QUEUE')
  pose = (g.number(initial['x_m']), g.number(initial['y_m']), g.number(initial['heading_rad']))
  reference = (0.0, 0.0, 0.0)
  applied_before = g.number(initial['applied_last'])
  need(abs(applied_before) <= 1, 'F8_INITIAL_APPLIED')
  m = g.mapping(spec['measurement'])
  need(m.get('unit') == 'm^-1' and m.get('coordinate') == 'plant_curvature_positive_yaw_negative', 'F8_COORDINATE')
  bias, amplitude = g.number(m['bias']), g.number(m['noise_amplitude'])
  delay, variable = g.integer(m['delay_steps']), g.flag(m['variable_delay'])
  need(amplitude >= 0 and 0 <= delay <= 4 and m.get('max_age_ns') == 40_000_000, 'F8_MEASUREMENT_PARAMETER')
  reset_at = spec['reset_sequence']
  need(reset_at is None or type(reset_at) is int and 0 < reset_at < len(rows), 'F8_RESET_SEQUENCE')
  if reset_at is None:
    need(mode == 'NO_EXPLICIT_RESET', 'F8_RESET_MODE')
  elif mode == 'RESET_MODE_A':
    need(arm == 'SG-A', 'F8_RESET_MODE')
  elif mode != 'RESET_MODE_B':
    need(arm != 'SG-A' and mode == 'SOURCE_DEFINED_OPTIMIZER_EVENT_RESET', 'F8_RESET_MODE')
  receipt = '0' * 64
  prior_native: object = None
  previous_rate: float | None = None
  previous_sg: float | None = None
  prior_active = prior_driver = None
  curvature_history: list[float] = []
  out: list[g.Frame] = []
  for n, value in enumerate(rows):
    r = g.mapping(value)
    need(set(r) == ROW_KEYS, 'F8_ROW_KEYS')
    need(g.integer(r['sequence']) == n and g.integer(r['time_ns']) == n * g.TIME_NS, 'F8_FRAME_TIME')
    need(r['source_sha256'] == expected_source and r['previous_receipt_sha256'] == receipt, 'F8_ROW_SOURCE_CHAIN')
    need(r['receipt_sha256'] == g.sha(g.canonical({key: val for key, val in r.items() if key != 'receipt_sha256'})), 'F8_ROW_RECEIPT')
    receipt = g.text(r['receipt_sha256'])
    f = g.mapping(r['input'])
    need(f == inputs[n], 'F8_EXOGENOUS_INPUT')
    v, desired, roll = g.number(f['speed_mps']), g.number(f['desired_curvature_1pm']), g.number(f['roll_rad'])
    active, driver = g.flag(f['active']), g.flag(f['steering_pressed'])
    explicit = n == reset_at
    events = []
    if n == 0:
      events.append('EXPERIMENT_START')
    if explicit:
      events.append('CONTROLLER_RESET')
    if n > 0:
      if prior_active and not active:
        events.append('INACTIVE')
      if not prior_driver and driver:
        events.append('STEERING_PRESSED')
      if prior_driver and not driver:
        events.append('RELEASE')
      if not prior_active and active:
        events.append('REENGAGEMENT')
    need(r['reset_events'] == events, 'F8_RESET_EVENTS')
    near(r['plant_before'], {'curvature_1pm': k, 'yaw_rate_rad_s': yaw, 'command_history': queue})
    near(r['pose_before'], pose)
    curvature_history.append(k)
    lag = (n // 8) % 5 if variable else delay
    acquisition = n - lag
    measured_raw = g.number(initial['curvature_1pm']) if acquisition < 0 else curvature_history[acquisition]
    noise = amplitude * g.number(f['noise_unit'])
    measured = measured_raw + bias + noise
    need(abs(measured) <= 0.1, 'F8_MEASUREMENT_DOMAIN')
    sensor = g.mapping(r['measurement'])
    near(
      sensor,
      {
        'packet_sequence': n,
        'acquisition_sequence': acquisition,
        'acquisition_time_ns': acquisition * g.TIME_NS,
        'receive_time_ns': n * g.TIME_NS,
        'age_ns': lag * g.TIME_NS,
        'priming': acquisition < 0,
        'raw_curvature_1pm': measured_raw,
        'curvature_1pm': measured,
        'noise_1pm': noise,
        'bias_1pm': bias,
        'unit': 'm^-1',
        'coordinate': 'plant_curvature_positive_yaw_negative',
      },
    )
    ni = {
      'desired_curvature_1pm': desired,
      'actual_curvature_1pm': measured,
      'speed_mps': v,
      'roll_rad': roll,
      'time_s': n * g.DT,
      'dt_s': g.DT,
      'active': active,
      'steering_pressed': driver,
      'safety_limited': False,
      'curvature_limited': False,
    }
    near(r['native_input'], ni)
    if n == 0 or explicit:
      near(r['native_state_before'], fresh_native('SCENARIO_BOUNDARY' if explicit else 'EXPERIMENT_START'))
    else:
      near(r['native_state_before'], prior_native)
    after = g.mapping(r['native_state_after'])
    near(after['prior_input'], ni)
    need(after['pending_events'] == [], 'F8_NATIVE_PENDING_EVENT')
    prior_native = after
    near(r['applied_before'], applied_before)
    native, command = g.number(r['native_request']), g.number(r['command'])
    need(abs(native) <= 1 and abs(command) <= 1, 'F8_COMMAND_DOMAIN')
    candidate = g.mapping(r['candidate'])
    src = g.mapping(candidate['source_result'])
    need(src.get('performance_qualified', False) is False and src.get('runtime_authorized', False) is False, 'F8_FORGED_QUALIFICATION')
    expected = native
    if arm != 'SG-A':
      need(
        src.get('valid') is True and src.get('variant') == arm and src.get('live_actuator_authority') is False and src.get('execution_stage') == 'offline_only',
        'F8_CANDIDATE_PROVENANCE',
      )
      near(src['baseline_command'], native)
      if events or not active:
        previous_rate = None
      near(candidate['previous_candidate_before'], previous_rate)
      if arm == 'A2':
        cap = 0.3 + (v - 5) / 5 * (0.2 - 0.3)
        expected = max(-cap, min(cap, native))
        near(g.mapping(src['authority'])['envelope_limit'], cap)
      elif arm == 'A3':
        expected = g.rate_step(native, applied_before if previous_rate is None else previous_rate)
        previous_rate = expected
      near(candidate['candidate_state_after'], previous_rate)
      near(src['candidate_command'], expected)
    else:
      if explicit and mode == 'RESET_MODE_B':
        previous_sg = None
      near(src['state_before'], previous_sg)
      governor_events = ['EXPERIMENT_START'] if n == 0 or explicit and mode == 'RESET_MODE_B' else [e for e in events if e != 'CONTROLLER_RESET']
      need(src['reset_events'] == governor_events and src.get('state_owner') == 'SG' and src.get('physical_delay_owner') == 'PLANT', 'F8_GOVERNOR_OWNERSHIP')
      need(
        src['core_source_sha256'] == native_identity['source_sha256'] and src['core_config_sha256'] == native_identity['config_sha256'], 'F8_GOVERNOR_SOURCE'
      )
      if not active:
        expected, previous_sg = 0.0, None
      elif driver or governor_events or previous_sg is None:
        previous_sg = native
      else:
        expected = max(previous_sg - 1, min(previous_sg + 1, native))
        previous_sg = expected
      near(src['state_after'], previous_sg)
      if explicit and mode == 'RESET_MODE_B':
        need(src['state_before'] is None and src['action'] == 'FRESH_CURRENT_COMMAND_REBASE', 'F8_GOVERNOR_FRESHNESS')
    near(candidate['raw_candidate'], expected)
    near(candidate['delivered'], expected if active else 0.0)
    near(command, expected if active else 0.0)
    need(candidate['delivery_gate'] == ('ACTIVE' if active else 'INACTIVE_NATIVE_AUTHORITY_ZERO'), 'F8_DELIVERY_GATE')
    delayed = queue.pop(0)
    queue.append(-command)
    near(r['applied'], -delayed)
    knew = 0.92 * k + 0.004 * delayed + 0.0002 * delayed * v + 0.002 * delayed / v + 0.001 * roll
    ynew = -knew * v + 0.75 * (yaw + k * v)
    heading = pose[2] + ynew * g.DT
    pose = (pose[0] + v * math.cos(heading) * g.DT, pose[1] + v * math.sin(heading) * g.DT, heading)
    rh = reference[2] - desired * v * g.DT
    reference = (reference[0] + v * math.cos(rh) * g.DT, reference[1] + v * math.sin(rh) * g.DT, rh)
    near(r['plant_after'], {'curvature_1pm': knew, 'yaw_rate_rad_s': ynew, 'command_history': queue})
    near(r['pose_after'], pose)
    near(r['reference_pose'], reference)
    out.append(g.Frame(n, (n + 1) * g.DT, v, desired, knew, ynew, command, -delayed, native, pose, reference, roll, active, driver, bool(events)))
    k, yaw, applied_before = knew, ynew, -delayed
    prior_active, prior_driver = active, driver
  need(receipt == item['last_receipt_sha256'], 'F8_FINAL_RECEIPT')
  return tuple(out)
