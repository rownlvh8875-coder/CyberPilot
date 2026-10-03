"""Actual LatControlTorque over a generic offline synthetic plant.

This diagnostic has no CAN, vehicle, profile, tuning, shadow, runtime, or
promotion authority. The generic plant is not a calibrated vehicle model.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from types import SimpleNamespace

from openpilot.tools.cyber_autotune.contracts import finite_number
from openpilot.tools.cyber_autotune.synthetic_lateral_plant import (
  PlantConfig,
  SyntheticLateralPlant,
)
from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
  SyntheticScenario,
  _valid_scenario,
  generate_frames,
  matrix_sha256,
)


DEFAULT_PLANT_CONFIG = PlantConfig(.01, .03, .20, 3.0, .05, 2.8, 16.0, 1.0)
NATIVE_TO_PLANT_SIGN = -1.0


@dataclass(frozen=True)
class SyntheticClosedLoopScenarioResult:
  scenario_id: str
  status: str
  blockers: tuple[str, ...]
  sample_count: int = 0
  trace_sha256: str | None = None
  car_params_sha256: str | None = None
  controller_executed: bool = False
  plant_executed: bool = False
  physical_delay_owner: str | None = None
  controller_delay_queue_present: bool = False
  native_to_plant_sign: float = NATIVE_TO_PLANT_SIGN
  lateral_error_rmse_m: float | None = None
  maximum_abs_lateral_error_m: float | None = None
  maximum_abs_heading_error_rad: float | None = None
  steering_jerk_rmse_deg_s3: float | None = None
  saturation_ratio: float | None = None
  command_reversal_events: int = 0
  signed_mean_desired_curvature_1pm: float | None = None
  signed_mean_actual_curvature_1pm: float | None = None
  maximum_abs_requested_torque: float | None = None
  inactive_requested_torque_max_abs: float | None = None
  inactive_applied_command_max_abs: float | None = None
  driver_intervention_frames: int = 0
  performance_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  vehicle_or_can_write: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


@dataclass(frozen=True)
class SyntheticClosedLoopMatrixReport:
  status: str
  blockers: tuple[str, ...]
  catalog_sha256: str | None = None
  car_params_sha256: str | None = None
  result_sha256: str | None = None
  scenario_count: int = 0
  completed_count: int = 0
  rejected_input_count: int = 0
  blocked_count: int = 0
  all_nominal_completed: bool = False
  fault_inputs_rejected: bool = False
  scenarios: tuple[SyntheticClosedLoopScenarioResult, ...] = ()
  qualified_closed_loop: bool = field(default=False, init=False)
  performance_qualified: bool = field(default=False, init=False)
  candidate_generation_allowed: bool = field(default=False, init=False)
  vehicle_or_can_write: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _canonical(value) -> bytes:
  return json.dumps(
    value, sort_keys=True, separators=(',', ':'), allow_nan=False,
  ).encode()


def _digest(value) -> str:
  return hashlib.sha256(_canonical(value)).hexdigest()


def _scenario_blocked(
  scenario_id: str,
  reason: str,
  *,
  car_params_sha256: str | None = None,
) -> SyntheticClosedLoopScenarioResult:
  return SyntheticClosedLoopScenarioResult(
    scenario_id=scenario_id,
    status='BLOCKED',
    blockers=(reason,),
    car_params_sha256=car_params_sha256,
  )


def _fault_result(
  scenario: SyntheticScenario,
) -> SyntheticClosedLoopScenarioResult:
  reason = (
    'SENSOR_INVALID'
    if 'sensor_dropout' in scenario.stress_axes
    else 'NONUNIFORM_TIMEBASE'
  )
  return SyntheticClosedLoopScenarioResult(
    scenario_id=scenario.scenario_id,
    status='REJECTED_INPUT',
    blockers=(reason,),
  )


def _rmse(values: tuple[float, ...]) -> float:
  return math.sqrt(math.fsum(value * value for value in values) / len(values))


def _command_reversals(values: tuple[float, ...]) -> int:
  signs = tuple(1 if value > 1e-9 else -1 if value < -1e-9 else 0 for value in values)
  nonzero = tuple(sign for sign in signs if sign != 0)
  return sum(right != left for left, right in zip(nonzero, nonzero[1:], strict=False))


def _steering_jerk_rmse(angles: tuple[float, ...], dt_s: float) -> float:
  if len(angles) < 4:
    return 0.0
  values = tuple(
    (
      angles[index + 3]
      - 3.0 * angles[index + 2]
      + 3.0 * angles[index + 1]
      - angles[index]
    ) / dt_s ** 3
    for index in range(len(angles) - 3)
  )
  return _rmse(values)


def _execute_nominal(
  scenario: SyntheticScenario,
  car_params_bytes: bytes,
  plant_config: PlantConfig,
  car_params_sha256: str,
) -> SyntheticClosedLoopScenarioResult:
  try:
    import numpy as np
    from opendbc.car import DT_CTRL, structs
    from opendbc.car.interfaces import CarInterfaceBase
    from opendbc.car.vehicle_model import VehicleModel
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
  except Exception:
    return _scenario_blocked(
      scenario.scenario_id, 'CONTROLLER_IMPORT_FAILED',
      car_params_sha256=car_params_sha256,
    )

  if scenario.dt_s != DT_CTRL or plant_config.dt_s != DT_CTRL:
    return _scenario_blocked(
      scenario.scenario_id, 'CONTROLLER_TIMESTEP_MISMATCH',
      car_params_sha256=car_params_sha256,
    )

  class LinearConversion:
    torque_from_lateral_accel_linear = CarInterfaceBase.torque_from_lateral_accel_linear
    torque_from_lateral_accel = CarInterfaceBase.torque_from_lateral_accel
    lateral_accel_from_torque_linear = CarInterfaceBase.lateral_accel_from_torque_linear
    lateral_accel_from_torque = CarInterfaceBase.lateral_accel_from_torque

  try:
    context = structs.CarParams.from_bytes(car_params_bytes)
  except Exception:
    return _scenario_blocked(
      scenario.scenario_id, 'INVALID_CAR_PARAMS',
      car_params_sha256=car_params_sha256,
    )

  try:
    with context as cp:
      positive_fields = (
        'mass', 'wheelbase', 'centerToFront', 'rotationalInertia',
        'tireStiffnessFront', 'tireStiffnessRear', 'steerRatio',
        'steerLimitTimer',
      )
      if (
        cp.carFingerprint != 'HYUNDAI_SANTA_FE_2022'
        or cp.lateralTuning.which() != 'torque'
        or str(cp.steerControlType) != 'torque'
        or any(
          not finite_number(getattr(cp, name)) or getattr(cp, name) <= 0
          for name in positive_fields
        )
        or not cp.centerToFront < cp.wheelbase
      ):
        return _scenario_blocked(
          scenario.scenario_id, 'INVALID_CAR_PARAMS',
          car_params_sha256=car_params_sha256,
        )

      try:
        controller = LatControlTorque(cp, LinearConversion(), DT_CTRL)
        vehicle_model = VehicleModel(cp)
        plant = SyntheticLateralPlant(plant_config)
        frames = generate_frames(scenario)
        trace = []
        previous_time = None
        for frame in frames:
          if not frame.sensor_valid:
            raise ValueError('INVALID_SENSOR_IN_NOMINAL_RUN')
          if previous_time is not None and not math.isclose(
            frame.time_s - previous_time, DT_CTRL,
            rel_tol=1e-12, abs_tol=1e-12,
          ):
            raise ValueError('NONUNIFORM_TIMEBASE')
          previous_time = frame.time_s

          plant_state = plant.snapshot()
          state = structs.CarState()
          state.vEgo = state.vEgoRaw = frame.speed_mps
          state.aEgo = 0.0
          state.steeringAngleDeg = -plant_state.steering_angle_deg
          state.steeringRateDeg = -plant_state.steering_rate_deg_s
          state.steeringTorque = 1.0 if frame.steering_pressed else 0.0
          state.steeringPressed = frame.steering_pressed
          params = SimpleNamespace(roll=0.0, angleOffsetDeg=0.0)
          vehicle_model.update_params(1.0, cp.steerRatio)
          with np.errstate(over='raise', invalid='raise', divide='raise'):
            torque, _, _ = controller.update(
              frame.active,
              state,
              vehicle_model,
              params,
              False,
              frame.desired_curvature_1pm,
              False,
              frame.lateral_delay_s,
            )
          torque = float(torque)
          if not finite_number(torque) or abs(torque) > 1.0:
            raise ValueError('INVALID_NATIVE_TORQUE')
          plant_sample = plant.step(
            NATIVE_TO_PLANT_SIGN * torque,
            speed_mps=frame.speed_mps,
            desired_curvature_1pm=frame.desired_curvature_1pm,
            friction_scale=frame.plant_friction_scale,
          )
          actual_curvature = plant_sample.yaw_rate_rps / frame.speed_mps
          trace.append({
            'step_index': frame.step_index,
            'time_s': frame.time_s,
            'active': frame.active,
            'steering_pressed': frame.steering_pressed,
            'desired_curvature_1pm': frame.desired_curvature_1pm,
            'requested_torque': torque,
            'plant_command': NATIVE_TO_PLANT_SIGN * torque,
            'applied_command': plant_sample.applied_command,
            'actual_curvature_1pm': actual_curvature,
            'lateral_accel_mps2': plant_sample.lateral_accel_mps2,
            'heading_error_rad': plant_sample.heading_error_rad,
            'lateral_error_m': plant_sample.lateral_error_m,
            'steering_angle_deg': plant_sample.steering_angle_deg,
            'steering_rate_deg_s': plant_sample.steering_rate_deg_s,
            'saturated': abs(torque) >= 0.999 or plant_sample.saturated,
          })
      except Exception:
        return _scenario_blocked(
          scenario.scenario_id, 'CONTROLLER_OR_PLANT_EXECUTION_FAILED',
          car_params_sha256=car_params_sha256,
        )
  except Exception:
    return _scenario_blocked(
      scenario.scenario_id, 'INVALID_CAR_PARAMS',
      car_params_sha256=car_params_sha256,
    )

  requested = tuple(row['requested_torque'] for row in trace)
  desired = tuple(row['desired_curvature_1pm'] for row in trace)
  actual = tuple(row['actual_curvature_1pm'] for row in trace)
  lateral_error = tuple(row['lateral_error_m'] for row in trace)
  heading_error = tuple(row['heading_error_rad'] for row in trace)
  steering_angles = tuple(row['steering_angle_deg'] for row in trace)
  inactive_requested = tuple(
    abs(row['requested_torque']) for row in trace if not row['active']
  )
  inactive_applied = tuple(
    abs(row['applied_command']) for row in trace if not row['active']
  )
  return SyntheticClosedLoopScenarioResult(
    scenario_id=scenario.scenario_id,
    status='COMPLETED_DIAGNOSTIC',
    blockers=('GENERIC_SYNTHETIC_PLANT_NOT_VEHICLE_CALIBRATED',),
    sample_count=len(trace),
    trace_sha256=_digest(trace),
    car_params_sha256=car_params_sha256,
    controller_executed=True,
    plant_executed=True,
    physical_delay_owner='PLANT',
    controller_delay_queue_present=False,
    lateral_error_rmse_m=_rmse(lateral_error),
    maximum_abs_lateral_error_m=max(abs(value) for value in lateral_error),
    maximum_abs_heading_error_rad=max(abs(value) for value in heading_error),
    steering_jerk_rmse_deg_s3=_steering_jerk_rmse(
      steering_angles, scenario.dt_s,
    ),
    saturation_ratio=sum(row['saturated'] for row in trace) / len(trace),
    command_reversal_events=_command_reversals(requested),
    signed_mean_desired_curvature_1pm=math.fsum(desired) / len(desired),
    signed_mean_actual_curvature_1pm=math.fsum(actual) / len(actual),
    maximum_abs_requested_torque=max(abs(value) for value in requested),
    inactive_requested_torque_max_abs=max(inactive_requested, default=0.0),
    inactive_applied_command_max_abs=max(inactive_applied, default=0.0),
    driver_intervention_frames=sum(row['steering_pressed'] for row in trace),
  )


def run_synthetic_scenario(
  scenario: SyntheticScenario,
  car_params_bytes: bytes,
  plant_config: PlantConfig | None = None,
) -> SyntheticClosedLoopScenarioResult:
  """Run one scenario with fresh native-controller and generic-plant state."""
  scenario_id = getattr(scenario, 'scenario_id', 'invalid')
  if not _valid_scenario(scenario):
    return _scenario_blocked(scenario_id, 'INVALID_SCENARIO')
  if scenario.expected_outcome == 'REJECTED_INPUT':
    return _fault_result(scenario)
  if type(car_params_bytes) is not bytes or not car_params_bytes:
    return _scenario_blocked(scenario.scenario_id, 'INVALID_CAR_PARAMS')
  config = DEFAULT_PLANT_CONFIG if plant_config is None else plant_config
  try:
    SyntheticLateralPlant(config)
  except ValueError:
    return _scenario_blocked(scenario.scenario_id, 'INVALID_PLANT_CONFIG')
  car_params_sha256 = hashlib.sha256(car_params_bytes).hexdigest()
  return _execute_nominal(
    scenario, car_params_bytes, config, car_params_sha256,
  )


def _matrix_blocked(reason: str) -> SyntheticClosedLoopMatrixReport:
  return SyntheticClosedLoopMatrixReport('BLOCKED', (reason,))


def run_synthetic_matrix(
  matrix: tuple[SyntheticScenario, ...],
  car_params_bytes: bytes,
  plant_config: PlantConfig | None = None,
) -> SyntheticClosedLoopMatrixReport:
  """Run exact declared scenarios with fresh state and no promotion authority."""
  if type(matrix) is not tuple or not matrix:
    return _matrix_blocked('INVALID_MATRIX')
  scenario_ids = tuple(getattr(item, 'scenario_id', None) for item in matrix)
  if any(type(item) is not str for item in scenario_ids):
    return _matrix_blocked('INVALID_MATRIX')
  if len(scenario_ids) != len(set(scenario_ids)):
    return _matrix_blocked('DUPLICATE_SCENARIO_ID')

  results = tuple(
    run_synthetic_scenario(item, car_params_bytes, plant_config)
    for item in matrix
  )
  completed = sum(item.status == 'COMPLETED_DIAGNOSTIC' for item in results)
  rejected = sum(item.status == 'REJECTED_INPUT' for item in results)
  blocked = sum(item.status == 'BLOCKED' for item in results)
  nominal_expected = sum(item.expected_outcome == 'COMPLETED' for item in matrix)
  fault_expected = len(matrix) - nominal_expected
  all_nominal_completed = completed == nominal_expected
  fault_inputs_rejected = rejected == fault_expected
  car_params_sha256 = (
    hashlib.sha256(car_params_bytes).hexdigest()
    if type(car_params_bytes) is bytes and car_params_bytes
    else None
  )
  if blocked or not all_nominal_completed or not fault_inputs_rejected:
    reasons = tuple(
      f'SCENARIO_BLOCKED:{item.scenario_id}:{item.blockers[0]}'
      for item in results if item.status == 'BLOCKED'
    )
    return SyntheticClosedLoopMatrixReport(
      status='BLOCKED',
      blockers=reasons or ('SCENARIO_OUTCOME_MISMATCH',),
      catalog_sha256=matrix_sha256(matrix),
      car_params_sha256=car_params_sha256,
      scenario_count=len(matrix),
      completed_count=completed,
      rejected_input_count=rejected,
      blocked_count=blocked,
      all_nominal_completed=all_nominal_completed,
      fault_inputs_rejected=fault_inputs_rejected,
      scenarios=results,
    )

  payload = {
    'catalog_sha256': matrix_sha256(matrix),
    'car_params_sha256': car_params_sha256,
    'scenarios': [asdict(item) for item in results],
  }
  return SyntheticClosedLoopMatrixReport(
    status='SYNTHETIC_CLOSED_LOOP_DIAGNOSTIC',
    blockers=(
      'GENERIC_SYNTHETIC_PLANT_NOT_VEHICLE_CALIBRATED',
      'PERFORMANCE_GATE_NOT_EVALUATED',
    ),
    catalog_sha256=payload['catalog_sha256'],
    car_params_sha256=car_params_sha256,
    result_sha256=_digest(payload),
    scenario_count=len(matrix),
    completed_count=completed,
    rejected_input_count=rejected,
    blocked_count=0,
    all_nominal_completed=True,
    fault_inputs_rejected=True,
    scenarios=results,
  )
