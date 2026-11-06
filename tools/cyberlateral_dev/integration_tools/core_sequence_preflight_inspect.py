"""Read-only exact saved preflight report/original archive consistency."""

import hashlib
import os
from pathlib import Path

from .core_sequence_archive_preflight import ArchivePreflightError
from .core_sequence_bundle import PortableError, _expected
from .core_sequence_preflight_report import PreflightReportError, report_preflight_archive
from .core_sequence_run_inspect import RunInspectError, _directory, _read_file
from .core_sequence_suite import SuiteError, _path
from .scenario_output import canonical


class PreflightInspectError(ValueError):
    """Fixed diagnostics without raw caller paths or partial success."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def inspect_preflight_report(input_root: Path, input_archive: Path, expected_sha256: str) -> dict:
    """Regenerate once, capture each saved file once and compare exact bytes."""
    try:
        _expected(expected_sha256)
    except PortableError as error:
        raise ArchivePreflightError('ARCHIVE_PREFLIGHT:' + error.code) from error
    try:
        target = _path(input_root, 'PREFLIGHT_INSPECT_PATH')
        with _directory(target, {n: False for n in ('PREFLIGHT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt')}) as directory:
            preflight, markdown = report_preflight_archive(input_archive, expected_sha256)
            code = {'INPUTS_COMPATIBLE': 0, 'INPUTS_REJECTED': 1}[preflight['preflight_status']]
            files = {'PREFLIGHT.json': canonical(preflight), 'SUMMARY_KO.md': markdown}
            files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
                for name, raw in sorted(files.items())).encode()
            for name, raw in files.items():
                if _read_file(directory, name, len(raw)) != raw:
                    raise PreflightInspectError('PREFLIGHT_INSPECT_REPORT_MISMATCH')
            opened, current = os.fstat(directory), target.stat(follow_symlinks=False)
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise PreflightInspectError('PREFLIGHT_INSPECT_ROOT_IDENTITY')
        return {'schema_version': 1, 'contract_id': 'CORE26_SAVED_PREFLIGHT_REPORT_INSPECTION_V1',
            'inspection_status': 'SAVED_PREFLIGHT_REPORT_CONSISTENT', 'inspection_exit_code': 0, 'execution_requested': False,
            'preflight_status': preflight['preflight_status'], 'preflight_exit_code': code,
            'archive_sha256': preflight['archive']['archive_sha256'], 'archive_byte_size': preflight['archive']['archive_byte_size'],
            **{key: preflight[key] for key in ('case_count', 'compatible_case_count', 'rejected_case_count',
                'validated_transition_count', 'declared_transition_count', 'recorded_model_steps')},
            'captured_report_file_count': 3,
            'files': {n: {'sha256': hashlib.sha256(raw).hexdigest(), 'byte_size': len(raw)} for n, raw in files.items()},
            'new_synthetic_model_steps': 0, 'new_reference_steps': 0, 'numeric_validation_work': preflight['numeric_validation_work'],
            **{key: preflight[key] for key in ('source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked',
                'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed')},
            'gates': dict(preflight['gates']), 'scope': 'CAPTURED_PREFLIGHT_REPORT_CONSISTENCY_NOT_ARITHMETIC_OR_ORIGIN_PROOF'}
    except (ArchivePreflightError, PreflightReportError, PreflightInspectError):
        raise
    except (RunInspectError, SuiteError) as error:
        raise PreflightInspectError('PREFLIGHT_INSPECT:' + error.code) from error
    except (OSError, ValueError, RuntimeError) as error:
        raise PreflightInspectError('PREFLIGHT_INSPECT_INPUT') from error
