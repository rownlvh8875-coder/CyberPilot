"""Offline-only orchestration for STEP 7 lateral A0-A5 experiments.

The orchestrator accepts already-computed baseline commands and returns
counterfactual candidates. It has no cereal, Params, CAN, controller callback,
or live actuator path. Speed-aware controller application remains blocked until
an evidence-bound native controller adapter is supplied in a later change.
"""
from dataclasses import dataclass
import math

from openpilot.selfdrive.controls.lib.cyber_lateral.experiments import (
  LateralExperimentVariant, OfflineLateralFeatures, features_for_variant,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.speed_aware_tune import (
  SpeedAwareTuneResult, SpeedAwareTuneTable, evaluate_speed_aware_tune,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.steering_rate import (
  SteeringRateLimits, SteeringRateObservation, evaluate_steering_rate_candidate,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.torque_authority import (
  TorqueAuthorityEnvelope, TorqueAuthorityObservation, observe_torque_authority,
)


@dataclass(frozen=True)
class OfflineOptimizerConfig:
  variant: LateralExperimentVariant
  speed_tune_table: SpeedAwareTuneTable | None = None
  authority_envelope: TorqueAuthorityEnvelope | None = None
  rate_limits: SteeringRateLimits | None = None
  baseline_max_magnitude_increase_per_s: float | None = None
  baseline_max_magnitude_decrease_per_s: float | None = None

  def __post_init__(self):
    if not isinstance(self.variant, LateralExperimentVariant):
      raise ValueError('variant must be a LateralExperimentVariant')
    features = features_for_variant(self.variant)
    if features.speed_aware_tune and not isinstance(self.speed_tune_table, SpeedAwareTuneTable):
      raise ValueError('Speed-aware variants require an immutable speed tune table')
    if not features.speed_aware_tune and self.speed_tune_table is not None:
      raise ValueError('Speed tune table supplied to a variant that does not use it')
    if features.torque_authority_envelope and not isinstance(self.authority_envelope, TorqueAuthorityEnvelope):
      raise ValueError('Authority-envelope variants require an immutable envelope')
    if not features.torque_authority_envelope and self.authority_envelope is not None:
      raise ValueError('Authority envelope supplied to a variant that does not use it')
    if features.steering_rate_control:
      if not isinstance(self.rate_limits, SteeringRateLimits):
        raise ValueError('Rate-control variants require immutable rate limits')
      rates = (
        self.baseline_max_magnitude_increase_per_s,
        self.baseline_max_magnitude_decrease_per_s,
      )
      if not all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in rates):
        raise ValueError('Rate-control variants require finite positive baseline rates')
    elif any(value is not None for value in (
      self.rate_limits,
      self.baseline_max_magnitude_increase_per_s,
      self.baseline_max_magnitude_decrease_per_s,
    )):
      raise ValueError('Rate configuration supplied to a variant that does not use it')


@dataclass(frozen=True)
class OptimizerStepInput:
  speed_mps: float
  baseline_command: float
  applied_command: float
  dt_s: float
  baseline_lat_accel_factor: float | None = None
  baseline_friction: float | None = None
  baseline_steering_response: float | None = None
  rate_limited: bool = False
  driver_limited: bool = False

  def __post_init__(self):
    numeric = (
      self.speed_mps, self.baseline_command, self.applied_command, self.dt_s,
    )
    if not all(type(value) in (int, float) and math.isfinite(value) for value in numeric):
      raise ValueError('Optimizer step inputs must be finite numbers')
    if self.speed_mps < 0 or self.dt_s <= 0:
      raise ValueError('Optimizer speed must be nonnegative and dt must be positive')
    tune = (self.baseline_lat_accel_factor, self.baseline_friction, self.baseline_steering_response)
    if any(value is not None and (type(value) not in (int, float) or not math.isfinite(value)) for value in tune):
      raise ValueError('Baseline tune values must be finite when supplied')
    if ((self.baseline_lat_accel_factor is not None and self.baseline_lat_accel_factor <= 0) or
        (self.baseline_friction is not None and self.baseline_friction < 0) or
        (self.baseline_steering_response is not None and self.baseline_steering_response <= 0)):
      raise ValueError('Baseline tune is outside its physical domain')
    if type(self.rate_limited) is not bool or type(self.driver_limited) is not bool:
      raise ValueError('Optimizer limit flags must be booleans')


@dataclass(frozen=True)
class OfflineOptimizerResult:
  variant: LateralExperimentVariant
  valid: bool
  reason: str
  baseline_command: float
  candidate_command: float
  features: OfflineLateralFeatures
  speed_tune: SpeedAwareTuneResult | None
  authority: TorqueAuthorityObservation | None
  rate: SteeringRateObservation | None
  execution_stage: str = 'offline_only'
  live_actuator_authority: bool = False


class CyberLateralOptimizer:
  def __init__(self, config: OfflineOptimizerConfig):
    if not isinstance(config, OfflineOptimizerConfig):
      raise ValueError('config must be an OfflineOptimizerConfig')
    self.config = config
    self.features = features_for_variant(config.variant)
    self.reset()

  def reset(self) -> None:
    self._previous_candidate: float | None = None

  def _result(self, data: OptimizerStepInput, *, valid: bool, reason: str,
              candidate: float, speed_tune: SpeedAwareTuneResult | None = None,
              authority: TorqueAuthorityObservation | None = None,
              rate: SteeringRateObservation | None = None) -> OfflineOptimizerResult:
    return OfflineOptimizerResult(
      self.config.variant, valid, reason, data.baseline_command, float(candidate),
      self.features, speed_tune, authority, rate,
    )

  def evaluate(self, data: OptimizerStepInput) -> OfflineOptimizerResult:
    if not isinstance(data, OptimizerStepInput):
      raise ValueError('data must be an OptimizerStepInput')
    if self.config.variant == LateralExperimentVariant.A0:
      return self._result(data, valid=True, reason='baseline', candidate=data.baseline_command)

    speed_tune = None
    if self.features.speed_aware_tune:
      assert self.config.speed_tune_table is not None
      tune = (data.baseline_lat_accel_factor, data.baseline_friction, data.baseline_steering_response)
      if any(value is None for value in tune):
        return self._result(
          data, valid=False, reason='baseline_tune_missing', candidate=data.baseline_command,
        )
      assert data.baseline_lat_accel_factor is not None
      assert data.baseline_friction is not None
      assert data.baseline_steering_response is not None
      speed_tune = evaluate_speed_aware_tune(
        self.config.speed_tune_table, data.speed_mps,
        data.baseline_lat_accel_factor, data.baseline_friction,
        data.baseline_steering_response,
      )
      if not speed_tune.valid:
        return self._result(
          data, valid=False, reason=f'speed_tune_{speed_tune.reason}',
          candidate=data.baseline_command, speed_tune=speed_tune,
        )
      return self._result(
        data, valid=False, reason='native_speed_tune_adapter_missing',
        candidate=data.baseline_command, speed_tune=speed_tune,
      )

    candidate = data.baseline_command
    rate = None
    if self.features.steering_rate_control:
      assert self.config.rate_limits is not None
      previous = data.applied_command if self._previous_candidate is None else self._previous_candidate
      rate = evaluate_steering_rate_candidate(
        candidate, previous, data.dt_s, self.config.rate_limits,
        baseline_max_magnitude_increase_per_s=self.config.baseline_max_magnitude_increase_per_s,
        baseline_max_magnitude_decrease_per_s=self.config.baseline_max_magnitude_decrease_per_s,
      )
      candidate = rate.candidate
      self._previous_candidate = candidate

    authority = None
    if self.features.torque_authority_envelope:
      assert self.config.authority_envelope is not None
      authority = observe_torque_authority(
        self.config.authority_envelope, data.speed_mps,
        requested=candidate, applied=data.applied_command,
        rate_limited=data.rate_limited, driver_limited=data.driver_limited,
      )
      candidate = authority.candidate
      if not authority.valid:
        return self._result(
          data, valid=False, reason=authority.reason, candidate=candidate,
          authority=authority, rate=rate,
        )

    return self._result(
      data, valid=True, reason='ok', candidate=candidate,
      authority=authority, rate=rate,
    )
