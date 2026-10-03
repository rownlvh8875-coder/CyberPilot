"""Offline-only STEP 7 experiment matrix.

These flags describe replay and simulator candidates. They intentionally have
no runtime Params binding and cannot grant live actuator authority.
"""
from dataclasses import dataclass
from enum import StrEnum


class LateralExperimentVariant(StrEnum):
  A0 = 'A0'
  A1 = 'A1'
  A2 = 'A2'
  A3 = 'A3'
  A4 = 'A4'
  A5 = 'A5'


@dataclass(frozen=True)
class OfflineLateralFeatures:
  speed_aware_tune: bool = False
  torque_authority_envelope: bool = False
  steering_rate_control: bool = False
  execution_stage: str = 'offline_only'
  live_actuator_authority: bool = False

  def __post_init__(self):
    flags = (self.speed_aware_tune, self.torque_authority_envelope,
             self.steering_rate_control, self.live_actuator_authority)
    if any(type(value) is not bool for value in flags):
      raise ValueError('Experiment flags must be booleans')
    if self.execution_stage != 'offline_only' or self.live_actuator_authority:
      raise ValueError('STEP 7 candidates are offline-only and non-actuating')


_VARIANTS = {
  LateralExperimentVariant.A0: OfflineLateralFeatures(),
  LateralExperimentVariant.A1: OfflineLateralFeatures(speed_aware_tune=True),
  LateralExperimentVariant.A2: OfflineLateralFeatures(torque_authority_envelope=True),
  LateralExperimentVariant.A3: OfflineLateralFeatures(steering_rate_control=True),
  LateralExperimentVariant.A4: OfflineLateralFeatures(
    speed_aware_tune=True, torque_authority_envelope=True,
  ),
  LateralExperimentVariant.A5: OfflineLateralFeatures(
    speed_aware_tune=True, torque_authority_envelope=True, steering_rate_control=True,
  ),
}


def features_for_variant(variant: LateralExperimentVariant) -> OfflineLateralFeatures:
  if not isinstance(variant, LateralExperimentVariant):
    raise ValueError('variant must be a LateralExperimentVariant')
  return _VARIANTS[variant]
