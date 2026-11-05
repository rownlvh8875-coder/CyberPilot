"""Single-capture saved-suite export and bounded read-only ZIP verification."""

import os
import stat
from pathlib import Path

from .core_sequence_bundle import ARCHIVE_CAP, PortableError, _expected, _sha, build_suite_archive, verify_suite_bytes
from .core_sequence_cases import CASE_IDS
from .core_sequence_saved import InspectError, _capture
from .core_sequence_suite import ROOT, SuiteError, _path, _root


def _safe_path(value: Path, code: str) -> Path:
    try:
        return _path(value, code)
    except SuiteError as error:
        raise PortableError(error.code) from error


def _read_archive(path: Path) -> bytes:
    target = _safe_path(path, 'PORTABLE_ARCHIVE_FILE')
    try:
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise PortableError('PORTABLE_ARCHIVE_FILE')
            if info.st_size > ARCHIVE_CAP:
                raise PortableError('PORTABLE_ARCHIVE_SIZE')
            chunks, size = [], 0
            while size <= ARCHIVE_CAP:
                data = os.read(fd, ARCHIVE_CAP + 1 - size)
                if not data:
                    break
                chunks.append(data)
                size += len(data)
            if size > ARCHIVE_CAP:
                raise PortableError('PORTABLE_ARCHIVE_SIZE')
            return b''.join(chunks)
        finally:
            os.close(fd)
    except PortableError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise PortableError('PORTABLE_ARCHIVE_FILE') from error


def verify_suite_archive(archive: Path, expected_sha256: str) -> dict:
    """Require a complete external digest before touching caller filesystem paths."""
    _expected(expected_sha256)
    return verify_suite_bytes(_read_archive(archive), expected_sha256)


def _output(path: Path) -> Path:
    target = _safe_path(path, 'PORTABLE_OUTPUT_PATH')
    try:
        if target.exists():
            raise PortableError('PORTABLE_OUTPUT_EXISTS')
        if not target.parent.is_dir():
            raise PortableError('PORTABLE_OUTPUT_PARENT')
        if target.resolve().is_relative_to(ROOT.parents[1].resolve()):
            raise PortableError('PORTABLE_OUTPUT_LOCATION')
        return target
    except PortableError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise PortableError('PORTABLE_OUTPUT_PATH') from error


def export_saved_suite(input_root: Path, output: Path) -> dict:
    """Validate/capture everything before exclusive publication; never replay."""
    target = _output(output)
    files = {}
    try:
        with _root(input_root, 'INPUT') as source:
            if target.resolve().is_relative_to(source.resolve()):
                raise SuiteError('PORTABLE_OUTPUT_SOURCE_OVERLAP')
            for case in CASE_IDS:
                try:
                    captured = _capture(source / case)
                except InspectError as error:
                    raise SuiteError('PORTABLE_CASE:' + case + ':' + error.code) from error
                files.update({'suite/' + case + '/' + n: data for n, data in captured.items()})
    except SuiteError as error:
        code = error.code if error.code.startswith('PORTABLE_') else 'PORTABLE_SOURCE:' + error.code
        raise PortableError(code) from error
    raw = build_suite_archive(files)
    digest = _sha(raw)
    report = verify_suite_bytes(raw, digest)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600)
        try:
            pending = memoryview(raw)
            while pending:
                written = os.write(fd, pending)
                if written <= 0:
                    raise OSError('no write progress')
                pending = pending[written:]
        finally:
            os.close(fd)
    except (OSError, ValueError, RuntimeError) as error:
        raise PortableError('PORTABLE_PUBLICATION_FAILED_PARTIAL_FILE_POSSIBLE') from error
    try:
        published = _read_archive(target)
        if published != raw:
            raise PortableError('PORTABLE_PUBLISHED_ARCHIVE_MISMATCH_PARTIAL_FILE_POSSIBLE')
        verify_suite_bytes(published, digest)
    except PortableError as error:
        if error.code == 'PORTABLE_PUBLISHED_ARCHIVE_MISMATCH_PARTIAL_FILE_POSSIBLE':
            raise
        raise PortableError('PORTABLE_PUBLICATION_CHECK_FAILED_FILE_MAY_EXIST') from error
    except (OSError, ValueError, RuntimeError) as error:
        raise PortableError('PORTABLE_PUBLICATION_CHECK_FAILED_FILE_MAY_EXIST') from error
    return {**report, 'operation': 'EXPORT_SAVED_SUITE', 'status': 'SUITE_ARCHIVE_EXPORTED'}
