"""Explicit current-algorithm synthetic replay;not origin or independent proof."""

import hashlib
from pathlib import Path

from .recording_diagnostics_saved import FLAGS, _sha, inspect_recording_diagnostics
from .recording_input_run import RecordingInputRunError, _capture, _diagnose_captured
from .scenario_output import GATES, canonical


class DiagnosticsAuditError(ValueError):
    """Fixed audit pre-execution failure,never caller paths or input content."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def audit_recording_diagnostics(input_file: Path, input_sha256: str,
                                diagnostics_root: Path, diagnostics_sha256: str) -> dict:
    """Capture both artifacts once,then replay exactly one complete synthetic input."""
    if not _sha(input_sha256) or not _sha(diagnostics_sha256):
        raise DiagnosticsAuditError('DIAGNOSTICS_AUDIT_EXPECTED_SHA256')
    inspected = inspect_recording_diagnostics(diagnostics_root, diagnostics_sha256)
    stored = inspected['stored_record']
    if stored['input_sha256'] != input_sha256:
        raise DiagnosticsAuditError('DIAGNOSTICS_AUDIT_INPUT_IDENTITY')
    raw = _capture(input_file)
    if hashlib.sha256(raw).hexdigest() != input_sha256:
        raise RecordingInputRunError('RECORDING_DIAGNOSTICS_INPUT_CHECKSUM')
    if stored['input_bytes'] != len(raw):
        raise DiagnosticsAuditError('DIAGNOSTICS_AUDIT_INPUT_IDENTITY')
    recomputed = _diagnose_captured(raw)
    headers = sorted(k for k in stored if k != 'rows' and canonical(stored[k]) != canonical(recomputed[k]))
    old_rows, new_rows = stored['rows'], recomputed['rows']
    indices = [i for i in range(max(len(old_rows), len(new_rows)))
               if i >= len(old_rows) or i >= len(new_rows) or canonical(old_rows[i]) != canonical(new_rows[i])]
    different = bool(headers or indices)
    return {'schema_version': 1, 'contract_id': 'CORE68_SYNTHETIC_DIAGNOSTICS_AUDIT_V1',
        'audit_status': 'DIFFERENT' if different else 'REPRODUCED', 'audit_exit_code': int(different),
        'saved_diagnostic_status': stored['status'], 'recomputed_diagnostic_status': recomputed['status'],
        'input_sha256': input_sha256, 'input_bytes': len(raw),
        'diagnostics_sha256': inspected['diagnostics_sha256'], 'diagnostics_bytes': inspected['diagnostics_bytes'],
        'recorded_model_steps': stored['new_synthetic_model_steps'],
        'new_synthetic_model_steps': recomputed['new_synthetic_model_steps'], 'new_reference_steps': 0,
        'differing_header_fields': headers, 'differing_transition_indices': indices,
        'stored_record': stored, 'recomputed_record': recomputed, 'arithmetic_recomputed': True,
        'supplied_input_bytes_verified': True, 'independent_numerical_oracle': False,
        'numeric_validation_work': 'NONZERO_NOT_AGGREGATED', **{name: False for name in FLAGS},
        'gates': dict(GATES),
        'scope': 'SUPPLIED_SYNTHETIC_INPUT_RECOMPUTATION_NOT_ORIGIN_OR_INDEPENDENT_OR_VEHICLE_PROOF'}
