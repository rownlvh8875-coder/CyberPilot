"""Closed hand-derived vectors; no target/model/quantizer/oracle execution."""

import hashlib
import json
import os
from pathlib import Path

from .core_sequence_run_inspect import _read_file
from .core_sequence_suite import _path

REFERENCE_PATH = Path(__file__).resolve().parents[1] / 'reference/core30_rollout_expected_v1.json'
REFERENCE_SHA256 = '3ba18d20fb93f6c5ee0d432ecacbaa314df40046a9289264b7c1954f4762e5b3'
REFERENCE_BYTE_SIZE = 2132
CASE_IDS = ('sign-cycle', 'declared-difference', 'late-invalid')
META = {'contract_id': 'CORE27_COUNTERFACTUAL_COMPUTED_STATE_ROLLOUT_V1',
    'validation_claim': 'COUNTERFACTUAL_COMPUTED_STATE_CHAIN_NOT_SOURCE_OR_PREHISTORY_PROOF',
    'state_feed_rule': 'FIRST_DECLARED_ENTRY_THEN_COMPUTED_NEXT_STATE_NO_RESEED', 'computed_state_fed': True,
    'first_frame_transition_checked': False, 'prehistory_checked': False, 'source_identity_reauthenticated': False,
    'v4_payload_allowed': False, 'f61_input_allowed': False, 'actual_activation_allowed': False}


def load_reference() -> dict:
    """Capture a bounded owned regular file once and hash before decoding."""
    try:
        path = _path(REFERENCE_PATH, 'ROLLOUT_REFERENCE_PATH')
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            raw = _read_file(directory, path.name, REFERENCE_BYTE_SIZE)
        finally:
            os.close(directory)
        if len(raw) != REFERENCE_BYTE_SIZE or hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
            raise ValueError('ROLLOUT_REFERENCE_IDENTITY')
        return json.loads(raw)
    except (OSError, ValueError, RuntimeError) as error:
        raise ValueError('ROLLOUT_REFERENCE_IDENTITY') from error


def _state(values) -> dict:
    return dict(zip(('index', 'previous_requested', 'previous_applied', 'angle_counter'), values, strict=True))


def _clip(value, bounds, result, kind) -> dict:
    return {'x': {'kind': kind, 'value': value}, 'lower': {'kind': 'python.int', 'value': bounds[0]},
            'upper': {'kind': 'python.int', 'value': bounds[1]}, 'result': {'kind': 'numpy.int64', 'value': result}}


def _expected(case_id: str, reference: dict) -> dict:
    case = reference['cases'][case_id]
    if case_id == 'late-invalid':
        return {'status': 'REJECTED', 'rejection_code': case['rejection_code'], 'synthetic_model_steps': 0, 'steps': []}
    rows = []
    for i, vector in enumerate(reference['steps']):
        entry, after, command = _state(vector['entry']), _state(vector['next']), vector['command']
        declared = {**entry, 'previous_applied': case['declared_applied'][i]}
        saved = {'saved_limited_state': case['saved_applied'][i], 'saved_angle_counter': after['angle_counter']}
        # This assembly maps preregistered literals; it runs no target arithmetic.
        entry_diff = [] if i not in case['entry_indices'] else [
            {'field': 'entry_previous_applied', 'declared': case['declared_applied'][i], 'computed': entry['previous_applied']}]
        output_diff = [] if i not in case['output_indices'] else [
            {'field': 'saved_limited_state', 'declared': case['saved_applied'][i], 'computed': command}]
        quantization = {'request_hex': vector['request_hex'], 'scale': reference['scale'], 'product_hex': vector['product_hex'],
                        'rounded_integer': vector['integer_request'], 'integer_command': vector['integer_request']}
        downstream = {'limiter_previous': entry['previous_applied'],
            'driver_clip': _clip(vector['integer_request'], reference['driver_bounds'], vector['integer_request'], 'python.int'),
            'rate_clip': _clip(vector['integer_request'], vector['rate_bounds'], command, 'numpy.int64'),
            'limited_command': command, 'fault_condition': True, 'steer_request': True, 'final_command': command, 'next_state': after}
        projection = {'integer_command': command, 'scale': reference['scale'],
            'normalized_expression': float.fromhex(vector['normalized_hex']), 'normalized_expression_hex': vector['normalized_hex'],
            'torque_float32': {'bits_hex': vector['normalized_bits'], 'value_hex': vector['normalized_hex']},
            'torque_output_can_float32': {'bits_hex': vector['command_bits'], 'value_hex': vector['command_hex']},
            'status': 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE'}
        rows.append({'model_index': entry['index'], 'entry_state': entry, 'declared_entry_state': declared, 'declared_saved_state': saved,
            'output': {'projection': projection, 'steer_request': True, 'next_state': after,
                       'trace': {'quantization': quantization, 'downstream': downstream}},
            'entry_differences': entry_diff, 'output_differences': output_diff,
            'status': 'DIFFERENT' if i in case['difference_indices'] else 'MATCH'})
    return {**META, 'status': case['status'], 'rejection_code': None, 'synthetic_model_steps': 3, 'checked_transition_count': 3,
            'initial_declared_state': _state(reference['steps'][0]['entry']), 'final_computed_state': _state(reference['steps'][-1]['next']),
            'entry_differing_transition_indices': list(case['entry_indices']), 'output_differing_transition_indices': list(case['output_indices']),
            'differing_transition_indices': list(case['difference_indices']), 'steps': rows}


def expected_rollout(case_id: object) -> dict:
    """Return fresh closed expected records, never a general numerical oracle."""
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise ValueError('ROLLOUT_REFERENCE_CASE')
    return _expected(case_id, load_reference())
