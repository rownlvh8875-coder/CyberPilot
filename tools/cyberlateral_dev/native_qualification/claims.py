"""Auxiliary decoded-JSON declaration checks, not byte/history/OS authentication."""

import json
import re
from typing import Any, cast

from integration_tools import fault_reference as r24
from integration_tools import fixed_model_reference as r22
from integration_tools import sequence_reference as r23
from native_qualification.worker import SCHEMA_SHA, WHEEL_SHA


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError('OBSERVATION_CLAIMS')


def _text(value, expected: str) -> bool:
    return type(value) is str and value == expected


def _equal(actual, expected) -> bool:
    try:
        return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False


def _digest(value) -> bool:
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_claims(data: dict, mode: str) -> None:
    if type(data) is not dict or type(mode) is not str or mode not in ('R22', 'R23', 'R24'):
        raise ValueError('OBSERVATION_CLAIMS')
    profiles = {
        'R22': ('FIVE_FIXED_SYNTHETIC_SINGLE_STEPS_NOT_ACTUAL_OR_CHAIN', r22.REFERENCE_SHA256, 8),
        'R23': ('FOUR_FIXED_SYNTHETIC_NATIVE_MODEL_STEPS_NOT_ACTUAL_HISTORY', r23.REFERENCE_SHA256, 4),
        'R24': ('NINETY_SIX_FIXED_SYNTHETIC_FAULT_RESET_STEPS_NOT_ACTUAL_HISTORY', r24.REFERENCE_SHA256, 96),
    }
    scope, reference, count = profiles[mode]
    _require(type(data.get('schema_version')) is int and data['schema_version'] == 1
             and _text(data.get('scope'), scope) and _text(data.get('package_version'), '0.3.0')
             and _text(data.get('model_reference_sha256'), reference)
             and _text(data.get('actual_call_custody'), 'NOT_QUALIFIED'))
    _require(type(data.get('identity')) is dict and _equal(data['identity'], {'schema_sha256': SCHEMA_SHA, 'wheel_sha256': WHEEL_SHA}))
    _require(type(data.get('forbidden_modules_loaded')) is list and data['forbidden_modules_loaded'] == [])
    rows = data.get('cases')
    if type(rows) is not list or len(rows) != count:
        raise ValueError('OBSERVATION_CLAIMS')
    if mode == 'R22':
        _require(_text(data.get('oracle_algorithm'), 'INDEPENDENT_INTEGER_SIGNIFICAND_EXPONENT_NOT_STRUCT_ROUNDTRIP')
                 and data.get('input_structure_only_not_F61') is True)
    else:
        _require(_text(data.get('time_semantics'), 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'))
    for raw in rows:
        if type(raw) is not dict:
            raise ValueError('OBSERVATION_CLAIMS')
        row = cast(dict[str, Any], raw)
        _require(row.get('oracle_parity') is True and _digest(row.get('cc_sha256')) and _digest(row.get('cs_sha256')))
        if mode == 'R22':
            _require(type(row.get('id')) is str)
            if row['id'] in r22.CASE_IDS:
                _require(_text(row.get('custody_claim'), 'DECLARED_READBACK_BINDING_NOT_AUTHENTICATED_NATIVE_CUSTODY')
                         and _text(row.get('precision_claim'), 'EXACT_SUPPLIED_FLOAT32_PROMOTED_TO_PYTHON_FLOAT'))
            else:
                _require(_text(row.get('oracle_rejection_code'), 'SEMANTIC_DOMAIN')
                         and _text(row.get('rejection_code'), 'SEMANTIC_DOMAIN'))
        else:
            index = row.get('index')
            if type(index) is not int or not 0 <= index < count:
                raise ValueError('OBSERVATION_CLAIMS')
            sequence_id = 'R23_FIXED_SEQUENCE' if mode == 'R23' else 'R24_FIXED_FAULT_RESET'
            _require(type(row.get('stamp')) is dict and _equal(row['stamp'], {
                'sequence_id': sequence_id, 'invocation_index': index, 'capture_id': 'entry_' + str(index)}))
            _require(_text(row.get('state_binding'), 'EXPLICIT_FIXED_INITIAL_DATA' if index == 0 else
                           'PREVIOUS_VERIFIED_MODEL_OUTPUT_NOT_ACTUAL_HISTORY'))
