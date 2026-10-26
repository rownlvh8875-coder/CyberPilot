"""Offline-only local convergence observation at a caller-owned action horizon.

The caller supplies an already-validated recenter condition plus local
path-minus-lane offset and slope. This module classifies exact local convergence
without selecting a horizon, applying a threshold, generating curvature, tuning
parameters, or returning a vehicle command.
"""

from dataclasses import dataclass
import math

from openpilot.tools.cyber_autotune.action_geometry_alignment import _valid_condition
from openpilot.tools.cyber_autotune.recenter_condition import RecenterConditionObservation


@dataclass(frozen=True)
class ActionHorizonConvergenceObservation:
  status: str
  reason: str
  path_minus_lane_m: float | None
  path_minus_lane_slope_per_m: float | None
  turn_relative_offset_m: float | None
  turn_relative_slope_per_m: float | None
  offset_side: str | None
  convergence_state: str | None
  locally_converging: bool | None
  recentered: bool | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> ActionHorizonConvergenceObservation:
  return ActionHorizonConvergenceObservation(
    status='BLOCKED',
    reason=reason,
    path_minus_lane_m=None,
    path_minus_lane_slope_per_m=None,
    turn_relative_offset_m=None,
    turn_relative_slope_per_m=None,
    offset_side=None,
    convergence_state=None,
    locally_converging=None,
    recentered=None,
  )


def _finite(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _sign(value: float) -> int:
  return 1 if value > 0.0 else -1 if value < 0.0 else 0


def observe_action_horizon_convergence(
  condition: RecenterConditionObservation,
  *,
  path_minus_lane_m: float,
  path_minus_lane_slope_per_m: float,
) -> ActionHorizonConvergenceObservation:
  """Describe whether local path-to-lane offset is moving toward zero.

  Model/calibrated geometry and current-branch curvature use +right. Offset and
  slope are normalized by the model-action turn sign so positive offset means
  turn-inside. Local convergence itself is coordinate-invariant: a nonzero
  offset converges exactly when offset and slope have opposite signs.

  CENTER and FLAT are retained as separate exact states. No epsilon, magnitude
  threshold, promotion rule, or tuning objective is introduced.
  """
  if not isinstance(condition, RecenterConditionObservation) or condition.status != 'DESCRIPTIVE_ONLY':
    return _blocked('RECENTER_CONDITION_BLOCKED')
  if not _valid_condition(condition):
    return _blocked('RECENTER_CONDITION_INVALID')
  if not _finite(path_minus_lane_m) or not _finite(path_minus_lane_slope_per_m):
    return _blocked('NONFINITE_GEOMETRY')

  offset = float(path_minus_lane_m)
  slope = float(path_minus_lane_slope_per_m)
  turn = _sign(float(condition.model_action_curvature_1pm))
  turn_relative_offset = offset * turn
  turn_relative_slope = slope * turn

  offset_slope_product = offset * slope
  derived = (turn_relative_offset, turn_relative_slope, offset_slope_product)
  if not all(math.isfinite(value) for value in derived):
    return _blocked('DERIVED_VALUE_INVALID')

  if turn_relative_offset > 0.0:
    side = 'INSIDE'
  elif turn_relative_offset < 0.0:
    side = 'OUTSIDE'
  else:
    side = 'CENTER'

  if offset == 0.0:
    state = 'CENTER'
  elif slope == 0.0:
    state = 'FLAT'
  elif offset_slope_product < 0.0:
    state = 'CONVERGING'
  else:
    state = 'DIVERGING'

  return ActionHorizonConvergenceObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    path_minus_lane_m=offset,
    path_minus_lane_slope_per_m=slope,
    turn_relative_offset_m=float(turn_relative_offset),
    turn_relative_slope_per_m=float(turn_relative_slope),
    offset_side=side,
    convergence_state=state,
    locally_converging=state == 'CONVERGING',
    recentered=condition.recentered,
  )
