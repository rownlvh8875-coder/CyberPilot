"""Declared-input selected-source reference audit;no public model step calls."""

import hashlib
import platform
import struct
import subprocess
import sys
from pathlib import Path

from .core_sequence_saved import InspectError, _parse
from .offline_recording_input_codec import decode_recording_input
from .recording_diagnostics_saved import FLAGS, STATE_KEYS, _sha, inspect_recording_diagnostics
from .recording_input_run import RecordingInputRunError, _capture
from .scenario_output import GATES, canonical
from .scenario_reference_run import ReferenceCheckError, _identity

ROOT = Path(__file__).resolve().parents[1]
OBSERVED = ('integration_tools/recording_diagnostics_reference.py', 'project/recording_diagnostics_reference.py',
    'tools/recording_diagnostics_reference_worker.py', 'tools/recording_diagnostics_reference.py',
    'integration_tools/recording_input_run.py', 'integration_tools/offline_recording_input_codec.py',
    'integration_tools/offline_recording_preflight.py', 'integration_tools/synthetic_model_input.py',
    'integration_tools/recording_diagnostics_saved.py', 'integration_tools/core_sequence_saved.py',
    'integration_tools/core_sequence_run_inspect.py', 'integration_tools/core_sequence_suite.py',
    'integration_tools/core_sequence_record.py', 'integration_tools/request_snapshot.py',
    'integration_tools/limiter_snapshot.py', 'integration_tools/offline_call_recorder.py',
    'integration_tools/offline_recording_codec.py')


