"""Fail-closed speed-aware tune evaluation for offline replay and simulation.

The caller supplies a frozen, evidence-backed table. This module contains no
default speed bins, learner, cache, Params write, or controller integration.
"""
from bisect import bisect_right
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SpeedTunePoint:
  speed_mps: float
  lat_accel_factor: float
  friction: float
  steering_response: float

  def __post_init__(self):
    values = (self.speed_mps, self.lat_accel_factor, self.friction, self.steering_response)
    if not all(type(value) in (int, float) and math.isfinite(value) for value in values):
      raise ValueError('Speed tune values must be finite numbers')
    if self.speed_mps < 0 or self.lat_accel_factor <= 0 or self.friction < 0 or self.steering_response <= 0:
      raise ValueError('Speed tune values are outside their physical domain')


@dataclass(frozen=True)
class SpeedAwareTuneTable:
  points: tuple[SpeedTunePoint, ...]
  provenance: str

  def __post_init__(self):
    if not isinstance(self.points, tuple) or len(self.points) < 2:
      raise ValueError('At least two immutable speed tune points are required')
    if not all(isinstance(point, SpeedTunePoint) for point in self.points):
      raise ValueError('Every speed tune point must be a SpeedTunePoint')
    if any(current.speed_mps <= previous.speed_mps
           for previous, current in zip(self.points, self.points[1:], strict=False)):
      raise ValueError('Speed tune points must be strictly increasing')
    if not isinstance(self.provenance, str) or not self.provenance.strip():
      raise ValueError('Speed tune provenance is required')


@dataclass(frozen=True)
class SpeedAwareTuneResult:
  valid: bool
  reason: str
  speed_mps: float
  lat_accel_factor: float
  friction: float
  steering_response: float
  lower_speed_mps: float | None
  upper_speed_mps: float | None
  provenance: str


def _finite_baseline(lat_accel_factor: float, friction: float, steering_response: float) -> bool:
  values = (lat_accel_factor, friction, steering_response)
  return (all(type(value) in (int, float) and math.isfinite(value) for value in values) and
          lat_accel_factor > 0 and friction >= 0 and steering_response > 0)


def evaluate_speed_aware_tune(table: SpeedAwareTuneTable, speed_mps: float,
                              baseline_lat_accel_factor: float, baseline_friction: float,
                              baseline_steering_response: float) -> SpeedAwareTuneResult:
  if not isinstance(table, SpeedAwareTuneTable):
    raise ValueError('table must be a SpeedAwareTuneTable')
  if not _finite_baseline(baseline_lat_accel_factor, baseline_friction, baseline_steering_response):
    raise ValueError('Baseline tune must be finite and physically valid')

  fallback = (baseline_lat_accel_factor, baseline_friction, baseline_steering_response)
  if type(speed_mps) not in (int, float) or not math.isfinite(speed_mps) or speed_mps < 0:
    raise ValueError('Speed must be a finite nonnegative number')
  if speed_mps < table.points[0].speed_mps or speed_mps > table.points[-1].speed_mps:
    return SpeedAwareTuneResult(
      False, 'outside_qualified_speed_domain', float(speed_mps), *fallback, None, None, table.provenance,
    )

  speeds = tuple(point.speed_mps for point in table.points)
  right = bisect_right(speeds, speed_mps)
  if right == len(table.points):
    left = right - 1
    point = table.points[left]
    return SpeedAwareTuneResult(
      True, 'ok', float(speed_mps), point.lat_accel_factor, point.friction,
      point.steering_response, point.speed_mps, point.speed_mps, table.provenance,
    )
  left = max(0, right - 1)
  lower = table.points[left]
  upper = table.points[right]
  fraction = (speed_mps - lower.speed_mps) / (upper.speed_mps - lower.speed_mps)

  def interpolate(lower_value: float, upper_value: float) -> float:
    return float(lower_value + fraction * (upper_value - lower_value))

  return SpeedAwareTuneResult(
    True, 'ok', float(speed_mps),
    interpolate(lower.lat_accel_factor, upper.lat_accel_factor),
    interpolate(lower.friction, upper.friction),
    interpolate(lower.steering_response, upper.steering_response),
    lower.speed_mps, upper.speed_mps, table.provenance,
  )
