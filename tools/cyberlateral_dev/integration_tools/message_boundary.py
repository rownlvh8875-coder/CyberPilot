"""Validate/copy explicit synthetic fields only: no IO, native reader or model work."""

import re
from math import isfinite

import cyberlateral_dev as p

from .message_boundary_types import (
    MessageBoundaryError,
    PreparedLateralInputV1,
    SyntheticActuatorsV1,
    SyntheticBoundaryFrameV1,
    SyntheticCarControlV1,
    SyntheticCarStateValuesV1,
    SyntheticCarStateWrapperV1,
    SyntheticPreviousV1,
)

__all__ = [
    'MessageBoundaryError', 'PreparedLateralInputV1', 'SyntheticActuatorsV1', 'SyntheticBoundaryFrameV1',
    'SyntheticCarControlV1', 'SyntheticCarStateValuesV1', 'SyntheticCarStateWrapperV1', 'SyntheticPreviousV1',
    'extract_synthetic_message',
]

CONTRACT_ID = 'F70UGZ_R13_MESSAGE_BOUNDARY_V1'
PROFILE_ID = 'R13_HYUNDAI_TORQUE_ENTRY_SYNTHETIC_V1'
SOURCE_SET_ID = 'R11_C8FB9068_4134C0D1_V1'


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise MessageBoundaryError(code)


def _text(value, expected: str) -> bool:
    return type(value) is str and value == expected


def _integer(value, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _number(value, bound: float, dyadic: bool = False) -> bool:
    return (type(value) is float and isfinite(value) and abs(value) <= bound
            and (not dyadic or value.as_integer_ratio()[1] <= 256))


def _records(frame: SyntheticBoundaryFrameV1) -> None:
    # Each owner must be exact before reading its children; never probe properties.
    _require(type(frame) is SyntheticBoundaryFrameV1, 'BOUNDARY_RECORD_TYPE')
    _require(type(frame.cc) is SyntheticCarControlV1 and type(frame.cs) is SyntheticCarStateWrapperV1
             and type(frame.previous) is SyntheticPreviousV1 and type(frame.consumed_limits) is p.Limits, 'BOUNDARY_RECORD_TYPE')
    _require(type(frame.cc.actuators) is SyntheticActuatorsV1 and type(frame.cs.out) is SyntheticCarStateValuesV1
             and type(frame.previous.model_state) is p.LateralState, 'BOUNDARY_RECORD_TYPE')


def _sequence(value) -> None:
    _require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value) is not None, 'BOUNDARY_SEQUENCE')


def _domain(frame: SyntheticBoundaryFrameV1) -> None:
    limits, previous = frame.consumed_limits, frame.previous
    state = previous.model_state
    _require(_number(frame.cc.actuators.torque, 1.0) and _number(frame.cs.out.steeringTorque, 1024.0, True)
             and _number(frame.cs.out.steeringAngleDeg, 180.0, True) and type(frame.cc.latActive) is bool, 'BOUNDARY_DOMAIN')
    _require(_integer(limits.STEER_MAX, 1, 2048)
             and all(_integer(v, 0, 64) for v in (limits.STEER_DELTA_UP, limits.STEER_DELTA_DOWN, limits.STEER_DRIVER_ALLOWANCE))
             and all(_integer(v, 0, 8) for v in (limits.STEER_DRIVER_FACTOR, limits.STEER_DRIVER_MULTIPLIER)), 'BOUNDARY_DOMAIN')
    _require(_integer(previous.source_previous_applied, -2048, 2048) and _integer(state.previous_applied, -2048, 2048)
             and _integer(previous.source_angle_counter, 0, 90) and _integer(state.angle_counter, 0, 90), 'BOUNDARY_DOMAIN')
    if frame.invocation_index == 0:
        _require(state.previous_requested is None, 'BOUNDARY_DOMAIN')
    else:
        _require(_integer(state.previous_requested, -2048, 2048), 'BOUNDARY_DOMAIN')


def extract_synthetic_message(frame: SyntheticBoundaryFrameV1) -> PreparedLateralInputV1:
    _records(frame)
    _require(type(frame.schema_version) is int and frame.schema_version == 1
             and _text(frame.scope, 'SYNTHETIC_DEVELOPMENT_ONLY')
             and _text(frame.value_representation, 'SYNTHETIC_PYTHON_BINARY64')
             and _text(frame.static_context_reference, 'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY')
             and _text(frame.consumed_settings_origin, 'EXPLICIT_SYNTHETIC_CALL_ENTRY'), 'BOUNDARY_SCOPE')
    _require(_text(frame.profile_id, PROFILE_ID) and _text(frame.source_set_id, SOURCE_SET_ID)
             and _text(p.__version__, '0.3.0'), 'BOUNDARY_SOURCE_PROFILE')
    previous, state = frame.previous, frame.previous.model_state
    _sequence(frame.sequence_id)
    _sequence(previous.sequence_id)
    _require(frame.sequence_id == previous.sequence_id, 'BOUNDARY_SEQUENCE')
    _require(_integer(frame.invocation_index, 0, 4095) and _integer(state.index, 0, 4096)
             and state.index == frame.invocation_index, 'BOUNDARY_ORDER')
    if frame.invocation_index == 0:
        _require(previous.previous_invocation_index is None, 'BOUNDARY_ORDER')
    else:
        _require(_integer(previous.previous_invocation_index, 0, 4094)
                 and previous.previous_invocation_index == frame.invocation_index - 1, 'BOUNDARY_ORDER')
    _domain(frame)
    _require(_text(previous.snapshot_stage, 'ENTRY_BEFORE_CURRENT_LIMITER')
             and previous.source_previous_applied == state.previous_applied
             and previous.source_angle_counter == state.angle_counter, 'BOUNDARY_CUSTODY')
    if frame.invocation_index == 0:
        _require(state.previous_applied == 0 and state.angle_counter == 0, 'BOUNDARY_CUSTODY')
    sample = p.LateralInput(frame.invocation_index, frame.cc.actuators.torque, frame.cs.out.steeringTorque,
                            frame.cs.out.steeringAngleDeg, frame.cc.latActive, frame.consumed_limits, 'SYNTHETIC_ONLY')
    return PreparedLateralInputV1(CONTRACT_ID, SOURCE_SET_ID, frame.sequence_id, sample, state,
                                  'SYNTHETIC_DECLARATION_ONLY', 'EXACT_SUPPLIED_BINARY64_NOT_NATIVE_ABI',
                                  'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
