"""Offline-only separation of local path geometry and future tracking tendency.

The caller supplies an already-validated action-horizon convergence observation
and a signed, caller-owned future tracking heading-error scalar normalized to
the requested turn direction. This module only describes whether tracking error
reinforces or counteracts the current path offset. It does not integrate logs,
estimate vehicle pose, tune parameters, generate curvature, or return commands.
"""

from dataclasses import dataclass
import math

from openpilot.tools.cyber_autotune.action_horizon_convergence import (
  ActionHorizonConvergenceObservation,
)
from openpilot.tools.cyber_autotune.pixel_action_horizon_consistency import (
  _valid_action_horizon,
)


@dataclass(frozen=True)
class TrackingGeometrySeparationObservation:
  status: str
  reason: str
  geometry_state: str | None
  offset_side: str | None
  model_locally_converging: bool | None
  future_tracking_heading_error_toward_turn_rad: float | None
  future_tracking_heading_error_toward_offset_rad: float | None
  tracking_relation: str | None
  separation_state: str | None
  geometry_diverging: bool | None
  tracking_reinforces_offset: bool | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> TrackingGeometrySeparationObservation:
  return TrackingGeometrySeparationObservation(
    status='BLOCKED',
    reason=reason,
    geometry_state=None,
    offset_side=None,
    model_locally_converging=None,
    future_tracking_heading_error_toward_turn_rad=None,
    future_tracking_heading_error_toward_offset_rad=None,
    tracking_relation=None,
    separation_state=None,
    geometry_diverging=None,
    tracking_reinforces_offset=None,
  )


def _finite(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _sign(value: float) -> int:
  return 1 if value > 0.0 else -1 if value < 0.0 else 0


def observe_tracking_geometry_separation(
  model: ActionHorizonConvergenceObservation,
  *,
  future_tracking_heading_error_toward_turn_rad: float,
) -> TrackingGeometrySeparationObservation:
  """Separate local geometry state from caller-owned future tracking tendency.

  The future tracking scalar is positive when accumulated tracking curvature
  error bends more toward the current turn than desired, and negative when it
  bends less toward that turn.

  For a non-zero path offset, multiplying that scalar by the sign of the
  turn-relative path offset yields a coordinate-invariant relation:
  positive reinforces the current offset side, negative counteracts it.

  This is descriptive kinematic attribution only. It is not measured lateral
  lane position and introduces no magnitude threshold or acceptance rule.
  """
  if not isinstance(model, ActionHorizonConvergenceObservation) or model.status != 'DESCRIPTIVE_ONLY':
    return _blocked('ACTION_HORIZON_CONVERGENCE_BLOCKED')
  if not _valid_action_horizon(model):
    return _blocked('ACTION_HORIZON_CONVERGENCE_INVALID')
  if not _finite(future_tracking_heading_error_toward_turn_rad):
    return _blocked('NONFINITE_FUTURE_TRACKING')

  tracking_toward_turn = float(future_tracking_heading_error_toward_turn_rad)
  turn_relative_offset = float(model.turn_relative_offset_m)
  offset_sign = _sign(turn_relative_offset)

  if offset_sign == 0:
    tracking_toward_offset = None
    relation = 'OFFSET_UNRESOLVED'
    reinforces = None
  else:
    tracking_toward_offset = tracking_toward_turn * offset_sign
    if not math.isfinite(tracking_toward_offset):
      return _blocked('DERIVED_VALUE_INVALID')
    if tracking_toward_offset > 0.0:
      relation = 'REINFORCES_OFFSET'
      reinforces = True
    elif tracking_toward_offset < 0.0:
      relation = 'COUNTERACTS_OFFSET'
      reinforces = False
    else:
      relation = 'NEUTRAL'
      reinforces = False

  geometry_state = str(model.convergence_state)
  separation_state = f'{geometry_state}__{relation}'

  return TrackingGeometrySeparationObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    geometry_state=geometry_state,
    offset_side=str(model.offset_side),
    model_locally_converging=model.locally_converging,
    future_tracking_heading_error_toward_turn_rad=tracking_toward_turn,
    future_tracking_heading_error_toward_offset_rad=(
      None if tracking_toward_offset is None else float(tracking_toward_offset)
    ),
    tracking_relation=relation,
    separation_state=separation_state,
    geometry_diverging=geometry_state == 'DIVERGING',
    tracking_reinforces_offset=reinforces,
  )
