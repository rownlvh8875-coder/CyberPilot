"""Pinned hand boundary vectors; representation assembly only, no target arithmetic."""

import hashlib
import json
import os
from pathlib import Path

from .core_sequence_run_inspect import _read_file
from .core_sequence_suite import _path
from .rollout_reference import META, _clip, _state

CASE_IDS = ('inactive-resume', 'fault-reset', 'rounding-ties')
REFERENCE_PATH = Path(__file__).resolve().parents[1] / 'reference/core31_boundary_expected_v1.json'
REFERENCE_SHA256 = 'a9acf091ecf2cd2bb4a5ae37fcadfcd9c292bbab6534f43d926f2bb9ddb79745'
REFERENCE_BYTE_SIZE = 5357


def load_reference() -> dict:
    """Bounded single owned-file capture, exact identity before JSON decode."""
    try:
        path = _path(REFERENCE_PATH, 'BOUNDARY_REFERENCE_PATH')
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            raw = _read_file(fd, path.name, REFERENCE_BYTE_SIZE)
        finally:
            os.close(fd)
        if len(raw) != REFERENCE_BYTE_SIZE or hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
            raise ValueError('BOUNDARY_REFERENCE_IDENTITY')
        return json.loads(raw)
    except (OSError, ValueError, RuntimeError) as error:
        raise ValueError('BOUNDARY_REFERENCE_IDENTITY') from error


def _expected(case_id: str, data: dict) -> dict:
    vectors = data['cases'][case_id]['steps']; rows = []
    for v in vectors:
        entry, after = _state(v['entry']), _state(v['next'])
        quantization = {'request_hex': v['request_hex'], 'scale': data['scale'], 'product_hex': v['product_hex'],
                        'rounded_integer': v['integer_request'], 'integer_command': v['integer_request']}
        downstream = {'limiter_previous': entry['previous_applied'],
            'driver_clip': _clip(v['integer_request'], data['driver_bounds'], v['integer_request'], 'python.int'),
            'rate_clip': _clip(v['integer_request'], v['rate_bounds'], v['limited'], 'numpy.int64'),
            'limited_command': v['limited'], 'fault_condition': v['fault'], 'steer_request': v['steer'],
            'final_command': v['final'], 'next_state': after}
        projection = {'integer_command': v['final'], 'scale': data['scale'],
            'normalized_expression': float.fromhex(v['normalized_hex']), 'normalized_expression_hex': v['normalized_hex'],
            'torque_float32': {'bits_hex': v['normalized_bits'], 'value_hex': v['normalized_hex']},
            'torque_output_can_float32': {'bits_hex': v['command_bits'], 'value_hex': v['command_hex']},
            'status': 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE'}
        rows.append({'model_index': entry['index'], 'entry_state': entry, 'declared_entry_state': dict(entry),
            'declared_saved_state': {'saved_limited_state': v['final'], 'saved_angle_counter': after['angle_counter']},
            'output': {'projection': projection, 'steer_request': v['steer'], 'next_state': after,
                       'trace': {'quantization': quantization, 'downstream': downstream}},
            'entry_differences': [], 'output_differences': [], 'status': 'MATCH'})
    return {**META, 'status': 'MATCH', 'rejection_code': None, 'synthetic_model_steps': len(rows), 'checked_transition_count': len(rows),
            'initial_declared_state': _state(vectors[0]['entry']), 'final_computed_state': _state(vectors[-1]['next']),
            'entry_differing_transition_indices': [], 'output_differing_transition_indices': [], 'differing_transition_indices': [], 'steps': rows}


def expected_boundary(case_id: object) -> dict:
    """Fresh closed literals, not a numerical function on arbitrary input."""
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise ValueError('BOUNDARY_REFERENCE_CASE')
    return _expected(case_id, load_reference())
