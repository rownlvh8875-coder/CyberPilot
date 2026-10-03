"""Offline native controller-core experiment over declared generic plants.

Supplied trajectory/plan fixtures bypass perception/planning. No car controller,
CAN, Params, persistent profile or runtime activation interface exists here.
Use a bounded fresh-process supervisor for final evidence, not a control thread.
"""
from collections import deque
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

from openpilot.tools.cyber_autotune.contracts import finite_number
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.synthetic_lateral_closed_loop import DEFAULT_PLANT_CONFIG
from openpilot.tools.cyber_autotune.synthetic_lateral_plant import SyntheticLateralPlant
from openpilot.tools.cyber_autotune.synthetic_metrics import lateral_metrics, longitudinal_metrics
from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, catalog_digest, frame_digest, frames, input_digest, validate_frames


POLICY_SHA256 = '4ff9dcfaa369cbdcee53f56a8db9c160efb3005a50f463e4125a1f41b74e8d35'
POLICY_PATH = Path(__file__).resolve().parents[3] / 'docs/cyberpilot/policies/synthetic-stress-candidate-v2.json'


def frozen_policy() -> dict:
  raw = POLICY_PATH.read_bytes()
  if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
    raise ValueError('SYNTHETIC_POLICY_CHANGED')
  return json.loads(raw)


def feedback_angle_deg(model, curvature: float, speed: float) -> float:
  """Native-sign feedback inverse; generic plant's display geometry is not CP."""
  return math.degrees(model.get_steer_from_curvature(-curvature, speed, 0.))


def _lateral_trace(case, rows, cp, scale, delay_s):
  from opendbc.car import structs
  from opendbc.car.interfaces import CarInterfaceBase
  from opendbc.car.vehicle_model import VehicleModel
  from openpilot.common.pid import PIDController
  from openpilot.selfdrive.controls.lib.latcontrol_torque import INTERP_SPEEDS, KP_INTERP, KI, LatControlTorque

  class LinearConversion:
    torque_from_lateral_accel_linear = CarInterfaceBase.torque_from_lateral_accel_linear
    torque_from_lateral_accel = CarInterfaceBase.torque_from_lateral_accel
    lateral_accel_from_torque_linear = CarInterfaceBase.lateral_accel_from_torque_linear
    lateral_accel_from_torque = CarInterfaceBase.lateral_accel_from_torque

  controller = LatControlTorque(cp.as_reader(), LinearConversion(), case.dt_s)
  # This upstream revision stores gains on the PID, not in torque CarParams.
  # Replace only this fresh synthetic instance; do not mutate module tables.
  controller.pid = PIDController((INTERP_SPEEDS, [value * scale for value in KP_INTERP]), KI,
                                 pos_limit=controller.pid.pos_limit, neg_limit=controller.pid.neg_limit, rate=1 / case.dt_s)
  model = VehicleModel(cp)
  config = replace(DEFAULT_PLANT_CONFIG, actuator_delay_s=delay_s)
  plant = SyntheticLateralPlant(config)
  trace = []
  prior_command = 0.
  prior_feedback = 0.
  for frame in rows:
    observed = plant.snapshot()
    state = structs.CarState()
    state.vEgo = state.vEgoRaw = frame.speed_mps
    # Injection changes measured pose, never synthetic ground truth.
    model.update_params(1., cp.steerRatio)
    measured_curvature = observed.lateral_accel_mps2 / frame.speed_mps ** 2 + frame.pose_yaw_bias / frame.speed_mps
    state.steeringAngleDeg = feedback_angle_deg(model, measured_curvature, frame.speed_mps)
    state.steeringRateDeg = (state.steeringAngleDeg - prior_feedback) / case.dt_s
    prior_feedback = state.steeringAngleDeg
    state.steeringPressed = frame.steering_pressed
    state.steeringTorque = 1. if frame.steering_pressed else 0.
    params = SimpleNamespace(roll=0., angleOffsetDeg=0.)
    requested, _, _ = controller.update(frame.active, state, model, params, False, frame.curvature, False, .15)
    requested = float(requested)
    if not finite_number(requested) or abs(requested) > 1:
      raise ValueError('INVALID_NATIVE_TORQUE')
    command = -requested  # preserved v1 native-to-plant sign
    limited = command
    if case.case_id == 'lat_rate_limit' and frame.active:
      limited = max(prior_command - .5 * case.dt_s, min(prior_command + .5 * case.dt_s, command))
    if not frame.active:
      limited = 0.
    rate_limited = limited != command
    prior_command = limited
    # Time-varying generic response stress; not a learned vehicle parameter.
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
  return tuple(trace), asdict(config)


