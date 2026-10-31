"""Controlled synthetic construction/read only; use the qualified native context."""

import hashlib
import math
import struct
from dataclasses import dataclass
from typing import Any
from weakref import WeakKeyDictionary

from . import owned_message_boundary as b
from .semantic_bridge import SemanticBridgeError, prepare_semantic_input
from .semantic_types import PreparedSemanticInput, ScalarReadback


class AdapterError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SyntheticSpec:
    stamp: b.Stamp
    settings: b.SettingsSnapshot
    previous: b.PreviousSnapshot
    request: float
    driver: float
    angle_deg: float
    lat_active: bool


@dataclass(frozen=True, slots=True)
class PreparedNativeInput:
    prepared: PreparedSemanticInput
    read_claim: str


class _Handle:
    __slots__ = ('__weakref__',)


def _frame(spec: SyntheticSpec, cc_raw: bytes, cs_raw: bytes) -> b.OwnedFrame:
    cc_sha, cs_sha = (hashlib.sha256(raw).hexdigest() for raw in (cc_raw, cs_raw))
    return b.OwnedFrame(
        'SYNTHETIC_OWNED_MESSAGES_ONLY', 'R11_C8FB9068_4134C0D1_V1',
        '098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788',
        'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY', spec.stamp,
        b.OwnedPayload(spec.stamp, 17836551423953212591, cc_raw, cc_sha),
        b.OwnedPayload(spec.stamp, 11359479080460390460, cs_raw, cs_sha),
        b.FieldLedger(spec.stamp, cc_sha, cs_sha,
                      ('CC.actuators.torque', 'CC.latActive', 'CS.out.steeringAngleDeg', 'CS.out.steeringTorque')),
        spec.settings, spec.previous)


def _validate_frame(frame: b.OwnedFrame) -> None:
    try:
        b.prepare_owned_frame(frame)
    except b.OwnedBoundaryError as error:
        raise AdapterError('ADAPTER_ENVELOPE:' + error.code) from error


def validate_spec(spec: SyntheticSpec) -> None:
    if type(spec) is not SyntheticSpec:
        raise AdapterError('ADAPTER_SPEC_TYPE')
    # Structural preflight only: these sentinel bytes are never passed to a
    # native parser. Real serialized payloads are revalidated after construction.
    _validate_frame(_frame(spec, b'preflight', b'preflight'))
    for value, bound, dyadic in [(spec.request, 1, False), (spec.driver, 1024, True), (spec.angle_deg, 180, True)]:
        if (type(value) is not float or not math.isfinite(value) or abs(value) > bound
                or (dyadic and value.as_integer_ratio()[1] > 256)):
            raise AdapterError('ADAPTER_DOMAIN')
    if type(spec.lat_active) is not bool:
        raise AdapterError('ADAPTER_DOMAIN')
    for value in (spec.request, spec.driver, spec.angle_deg):
        if type(value) is not float:
            raise AdapterError('ADAPTER_DOMAIN')
        if struct.unpack('!f', struct.pack('!f', value))[0].hex() != value.hex():
            raise AdapterError('ADAPTER_PRECISION')


class _SyntheticAdapter:
    """Private backend-bound object, single-threaded/cooperative process only."""

    def __init__(self, car: Any):
        self._car: Any = car
        self._closed = False
        self._handles: WeakKeyDictionary[_Handle, tuple[SyntheticSpec, b.OwnedFrame]] = WeakKeyDictionary()

    def _open(self) -> None:
        if self._closed:
            raise AdapterError('ADAPTER_CONTEXT_CLOSED')

    def _lookup(self, handle: _Handle) -> tuple[SyntheticSpec, b.OwnedFrame]:
        self._open()
        if type(handle) is not _Handle:
            raise AdapterError('ADAPTER_HANDLE_TYPE')
        try:
            return self._handles[handle]
        except KeyError as error:
            raise AdapterError('ADAPTER_HANDLE_UNKNOWN') from error

    def construct(self, spec: SyntheticSpec) -> _Handle:
        self._open()
        validate_spec(spec)
        try:
            cc, cs = self._car.CarControl.new_message(), self._car.CarState.new_message()
            cc.actuators.torque, cc.latActive = spec.request, spec.lat_active
            cs.steeringTorque, cs.steeringAngleDeg = spec.driver, spec.angle_deg
            if (cc.schema.node.id, cs.schema.node.id) != (17836551423953212591, 11359479080460390460):
                raise AdapterError('ADAPTER_NATIVE_SCHEMA')
            frame = _frame(spec, cc.to_bytes(), cs.to_bytes())
        except AdapterError:
            raise
        except Exception as error:
            raise AdapterError('ADAPTER_NATIVE_CONSTRUCTION') from error
        _validate_frame(frame)
        handle = _Handle()
        self._handles[handle] = spec, frame
        return handle

    def inspect(self, handle: _Handle) -> b.OwnedFrame:
        return self._lookup(handle)[1]

    def prepare(self, handle: _Handle) -> PreparedNativeInput:
        spec, frame = self._lookup(handle)
        _validate_frame(frame)
        try:
            with (self._car.CarControl.from_bytes(frame.cc.payload) as cc,
                  self._car.CarState.from_bytes(frame.cs.payload) as cs):
                readback = ScalarReadback(frame.stamp, frame.cc.payload_sha256, frame.cs.payload_sha256,
                                          'NATIVE_FLOAT32_DECLARATION', cc.actuators.torque,
                                          cs.steeringTorque, cs.steeringAngleDeg, cc.latActive)
        except Exception as error:
            raise AdapterError('ADAPTER_NATIVE_READ') from error
        values = (readback.request, readback.driver, readback.angle_deg)
        if (any(type(value) is not float for value in values)
                or [float.hex(value) for value in values] != [float.hex(spec.request), float.hex(spec.driver), float.hex(spec.angle_deg)]
                or type(readback.lat_active) is not bool or readback.lat_active is not spec.lat_active):
            raise AdapterError('ADAPTER_READBACK_MISMATCH')
        try:
            prepared = prepare_semantic_input(frame, readback)
        except SemanticBridgeError as error:
            raise AdapterError('ADAPTER_SEMANTIC:' + error.code) from error
        return PreparedNativeInput(prepared, 'INTERNALLY_CONSTRUCTED_OWNED_SYNTHETIC_BYTES_READ_WITHIN_CONTEXT')

    def close(self) -> None:
        self._closed = True
        self._handles.clear()
        self._car = None
