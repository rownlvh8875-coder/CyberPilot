"""Closed synthetic source-shaped bridge. No IO, native reader or runtime hook."""

import hashlib
import json
import re
from dataclasses import asdict
from math import isfinite

import cyberlateral_dev as p
from cyberlateral_dev import synthetic_catalog

from .dev_bridge_types import DevBridgeError, DevBridgeResultV1, DevBridgeSessionV1, DevSourceSnapshotV1

__all__ = ['DevBridgeError', 'DevBridgeResultV1', 'DevBridgeSessionV1', 'DevSourceSnapshotV1', 'advance', 'begin_sequence', 'fixture_snapshot']

CONTRACT_ID = 'F70UGZ_R11_DEV_BRIDGE_V1'
PROFILE_ID = 'R11_HYUNDAI_TORQUE_SYNTHETIC_V1'
SOURCE_SET_ID = 'R11_C8FB9068_4134C0D1_V1'
SCOPE = 'SYNTHETIC_DEVELOPMENT_ONLY'
REPRESENTATION = 'SYNTHETIC_PYTHON_BINARY64'
CATALOG_SHA256 = '74095144882ff3977679ce92ec7dad0e7bf3f532a0cacae2cfa26f4aab0fd287'


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise DevBridgeError(code)


def _registry():
    catalog = synthetic_catalog.fixed_catalog()
    records = [{'id': s.id, 'initial_state': asdict(s.initial_state), 'samples': [asdict(x) for x in s.samples]} for s in catalog]
    raw = (json.dumps(records, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
    _require(type(p.__version__) is str and p.__version__ == '0.3.0'
             and hashlib.sha256(raw).hexdigest() == CATALOG_SHA256, 'BRIDGE_SOURCE_PROFILE')
    return {s.id: s for s in catalog}


def _sequence(sequence_id: str) -> None:
    _require(type(sequence_id) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', sequence_id) is not None, 'BRIDGE_SEQUENCE')


def _fixture(registry, fixture_id: str):
    _require(type(fixture_id) is str and fixture_id in registry, 'BRIDGE_FIXTURE')
    return registry[fixture_id]


def _offset(offset: int, size: int) -> None:
    _require(type(offset) is int and 0 <= offset < size, 'BRIDGE_ORDER')


def fixture_snapshot(fixture_id: str, offset: int, sequence_id: str) -> DevSourceSnapshotV1:
    registry = _registry()
    _sequence(sequence_id)
    fixture = _fixture(registry, fixture_id)
    _offset(offset, len(fixture.samples))
    sample = fixture.samples[offset]
    return DevSourceSnapshotV1(1, SCOPE, REPRESENTATION, PROFILE_ID, SOURCE_SET_ID, fixture_id, sequence_id,
                               offset, sample.index, sample.request, sample.driver, sample.angle_deg, sample.lat_active, sample.limits)


def begin_sequence(fixture_id: str, sequence_id: str) -> DevBridgeSessionV1:
    registry = _registry()
    _sequence(sequence_id)
    fixture = _fixture(registry, fixture_id)
    return DevBridgeSessionV1(1, SCOPE, PROFILE_ID, SOURCE_SET_ID, fixture_id, sequence_id, 0, fixture.initial_state)


def _text(value, expected: str) -> bool:
    return type(value) is str and value == expected


def _integer(value, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _float(value, bound: float, dyadic: bool = False) -> bool:
    return (type(value) is float and isfinite(value) and abs(value) <= bound
            and (not dyadic or value.as_integer_ratio()[1] <= 256))


def _same_float_bits(value, expected) -> bool:
    return type(value) is float and type(expected) is float and value.hex() == expected.hex()


def _domain(snapshot: DevSourceSnapshotV1, session: DevBridgeSessionV1) -> None:
    limits, state = snapshot.limits, session.model_state
    _require(type(limits) is p.Limits and type(state) is p.LateralState, 'BRIDGE_DOMAIN')
    _require(_float(snapshot.requested_torque, 1.0) and _float(snapshot.driver_torque_native, 1024.0, True)
             and _float(snapshot.steering_angle_deg, 180.0, True) and type(snapshot.lat_active) is bool, 'BRIDGE_DOMAIN')
    _require(_integer(limits.STEER_MAX, 1, 2048)
             and all(_integer(v, 0, 64) for v in (limits.STEER_DELTA_UP, limits.STEER_DELTA_DOWN, limits.STEER_DRIVER_ALLOWANCE))
             and all(_integer(v, 0, 8) for v in (limits.STEER_DRIVER_FACTOR, limits.STEER_DRIVER_MULTIPLIER)), 'BRIDGE_DOMAIN')
    _require(_integer(state.index, 0, 4096) and _integer(state.previous_applied, -2048, 2048)
             and _integer(state.angle_counter, 0, 90), 'BRIDGE_DOMAIN')
    if state.index == 0:
        _require(state.previous_requested is None and state.previous_applied == 0 and state.angle_counter == 0, 'BRIDGE_DOMAIN')
    else:
        _require(_integer(state.previous_requested, -2048, 2048), 'BRIDGE_DOMAIN')


def advance(snapshot: DevSourceSnapshotV1, session: DevBridgeSessionV1) -> DevBridgeResultV1:
    # Never inspect native-like objects or subclasses, even to read metadata.
    _require(type(snapshot) is DevSourceSnapshotV1 and type(session) is DevBridgeSessionV1, 'BRIDGE_RECORD_TYPE')
    _require(type(snapshot.schema_version) is int and snapshot.schema_version == 1
             and type(session.schema_version) is int and session.schema_version == 1
             and _text(snapshot.scope, SCOPE) and _text(session.scope, SCOPE)
             and _text(snapshot.value_representation, REPRESENTATION), 'BRIDGE_SCOPE')
    _require(_text(snapshot.profile_id, PROFILE_ID) and _text(session.profile_id, PROFILE_ID)
             and _text(snapshot.source_set_id, SOURCE_SET_ID) and _text(session.source_set_id, SOURCE_SET_ID), 'BRIDGE_SOURCE_PROFILE')
    registry = _registry()
    _sequence(snapshot.sequence_id)
    _sequence(session.sequence_id)
    _require(snapshot.sequence_id == session.sequence_id, 'BRIDGE_SEQUENCE')
    fixture = _fixture(registry, snapshot.fixture_id)
    _fixture(registry, session.fixture_id)
    _require(snapshot.fixture_id == session.fixture_id, 'BRIDGE_FIXTURE')
    _offset(snapshot.offset, len(fixture.samples))
    _offset(session.next_offset, len(fixture.samples))
    expected = fixture.samples[snapshot.offset]
    _require(snapshot.offset == session.next_offset and _integer(snapshot.model_index, 0, 4095)
             and snapshot.model_index == expected.index, 'BRIDGE_ORDER')
    _domain(snapshot, session)
    _require(_same_float_bits(snapshot.requested_torque, expected.request)
             and _same_float_bits(snapshot.driver_torque_native, expected.driver)
             and _same_float_bits(snapshot.steering_angle_deg, expected.angle_deg)
             and snapshot.lat_active == expected.lat_active and snapshot.limits == expected.limits, 'BRIDGE_SNAPSHOT_MISMATCH')
    try:
        previous = (fixture.initial_state if snapshot.offset == 0 else
                    p.simulate(fixture.samples[:snapshot.offset], fixture.initial_state).next_state)
    except ValueError as error:
        raise DevBridgeError('BRIDGE_MODEL_REJECTED') from error
    _require(session.model_state == previous, 'BRIDGE_STATE_MISMATCH')
    sample = p.LateralInput(snapshot.model_index, snapshot.requested_torque, snapshot.driver_torque_native,
                            snapshot.steering_angle_deg, snapshot.lat_active, snapshot.limits, 'SYNTHETIC_ONLY')
    try:
        diagnostic = p.step(sample, session.model_state)
    except ValueError as error:
        raise DevBridgeError('BRIDGE_MODEL_REJECTED') from error
    following = DevBridgeSessionV1(1, SCOPE, PROFILE_ID, SOURCE_SET_ID, session.fixture_id,
                                   session.sequence_id, snapshot.offset + 1, diagnostic.next_state)
    return DevBridgeResultV1(CONTRACT_ID, snapshot.fixture_id, snapshot.sequence_id, snapshot.offset, diagnostic, following)
