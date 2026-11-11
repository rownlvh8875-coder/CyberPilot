"""Exact bounded synthetic recording bytes; no actual log or vehicle interface."""

import json
import re
from dataclasses import asdict
from typing import Any, cast

from .limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
from .offline_call_recorder import FinishedSyntheticRecordingV1, RecorderError, _validate_finished
from .request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1


def encode_recording(recording: object) -> bytes:
    checked = _validate_finished(recording)
    payload = asdict(checked)
    for frame in payload['records']:
        request = frame['request']
        request['requested_binary32_hex'] = request.pop('requested_binary32').hex()
        for name in ('sequence', 'sample_time_ns'):
            request[name] = str(request[name])
        for name in ('reset_generation', 'loss_generation'):
            request['context'][name] = str(request['context'][name])
    payload['gates'] = {'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL',
        'actual_r': None, 'T2': None, 'vehicle_scale': None,
        'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED'}
    return (json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _mapping(value: object) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError('shape')
    return cast(dict[str, Any], value).copy()


def _decimal(value: object) -> int:
    if type(value) is not str or re.fullmatch(r'-?(0|[1-9][0-9]{0,19})', value) is None:
        raise ValueError('integer token')
    return int(value)


def _request(value: object) -> SyntheticRequestSnapshotV1:
    data = _mapping(value)
    word = data.pop('requested_binary32_hex')
    if type(word) is not str or re.fullmatch('[0-9a-f]{8}', word) is None:
        raise ValueError('word')
    context = _mapping(data.pop('context'))
    for name in ('reset_generation', 'loss_generation'):
        context[name] = _decimal(context[name])
    for name in ('sequence', 'sample_time_ns'):
        data[name] = _decimal(data[name])
    return SyntheticRequestSnapshotV1(context=SyntheticRequestContextV1(**context),
        requested_binary32=bytes.fromhex(word), **data)


def _frame(value: object) -> SyntheticLimiterSnapshotV1:
    data = _mapping(value)
    request = _request(data.pop('request'))
    settings = SyntheticConsumedSettingsV1(**_mapping(data.pop('settings')))
    return SyntheticLimiterSnapshotV1(request=request, settings=settings, **data)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('duplicate')
        result[name] = value
    return result


def _constant(_value: str) -> None:
    raise ValueError('nonfinite')


def decode_recording(raw: object) -> FinishedSyntheticRecordingV1:
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= 262144:
            raise ValueError('size/type')
        data = _mapping(json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_constant))
        records = data['records']
        if type(records) is not list or not 2 <= len(records) <= 128:
            raise ValueError('records')
        result = FinishedSyntheticRecordingV1(tuple(_frame(frame) for frame in records))
        if encode_recording(result) != raw:
            raise ValueError('noncanonical/metadata')
        return result
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        raise RecorderError('RECORDER_SERIALIZATION') from None
