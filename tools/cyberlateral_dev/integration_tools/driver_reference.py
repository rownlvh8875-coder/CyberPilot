"""Preregistered complete literals; representation conversion only, no model math."""

import hashlib
import json
from pathlib import Path

REFERENCE_PATH = Path(__file__).resolve().parents[1] / 'reference/r25_driver_expected_v1.json'
REFERENCE_SHA256 = '21de9d95fa3e45dd03fe5ac8da0505a4ea94d233dc81d21ba65d741573ef1fa7'


def load_reference() -> dict:
    raw = REFERENCE_PATH.read_bytes()
    if REFERENCE_PATH.is_symlink() or hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError('DRIVER_REFERENCE_IDENTITY')
    return json.loads(raw)


def _record(index: int) -> dict:
    if type(index) is not int or not 0 <= index < 20:
        raise ValueError('DRIVER_INDEX')
    return load_reference()['steps'][index]


def expected_input(index: int) -> dict:
    return _record(index)['prepared']


def expected_output(index: int) -> dict:
    result = _record(index)['model_output']
    projection = result['projection']
    projection['normalized_expression'] = float.fromhex(projection['normalized_expression_hex'])
    return result
