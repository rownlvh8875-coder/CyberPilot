"""Immutable Cyber Lateral observation contracts.

These records contain diagnostics only. They intentionally expose no cereal
actuator object, controller callback, Params handle, or parameter write path.
"""
from dataclasses import dataclass
from enum import StrEnum

from openpilot.selfdrive.controls.lib.cyber_lateral.jerk_observer import JerkPersistenceObservation
from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import PathQualityObservation
from openpilot.selfdrive.controls.lib.cyber_lateral.path_tracking import PathTrackingObservation


class CyberLateralMode(StrEnum):
  DISABLED = 'disabled'
  OBSERVE_ONLY = 'observe_only'


@dataclass(frozen=True)
class CyberLateralConfig:
  mode: CyberLateralMode = CyberLateralMode.DISABLED
  configuration_epoch: int = 0

  def __post_init__(self):
    if not isinstance(self.mode, CyberLateralMode):
      raise ValueError('Only disabled and observe-only modes are available')
    if type(self.configuration_epoch) is not int or self.configuration_epoch < 0:
      raise ValueError('Configuration epoch must be a nonnegative identity counter')


@dataclass(frozen=True)
class LateralBinding:
  vehicle: str | None = None
  firmware: str | None = None
  model: str | None = None
  controller_type: str | None = None
  configuration_epoch: int = 0

  @property
  def complete(self) -> bool:
    identities = (self.vehicle, self.firmware, self.model, self.controller_type)
    return (all(isinstance(value, str) and bool(value.strip()) for value in identities) and
            type(self.configuration_epoch) is int and self.configuration_epoch >= 0)


@dataclass(frozen=True)
class NativeLateralResult:
  steer: float
  lateral_output: float
  state_kind: str


@dataclass(frozen=True)
class LateralContext:
  model_mono_time_ns: int
  car_state_mono_time_ns: int
  vehicle_parameters_mono_time_ns: int
  lateral_delay_mono_time_ns: int
  input_valid: bool
  lat_active: bool
  steering_pressed: bool
  steer_limited_by_safety: bool
  curvature_limited: bool
  v_ego_mps: float
  desired_curvature_1pm: float
  current_curvature_1pm: float
  roll_rad: float
  lateral_delay_s: float
  native_result: NativeLateralResult
  binding: LateralBinding
  future_jerk_observation: JerkPersistenceObservation | None = None
  path_quality_observation: PathQualityObservation | None = None

  def __post_init__(self):
    if not isinstance(self.native_result, NativeLateralResult):
      raise ValueError('Native result must be an immutable NativeLateralResult')
    if not isinstance(self.binding, LateralBinding):
      raise ValueError('Binding must be an immutable LateralBinding')
    if (self.future_jerk_observation is not None and
        not isinstance(self.future_jerk_observation, JerkPersistenceObservation)):
      raise ValueError('Future jerk observation must be immutable diagnostic data')
    if (self.path_quality_observation is not None and
        not isinstance(self.path_quality_observation, PathQualityObservation)):
      raise ValueError('Path quality observation must be immutable diagnostic data')


@dataclass(frozen=True)
class LateralObservation:
  context: LateralContext
  mode: CyberLateralMode
  reason: str
  provenance_complete: bool
  path_tracking_observation: PathTrackingObservation | None = None
