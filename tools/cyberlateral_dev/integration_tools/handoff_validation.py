"""Stdlib-only full trace acceptance from frozen source inputs and result hashes."""

import hashlib
import json
from pathlib import Path


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _object(value) -> dict:
    _require(type(value) is dict, 'HANDOFF_CONTRACT_OBJECT')
    return value


def _array(value) -> list:
    _require(type(value) is list, 'HANDOFF_CONTRACT_ARRAY')
    return value


def _expected_frame(sample: dict, state: dict, sequence: str) -> dict:
    return {
        'schema_version': 1, 'scope': 'SYNTHETIC_DEVELOPMENT_ONLY', 'profile_id': 'R13_HYUNDAI_TORQUE_ENTRY_SYNTHETIC_V1',
        'source_set_id': 'R11_C8FB9068_4134C0D1_V1', 'value_representation': 'SYNTHETIC_PYTHON_BINARY64',
        'sequence_id': sequence, 'invocation_index': sample['index'], 'static_context_reference': 'SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY',
        'consumed_settings_origin': 'EXPLICIT_SYNTHETIC_CALL_ENTRY',
        'cc': {'actuators': {'torque': sample['request']}, 'latActive': sample['lat_active']},
        'cs': {'out': {'steeringTorque': sample['driver'], 'steeringAngleDeg': sample['angle_deg']}},
        'consumed_limits': sample['limits'],
        'previous': {'snapshot_stage': 'ENTRY_BEFORE_CURRENT_LIMITER', 'sequence_id': sequence,
                     'previous_invocation_index': None if sample['index'] == 0 else sample['index'] - 1,
                     'source_previous_applied': state['previous_applied'], 'source_angle_counter': state['angle_counter'], 'model_state': state},
    }


def handoff_pair_summary(first: Path, second: Path) -> dict:
    try:
        one = {p.name: p.read_bytes() for p in first.iterdir()}
        two = {p.name: p.read_bytes() for p in second.iterdir()}
    except OSError as error:
        raise ValueError('HANDOFF_ARTIFACT_READ') from error
    _require(set(one) == set(two) == {'RESULTS.json', 'SHA256SUMS.txt'}, 'HANDOFF_ARTIFACT_MISSING')
    _require(one == two, 'HANDOFF_ARTIFACT_BYTE_MISMATCH')
    raw = one['RESULTS.json']
    record = _object(json.loads(raw))
    _require(canonical(record) == raw, 'HANDOFF_CONTRACT_CANONICAL')
    golden = json.loads((Path(__file__).resolve().parents[1] / 'reference/synthetic_harness_expected_v1.json').read_bytes())
    identities = {
        'schema_version': 1, 'contract_id': 'F70UGZ_R15_FIXED_SYNTHETIC_HANDOFF_V1',
        'status': 'F70UGZ_R15_SYNTHETIC_HANDOFF_CHAIN_PASS', 'package_version': '0.3.0',
        'boundary_contract_id': 'F70UGZ_R13_MESSAGE_BOUNDARY_V1', 'fixture_catalog_sha256': golden['fixture_catalog_sha256'],
        'scope': 'FIXED_SYNTHETIC_HANDOFF_NOT_NATIVE_OR_INDEPENDENT_ARITHMETIC_PROOF',
        'scenario_count': 7, 'extractor_calls': 112, 'model_steps': 112, 'prefix_validation_steps': 0,
        'count_scope': 'PER_FIXED_HANDOFF_PROCESS_NOT_AGGREGATE_TEST_ACTIVITY',
        'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME', 'native_qualification': 'NOT_RUN_NOT_AUTHORIZED',
        'gates': golden['required_gates'],
        'execution_environment': {'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': []},
    }
    _require(set(record) == set(identities) | {'scenarios'}
             and all(canonical(record.get(k)) == canonical(v) for k, v in identities.items()), 'HANDOFF_CONTRACT_IDENTITY_OR_GATES')
    rows = [_object(row) for row in _array(record.get('scenarios'))]
    _require(len(rows) == len(golden['scenarios']), 'HANDOFF_CONTRACT_COVERAGE')
    fixtures = []
    for row, expected in zip(rows, golden['scenarios'], strict=True):
        _require(set(row) == {'id', 'steps', 'initial_state', 'source_samples', 'frames', 'prepared', 'result', 'result_sha256', 'seed_origin', 'continuation_scope'},
                 'HANDOFF_CONTRACT_SCENARIO_FIELDS')
        _require(canonical({k: row.get(k) for k in ['id', 'steps', 'result_sha256']}) == canonical(expected), 'HANDOFF_CONTRACT_SCENARIO_IDENTITY')
        result = _object(row['result'])
        _require(hashlib.sha256(canonical(result)).hexdigest() == expected['result_sha256'], 'HANDOFF_CONTRACT_RESULT_GOLDEN')
        fixtures.append({'id': row['id'], 'initial_state': row['initial_state'], 'samples': row['source_samples']})
    _require(hashlib.sha256(canonical(fixtures)).hexdigest() == golden['fixture_catalog_sha256'], 'HANDOFF_CONTRACT_CATALOG')
    for row in rows:
        state = _object(row['initial_state'])
        seed_origin = ('DECLARED_CANONICAL_SYNTHETIC_INITIAL_STATE' if state['index'] == 0 else
                       'REGISTERED_SYNTHETIC_SEED_NOT_OBSERVED_PREHISTORY')
        _require(row['seed_origin'] == seed_origin
                 and row['continuation_scope'] == 'OWNED_IMMEDIATE_PRIOR_MODEL_OUTPUT_NOT_NATIVE_CUSTODY', 'HANDOFF_CONTRACT_SEED_OR_CUSTODY')
        samples, frames, prepared = _array(row['source_samples']), _array(row['frames']), _array(row['prepared'])
        _require(len(samples) == len(frames) == len(prepared) == row['steps'], 'HANDOFF_CONTRACT_TRACE_COVERAGE')
        sequence = 'handoff_' + row['id']
        result = _object(row['result'])
        outputs = _array(result['outputs'])
        for offset, raw_sample in enumerate(samples):
            sample = _object(raw_sample)
            previous = state if offset == 0 else _object(_object(outputs[offset - 1])['next_state'])
            _require(canonical(frames[offset]) == canonical(_expected_frame(sample, previous, sequence)), 'HANDOFF_CONTRACT_FRAME')
            expected_prepared = {
                'contract_id': 'F70UGZ_R13_MESSAGE_BOUNDARY_V1', 'source_set_id': 'R11_C8FB9068_4134C0D1_V1', 'sequence_id': sequence,
                'sample': sample, 'state': previous, 'custody_claim': 'SYNTHETIC_DECLARATION_ONLY',
                'precision_claim': 'EXACT_SUPPLIED_BINARY64_NOT_NATIVE_ABI', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
            }
            _require(canonical(prepared[offset]) == canonical(expected_prepared), 'HANDOFF_CONTRACT_PREPARED')
    _require(one['SHA256SUMS.txt'] == (hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n').encode(), 'HANDOFF_CONTRACT_MANIFEST')
    return {'status': record['status'], 'byte_identical': True, 'scenario_count': record['scenario_count'], 'model_steps': record['model_steps'],
            'file_hashes': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(one.items())},
            'scope': 'fixed synthetic handoff/state continuity, not native custody or new independent numerical oracle'}
