"""Offline descriptive timeline for separated path-bias/tracking diagnostics.

The caller owns source provenance and reconstruction. This module never loads
logs, searches for an alignment lag, classifies root cause, changes a controller
or treats model lane geometry as independent lane-center truth.
"""
from dataclasses import dataclass
from fractions import Fraction
import math


_MAX_TIME_NS = 2 ** 63 - 1


@dataclass(frozen=True)
class PathTrackingTimelineSample:
  path_mono_time_ns: int
  tracking_mono_time_ns: int
  model_to_lane_center_bias_m: float
  desired_curvature_1pm: float
  current_curvature_1pm: float


@dataclass(frozen=True)
class PathTrackingTimelinePoint:
  path_mono_time_ns: int
  tracking_mono_time_ns: int
  time_skew_ns: int
  model_to_lane_center_bias_m: float
  desired_curvature_1pm: float
  current_curvature_1pm: float
  curvature_tracking_error_1pm: float


@dataclass(frozen=True)
class CurvatureBucketSummary:
  count: int
  model_bias_signed_mean_m: float | None
  model_bias_rmse_m: float | None
  model_bias_max_abs_m: float | None
  tracking_error_signed_mean_1pm: float | None
  tracking_error_rmse_1pm: float | None
  tracking_error_max_abs_1pm: float | None


@dataclass(frozen=True)
class PathTrackingTimelineSummary:
  sample_count: int
  unique_tracking_time_count: int
  points: tuple[PathTrackingTimelinePoint, ...]
  time_skew_mean_ns: float
  time_skew_min_ns: int
  time_skew_max_ns: int
  model_bias_signed_mean_m: float
  model_bias_rmse_m: float
  model_bias_max_abs_m: float
  tracking_error_signed_mean_1pm: float
  tracking_error_rmse_1pm: float
  tracking_error_max_abs_1pm: float
  model_bias_peak_path_time_ns: int
  tracking_error_peak_tracking_time_ns: int
  tracking_peak_minus_bias_peak_ns: int
  positive_curvature: CurvatureBucketSummary
  negative_curvature: CurvatureBucketSummary
  zero_curvature: CurvatureBucketSummary


def _finite_number(value) -> bool:
  try:
    return type(value) in (int, float) and math.isfinite(value)
  except OverflowError:
    return False


def _stable_mean(values: tuple[float, ...]) -> float:
  if not values:
    raise ValueError('EMPTY_NUMERIC_SERIES')
  exact_total = sum((Fraction.from_float(value) for value in values), Fraction())
  result = float(exact_total / len(values))
  if not math.isfinite(result):
    raise ValueError('NONFINITE_DERIVED_STATISTIC')
  return result


def _stable_rmse(values: tuple[float, ...]) -> float:
  if not values:
    raise ValueError('EMPTY_NUMERIC_SERIES')
  scale = max(abs(value) for value in values)
  if scale == 0.:
    return 0.
  normalized = math.fsum((value / scale) ** 2 for value in values) / len(values)
  result = scale * math.sqrt(normalized)
  if not math.isfinite(result):
    raise ValueError('NONFINITE_DERIVED_STATISTIC')
  return float(result)


def _bucket(points: tuple[PathTrackingTimelinePoint, ...]) -> CurvatureBucketSummary:
  if not points:
    return CurvatureBucketSummary(0, None, None, None, None, None, None)
  bias = tuple(point.model_to_lane_center_bias_m for point in points)
  residual = tuple(point.curvature_tracking_error_1pm for point in points)
  return CurvatureBucketSummary(
    count=len(points),
    model_bias_signed_mean_m=_stable_mean(bias),
    model_bias_rmse_m=_stable_rmse(bias),
    model_bias_max_abs_m=float(max(abs(value) for value in bias)),
    tracking_error_signed_mean_1pm=_stable_mean(residual),
    tracking_error_rmse_1pm=_stable_rmse(residual),
    tracking_error_max_abs_1pm=float(max(abs(value) for value in residual)),
  )


