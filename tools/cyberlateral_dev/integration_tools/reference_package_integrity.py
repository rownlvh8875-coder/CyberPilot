"""Pinned three-file byte integrity and narrow envelope;never stored audit semantics."""

import hashlib
import os
from pathlib import Path

from .core_sequence_run_inspect import RunInspectError, _directory, _read_file
from .core_sequence_saved import InspectError, _parse
from .core_sequence_suite import SuiteError, _path
from .recording_diagnostics_saved import FLAGS, _sha
from .scenario_output import GATES, canonical

CAPS = {'REFERENCE_AUDIT.json': 2097152, 'SUMMARY_KO.md': 65536, 'SHA256SUMS.txt': 512}


class ReferencePackageIntegrityError(ValueError):
    """Fixed integrity-only error,without caller text or implicit replay."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _envelope(value: dict) -> None:
    """Known identification/gates only;other body keys have no validated meaning here."""
    if not (type(value.get('schema_version')) is int and value['schema_version'] == 1
            and value.get('contract_id') == 'CORE69_DECLARED_DIAGNOSTICS_REFERENCE_AUDIT_V1'
            and value.get('scope') == 'BOUNDED_DECLARED_NEXT_STATE_SELECTED_SOURCE_PARITY_NOT_FULL_CONTROLLER_ORIGIN_OR_VEHICLE_PROOF'
            and all(name in value and value[name] is False for name in FLAGS)
            and canonical(value.get('gates')) == canonical(GATES)):
        raise ReferencePackageIntegrityError('REFERENCE_PACKAGE_ENVELOPE')


def inspect_reference_package(input_root: Path, expected_manifest_sha256: str) -> dict:
    """Capture/check bytes once;no interpretation of saved audit status,rows or identity."""
    if not _sha(expected_manifest_sha256):
        raise ReferencePackageIntegrityError('REFERENCE_PACKAGE_EXPECTED_MANIFEST_SHA256')
    try:
        target = _path(input_root, 'REFERENCE_PACKAGE_INPUT')
        with _directory(target, {name: False for name in CAPS}) as directory:
            captured = {name: _read_file(directory, name, cap) for name, cap in CAPS.items()}
            opened, current = os.fstat(directory), target.stat(follow_symlinks=False)
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino) or any(not raw for raw in captured.values()):
                raise ValueError('captured input shape')
    except (RunInspectError, SuiteError, OSError, ValueError, RuntimeError) as error:
        raise ReferencePackageIntegrityError('REFERENCE_PACKAGE_INPUT') from error
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in captured.items()}
    manifest = ''.join(hashes[name] + '  ' + name + '\n' for name in ('REFERENCE_AUDIT.json', 'SUMMARY_KO.md')).encode()
    if hashes['SHA256SUMS.txt'] != expected_manifest_sha256 or captured['SHA256SUMS.txt'] != manifest:
        raise ReferencePackageIntegrityError('REFERENCE_PACKAGE_CHECKSUM')
    try:
        value = _parse(captured['REFERENCE_AUDIT.json'])
        if type(value) is not dict:
            raise ValueError('JSON object required')
    except (InspectError, ValueError, TypeError) as error:
        raise ReferencePackageIntegrityError('REFERENCE_PACKAGE_JSON') from error
    _envelope(value)
    try:
        captured['SUMMARY_KO.md'].decode('utf-8', errors='strict')
    except UnicodeError as error:
        raise ReferencePackageIntegrityError('REFERENCE_PACKAGE_SUMMARY_UTF8') from error
    return {'schema_version': 1, 'contract_id': 'CORE71_REFERENCE_PACKAGE_INTEGRITY_INSPECTION_V1',
        'inspection_status': 'REFERENCE_PACKAGE_INTEGRITY_VERIFIED', 'inspection_exit_code': 0,
        'manifest_sha256': hashes['SHA256SUMS.txt'], 'captured_file_count': 3,
        'files': {name: {'sha256': hashes[name], 'byte_size': len(raw)} for name, raw in captured.items()},
        'envelope_validation': 'CORE69_IDENTIFICATION_AND_CLOSED_AUTHORITY_FLAGS_ONLY',
        'audit_semantics_validated': False, 'summary_consistency_checked': False, 'recorded_work_counts_validated': False,
        'original_input_verified': False, 'arithmetic_recomputed': False, 'new_synthetic_model_steps': 0, 'new_reference_steps': 0,
        **{name: False for name in FLAGS}, 'gates': dict(GATES),
        'scope': 'CAPTURED_THREE_FILE_INTEGRITY_ENVELOPE_NOT_AUDIT_SEMANTIC_NUMERICAL_OR_ORIGIN_PROOF'}
