"""Independent preregistered literals; no model/quantizer/limiter imports or calls."""

import hashlib
import json
from pathlib import Path

REFERENCE_PATH = Path(__file__).resolve().parents[1] / 'reference/r22_model_expected_v1.json'
REFERENCE_SHA256 = '55e07d229fadd5cbe96130670b3a16812ef0ef9ebf20a389408cd5ca9cf0fff1'
CASE_IDS = ('zero', 'rounded_request', 'signed_zero', 'resumed', 'smallest_subnormal')


def load_reference() -> dict:
    raw = REFERENCE_PATH.read_bytes()
    if REFERENCE_PATH.is_symlink() or hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError('MODEL_REFERENCE_IDENTITY')
    return json.loads(raw)


def _case(case_id: str) -> tuple[dict, dict]:
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise ValueError('CONSUMPTION_CASE')
    reference = load_reference()
    return reference, reference['cases'][case_id]


def _state(values: list) -> dict:
    return dict(zip(('index', 'previous_requested', 'previous_applied', 'angle_counter'), values, strict=True))


def expected_input(case_id: str) -> dict:
    reference, record = _case(case_id)
    source = record['input']
    return {'sample': {**{k: source[k] for k in ('index', 'request_hex', 'driver_hex', 'angle_hex', 'lat_active')},
                       'limits': reference['limits'], 'provenance': 'SYNTHETIC_ONLY'}, 'state': _state(source['state'])}


def _clip(x: int, bounds: list, result: int, x_kind: str) -> dict:
    return {'x': {'kind': x_kind, 'value': x}, 'lower': {'kind': 'python.int', 'value': bounds[0]},
            'upper': {'kind': 'python.int', 'value': bounds[1]}, 'result': {'kind': 'numpy.int64', 'value': result}}


def expected_output(case_id: str) -> dict:
    reference, record = _case(case_id)
    state = _state(record['next_state'])
    projection = {'integer_command': record['final'], 'scale': reference['limits'][0],
                  'normalized_expression': float.fromhex(record['normalized_hex']),
                  'normalized_expression_hex': record['normalized_hex'],
                  'torque_float32': {'bits_hex': record['normalized_bits'], 'value_hex': record['normalized_hex']},
                  'torque_output_can_float32': {'bits_hex': record['command_bits'], 'value_hex': record['command_hex']},
                  'status': 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE'}
    quantization = {'request_hex': record['input']['request_hex'], 'scale': reference['limits'][0],
                    'product_hex': record['product_hex'], 'rounded_integer': record['integer_request'],
                    'integer_command': record['integer_request']}
    downstream = {'limiter_previous': record['input']['state'][2],
                  'driver_clip': _clip(record['integer_request'], reference['driver_bounds'], record['driver_result'], 'python.int'),
                  'rate_clip': _clip(record['driver_result'], record['rate_bounds'], record['limited'], 'numpy.int64'),
                  'limited_command': record['limited'], 'fault_condition': False, 'steer_request': record['steer_request'],
                  'final_command': record['final'], 'next_state': state}
    return {'projection': projection, 'steer_request': record['steer_request'], 'next_state': state,
            'trace': {'quantization': quantization, 'downstream': downstream}}
