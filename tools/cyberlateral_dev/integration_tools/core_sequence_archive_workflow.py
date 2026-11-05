"""Exclusive saved-only comparison/Markdown publication; never numerical replay."""

import hashlib
import os
import stat
from pathlib import Path

from .core_sequence_archive_compare import _preflight, exit_code
from .core_sequence_archive_report import report_suite_archives
from .core_sequence_suite import ROOT, SuiteError, _path
from .scenario_output import GATES, canonical


class ArchiveWorkflowError(ValueError):
    """Fixed diagnostics retain publication uncertainty without raw caller data."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _output(path: Path) -> Path:
    try:
        target = _path(path, 'ARCHIVE_WORKFLOW_OUTPUT_PATH')
        if target.exists():
            raise ArchiveWorkflowError('ARCHIVE_WORKFLOW_OUTPUT_EXISTS')
        if not target.parent.is_dir():
            raise ArchiveWorkflowError('ARCHIVE_WORKFLOW_OUTPUT_PARENT')
        if target.resolve().is_relative_to(ROOT.parents[1].resolve()):
            raise ArchiveWorkflowError('ARCHIVE_WORKFLOW_OUTPUT_LOCATION')
        return target
    except SuiteError as error:
        raise ArchiveWorkflowError(error.code) from error
    except (OSError, ValueError, RuntimeError) as error:
        if isinstance(error, ArchiveWorkflowError):
            raise
        raise ArchiveWorkflowError('ARCHIVE_WORKFLOW_OUTPUT_PATH') from error


def _write(directory: int, name: str, raw: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600, dir_fd=directory)
    try:
        pending = memoryview(raw)
        while pending:
            written = os.write(fd, pending)
            if written <= 0:
                raise OSError('no write progress')
            pending = pending[written:]
    finally:
        os.close(fd)


def _readback(directory: int, name: str, expected: bytes) -> None:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size != len(expected):
            raise OSError('published file shape')
        chunks, size = [], 0
        while size <= len(expected):
            raw = os.read(fd, len(expected) + 1 - size)
            if not raw:
                break
            chunks.append(raw)
            size += len(raw)
        if b''.join(chunks) != expected:
            raise OSError('published file mismatch')
    finally:
        os.close(fd)


def _publish(target: Path, files: dict[str, bytes]) -> None:
    try:
        target.mkdir(mode=0o700, exist_ok=False)
        directory = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except (OSError, ValueError, RuntimeError) as error:
        raise ArchiveWorkflowError('ARCHIVE_WORKFLOW_PUBLICATION_FAILED_PARTIAL_DIRECTORY_POSSIBLE') from error
    try:
        try:
            for name, raw in files.items():
                _write(directory, name, raw)
        except (OSError, ValueError, RuntimeError) as error:
            raise ArchiveWorkflowError('ARCHIVE_WORKFLOW_PUBLICATION_FAILED_PARTIAL_DIRECTORY_POSSIBLE') from error
        try:
            if set(os.listdir(directory)) != set(files):
                raise OSError('published layout')
            for name, raw in files.items():
                _readback(directory, name, raw)
            info = os.fstat(directory)
            current = target.stat(follow_symlinks=False)
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino) or set(os.listdir(directory)) != set(files):
                raise OSError('published directory identity')
        except (OSError, ValueError, RuntimeError) as error:
            raise ArchiveWorkflowError('ARCHIVE_WORKFLOW_PUBLICATION_CHECK_FAILED_DIRECTORY_MAY_EXIST') from error
    finally:
        try:
            os.close(directory)
        except OSError as error:
            raise ArchiveWorkflowError('ARCHIVE_WORKFLOW_PUBLICATION_CHECK_FAILED_DIRECTORY_MAY_EXIST') from error


def publish_archive_report(left: Path, left_sha256: str, right: Path, right_sha256: str, output_root: Path) -> dict:
    """Preflight both digests, capture/compare once and publish exact report bytes."""
    _preflight(left_sha256, right_sha256)
    target = _output(output_root)
    comparison, markdown = report_suite_archives(left, left_sha256, right, right_sha256)
    files = {'COMPARISON.json': canonical(comparison), 'SUMMARY_KO.md': markdown}
    files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()
    _publish(target, files)
    return {'schema_version': 1, 'contract_id': 'CORE16_ARCHIVE_WORKFLOW_V1', 'status': 'ARCHIVE_REPORT_PUBLISHED',
        'comparison_status': comparison['comparison_status'], 'comparison_exit_code': exit_code(comparison),
        'files': {n: {'sha256': hashlib.sha256(raw).hexdigest(), 'byte_size': len(raw)} for n, raw in files.items()},
        'new_synthetic_model_steps': 0, 'comparison_model_executions': 0, 'comparison_reference_executions': 0,
        'source_identity_reauthenticated': False, 'arithmetic_recomputed': False, 'gates': dict(GATES),
        'scope': 'VERIFIED_SAVED_REPORT_PUBLICATION_NOT_ARITHMETIC_OR_ORIGIN_PROOF'}
