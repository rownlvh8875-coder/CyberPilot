"""Counterfactual software state/settings links, never limiter arithmetic or capture."""

from dataclasses import dataclass, field
from typing import cast

from .request_snapshot import (
    PreparedSyntheticRequestPairV1,
    RequestSnapshotError,
    SyntheticRequestSnapshotV1,
    prepare_request_pair,
)


class LimiterSnapshotError(ValueError):
    """Fixed diagnostic code, no raw input or partial result."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticConsumedSettingsV1:
    request_scale: int
    limiter_scale: int
    delta_up: int
    delta_down: int
    driver_allowance: int
    driver_factor: int
    driver_multiplier: int


@dataclass(frozen=True, slots=True)
class SyntheticLimiterSnapshotV1:
    request: SyntheticRequestSnapshotV1
    settings: SyntheticConsumedSettingsV1
    state_stage: str
    settings_origin: str
    limited_state_at_entry: int
    saved_limited_state: int
    angle_counter_at_entry: int
    saved_angle_counter: int
    inactive_gate_active: bool


@dataclass(frozen=True, slots=True)
class PreparedSyntheticLimiterPairV1:
    previous: SyntheticLimiterSnapshotV1
    current: SyntheticLimiterSnapshotV1
    request_pair: PreparedSyntheticRequestPairV1 = field(init=False)
    contract_id: str = field(default='CORE4_COUNTERFACTUAL_LIMITER_PAIR_V1', init=False)
    validation_claim: str = field(default='DECLARED_STATE_LINKS_NOT_LIMITER_ARITHMETIC_OR_SOURCE_PROOF', init=False)
    state_link_scope: str = field(default='PREVIOUS_SAVED_TO_CURRENT_ENTRY_ONLY_NOT_PREHISTORY', init=False)
    source_identity_reauthenticated: bool = field(default=False, init=False)
    model_input_allowed: bool = field(default=False, init=False)
    v4_payload_allowed: bool = field(default=False, init=False)
    f61_input_allowed: bool = field(default=False, init=False)
    actual_activation_allowed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        request_pair = _validate_pair(self)
        object.__setattr__(self, 'request_pair', request_pair)


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise LimiterSnapshotError(code)


def _integer(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _validate_frame(frame: SyntheticLimiterSnapshotV1) -> None:
    _need(type(frame.state_stage) is str and frame.state_stage == 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE'
          and type(frame.settings_origin) is str and frame.settings_origin == 'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS',
          'LIMITER_DECLARATION')
    settings = frame.settings
    _need(type(settings) is SyntheticConsumedSettingsV1, 'LIMITER_SETTINGS_TYPE')
    _need(_integer(settings.request_scale, 1, 2048) and _integer(settings.limiter_scale, 1, 2048)
          and all(_integer(value, 0, 64) for value in (settings.delta_up, settings.delta_down, settings.driver_allowance))
          and all(_integer(value, 0, 8) for value in (settings.driver_factor, settings.driver_multiplier)),
          'LIMITER_SETTINGS_DOMAIN')
    _need(settings.request_scale == settings.limiter_scale, 'LIMITER_SCALE_MISMATCH')
    _need(_integer(frame.limited_state_at_entry, -2048, 2048)
          and _integer(frame.saved_limited_state, -2048, 2048), 'LIMITER_STATE_DOMAIN')
    _need(_integer(frame.angle_counter_at_entry, 0, 90)
          and _integer(frame.saved_angle_counter, 0, 90), 'LIMITER_COUNTER_DOMAIN')
    _need(type(frame.inactive_gate_active) is bool, 'LIMITER_GATE_FLAG')
    _need(frame.inactive_gate_active or frame.saved_limited_state == 0, 'LIMITER_INACTIVE_STATE')


def _validate_pair(value: PreparedSyntheticLimiterPairV1) -> PreparedSyntheticRequestPairV1:
    _need(type(value) is PreparedSyntheticLimiterPairV1, 'LIMITER_SNAPSHOT_TYPE')
    previous, current = value.previous, value.current
    _need(type(previous) is SyntheticLimiterSnapshotV1 and type(current) is SyntheticLimiterSnapshotV1, 'LIMITER_SNAPSHOT_TYPE')
    try:
        request_pair = prepare_request_pair(previous.request, current.request)
    except RequestSnapshotError as error:
        raise LimiterSnapshotError('LIMITER_REQUEST:' + error.code) from error
    _validate_frame(previous)
    _validate_frame(current)
    _need(previous.settings == current.settings, 'LIMITER_PAIR_SETTINGS')
    _need(previous.saved_limited_state == current.limited_state_at_entry, 'LIMITER_PAIR_STATE_LINK')
    _need(previous.saved_angle_counter == current.angle_counter_at_entry, 'LIMITER_PAIR_COUNTER_LINK')
    return request_pair


def prepare_limiter_pair(previous: object, current: object) -> PreparedSyntheticLimiterPairV1:
    """Preserve distinct declared roles; never calculate requests, limits or policy."""
    return PreparedSyntheticLimiterPairV1(cast(SyntheticLimiterSnapshotV1, previous),
                                        cast(SyntheticLimiterSnapshotV1, current))
