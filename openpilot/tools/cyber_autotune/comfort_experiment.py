"""Fixed synthetic cap95 experiment; no real logs, candidate search or actuation.

Uses native MPC/planner and LongControl, test-local messages and a generic plant.
All thresholds are predeclared in offline-positive-accel-cap.md. No production
controller or frozen v2 comparison is modified by this experiment.
"""
from collections import deque
import math
from pathlib import Path

from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.common.realtime import DT_CTRL, DT_MDL
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.tests.test_cyber_long_integration import FixtureSubMaster, car_params
from openpilot.tools.cyber_autotune.comfort_cap import OfflineComfortPlanner
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.planner_feedback_metrics import summarize
from openpilot.tools.cyber_autotune.synthetic_pipeline import source_binding


CASES = ('open_road', 'lead_brake', 'cut_in_loss', 'stop_start', 'driver_cancel', 'force_decel',
         'coast', 'curve_left', 'curve_right', 'model_stop')
DELAYS = (.03, .15, .30)
ARMS = ('baseline', 'disabled', 'cap95')
DURATION_S = 12
RESPONSE_S = .2
NUMERIC_ALLOWANCE = 1e-9
MINIMUM_JERK_IMPROVEMENT = .01
LOWER = ('planner_tracking_rms_mps2', 'request_to_applied_rms_mps2', 'command_jerk_rms_mps3',
         'actual_jerk_rms_mps3', 'nonpositive_gap_frames', 'unresolved_stops', 'restart_delay_s',
         'unresolved_restarts', 'release_without_standstill_count', 'cut_in_response_s', 'unresolved_cut_ins',
         'inactive_max_abs_request_mps2')
HIGHER = ('minimum_lead_gap_m', 'minimum_ttc_s')