def _longitudinal_trace(case, rows, cp, scale, delay_s):
  from opendbc.car import structs
  from opendbc.car.hyundai.interface import CarInterface
  from openpilot.cereal import log
  from openpilot.selfdrive.controls.lib.longcontrol import LongControl

  cp.longitudinalTuning.kiV = [value * scale for value in cp.longitudinalTuning.kiV]
  controller = LongControl(cp)
  delay_queue = deque([0.] * round(delay_s / case.dt_s))
  speed, accel, response, position, lead_position = rows[0].speed_mps, 0., 0., 0., 35.
  config = {'dt_s': case.dt_s, 'physical_delay_s': delay_s, 'response_tau_s': .2,
            'minimum_accel_mps2': -3.5, 'maximum_accel_mps2': 2., 'model': 'GENERIC_1D_NOT_CALIBRATED'}
  trace = []
  for frame in rows:
    state = structs.CarState(vEgo=speed, aEgo=accel, vCruise=frame.target_speed_mps * 3.6, brakePressed=False)
    state.cruiseState.standstill = False
    plan = log.LongitudinalPlan.new_message(aTarget=frame.supplied_accel_mps2, shouldStop=frame.should_stop)
    limits = CarInterface.get_pid_accel_limits(cp, speed, frame.target_speed_mps)
    if tuple(limits) != (-3.5, 2.):
      raise ValueError('UNSUPPORTED_NATIVE_LIMITS')
    if not frame.active:
      controller.reset()
    requested = float(controller.update(frame.active, state, plan.aTarget, plan.shouldStop, limits))
    if not finite_number(requested) or not limits[0] <= requested <= limits[1]:
      raise ValueError('INVALID_NATIVE_ACCEL')
    applied = requested
    if delay_queue:
      applied = delay_queue.popleft()
      delay_queue.append(requested)
    response += case.dt_s / config['response_tau_s'] * (applied - response)
    next_speed = max(0., speed + (response + frame.grade_accel) * case.dt_s)
    accel = (next_speed - speed) / case.dt_s
    position += .5 * (speed + next_speed) * case.dt_s
    speed = next_speed
    lead_position += frame.lead_speed_mps * case.dt_s
    if frame.lead_distance_reset_m is not None:
      lead_position = position + frame.lead_distance_reset_m
    trace.append({
      'interval_start_s': frame.time_ns * 1e-9, 'time_s': frame.time_ns * 1e-9 + case.dt_s,
      'speed_mps': speed, 'accel_mps2': accel,
      'target_accel_mps2': float(plan.aTarget), 'requested_accel_mps2': requested,
      'lead_available': frame.lead_available, 'lead_distance_m': lead_position - position,
      'lead_speed_mps': frame.lead_speed_mps, 'desired_distance_m': 5. + 1.5 * speed,
      'position_m': position, 'stop_target_m': frame.stop_target_m, 'should_stop': frame.should_stop,
      'stop_required': frame.stop_required, 'target_speed_mps': frame.target_speed_mps, 'active': frame.active,
      'saturated': requested <= limits[0] + 1e-9 or requested >= limits[1] - 1e-9,
    })
  return tuple(trace), config


def run_variant(case_id: str, *, tune_id: str = 'identity', delay_s: float | None = None) -> dict:
  """Fresh in-memory CP/controller/plant per case; no candidate is persisted."""
  policy = frozen_policy()
  if catalog_digest() != policy['catalog_sha256']:
    raise ValueError('SYNTHETIC_CATALOG_CHANGED')
  return _run_variant(policy, case_id, tune_id=tune_id, delay_s=delay_s)


def run_batch(tune_id: str) -> list[dict]:
  """Fixed full catalog; verify boundary identity, fresh state for every variant."""
  policy = frozen_policy()
  if catalog_digest() != policy['catalog_sha256']:
    raise ValueError('SYNTHETIC_CATALOG_CHANGED')
  results = [_run_variant(policy, case.case_id, tune_id=tune_id, delay_s=delay)
             for case in catalog() for delay in case.physical_delays_s]
  if catalog_digest() != policy['catalog_sha256'] or frozen_policy() != policy:
    raise ValueError('SYNTHETIC_BINDING_CHANGED_DURING_RUN')
  return results


