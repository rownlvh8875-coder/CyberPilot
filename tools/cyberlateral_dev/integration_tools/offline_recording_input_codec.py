"""Canonical complete synthetic recording inputs;compatibility only,never execution."""

import json
from math import isfinite

from .offline_recording_codec import _constant, _mapping, _unique, decode_recording, encode_recording
from .offline_recording_preflight import SyntheticRecordingInputPreflightV1, preflight_recording_input
from .synthetic_model_input import SyntheticModelContextV1

_HEADER = {'schema_version': 1, 'contract_id': 'CORE55_COUNTERFACTUAL_RECORDING_INPUT_V1',
    'scope': 'COUNTERFACTUAL_RECORDING_INPUT_ONLY', 'source_identity_reauthenticated': False,
    'model_input_allowed': False, 'v4_payload_allowed': False, 'f61_input_allowed': False, 'actual_activation_allowed': False}
_CONTEXT_KEYS = {'scope', 'model_index', 'previous_integer_request', 'current_driver_hex', 'current_angle_deg_hex'}


class RecordingInputCodecError(ValueError):
    """Fixed structural wire rejection,not raw data or a semantic-error rewrite."""

    def __init__(self):
        self.code = 'RECORDING_INPUT_SERIALIZATION'
        super().__init__(self.code)


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _serialize(checked: SyntheticRecordingInputPreflightV1) -> bytes:
    contexts = []
    for c in checked.contexts:
        driver, angle = c.current_driver, c.current_angle_deg
        assert type(driver) is float and type(angle) is float  # Already enforced by CORE46/CORE5;also narrow for static checking.
        contexts.append({'scope': c.scope, 'model_index': c.model_index, 'previous_integer_request': c.previous_integer_request,
                         'current_driver_hex': driver.hex(), 'current_angle_deg_hex': angle.hex()})
    raw = _canonical({**_HEADER, 'recording_json': encode_recording(checked.recording).decode('utf-8'), 'contexts': contexts})
    if len(raw) > 1048576:
        raise RecordingInputCodecError()
    return raw


def encode_recording_input(recording: object, contexts: object) -> bytes:
    """Revalidate all explicit declarations and serialize;no model/reference step."""
    return _serialize(preflight_recording_input(recording, contexts))


def _float_hex(value: object) -> float:
    if type(value) is not str or not 0 < len(value) <= 32:
        raise ValueError('float wire type/size')
    result = float.fromhex(value)
    if not isfinite(result) or result.hex() != value:
        raise ValueError('float wire encoding')
    return result


def _context(value: object) -> SyntheticModelContextV1:
    data = _mapping(value)
    if set(data) != _CONTEXT_KEYS:
        raise ValueError('context shape')
    return SyntheticModelContextV1(data['scope'], data['model_index'], data['previous_integer_request'],
        _float_hex(data['current_driver_hex']), _float_hex(data['current_angle_deg_hex']))


def decode_recording_input(raw: object) -> SyntheticRecordingInputPreflightV1:
    """Decode exact canonical input bytes,then CORE46 semantic preflight without steps."""
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= 1048576:
            raise ValueError('raw type/size')
        data = _mapping(json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_constant))
        if _canonical(data) != raw or set(data) != set(_HEADER) | {'recording_json', 'contexts'}:
            raise ValueError('outer canonical shape')
        if not all(type(data[key]) is type(value) and data[key] == value for key, value in _HEADER.items()):
            raise ValueError('outer metadata')
        if type(data['recording_json']) is not str:
            raise ValueError('recording text')
        recording = decode_recording(data['recording_json'].encode('utf-8'))
        rows = data['contexts']
        if type(rows) is not list or not 1 <= len(rows) <= 127:
            raise ValueError('context container/count')
        contexts = tuple(_context(row) for row in rows)
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        raise RecordingInputCodecError() from None
    return preflight_recording_input(recording, contexts)