def run_case(case_id: str, *, arm='baseline', delay_s=.03) -> dict:
  if case_id not in CASES or arm not in ARMS or type(delay_s) not in (int, float) or delay_s not in DELAYS:
    raise ValueError('UNDECLARED_COMFORT_EXPERIMENT')
  cp = car_params()
  speed = .5 if case_id == 'stop_start' else 10.
  planner = (LongitudinalPlanner(cp, init_v=speed) if arm == 'baseline' else
             OfflineComfortPlanner(cp, init_v=speed, experiment_enabled=arm == 'cap95'))
  control, sm = LongControl(cp), FixtureSubMaster()
  delay = deque([0.] * round(delay_s / DT_CTRL))
  accel = response = position = 0.
  lead_position = 35.
  measurements, speed_errors, trace = [], [], []
  cap_frames = 0
  for tick in range(round(DURATION_S / DT_CTRL)):
    active = not (case_id == 'driver_cancel' and 400 <= tick < 600)
    stop = (case_id == 'stop_start' and tick < 300) or (case_id == 'model_stop' and 300 <= tick < 900)
    lead_present = case_id == 'lead_brake' or (case_id == 'cut_in_loss' and 400 <= tick < 700)
    cut = case_id == 'cut_in_loss' and tick == 400
    lead_speed = (10. if tick < 400 else 0.) if case_id == 'lead_brake' else 5.
    if cut:
      lead_position = position + 12.
    target_speed = 4. if case_id == 'stop_start' else 20.
    car = sm['carState']
    car.vEgo, car.aEgo, car.vCruise = speed, accel, target_speed * 3.6
    car.standstill, car.cruiseState.standstill = speed < .01, False
    car.brakePressed = not active
    car.steeringAngleDeg = 20. if case_id == 'curve_left' else (-20. if case_id == 'curve_right' else 0.)
    sm['selfdriveState'].enabled = active
    sm['selfdriveState'].experimentalMode = case_id in ('stop_start', 'model_stop')
    sm['carControl'].longActive = active
    sm['controlsState'].longControlState = control.long_control_state
    forced = case_id == 'force_decel' and tick >= 400
    sm['controlsState'].forceDecel = forced
    if case_id == 'coast':
      sm['modelV2'].meta.disengagePredictions.gasPressProbs = [0., 0.]
    if tick % round(DT_MDL / DT_CTRL) == 0:
      for service in sm.logMonoTime:
        sm.logMonoTime[service] = (tick + 1) * round(DT_CTRL * 1e9)
      lead = sm['radarState'].leadOne
      lead.present, lead.dRel = lead_present, max(0., lead_position - position)
      lead.vLead = lead.vLeadK = lead_speed
      lead.vRel = lead_speed - speed
      lead.aLeadK, lead.aLeadTau, lead.modelProb = 0., 1.5, 1.
      action = sm['modelV2'].action
      action.desiredAcceleration, action.shouldStop = (-.5 if stop else .2), stop
      planner.update(sm)
      cap_frames += int(getattr(planner, 'last_cap', None) is not None)
    row = {'time_s': tick * DT_CTRL, 'active': active, 'stop_demand': stop,
           'lead_present': lead_present, 'cut_in_event': cut, 'speed_mps': speed, 'accel_mps2': accel,
           'position_m': position, 'lead_gap_m': lead_position - position, 'lead_speed_mps': lead_speed,
           'planner_accel_mps2': float(planner.output_a_target)}
    command = float(control.update(active, car, planner.output_a_target, planner.output_should_stop, (ACCEL_MIN, ACCEL_MAX)))
    applied = delay.popleft()
    delay.append(command)
    response += DT_CTRL / RESPONSE_S * (applied - response)
    next_speed = max(0., speed + response * DT_CTRL)
    accel = (next_speed - speed) / DT_CTRL
    position += .5 * (speed + next_speed) * DT_CTRL
    speed = next_speed
    lead_position += lead_speed * DT_CTRL
    if not all(math.isfinite(v) for v in (command, speed, accel, position)) or not ACCEL_MIN <= command <= ACCEL_MAX:
      raise ValueError('INVALID_COMFORT_NATIVE_OUTPUT')
    if active:
      speed_errors.append(speed - (0. if stop or forced else target_speed))
    measurements.append({**row, 'requested_accel_mps2': command, 'applied_accel_mps2': applied,
                         'response_speed_mps': speed, 'response_accel_mps2': accel})
    trace.append((planner.output_a_target, planner.output_should_stop, command, speed, accel, position,
                  planner.v_desired_filter.x, tuple(planner.mpc.a_solution), control.pid.i, str(control.long_control_state)))
  return {'schema': 'offline-comfort-case-v1', 'case_id': case_id, 'physical_delay_s': delay_s,
          'dt_s': DT_CTRL, 'duration_s': DURATION_S, 'physical_delay_owner': 'PLANT',
          'metrics': summarize(measurements, DT_CTRL), 'native_trace_sha256': digest(canonical(trace)),
          'speed_tracking_rms_mps': math.sqrt(math.fsum(x*x for x in speed_errors) / len(speed_errors)),
          'cap_frames': cap_frames, 'vehicle_activation_allowed': False, 'vehicle_qualified': False}


