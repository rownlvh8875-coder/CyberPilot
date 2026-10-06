"""Offline-only comparison of model action with local path/lane curvature.

This diagnostic consumes an already-validated recenter-condition observation
and caller-owned local geometric curvatures. It only reports relative
relationships; it never generates a path, curvature request, tune, Params
value, CAN message, or vehicle command.
"""

from dataclasses import dataclass
import math

from openpilot.tools.cyber_autotune.recenter_condition import RecenterConditionObservation


@dataclass(frozen=True)
class ActionGeometryAlignmentObservation:
  status: str
  reason: str
  path_curvature_1pm: float | None
  lane_center_curvature_1pm: float | None
  action_lane_turn_excess_1pm: float | None
  path_lane_turn_excess_1pm: float | None
  action_path_turn_excess_1pm: float | None
  controls_lane_turn_excess_1pm: float | None
  controls_path_turn_excess_1pm: float | None
  action_abs_error_to_path_1pm: float | None
  action_abs_error_to_lane_1pm: float | None
  controls_abs_error_to_path_1pm: float | None
  controls_abs_error_to_lane_1pm: float | None
  action_reference_state: str | None
  controls_reference_state: str | None
  path_vs_lane_turn_state: str | None
  recentered: bool | None
  readiness: str = 'NOT_READY'
  vehicle_status: str = 'REAL_VEHICLE_UNVERIFIED'
  safety_status: str = 'VEHICLE_ACTIVATION_BLOCKED'
  vehicle_activation_allowed: bool = False


def _blocked(reason: str) -> ActionGeometryAlignmentObservation:
  return ActionGeometryAlignmentObservation(
    status='BLOCKED',
    reason=reason,
    path_curvature_1pm=None,
    lane_center_curvature_1pm=None,
    action_lane_turn_excess_1pm=None,
    path_lane_turn_excess_1pm=None,
    action_path_turn_excess_1pm=None,
    controls_lane_turn_excess_1pm=None,
    controls_path_turn_excess_1pm=None,
    action_abs_error_to_path_1pm=None,
    action_abs_error_to_lane_1pm=None,
    controls_abs_error_to_path_1pm=None,
    controls_abs_error_to_lane_1pm=None,
    action_reference_state=None,
    controls_reference_state=None,
    path_vs_lane_turn_state=None,
    recentered=None,
  )


def _finite(value) -> bool:
  return type(value) in (int, float) and math.isfinite(value)


def _sign(value: float) -> int:
  return 1 if value > 0.0 else -1 if value < 0.0 else 0


def _reference_state(reference: float, path: float, lane: float) -> str:
  path_error = abs(reference - path)
  lane_error = abs(reference - lane)
  if path_error < lane_error:
    return 'PATH_CLOSER'
  if path_error > lane_error:
    return 'LANE_CLOSER'
  return 'EQUAL_DISTANCE'


def _valid_condition(condition: RecenterConditionObservation) -> bool:
  if not isinstance(condition, RecenterConditionObservation):
    return False
  if condition.status != 'DESCRIPTIVE_ONLY' or condition.reason != 'ok':
    return False
  if (
    condition.readiness != 'NOT_READY'
    or condition.vehicle_status != 'REAL_VEHICLE_UNVERIFIED'
    or condition.safety_status != 'VEHICLE_ACTIVATION_BLOCKED'
    or condition.vehicle_activation_allowed is not False
  ):
    return False

  required = (
    condition.future_station_m,
    condition.start_offset_m,
    condition.future_offset_m,
    condition.start_turn_relative_offset_m,
    condition.model_action_curvature_1pm,
    condition.controls_desired_curvature_1pm,
    condition.current_curvature_1pm,
    condition.tracking_toward_turn_1pm,
    condition.tracking_abs_error_1pm,
    condition.v_ego_mps,
  )
  if not all(_finite(value) for value in required):
    return False

  action = float(condition.model_action_curvature_1pm)
  desired = float(condition.controls_desired_curvature_1pm)
  current = float(condition.current_curvature_1pm)
  speed = float(condition.v_ego_mps)
  action_sign = _sign(action)
  desired_sign = _sign(desired)
  if action_sign == 0 or desired_sign == 0 or action_sign != desired_sign or speed < 0.0:
    return False

  start_offset = float(condition.start_offset_m)
  future_offset = float(condition.future_offset_m)
  turn_relative_start = start_offset * action_sign
  tracking_toward_turn = (current - desired) * desired_sign
  tracking_abs_error = abs(current - desired)

  if not math.isclose(
    float(condition.start_turn_relative_offset_m), turn_relative_start,
    rel_tol=0.0, abs_tol=1e-12,
  ):
    return False
  if not math.isclose(
    float(condition.tracking_toward_turn_1pm), tracking_toward_turn,
    rel_tol=0.0, abs_tol=1e-12,
  ):
    return False
  if not math.isclose(
    float(condition.tracking_abs_error_1pm), tracking_abs_error,
    rel_tol=0.0, abs_tol=1e-12,
  ):
    return False

  expected_start_state = (
    'INSIDE' if turn_relative_start > 0.0
    else 'OUTSIDE' if turn_relative_start < 0.0
    else 'CENTER'
  )
  expected_tracking_state = (
    'OVER' if tracking_toward_turn > 0.0
    else 'UNDER' if tracking_toward_turn < 0.0
    else 'NEUTRAL'
  )
  expected_same_side = start_offset * future_offset > 0.0
  expected_recentered = abs(future_offset) < abs(start_offset)
  if float(condition.future_station_m) <= 0.0:
    return False

  return (
    condition.start_turn_relative_state == expected_start_state
    and condition.tracking_state == expected_tracking_state
    and type(condition.recentered) is bool
    and type(condition.same_side) is bool
    and condition.recentered is expected_recentered
    and condition.same_side is expected_same_side
  )


