"""Deterministic data-only fixed audit export and bounded repository-based verification."""

import argparse
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # DEV stdlib glue, never src/reference/native selectors.

from integration_tools.handoff_audit import canonical, read_audit_pair

ZIP_NAME = 'F70UGZ_R18_AUDIT_BUNDLE.zip'
MAX_ARCHIVE = MAX_UNPACKED = 8 * 1024 * 1024
MAX_MEMBER = 4 * 1024 * 1024
DATA_NAMES = tuple(sorted(
    [f'lifecycle_{side}/{name}' for side in ['one', 'two'] for name in ['RESULTS.json', 'SHA256SUMS.txt']]
    + [f'audit_{side}/{name}' for side in ['one', 'two'] for name in ['AUDIT.json', 'audit.csv', 'SUMMARY_KO.md', 'EXECUTION.json', 'SHA256SUMS.txt']]
))
README = '''# 고정 합성 감사 근거 보관용 ZIP

R16 근거 쌍과 R17 보고서 쌍의 정확한 데이터14개 및 metadata/Manifest입니다.
실행 코드·wheel·차량 설치 파일은 없습니다. 자체 서명/원본 출처 인증이 아닙니다.
검산에는 동일 저장소의 신뢰된 tools/cyberlateral_dev 도구/기준 자료가 필요합니다.
CPython3.12.13에서 저장소 root 기준으로 실행하세요. 별도 모델 설치/실행은 없습니다.

python -I -B tools/cyberlateral_dev/integration_tools/audit_bundle.py verify --bundle ZIP_PATH

검산은 고정17항목/크기/CRC/해시/기존 합성 계약/정확한 ZIP bytes를 확인합니다.
영구 추출·입력 수정·Controller/Runtime/CAN/F61 실행을 하지 않습니다.
ZIP header의1980 시각은 형식용 상수이며 실제 생성/sample/차량 시각이 아닙니다.
source9010회와 report/bundle0회를 구분합니다. 새 수학·성능·안전 증명이 아닙니다.
history-scale seed는 선언값이며 관측된 이전 호출이 아닙니다. 시간은 호출 순서입니다.
CSV 표시 변환이 가능하므로 정밀도는 JSON/hex로 확인하세요.
실제 r/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL,
Candidate/Runtime NO_GO, actual activation/F70UH/F70V/F71 NOT_ALLOWED 유지.
'''.encode()


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _manifest(files):
    return ''.join(_sha(raw) + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()


def _collect_snapshot(root: Path) -> dict[str, bytes]:
    record, audit, summary = read_audit_pair(root / 'audit_one', root / 'audit_two', root / 'lifecycle_one', root / 'lifecycle_two')
    source = canonical(record)
    _require(_sha(source) == summary['input_lifecycle_sha256'], 'BUNDLE_SNAPSHOT_IDENTITY')
    data = {}
    for side in ['one', 'two']:
        data[f'lifecycle_{side}/RESULTS.json'] = source
        data[f'lifecycle_{side}/SHA256SUMS.txt'] = (_sha(source) + '  RESULTS.json\n').encode()
        for name, raw in audit.items():
            data[f'audit_{side}/{name}'] = raw
    return data


def _validate_data(data: dict[str, bytes]):
    _require(set(data) == set(DATA_NAMES), 'BUNDLE_DATA_MEMBERS')
    with tempfile.TemporaryDirectory(prefix='cyberpilot-r18-validate-') as scratch:
        root = Path(scratch)
        for name in DATA_NAMES:
            path = root / name  # Hardcoded allowlist only, never an archive-supplied extraction path.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data[name])
        return read_audit_pair(root / 'audit_one', root / 'audit_two', root / 'lifecycle_one', root / 'lifecycle_two')


def _payloads(data: dict[str, bytes]) -> dict[str, bytes]:
    record, audit, summary = _validate_data(data)
    metadata = {
        'schema_version': 1, 'contract_id': 'F70UGZ_R18_FIXED_AUDIT_BUNDLE_V1', 'scope': 'FIXED_SYNTHETIC_DATA_NOT_STANDALONE_AUTHORITY_OR_INSTALLER',
        'source_lifecycle_sha256': summary['input_lifecycle_sha256'], 'audit_sha256': _sha(audit['AUDIT.json']),
        'scenario_count': 7, 'rows': 112, 'columns': 37, 'data_sha256': {name: _sha(raw) for name, raw in sorted(data.items())},
        'gates': record['gates'], 'source_execution_counts': {'model_steps': record['model_steps'], 'extractor_calls': record['extractor_calls']},
        'report_execution_counts': {'model_steps': 0, 'extractor_calls': 0},
        'bundle_execution_counts': {'model_steps': 0, 'extractor_calls': 0, 'F61': 0, 'r_calculations': 0, 'dt_calculations': 0},
        'format_time_semantics': 'FIXED_ZIP_FORMAT_METADATA_NOT_SAMPLE_TIME',
        'verification_authority': 'TRUSTED_REPOSITORY_VALIDATORS_AND_FROZEN_EVIDENCE_NOT_BUNDLED_SIGNATURE',
    }
    files = data | {'BUNDLE.json': canonical(metadata), 'README_KO.md': README}
    files['SHA256SUMS.txt'] = _manifest(files)
    return files


def _archive_bytes(payloads: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, raw)
    return stream.getvalue()


def _verify_bytes(raw: bytes) -> dict:
    _require(len(raw) <= MAX_ARCHIVE, 'BUNDLE_ARCHIVE_SIZE_LIMIT')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            names = [info.filename for info in entries]
            _require(len(names) == 17 and len(set(names)) == 17
                     and set(names) == set(DATA_NAMES) | {'BUNDLE.json', 'README_KO.md', 'SHA256SUMS.txt'}, 'BUNDLE_MEMBERS')
            _require(sum(info.file_size for info in entries) <= MAX_UNPACKED
                     and all(0 <= info.file_size <= MAX_MEMBER for info in entries), 'BUNDLE_UNPACKED_SIZE_LIMIT')
            _require(all(info.compress_type == zipfile.ZIP_STORED and info.create_system == 3 and info.external_attr == 0o100644 << 16
                         and not info.is_dir() and info.flag_bits == 0 and info.extra == b'' and info.comment == b''
                         and info.date_time == (1980, 1, 1, 0, 0, 0) for info in entries) and archive.comment == b'', 'BUNDLE_ZIP_LAYOUT')
            files = {info.filename: archive.read(info) for info in entries}  # CRC checked; never extractall.
    except (zipfile.BadZipFile, RuntimeError, OSError) as error:
        raise ValueError('BUNDLE_ZIP_REJECTED') from error
    _require(raw == _archive_bytes(files), 'BUNDLE_NONCANONICAL_ZIP')
    expected = _payloads({name: files[name] for name in DATA_NAMES})
    _require(files == expected, 'BUNDLE_CONTRACT_OR_MANIFEST')
    metadata = json.loads(expected['BUNDLE.json'])
    return {
        'schema_version': 1, 'status': 'F70UGZ_R18_FIXED_AUDIT_BUNDLE_PASS', 'bundle_sha256': _sha(raw), 'bundle_bytes': len(raw),
        'archive_members': 17, 'manifest_entries': 16, 'source_lifecycle_sha256': metadata['source_lifecycle_sha256'],
        'audit_sha256': metadata['audit_sha256'], 'scenario_count': 7, 'rows': 112, 'columns': 37, 'model_steps': 0, 'extractor_calls': 0,
        'gates': metadata['gates'], 'scope': 'BOUNDED_FIXED_EVIDENCE_CONSISTENCY_NOT_ORIGIN_AUTHENTICATION_OR_DEPLOYMENT',
    }


def verify_bundle(path: Path) -> dict:
    with path.open('rb') as stream:
        raw = stream.read(MAX_ARCHIVE + 1)
    return _verify_bytes(raw)


def _execution_facts():
    forbidden = {'cyberlateral_dev', 'numpy', 'kernel', 'openpilot', 'selfdrive', 'opendbc', 'cereal', 'capnp', 'normalized_reference', 'output_oracle',
                 'synthetic_rate_constraint_feasibility_v1', 'synthetic_rate_constraint_feasibility_reconstructed_v2'}
    return {'isolated': bool(sys.flags.isolated), 'forbidden_modules_loaded': sorted(n for n in sys.modules if n.split('.')[0] in forbidden)}


def write_bundle(evidence: Path, output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS_NO_BUNDLE_WORK')
    raw = _archive_bytes(_payloads(_collect_snapshot(evidence)))
    result = _verify_bytes(raw)
    receipts = {ZIP_NAME + '.sha256': (_sha(raw) + '  ' + ZIP_NAME + '\n').encode(),
                'RESULTS.json': canonical(result), 'EXECUTION.json': canonical(_execution_facts())}
    output.mkdir(parents=True, exist_ok=False)
    staged = output / (ZIP_NAME + '.pending')
    with staged.open('xb') as stream:
        stream.write(raw)
    for name, value in receipts.items():
        with (output / name).open('xb') as stream:
            stream.write(value)
    staged.rename(output / ZIP_NAME)


def bundle_pair_summary(first: Path, second: Path) -> dict:
    try:
        one = {p.name: p.read_bytes() for p in first.iterdir()}
        two = {p.name: p.read_bytes() for p in second.iterdir()}
    except OSError as error:
        raise ValueError('BUNDLE_ARTIFACT_READ') from error
    _require(set(one) == {ZIP_NAME, ZIP_NAME + '.sha256', 'RESULTS.json', 'EXECUTION.json'} and one == two, 'BUNDLE_ARTIFACT_MISMATCH')
    result = _verify_bytes(one[ZIP_NAME])
    _require(one['RESULTS.json'] == canonical(result)
             and one['EXECUTION.json'] == canonical({'isolated': True, 'forbidden_modules_loaded': []})
             and one[ZIP_NAME + '.sha256'] == (result['bundle_sha256'] + '  ' + ZIP_NAME + '\n').encode(), 'BUNDLE_RECEIPT_OR_ENVIRONMENT')
    return result | {'byte_identical': True, 'file_hashes': {name: _sha(raw) for name, raw in sorted(one.items())}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    export = modes.add_parser('export', help='fixed R16/R17 evidence only, no model work')
    export.add_argument('--evidence', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    verify = modes.add_parser('verify', help='read-only bounded validation, trusted repository required')
    verify.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == 'export':
            write_bundle(args.evidence, args.output)
            print('F70UGZ_R18_FIXED_AUDIT_BUNDLE_PASS')
        else:
            result = verify_bundle(args.bundle)
            print(canonical({'result': result, 'execution_environment': _execution_facts()}).decode(), end='')
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
