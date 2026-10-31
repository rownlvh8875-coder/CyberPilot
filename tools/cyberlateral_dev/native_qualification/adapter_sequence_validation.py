"""Data-only complete R29 coverage/literal validation; never native/model work."""

import re

from integration_tools import negative_cycle_reference, sequence_reference

from .worker import canonical


def _require(condition: bool, code: str):
    if not condition:
        raise ValueError('CHAIN_EXPORT:' + code)


def _validate(data: dict) -> int:
    _require(type(data) is dict, 'SHAPE')
    expected_root = {
        'schema_version': 1, 'status': 'F70UGZ_R29_FIXED_SYNTHETIC_ADAPTER_MODEL_SEQUENCE_PASS',
        'scope': 'TWO_REGISTERED_SYNTHETIC_NATIVE_ADAPTER_MODEL_SEQUENCES_ONLY',
        'package_version': '0.3.0', 'model_execution': 103, 'observed_model_calls': 103,
        'F61_execution': 0, 'Controller_execution': 0, 'Runtime_execution': 0, 'CAN': 0,
        'calculator_input_execution': 0, 'actual_inputs': 0, 'r_calculation': 0, 'dt_calculation': 0,
        'actual_call_custody': 'NOT_QUALIFIED', 'actual_activation': 'NOT_ALLOWED', 'generic_external_reader': 'NOT_IMPLEMENTED',
        'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'}
    _require(set(data) == {*expected_root, 'profiles'}, 'SHAPE')
    _require(canonical({k: v for k, v in data.items() if k != 'profiles'}) == canonical(expected_root), 'ROOT')
    profiles = data['profiles']
    _require(type(profiles) is list and len(profiles) == 2, 'PROFILES')
    for profile, (name, count, reference) in zip(profiles, [
            ('SIGN_CHANGE_4', 4, sequence_reference), ('NEGATIVE_CYCLE_99', 99, negative_cycle_reference)], strict=True):
        _require(type(profile) is dict and set(profile) == {'profile_id', 'reference_sha256', 'model_execution', 'initial_state', 'final_state', 'cases'}, 'PROFILE')
        expected_meta = {'profile_id': name, 'reference_sha256': reference.REFERENCE_SHA256, 'model_execution': count,
                         'initial_state': {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0},
                         'final_state': reference.expected_output(count - 1)['next_state']}
        _require(canonical({k: v for k, v in profile.items() if k != 'cases'}) == canonical(expected_meta), 'PROFILE')
        cases = profile['cases']
        _require(type(cases) is list and len(cases) == count, 'COVERAGE')
        previous = profile['initial_state']
        for index, row in enumerate(cases):
            _require(type(row) is dict and set(row) == {'index', 'stamp', 'prepared', 'model_output', 'model_steps', 'oracle_parity',
                                                       'cc_sha256', 'cs_sha256', 'read_claim', 'state_binding'}, 'CASE')
            _require(type(row['index']) is int and row['index'] == index and type(row['model_steps']) is int
                     and row['model_steps'] == 1 and row['oracle_parity'] is True, 'COVERAGE')
            _require(canonical(row['stamp']) == canonical({'sequence_id': 'R29_' + name, 'invocation_index': index, 'capture_id': 'entry_' + str(index)}), 'STAMP')
            _require(canonical(row['prepared']) == canonical(reference.expected_input(index)), 'INPUT')
            _require(canonical(row['model_output']) == canonical(reference.expected_output(index)), 'OUTPUT')
            _require(canonical(row['prepared']['state']) == canonical(previous), 'ADJACENCY')
            previous = row['model_output']['next_state']
            for key in ['cc_sha256', 'cs_sha256']:
                _require(type(row[key]) is str and re.fullmatch('[0-9a-f]{64}', row[key]) is not None, 'PAYLOAD_HASH')
            _require(row['read_claim'] == 'INTERNALLY_CONSTRUCTED_OWNED_SYNTHETIC_BYTES_READ_WITHIN_CONTEXT', 'READ_CLAIM')
            _require(row['state_binding'] == ('EXPLICIT_FIXED_INITIAL_DATA' if index == 0 else 'PREVIOUS_VERIFIED_MODEL_OUTPUT_NOT_ACTUAL_HISTORY'), 'STATE_CLAIM')
    return 103


def validate_observations(data: dict) -> int:
    try:
        return _validate(data)
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError('CHAIN_EXPORT:SHAPE') from error
