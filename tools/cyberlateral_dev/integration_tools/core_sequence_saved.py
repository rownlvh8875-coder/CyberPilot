"""Bounded read-only capture of saved CORE8 records, not numerical replay."""

import hashlib
import json
import os
import stat
from pathlib import Path

from .core_sequence_record import InspectError, validate_records
from .scenario_output import canonical

CAPS = {'INPUT.json': 65536, 'RESULTS.json': 524288, 'SHA256SUMS.txt': 512}


def _capture(input_path: Path) -> dict[str, bytes]:
    if not isinstance(input_path, Path):
        raise InspectError('INSPECT_INPUT_FILE')
    try:
        path = input_path.absolute()
        text = str(path)
        text.encode('utf-8', errors='strict')
        if '\0' in text or any(p.is_symlink() for p in (path, *path.parents)):
            raise InspectError('INSPECT_INPUT_FILE')
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        directory = os.open(path, flags | os.O_DIRECTORY)
        try:
            if set(os.listdir(directory)) != set(CAPS):
                raise InspectError('INSPECT_FILES')
            captured = {}
            for name, cap in CAPS.items():
                fd = os.open(name, flags, dir_fd=directory)
                try:
                    info = os.fstat(fd)
                    if not stat.S_ISREG(info.st_mode):
                        raise InspectError('INSPECT_INPUT_FILE')
                    if info.st_size > cap:
                        raise InspectError('INSPECT_SIZE')
                    chunks, size = [], 0
                    while size <= cap:
                        chunk = os.read(fd, cap + 1 - size)
                        if not chunk:
                            break
                        chunks.append(chunk)
                        size += len(chunk)
                    if size > cap:
                        raise InspectError('INSPECT_SIZE')
                    captured[name] = b''.join(chunks)
                finally:
                    os.close(fd)
            if set(os.listdir(directory)) != set(CAPS):
                raise InspectError('INSPECT_FILES')
            return captured
        finally:
            os.close(directory)
    except InspectError:
        raise
    except (OSError, ValueError, RuntimeError) as error:
        raise InspectError('INSPECT_INPUT_FILE') from error


def _invalid(*_args):
    raise InspectError('INSPECT_JSON')


def _pairs(items):
    record = {}
    for key, value in items:
        if key in record:
            _invalid()
        record[key] = value
    return record


def _int(token):
    if len(token) > 32:
        _invalid()
    return int(token)


def _parse(raw: bytes):
    try:
        value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_pairs,
                           parse_int=_int, parse_float=_invalid, parse_constant=_invalid)
        pending = [(value, 0)]
        while pending:
            node, depth = pending.pop()
            if type(node) in (dict, list):
                if depth >= 64:
                    _invalid()
                pending.extend((child, depth + 1) for child in (node.values() if type(node) is dict else node))
        encoded = canonical(value)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise InspectError('INSPECT_JSON') from error
    if encoded != raw:
        raise InspectError('INSPECT_CANONICAL')
    return value


def _decode(files: dict[str, bytes]) -> dict:
    """Validate already captured CORE9 bytes without any filesystem access."""
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}
    manifest = ''.join(hashes[name] + '  ' + name + '\n' for name in ('INPUT.json', 'RESULTS.json')).encode()
    if files['SHA256SUMS.txt'] != manifest:
        raise InspectError('INSPECT_CHECKSUM')
    input_record, result_record = _parse(files['INPUT.json']), _parse(files['RESULTS.json'])
    summary = {**validate_records(input_record, result_record), 'captured_sha256': hashes}
    return {'input_record': input_record, 'result_record': result_record, 'summary': summary}


def read_saved_sequence_records(input_path: Path) -> dict:
    """Capture/validate once and expose owned records, never reopen their files."""
    return _decode(_capture(input_path))


def inspect_saved_sequence(input_path: Path) -> dict:
    """Checksum captured bytes and compare stored relations; no authenticity claim."""
    return read_saved_sequence_records(input_path)['summary']


def format_saved_sequence(input_path: Path, output_format: str = 'json') -> bytes:
    if type(output_format) is not str or output_format not in ('json', 'markdown'):
        raise InspectError('INSPECT_FORMAT')
    summary = inspect_saved_sequence(input_path)
    if output_format == 'json':
        return canonical(summary)
    lines = ['# CORE9 저장 기록 조회', '', '조회: SAVED_RECORDS_CONSISTENT (새 수치 판정 아님)', '',
             '저장 case: ' + summary['case_id'], '저장 status: ' + summary['saved_status'],
             '저장 rejection: ' + str(summary['saved_rejection_code']),
             '저장 model steps: ' + str(summary['recorded_model_steps']),
             '조회 신규 모델 실행: 0 / 신규 reference 실행: 0', '',
             '| 전이 | 저장 판정 | 저장 명령 | 기록된 계산 명령 | 저장 counter | 기록된 계산 counter |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in summary['rows']:
        lines.append('| ' + ' | '.join(str(row[key]) for key in ('transition_index', 'status', 'saved_limited_state',
                     'computed_limited_state', 'saved_angle_counter', 'computed_angle_counter')) + ' |')
    lines.extend(['', '한계: captured bytes checksum 및 저장 관계만 확인. 산술 재계산·원본 인증·현재 소스 인증 없음.',
                  'anchor/prehistory 미검증. 일관되게 조작한 기록은 탐지하지 못할 수 있습니다.',
                  'R_BUDGET=UNRESOLVED; Static Evidence Gate=FAIL; 실제 r/T2/scale=null; 실차 활성화 금지.', ''])
    return '\n'.join(lines).encode()
