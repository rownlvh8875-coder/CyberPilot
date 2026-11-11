"""Read-only saved diagnostic relations;never replay,repair or authenticate origin."""

import hashlib
import os
from pathlib import Path

from .core_sequence_run_inspect import RunInspectError, _directory, _read_file
from .core_sequence_saved import InspectError, _parse
from .core_sequence_suite import SuiteError, _path
from .scenario_output import GATES, canonical

FLAGS = ('first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
         'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed')
KEYS = set(('schema_version contract_id scope input_sha256 input_bytes status frame_count '
            'checked_transition_count new_synthetic_model_steps differing_transition_indices rows '
            'validation_claim state_feed_rule gates').split()) | set(FLAGS)
ROW_KEYS: set[str] = set('transition_index model_index status declared_entry_state computed_next_state declared_saved_state differences'.split())
STATE_KEYS: set[str] = set('index previous_requested previous_applied angle_counter'.split())
SAVED_KEYS = {'saved_limited_state', 'saved_angle_counter'}


class SavedDiagnosticsError(ValueError):
    """Fixed saved-only failure code,not caller content."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise SavedDiagnosticsError(code)


def _integer(value, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _sha(value) -> bool:
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _mapping(value, keys: set[str], code: str) -> dict:
    _need(type(value) is dict and set(value) == keys, code)
    return value


def _same(left, right) -> bool:
    return canonical(left) == canonical(right)


def _state(value) -> dict:
    state = _mapping(value, STATE_KEYS, 'SAVED_DIAGNOSTICS_ROWS')
    _need(_integer(state['index'], 1, 4096) and _integer(state['angle_counter'], 0, 90)
          and all(_integer(state[k], -2048, 2048) for k in ('previous_requested', 'previous_applied')), 'SAVED_DIAGNOSTICS_ROWS')
    return state


def _validate(value) -> dict:
    record = _mapping(value, KEYS, 'SAVED_DIAGNOSTICS_RECORD')
    _need(_integer(record['schema_version'], 1, 1)
          and record['contract_id'] == 'CORE61_COUNTERFACTUAL_RECORDING_DIAGNOSTICS_V1'
          and record['scope'] == 'DECLARED_SYNTHETIC_INPUT_DIAGNOSTICS_ONLY'
          and record['validation_claim'] == 'ADJACENT_DECLARED_CURRENT_TRANSITIONS_ONLY_NOT_COMPUTED_ROLLOUT'
          and record['state_feed_rule'] == 'DECLARED_ENTRY_EACH_STEP_NO_REPAIR_OR_COMPUTED_ROLLOUT'
          and _sha(record['input_sha256']) and _integer(record['input_bytes'], 1, 1048576)
          and all(record[k] is False for k in FLAGS) and _same(record['gates'], GATES), 'SAVED_DIAGNOSTICS_RECORD')
    _need(_integer(record['frame_count'], 2, 128), 'SAVED_DIAGNOSTICS_RECORD')
    count = record['frame_count'] - 1
    _need(all(_integer(record[k], count, count) for k in ('checked_transition_count', 'new_synthetic_model_steps')), 'SAVED_DIAGNOSTICS_RECORD')
    rows = record['rows']
    _need(type(rows) is list and len(rows) == count, 'SAVED_DIAGNOSTICS_ROWS')
    differing = []
    for i, item in enumerate(rows):
        row = _mapping(item, ROW_KEYS, 'SAVED_DIAGNOSTICS_ROWS')
        _need(_integer(row['transition_index'], i, i) and _integer(row['model_index'], 1, 4095), 'SAVED_DIAGNOSTICS_ROWS')
        entry, computed = _state(row['declared_entry_state']), _state(row['computed_next_state'])
        _need(entry['index'] == row['model_index'] and computed['index'] == entry['index'] + 1, 'SAVED_DIAGNOSTICS_ROWS')
        saved = _mapping(row['declared_saved_state'], SAVED_KEYS, 'SAVED_DIAGNOSTICS_ROWS')
        _need(_integer(saved['saved_limited_state'], -2048, 2048) and _integer(saved['saved_angle_counter'], 0, 90), 'SAVED_DIAGNOSTICS_ROWS')
        differences = [{'field': field, 'declared': saved[field], 'computed': computed[key]}
                       for field, key in (('saved_limited_state', 'previous_applied'), ('saved_angle_counter', 'angle_counter'))
                       if saved[field] != computed[key]]
        _need(_same(row['differences'], differences) and row['status'] == ('DIFFERENT' if differences else 'MATCH'), 'SAVED_DIAGNOSTICS_ROWS')
        if differences:
            differing.append(i)
        if i:
            previous = rows[i - 1]
            _need(row['model_index'] == previous['model_index'] + 1
                  and entry['previous_requested'] == previous['computed_next_state']['previous_requested']
                  and entry['previous_applied'] == previous['declared_saved_state']['saved_limited_state']
                  and entry['angle_counter'] == previous['declared_saved_state']['saved_angle_counter'], 'SAVED_DIAGNOSTICS_ROWS')
    _need(_same(record['differing_transition_indices'], differing)
          and record['status'] == ('DIFFERENT' if differing else 'MATCH'), 'SAVED_DIAGNOSTICS_ROWS')
    return record


def inspect_recording_diagnostics(input_root: Path, expected_sha256: str) -> dict:
    """Pin captured bytes and validate stored relations only;no original-input check."""
    _need(_sha(expected_sha256), 'SAVED_DIAGNOSTICS_EXPECTED_SHA256')
    try:
        target = _path(input_root, 'SAVED_DIAGNOSTICS_INPUT')
        with _directory(target, {'DIAGNOSTICS.json': False, 'SHA256SUMS.txt': False}) as directory:
            raw = _read_file(directory, 'DIAGNOSTICS.json', 1048576)
            manifest = _read_file(directory, 'SHA256SUMS.txt', 512)
            opened, current = os.fstat(directory), target.stat(follow_symlinks=False)
            _need((opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino), 'SAVED_DIAGNOSTICS_INPUT')
    except SavedDiagnosticsError:
        raise
    except (RunInspectError, SuiteError, OSError, ValueError, RuntimeError) as error:
        raise SavedDiagnosticsError('SAVED_DIAGNOSTICS_INPUT') from error
    digest = hashlib.sha256(raw).hexdigest()
    _need(digest == expected_sha256 and manifest == (digest + '  DIAGNOSTICS.json\n').encode(), 'SAVED_DIAGNOSTICS_CHECKSUM')
    try:
        parsed = _parse(raw)
    except InspectError as error:
        raise SavedDiagnosticsError('SAVED_DIAGNOSTICS_JSON') from error
    record = _validate(parsed)
    return {'schema_version': 1, 'contract_id': 'CORE66_SAVED_RECORDING_DIAGNOSTICS_INSPECTION_V1',
        'inspection_status': 'SAVED_DIAGNOSTICS_CONSISTENT', 'inspection_exit_code': 0,
        'saved_status': record['status'], 'saved_diagnostic_exit_code': 0 if record['status'] == 'MATCH' else 1,
        'diagnostics_sha256': digest, 'diagnostics_bytes': len(raw), 'recorded_model_steps': record['new_synthetic_model_steps'],
        'new_synthetic_model_steps': 0, 'new_reference_steps': 0, 'numeric_validation_work': 'NONZERO_NOT_AGGREGATED',
        'stored_record': record, 'arithmetic_recomputed': False, 'original_input_verified': False,
        **{name: False for name in FLAGS}, 'gates': dict(GATES),
        'scope': 'CHECKED_CAPTURED_SAVED_RELATIONS_NOT_NUMERICAL_OR_ORIGIN_PROOF'}