def _run_variant(policy, case_id, *, tune_id, delay_s):
  cases = {case.case_id: case for case in catalog()}
  if type(case_id) is not str or case_id not in cases or type(tune_id) is not str or tune_id not in policy['candidate_grid']:
    raise ValueError('UNDECLARED_SYNTHETIC_EXPERIMENT')
  case = cases[case_id]
  delay = case.physical_delays_s[0] if delay_s is None else delay_s
  if not finite_number(delay) or delay not in case.physical_delays_s:
    raise ValueError('UNDECLARED_PHYSICAL_DELAY')
  tune = policy['candidate_grid'][tune_id]
  rows = frames(case)
  actual_input_sha = frame_digest(rows)
  if actual_input_sha != input_digest(case):
    raise ValueError('SYNTHETIC_EXECUTED_INPUT_CHANGED')
  input_status = validate_frames(rows, case.dt_s)
  result = {
    'schema': 'synthetic-native-v2', 'scope': 'NATIVE_CONTROLLER_CORE_SUPPLIED_PLAN_GENERIC_PLANT',
    'case_id': case_id, 'axis': case.axis, 'tune_id': tune_id, 'tune_sha256': digest(canonical(tune)),
    'policy_sha256': POLICY_SHA256, 'input_sha256': actual_input_sha, 'physical_delay_s': delay,
    'physical_delay_owner': 'PLANT', 'controller_delay_queue_present': False,
    'input_status': input_status, 'controller_executed': False, 'metrics': None,
    'real_vehicle_verified': False, 'runtime_accepted': False, 'active_profile_enabled': False,
    'vehicle_write_enabled': False, 'can_write_enabled': False, 'promotable_to_vehicle': False,
    'perception_planner_executed': False, 'vehicle_carcontroller_executed': False,
    'unexercised_inputs': ['lane_visible'] if case.axis == 'lateral' else ['radar_model_disagreement'],
    'unavailable_behavior': 'PERCEPTION_PLANNER_AND_VEHICLE_CARCONTROLLER',
    'time_semantics': 'INPUT_COMMAND_AT_INTERVAL_START_STATE_AT_INTERVAL_END',
    'lateral_reference_history_compensation_s': .15 if case.axis == 'lateral' else None,
    'feedback_measurement': 'NATIVE_VEHICLE_MODEL_INVERSE' if case.axis == 'lateral' else 'GENERIC_PLANT_STATE',
  }
  if input_status != case.expected_input_status:
    return {**result, 'status': 'BLOCKED', 'reason': 'SCENARIO_INPUT_EXPECTATION_MISMATCH'}
  if input_status != 'VALID':
    return {**result, 'status': 'REJECTED_INPUT'}
  from opendbc.car.hyundai.interface import CarInterface
  from opendbc.car.hyundai.values import CAR
  import numpy as np

  cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
  cp.openpilotLongitudinalControl = True  # synthetic fixture only, never a device CP
  result['base_car_params_sha256'] = digest(cp.to_bytes())
  cp = cp.as_reader().as_builder()
  with np.errstate(over='raise', invalid='raise', divide='raise'):
    if case.axis == 'lateral':
      trace, config = _lateral_trace(case, rows, cp, tune['lateral_kp_scale'], delay)
      metrics = lateral_metrics(trace, case.dt_s)
      controller_name = 'LatControlTorque'
    else:
      trace, config = _longitudinal_trace(case, rows, cp, tune['longitudinal_ki_scale'], delay)
      metrics = longitudinal_metrics(trace, case.dt_s)
      metrics['stopping_error_abs_m'] = abs(metrics['stopping_error_m']) if metrics['stopping_error_m'] is not None else None
      controller_name = 'LongControl'
  result.update(status='COMPLETED_SYNTHETIC_ONLY', controller_executed=True, controller=controller_name,
                metrics=metrics, plant_sha256=digest(canonical(config)),
                candidate_car_params_sha256=digest(cp.to_bytes()),
                reset_sha256=digest(canonical({'controller': 'FRESH', 'plant': 'FRESH', 'delay_queue': 'ZERO', 'step_index': 0})))
  canonical(result)
  return result
