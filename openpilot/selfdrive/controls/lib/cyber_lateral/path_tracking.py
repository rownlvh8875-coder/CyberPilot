"""Read-only separation of model-path bias from native curvature tracking error.

This diagnostic only combines values already observed in one LateralContext.
It has no thresholds, classification, path correction, controller input, Params
access, actuator authority, or vehicle write path.
"""
from dataclasses import dataclass
import math

from openpilot.selfdrive.controls.lib.cyber_lateral.path_observer import PathQualityObservation


@dataclass(frozen=True)
class PathTrackingObservation:
  valid: bool
  reason: str
  model_mono_time_ns: int | None
  car_state_mono_time_ns: int | None
  model_to_lane_center_bias_m: float | None
  curvature_tracking_error_1pm: float | None


def _invalid(reason: str, model_mono_time_ns: int | None = None,
             car_state_mono_time_ns: int | None = None) -> PathTrackingObservation:
  return PathTrackingObservation(
    False, reason, model_mono_time_ns, car_state_mono_time_ns, None, None,
  )


def observe_path_tracking(*, model_mono_time_ns: int, car_state_mono_time_ns: int,
                          desired_curvature_1pm: float, current_curvature_1pm: float,
                          path_quality: PathQualityObservation | None) -> PathTrackingObservation:
  """Keep model-reference bias and controller tracking residual separate."""
  if (type(model_mono_time_ns) is not int or model_mono_time_ns <= 0 or
      type(car_state_mono_time_ns) is not int or car_state_mono_time_ns <= 0):
    return _invalid('invalid_timestamp')

  if (type(desired_curvature_1pm) not in (int, float) or
      type(current_curvature_1pm) not in (int, float) or
      not math.isfinite(desired_curvature_1pm) or
      not math.isfinite(current_curvature_1pm)):
    return _invalid('invalid_numeric_input', model_mono_time_ns, car_state_mono_time_ns)

  if path_quality is None:
    return _invalid('missing_path_reference', model_mono_time_ns, car_state_mono_time_ns)
  if (not isinstance(path_quality, PathQualityObservation) or not path_quality.valid or
      type(path_quality.model_to_lane_center_bias_m) not in (int, float) or
      not math.isfinite(path_quality.model_to_lane_center_bias_m)):
    return _invalid('invalid_path_reference', model_mono_time_ns, car_state_mono_time_ns)

  tracking_error = float(current_curvature_1pm - desired_curvature_1pm)
  if not math.isfinite(tracking_error):
    return _invalid('invalid_tracking_residual', model_mono_time_ns, car_state_mono_time_ns)

  return PathTrackingObservation(
    valid=True,
    reason='ok',
    model_mono_time_ns=model_mono_time_ns,
    car_state_mono_time_ns=car_state_mono_time_ns,
    model_to_lane_center_bias_m=float(path_quality.model_to_lane_center_bias_m),
    curvature_tracking_error_1pm=tracking_error,
  )
