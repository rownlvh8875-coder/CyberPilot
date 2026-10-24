"""Offline-only virtual lane-center recenter diagnostic.

This module never publishes a path, curvature request, tune, profile, Params
value, CAN message, or vehicle command. It transforms already-observed model
geometry into an immutable virtual candidate for descriptive comparison only.
"""
from dataclasses import dataclass
from fractions import Fraction
import math

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import (
  PathQualityInput,
  PathQualityObservation,
  observe_path_quality,
)


@dataclass(frozen=True)
class VirtualPathRecenterCandidate:
  status: str
  reason: str
  sample_count: int
  station_m: tuple[float, ...] | None
  original_path_y_m: tuple[float, ...] | None
  candidate_path_y_m: tuple[float, ...] | None
  correction_y_m: tuple[float, ...] | None
  correction_signed_mean_m: float | None
  correction_rmse_m: float | None
  correction_max_abs_m: float | None
  original_curvature_rmse_1pm: float | None
  candidate_curvature_rmse_1pm: float | None
  original_curvature_jump_max_abs_1pm: float | None
  candidate_curvature_jump_max_abs_1pm: float | None
  original_curvature_rate_max_abs_1pm2: float | None
  candidate_curvature_rate_max_abs_1pm2: float | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


@dataclass(frozen=True)
class VirtualMeanShiftCandidate:
  status: str
  reason: str
  sample_count: int
  station_m: tuple[float, ...] | None
  original_path_y_m: tuple[float, ...] | None
  candidate_path_y_m: tuple[float, ...] | None
  applied_shift_m: float | None
  residual_lane_center_bias_mean_m: float | None
  residual_lane_center_bias_rmse_m: float | None
  residual_lane_center_bias_max_abs_m: float | None
  original_curvature_rmse_1pm: float | None
  candidate_curvature_rmse_1pm: float | None
  original_curvature_jump_max_abs_1pm: float | None
  candidate_curvature_jump_max_abs_1pm: float | None
  original_curvature_rate_max_abs_1pm2: float | None
  candidate_curvature_rate_max_abs_1pm2: float | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


@dataclass(frozen=True)
class VirtualMeanShiftTransition:
  status: str
  reason: str
  previous_sample_count: int
  current_sample_count: int
  common_sample_count: int
  sample_count_changed: bool
  station_axis_changed: bool
  previous_horizon_m: float | None
  current_horizon_m: float | None
  horizon_delta_m: float | None
  previous_shift_m: float | None
  current_shift_m: float | None
  shift_delta_m: float | None
  lane_center_component_m: float | None
  path_component_m: float | None
  common_lane_center_component_m: float | None
  common_path_component_m: float | None
  horizon_component_m: float | None
  left_lane_component_m: float | None
  right_lane_component_m: float | None
  common_left_lane_component_m: float | None
  common_right_lane_component_m: float | None
  lane_width_mean_delta_m: float | None
  lane_boundaries_same_direction: bool | None
  previous_confidence: float | None
  current_confidence: float | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> VirtualPathRecenterCandidate:
  return VirtualPathRecenterCandidate(
    status='BLOCKED',
    reason=reason,
    sample_count=0,
    station_m=None,
    original_path_y_m=None,
    candidate_path_y_m=None,
    correction_y_m=None,
    correction_signed_mean_m=None,
    correction_rmse_m=None,
    correction_max_abs_m=None,
    original_curvature_rmse_1pm=None,
    candidate_curvature_rmse_1pm=None,
    original_curvature_jump_max_abs_1pm=None,
    candidate_curvature_jump_max_abs_1pm=None,
    original_curvature_rate_max_abs_1pm2=None,
    candidate_curvature_rate_max_abs_1pm2=None,
  )


def _blocked_mean_shift(reason: str) -> VirtualMeanShiftCandidate:
  return VirtualMeanShiftCandidate(
    status='BLOCKED',
    reason=reason,
    sample_count=0,
    station_m=None,
    original_path_y_m=None,
    candidate_path_y_m=None,
    applied_shift_m=None,
    residual_lane_center_bias_mean_m=None,
    residual_lane_center_bias_rmse_m=None,
    residual_lane_center_bias_max_abs_m=None,
    original_curvature_rmse_1pm=None,
    candidate_curvature_rmse_1pm=None,
    original_curvature_jump_max_abs_1pm=None,
    candidate_curvature_jump_max_abs_1pm=None,
    original_curvature_rate_max_abs_1pm2=None,
    candidate_curvature_rate_max_abs_1pm2=None,
  )


