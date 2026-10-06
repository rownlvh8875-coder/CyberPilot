"""Offline-only attribution for path recenter conditions.

This module combines an already-computed recenter observation with existing
model-action and controls-state curvature scalars. It does not generate a path,
curvature request, tune, Params value, CAN message, or vehicle command.
"""
from dataclasses import dataclass
import math

from openpilot.tools.cyber_autotune.recenter_intent import RecenterIntentObservation


@dataclass(frozen=True)
class RecenterConditionObservation:
  status: str
  reason: str
  future_station_m: float | None
  start_offset_m: float | None
  future_offset_m: float | None
  start_turn_relative_offset_m: float | None
  start_turn_relative_state: str | None
  model_action_curvature_1pm: float | None
  controls_desired_curvature_1pm: float | None
  current_curvature_1pm: float | None
  tracking_toward_turn_1pm: float | None
  tracking_abs_error_1pm: float | None
  tracking_state: str | None
  v_ego_mps: float | None
  recentered: bool | None
  same_side: bool | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> RecenterConditionObservation:
  return RecenterConditionObservation(
    status='BLOCKED',
    reason=reason,
    future_station_m=None,
    start_offset_m=None,
    future_offset_m=None,
    start_turn_relative_offset_m=None,
    start_turn_relative_state=None,
    model_action_curvature_1pm=None,
    controls_desired_curvature_1pm=None,
    current_curvature_1pm=None,
    tracking_toward_turn_1pm=None,
    tracking_abs_error_1pm=None,
    tracking_state=None,
    v_ego_mps=None,
    recentered=None,
    same_side=None,
  )


def _finite_number(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _sign(value: float) -> int:
  return 1 if value > 0.0 else -1 if value < 0.0 else 0


def _valid_recenter(observation: RecenterIntentObservation) -> bool:
  if not isinstance(observation, RecenterIntentObservation):
    return False
  if observation.status != 'DESCRIPTIVE_ONLY' or observation.reason != 'ok':
    return False
  if (
    type(observation.sample_count) is not int or observation.sample_count <= 0
    or observation.readiness != 'NOT_READY'
    or observation.vehicle_status != 'REAL_VEHICLE_UNVERIFIED'
    or observation.safety_status != 'VEHICLE_ACTIVATION_BLOCKED'
    or observation.vehicle_activation_allowed is not False
  ):
    return False

  required = (
    observation.start_station_m,
    observation.future_station_m,
    observation.start_offset_m,
    observation.future_offset_m,
    observation.start_abs_offset_m,
    observation.future_abs_offset_m,
    observation.abs_offset_delta_m,
  )
  if not all(_finite_number(value) for value in required):
    return False

  start_station = float(observation.start_station_m)
  future_station = float(observation.future_station_m)
  start_offset = float(observation.start_offset_m)
  future_offset = float(observation.future_offset_m)
  start_abs = float(observation.start_abs_offset_m)
  future_abs = float(observation.future_abs_offset_m)
  delta = float(observation.abs_offset_delta_m)
  if future_station <= start_station:
    return False
  if not math.isclose(start_abs, abs(start_offset), rel_tol=0.0, abs_tol=1e-12):
    return False
  if not math.isclose(future_abs, abs(future_offset), rel_tol=0.0, abs_tol=1e-12):
    return False
  if not math.isclose(delta, future_abs - start_abs, rel_tol=0.0, abs_tol=1e-12):
    return False

  ratio = observation.retained_abs_offset_fraction
  if start_abs == 0.0:
    if ratio is not None:
      return False
  else:
    if not _finite_number(ratio):
      return False
    if not math.isclose(float(ratio), future_abs / start_abs, rel_tol=1e-12, abs_tol=1e-12):
      return False

  expected_same_side = start_offset * future_offset > 0.0
  expected_recentered = future_abs < start_abs
  return (
    type(observation.recentered) is bool
    and type(observation.same_side) is bool
    and observation.same_side is expected_same_side
    and observation.recentered is expected_recentered
  )


def observe_recenter_condition(
  recenter: RecenterIntentObservation,
  *,
  model_action_curvature_1pm: float,
  controls_desired_curvature_1pm: float,
  current_curvature_1pm: float,
  v_ego_mps: float,
) -> RecenterConditionObservation:
  """Describe turn-relative start side and tracking sign for a recenter result.

  Model/calibrated geometry uses +y to the right. In the current control
  convention, positive desired curvature is a right turn. Therefore
  start_offset * sign(action curvature) is positive when the model path is
  on the inside of the requested turn.

  Tracking is normalized similarly: positive means current curvature has more
  magnitude toward the requested turn than controlsState.desiredCurvature
  (OVER), negative means less (UNDER). These are descriptive signs only.
  """
  if not isinstance(recenter, RecenterIntentObservation) or recenter.status != 'DESCRIPTIVE_ONLY':
    return _blocked('RECENTER_OBSERVATION_BLOCKED')
  if not _valid_recenter(recenter):
    return _blocked('RECENTER_OBSERVATION_INVALID')

  values = (
    model_action_curvature_1pm,
    controls_desired_curvature_1pm,
    current_curvature_1pm,
    v_ego_mps,
  )
  if not all(_finite_number(value) for value in values):
    return _blocked('NONFINITE_INPUT')

  action = float(model_action_curvature_1pm)
  desired = float(controls_desired_curvature_1pm)
  current = float(current_curvature_1pm)
  speed = float(v_ego_mps)

  if speed < 0.0:
    return _blocked('INVALID_SPEED')
  action_sign = _sign(action)
  desired_sign = _sign(desired)
  if action_sign == 0:
    return _blocked('ACTION_TURN_UNRESOLVED')
  if desired_sign == 0:
    return _blocked('CONTROL_TURN_UNRESOLVED')
  if action_sign != desired_sign:
    return _blocked('ACTION_CONTROL_SIGN_MISMATCH')

  start_offset = float(recenter.start_offset_m)
  future_offset = float(recenter.future_offset_m)
  turn_relative_start = start_offset * action_sign
  tracking_toward_turn = (current - desired) * desired_sign
  tracking_abs_error = abs(current - desired)

  derived = (turn_relative_start, tracking_toward_turn, tracking_abs_error)
  if not all(math.isfinite(value) for value in derived):
    return _blocked('DERIVED_VALUE_INVALID')

  if turn_relative_start > 0.0:
    start_state = 'INSIDE'
  elif turn_relative_start < 0.0:
    start_state = 'OUTSIDE'
  else:
    start_state = 'CENTER'

  if tracking_toward_turn > 0.0:
    tracking_state = 'OVER'
  elif tracking_toward_turn < 0.0:
    tracking_state = 'UNDER'
  else:
    tracking_state = 'NEUTRAL'

  return RecenterConditionObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    future_station_m=float(recenter.future_station_m),
    start_offset_m=start_offset,
    future_offset_m=future_offset,
    start_turn_relative_offset_m=float(turn_relative_start),
    start_turn_relative_state=start_state,
    model_action_curvature_1pm=action,
    controls_desired_curvature_1pm=desired,
    current_curvature_1pm=current,
    tracking_toward_turn_1pm=float(tracking_toward_turn),
    tracking_abs_error_1pm=float(tracking_abs_error),
    tracking_state=tracking_state,
    v_ego_mps=speed,
    recentered=recenter.recentered,
    same_side=recenter.same_side,
  )
