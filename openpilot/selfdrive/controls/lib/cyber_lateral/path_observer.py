"""Carrot-inspired read-only lane/path quality observation.

The result diagnoses model-path geometry and never returns a path, curvature,
lane offset or actuator command.
"""
from bisect import bisect_right
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PathQualityInput:
  station_m: tuple[float, ...]
  desired_path_y_m: tuple[float, ...]
  left_lane_y_m: tuple[float, ...]
  right_lane_y_m: tuple[float, ...]
  left_lane_probability: tuple[float, ...]
  right_lane_probability: tuple[float, ...]
  left_lane_std_m: tuple[float, ...]
  right_lane_std_m: tuple[float, ...]
  left_road_edge_y_m: tuple[float, ...] | None
  right_road_edge_y_m: tuple[float, ...] | None
  lane_change_active: bool
  maneuver_state: str


@dataclass(frozen=True)
class PathQualityObservation:
  valid: bool
  reason: str
  sample_count: int
  model_to_lane_center_bias_m: float | None
  lane_width_mean_m: float | None
  lane_width_std_m: float | None
  confidence: float | None
  minimum_edge_clearance_m: float | None


def _invalid(reason: str) -> PathQualityObservation:
  return PathQualityObservation(False, reason, 0, None, None, None, None, None)


def _finite_tuple(value) -> bool:
  return (isinstance(value, tuple) and
          all(type(sample) in (int, float) and math.isfinite(sample) for sample in value))


def align_path_to_stations(source_x_m: tuple[float, ...], source_y_m: tuple[float, ...],
                           query_x_m: tuple[float, ...]) -> tuple[tuple[float, ...], tuple[float, ...], tuple[int, ...]]:
  """Linearly regrid a model path onto only the lane stations it actually covers."""
  if not all(_finite_tuple(values) for values in (source_x_m, source_y_m, query_x_m)):
    raise ValueError('path alignment values must be finite tuples')
  if len(source_x_m) != len(source_y_m) or len(source_x_m) < 2:
    raise ValueError('source path shape is invalid')
  if any(current <= previous for previous, current in zip(source_x_m, source_x_m[1:], strict=False)):
    raise ValueError('source path station must be strictly increasing')
  if any(current <= previous for previous, current in zip(query_x_m, query_x_m[1:], strict=False)):
    raise ValueError('query station must be strictly increasing')

  selected = tuple(
    index for index, station in enumerate(query_x_m)
    if source_x_m[0] <= station <= source_x_m[-1]
  )
  if len(selected) < 3:
    raise ValueError('fewer than three lane stations overlap the model path')

  stations = tuple(float(query_x_m[index]) for index in selected)
  aligned = []
  for station in stations:
    right = bisect_right(source_x_m, station)
    if right == 0:
      aligned.append(float(source_y_m[0]))
    elif right == len(source_x_m):
      aligned.append(float(source_y_m[-1]))
    else:
      left = right - 1
      if source_x_m[left] == station:
        aligned.append(float(source_y_m[left]))
      else:
        fraction = (station - source_x_m[left]) / (source_x_m[right] - source_x_m[left])
        aligned.append(float(source_y_m[left] + fraction * (source_y_m[right] - source_y_m[left])))
  return stations, tuple(aligned), selected


