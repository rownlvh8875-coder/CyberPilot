"""Validate decoded fixed-observation JSON before publication, no model imports."""

import json
from typing import Any, cast

from integration_tools import driver_reference as r25
from integration_tools import fault_reference as r24
from integration_tools import fixed_model_reference as r22
from integration_tools import sequence_reference as r23
from native_qualification.claims import validate_claims

REJECTED = ('driver_precision_reject', 'angle_precision_reject', 'request_range_reject')


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError('OBSERVATION_COVERAGE')


def _integer(value, expected: int) -> bool:
    return type(value) is int and value == expected


def _equal(actual, expected) -> bool:
    try:
        return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError):
        return False


def validate_coverage(observations: dict, mode: str) -> int:
    _require(type(observations) is dict and type(mode) is str and mode in ('R22', 'R23', 'R24', 'R25'))
    rows = observations.get('cases')
    if type(rows) is not list:
        raise ValueError('OBSERVATION_COVERAGE')
    _require(len(rows) == {'R22': 8, 'R23': 4, 'R24': 99, 'R25': 20}[mode])
    # Decoded JSON boundary: container shape is checked here and each row below.
    # The annotation does not replace the exact scalar/record validation.
    decoded = cast(list[dict[str, Any]], rows)
    _require(_integer(observations.get('F61_execution'), 0) and observations.get('actual_activation') == 'NOT_ALLOWED'
             and observations.get('R_BUDGET') == 'UNRESOLVED' and observations.get('STATIC_EVIDENCE_GATE') == 'FAIL')
    seen = set()
    total = 0
    previous_next = None
    for position, row in enumerate(decoded):
        if type(row) is not dict:
            raise ValueError('OBSERVATION_COVERAGE')
        key = row.get('id') if mode == 'R22' else row.get('index')
        if mode == 'R22':
            _require(type(key) is str and key in (*r22.CASE_IDS, *REJECTED))
            accepted = key in r22.CASE_IDS
        else:
            _require(type(key) is int and key == position)
            accepted = True
        _require(key not in seen)
        seen.add(key)
        _require(type(row.get('accepted')) is bool and row['accepted'] is accepted
                 and _integer(row.get('model_steps'), 1 if accepted else 0))
        if accepted:
            if mode == 'R22':
                if type(key) is not str:
                    raise ValueError('OBSERVATION_COVERAGE')
                expected_input, expected_output = r22.expected_input(key), r22.expected_output(key)
            else:
                reference = {'R23': r23, 'R24': r24, 'R25': r25}[mode]
                expected_input, expected_output = reference.expected_input(position), reference.expected_output(position)
            _require(row.get('model_expected_match') is True and _equal(row.get('prepared'), expected_input)
                     and _equal(row.get('model_output'), expected_output))
            total += row['model_steps']
            if mode != 'R22' and position:
                _require(_equal(previous_next, row['prepared']['state']))
            previous_next = row['model_output']['next_state']
        else:
            _require('model_output' not in row and row.get('rejection_code') == 'SEMANTIC_DOMAIN')
    _require(_integer(observations.get('model_execution'), total) and total == {'R22': 5, 'R23': 4, 'R24': 99, 'R25': 20}[mode])
    validate_claims(observations, mode)
    return total
