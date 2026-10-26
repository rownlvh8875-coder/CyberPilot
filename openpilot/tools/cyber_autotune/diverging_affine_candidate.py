"""Offline-only affine candidates for turn-inside diverging model-path geometry.

This module transforms caller-owned PathQualityInput geometry for descriptive
comparison only. It has no planner/control integration and never returns a
curvature request, tune, profile, Params value, CAN message, or vehicle command.
"""

from dataclasses import dataclass
import math

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import (
  PathQualityInput,
  observe_path_quality,
)


@dataclass(frozen=True)
class DivergingAffineCandidate:
  status: str
  reason: str
  mode: str | None
  sample_count: int
  station_m: tuple[float, ...] | None
  original_path_y_m: tuple[float, ...] | None
  candidate_path_y_m: tuple[float, ...] | None
  correction_y_m: tuple[float, ...] | None
  action_horizon_station_m: float | None
  requested_curvature_1pm: float | None
  turn_relative_offset_m: float | None
  turn_relative_offset_slope_per_m: float | None
  original_offset_slope_per_m: float | None
  target_offset_slope_per_m: float | None
  candidate_offset_slope_per_m: float | None
  delta_slope_per_m: float | None
  correction_at_action_horizon_m: float | None
  correction_at_first_station_m: float | None
  correction_max_abs_m: float | None
  candidate_within_lane_envelope: bool | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> DivergingAffineCandidate:
  return DivergingAffineCandidate(
    status='BLOCKED',
    reason=reason,
    mode=None,
    sample_count=0,
    station_m=None,
    original_path_y_m=None,
    candidate_path_y_m=None,
    correction_y_m=None,
    action_horizon_station_m=None,
    requested_curvature_1pm=None,
    turn_relative_offset_m=None,
    turn_relative_offset_slope_per_m=None,
    original_offset_slope_per_m=None,
    target_offset_slope_per_m=None,
    candidate_offset_slope_per_m=None,
    delta_slope_per_m=None,
    correction_at_action_horizon_m=None,
    correction_at_first_station_m=None,
    correction_max_abs_m=None,
    candidate_within_lane_envelope=None,
  )


