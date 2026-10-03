"""Offline raw-to-normalized steering command-domain translation.

This module has no actuator, cereal, Params, CAN, or controller callback path.
It exists to prevent recorded commands from one STEER_MAX contract from being
silently interpreted under another contract during offline experiments.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class OfflineTorqueCommandContract:
  steer_max: int
  delta_up_raw: int
  delta_down_raw: int
  control_dt_s: float
  provenance: str

  def __post_init__(self):
    integer_values = (self.steer_max, self.delta_up_raw, self.delta_down_raw)
    if not all(type(value) is int and value > 0 for value in integer_values):
      raise ValueError('Raw torque command limits must be positive integers')
    if type(self.control_dt_s) not in (int, float) or not math.isfinite(self.control_dt_s) or self.control_dt_s <= 0:
      raise ValueError('Control timestep must be a finite positive number')
    if not isinstance(self.provenance, str) or not self.provenance.strip():
      raise ValueError('Command contract requires nonempty provenance')

  @property
  def max_magnitude_increase_per_s(self) -> float:
    return self.delta_up_raw / self.steer_max / self.control_dt_s

  @property
  def max_magnitude_decrease_per_s(self) -> float:
    return self.delta_down_raw / self.steer_max / self.control_dt_s


@dataclass(frozen=True)
class OfflineTorqueCommandTranslation:
  raw_command: int
  source_normalized: float
  target_normalized: float
  rescaled: bool
  source_provenance: str
  target_provenance: str
  execution_stage: str = 'offline_only'
  live_actuator_authority: bool = False


def translate_raw_applied_command(raw_command: int,
                                  source: OfflineTorqueCommandContract,
                                  target: OfflineTorqueCommandContract) -> OfflineTorqueCommandTranslation:
  if type(raw_command) is not int:
    raise ValueError('Raw applied command must be an integer')
  if not isinstance(source, OfflineTorqueCommandContract) or not isinstance(target, OfflineTorqueCommandContract):
    raise ValueError('Source and target must be offline torque command contracts')
  if abs(raw_command) > source.steer_max or abs(raw_command) > target.steer_max:
    raise ValueError('Raw applied command exceeds a source or target controller limit')

  source_normalized = raw_command / source.steer_max
  target_normalized = raw_command / target.steer_max
  return OfflineTorqueCommandTranslation(
    raw_command=raw_command,
    source_normalized=float(source_normalized),
    target_normalized=float(target_normalized),
    rescaled=source.steer_max != target.steer_max,
    source_provenance=source.provenance,
    target_provenance=target.provenance,
  )
