"""Offline-only separation of position geometry from orientation geometry.

The caller supplies an already-validated action-horizon convergence observation,
a model-lane-center slope, and the model orientation yaw at the same horizon.
This module only reports whether orientation asks for more or less turn than the
lane-center tangent while preserving the position-geometry state. It does not
create an action correction, tune parameters, or return vehicle authority.
"""

from dataclasses import dataclass
import math

from openpilot.tools.cyber_autotune.action_horizon_convergence import (
  ActionHorizonConvergenceObservation,
)


@dataclass(frozen=True)
class PositionOrientationSeparationObservation:
  status: str
  reason: str
  geometry_state: str | None
  offset_side: str | None
  turn_sign: int | None
  lane_center_slope_per_m: float | None
  lane_center_yaw_rad: float | None
  model_orientation_yaw_rad: float | None
  orientation_minus_lane_yaw_rad: float | None
  turn_relative_orientation_minus_lane_yaw_rad: float | None
  orientation_relation: str | None
  combined_state: str | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> PositionOrientationSeparationObservation:
  return PositionOrientationSeparationObservation(
    status='BLOCKED',
    reason=reason,
    geometry_state=None,
    offset_side=None,
    turn_sign=None,
    lane_center_slope_per_m=None,
    lane_center_yaw_rad=None,
    model_orientation_yaw_rad=None,
    orientation_minus_lane_yaw_rad=None,
    turn_relative_orientation_minus_lane_yaw_rad=None,
    orientation_relation=None,
    combined_state=None,
  )


def _finite(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _convergence_state(offset: float, slope: float) -> str | None:
  product = offset * slope
  if not math.isfinite(product):
    return None
  if offset == 0.0:
    return 'CENTER'
  if slope == 0.0:
    return 'FLAT'
  return 'CONVERGING' if product < 0.0 else 'DIVERGING'


def _validated_turn(observation: ActionHorizonConvergenceObservation) -> tuple[bool, int | None]:
  if not isinstance(observation, ActionHorizonConvergenceObservation):
    return False, None
  if observation.status != 'DESCRIPTIVE_ONLY' or observation.reason != 'ok':
    return False, None
  if (
    observation.readiness != 'NOT_READY'
    or observation.vehicle_status != 'REAL_VEHICLE_UNVERIFIED'
    or observation.safety_status != 'VEHICLE_ACTIVATION_BLOCKED'
    or observation.vehicle_activation_allowed is not False
  ):
    return False, None

  required = (
    observation.path_minus_lane_m,
    observation.path_minus_lane_slope_per_m,
    observation.turn_relative_offset_m,
    observation.turn_relative_slope_per_m,
  )
  if not all(_finite(value) for value in required):
    return False, None
  if type(observation.locally_converging) is not bool or type(observation.recentered) is not bool:
    return False, None

  offset = float(observation.path_minus_lane_m)
  slope = float(observation.path_minus_lane_slope_per_m)
  turn_offset = float(observation.turn_relative_offset_m)
  turn_slope = float(observation.turn_relative_slope_per_m)

  expected_state = _convergence_state(offset, slope)
  if expected_state is None or observation.convergence_state != expected_state:
    return False, None
  if observation.locally_converging is not (expected_state == 'CONVERGING'):
    return False, None

  expected_side = 'INSIDE' if turn_offset > 0.0 else 'OUTSIDE' if turn_offset < 0.0 else 'CENTER'
  if observation.offset_side != expected_side:
    return False, None

  if offset == 0.0:
    # The hidden requested-turn sign cannot be recovered from a centered offset.
    # Safety and structural identities above are still validated first.
    return turn_offset == 0.0, None

  ratio = turn_offset / offset
  if not math.isfinite(ratio) or not math.isclose(abs(ratio), 1.0, rel_tol=0.0, abs_tol=1e-12):
    return False, None
  turn = 1 if ratio > 0.0 else -1

  if not math.isclose(turn_offset, offset * turn, rel_tol=0.0, abs_tol=1e-12):
    return False, None
  if not math.isclose(turn_slope, slope * turn, rel_tol=0.0, abs_tol=1e-12):
    return False, None
  return True, turn


def observe_position_orientation_separation(
  convergence: ActionHorizonConvergenceObservation,
  *,
  lane_center_slope_per_m: float,
  model_orientation_yaw_rad: float,
) -> PositionOrientationSeparationObservation:
  """Compare position-path geometry with orientation relative to lane tangent.

  Geometry is already normalized to the hidden requested-turn sign by the
  upstream observation. This function recovers that sign only from exact
  upstream identities and uses it to normalize orientation-vs-lane yaw.

  Positive normalized yaw residual means model orientation asks for more turn
  than the lane-center tangent; negative means less turn. No epsilon, action
  correction, acceptance rule, or tuning objective is introduced.
  """
  if not isinstance(convergence, ActionHorizonConvergenceObservation) or convergence.status != 'DESCRIPTIVE_ONLY':
    return _blocked('ACTION_HORIZON_CONVERGENCE_BLOCKED')

  valid_upstream, turn = _validated_turn(convergence)
  if not valid_upstream:
    return _blocked('ACTION_HORIZON_CONVERGENCE_INVALID')
  if turn is None:
    return _blocked('TURN_UNRESOLVED')

  if not _finite(lane_center_slope_per_m) or not _finite(model_orientation_yaw_rad):
    return _blocked('NONFINITE_ORIENTATION_GEOMETRY')

  lane_slope = float(lane_center_slope_per_m)
  model_yaw = float(model_orientation_yaw_rad)
  try:
    lane_yaw = math.atan(lane_slope)
    residual = model_yaw - lane_yaw
    normalized = residual * turn
  except (ArithmeticError, OverflowError, ValueError):
    return _blocked('DERIVED_VALUE_INVALID')

  if not all(math.isfinite(value) for value in (lane_yaw, residual, normalized)):
    return _blocked('DERIVED_VALUE_INVALID')

  if normalized > 0.0:
    relation = 'MORE_TURN_THAN_LANE'
  elif normalized < 0.0:
    relation = 'LESS_TURN_THAN_LANE'
  else:
    relation = 'LANE_TANGENT_MATCH'

  geometry_state = str(convergence.convergence_state)
  offset_side = str(convergence.offset_side)
  combined_state = f'{geometry_state}_{offset_side}__{relation}'

  return PositionOrientationSeparationObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    geometry_state=geometry_state,
    offset_side=offset_side,
    turn_sign=turn,
    lane_center_slope_per_m=lane_slope,
    lane_center_yaw_rad=float(lane_yaw),
    model_orientation_yaw_rad=model_yaw,
    orientation_minus_lane_yaw_rad=float(residual),
    turn_relative_orientation_minus_lane_yaw_rad=float(normalized),
    orientation_relation=relation,
    combined_state=combined_state,
  )
