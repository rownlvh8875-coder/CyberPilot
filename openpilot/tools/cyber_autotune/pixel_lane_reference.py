"""Offline-only qcamera pixel lane-reference diagnostic.

The detector consumes caller-owned qcamera RGB pixels and returns descriptive
image geometry only. It has no model, planner, controller, Params, CAN, device,
profile, or actuator integration. Projection comparison is a separate pure
function so the pixel detector cannot be influenced by model geometry.
"""
from dataclasses import dataclass
import math
from numbers import Real

import numpy as np


QCAMERA_SHAPE = (330, 526, 3)
Q_W = 526
FIT_Y0 = 185
FIT_Y1 = 292
EVAL_Y = 260

_MIN_ON_MEDIAN = 0.08
_MIN_CONTRAST_MEDIAN = 0.03
_MIN_POSITIVE_CONTRAST_FRACTION = 0.70


@dataclass(frozen=True)
class PixelLaneDetection:
  status: str
  reason: str
  eval_y_px: int
  left_x_px: float | None
  right_x_px: float | None
  center_x_px: float | None
  lane_width_px: float | None
  objective: float | None
  ambiguity_margin: float | None
  left_on_median: float | None
  right_on_median: float | None
  left_contrast_median: float | None
  right_contrast_median: float | None
  left_positive_contrast_fraction: float | None
  right_positive_contrast_fraction: float | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


@dataclass(frozen=True)
class PixelProjectionComparison:
  status: str
  reason: str
  turn: str | None
  model_center_abs_error_px: float | None
  model_path_abs_error_px: float | None
  model_center_inside_pixel_center_px: float | None
  model_path_inside_pixel_center_px: float | None
  model_path_inside_model_center_px: float | None
  path_farther_from_pixel_center: bool | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked_detection(reason: str) -> PixelLaneDetection:
  return PixelLaneDetection(
    status='BLOCKED',
    reason=reason,
    eval_y_px=EVAL_Y,
    left_x_px=None,
    right_x_px=None,
    center_x_px=None,
    lane_width_px=None,
    objective=None,
    ambiguity_margin=None,
    left_on_median=None,
    right_on_median=None,
    left_contrast_median=None,
    right_contrast_median=None,
    left_positive_contrast_fraction=None,
    right_positive_contrast_fraction=None,
  )


def _blocked_comparison(reason: str) -> PixelProjectionComparison:
  return PixelProjectionComparison(
    status='BLOCKED',
    reason=reason,
    turn=None,
    model_center_abs_error_px=None,
    model_path_abs_error_px=None,
    model_center_inside_pixel_center_px=None,
    model_path_inside_pixel_center_px=None,
    model_path_inside_model_center_px=None,
    path_farther_from_pixel_center=None,
  )


def _finite_real(value) -> bool:
  return isinstance(value, Real) and not isinstance(value, (bool, np.bool_)) and math.isfinite(float(value))


def _image_score(rgb: np.ndarray) -> np.ndarray:
  values = rgb.astype(np.float32) / 255.0
  minimum = values.min(axis=2)
  maximum = values.max(axis=2)
  saturation = maximum - minimum
  gray = 0.299 * values[:, :, 0] + 0.587 * values[:, :, 1] + 0.114 * values[:, :, 2]

  gx = np.zeros_like(gray)
  gy = np.zeros_like(gray)
  gx[:, 1:-1] = (gray[:, 2:] - gray[:, :-2]) * 0.5
  gy[1:-1, :] = (gray[2:, :] - gray[:-2, :]) * 0.5
  edge = np.clip(np.sqrt(gx * gx + gy * gy) / 0.22, 0.0, 1.0)
  white = np.clip((minimum - 0.16) / 0.55, 0.0, 1.0) * np.clip(1.0 - saturation / 0.55, 0.0, 1.0)

  score = 0.62 * edge + 0.38 * white
  score[:FIT_Y0 - 5, :] = 0.0
  score[FIT_Y1 + 6:, :] = 0.0
  return score