class RecordingReferenceError(ValueError):
    """Fixed public boundary code;late failures may have reference work."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _source_identity() -> dict:
    try:
        identity = _identity(ROOT)
        if any((ROOT / p).is_symlink() for p in OBSERVED):
            raise ValueError('reference symlink')
        identity['declared_reference_sources'] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in OBSERVED}
        return identity
    except (ReferenceCheckError, OSError, ValueError, KeyError) as error:
        raise RecordingReferenceError('RECORDING_REFERENCE_SOURCE_IDENTITY') from error


def _payload(checked) -> dict:
    rows = []
    for current, context in zip(checked.recording.records[1:], checked.contexts, strict=True):
        settings = current.settings
        rows.append({'state': {'index': context.model_index, 'previous_requested': context.previous_integer_request,
            'previous_applied': current.limited_state_at_entry, 'angle_counter': current.angle_counter_at_entry},
            'request_hex': struct.unpack('>f', current.request.requested_binary32)[0].hex(),
            'driver_hex': context.current_driver.hex(), 'angle_hex': context.current_angle_deg.hex(),
            'lat_active': current.inactive_gate_active,
            'limits': [settings.limiter_scale, settings.delta_up, settings.delta_down,
                       settings.driver_allowance, settings.driver_factor, settings.driver_multiplier],
            'saved': {'saved_limited_state': current.saved_limited_state, 'saved_angle_counter': current.saved_angle_counter}})
    return {'schema_version': 1, 'scope': 'CORE69_DECLARED_REFERENCE_INPUT_V1', 'rows': rows}


def _launch(raw: bytes) -> dict:
    try:
        if not 0 < len(raw) <= 1048576:
            raise RecordingReferenceError('RECORDING_REFERENCE_EXECUTION_FAILED_WORK_MAY_BE_NONZERO')
        process = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/recording_diagnostics_reference_worker.py'],
                                 input=raw, capture_output=True, cwd=ROOT, timeout=60, check=False)
        if process.returncode or process.stderr:
            raise RecordingReferenceError('RECORDING_REFERENCE_EXECUTION_FAILED_WORK_MAY_BE_NONZERO')
        if not 0 < len(process.stdout) <= 1048576:
            raise RecordingReferenceError('RECORDING_REFERENCE_RESULT_FAILED_WORK_MAY_BE_NONZERO')
        try:
            return _parse(process.stdout)
        except InspectError as error:
            raise RecordingReferenceError('RECORDING_REFERENCE_RESULT_FAILED_WORK_MAY_BE_NONZERO') from error
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RecordingReferenceError('RECORDING_REFERENCE_EXECUTION_FAILED_WORK_MAY_BE_NONZERO') from error


def _validate_result(result, payload) -> None:
    def need(condition):
        if not condition:
            raise RecordingReferenceError('RECORDING_REFERENCE_RESULT_FAILED_WORK_MAY_BE_NONZERO')
    count = len(payload['rows'])
    need(type(result) is dict and set(result) == {'schema_version', 'contract_id', 'states', 'reference_steps',
                                                'helper_counts', 'python', 'numpy_version', 'forbidden_modules_loaded'})
    need(type(result['schema_version']) is int and result['schema_version'] == 1
         and result['contract_id'] == 'CORE69_DECLARED_REFERENCE_STATES_V1'
         and type(result['reference_steps']) is int and result['reference_steps'] == count
         and result['python'] == '3.12.13' and result['numpy_version'] == '2.5.3'
         and type(result['forbidden_modules_loaded']) is list and result['forbidden_modules_loaded'] == [])
    counts = {'compile_calls': 1, 'selected_definitions_compiled': 2, 'limiter_direct': 0,
              'limiter_traced': count, 'fault_explicit': count, 'fault_default': 0, 'traced_clip_calls': 2 * count}
    need(type(result['helper_counts']) is dict and set(result['helper_counts']) == set(counts))
    need(all(type(result['helper_counts'][k]) is int and result['helper_counts'][k] == v for k, v in counts.items()))
    states = result['states']
    need(type(states) is list and len(states) == count)
    for state, row in zip(states, payload['rows'], strict=True):
        need(type(state) is dict and set(state) == STATE_KEYS)
        need(all(type(state[k]) is int for k in STATE_KEYS)
             and state['index'] == row['state']['index'] + 1 and 0 <= state['angle_counter'] <= 90
             and all(-2048 <= state[k] <= 2048 for k in ('previous_requested', 'previous_applied')))


def check_recording_reference(input_file: Path, input_sha256: str,
                              diagnostics_root: Path, diagnostics_sha256: str) -> dict:
    """Whole shared admission,independent declared-state reference,then exact comparison."""
    if not _sha(input_sha256) or not _sha(diagnostics_sha256):
        raise RecordingReferenceError('RECORDING_REFERENCE_EXPECTED_SHA256')
    inspected = inspect_recording_diagnostics(diagnostics_root, diagnostics_sha256)
    stored = inspected['stored_record']
    if stored['input_sha256'] != input_sha256:
        raise RecordingReferenceError('RECORDING_REFERENCE_INPUT_IDENTITY')
    raw = _capture(input_file)
    if hashlib.sha256(raw).hexdigest() != input_sha256:
        raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_CHECKSUM')
    if stored['input_bytes'] != len(raw):
        raise RecordingReferenceError('RECORDING_REFERENCE_INPUT_IDENTITY')
    checked = decode_recording_input(raw)
    if (platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13' or sys.platform != 'linux'
            or (sys.float_info.radix, sys.float_info.mant_dig) != (2, 53)):
        raise RecordingReferenceError('RECORDING_REFERENCE_RUNTIME')
    payload = _payload(checked)
    identity = _source_identity()
    result = _launch(canonical(payload))
    try:
        if _source_identity() != identity:
            raise RecordingReferenceError('RECORDING_REFERENCE_SOURCE_CHANGED_WORK_MAY_BE_NONZERO')
    except RecordingReferenceError as error:
        raise RecordingReferenceError('RECORDING_REFERENCE_SOURCE_CHANGED_WORK_MAY_BE_NONZERO') from error
    _validate_result(result, payload)
    rows = []
    for i, (row, state) in enumerate(zip(payload['rows'], result['states'], strict=True)):
        differences = [{'field': field, 'declared': row['saved'][field], 'computed': state[key]}
                       for field, key in (('saved_limited_state', 'previous_applied'), ('saved_angle_counter', 'angle_counter'))
                       if row['saved'][field] != state[key]]
        rows.append({'transition_index': i, 'model_index': row['state']['index'], 'status': 'DIFFERENT' if differences else 'MATCH',
            'declared_entry_state': row['state'], 'computed_next_state': state,
            'declared_saved_state': row['saved'], 'differences': differences})
    differing = [i for i, row in enumerate(rows) if row['status'] == 'DIFFERENT']
    count = len(rows)
    projection = {**stored, 'input_sha256': input_sha256, 'input_bytes': len(raw),
        'status': 'DIFFERENT' if differing else 'MATCH', 'frame_count': count + 1,
        'checked_transition_count': count, 'new_synthetic_model_steps': count,
        'differing_transition_indices': differing, 'rows': rows}
    headers = sorted(k for k in stored if k != 'rows' and canonical(stored[k]) != canonical(projection[k]))
    previous = stored['rows']
    indices = [i for i in range(max(len(previous), len(rows)))
               if i >= len(previous) or i >= len(rows) or canonical(previous[i]) != canonical(rows[i])]
    return {'schema_version': 1, 'contract_id': 'CORE69_DECLARED_DIAGNOSTICS_REFERENCE_AUDIT_V1',
        'audit_status': 'REFERENCE_DIFFERENT' if headers or indices else 'REFERENCE_MATCH',
        'audit_exit_code': int(bool(headers or indices)), 'saved_diagnostic_status': stored['status'],
        'reference_diagnostic_status': projection['status'], 'input_sha256': input_sha256, 'input_bytes': len(raw),
        'diagnostics_sha256': inspected['diagnostics_sha256'], 'diagnostics_bytes': inspected['diagnostics_bytes'],
        'recorded_model_steps': stored['new_synthetic_model_steps'], 'new_synthetic_model_steps': 0,
        'new_reference_steps': count, 'reference_helper_counts': result['helper_counts'],
        'reference_runtime': {'python': result['python'], 'numpy': result['numpy_version']},
        'reference_forbidden_modules_loaded': result['forbidden_modules_loaded'], 'reference_identity': identity,
        'reference_independence': 'EXISTING_SELECTED_SOURCE_AND_INTEGER_BIT_ORACLE_NOT_PUBLIC_MODEL',
        'shared_admission_preflight': True, 'numeric_validation_work': 'NONZERO_NOT_AGGREGATED',
        'differing_header_fields': headers, 'differing_transition_indices': indices,
        'stored_record': stored, 'reference_projection': projection, **{name: False for name in FLAGS},
        'gates': dict(GATES),
        'scope': 'BOUNDED_DECLARED_NEXT_STATE_SELECTED_SOURCE_PARITY_NOT_FULL_CONTROLLER_ORIGIN_OR_VEHICLE_PROOF'}
