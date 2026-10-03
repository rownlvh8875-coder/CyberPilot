"""Deterministic generic lateral plant for offline synthetic validation only.

This is not a calibrated vehicle model and grants no CAN, vehicle, runtime,
profile, tuning, shadow, or promotion authority.
"""
from collections import deque
from dataclasses import dataclass, field
import math

from openpilot.tools.cyber_autotune.contracts import finite_number


@dataclass(frozen=True)
class PlantConfig:
  dt_s: float
  actuator_delay_s: float
  response_tau_s: float
  lateral_accel_per_command_mps2: float
  command_friction: float
  wheelbase_m: float
  steer_ratio: float
  command_limit: float


@dataclass(frozen=True)
class PlantState:
  step_index: int
  applied_command: float
  lateral_accel_mps2: float
  yaw_rate_rps: float
  heading_error_rad: float
  lateral_error_m: float
  steering_angle_deg: float
  steering_rate_deg_s: float


@dataclass(frozen=True)
class PlantSample:
  step_index: int
  requested_command: float
  applied_command: float
  effective_command: float
  lateral_accel_mps2: float
  yaw_rate_rps: float
  heading_error_rad: float
  lateral_error_m: float
  steering_angle_deg: float
  steering_rate_deg_s: float
  saturated: bool
  physical_delay_owner: str
  controller_delay_queue_present: bool
  state: PlantState
  vehicle_or_can_write: bool = field(default=False, init=False)
  runtime_accepted: bool = field(default=False, init=False)
  promotable: bool = field(default=False, init=False)


def _valid_config(config) -> bool:
  if type(config) is not PlantConfig:
    return False
  values = (
    config.dt_s,
    config.actuator_delay_s,
    config.response_tau_s,
    config.lateral_accel_per_command_mps2,
    config.command_friction,
    config.wheelbase_m,
    config.steer_ratio,
    config.command_limit,
  )
  return (
    all(finite_number(value) for value in values)
    and 0.0 < config.dt_s <= 0.1
    and 0.0 <= config.actuator_delay_s <= 1.0
    and config.dt_s <= config.response_tau_s <= 5.0
    and 0.0 < config.lateral_accel_per_command_mps2 <= 20.0
    and 0.0 <= config.command_friction < config.command_limit
    and 0.5 <= config.wheelbase_m <= 10.0
    and 1.0 <= config.steer_ratio <= 40.0
    and 0.0 < config.command_limit <= 1.0
  )


class SyntheticLateralPlant:
  """One-state generic plant with one plant-owned physical delay queue."""

  def __init__(self, config: PlantConfig):
    if not _valid_config(config):
      raise ValueError('INVALID_PLANT_CONFIG')
    delay_steps = round(config.actuator_delay_s / config.dt_s)
    if abs(delay_steps * config.dt_s - config.actuator_delay_s) > 1e-12:
      raise ValueError('NONINTEGER_DELAY_STEPS')
    self.config = config
    self._delay_steps = delay_steps
    self.reset()

  def reset(self) -> None:
    self._delay_queue = deque([0.0] * self._delay_steps)
    self._state = PlantState(
      step_index=-1,
      applied_command=0.0,
      lateral_accel_mps2=0.0,
      yaw_rate_rps=0.0,
      heading_error_rad=0.0,
      lateral_error_m=0.0,
      steering_angle_deg=0.0,
      steering_rate_deg_s=0.0,
    )

  def snapshot(self) -> PlantState:
    return self._state

  def _delayed_command(self, requested: float) -> float:
    if self._delay_steps == 0:
      return requested
    applied = self._delay_queue.popleft()
    self._delay_queue.append(requested)
    return applied

  def step(
    self,
    command: float,
    *,
    speed_mps: float,
    desired_curvature_1pm: float,
    friction_scale: float = 1.0,
  ) -> PlantSample:
    values = (command, speed_mps, desired_curvature_1pm, friction_scale)
    if not all(finite_number(value) for value in values):
      raise ValueError('INVALID_PLANT_INPUT')
    if not 0.0 < speed_mps <= 80.0:
      raise ValueError('INVALID_SPEED')
    if abs(desired_curvature_1pm) > 0.1:
      raise ValueError('INVALID_CURVATURE')
    if not 0.1 <= friction_scale <= 3.0:
      raise ValueError('INVALID_FRICTION_SCALE')

    limit = self.config.command_limit
    requested = max(-limit, min(limit, float(command)))
    saturated = requested != float(command)
    applied = self._delayed_command(requested)

    friction = self.config.command_friction * friction_scale
    effective = math.copysign(max(abs(applied) - friction, 0.0), applied)
    if effective == 0.0:
      effective = 0.0

    target_accel = self.config.lateral_accel_per_command_mps2 * effective
    alpha = self.config.dt_s / self.config.response_tau_s
    lateral_accel = self._state.lateral_accel_mps2 + alpha * (
      target_accel - self._state.lateral_accel_mps2
    )
    yaw_rate = lateral_accel / speed_mps
    desired_yaw_rate = desired_curvature_1pm * speed_mps
    heading_error = self._state.heading_error_rad + (
      yaw_rate - desired_yaw_rate
    ) * self.config.dt_s
    lateral_error = self._state.lateral_error_m + (
      speed_mps * heading_error * self.config.dt_s
    )

    actual_curvature = yaw_rate / speed_mps
    steering_angle = math.degrees(
      math.atan(self.config.wheelbase_m * actual_curvature)
    ) * self.config.steer_ratio
    steering_rate = (
      steering_angle - self._state.steering_angle_deg
    ) / self.config.dt_s
    state = PlantState(
      step_index=self._state.step_index + 1,
      applied_command=applied,
      lateral_accel_mps2=lateral_accel,
      yaw_rate_rps=yaw_rate,
      heading_error_rad=heading_error,
      lateral_error_m=lateral_error,
      steering_angle_deg=steering_angle,
      steering_rate_deg_s=steering_rate,
    )
    self._state = state

    return PlantSample(
      step_index=state.step_index,
      requested_command=requested,
      applied_command=applied,
      effective_command=effective,
      lateral_accel_mps2=lateral_accel,
      yaw_rate_rps=yaw_rate,
      heading_error_rad=heading_error,
      lateral_error_m=lateral_error,
      steering_angle_deg=steering_angle,
      steering_rate_deg_s=steering_rate,
      saturated=saturated,
      physical_delay_owner='PLANT',
      controller_delay_queue_present=False,
      state=state,
    )
