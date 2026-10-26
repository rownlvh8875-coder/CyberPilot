"""Offline-only observation of model-path recenter tendency.

This module compares already-observed model path offset from the model lane
center at two existing stations. It does not generate a path, curvature,
controller correction, tune, Params value, CAN message, or vehicle command.
"""
from dataclasses import dataclass
import math

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import (
  PathQualityInput,
  observe_path_quality,
)


@dataclass(frozen=True)
class RecenterIntentObservation:
  status: str
  reason: str
  sample_count: int
  start_station_m: float | None
  future_station_m: float | None
  start_offset_m: float | None
  future_offset_m: float | None
  start_abs_offset_m: float | None
  future_abs_offset_m: float | None
  abs_offset_delta_m: float | None
  retained_abs_offset_fraction: float | None
  same_side: bool | None
  recentered: bool | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> RecenterIntentObservation:
  return RecenterIntentObservation(
    status='BLOCKED',
    reason=reason,
    sample_count=0,
    start_station_m=None,
    future_station_m=None,
    start_offset_m=None,
    future_offset_m=None,
    start_abs_offset_m=None,
    future_abs_offset_m=None,
    abs_offset_delta_m=None,
    retained_abs_offset_fraction=None,
    same_side=None,
    recentered=None,
  )


def _finite_number(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def observe_recenter_intent(data: PathQualityInput, *, future_station_m: float) -> RecenterIntentObservation:
  """Describe whether absolute path-to-lane-center offset shrinks by a future station.

  The future station must be one of the caller-owned station samples. Exact
  station matching avoids hidden interpolation or search policy in this
  diagnostic. A smaller future absolute offset is reported as recentered; this
  is descriptive only and is not an acceptance or control criterion.
  """
  if not isinstance(data, PathQualityInput):
    raise ValueError('data must be a PathQualityInput')
  if not _finite_number(future_station_m):
    return _blocked('invalid_future_station')

  quality = observe_path_quality(data)
  if not quality.valid:
    return _blocked(quality.reason)
  quality_values = (
    quality.model_to_lane_center_bias_m,
    quality.lane_width_mean_m,
    quality.lane_width_std_m,
    quality.confidence,
  )
  if quality.minimum_edge_clearance_m is not None:
    quality_values += (quality.minimum_edge_clearance_m,)
  if not all(_finite_number(value) for value in quality_values):
    return _blocked('invalid_path_reference_derived')

  start_station = data.station_m[0]
  future_station = float(future_station_m)
  if future_station <= start_station:
    return _blocked('future_station_not_after_start')
  try:
    future_index = data.station_m.index(future_station)
  except ValueError:
    return _blocked('future_station_unavailable')

  start_center = (data.left_lane_y_m[0] + data.right_lane_y_m[0]) / 2.0
  future_center = (
    data.left_lane_y_m[future_index] + data.right_lane_y_m[future_index]
  ) / 2.0
  start_offset = float(data.desired_path_y_m[0] - start_center)
  future_offset = float(data.desired_path_y_m[future_index] - future_center)
  start_abs = abs(start_offset)
  future_abs = abs(future_offset)
  delta = float(future_abs - start_abs)
  ratio = None if start_abs == 0.0 else float(future_abs / start_abs)
  derived = (start_offset, future_offset, start_abs, future_abs, delta)
  if ratio is not None:
    derived += (ratio,)
  if not all(math.isfinite(value) for value in derived):
    return _blocked('derived_offset_invalid')

  return RecenterIntentObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    sample_count=quality.sample_count,
    start_station_m=float(start_station),
    future_station_m=future_station,
    start_offset_m=start_offset,
    future_offset_m=future_offset,
    start_abs_offset_m=float(start_abs),
    future_abs_offset_m=float(future_abs),
    abs_offset_delta_m=delta,
    retained_abs_offset_fraction=ratio,
    same_side=bool(start_offset * future_offset > 0.0),
    recentered=bool(future_abs < start_abs),
  )
