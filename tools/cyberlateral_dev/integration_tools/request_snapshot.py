"""Counterfactual raw request carriers, not source capture or calculator inputs."""

import re
from dataclasses import dataclass, field
from typing import cast


class RequestSnapshotError(ValueError):
    """Fixed rejection code with no input forwarding or partial result."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticRequestContextV1:
    schema_version: int
    scope: str
    source_profile: str
    capture_epoch_id: str
    controller_instance_id: str
    configuration_epoch_id: str
    clock_domain: str
    control_mode: str
    request_stage: str
    reset_generation: int
    loss_generation: int


@dataclass(frozen=True, slots=True)
class SyntheticRequestSnapshotV1:
    context: SyntheticRequestContextV1
    sequence: int
    sample_time_ns: int
    requested_binary32: bytes
    request_active: bool
    request_override: bool
    reset_since_previous: bool


@dataclass(frozen=True, slots=True)
class PreparedSyntheticRequestPairV1:
    previous: SyntheticRequestSnapshotV1
    current: SyntheticRequestSnapshotV1
    contract_id: str = field(default='CORE3_COUNTERFACTUAL_REQUEST_PAIR_V1', init=False)
    validation_claim: str = field(default='COOPERATIVE_SYNTHETIC_DECLARATION_ONLY', init=False)
    time_semantics: str = field(default='ORDER_ONLY_NO_DELTA_OR_PERIOD', init=False)
    source_identity_reauthenticated: bool = field(default=False, init=False)
    v4_payload_allowed: bool = field(default=False, init=False)
    f61_input_allowed: bool = field(default=False, init=False)
    actual_activation_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _validate_pair(self)


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise RequestSnapshotError(code)


def _text(value: object, expected: str) -> bool:
    return type(value) is str and value == expected


def _integer(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _label(value: object) -> bool:
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value) is not None


def _validate_snapshot(value: SyntheticRequestSnapshotV1) -> None:
    _need(type(value.context) is SyntheticRequestContextV1, 'REQUEST_CONTEXT_TYPE')
    context = value.context
    _need(type(context.schema_version) is int and context.schema_version == 1
          and _text(context.scope, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY'), 'REQUEST_SCOPE')
    _need(_text(context.source_profile, 'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1'), 'REQUEST_SOURCE_PROFILE')
    _need(_text(context.control_mode, 'DECLARED_TORQUE_CONTROL')
          and _text(context.request_stage, 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER')
          and (_text(context.clock_domain, 'DECLARED_LIVE_MONOTONIC_NS')
               or _text(context.clock_domain, 'DECLARED_REPLAY_RECORDED_CAN_NS')), 'REQUEST_CONTEXT_MODE')
    _need(all(_label(label) for label in (context.capture_epoch_id, context.controller_instance_id,
                                        context.configuration_epoch_id)), 'REQUEST_CONTEXT_ID')
    _need(_integer(context.reset_generation, 0, (1 << 64) - 1)
          and _integer(context.loss_generation, 0, (1 << 64) - 1), 'REQUEST_GENERATION')
    _need(_integer(value.sequence, 0, (1 << 64) - 1), 'REQUEST_SEQUENCE')
    _need(_integer(value.sample_time_ns, -(1 << 63), (1 << 63) - 1), 'REQUEST_TIME')
    raw = value.requested_binary32
    _need(type(raw) is bytes and len(raw) == 4, 'REQUEST_WORD')
    # All IEEE binary32 magnitudes <=1 are finite. Validate the raw word without
    # converting it to a numeric native value, or losing its signed-zero bit.
    _need(int.from_bytes(raw, 'big') & 0x7fffffff <= 0x3f800000, 'REQUEST_WORD')
    _need(all(type(flag) is bool for flag in (value.request_active, value.request_override,
                                            value.reset_since_previous)), 'REQUEST_FLAGS')


def _validate_pair(value: PreparedSyntheticRequestPairV1) -> None:
    _need(type(value) is PreparedSyntheticRequestPairV1, 'REQUEST_SNAPSHOT_TYPE')
    previous, current = value.previous, value.current
    _need(type(previous) is SyntheticRequestSnapshotV1 and type(current) is SyntheticRequestSnapshotV1, 'REQUEST_SNAPSHOT_TYPE')
    _validate_snapshot(previous)
    _validate_snapshot(current)
    _need(previous.context == current.context, 'REQUEST_PAIR_CONTEXT')
    _need(current.sequence == previous.sequence + 1, 'REQUEST_PAIR_SEQUENCE')
    _need(current.sample_time_ns > previous.sample_time_ns, 'REQUEST_PAIR_TIME')
    _need(not current.reset_since_previous, 'REQUEST_PAIR_RESET')


def prepare_request_pair(previous: object, current: object) -> PreparedSyntheticRequestPairV1:
    """Check a declared pair; never infer flags, origin, applied state or elapsed dt."""
    return PreparedSyntheticRequestPairV1(cast(SyntheticRequestSnapshotV1, previous),
                                        cast(SyntheticRequestSnapshotV1, current))
