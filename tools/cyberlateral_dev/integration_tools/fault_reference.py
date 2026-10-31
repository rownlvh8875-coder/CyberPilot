"""All99 preregistered v2 literals, representation assembly only, no model math."""

import hashlib
import json
from pathlib import Path

from .fixed_model_reference import _clip, _state

REFERENCE_PATH = Path(__file__).resolve().parents[1] / 'reference/r24_fault_expected_v2.json'
REFERENCE_SHA256 = 'dfb150fc3f1348be6fae161bdb2d524dc1138c504410c8ef38bf874c27b4d8cd'


def load_reference() -> dict:
    raw = REFERENCE_PATH.read_bytes()
    if REFERENCE_PATH.is_symlink() or hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError('FAULT_REFERENCE_IDENTITY')
    return json.loads(raw)


def _record(index: int) -> tuple[dict, dict]:
    if type(index) is not int or not 0 <= index < 99:
        raise ValueError('FAULT_INDEX')
    reference = load_reference()
    return reference, reference['steps'][index]


def expected_input(index: int) -> dict:
    reference, record = _record(index)
    return {'sample': {'index': index, 'request_hex': record['request_hex'], 'driver_hex': '0x0.0p+0',
                       'angle_hex': record['angle_hex'], 'lat_active': record['active'], 'limits': reference['limits'],
                       'provenance': 'SYNTHETIC_ONLY'}, 'state': _state(record['previous'])}


def expected_output(index: int) -> dict:
    reference, record = _record(index)
    state = _state(record['next_state'])
    quantization = {'request_hex': record['request_hex'], 'scale': reference['limits'][0], 'product_hex': record['product_hex'],
                    'rounded_integer': record['integer_request'], 'integer_command': record['integer_request']}
    downstream = {'limiter_previous': record['previous'][2],
                  'driver_clip': _clip(record['integer_request'], reference['driver_bounds'], record['integer_request'], 'python.int'),
                  'rate_clip': _clip(record['integer_request'], record['rate_bounds'], record['limited'], 'numpy.int64'),
                  'limited_command': record['limited'], 'fault_condition': record['fault_condition'], 'steer_request': record['steer_request'],
                  'final_command': record['final'], 'next_state': state}
    projection = {'integer_command': record['final'], 'scale': reference['limits'][0],
                  'normalized_expression': float.fromhex(record['normalized_hex']), 'normalized_expression_hex': record['normalized_hex'],
                  'torque_float32': {'bits_hex': record['normalized_bits'], 'value_hex': record['normalized_hex']},
                  'torque_output_can_float32': {'bits_hex': record['command_bits'], 'value_hex': record['command_hex']},
                  'status': 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE'}
    return {'projection': projection, 'steer_request': record['steer_request'], 'next_state': state,
            'trace': {'quantization': quantization, 'downstream': downstream}}
