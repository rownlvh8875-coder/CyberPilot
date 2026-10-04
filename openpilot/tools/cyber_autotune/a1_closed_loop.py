"""Fixed A1 tables through existing generic plants; no real-data/live interface.

Frozen v2 inputs, plant and measurements stay unchanged. Separate feedback glue
is parity-tested against v2 so new A1 admission cannot rewrite old evidence.
"""
import base64
from dataclasses import asdict, replace
import math
from types import SimpleNamespace

from openpilot.tools.cyber_autotune.a1_experiment import FIXTURES, build_request, make_fixture
from openpilot.tools.cyber_autotune.a1_schedule import prepare_schedule
from openpilot.tools.cyber_autotune.contracts import finite_number
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.native_worker import _a1_dynamic_state, _a1_invariants
from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import DEFAULT_PLANT_CONFIG
from openpilot.tools.cyber_autotune.synthetic_lateral_plant import SyntheticLateralPlant
from openpilot.tools.cyber_autotune.synthetic_metrics import lateral_metrics
from openpilot.tools.cyber_autotune.synthetic_native_v2 import POLICY_SHA256, feedback_angle_deg, frozen_policy
from openpilot.tools.cyber_autotune.synthetic_pipeline import AUTHORITY, _compare
from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, catalog_digest, frame_digest, frames, validate_frames


def _trace(case, rows, cp, table, delay_s):
  from opendbc.car import structs
  from opendbc.car.interfaces import CarInterfaceBase
  from opendbc.car.vehicle_model import VehicleModel
  from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque

  tuning = cp.lateralTuning.torque
  schedule = None if table is None else prepare_schedule(
    table, tuple(row.speed_mps for row in rows), tuning.latAccelFactor, tuning.friction)

  class LinearConversion:
    torque_from_lateral_accel_linear = CarInterfaceBase.torque_from_lateral_accel_linear
    torque_from_lateral_accel = CarInterfaceBase.torque_from_lateral_accel
    lateral_accel_from_torque_linear = CarInterfaceBase.lateral_accel_from_torque_linear
    lateral_accel_from_torque = CarInterfaceBase.lateral_accel_from_torque

  controller = LatControlTorque(cp.as_reader(), LinearConversion(), case.dt_s)
  invariants = _a1_invariants(controller)
  model = VehicleModel(cp)
  config = replace(DEFAULT_PLANT_CONFIG, actuator_delay_s=delay_s)
  plant = SyntheticLateralPlant(config)
  trace, feedback, states = [], [], []
  prior_command = prior_feedback = 0.
  for index, frame in enumerate(rows):
    observed = plant.snapshot()
    state = structs.CarState()
    state.vEgo = state.vEgoRaw = frame.speed_mps
    model.update_params(1., cp.steerRatio)
    measured_curvature = observed.lateral_accel_mps2 / frame.speed_mps ** 2 + frame.pose_yaw_bias / frame.speed_mps
    state.steeringAngleDeg = feedback_angle_deg(model, measured_curvature, frame.speed_mps)
    state.steeringRateDeg = (state.steeringAngleDeg - prior_feedback) / case.dt_s
    prior_feedback = state.steeringAngleDeg
    feedback.append([float(state.steeringAngleDeg), float(state.steeringRateDeg)])
    state.steeringPressed = frame.steering_pressed
    state.steeringTorque = 1. if frame.steering_pressed else 0.
    if schedule is not None:
      speed, _, _, factor, friction = schedule[index]
      before = _a1_dynamic_state(controller)
      controller.update_torque_parameters(factor, tuning.latAccelOffset, friction)
      if (state.vEgo != speed or controller.torque_params.latAccelFactor != factor or
          controller.torque_params.friction != friction or before != _a1_dynamic_state(controller)):
        raise ValueError('A1_NATIVE_STORAGE_OR_STATE_MISMATCH')
    if _a1_invariants(controller) != invariants:
      raise ValueError('A1_INVARIANT_CHANGED')
    params = SimpleNamespace(roll=0., angleOffsetDeg=0.)
    requested, _, _ = controller.update(frame.active, state, model, params, False, frame.curvature, False, .15)
    requested = float(requested)
    if not finite_number(requested) or abs(requested) > 1:
      raise ValueError('INVALID_NATIVE_TORQUE')
    states.append(_a1_dynamic_state(controller))
    command = -requested
    limited = command
    if case.case_id == 'lat_rate_limit' and frame.active:
      limited = max(prior_command - .5 * case.dt_s, min(prior_command + .5 * case.dt_s, command))
    if not frame.active:
      limited = 0.
    rate_limited = limited != command
    prior_command = limited
    plant.config = replace(config, lateral_accel_per_command_mps2=config.lateral_accel_per_command_mps2 * frame.gain_scale)
    sample = plant.step(limited, speed_mps=frame.speed_mps, desired_curvature_1pm=frame.curvature,
                        friction_scale=frame.friction_scale)
    trace.append({
      'interval_start_s': frame.time_ns * 1e-9, 'time_s': frame.time_ns * 1e-9 + case.dt_s,
      'lateral_error_m': sample.lateral_error_m + frame.path_bias_m,
      'heading_error_rad': sample.heading_error_rad, 'desired_curvature_1pm': frame.curvature,
      'actual_curvature_1pm': sample.yaw_rate_rps / frame.speed_mps, 'speed_mps': frame.speed_mps,
      'requested_command': command, 'applied_command': sample.applied_command,
      'steering_angle_deg': sample.steering_angle_deg,
      'desired_steering_angle_deg': math.degrees(math.atan(config.wheelbase_m * frame.curvature)) * config.steer_ratio,
      'saturated': abs(requested) >= .999 or sample.saturated, 'rate_limited': rate_limited,
      'active': frame.active, 'steering_pressed': frame.steering_pressed,
      'lane_half_width_m': 1.8, 'vehicle_half_width_m': .9,
    })
  return tuple(trace), asdict(config), {
    'feedback_sha256': digest(canonical(feedback)), 'state_sha256': digest(canonical(states)),
    'schedule_sha256': digest(canonical(schedule)), 'invariants_sha256': digest(canonical(invariants)),
    'physical_delay_owner': 'PLANT', 'controller_delay_queue_present': False,
    'native_reference_history_compensation_s': .15,
  }