def _line_samples(score: np.ndarray, xt: int, xb: int) -> tuple[np.ndarray, np.ndarray]:
  ys = np.arange(FIT_Y0, FIT_Y1 + 1, dtype=np.intp)
  xs = np.rint(xt + (xb - xt) * (ys - FIT_Y0) / (FIT_Y1 - FIT_Y0)).astype(np.intp)

  on_offsets = np.arange(-3, 4, dtype=np.intp)
  on_x = xs[:, None] + on_offsets[None, :]
  on_values = score[ys[:, None], on_x]
  on = np.max(on_values, axis=1)

  background_offsets = np.concatenate((
    np.arange(-17, -7, dtype=np.intp),
    np.arange(8, 18, dtype=np.intp),
  ))
  background_x = xs[:, None] + background_offsets[None, :]
  valid = (background_x >= 0) & (background_x < Q_W)
  clipped_x = np.clip(background_x, 0, Q_W - 1)
  background_values = score[ys[:, None], clipped_x]
  background_values = np.where(valid, background_values, np.nan)
  background = np.nanmedian(background_values, axis=1)

  return on, on - background


def _side_objective(score: np.ndarray, xt: int, xb: int) -> tuple[float, tuple[float, float, float]]:
  on, contrast = _line_samples(score, xt, xb)
  on_median = float(np.median(on))
  contrast_median = float(np.median(contrast))
  positive_fraction = float(np.mean(contrast > 0.0))
  objective = (
    on_median
    + 0.40 * float(np.quantile(on, 0.25))
    + 0.45 * contrast_median
    + 0.20 * float(np.quantile(contrast, 0.25))
  )
  return float(objective), (on_median, contrast_median, positive_fraction)


def _line_x(xt: float, xb: float, y: float) -> float:
  return float(xt + (xb - xt) * (y - FIT_Y0) / (FIT_Y1 - FIT_Y0))


def _sufficient_signal(quality: tuple[float, float, float]) -> bool:
  on_median, contrast_median, positive_fraction = quality
  return (
    on_median >= _MIN_ON_MEDIAN
    and contrast_median >= _MIN_CONTRAST_MEDIAN
    and positive_fraction >= _MIN_POSITIVE_CONTRAST_FRACTION
  )


def detect_qcamera_lane_pair(rgb: np.ndarray) -> PixelLaneDetection:
  """Detect a lower-ROI perspective lane pair without using model geometry.

  This deliberately accepts only the qcamera uint8 RGB contract used by the
  private probe. Unsupported frames fail closed instead of being rescaled or
  implicitly converted.
  """
  if not isinstance(rgb, np.ndarray) or rgb.shape != QCAMERA_SHAPE or rgb.dtype != np.uint8:
    return _blocked_detection('INVALID_QCAMERA_FRAME')

  score = _image_score(rgb)
  if float(np.max(score[FIT_Y0:FIT_Y1 + 1])) < _MIN_ON_MEDIAN:
    return _blocked_detection('INSUFFICIENT_LANE_SIGNAL')

  left_candidates = []
  for xt in range(145, 291, 4):
    for xb in range(12, min(xt - 8, 252), 4):
      objective, quality = _side_objective(score, xt, xb)
      left_candidates.append((objective, xt, xb, quality))

  right_candidates = []
  for xt in range(195, 371, 4):
    for xb in range(max(xt + 8, 278), 518, 4):
      objective, quality = _side_objective(score, xt, xb)
      right_candidates.append((objective, xt, xb, quality))

  left_candidates = sorted(left_candidates, key=lambda value: value[0], reverse=True)[:100]
  right_candidates = sorted(right_candidates, key=lambda value: value[0], reverse=True)[:100]

  pairs = []
  for left_score, left_top, left_bottom, left_quality in left_candidates:
    for right_score, right_top, right_bottom, right_quality in right_candidates:
      top_width = right_top - left_top
      bottom_width = right_bottom - left_bottom
      if not (22 <= top_width <= 190 and 145 <= bottom_width <= 400):
        continue
      if bottom_width < top_width + 70:
        continue

      denominator = (right_bottom - right_top) - (left_bottom - left_top)
      if abs(denominator) < 1e-9:
        continue
      fraction = -top_width / denominator
      vanishing_y = FIT_Y0 + fraction * (FIT_Y1 - FIT_Y0)
      if not (55 <= vanishing_y <= 210):
        continue

      left_x = _line_x(left_top, left_bottom, EVAL_Y)
      right_x = _line_x(right_top, right_bottom, EVAL_Y)
      lane_width = right_x - left_x
      center_x = (left_x + right_x) / 2.0
      if not (125 <= lane_width <= 355 and 120 <= center_x <= 405):
        continue

      width_prior = -0.00045 * abs(bottom_width - 280)
      objective = float(left_score + right_score + width_prior)
      if not math.isfinite(objective):
        continue
      pairs.append((
        objective, left_top, left_bottom, right_top, right_bottom,
        left_quality, right_quality, center_x, lane_width,
      ))

  if not pairs:
    return _blocked_detection('NO_GEOMETRIC_PAIR')

  pairs.sort(key=lambda value: value[0], reverse=True)
  best = pairs[0]
  best_center = best[7]
  alternate = next((pair for pair in pairs[1:] if abs(pair[7] - best_center) >= 12.0), None)
  ambiguity_margin = None if alternate is None else float(best[0] - alternate[0])

  objective, left_top, left_bottom, right_top, right_bottom, left_quality, right_quality, center_x, lane_width = best
  if not _sufficient_signal(left_quality) or not _sufficient_signal(right_quality):
    return _blocked_detection('INSUFFICIENT_LANE_SIGNAL')

  left_x = _line_x(left_top, left_bottom, EVAL_Y)
  right_x = _line_x(right_top, right_bottom, EVAL_Y)
  values = (objective, left_x, right_x, center_x, lane_width, *left_quality, *right_quality)
  if ambiguity_margin is not None:
    values += (ambiguity_margin,)
  if not all(math.isfinite(float(value)) for value in values):
    return _blocked_detection('DERIVED_GEOMETRY_NONFINITE')

  return PixelLaneDetection(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    eval_y_px=EVAL_Y,
    left_x_px=float(left_x),
    right_x_px=float(right_x),
    center_x_px=float(center_x),
    lane_width_px=float(lane_width),
    objective=float(objective),
    ambiguity_margin=ambiguity_margin,
    left_on_median=float(left_quality[0]),
    right_on_median=float(right_quality[0]),
    left_contrast_median=float(left_quality[1]),
    right_contrast_median=float(right_quality[1]),
    left_positive_contrast_fraction=float(left_quality[2]),
    right_positive_contrast_fraction=float(right_quality[2]),
  )


