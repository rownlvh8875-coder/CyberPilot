"""Offline-only model/pixel consistency check at a caller-owned action horizon.

The caller supplies an already-validated action-horizon convergence observation
and signed pixel-lane-relative offset measurements. This module only compares
descriptive states. It does not select frames, decode images, estimate
calibration or latency, generate curvature, tune parameters, or return vehicle
commands.
"""

from dataclasses import dataclass
import math

from openpilot.tools.cyber_autotune.action_horizon_convergence import (
  ActionHorizonConvergenceObservation,
)


@dataclass(frozen=True)
class PixelActionHorizonConsistencyObservation:
  status: str
  reason: str
  model_path_minus_lane_m: float | None
  model_path_minus_lane_slope_per_m: float | None
  model_convergence_state: str | None
  model_locally_converging: bool | None
  pixel_offset_lane_fraction: float | None
  pixel_offset_lane_fraction_slope_per_m: float | None
  pixel_convergence_state: str | None
  pixel_locally_converging: bool | None
  offset_sign_agreement: bool | None
  convergence_agreement: bool | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> PixelActionHorizonConsistencyObservation:
  return PixelActionHorizonConsistencyObservation(
    status='BLOCKED',
    reason=reason,
    model_path_minus_lane_m=None,
    model_path_minus_lane_slope_per_m=None,
    model_convergence_state=None,
    model_locally_converging=None,
    pixel_offset_lane_fraction=None,
    pixel_offset_lane_fraction_slope_per_m=None,
    pixel_convergence_state=None,
    pixel_locally_converging=None,
    offset_sign_agreement=None,
    convergence_agreement=None,
  )


def _finite(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _sign(value: float) -> int:
  return 1 if value > 0.0 else -1 if value < 0.0 else 0


def _convergence_state(offset: float, slope: float) -> str | None:
  product = offset * slope
  if not math.isfinite(product):
    return None
  if offset == 0.0:
    return 'CENTER'
  if slope == 0.0:
    return 'FLAT'
  return 'CONVERGING' if product < 0.0 else 'DIVERGING'


def _valid_action_horizon(observation: ActionHorizonConvergenceObservation) -> bool:
  if not isinstance(observation, ActionHorizonConvergenceObservation):
    return False
  if observation.status != 'DESCRIPTIVE_ONLY' or observation.reason != 'ok':
    return False
  if (
    observation.readiness != 'NOT_READY'
    or observation.vehicle_status != 'REAL_VEHICLE_UNVERIFIED'
    or observation.safety_status != 'VEHICLE_ACTIVATION_BLOCKED'
    or observation.vehicle_activation_allowed is not False
  ):
    return False

  required = (
    observation.path_minus_lane_m,
    observation.path_minus_lane_slope_per_m,
    observation.turn_relative_offset_m,
    observation.turn_relative_slope_per_m,
  )
  if not all(_finite(value) for value in required):
    return False
  if type(observation.locally_converging) is not bool or type(observation.recentered) is not bool:
    return False

  offset = float(observation.path_minus_lane_m)
  slope = float(observation.path_minus_lane_slope_per_m)
  turn_offset = float(observation.turn_relative_offset_m)
  turn_slope = float(observation.turn_relative_slope_per_m)

  expected_state = _convergence_state(offset, slope)
  if expected_state is None or observation.convergence_state != expected_state:
    return False
  if observation.locally_converging is not (expected_state == 'CONVERGING'):
    return False

  if turn_offset > 0.0:
    expected_side = 'INSIDE'
  elif turn_offset < 0.0:
    expected_side = 'OUTSIDE'
  else:
    expected_side = 'CENTER'
  if observation.offset_side != expected_side:
    return False

  # Recover the hidden turn normalization from either non-zero component and
  # require one common +/-1 sign for both offset and slope.
  turn = None
  if offset != 0.0:
    ratio = turn_offset / offset
    if not math.isfinite(ratio) or not math.isclose(abs(ratio), 1.0, rel_tol=0.0, abs_tol=1e-12):
      return False
    turn = 1 if ratio > 0.0 else -1
  elif slope != 0.0:
    ratio = turn_slope / slope
    if not math.isfinite(ratio) or not math.isclose(abs(ratio), 1.0, rel_tol=0.0, abs_tol=1e-12):
      return False
    turn = 1 if ratio > 0.0 else -1

  if turn is not None:
    if not math.isclose(turn_offset, offset * turn, rel_tol=0.0, abs_tol=1e-12):
      return False
    if not math.isclose(turn_slope, slope * turn, rel_tol=0.0, abs_tol=1e-12):
      return False
  elif turn_offset != 0.0 or turn_slope != 0.0:
    return False

  return True


def observe_pixel_action_horizon_consistency(
  model: ActionHorizonConvergenceObservation,
  *,
  pixel_offset_lane_fraction: float,
  pixel_offset_lane_fraction_slope_per_m: float,
) -> PixelActionHorizonConsistencyObservation:
  """Compare model-lane and image-derived local convergence descriptively.

  Pixel offset is expected to be signed in image-x coordinates compatible with
  the model/calibrated lateral sign (+right). Dividing by image-derived lane
  width is caller-owned and makes the supplied offset dimensionless.

  Convergence uses the coordinate-invariant exact rule offset * slope < 0.
  CENTER and FLAT remain distinct states. No epsilon, acceptance threshold,
  tuning rule, or vehicle authority is introduced.
  """
  if not isinstance(model, ActionHorizonConvergenceObservation) or model.status != 'DESCRIPTIVE_ONLY':
    return _blocked('ACTION_HORIZON_CONVERGENCE_BLOCKED')
  if not _valid_action_horizon(model):
    return _blocked('ACTION_HORIZON_CONVERGENCE_INVALID')
  if not _finite(pixel_offset_lane_fraction) or not _finite(pixel_offset_lane_fraction_slope_per_m):
    return _blocked('NONFINITE_PIXEL_REFERENCE')

  pixel_offset = float(pixel_offset_lane_fraction)
  pixel_slope = float(pixel_offset_lane_fraction_slope_per_m)
  pixel_state = _convergence_state(pixel_offset, pixel_slope)
  if pixel_state is None:
    return _blocked('PIXEL_DERIVED_VALUE_INVALID')

  model_offset = float(model.path_minus_lane_m)
  model_slope = float(model.path_minus_lane_slope_per_m)
  model_state = str(model.convergence_state)

  model_sign = _sign(model_offset)
  pixel_sign = _sign(pixel_offset)
  sign_agreement = None if model_sign == 0 or pixel_sign == 0 else model_sign == pixel_sign
  pixel_locally_converging = pixel_state == 'CONVERGING'

  return PixelActionHorizonConsistencyObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    model_path_minus_lane_m=model_offset,
    model_path_minus_lane_slope_per_m=model_slope,
    model_convergence_state=model_state,
    model_locally_converging=model.locally_converging,
    pixel_offset_lane_fraction=pixel_offset,
    pixel_offset_lane_fraction_slope_per_m=pixel_slope,
    pixel_convergence_state=pixel_state,
    pixel_locally_converging=pixel_locally_converging,
    offset_sign_agreement=sign_agreement,
    convergence_agreement=model_state == pixel_state,
  )