def observe_path_quality(data: PathQualityInput) -> PathQualityObservation:
  if not isinstance(data, PathQualityInput):
    raise ValueError('data must be a PathQualityInput')
  if data.lane_change_active or data.maneuver_state != 'none':
    return _invalid('lane_change_or_maneuver')

  required = (
    data.station_m, data.desired_path_y_m, data.left_lane_y_m, data.right_lane_y_m,
    data.left_lane_probability, data.right_lane_probability,
    data.left_lane_std_m, data.right_lane_std_m,
  )
  if not all(_finite_tuple(values) for values in required):
    return _invalid('invalid_geometry_values')
  sample_count = len(data.station_m)
  optional_edges = tuple(
    edge for edge in (data.left_road_edge_y_m, data.right_road_edge_y_m) if edge is not None
  )
  if (sample_count < 3 or any(len(values) != sample_count for values in (*required[1:], *optional_edges))):
    return _invalid('geometry_shape_mismatch')
  if any(current <= previous for previous, current in zip(data.station_m, data.station_m[1:], strict=False)):
    return _invalid('invalid_station_axis')
  if not all(_finite_tuple(edge) for edge in optional_edges):
    return _invalid('invalid_geometry_values')

  probabilities = (*data.left_lane_probability, *data.right_lane_probability)
  if any(probability < 0. or probability > 1. for probability in probabilities):
    return _invalid('invalid_lane_probability')
  if any(probability == 0. for probability in probabilities):
    return _invalid('lane_loss')
  standard_deviations = (*data.left_lane_std_m, *data.right_lane_std_m)
  if any(std < 0. for std in standard_deviations):
    return _invalid('invalid_lane_std')

  lane_order = tuple(
    1 if left > right else -1 if left < right else 0
    for left, right in zip(data.left_lane_y_m, data.right_lane_y_m, strict=True)
  )
  if 0 in lane_order or any(direction != lane_order[0] for direction in lane_order[1:]):
    return _invalid('crossed_lane_boundaries')
  if data.left_road_edge_y_m is not None and data.right_road_edge_y_m is not None:
    edge_order = tuple(
      1 if left > right else -1 if left < right else 0
      for left, right in zip(data.left_road_edge_y_m, data.right_road_edge_y_m, strict=True)
    )
    if (0 in edge_order or any(direction != edge_order[0] for direction in edge_order[1:]) or
        edge_order[0] != lane_order[0]):
      return _invalid('crossed_lane_boundaries')

  widths = tuple(
    abs(left - right) for left, right in zip(data.left_lane_y_m, data.right_lane_y_m, strict=True)
  )
  if any(not min(left, right) <= desired <= max(left, right) for desired, left, right in zip(
    data.desired_path_y_m, data.left_lane_y_m, data.right_lane_y_m, strict=True,
  )):
    return _invalid('desired_path_outside_lanes')

  lane_centers = tuple(
    (left + right) / 2. for left, right in zip(data.left_lane_y_m, data.right_lane_y_m, strict=True)
  )
  edge_clearances = []
  if data.left_road_edge_y_m is not None:
    for edge, lane, center in zip(data.left_road_edge_y_m, data.left_lane_y_m, lane_centers, strict=True):
      if (edge - center) * (lane - center) <= 0. or abs(edge - center) < abs(lane - center):
        return _invalid('invalid_road_edge_ordering')
      edge_clearances.append(abs(edge - lane))
  if data.right_road_edge_y_m is not None:
    for edge, lane, center in zip(data.right_road_edge_y_m, data.right_lane_y_m, lane_centers, strict=True):
      if (edge - center) * (lane - center) <= 0. or abs(edge - center) < abs(lane - center):
        return _invalid('invalid_road_edge_ordering')
      edge_clearances.append(abs(edge - lane))
  bias = tuple(
    desired - center for desired, center in zip(data.desired_path_y_m, lane_centers, strict=True)
  )
  width_mean = sum(widths) / sample_count
  width_std = math.sqrt(sum((width - width_mean) ** 2 for width in widths) / sample_count)
  confidence_samples = tuple(
    probability / (1. + std)
    for probability, std in zip(
      (*data.left_lane_probability, *data.right_lane_probability),
      (*data.left_lane_std_m, *data.right_lane_std_m), strict=True,
    )
  )
  return PathQualityObservation(
    valid=True,
    reason='ok',
    sample_count=sample_count,
    model_to_lane_center_bias_m=float(sum(bias) / sample_count),
    lane_width_mean_m=float(width_mean),
    lane_width_std_m=float(width_std),
    confidence=float(sum(confidence_samples) / len(confidence_samples)),
    minimum_edge_clearance_m=float(min(edge_clearances)) if edge_clearances else None,
  )
