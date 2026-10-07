"""Pure offline curvature/yaw plant step.

This module intentionally contains no fitted vehicle coefficients, log loading,
controller callback, Params access, CAN transport, device IO, acceptance rule,
or promotion surface. The caller owns the descriptive coefficients and domain.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CurvatureYawPlantConfig:
  dt_s: float
  delay_steps: int
  min_speed_mps: float
  max_speed_mps: float
  command_limit: float
  curvature_intercept_1pm: float
  curvature_ar: float
  command_gain_1pm: float
  command_speed_gain_s_per_m2: float
  command_inv_speed_gain_per_s: float
  roll_gain_1pm_per_rad: float
  yaw_ar: float
  yaw_bias_rad_s: float


@dataclass(frozen=True)
class CurvatureYawPlantState:
  curvature_1pm: float
  yaw_rate_rad_s: float
  command_history: tuple[float, ...]


@dataclass(frozen=True)
class CurvatureYawPlantObservation:
  status: str
  reason: str
  delayed_command: float | None
  current_yaw_target_rad_s: float | None
  next_yaw_target_rad_s: float | None
  next_state: CurvatureYawPlantState | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _finite(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _blocked(reason: str) -> CurvatureYawPlantObservation:
  return CurvatureYawPlantObservation(
    status='BLOCKED',
    reason=reason,
    delayed_command=None,
    current_yaw_target_rad_s=None,
    next_yaw_target_rad_s=None,
    next_state=None,
  )


def _valid_config(config: CurvatureYawPlantConfig) -> bool:
  if not isinstance(config, CurvatureYawPlantConfig):
    return False
  if type(config.delay_steps) is not int or not 0 <= config.delay_steps <= 10_000:
    return False

  finite_values = (
    config.dt_s,
    config.min_speed_mps,
    config.max_speed_mps,
    config.command_limit,
    config.curvature_intercept_1pm,
    config.curvature_ar,
    config.command_gain_1pm,
    config.command_speed_gain_s_per_m2,
    config.command_inv_speed_gain_per_s,
    config.roll_gain_1pm_per_rad,
    config.yaw_ar,
    config.yaw_bias_rad_s,
  )
  if not all(_finite(value) for value in finite_values):
    return False
  if not 0.0 < float(config.dt_s) <= 0.1:
    return False
  if not 0.0 < float(config.min_speed_mps) < float(config.max_speed_mps):
    return False
  if not 0.0 < float(config.command_limit) <= 1.0:
    return False
  if not abs(float(config.curvature_ar)) < 1.0:
    return False
  if not 0.0 <= float(config.yaw_ar) < 1.0:
    return False
  return True


def _valid_state(config: CurvatureYawPlantConfig, state: CurvatureYawPlantState) -> bool:
  if not isinstance(state, CurvatureYawPlantState):
    return False
  if not _finite(state.curvature_1pm) or not _finite(state.yaw_rate_rad_s):
    return False
  if type(state.command_history) is not tuple or len(state.command_history) != config.delay_steps:
    return False
  limit = float(config.command_limit)
  return all(_finite(value) and abs(float(value)) <= limit for value in state.command_history)


def observe_curvature_yaw_step(
  config: CurvatureYawPlantConfig,
  state: CurvatureYawPlantState,
  *,
  command: float,
  speed_mps: float,
  roll_rad: float,
) -> CurvatureYawPlantObservation:
  """Advance one descriptive offline plant state.

  Sign convention is caller-owned but must be internally consistent. This
  primitive uses the screening convention where yaw target equals negative
  curvature times speed. It neither applies nor returns a vehicle command.
  """
  if not _valid_config(config):
    return _blocked('INVALID_CONFIG')
  if not _valid_state(config, state):
    return _blocked('INVALID_STATE')

  if (
    not all(_finite(value) for value in (command, speed_mps, roll_rad))
    or abs(float(command)) > float(config.command_limit)
    or not float(config.min_speed_mps) <= float(speed_mps) <= float(config.max_speed_mps)
  ):
    return _blocked('INPUT_OUTSIDE_DOMAIN')

  command_f = float(command)
  speed = float(speed_mps)
  roll = float(roll_rad)

  if config.delay_steps == 0:
    delayed = command_f
    history: tuple[float, ...] = ()
  else:
    delayed = float(state.command_history[0])
    history = (*state.command_history[1:], command_f)

  try:
    curvature_next = (
      float(config.curvature_intercept_1pm)
      + float(config.curvature_ar) * float(state.curvature_1pm)
      + float(config.command_gain_1pm) * delayed
      + float(config.command_speed_gain_s_per_m2) * delayed * speed
      + float(config.command_inv_speed_gain_per_s) * delayed / speed
      + float(config.roll_gain_1pm_per_rad) * roll
    )
    current_target = -float(state.curvature_1pm) * speed
    next_target = -curvature_next * speed
    yaw_next = (
      next_target
      + float(config.yaw_ar) * (float(state.yaw_rate_rad_s) - current_target)
      + float(config.yaw_bias_rad_s)
    )
  except (ArithmeticError, OverflowError, ValueError):
    return _blocked('DERIVED_VALUE_INVALID')

  if not all(math.isfinite(value) for value in (delayed, curvature_next, current_target, next_target, yaw_next)):
    return _blocked('DERIVED_VALUE_INVALID')

  next_state = CurvatureYawPlantState(
    curvature_1pm=float(curvature_next),
    yaw_rate_rad_s=float(yaw_next),
    command_history=tuple(float(value) for value in history),
  )
  return CurvatureYawPlantObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    delayed_command=float(delayed),
    current_yaw_target_rad_s=float(current_target),
    next_yaw_target_rad_s=float(next_target),
    next_state=next_state,
  )