def _blocked_transition(reason: str, previous_count: int = 0,
                        current_count: int = 0, common_count: int = 0,
                        station_axis_changed: bool = False) -> VirtualMeanShiftTransition:
  return VirtualMeanShiftTransition(
    status='BLOCKED',
    reason=reason,
    previous_sample_count=previous_count,
    current_sample_count=current_count,
    common_sample_count=common_count,
    sample_count_changed=previous_count != current_count,
    station_axis_changed=station_axis_changed,
    previous_horizon_m=None,
    current_horizon_m=None,
    horizon_delta_m=None,
    previous_shift_m=None,
    current_shift_m=None,
    shift_delta_m=None,
    lane_center_component_m=None,
    path_component_m=None,
    common_lane_center_component_m=None,
    common_path_component_m=None,
    horizon_component_m=None,
    left_lane_component_m=None,
    right_lane_component_m=None,
    common_left_lane_component_m=None,
    common_right_lane_component_m=None,
    lane_width_mean_delta_m=None,
    lane_boundaries_same_direction=None,
    previous_confidence=None,
    current_confidence=None,
  )


def _finite_number(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _observation_is_finite(observation: PathQualityObservation) -> bool:
  values = (
    observation.model_to_lane_center_bias_m,
    observation.lane_width_mean_m,
    observation.lane_width_std_m,
    observation.confidence,
  )
  if observation.minimum_edge_clearance_m is not None:
    values += (observation.minimum_edge_clearance_m,)
  return all(value is not None and _finite_number(value) for value in values)


def _stable_mean(values: tuple[float, ...]) -> float:
  if not values:
    raise ValueError('empty series')
  exact = sum((Fraction.from_float(value) for value in values), Fraction())
  result = float(exact / len(values))
  if not math.isfinite(result):
    raise ValueError('nonfinite mean')
  return result


def _stable_rmse(values: tuple[float, ...]) -> float:
  if not values:
    raise ValueError('empty series')
  scale = max(abs(value) for value in values)
  if not math.isfinite(scale):
    raise ValueError('nonfinite scale')
  if scale == 0.0:
    return 0.0
  normalized = math.fsum((value / scale) ** 2 for value in values) / len(values)
  result = scale * math.sqrt(normalized)
  if not math.isfinite(result):
    raise ValueError('nonfinite rmse')
  return float(result)


def _polyline_curvatures(station_m: tuple[float, ...], y_m: tuple[float, ...]) -> tuple[float, ...]:
  """Return signed three-point geometric curvature for each interior sample."""
  if len(station_m) != len(y_m) or len(station_m) < 3:
    raise ValueError('invalid polyline shape')

  result = []
  for i in range(1, len(station_m) - 1):
    dx1 = station_m[i] - station_m[i - 1]
    dy1 = y_m[i] - y_m[i - 1]
    dx2 = station_m[i + 1] - station_m[i]
    dy2 = y_m[i + 1] - y_m[i]
    if not all(math.isfinite(value) for value in (dx1, dy1, dx2, dy2)):
      raise ValueError('nonfinite polyline delta')

    scale = max(abs(dx1), abs(dy1), abs(dx2), abs(dy2))
    if scale == 0.0 or not math.isfinite(scale):
      raise ValueError('degenerate polyline scale')

    x1, y1 = dx1 / scale, dy1 / scale
    x2, y2 = dx2 / scale, dy2 / scale
    a = math.hypot(x1, y1)
    b = math.hypot(x2, y2)
    c = math.hypot(x1 + x2, y1 + y2)
    denom = a * b * c * scale
    if denom <= 0.0 or not math.isfinite(denom):
      raise ValueError('degenerate polyline geometry')

    cross = x1 * y2 - y1 * x2
    curvature = 2.0 * cross / denom
    if not math.isfinite(curvature):
      raise ValueError('nonfinite curvature')
    result.append(float(curvature))
  return tuple(result)


def _curvature_metrics(station_m: tuple[float, ...], y_m: tuple[float, ...]) -> tuple[float, float, float]:
  curvature = _polyline_curvatures(station_m, y_m)
  rmse = _stable_rmse(curvature)
  if len(curvature) < 2:
    return rmse, 0.0, 0.0

  jumps = tuple(current - previous for previous, current in zip(curvature, curvature[1:], strict=False))
  if not all(math.isfinite(value) for value in jumps):
    raise ValueError('nonfinite curvature jump')

  middle_station_m = station_m[1:-1]
  distances = tuple(
    current - previous
    for previous, current in zip(middle_station_m, middle_station_m[1:], strict=False)
  )
  if len(distances) != len(jumps) or not all(math.isfinite(value) and value > 0.0 for value in distances):
    raise ValueError('invalid curvature sample spacing')
  rates = tuple(jump / distance for jump, distance in zip(jumps, distances, strict=True))
  if not all(math.isfinite(value) for value in rates):
    raise ValueError('nonfinite curvature rate')

  return rmse, float(max(abs(value) for value in jumps)), float(max(abs(value) for value in rates))


def build_virtual_lane_center_candidate(data: PathQualityInput) -> VirtualPathRecenterCandidate:
  """Build a model-relative virtual lane-center candidate with no vehicle authority."""
  if not isinstance(data, PathQualityInput):
    raise ValueError('data must be a PathQualityInput')

  observation = observe_path_quality(data)
  if not observation.valid:
    return _blocked(observation.reason)
  if not _observation_is_finite(observation):
    return _blocked('derived_geometry_invalid')

  try:
    center = tuple(
      float(left / 2.0 + right / 2.0)
      for left, right in zip(data.left_lane_y_m, data.right_lane_y_m, strict=True)
    )
    correction = tuple(
      float(candidate - original)
      for candidate, original in zip(center, data.desired_path_y_m, strict=True)
    )
    if not all(math.isfinite(value) for value in (*center, *correction)):
      raise ValueError('nonfinite recenter geometry')

    correction_mean = _stable_mean(correction)
    correction_rmse = _stable_rmse(correction)
    correction_max = float(max(abs(value) for value in correction))
    original_curvature_rmse, original_jump, original_rate = _curvature_metrics(data.station_m, data.desired_path_y_m)
    candidate_curvature_rmse, candidate_jump, candidate_rate = _curvature_metrics(data.station_m, center)
  except (ArithmeticError, OverflowError, ValueError):
    return _blocked('derived_geometry_invalid')

  return VirtualPathRecenterCandidate(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    sample_count=len(data.station_m),
    station_m=tuple(float(value) for value in data.station_m),
    original_path_y_m=tuple(float(value) for value in data.desired_path_y_m),
    candidate_path_y_m=center,
    correction_y_m=correction,
    correction_signed_mean_m=correction_mean,
    correction_rmse_m=correction_rmse,
    correction_max_abs_m=correction_max,
    original_curvature_rmse_1pm=original_curvature_rmse,
    candidate_curvature_rmse_1pm=candidate_curvature_rmse,
    original_curvature_jump_max_abs_1pm=original_jump,
    candidate_curvature_jump_max_abs_1pm=candidate_jump,
    original_curvature_rate_max_abs_1pm2=original_rate,
    candidate_curvature_rate_max_abs_1pm2=candidate_rate,
  )


def build_virtual_mean_shift_candidate(data: PathQualityInput) -> VirtualMeanShiftCandidate:
  """Translate the observed path laterally by its mean model-relative lane-center bias."""
  if not isinstance(data, PathQualityInput):
    raise ValueError('data must be a PathQualityInput')

  observation = observe_path_quality(data)
  if not observation.valid:
    return _blocked_mean_shift(observation.reason)
  if not _observation_is_finite(observation):
    return _blocked_mean_shift('derived_geometry_invalid')

  try:
    center = tuple(
      float(left / 2.0 + right / 2.0)
      for left, right in zip(data.left_lane_y_m, data.right_lane_y_m, strict=True)
    )
    original_bias = tuple(
      float(original - lane_center)
      for original, lane_center in zip(data.desired_path_y_m, center, strict=True)
    )
    applied_shift = -_stable_mean(original_bias)
    candidate = tuple(float(original + applied_shift) for original in data.desired_path_y_m)
    if not all(math.isfinite(value) for value in (*center, *original_bias, *candidate, applied_shift)):
      raise ValueError('nonfinite mean-shift geometry')
    if any(not min(left, right) <= shifted <= max(left, right) for shifted, left, right in zip(
      candidate, data.left_lane_y_m, data.right_lane_y_m, strict=True,
    )):
      return _blocked_mean_shift('candidate_outside_lanes')

    residual_bias = tuple(
      float(shifted - lane_center)
      for shifted, lane_center in zip(candidate, center, strict=True)
    )
    if not all(math.isfinite(value) for value in residual_bias):
      raise ValueError('nonfinite mean-shift geometry')

    residual_mean = _stable_mean(residual_bias)
    residual_rmse = _stable_rmse(residual_bias)
    residual_max = float(max(abs(value) for value in residual_bias))
    original_curvature_rmse, original_jump, original_rate = _curvature_metrics(data.station_m, data.desired_path_y_m)
    candidate_curvature_rmse, candidate_jump, candidate_rate = _curvature_metrics(data.station_m, candidate)
  except (ArithmeticError, OverflowError, ValueError):
    return _blocked_mean_shift('derived_geometry_invalid')

  return VirtualMeanShiftCandidate(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    sample_count=len(data.station_m),
    station_m=tuple(float(value) for value in data.station_m),
    original_path_y_m=tuple(float(value) for value in data.desired_path_y_m),
    candidate_path_y_m=candidate,
    applied_shift_m=float(applied_shift),
    residual_lane_center_bias_mean_m=residual_mean,
    residual_lane_center_bias_rmse_m=residual_rmse,
    residual_lane_center_bias_max_abs_m=residual_max,
    original_curvature_rmse_1pm=original_curvature_rmse,
    candidate_curvature_rmse_1pm=candidate_curvature_rmse,
    original_curvature_jump_max_abs_1pm=original_jump,
    candidate_curvature_jump_max_abs_1pm=candidate_jump,
    original_curvature_rate_max_abs_1pm2=original_rate,
    candidate_curvature_rate_max_abs_1pm2=candidate_rate,
  )


def attribute_virtual_mean_shift_transition(previous: PathQualityInput,
                                            current: PathQualityInput) -> VirtualMeanShiftTransition:
  """Attribute a virtual mean-shift change without creating temporal control state."""
  if not isinstance(previous, PathQualityInput) or not isinstance(current, PathQualityInput):
    raise ValueError('previous and current must be PathQualityInput values')

  previous_count = len(previous.station_m)
  current_count = len(current.station_m)
  station_axis_changed = tuple(previous.station_m) != tuple(current.station_m)
  previous_candidate = build_virtual_mean_shift_candidate(previous)
  if previous_candidate.status != 'DESCRIPTIVE_ONLY':
    return _blocked_transition('previous_' + previous_candidate.reason, previous_count, current_count,
                               station_axis_changed=station_axis_changed)
  current_candidate = build_virtual_mean_shift_candidate(current)
  if current_candidate.status != 'DESCRIPTIVE_ONLY':
    return _blocked_transition('current_' + current_candidate.reason, previous_count, current_count,
                               station_axis_changed=station_axis_changed)

  previous_observation = observe_path_quality(previous)
  current_observation = observe_path_quality(current)
  if not (_observation_is_finite(previous_observation) and _observation_is_finite(current_observation)):
    return _blocked_transition('derived_transition_invalid', previous_count, current_count,
                               station_axis_changed=station_axis_changed)

  previous_index = {station: i for i, station in enumerate(previous.station_m)}
  current_index = {station: i for i, station in enumerate(current.station_m)}
  common_station = tuple(station for station in previous.station_m if station in current_index)
  if len(common_station) < 3:
    return _blocked_transition('insufficient_common_stations', previous_count, current_count,
                               common_count=len(common_station), station_axis_changed=station_axis_changed)

  try:
    previous_center = tuple(
      float(left / 2.0 + right / 2.0)
      for left, right in zip(previous.left_lane_y_m, previous.right_lane_y_m, strict=True)
    )
    current_center = tuple(
      float(left / 2.0 + right / 2.0)
      for left, right in zip(current.left_lane_y_m, current.right_lane_y_m, strict=True)
    )

    previous_path_mean = _stable_mean(previous.desired_path_y_m)
    current_path_mean = _stable_mean(current.desired_path_y_m)
    previous_center_mean = _stable_mean(previous_center)
    current_center_mean = _stable_mean(current_center)
    previous_left_mean = _stable_mean(previous.left_lane_y_m)
    current_left_mean = _stable_mean(current.left_lane_y_m)
    previous_right_mean = _stable_mean(previous.right_lane_y_m)
    current_right_mean = _stable_mean(current.right_lane_y_m)

    previous_path_common = _stable_mean(tuple(previous.desired_path_y_m[previous_index[s]] for s in common_station))
    current_path_common = _stable_mean(tuple(current.desired_path_y_m[current_index[s]] for s in common_station))
    previous_center_common = _stable_mean(tuple(previous_center[previous_index[s]] for s in common_station))
    current_center_common = _stable_mean(tuple(current_center[current_index[s]] for s in common_station))
    previous_left_common = _stable_mean(tuple(previous.left_lane_y_m[previous_index[s]] for s in common_station))
    current_left_common = _stable_mean(tuple(current.left_lane_y_m[current_index[s]] for s in common_station))
    previous_right_common = _stable_mean(tuple(previous.right_lane_y_m[previous_index[s]] for s in common_station))
    current_right_common = _stable_mean(tuple(current.right_lane_y_m[current_index[s]] for s in common_station))

    previous_shift = float(previous_candidate.applied_shift_m)
    current_shift = float(current_candidate.applied_shift_m)
    shift_delta = current_shift - previous_shift
    lane_component = current_center_mean - previous_center_mean
    path_component = -(current_path_mean - previous_path_mean)
    common_lane_component = current_center_common - previous_center_common
    common_path_component = -(current_path_common - previous_path_common)
    horizon_component = shift_delta - common_lane_component - common_path_component
    left_component = current_left_mean - previous_left_mean
    right_component = current_right_mean - previous_right_mean
    common_left_component = current_left_common - previous_left_common
    common_right_component = current_right_common - previous_right_common
    lane_width_delta = float(current_observation.lane_width_mean_m - previous_observation.lane_width_mean_m)
    values = (
      previous_shift, current_shift, shift_delta, lane_component, path_component,
      common_lane_component, common_path_component, horizon_component,
      left_component, right_component, common_left_component, common_right_component,
      lane_width_delta,
    )
    if not all(math.isfinite(value) for value in values):
      raise ValueError('nonfinite transition geometry')
    if not math.isclose(shift_delta, lane_component + path_component, rel_tol=1e-12, abs_tol=1e-12):
      raise ValueError('mean-shift decomposition mismatch')
  except (ArithmeticError, OverflowError, TypeError, ValueError):
    return _blocked_transition('derived_transition_invalid', previous_count, current_count,
                               common_count=len(common_station), station_axis_changed=station_axis_changed)

  same_direction = (
    (common_left_component > 0.0 and common_right_component > 0.0) or
    (common_left_component < 0.0 and common_right_component < 0.0)
  )
  return VirtualMeanShiftTransition(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    previous_sample_count=previous_count,
    current_sample_count=current_count,
    common_sample_count=len(common_station),
    sample_count_changed=previous_count != current_count,
    station_axis_changed=station_axis_changed,
    previous_horizon_m=float(previous.station_m[-1]),
    current_horizon_m=float(current.station_m[-1]),
    horizon_delta_m=float(current.station_m[-1] - previous.station_m[-1]),
    previous_shift_m=previous_shift,
    current_shift_m=current_shift,
    shift_delta_m=float(shift_delta),
    lane_center_component_m=float(lane_component),
    path_component_m=float(path_component),
    common_lane_center_component_m=float(common_lane_component),
    common_path_component_m=float(common_path_component),
    horizon_component_m=float(horizon_component),
    left_lane_component_m=float(left_component),
    right_lane_component_m=float(right_component),
    common_left_lane_component_m=float(common_left_component),
    common_right_lane_component_m=float(common_right_component),
    lane_width_mean_delta_m=lane_width_delta,
    lane_boundaries_same_direction=same_direction,
    previous_confidence=float(previous_observation.confidence),
    current_confidence=float(current_observation.confidence),
  )