def summarize_path_tracking_timeline(
    samples: tuple[PathTrackingTimelineSample, ...],
) -> PathTrackingTimelineSummary:
  """Summarize pre-associated path and tracking samples without inferring cause.

  The path and tracking timestamps remain separate clocks from caller-selected
  sources. Their difference is descriptive skew, not an alignment correction.
  Peak-time ordering is descriptive and is not causal.
  """
  if not isinstance(samples, tuple) or len(samples) < 2:
    raise ValueError('TIMELINE_REQUIRES_AT_LEAST_TWO_SAMPLES')
  if not all(isinstance(sample, PathTrackingTimelineSample) for sample in samples):
    raise ValueError('INVALID_TIMELINE_SAMPLE_TYPE')

  points = []
  previous_path = None
  previous_tracking = None
  for sample in samples:
    if (type(sample.path_mono_time_ns) is not int or not 0 < sample.path_mono_time_ns <= _MAX_TIME_NS or
        type(sample.tracking_mono_time_ns) is not int or not 0 < sample.tracking_mono_time_ns <= _MAX_TIME_NS):
      raise ValueError('INVALID_TIMELINE_TIMESTAMP')
    if previous_path is not None and sample.path_mono_time_ns <= previous_path:
      raise ValueError('PATH_TIME_NOT_STRICTLY_INCREASING')
    if previous_tracking is not None and sample.tracking_mono_time_ns < previous_tracking:
      raise ValueError('TRACKING_TIME_REVERSED')
    previous_path = sample.path_mono_time_ns
    previous_tracking = sample.tracking_mono_time_ns

    numeric = (
      sample.model_to_lane_center_bias_m,
      sample.desired_curvature_1pm,
      sample.current_curvature_1pm,
    )
    if not all(_finite_number(value) for value in numeric):
      raise ValueError('INVALID_TIMELINE_NUMERIC_VALUE')
    try:
      residual = float(sample.current_curvature_1pm - sample.desired_curvature_1pm)
    except OverflowError as error:
      raise ValueError('INVALID_TRACKING_RESIDUAL') from error
    if not math.isfinite(residual):
      raise ValueError('INVALID_TRACKING_RESIDUAL')

    points.append(PathTrackingTimelinePoint(
      path_mono_time_ns=sample.path_mono_time_ns,
      tracking_mono_time_ns=sample.tracking_mono_time_ns,
      time_skew_ns=sample.tracking_mono_time_ns - sample.path_mono_time_ns,
      model_to_lane_center_bias_m=float(sample.model_to_lane_center_bias_m),
      desired_curvature_1pm=float(sample.desired_curvature_1pm),
      current_curvature_1pm=float(sample.current_curvature_1pm),
      curvature_tracking_error_1pm=residual,
    ))

  frozen_points = tuple(points)
  bias = tuple(point.model_to_lane_center_bias_m for point in frozen_points)
  residual = tuple(point.curvature_tracking_error_1pm for point in frozen_points)
  skew = tuple(point.time_skew_ns for point in frozen_points)

  bias_peak_index = max(range(len(frozen_points)), key=lambda index: abs(bias[index]))
  tracking_peak_index = max(range(len(frozen_points)), key=lambda index: abs(residual[index]))
  positive = tuple(point for point in frozen_points if point.desired_curvature_1pm > 0.)
  negative = tuple(point for point in frozen_points if point.desired_curvature_1pm < 0.)
  zero = tuple(point for point in frozen_points if point.desired_curvature_1pm == 0.)

  return PathTrackingTimelineSummary(
    sample_count=len(frozen_points),
    unique_tracking_time_count=len({point.tracking_mono_time_ns for point in frozen_points}),
    points=frozen_points,
    time_skew_mean_ns=float(sum(skew) / len(skew)),
    time_skew_min_ns=min(skew),
    time_skew_max_ns=max(skew),
    model_bias_signed_mean_m=_stable_mean(bias),
    model_bias_rmse_m=_stable_rmse(bias),
    model_bias_max_abs_m=float(max(abs(value) for value in bias)),
    tracking_error_signed_mean_1pm=_stable_mean(residual),
    tracking_error_rmse_1pm=_stable_rmse(residual),
    tracking_error_max_abs_1pm=float(max(abs(value) for value in residual)),
    model_bias_peak_path_time_ns=frozen_points[bias_peak_index].path_mono_time_ns,
    tracking_error_peak_tracking_time_ns=frozen_points[tracking_peak_index].tracking_mono_time_ns,
    tracking_peak_minus_bias_peak_ns=(
      frozen_points[tracking_peak_index].tracking_mono_time_ns -
      frozen_points[bias_peak_index].path_mono_time_ns
    ),
    positive_curvature=_bucket(positive),
    negative_curvature=_bucket(negative),
    zero_curvature=_bucket(zero),
  )
