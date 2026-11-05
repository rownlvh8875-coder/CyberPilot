"""Cross-check a fixed saved run tree without replay, extraction or model imports."""

import hashlib
import os
import stat
from contextlib import contextmanager
from pathlib import Path

from .core_sequence_archive_compare import ArchiveCompareError, _preflight
from .core_sequence_archive_report import ArchiveReportError, report_suite_archive_bytes
from .core_sequence_bundle import PortableError, build_suite_archive
from .core_sequence_cases import CASE_IDS
from .core_sequence_portable import _read_archive
from .core_sequence_saved import InspectError, _capture
from .core_sequence_suite import SuiteError, _path, _root
from .scenario_output import GATES, canonical


class RunInspectError(ValueError):
    """Fixed saved-only rejection; never a partial receipt or raw caller text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _layout(directory: int, expected: dict[str, bool]) -> None:
    if set(os.listdir(directory)) != set(expected):
        raise RunInspectError('RUN_INSPECT_LAYOUT')
    for name, is_directory in expected.items():
        mode = os.stat(name, dir_fd=directory, follow_symlinks=False).st_mode
        if not (stat.S_ISDIR(mode) if is_directory else stat.S_ISREG(mode)):
            raise RunInspectError('RUN_INSPECT_FILE_TYPE')


@contextmanager
def _directory(path: Path, expected: dict[str, bool]):
    target = _path(path, 'RUN_INSPECT_PATH')
    directory = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        _layout(directory, expected)
        yield directory
        _layout(directory, expected)
    finally:
        os.close(directory)


def _read_file(directory: int, name: str, cap: int) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise RunInspectError('RUN_INSPECT_FILE_TYPE')
        if info.st_size > cap:
            raise RunInspectError('RUN_INSPECT_SIZE')
        chunks, size = [], 0
        while size <= cap:
            raw = os.read(fd, cap + 1 - size)
            if not raw:
                break
            chunks.append(raw); size += len(raw)
        if size > cap:
            raise RunInspectError('RUN_INSPECT_SIZE')
        return b''.join(chunks)
    finally:
        os.close(fd)


def inspect_archived_run(input_root: Path, baseline_sha256: str, current_sha256: str) -> dict:
    """Each saved file captured once; regenerate report only from verified archives."""
    try:
        _preflight(baseline_sha256, current_sha256)
        captured = {}
        with _directory(input_root, {'BASELINE.zip': False, 'CURRENT.zip': False, 'suite': True, 'comparison': True}):
            root = _path(input_root, 'RUN_INSPECT_PATH')
            captured['BASELINE.zip'] = _read_archive(root / 'BASELINE.zip')
            captured['CURRENT.zip'] = _read_archive(root / 'CURRENT.zip')
            comparison, markdown = report_suite_archive_bytes(captured['BASELINE.zip'], baseline_sha256, captured['CURRENT.zip'], current_sha256)
            suite_files = {}
            with _root(root / 'suite', 'INPUT') as suite:
                for case in CASE_IDS:
                    try:
                        source = _capture(suite / case)
                    except InspectError as error:
                        raise SuiteError('RUN_INSPECT_CASE:' + case + ':' + error.code) from error
                    suite_files.update({'suite/' + case + '/' + n: raw for n, raw in source.items()})
            if build_suite_archive(suite_files) != captured['CURRENT.zip']:
                raise RunInspectError('RUN_INSPECT_SUITE_MISMATCH')
            captured.update(suite_files)
            expected = {'COMPARISON.json': canonical(comparison), 'SUMMARY_KO.md': markdown}
            expected['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + n + '\n' for n, raw in sorted(expected.items())).encode()
            with _directory(root / 'comparison', {n: False for n in expected}) as directory:
                for name, raw in expected.items():
                    actual = _read_file(directory, name, len(raw))
                    if actual != raw:
                        raise RunInspectError('RUN_INSPECT_REPORT_MISMATCH')
                    captured['comparison/' + name] = actual
        return {'schema_version': 1, 'contract_id': 'CORE18_SAVED_ARCHIVE_RUN_INSPECTION_V1',
            'inspection_status': 'SAVED_ARCHIVE_RUN_CONSISTENT', 'execution_requested': False,
            'captured_file_count': len(captured), 'captured_file_sha256': {n: hashlib.sha256(raw).hexdigest() for n, raw in sorted(captured.items())},
            'baseline': comparison['left'], 'current': comparison['right'], 'comparison_status': comparison['comparison_status'],
            'comparison_exit_code': 0 if comparison['archive_bytes_identical'] else 1,
            'difference_count': comparison['difference_count'], 'difference_counts': comparison['difference_counts'],
            'recorded_current_model_steps': comparison['right']['suite']['recorded_model_steps'],
            'new_synthetic_model_steps': 0, 'inspection_model_executions': 0, 'inspection_reference_executions': 0,
            'source_identity_reauthenticated': False, 'arithmetic_recomputed': False, 'gates': dict(GATES),
            'scope': 'CAPTURED_RUN_CROSS_ARTIFACT_CONSISTENCY_NOT_EXECUTION_OR_ORIGIN_PROOF'}
    except RunInspectError:
        raise
    except (ArchiveCompareError, ArchiveReportError, PortableError, InspectError, SuiteError) as error:
        raise RunInspectError('RUN_INSPECT:' + error.code) from error
    except (OSError, ValueError, RuntimeError) as error:
        raise RunInspectError('RUN_INSPECT_INPUT') from error
