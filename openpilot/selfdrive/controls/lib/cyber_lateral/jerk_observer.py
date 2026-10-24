"""Sunny-inspired future lateral-jerk persistence observation.

This pure observer returns no friction, torque or controller command.
"""
from bisect import bisect_right
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FutureLateralProfile:
  time_s: tuple[float, ...]
  lateral_accel_mps2: tuple[float, ...]

  def __post_init__(self):
    if not isinstance(self.time_s, tuple) or not isinstance(self.lateral_accel_mps2, tuple):
      raise ValueError('Future profile storage must be immutable tuples')
    if not self.time_s or len(self.time_s) != len(self.lateral_accel_mps2):
      raise ValueError('Future profile axes must be nonempty and equal length')
    if not all(type(value) in (int, float) and math.isfinite(value)
               for value in (*self.time_s, *self.lateral_accel_mps2)):
      raise ValueError('Future profile values must be finite numbers')
    if self.time_s[0] != 0:
      raise ValueError('Future profile must begin at zero seconds')
    if any(current <= previous for previous, current in zip(self.time_s, self.time_s[1:], strict=False)):
      raise ValueError('Future profile time must be strictly increasing')


@dataclass(frozen=True)
class JerkPersistenceObservation:
  valid: bool
  reason: str
  query_times_s: tuple[float, ...]
  jerk_mps3: tuple[float, ...]
  sign_consistent: bool
  minimum_abs_jerk_mps3: float | None


def _invalid(reason: str, query_times_s: tuple[float, ...] = (),
             jerk_mps3: tuple[float, ...] = (), sign_consistent: bool = False):
  return JerkPersistenceObservation(False, reason, query_times_s, jerk_mps3, sign_consistent, None)


def _interpolate(profile: FutureLateralProfile, query: float) -> float:
  index = bisect_right(profile.time_s, query)
  if index == 0:
    return float(profile.lateral_accel_mps2[0])
  if index == len(profile.time_s):
    return float(profile.lateral_accel_mps2[-1])
  left = index - 1
  if profile.time_s[left] == query:
    return float(profile.lateral_accel_mps2[left])
  fraction = (query - profile.time_s[left]) / (profile.time_s[index] - profile.time_s[left])
  return float(
    profile.lateral_accel_mps2[left] +
    fraction * (profile.lateral_accel_mps2[index] - profile.lateral_accel_mps2[left])
  )


def observe_jerk_persistence(profile: FutureLateralProfile,
                             query_times_s: tuple[float, ...]) -> JerkPersistenceObservation:
  if not isinstance(profile, FutureLateralProfile):
    raise ValueError('profile must be a FutureLateralProfile')
  if len(profile.time_s) < 2:
    return _invalid('insufficient_profile')
  if (not isinstance(query_times_s, tuple) or
      not all(type(value) in (int, float) and math.isfinite(value) for value in query_times_s) or
      any(current <= previous for previous, current in zip(query_times_s, query_times_s[1:], strict=False))):
    return _invalid('invalid_queries')
  if len(query_times_s) < 2:
    return _invalid('insufficient_queries', query_times_s)
  if query_times_s[0] < profile.time_s[0] or query_times_s[-1] > profile.time_s[-1]:
    return _invalid('query_outside_profile', query_times_s)

  acceleration = tuple(_interpolate(profile, query) for query in query_times_s)
  jerk = tuple(
    (current_accel - previous_accel) / (current_time - previous_time)
    for previous_time, current_time, previous_accel, current_accel in zip(
      query_times_s[:-1], query_times_s[1:], acceleration[:-1], acceleration[1:], strict=True,
    )
  )
  nonzero_signs = {1 if value > 0 else -1 for value in jerk if value != 0}
  sign_consistent = len(nonzero_signs) <= 1
  if not sign_consistent:
    return _invalid('mixed_sign_jerk', query_times_s, jerk, False)
  return JerkPersistenceObservation(
    True, 'ok', query_times_s, jerk, True, float(min(abs(value) for value in jerk)),
  )
