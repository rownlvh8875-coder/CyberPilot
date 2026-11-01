"""Opaque immutable synthetic envelopes; structural checks, NOT a native decoder."""

import hashlib
import re
from dataclasses import dataclass


class OwnedBoundaryError(ValueError):
    """Stable rejection code, no partial output or fallback."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class Stamp:
    sequence_id: str
    invocation_index: int
    capture_id: str


@dataclass(frozen=True, slots=True)
class OwnedPayload:
    stamp: Stamp
    schema_id: int
    payload: bytes
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class FieldLedger:
    stamp: Stamp
    cc_sha256: str
    cs_sha256: str
    written_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    stamp: Stamp
    steer_max: int
    delta_up: int
    delta_down: int
    driver_allowance: int
    driver_factor: int
    driver_multiplier: int


@dataclass(frozen=True, slots=True)
class PreviousSnapshot:
    stamp: Stamp
    previous_invocation_index: int | None
    source_previous_applied: int
    source_angle_counter: int
    previous_applied: int
    angle_counter: int
    previous_requested: int | None
    stage: str


@dataclass(frozen=True, slots=True)
class OwnedFrame:
    scope: str
    source_set_id: str
    schema_sha256: str
    static_context_reference: str
    stamp: Stamp
    cc: OwnedPayload
    cs: OwnedPayload
    ledger: FieldLedger
    settings: SettingsSnapshot
    previous: PreviousSnapshot


@dataclass(frozen=True, slots=True)
class PreparedOwnedFrame:
    contract_id: str
    frame: OwnedFrame
    custody_claim: str
    precision_claim: str
    time_semantics: str


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise OwnedBoundaryError(code)


def _text(value, expected: str) -> bool:
    return type(value) is str and value == expected


def _integer(value, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _label(value) -> bool:
    return type(value) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}', value) is not None


def _payload(value: OwnedPayload) -> None:
    _require(type(value.payload) is bytes and 1 <= len(value.payload) <= 65536, 'OWNED_PAYLOAD')
    _require(type(value.payload_sha256) is str and re.fullmatch('[0-9a-f]{64}', value.payload_sha256) is not None
             and hashlib.sha256(value.payload).hexdigest() == value.payload_sha256, 'OWNED_PAYLOAD')


def prepare_owned_frame(frame: OwnedFrame) -> PreparedOwnedFrame:
    _require(type(frame) is OwnedFrame, 'OWNED_RECORD_TYPE')
    _require(type(frame.cc) is OwnedPayload and type(frame.cs) is OwnedPayload
             and type(frame.ledger) is FieldLedger and type(frame.settings) is SettingsSnapshot
             and type(frame.previous) is PreviousSnapshot, 'OWNED_RECORD_TYPE')
    stamps = (frame.stamp, frame.cc.stamp, frame.cs.stamp, frame.ledger.stamp, frame.settings.stamp, frame.previous.stamp)
    _require(all(type(stamp) is Stamp for stamp in stamps), 'OWNED_RECORD_TYPE')
    _require(_text(frame.scope, 'SYNTHETIC_OWNED_MESSAGES_ONLY')
             and _text(frame.source_set_id, 'R11_C8FB9068_4134C0D1_V1')
             and _text(frame.schema_sha256, '098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788')
             and _text(frame.static_context_reference, 'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY'), 'OWNED_SCOPE')
    for stamp in stamps:
        _require(_label(stamp.sequence_id) and _integer(stamp.invocation_index, 0, 4095) and _label(stamp.capture_id), 'OWNED_STAMP')
    _require(all(stamp == frame.stamp for stamp in stamps), 'OWNED_STAMP')
    _require(type(frame.cc.schema_id) is int and frame.cc.schema_id == 17836551423953212591
             and type(frame.cs.schema_id) is int and frame.cs.schema_id == 11359479080460390460, 'OWNED_SCHEMA')
    _payload(frame.cc)
    _payload(frame.cs)
    ledger = frame.ledger
    _require(type(ledger.cc_sha256) is str and ledger.cc_sha256 == frame.cc.payload_sha256
             and type(ledger.cs_sha256) is str and ledger.cs_sha256 == frame.cs.payload_sha256
             and type(ledger.written_fields) is tuple and all(type(value) is str for value in ledger.written_fields)
             and ledger.written_fields == ('CC.actuators.torque', 'CC.latActive', 'CS.out.steeringAngleDeg', 'CS.out.steeringTorque'),
             'OWNED_FIELD_LEDGER')
    settings = frame.settings
    _require(_integer(settings.steer_max, 1, 2048) and _integer(settings.delta_up, 0, 64)
             and _integer(settings.delta_down, 0, 64) and _integer(settings.driver_allowance, 0, 64)
             and _integer(settings.driver_factor, 0, 8) and _integer(settings.driver_multiplier, 0, 8), 'OWNED_SETTINGS')
    previous = frame.previous
    _require(_text(previous.stage, 'ENTRY_BEFORE_CURRENT_LIMITER')
             and _integer(previous.source_previous_applied, -2048, 2048) and _integer(previous.previous_applied, -2048, 2048)
             and _integer(previous.source_angle_counter, 0, 90) and _integer(previous.angle_counter, 0, 90)
             and previous.source_previous_applied == previous.previous_applied
             and previous.source_angle_counter == previous.angle_counter, 'OWNED_PREVIOUS')
    if frame.stamp.invocation_index == 0:
        _require(previous.previous_invocation_index is None and previous.previous_requested is None
                 and previous.previous_applied == 0 and previous.angle_counter == 0, 'OWNED_PREVIOUS')
    else:
        _require(_integer(previous.previous_invocation_index, 0, 4094)
                 and previous.previous_invocation_index == frame.stamp.invocation_index - 1
                 and _integer(previous.previous_requested, -2048, 2048), 'OWNED_PREVIOUS')
    return PreparedOwnedFrame('F70UGZ_R20_OWNED_SYNTHETIC_ENVELOPE_V1', frame, 'STRUCTURAL_SYNTHETIC_DECLARATION_ONLY',
                              'OPAQUE_OWNED_WIRE_BYTES_NO_DECODE', 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
