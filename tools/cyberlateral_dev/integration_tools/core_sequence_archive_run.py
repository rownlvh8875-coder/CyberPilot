"""Explicit fixed synthetic run/export/report, never arbitrary or vehicle intake."""

import os
import stat
from contextlib import contextmanager
from pathlib import Path

from .core_sequence_archive_compare import ArchiveCompareError
from .core_sequence_archive_report import ArchiveReportError
from .core_sequence_archive_workflow import ArchiveWorkflowError, _output, _publish, publish_archive_report
from .core_sequence_bundle import PortableError, _expected, verify_suite_bytes
from .core_sequence_portable import _read_archive, export_saved_suite
from .core_sequence_suite import SuiteError, _path, run_closed_suite
from .scenario_output import GATES


class ArchiveRunError(ValueError):
    """Stage-qualified fixed rejection, preserving possible work/output uncertainty."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@contextmanager
def _stage(name: str, suffix: str):
    try:
        yield
    except Exception as error:
        known = (ArchiveCompareError, ArchiveReportError, ArchiveWorkflowError, PortableError, SuiteError)
        detail = error.code if isinstance(error, known) else 'UNEXPECTED'
        raise ArchiveRunError('ARCHIVE_RUN_' + name + ':' + detail + ':' + suffix) from error


def _layout(output: Path) -> None:
    target = _path(output, 'ARCHIVE_RUN_OUTPUT_PATH')
    directory = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        if set(os.listdir(directory)) != {'BASELINE.zip', 'CURRENT.zip', 'suite', 'comparison'}:
            raise OSError('unexpected root layout')
        for name in ('BASELINE.zip', 'CURRENT.zip', 'suite', 'comparison'):
            mode = os.stat(name, dir_fd=directory, follow_symlinks=False).st_mode
            if not (stat.S_ISREG(mode) if name.endswith('.zip') else stat.S_ISDIR(mode)):
                raise OSError('unexpected root member type')
    finally:
        os.close(directory)


def run_archived_suite(baseline: Path, baseline_sha256: str, output_root: Path) -> dict:
    """Validate original once before execution; compare its retained exact copy."""
    with _stage('PREFLIGHT', 'NO_MODEL_EXECUTION'):
        _expected(baseline_sha256)
        target = _output(output_root)
        raw = _read_archive(baseline)
        verified = verify_suite_bytes(raw, baseline_sha256)
    with _stage('BASELINE_COPY', 'NO_MODEL_EXECUTION:OUTPUT_MAY_EXIST'):
        _publish(target, {'BASELINE.zip': raw})
    uncertainty = 'WORK_MAY_BE_NONZERO:OUTPUT_MAY_EXIST'
    with _stage('RUN', uncertainty):
        suite = run_closed_suite(target / 'suite')
    with _stage('EXPORT', uncertainty):
        exported = export_saved_suite(target / 'suite', target / 'CURRENT.zip')
    with _stage('COMPARE', uncertainty):
        compared = publish_archive_report(target / 'BASELINE.zip', baseline_sha256, target / 'CURRENT.zip',
                                         exported['archive_sha256'], target / 'comparison')
    with _stage('FINAL_LAYOUT', uncertainty):
        _layout(target)
    return {'schema_version': 1, 'contract_id': 'CORE17_CLOSED_OFFLINE_ARCHIVE_RUN_V1',
        'status': 'OFFLINE_SYNTHETIC_ARCHIVE_RUN_COMPLETED', 'execution_requested': True,
        'baseline_verification': verified, 'suite_run': suite, 'current_export': exported,
        'comparison_publication': compared, 'comparison_exit_code': compared['comparison_exit_code'],
        'new_synthetic_model_steps': suite['new_synthetic_model_steps'], 'source_identity_reauthenticated': False,
        'gates': dict(GATES), 'scope': 'CLOSED_SYNTHETIC_RUN_AND_SAVED_COMPARISON_NOT_VEHICLE_OR_ORIGIN_AUTHORITY'}
