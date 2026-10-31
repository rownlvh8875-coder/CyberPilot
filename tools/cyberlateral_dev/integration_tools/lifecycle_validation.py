"""Stdlib-only complete lifecycle acceptance against the existing frozen trace."""

import hashlib
import json
from pathlib import Path

from .handoff_validation import _array, _object, canonical, validate_handoff_record


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def lifecycle_pair_summary(first: Path, second: Path) -> dict:
    try:
        one = {p.name: p.read_bytes() for p in first.iterdir()}
        two = {p.name: p.read_bytes() for p in second.iterdir()}
    except OSError as error:
        raise ValueError('LIFECYCLE_ARTIFACT_READ') from error
    _require(set(one) == set(two) == {'RESULTS.json', 'SHA256SUMS.txt'}, 'LIFECYCLE_ARTIFACT_MISSING')
    _require(one == two, 'LIFECYCLE_ARTIFACT_BYTE_MISMATCH')
    raw = one['RESULTS.json']
    record = _object(json.loads(raw))
    _require(canonical(record) == raw, 'LIFECYCLE_CONTRACT_CANONICAL')
    baseline = _object(record.get('baseline'))
    _require('execution_environment' not in baseline, 'LIFECYCLE_CONTRACT_BASELINE_FIELDS')
    environment = {'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': []}
    validate_handoff_record(baseline | {'execution_environment': environment})
    identities = {
        'schema_version': 1, 'contract_id': 'F70UGZ_R16_SYNTHETIC_HANDOFF_LIFECYCLE_V1',
        'status': 'F70UGZ_R16_SYNTHETIC_HANDOFF_LIFECYCLE_PASS', 'scope': 'CLOSED_SAME_PROCESS_SYNTHETIC_LIFECYCLE_NOT_NATIVE_OR_PERSISTENT_REPLAY',
        'scenario_count': 7, 'total_source_samples': 112, 'two_chunk_splits': 105,
        'extractor_calls': 9010, 'model_steps': 9010, 'prefix_validation_steps': 0,
        'count_scope': 'PER_FIXED_LIFECYCLE_PROCESS_NOT_AGGREGATE_TEST_ACTIVITY',
        'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME', 'native_qualification': 'NOT_RUN_NOT_AUTHORIZED',
        'gates': baseline['gates'], 'execution_environment': environment,
    }
    _require(set(record) == set(identities) | {'baseline', 'split_runs', 'interleaved_events'}
             and all(canonical(record.get(k)) == canonical(v) for k, v in identities.items()), 'LIFECYCLE_CONTRACT_IDENTITY_OR_GATES')
    expected_splits, expected_events = [], []
    rows = [_object(row) for row in _array(baseline['scenarios'])]
    for row in rows:
        cuts = []
        outputs = _array(_object(row['result'])['outputs'])
        for cut in range(1, row['steps']):
            state = _object(outputs[cut - 1])['next_state']
            cuts.append({'cut': cut, 'prefix_final_state': state, 'resumed_prepared_state': state,
                         'frames_sha256': _sha(row['frames']), 'prepared_sha256': _sha(row['prepared']), 'result_sha256': row['result_sha256']})
        expected_splits.append({'id': row['id'], 'cuts': cuts})
    for offset in range(max(row['steps'] for row in rows)):
        for row in rows:
            if offset < row['steps']:
                expected_events.append({'id': row['id'], 'offset': offset, 'frame': _array(row['frames'])[offset],
                                        'prepared': _array(row['prepared'])[offset], 'output': _array(_object(row['result'])['outputs'])[offset]})
    _require(canonical(record['split_runs']) == canonical(expected_splits), 'LIFECYCLE_CONTRACT_SPLITS')
    _require(canonical(record['interleaved_events']) == canonical(expected_events), 'LIFECYCLE_CONTRACT_INTERLEAVED')
    _require(one['SHA256SUMS.txt'] == (hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n').encode(), 'LIFECYCLE_CONTRACT_MANIFEST')
    return {'status': record['status'], 'byte_identical': True, 'scenario_count': record['scenario_count'], 'two_chunk_splits': record['two_chunk_splits'],
            'model_steps': record['model_steps'], 'file_hashes': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(one.items())},
            'scope': 'closed same-process synthetic lifecycle only, not native custody, persistent replay or independent arithmetic proof'}
