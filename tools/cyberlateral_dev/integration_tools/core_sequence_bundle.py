"""Bounded canonical ZIP bytes for saved suites; no extraction or model imports."""

import hashlib
import io
import re
import struct
import zipfile

from .core_sequence_cases import CASE_IDS
from .core_sequence_saved import CAPS, InspectError, _decode
from .core_sequence_suite import _summary
from .core_sequence_workflow import _report
from .scenario_output import GATES, canonical

ARCHIVE_CAP = 2_000_000
SOURCE_CAPS = {'suite/' + c + '/' + n: cap for c in CASE_IDS for n, cap in CAPS.items()}
MEMBER_CAPS = {**SOURCE_CAPS, 'SUITE_REPORT.json': 65536, 'SHA256SUMS.txt': 4096}


class PortableError(ValueError):
    """Fixed diagnostics only; checksums are not origin or arithmetic proof."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _expected(value: str) -> None:
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise PortableError('PORTABLE_EXPECTED_SHA256')


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _bounded_files(files: dict[str, bytes], caps: dict[str, int]) -> None:
    if type(files) is not dict or set(files) != set(caps):
        raise PortableError('PORTABLE_ZIP_MEMBERS')
    if any(type(files[n]) is not bytes or len(files[n]) > cap for n, cap in caps.items()):
        raise PortableError('PORTABLE_ZIP_SIZE')


def _suite(files: dict[str, bytes]) -> dict:
    reports = []
    for case in CASE_IDS:
        try:
            record = _decode({n: files['suite/' + case + '/' + n] for n in CAPS})
        except InspectError as error:
            raise PortableError('PORTABLE_CASE:' + case + ':' + error.code) from error
        if record['summary']['case_id'] != case:
            raise PortableError('PORTABLE_CASE_ID:' + case)
        reports.append(_report('CHECK_SAVED_ONLY', record, None, 0))
    return _summary('CHECK_SAVED_SUITE', reports, False)


def _manifest(files: dict[str, bytes]) -> bytes:
    return ''.join(_sha(files[n]) + '  ' + n + '\n' for n in sorted(files) if n != 'SHA256SUMS.txt').encode()


def _zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, files[name])
    return buffer.getvalue()


def build_suite_archive(source_files: dict[str, bytes]) -> bytes:
    """Preserve original nine files and derive only the saved-only custody report."""
    _bounded_files(source_files, SOURCE_CAPS)
    files = {**source_files, 'SUITE_REPORT.json': canonical(_suite(source_files))}
    files['SHA256SUMS.txt'] = _manifest(files)
    _bounded_files(files, MEMBER_CAPS)
    raw = _zip(files)
    if len(raw) > ARCHIVE_CAP:
        raise PortableError('PORTABLE_ARCHIVE_SIZE')
    return raw


def _members(raw: bytes) -> dict[str, bytes]:
    # Bound central directory parsing before handing attacker-controlled bytes to
    # ZipFile. Fixed uncompressed member caps also bound all subsequent reads.
    if len(raw) < 22:
        raise PortableError('PORTABLE_ZIP_FORMAT')
    magic, disk, cd_disk, count_disk, count, size, offset, comment = struct.unpack('<4s4H2LH', raw[-22:])
    if (magic != b'PK\x05\x06' or disk != 0 or cd_disk != 0 or count_disk != 11 or count != 11
            or comment != 0 or not 506 <= size <= 4096 or offset + size != len(raw) - 22):
        raise PortableError('PORTABLE_ZIP_FORMAT')
    try:
        with zipfile.ZipFile(io.BytesIO(raw), 'r') as archive:
            infos = archive.infolist()
            if len(infos) != 11 or {info.filename for info in infos} != set(MEMBER_CAPS):
                raise PortableError('PORTABLE_ZIP_MEMBERS')
            files = {}
            for info in infos:
                if (info.filename != info.orig_filename or info.filename in files or info.is_dir()
                        or info.compress_type != zipfile.ZIP_STORED or info.flag_bits != 0
                        or info.external_attr != 0o100644 << 16 or info.create_system != 3):
                    raise PortableError('PORTABLE_ZIP_MEMBERS')
                cap = MEMBER_CAPS[info.filename]
                if not 0 <= info.file_size <= cap or info.compress_size != info.file_size:
                    raise PortableError('PORTABLE_ZIP_SIZE')
                with archive.open(info, 'r') as member:
                    data = member.read(cap + 1)
                if len(data) != info.file_size or len(data) > cap:
                    raise PortableError('PORTABLE_ZIP_SIZE')
                files[info.filename] = data
            return files
    except PortableError:
        raise
    except (zipfile.BadZipFile, OSError, ValueError, RuntimeError, NotImplementedError, UnicodeError, struct.error) as error:
        raise PortableError('PORTABLE_ZIP_FORMAT') from error


def verify_suite_bytes(raw: bytes, expected_sha256: str) -> dict:
    """Verify explicit external SHA and bounded self-consistency, never authority."""
    _expected(expected_sha256)
    if type(raw) is not bytes:
        raise PortableError('PORTABLE_ARCHIVE_FILE')
    if len(raw) > ARCHIVE_CAP:
        raise PortableError('PORTABLE_ARCHIVE_SIZE')
    if _sha(raw) != expected_sha256:
        raise PortableError('PORTABLE_ARCHIVE_CHECKSUM')
    files = _members(raw)
    if files['SHA256SUMS.txt'] != _manifest(files):
        raise PortableError('PORTABLE_MANIFEST')
    suite = _suite(files)
    if files['SUITE_REPORT.json'] != canonical(suite):
        raise PortableError('PORTABLE_REPORT')
    if raw != _zip(files):
        raise PortableError('PORTABLE_ZIP_CANONICAL')
    return {'schema_version': 1, 'contract_id': 'CORE13_PORTABLE_SAVED_SUITE_V1',
        'operation': 'VERIFY_SAVED_SUITE_ARCHIVE', 'status': 'SUITE_ARCHIVE_VERIFIED',
        'archive_sha256': expected_sha256, 'archive_byte_size': len(raw), 'member_count': 11, 'source_member_count': 9,
        'member_sha256': {name: _sha(files[name]) for name in sorted(files)}, 'suite': suite,
        'new_synthetic_model_steps': 0, 'reader_model_executions': 0, 'reader_reference_executions': 0,
        'source_identity_reauthenticated': False, 'gates': dict(GATES),
        'scope': 'SAVED_SUITE_BYTES_CUSTODY_NOT_ARITHMETIC_OR_ORIGIN_PROOF'}