def compare_case(base: dict, candidate: dict) -> dict:
  """Internal trusted-runner comparison, not admission of external evidence."""
  reasons, improvements = [], []
  try:
    for key in ('schema', 'case_id', 'physical_delay_s', 'dt_s', 'duration_s', 'physical_delay_owner'):
      if base[key] != candidate[key]:
        return {'status': 'BLOCKED', 'reasons': ['INCOMPARABLE_CASE']}
    if any(result[key] is not False for result in (base, candidate)
           for key in ('vehicle_activation_allowed', 'vehicle_qualified')):
      return {'status': 'BLOCKED', 'reasons': ['INVALID_AUTHORITY']}
    bm = {**base['metrics'], 'speed_tracking_rms_mps': base['speed_tracking_rms_mps']}
    cm = {**candidate['metrics'], 'speed_tracking_rms_mps': candidate['speed_tracking_rms_mps']}
    for key in (*LOWER, *HIGHER, 'speed_tracking_rms_mps'):
      left, right = bm[key], cm[key]
      if left is None or right is None:
        if left != right:
          reasons.append(key + ':AVAILABILITY_CHANGED')
        continue
      if not all(type(v) in (int, float) and math.isfinite(v) for v in (left, right)):
        return {'status': 'BLOCKED', 'reasons': ['INVALID_METRIC']}
      worsening = left - right if key in HIGHER else right - left
      if worsening > NUMERIC_ALLOWANCE:
        reasons.append(key + ':REGRESSION')
      if key in ('command_jerk_rms_mps3', 'actual_jerk_rms_mps3') and left > 0 and (left - right) / left >= MINIMUM_JERK_IMPROVEMENT:
        improvements.append(key)
    if reasons:
      status = 'REJECTED'
    elif base['native_trace_sha256'] == candidate['native_trace_sha256']:
      status = 'NO_EFFECT'
    elif improvements:
      status = 'SYNTHETIC_ONLY_PASS'
    else:
      status = 'REJECTED'
      reasons.append('NO_REQUIRED_JERK_IMPROVEMENT')
    return {'status': status, 'reasons': reasons, 'improvements': improvements}
  except (KeyError, TypeError, ValueError):
    return {'status': 'BLOCKED', 'reasons': ['INVALID_CASE']}


def _binding():
  # Existing binding includes the native libs/dependencies, experimental modules,
  # policy and metric reader. Explicitly add reused test-local CP/input factories.
  root = Path(__file__).resolve().parents[3]
  fixture = 'openpilot/selfdrive/controls/tests/test_cyber_long_integration.py'
  cruise = 'openpilot/selfdrive/car/cruise.py'
  return {**source_binding(), 'synthetic_fixture_sha256': digest((root / fixture).read_bytes()),
          'planner_cruise_sha256': digest((root / cruise).read_bytes())}


def run_matrix() -> dict:
  """All predeclared cases/delays/arms; no selected subset or candidate search.

Internal fresh native state per run, two repetitions; callers must additionally
repeat this whole function in separate processes for cross-process evidence.
"""
  before = _binding()
  variants, comparisons = [], []
  for case in CASES:
    for delay in DELAYS:
      arms = {}
      for arm in ARMS:
        first = run_case(case, arm=arm, delay_s=delay)
        second = run_case(case, arm=arm, delay_s=delay)
        if canonical(first) != canonical(second):
          raise ValueError('NONREPEATABLE_COMFORT_CASE')
        arms[arm] = first
      if canonical(arms['baseline']) != canonical(arms['disabled']):
        raise ValueError('DISABLED_COMFORT_REGRESSION')
      comparisons.append({'case_id': case, 'physical_delay_s': delay,
                          **compare_case(arms['baseline'], arms['cap95'])})
      variants.append(arms)
  if _binding() != before:
    raise ValueError('SOURCE_CHANGED_DURING_COMFORT_MATRIX')
  statuses = {row['status'] for row in comparisons}
  status = ('BLOCKED' if 'BLOCKED' in statuses else 'REJECTED' if 'REJECTED' in statuses else
            'SYNTHETIC_ONLY_PASS' if 'SYNTHETIC_ONLY_PASS' in statuses else 'NO_EFFECT')
  return {'schema': 'offline-comfort-matrix-v1', 'scope': 'NATIVE_PLANNER_GENERIC_PLANT_SYNTHETIC_ONLY',
          'binding': before, 'case_count': len(variants), 'native_runs': len(variants) * len(ARMS) * 2,
          'repeatable': True, 'disabled_exact_identity': True, 'candidate_status': status,
          'comparisons': comparisons, 'variants': variants,
          'readiness': 'NOT_READY', 'vehicle_activation_allowed': False,
          'real_vehicle_verified': False, 'runtime_accepted': False, 'active_profile_enabled': False,
          'vehicle_write_enabled': False, 'can_write_enabled': False, 'promotable_to_vehicle': False}
