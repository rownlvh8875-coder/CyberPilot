"""Offline-only temporal persistence for position/orientation separation states.

The caller supplies timestamped PositionOrientationSeparationObservation values
and an explicit maximum inter-sample gap. This module only groups consecutive
identical descriptive states into immutable runs. It does not choose persistence
thresholds, rank candidates, tune parameters, or provide vehicle authority.
"""

from dataclasses import dataclass
import math

from openpilot.tools.cyber_autotune.position_orientation_separation import (
  PositionOrientationSeparationObservation,
)


@dataclass(frozen=True)
class PositionOrientationRun:
  combined_state: str
  geometry_state: str
  offset_side: str
  orientation_relation: str
  start_time_s: float
  end_time_s: float
  span_s: float
  sample_count: int


@dataclass(frozen=True)
class PositionOrientationPersistenceObservation:
  status: str
  reason: str
  sample_count: int
  run_count: int
  max_gap_s: float | None
  runs: tuple[PositionOrientationRun, ...]
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> PositionOrientationPersistenceObservation:
  return PositionOrientationPersistenceObservation(
    status='BLOCKED',
    reason=reason,
    sample_count=0,
    run_count=0,
    max_gap_s=None,
    runs=(),
  )


def _finite(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _valid_observation(obs: PositionOrientationSeparationObservation) -> bool:
  if not isinstance(obs, PositionOrientationSeparationObservation):
    return False
  if obs.status != 'DESCRIPTIVE_ONLY' or obs.reason != 'ok':
    return False
  if (
    obs.readiness != 'NOT_READY'
    or obs.vehicle_status != 'REAL_VEHICLE_UNVERIFIED'
    or obs.safety_status != 'VEHICLE_ACTIVATION_BLOCKED'
    or obs.vehicle_activation_allowed is not False
  ):
    return False
  if obs.turn_sign not in (-1, 1):
    return False
  if obs.geometry_state not in ('CONVERGING', 'DIVERGING', 'FLAT'):
    return False
  if obs.offset_side not in ('INSIDE', 'OUTSIDE'):
    return False

  required = (
    obs.lane_center_slope_per_m,
    obs.lane_center_yaw_rad,
    obs.model_orientation_yaw_rad,
    obs.orientation_minus_lane_yaw_rad,
    obs.turn_relative_orientation_minus_lane_yaw_rad,
  )
  if not all(_finite(value) for value in required):
    return False

  lane_slope = float(obs.lane_center_slope_per_m)
  lane_yaw = float(obs.lane_center_yaw_rad)
  model_yaw = float(obs.model_orientation_yaw_rad)
  residual = float(obs.orientation_minus_lane_yaw_rad)
  normalized = float(obs.turn_relative_orientation_minus_lane_yaw_rad)
  turn = int(obs.turn_sign)

  expected_lane_yaw = math.atan(lane_slope)
  expected_residual = model_yaw - expected_lane_yaw
  expected_normalized = expected_residual * turn
  if not math.isclose(lane_yaw, expected_lane_yaw, rel_tol=0.0, abs_tol=1e-12):
    return False
  if not math.isclose(residual, expected_residual, rel_tol=0.0, abs_tol=1e-12):
    return False
  if not math.isclose(normalized, expected_normalized, rel_tol=0.0, abs_tol=1e-12):
    return False

  expected_relation = (
    'MORE_TURN_THAN_LANE' if expected_normalized > 0.0
    else 'LESS_TURN_THAN_LANE' if expected_normalized < 0.0
    else 'LANE_TANGENT_MATCH'
  )
  if obs.orientation_relation != expected_relation:
    return False

  expected_combined = f'{obs.geometry_state}_{obs.offset_side}__{expected_relation}'
  return obs.combined_state == expected_combined


def observe_position_orientation_persistence(
  samples: tuple[tuple[float, PositionOrientationSeparationObservation], ...],
  *,
  max_gap_s: float,
) -> PositionOrientationPersistenceObservation:
  """Group consecutive identical descriptive states into temporal runs.

  max_gap_s is caller-owned. This function returns actual run spans and does not
  classify them as persistent/non-persistent or compare against any duration
  threshold.
  """
  if not _finite(max_gap_s) or max_gap_s <= 0.0:
    return _blocked('INVALID_MAX_GAP')
  if not samples:
    return _blocked('NO_SAMPLES')

  timestamps: list[float] = []
  observations: list[PositionOrientationSeparationObservation] = []
  for timestamp_s, observation in samples:
    if not _finite(timestamp_s):
      return _blocked('INVALID_TIMESTAMPS')
    if not _valid_observation(observation):
      return _blocked('POSITION_ORIENTATION_INVALID')
    timestamps.append(float(timestamp_s))
    observations.append(observation)

  if any(current <= previous for previous, current in zip(timestamps, timestamps[1:], strict=False)):
    return _blocked('INVALID_TIMESTAMPS')

  runs: list[PositionOrientationRun] = []
  run_start = 0
  for i in range(1, len(samples) + 1):
    split = i == len(samples)
    if not split:
      gap = timestamps[i] - timestamps[i - 1]
      split = gap > max_gap_s or observations[i].combined_state != observations[i - 1].combined_state
    if not split:
      continue

    first = observations[run_start]
    start_time = timestamps[run_start]
    end_time = timestamps[i - 1]
    span = end_time - start_time
    if not math.isfinite(span) or span < 0.0:
      return _blocked('DERIVED_VALUE_INVALID')
    runs.append(PositionOrientationRun(
      combined_state=str(first.combined_state),
      geometry_state=str(first.geometry_state),
      offset_side=str(first.offset_side),
      orientation_relation=str(first.orientation_relation),
      start_time_s=float(start_time),
      end_time_s=float(end_time),
      span_s=float(span),
      sample_count=i - run_start,
    ))
    run_start = i

  return PositionOrientationPersistenceObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    sample_count=len(samples),
    run_count=len(runs),
    max_gap_s=float(max_gap_s),
    runs=tuple(runs),
  )