def _finite_number(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _interp(x: tuple[float, ...], y: tuple[float, ...], query: float) -> float | None:
  if len(x) != len(y) or not x or query < x[0] or query > x[-1]:
    return None
  if query == x[-1]:
    return float(y[-1])
  for i, (left, right) in enumerate(zip(x, x[1:], strict=False)):
    if left <= query <= right:
      width = right - left
      if width <= 0.0 or not math.isfinite(width):
        return None
      fraction = (query - left) / width
      value = y[i] + fraction * (y[i + 1] - y[i])
      return float(value) if math.isfinite(value) else None
  return None


def _local_offset_slope(
  data: PathQualityInput,
  path_y_m: tuple[float, ...],
  action_horizon_station_m: float,
) -> tuple[float, float] | None:
  center = tuple(
    float(left / 2.0 + right / 2.0)
    for left, right in zip(data.left_lane_y_m, data.right_lane_y_m, strict=True)
  )
  station = tuple(float(value) for value in data.station_m)
  if len(station) < 3 or len(path_y_m) != len(station):
    return None

  interior_station = station[1:-1]
  if not interior_station or not (interior_station[0] <= action_horizon_station_m <= interior_station[-1]):
    return None

  path_slopes = tuple(
    float((path_y_m[i + 1] - path_y_m[i - 1]) / (station[i + 1] - station[i - 1]))
    for i in range(1, len(station) - 1)
  )
  center_slopes = tuple(
    float((center[i + 1] - center[i - 1]) / (station[i + 1] - station[i - 1]))
    for i in range(1, len(station) - 1)
  )
  if not all(math.isfinite(value) for value in (*path_slopes, *center_slopes)):
    return None

  path_y = _interp(station, path_y_m, action_horizon_station_m)
  center_y = _interp(station, center, action_horizon_station_m)
  path_slope = _interp(interior_station, path_slopes, action_horizon_station_m)
  center_slope = _interp(interior_station, center_slopes, action_horizon_station_m)
  if None in (path_y, center_y, path_slope, center_slope):
    return None

  offset = float(path_y - center_y)
  slope = float(path_slope - center_slope)
  if not math.isfinite(offset) or not math.isfinite(slope):
    return None
  return offset, slope


def build_diverging_affine_candidate(
  data: PathQualityInput,
  *,
  action_horizon_station_m: float,
  requested_curvature_1pm: float,
  mode: str,
) -> DivergingAffineCandidate:
  """Build one bounded descriptive affine candidate.

  Current branch/model geometry uses +right lateral coordinates. Requested
  curvature sign is therefore used only to normalize whether the current path
  offset is toward the requested turn.

  FLAT sets the local path-minus-lane slope to zero.
  MIRROR sets it to the same magnitude with the opposite sign.

  Both candidates are anchored so the path value at action_horizon_station_m is
  unchanged. No threshold, gain search, temporal filter, promotion rule, or
  vehicle authority is introduced.
  """
  if not isinstance(data, PathQualityInput):
    raise ValueError('data must be a PathQualityInput')
  if mode not in ('FLAT', 'MIRROR'):
    return _blocked('UNSUPPORTED_MODE')
  if not _finite_number(requested_curvature_1pm) or requested_curvature_1pm == 0.0:
    return _blocked('TURN_UNRESOLVED')
  if not _finite_number(action_horizon_station_m):
    return _blocked('INVALID_ACTION_HORIZON')

  observation = observe_path_quality(data)
  if not observation.valid:
    return _blocked(observation.reason)

  station = tuple(float(value) for value in data.station_m)
  original = tuple(float(value) for value in data.desired_path_y_m)
  if len(station) < 3 or not (station[1] <= action_horizon_station_m <= station[-2]):
    return _blocked('INVALID_ACTION_HORIZON')

  original_geometry = _local_offset_slope(data, original, float(action_horizon_station_m))
  if original_geometry is None:
    return _blocked('DERIVED_GEOMETRY_INVALID')
  offset, slope = original_geometry

  turn = 1 if requested_curvature_1pm > 0.0 else -1
  turn_relative_offset = offset * turn
  turn_relative_slope = slope * turn
  if not all(math.isfinite(value) for value in (turn_relative_offset, turn_relative_slope)):
    return _blocked('DERIVED_GEOMETRY_INVALID')
  if turn_relative_offset <= 0.0:
    return _blocked('PATH_NOT_TURN_INSIDE')
  if offset * slope <= 0.0:
    return _blocked('PATH_NOT_DIVERGING')

  target_slope = 0.0 if mode == 'FLAT' else -slope
  delta_slope = target_slope - slope
  try:
    correction = tuple(
      float(delta_slope * (x - action_horizon_station_m))
      for x in station
    )
    candidate = tuple(
      float(y + correction_value)
      for y, correction_value in zip(original, correction, strict=True)
    )
  except (ArithmeticError, OverflowError, ValueError):
    return _blocked('DERIVED_GEOMETRY_INVALID')

  if not all(math.isfinite(value) for value in (*correction, *candidate, target_slope, delta_slope)):
    return _blocked('DERIVED_GEOMETRY_INVALID')

  candidate_within_lanes = all(
    min(left, right) <= candidate_y <= max(left, right)
    for candidate_y, left, right in zip(
      candidate, data.left_lane_y_m, data.right_lane_y_m, strict=True,
    )
  )
  if not candidate_within_lanes:
    return _blocked('CANDIDATE_OUTSIDE_LANES')

  candidate_geometry = _local_offset_slope(data, candidate, float(action_horizon_station_m))
  if candidate_geometry is None:
    return _blocked('DERIVED_GEOMETRY_INVALID')
  candidate_offset, candidate_slope = candidate_geometry

  correction_at_horizon = _interp(station, correction, float(action_horizon_station_m))
  if correction_at_horizon is None:
    return _blocked('DERIVED_GEOMETRY_INVALID')
  correction_max = max(abs(value) for value in correction)
  if not all(math.isfinite(value) for value in (candidate_offset, candidate_slope, correction_at_horizon, correction_max)):
    return _blocked('DERIVED_GEOMETRY_INVALID')

  return DivergingAffineCandidate(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    mode=mode,
    sample_count=len(station),
    station_m=station,
    original_path_y_m=original,
    candidate_path_y_m=candidate,
    correction_y_m=correction,
    action_horizon_station_m=float(action_horizon_station_m),
    requested_curvature_1pm=float(requested_curvature_1pm),
    turn_relative_offset_m=float(turn_relative_offset),
    turn_relative_offset_slope_per_m=float(turn_relative_slope),
    original_offset_slope_per_m=float(slope),
    target_offset_slope_per_m=float(target_slope),
    candidate_offset_slope_per_m=float(candidate_slope),
    delta_slope_per_m=float(delta_slope),
    correction_at_action_horizon_m=float(correction_at_horizon),
    correction_at_first_station_m=float(correction[0]),
    correction_max_abs_m=float(correction_max),
    candidate_within_lane_envelope=True,
  )
