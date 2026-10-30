"""Closed synthetic source-shaped bridge. No IO, native reader or runtime hook."""

import hashlib
import json
import re
from dataclasses import asdict

import cyberlateral_dev as p
from cyberlateral_dev import synthetic_catalog

from .dev_bridge_types import DevBridgeError, DevBridgeResultV1, DevBridgeSessionV1, DevSourceSnapshotV1

__all__ = ['DevBridgeError', 'DevBridgeResultV1', 'DevBridgeSessionV1', 'DevSourceSnapshotV1', 'begin_sequence', 'fixture_snapshot']

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
