"""Test-only native history fixture; fixed inputs, no vehicle or profile consumer.

Separate from the frozen rejected cap experiment. This checks what happens after
intervention, not whether that intervention is a usable tune. No Carrot port.
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
from openpilot.tools.cyber_autotune.comfort_experiment import NUMERIC_ALLOWANCE, _binding, compare_case
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.planner_feedback_metrics import summarize


CASES = ('lead_stop_restart', 'model_stop_restart', 'force_stop_restart')
DELAYS = (.03, .15, .30)
ARMS = ('baseline', 'disabled', 'cap95')
EVENT_S, RELEASE_S, DURATION_S = 3., 18., 24.
INITIAL_SPEED_MPS, CRUISE_MPS = 2., 20.
LEAD_POSITION_M, LEAD_RELEASE_SPEED_MPS = 18., 4.
RESPONSE_S = .2
MODEL_ACCEL_MPS2, MODEL_BRAKE_MPS2 = 2., -2.


def run_history(case_id: str, *, arm='baseline', delay_s=.03) -> dict:
  """Fresh native planner/control state and a single generic plant delay queue.

  Event schedule and lead world trajectory are exogenous and equal across arms.
  Candidate's protected arbitration is checked against its OWN current stock
  candidates; different closed-loop states must not imply equal braking outputs.
  """
  if case_id not in CASES or arm not in ARMS or type(delay_s) not in (int, float) or delay_s not in DELAYS:
    raise ValueError('UNDECLARED_COMFORT_HISTORY')
  cp = car_params()
  planner = (LongitudinalPlanner(cp, init_v=INITIAL_SPEED_MPS) if arm == 'baseline' else
             OfflineComfortPlanner(cp, init_v=INITIAL_SPEED_MPS, experiment_enabled=arm == 'cap95'))
  control, sm = LongControl(cp), FixtureSubMaster()
  delay = deque([0.] * round(delay_s / DT_CTRL))
  speed = INITIAL_SPEED_MPS
  accel = response = position = 0.
  rows, trace, speed_errors = [], [], []
  coverage = dict.fromkeys(('cap_before_event_frames', 'cap_during_demand_frames',
                            'protected_planner_frames', 'protected_arbitration_mismatches',
                            'candidate_planner_frames', 'observed_planner_frames', 'initial_reset_frames'), 0)
  for tick in range(round(DURATION_S / DT_CTRL)):
    time_s = tick * DT_CTRL
    demand = EVENT_S <= time_s < RELEASE_S
    lead_present = case_id == 'lead_stop_restart' and time_s >= EVENT_S
    lead_position = LEAD_POSITION_M + max(0., time_s - RELEASE_S) * LEAD_RELEASE_SPEED_MPS
    lead_speed = LEAD_RELEASE_SPEED_MPS if time_s >= RELEASE_S else 0.
    forced = case_id == 'force_stop_restart' and demand
    model_stop = case_id == 'model_stop_restart' and demand
    car = sm['carState']
    car.vEgo, car.aEgo, car.vCruise = speed, accel, CRUISE_MPS * 3.6
    car.standstill, car.cruiseState.standstill = speed < .01, False
    sm['controlsState'].longControlState = control.long_control_state
    sm['controlsState'].forceDecel = forced
    sm['selfdriveState'].experimentalMode = case_id == 'model_stop_restart'
    if tick % round(DT_MDL / DT_CTRL) == 0:
      for service in sm.logMonoTime:
        sm.logMonoTime[service] = (tick + 1) * round(DT_CTRL * 1e9)
      lead = sm['radarState'].leadOne
      lead.present, lead.dRel = lead_present, max(0., lead_position - position)
      lead.vLead = lead.vLeadK = lead_speed
      lead.vRel = lead_speed - speed
      lead.aLeadK, lead.aLeadTau, lead.modelProb = 0., 1.5, 1.
      sm['modelV2'].action.desiredAcceleration = MODEL_BRAKE_MPS2 if model_stop else MODEL_ACCEL_MPS2
      sm['modelV2'].action.shouldStop = model_stop
      planner.update(sm)
      cap = getattr(planner, 'last_cap', None)
      coverage['cap_before_event_frames'] += int(cap is not None and time_s < EVENT_S)
      coverage['cap_during_demand_frames'] += int(cap is not None and demand)
      if arm == 'cap95':
        coverage['candidate_planner_frames'] += 1
        observation = planner.cyber_long_policy.last_observation
        # Only tick zero is the known OFF-state reset. Missing diagnostics later
        # must not make unsafe cycles disappear from the coverage denominator.
        if tick and (observation is None or planner.cyber_long_fault is not None or
                     observation.context.model_mono_time_ns != sm.logMonoTime['modelV2']):
          raise ValueError('UNOBSERVED_HISTORY_CYCLE')
        coverage['initial_reset_frames'] += int(tick == 0 and observation is None)
        if observation is not None:
          coverage['observed_planner_frames'] += 1
          stock = observation.context.candidates
          stock_accel = min(c.accel_mps2 for c in stock)
          stock_stop = any(c.should_stop for c in stock)
          if stock_accel < 0 or stock_stop or forced:
            coverage['protected_planner_frames'] += 1
            coverage['protected_arbitration_mismatches'] += int(
              cap is not None or planner.output_a_target != max(ACCEL_MIN, min(ACCEL_MAX, stock_accel)) or
              planner.output_should_stop != stock_stop)
    row = {'time_s': time_s, 'active': True, 'stop_demand': demand, 'lead_present': lead_present,
           'cut_in_event': lead_present and time_s == EVENT_S, 'speed_mps': speed, 'accel_mps2': accel,
           'position_m': position, 'lead_gap_m': lead_position - position, 'lead_speed_mps': lead_speed,
           'planner_accel_mps2': float(planner.output_a_target)}
    command = float(control.update(True, car, planner.output_a_target, planner.output_should_stop, (ACCEL_MIN, ACCEL_MAX)))
    applied = delay.popleft()
    delay.append(command)
    response += DT_CTRL / RESPONSE_S * (applied - response)
    next_speed = max(0., speed + response * DT_CTRL)
    accel = (next_speed - speed) / DT_CTRL
    position += .5 * (speed + next_speed) * DT_CTRL
    speed = next_speed
    if not all(math.isfinite(v) for v in (command, speed, accel, position)) or not ACCEL_MIN <= command <= ACCEL_MAX:
      raise ValueError('INVALID_HISTORY_OUTPUT')
    rows.append({**row, 'requested_accel_mps2': command, 'applied_accel_mps2': applied,
                 'response_speed_mps': speed, 'response_accel_mps2': accel})
    speed_errors.append(speed - (0. if demand else CRUISE_MPS))
    trace.append((planner.output_a_target, planner.output_should_stop, command, speed, accel, position,
                  planner.v_desired_filter.x, tuple(planner.mpc.a_solution), control.pid.i, str(control.long_control_state)))
  event_rows = [r for r in rows if EVENT_S <= r['time_s'] < RELEASE_S]
  requested = next((r for r in event_rows if r['requested_accel_mps2'] < 0), None)
  applied = next((r for r in event_rows if r['applied_accel_mps2'] < 0), None)
  stopped = next((r for r in event_rows if r['response_speed_mps'] <= .01), None)
  events = {'negative_request_latency_s': requested['time_s'] - EVENT_S if requested else None,
            'negative_applied_latency_s': applied['time_s'] - EVENT_S if applied else None,
            'stop_latency_s': stopped['time_s'] + DT_CTRL - EVENT_S if stopped else None,
            'stop_position_m': (stopped['position_m'] + .5 * (stopped['speed_mps'] + stopped['response_speed_mps']) * DT_CTRL
                                if stopped else None)}
  return {'schema': 'comfort-history-case-v1', 'case_id': case_id, 'physical_delay_s': delay_s,
          'dt_s': DT_CTRL, 'duration_s': DURATION_S, 'physical_delay_owner': 'PLANT',
          'scenario_identity': digest(canonical((case_id, EVENT_S, RELEASE_S, DURATION_S, INITIAL_SPEED_MPS,
                                                CRUISE_MPS, LEAD_POSITION_M, LEAD_RELEASE_SPEED_MPS,
                                                MODEL_ACCEL_MPS2, MODEL_BRAKE_MPS2))),
          'metrics': summarize(rows, DT_CTRL), 'event_metrics': events, 'coverage': coverage,
          'native_trace_sha256': digest(canonical(trace)),
          'speed_tracking_rms_mps': math.sqrt(math.fsum(x*x for x in speed_errors) / len(speed_errors)),
          'vehicle_activation_allowed': False, 'vehicle_qualified': False}


def history_binding():
  directory = Path(__file__).resolve().parent
  return {**_binding(), 'history_fixture_sha256': digest(Path(__file__).read_bytes()),
          'history_test_sha256': digest((directory / 'test_comfort_history.py').read_bytes())}


def run_matrix() -> dict:
  """Bound supplemental coverage, never a promotion or replacement verdict."""
  before = history_binding()
  variants, comparisons = [], []
  covered = True
  for case in CASES:
    for delay in DELAYS:
      arms = {}
      for arm in ARMS:
        first = run_history(case, arm=arm, delay_s=delay)
        if canonical(first) != canonical(run_history(case, arm=arm, delay_s=delay)):
          raise ValueError('NONREPEATABLE_HISTORY')
        arms[arm] = first
      if canonical(arms['baseline']) != canonical(arms['disabled']):
        raise ValueError('DISABLED_HISTORY_REGRESSION')
      coverage = arms['cap95']['coverage']
      covered = covered and coverage['cap_before_event_frames'] > 0 and coverage['protected_planner_frames'] > 0
      if coverage['protected_arbitration_mismatches']:
        raise ValueError('PROTECTED_ARBITRATION_REGRESSION')
      base, candidate = arms['baseline'], arms['cap95']
      # A relative comparison can improve yet both arms collide. Keep absolute
      # gap failure prominent; never let a scoped relative PASS imply safety.
      gap_status = ('FAIL' if any(r['metrics']['nonpositive_gap_frames'] for r in (base, candidate)) else
                    'NOT_APPLICABLE' if base['metrics']['minimum_lead_gap_m'] is None else 'PASS')
      event_regressions = []
      for key in ('negative_request_latency_s', 'negative_applied_latency_s', 'stop_latency_s'):
        left, right = base['event_metrics'][key], candidate['event_metrics'][key]
        if left is None or right is None:
          if left != right:
            event_regressions.append(key + ':AVAILABILITY_CHANGED')
        elif right - left > NUMERIC_ALLOWANCE:
          event_regressions.append(key)
      comparisons.append({'case_id': case, 'physical_delay_s': delay,
                          'relative_comparison': compare_case(base, candidate),
                          'absolute_gap_check': gap_status, 'event_metric_regressions': event_regressions})
      variants.append(arms)
  if history_binding() != before:
    raise ValueError('HISTORY_SOURCE_CHANGED')
  return {'schema': 'comfort-history-matrix-v1', 'binding': before, 'case_count': len(variants),
          'native_runs': len(variants) * len(ARMS) * 2, 'repeatable': True,
          'disabled_exact_identity': True, 'intervention_before_event_covered': covered,
          'scope': 'SUPPLEMENTAL_SYNTHETIC_COVERAGE_ONLY', 'comparisons': comparisons, 'variants': variants,
          'absolute_gap_check': 'FAIL' if any(c['absolute_gap_check'] == 'FAIL' for c in comparisons) else 'PASS',
          'candidate_status': 'REJECTED_PRIOR_EXPERIMENT', 'readiness': 'NOT_READY',
          'vehicle_activation_allowed': False, 'real_vehicle_verified': False, 'runtime_accepted': False,
          'active_profile_enabled': False, 'vehicle_write_enabled': False, 'can_write_enabled': False,
          'promotable_to_vehicle': False}
