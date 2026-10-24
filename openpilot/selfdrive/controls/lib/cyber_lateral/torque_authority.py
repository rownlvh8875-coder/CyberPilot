"""Non-actuating torque-authority envelope observation.

The envelope may only reduce a normalized request below the existing vehicle
limit. It does not alter CarController, opendbc, panda, or any actuator object.
"""
from bisect import bisect_right
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TorqueAuthorityPoint:
  speed_mps: float
  maximum_abs_command: float

  def __post_init__(self):
    if not all(type(value) in (int, float) and math.isfinite(value)
               for value in (self.speed_mps, self.maximum_abs_command)):
      raise ValueError('Torque envelope values must be finite numbers')
    if self.speed_mps < 0 or self.maximum_abs_command <= 0:
      raise ValueError('Torque envelope values must be positive in their physical domain')


@dataclass(frozen=True)
class TorqueAuthorityEnvelope:
  points: tuple[TorqueAuthorityPoint, ...]
  existing_vehicle_limit: float
  provenance: str

  def __post_init__(self):
    if not isinstance(self.points, tuple) or len(self.points) < 2:
      raise ValueError('At least two immutable torque envelope points are required')
    if not all(isinstance(point, TorqueAuthorityPoint) for point in self.points):
      raise ValueError('Every torque envelope point must be a TorqueAuthorityPoint')
    if any(current.speed_mps <= previous.speed_mps
           for previous, current in zip(self.points, self.points[1:], strict=False)):
      raise ValueError('Torque envelope speeds must be strictly increasing')
    if (type(self.existing_vehicle_limit) not in (int, float) or
        not math.isfinite(self.existing_vehicle_limit) or self.existing_vehicle_limit <= 0):
      raise ValueError('Existing vehicle limit must be a finite positive number')
    if any(point.maximum_abs_command > self.existing_vehicle_limit for point in self.points):
      raise ValueError('Torque envelope cannot exceed the existing vehicle limit')
    if not isinstance(self.provenance, str) or not self.provenance.strip():
      raise ValueError('Torque envelope provenance is required')


@dataclass(frozen=True)
class TorqueAuthorityObservation:
  valid: bool
  reason: str
  requested: float
  applied: float
  candidate: float
  envelope_limit: float
  authority_utilization: float
  envelope_limited: bool
  safety_rail_requested: bool
  applied_exceeds_envelope: bool
  rate_limited: bool
  driver_limited: bool
  unexplained_tracking_gap: bool


def _interpolate_limit(envelope: TorqueAuthorityEnvelope, speed_mps: float) -> float | None:
  if speed_mps < envelope.points[0].speed_mps or speed_mps > envelope.points[-1].speed_mps:
    return None
  speeds = tuple(point.speed_mps for point in envelope.points)
  right = bisect_right(speeds, speed_mps)
  if right == len(envelope.points):
    return float(envelope.points[-1].maximum_abs_command)
  left = max(0, right - 1)
  lower = envelope.points[left]
  upper = envelope.points[right]
  fraction = (speed_mps - lower.speed_mps) / (upper.speed_mps - lower.speed_mps)
  return float(lower.maximum_abs_command + fraction * (upper.maximum_abs_command - lower.maximum_abs_command))


def observe_torque_authority(envelope: TorqueAuthorityEnvelope, speed_mps: float,
                             requested: float, applied: float, *, rate_limited: bool = False,
                             driver_limited: bool = False) -> TorqueAuthorityObservation:
  if not isinstance(envelope, TorqueAuthorityEnvelope):
    raise ValueError('envelope must be a TorqueAuthorityEnvelope')
  numeric = (speed_mps, requested, applied)
  if not all(type(value) in (int, float) and math.isfinite(value) for value in numeric):
    raise ValueError('Torque observation values must be finite numbers')
  if speed_mps < 0 or type(rate_limited) is not bool or type(driver_limited) is not bool:
    raise ValueError('Torque observation flags or speed are invalid')

  qualified_limit = _interpolate_limit(envelope, speed_mps)
  valid = qualified_limit is not None
  reason = 'ok' if valid else 'outside_qualified_speed_domain'
  limit = envelope.existing_vehicle_limit if qualified_limit is None else qualified_limit
  candidate = float(max(-limit, min(limit, requested)))
  envelope_limited = not math.isclose(candidate, requested, rel_tol=0., abs_tol=1e-12)
  safety_rail_requested = abs(requested) >= envelope.existing_vehicle_limit
  applied_exceeds_envelope = abs(applied) > limit
  utilization = abs(applied) / limit
  explained = envelope_limited or safety_rail_requested or rate_limited or driver_limited
  unexplained = not explained and not math.isclose(applied, requested, rel_tol=0., abs_tol=1e-6)
  return TorqueAuthorityObservation(
    valid, reason, float(requested), float(applied), candidate, float(limit), float(utilization),
    envelope_limited, safety_rail_requested, applied_exceeds_envelope,
    rate_limited, driver_limited, unexplained,
  )