def run_case(case_id, fixture, delay_s):
  """Fixed repository fixtures only. Rejections have no partially run controller."""
  cases = {case.case_id: case for case in catalog() if case.axis == 'lateral'}
  if type(case_id) is not str or case_id not in cases or type(fixture) is not str or fixture not in FIXTURES:
    raise ValueError('UNDECLARED_A1_CLOSED_LOOP_CASE')
  case = cases[case_id]
  if not finite_number(delay_s) or delay_s not in case.physical_delays_s:
    raise ValueError('UNDECLARED_PHYSICAL_DELAY')
  rows = frames(case)
  input_status = validate_frames(rows, case.dt_s)
  result = {'case_id': case_id, 'fixture': fixture, 'physical_delay_s': delay_s,
            'input_sha256': frame_digest(rows), 'input_status': input_status,
            'policy_sha256': POLICY_SHA256, 'controller_executed': False, 'metrics': None,
            'physical_delay_owner': 'PLANT', 'controller_delay_queue_present': False,
            'time_semantics': 'INPUT_COMMAND_AT_INTERVAL_START_STATE_AT_INTERVAL_END',
            'vehicle_activation_allowed': False, **dict.fromkeys(AUTHORITY, False)}
  if input_status != case.expected_input_status:
    raise ValueError('SCENARIO_INPUT_EXPECTATION_MISMATCH')
  if input_status != 'VALID':
    return dict(result, status='REJECTED_INPUT', reason=input_status)
  from opendbc.car import structs
  import numpy as np
  native, table = make_fixture(build_request(fixture))
  with structs.CarParams.from_bytes(base64.b64decode(native['car_params_base64'])) as reader:
    cp = reader.as_builder()
  table = None if fixture == 'disabled' else table
  # Admission failure is distinct from native execution failure; do not catch a
  # controller exception here and call it an expected schedule rejection.
  if table is not None:
    try:
      prepare_schedule(table, tuple(row.speed_mps for row in rows), cp.lateralTuning.torque.latAccelFactor,
                       cp.lateralTuning.torque.friction)
    except ValueError as exc:
      if str(exc) not in ('A1_TRANSITION_EXCEEDED', 'OUTSIDE_A1_SPEED_DOMAIN', 'OUTSIDE_SYNTHETIC_A1_BOUNDS'):
        raise
      return dict(result, status='BLOCKED', reason=str(exc))
  with np.errstate(over='raise', invalid='raise', divide='raise'):
    trace, config, receipt = _trace(case, rows, cp, table, delay_s)
    metrics = lateral_metrics(trace, case.dt_s)
  return dict(result, status='COMPLETED_SYNTHETIC_ONLY', controller_executed=True, metrics=metrics, receipt=receipt,
              plant_sha256=digest(canonical(config)), base_car_params_sha256=native['car_params_sha256'],
              table_sha256=digest(canonical(asdict(table))) if table is not None else None,
              reset_sha256=digest(canonical({'controller': 'FRESH', 'plant': 'FRESH', 'delay_queue': 'ZERO', 'step_index': 0})))