def compare_projection_to_pixel_reference(pixel_lane_center_x_px, model_lane_center_x_px,
                                          model_path_x_px, desired_curvature_1pm) -> PixelProjectionComparison:
  """Compare projected model geometry against an image-derived lane midpoint.

  Positive inside metrics mean the projected item lies farther toward the
  inside of the requested turn. The function is descriptive and cannot accept
  a candidate, tune a controller, or activate a vehicle.
  """
  values = (pixel_lane_center_x_px, model_lane_center_x_px, model_path_x_px, desired_curvature_1pm)
  if not all(_finite_real(value) for value in values):
    return _blocked_comparison('NONFINITE_INPUT')

  pixel_center = float(pixel_lane_center_x_px)
  if not 0.0 <= pixel_center < Q_W:
    return _blocked_comparison('PIXEL_REFERENCE_OUT_OF_FRAME')

  model_center = float(model_lane_center_x_px)
  model_path = float(model_path_x_px)
  desired_curvature = float(desired_curvature_1pm)
  if desired_curvature == 0.0:
    return _blocked_comparison('TURN_UNRESOLVED')

  turn = 'LEFT' if desired_curvature > 0.0 else 'RIGHT'
  inside_sign = -1.0 if desired_curvature > 0.0 else 1.0
  center_delta = model_center - pixel_center
  path_delta = model_path - pixel_center
  path_from_model_center = model_path - model_center

  derived = (
    abs(center_delta),
    abs(path_delta),
    center_delta * inside_sign,
    path_delta * inside_sign,
    path_from_model_center * inside_sign,
  )
  if not all(math.isfinite(value) for value in derived):
    return _blocked_comparison('DERIVED_GEOMETRY_NONFINITE')

  return PixelProjectionComparison(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    turn=turn,
    model_center_abs_error_px=float(derived[0]),
    model_path_abs_error_px=float(derived[1]),
    model_center_inside_pixel_center_px=float(derived[2]),
    model_path_inside_pixel_center_px=float(derived[3]),
    model_path_inside_model_center_px=float(derived[4]),
    path_farther_from_pixel_center=bool(derived[1] > derived[0]),
  )
