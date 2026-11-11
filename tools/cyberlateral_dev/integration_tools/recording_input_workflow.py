"""Explicit synthetic diagnosis plus exclusive checked publication;not actual intake."""

import hashlib
from pathlib import Path

from .core_sequence_archive_workflow import _output, _publish
from .recording_input_run import RecordingInputRunError, run_recording_input
from .scenario_output import canonical


class RecordingInputWorkflowError(ValueError):
    """Fixed publication preparation error, possibly after synthetic work."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def publish_recording_input(input_file: Path, expected_sha256: str, output_root: Path) -> dict:
    """Run unchanged CORE61 once;serialize before mkdir,then publish without retry."""
    if type(expected_sha256) is not str or len(expected_sha256) != 64 or any(c not in '0123456789abcdef' for c in expected_sha256):
        raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_SHA256')
    target = _output(output_root)
    result = run_recording_input(input_file, expected_sha256)
    code = {'MATCH': 0, 'DIFFERENT': 1}[result['status']]
    raw = canonical(result)
    if not 0 < len(raw) <= 1048576:
        raise RecordingInputWorkflowError('RECORDING_DIAGNOSTICS_OUTPUT_SIZE_WORK_MAY_BE_NONZERO')
    files = {'DIAGNOSTICS.json': raw,
             'SHA256SUMS.txt': (hashlib.sha256(raw).hexdigest() + '  DIAGNOSTICS.json\n').encode()}
    receipt = {'schema_version': 1, 'contract_id': 'CORE64_RECORDING_INPUT_WORKFLOW_V1',
        'status': 'RECORDING_DIAGNOSTICS_PUBLISHED', 'diagnostic_status': result['status'], 'diagnostic_exit_code': code,
        **{name: result[name] for name in ('input_sha256', 'input_bytes', 'frame_count', 'checked_transition_count',
            'new_synthetic_model_steps', 'differing_transition_indices', 'validation_claim', 'state_feed_rule',
            'first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
            'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed')},
        'gates': dict(result['gates']),
        'files': {name: {'sha256': hashlib.sha256(content).hexdigest(), 'byte_size': len(content)} for name, content in files.items()},
        'scope': 'DECLARED_SYNTHETIC_DIAGNOSTIC_PUBLICATION_NOT_ORIGIN_OR_VEHICLE_PROOF'}
    canonical(receipt)
    _publish(target, files)
    return receipt