def run_matrix():
  """Complete fixed lateral catalog, including all blocked and invalid cases."""
  policy = frozen_policy()
  if catalog_digest() != policy['catalog_sha256']:
    raise ValueError('SYNTHETIC_CATALOG_CHANGED')
  variants = [(case.case_id, delay) for case in catalog() if case.axis == 'lateral' for delay in case.physical_delays_s]
  arms = {fixture: [run_case(case, fixture, delay) for case, delay in variants] for fixture in FIXTURES}
  for base, identity in zip(arms['disabled'], arms['identity'], strict=True):
    if (base['status'] != identity['status'] or base['metrics'] != identity['metrics'] or
        (base['metrics'] is not None and any(base['receipt'][k] != identity['receipt'][k]
                                            for k in ('feedback_sha256', 'state_sha256', 'invariants_sha256')))):
      raise ValueError('A1_CLOSED_LOOP_IDENTITY_PARITY_FAILED')
  comparisons = {}
  for fixture in ('factor', 'friction', 'combined'):
    verdict = _compare({'results': arms['disabled']}, {'results': arms[fixture]}, policy)
    reasons = verdict['reasons']
    for row in arms[fixture]:
      if row['input_status'] == 'VALID' and row['status'] != 'COMPLETED_SYNTHETIC_ONLY':
        reasons.append('INCOMPLETE_VALID_COVERAGE')
      if row['metrics'] is not None:
        if row['metrics']['lane_edge_minimum_margin_m'] < 0:
          reasons.append(row['case_id'] + ':NEGATIVE_LANE_MARGIN')
        if row['metrics']['unresolved_recoveries'] != 0:
          reasons.append(row['case_id'] + ':UNRESOLVED_RECOVERY')
    comparisons[fixture] = dict(verdict, status='REJECTED' if reasons else 'PASS_SYNTHETIC_ONLY', reasons=sorted(set(reasons)))
  return {'schema': 'a1-generic-closed-loop-v1', 'status': 'COMPLETED_SYNTHETIC_ONLY',
          'scope': 'SUPPLIED_TRAJECTORY_NATIVE_CONTROLLER_GENERIC_PLANT_NOT_CALIBRATED',
          'identity_parity': 'PASS', 'deterministic_repeats': 'NOT_CHECKED_IN_SINGLE_RUN',
          'case_delay_count': len(variants), 'arms': arms, 'comparisons': comparisons,
          'policy_sha256': POLICY_SHA256, 'catalog_sha256': policy['catalog_sha256'],
          'unexercised': ['lane_perception', 'model', 'planner', 'vehicle_carcontroller', 'EPS'],
          'readiness': 'NOT_READY', 'vehicle_activation_allowed': False, **dict.fromkeys(AUTHORITY, False)}