def observe_action_geometry_alignment(
  condition: RecenterConditionObservation,
  *,
  path_curvature_1pm: float,
  lane_center_curvature_1pm: float,
) -> ActionGeometryAlignmentObservation:
  """Describe model-action alignment with caller-owned local path/lane geometry.

  Model/calibrated geometry y and current-branch curvature are positive to the
  right. Results are normalized by model-action turn sign, so positive excess
  means more curvature toward the requested turn.

  Closer-to-path/lane classifications use exact absolute-distance comparison
  only. They are descriptive labels, not acceptance thresholds.
  """
  if not isinstance(condition, RecenterConditionObservation) or condition.status != 'DESCRIPTIVE_ONLY':
    return _blocked('RECENTER_CONDITION_BLOCKED')
  if not _valid_condition(condition):
    return _blocked('RECENTER_CONDITION_INVALID')
  if not _finite(path_curvature_1pm) or not _finite(lane_center_curvature_1pm):
    return _blocked('NONFINITE_GEOMETRY')

  path = float(path_curvature_1pm)
  lane = float(lane_center_curvature_1pm)
  action = float(condition.model_action_curvature_1pm)
  controls = float(condition.controls_desired_curvature_1pm)
  turn = _sign(action)

  action_lane = (action - lane) * turn
  path_lane = (path - lane) * turn
  action_path = (action - path) * turn
  controls_lane = (controls - lane) * turn
  controls_path = (controls - path) * turn
  action_path_error = abs(action - path)
  action_lane_error = abs(action - lane)
  controls_path_error = abs(controls - path)
  controls_lane_error = abs(controls - lane)

  derived = (
    action_lane,
    path_lane,
    action_path,
    controls_lane,
    controls_path,
    action_path_error,
    action_lane_error,
    controls_path_error,
    controls_lane_error,
  )
  if not all(math.isfinite(value) for value in derived):
    return _blocked('DERIVED_VALUE_INVALID')

  if path_lane > 0.0:
    path_state = 'MORE_TURN_THAN_LANE'
  elif path_lane < 0.0:
    path_state = 'LESS_TURN_THAN_LANE'
  else:
    path_state = 'LANE_MATCH'

  return ActionGeometryAlignmentObservation(
    status='DESCRIPTIVE_ONLY',
    reason='ok',
    path_curvature_1pm=path,
    lane_center_curvature_1pm=lane,
    action_lane_turn_excess_1pm=float(action_lane),
    path_lane_turn_excess_1pm=float(path_lane),
    action_path_turn_excess_1pm=float(action_path),
    controls_lane_turn_excess_1pm=float(controls_lane),
    controls_path_turn_excess_1pm=float(controls_path),
    action_abs_error_to_path_1pm=float(action_path_error),
    action_abs_error_to_lane_1pm=float(action_lane_error),
    controls_abs_error_to_path_1pm=float(controls_path_error),
    controls_abs_error_to_lane_1pm=float(controls_lane_error),
    action_reference_state=_reference_state(action, path, lane),
    controls_reference_state=_reference_state(controls, path, lane),
    path_vs_lane_turn_state=path_state,
    recentered=condition.recentered,
  )
