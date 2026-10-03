"""Offline steering-rate candidate with an upstream-authority ceiling."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SteeringRateLimits:
  max_magnitude_increase_per_s: float
  max_magnitude_decrease_per_s: float

  def __post_init__(self):
    values = (self.max_magnitude_increase_per_s, self.max_magnitude_decrease_per_s)
    if not all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in values):
      raise ValueError('Steering rate limits must be finite positive numbers')


@dataclass(frozen=True)
class SteeringRateObservation:
  requested: float
  previous_candidate: float
  candidate: float
  applied_rate_per_s: float
  response_error: float
  rate_limited: bool


def evaluate_steering_rate_candidate(requested: float, previous_candidate: float, dt: float,
                                     limits: SteeringRateLimits, *,
                                     baseline_max_magnitude_increase_per_s: float,
                                     baseline_max_magnitude_decrease_per_s: float) -> SteeringRateObservation:
  if not isinstance(limits, SteeringRateLimits):
    raise ValueError('limits must be SteeringRateLimits')
  numeric = (
    requested, previous_candidate, dt,
    baseline_max_magnitude_increase_per_s, baseline_max_magnitude_decrease_per_s,
  )
  if not all(type(value) in (int, float) and math.isfinite(value) for value in numeric) or dt <= 0:
    raise ValueError('Steering rate inputs must be finite and dt must be positive')
  if baseline_max_magnitude_increase_per_s <= 0 or baseline_max_magnitude_decrease_per_s <= 0:
    raise ValueError('Baseline steering rates must be positive')
  if (limits.max_magnitude_increase_per_s > baseline_max_magnitude_increase_per_s or
      limits.max_magnitude_decrease_per_s > baseline_max_magnitude_decrease_per_s):
    raise ValueError('Candidate steering rate cannot be faster than the existing controller')

  previous_abs = abs(previous_candidate)
  requested_abs = abs(requested)
  same_direction = requested == 0 or previous_candidate == 0 or requested * previous_candidate > 0
  if not same_direction:
    candidate_abs = max(0., previous_abs - limits.max_magnitude_decrease_per_s * dt)
    candidate = math.copysign(candidate_abs, previous_candidate) if candidate_abs else 0.
  elif requested_abs > previous_abs:
    candidate_abs = min(requested_abs, previous_abs + limits.max_magnitude_increase_per_s * dt)
    candidate = math.copysign(candidate_abs, requested)
  else:
    candidate_abs = max(requested_abs, previous_abs - limits.max_magnitude_decrease_per_s * dt)
    candidate = math.copysign(candidate_abs, requested if requested else previous_candidate)

  rate = (candidate - previous_candidate) / dt
  return SteeringRateObservation(
    float(requested), float(previous_candidate), float(candidate), float(rate),
    float(requested - candidate),
    not math.isclose(candidate, requested, rel_tol=0., abs_tol=1e-12),
  )
