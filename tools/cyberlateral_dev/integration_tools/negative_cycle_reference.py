"""Preregistered99 complete literals; representation assembly, no model math."""

import hashlib
import json
from pathlib import Path

REFERENCE_PATH = Path(__file__).resolve().parents[1] / 'reference/r26_negative_cycle_expected_v1.json'
REFERENCE_SHA256 = 'f3b60afc2e3ba8b100ee9dbcb2a125f9c27c797c3d6b4af7b882cc7c069390f8'


def load_reference() -> dict:
    raw = REFERENCE_PATH.read_bytes()
    if REFERENCE_PATH.is_symlink() or hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError('NEGATIVE_CYCLE_REFERENCE_IDENTITY')
    return json.loads(raw)


def _record(index: int) -> dict:
    if type(index) is not int or not 0 <= index < 99:
        raise ValueError('NEGATIVE_CYCLE_INDEX')
    return load_reference()['steps'][index]


def expected_input(index: int) -> dict:
    return _record(index)['prepared']


def expected_output(index: int) -> dict:
    result = _record(index)['model_output']
    projection = result['projection']
    projection['normalized_expression'] = float.fromhex(projection['normalized_expression_hex'])
    return result
