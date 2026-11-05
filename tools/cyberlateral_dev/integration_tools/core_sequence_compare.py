"""Exact stored-record differences, never model replay or source authentication."""

import json
from pathlib import Path

from .core_sequence_saved import InspectError, read_saved_sequence_records
from .scenario_output import GATES, canonical

MISSING = object()
DETAIL_LIMIT = 256


class CompareError(ValueError):
    """Side-qualified fixed errors, no raw input diagnostics."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _pointer(key: str) -> str:
    return key.replace('~', '~0').replace('/', '~1')


def _difference(path, left, right, kind):
    section = ('INPUT' if path.startswith('/INPUT.json') else
               'IDENTITY' if path == '/RESULTS.json/identity' or path.startswith('/RESULTS.json/identity/') else 'RESULT')
    return {'path': path, 'section': section, 'kind': kind,
        'left_present': left is not MISSING, 'right_present': right is not MISSING,
        'left': None if left is MISSING else left, 'right': None if right is MISSING else right}


def _walk(path, left, right):
    if left is MISSING or right is MISSING:
        yield _difference(path, left, right, 'RIGHT_ONLY' if left is MISSING else 'LEFT_ONLY')
    elif type(left) is not type(right):
        yield _difference(path, left, right, 'TYPE_CHANGED')
    elif type(left) is dict:
        for key in sorted(left.keys() | right.keys()):
            yield from _walk(path + '/' + _pointer(key), left.get(key, MISSING), right.get(key, MISSING))
    elif type(left) is list:
        for i in range(max(len(left), len(right))):
            yield from _walk(path + '/' + str(i), left[i] if i < len(left) else MISSING, right[i] if i < len(right) else MISSING)
    elif left != right:
        yield _difference(path, left, right, 'VALUE_CHANGED')


def _read(path: Path, side: str) -> dict:
    try:
        return read_saved_sequence_records(path)
    except InspectError as error:
        raise CompareError('COMPARE_' + side + ':' + error.code) from error


def _metadata(summary):
    return {key: summary[key] for key in ('case_id', 'saved_status', 'saved_rejection_code',
        'recorded_model_steps', 'recorded_transition_count', 'captured_sha256')}


def _compare_captured(lhs: dict, rhs: dict) -> dict:
    """Internal comparison of CORE9 loader-owned records, not external dict intake."""
    counts = {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 0}
    details = []
    for filename, key in [('INPUT.json', 'input_record'), ('RESULTS.json', 'result_record')]:
        for difference in _walk('/' + filename, lhs[key], rhs[key]):
            counts[difference['section']] += 1
            if len(details) < DETAIL_LIMIT:
                details.append(difference)
    total = sum(counts.values())
    return {'schema_version': 1, 'contract_id': 'CORE10_SAVED_SEQUENCE_COMPARISON_V1',
        'comparison_status': 'SAVED_PACKAGES_DIFFERENT' if total else 'SAVED_PACKAGES_IDENTICAL',
        'same_case_id': lhs['summary']['case_id'] == rhs['summary']['case_id'],
        'left': _metadata(lhs['summary']), 'right': _metadata(rhs['summary']),
        'difference_count': total, 'difference_counts': counts, 'reported_difference_count': len(details),
        'differences_truncated': total > len(details), 'differences': details, 'gates': dict(GATES),
        'comparison_model_executions': 0, 'comparison_reference_executions': 0,
        'source_identity_reauthenticated': False, 'arithmetic_recomputed': False,
        'integrity_scope': 'CAPTURED_RECORD_COMPARISON_NOT_ARITHMETIC_OR_ORIGIN_PROOF'}


def compare_saved_sequences(left: Path, right: Path) -> dict:
    """Compare all validated stored fields, including opaque historical identity."""
    return _compare_captured(_read(left, 'LEFT'), _read(right, 'RIGHT'))


def _cell(value) -> str:
    # Code spans keep Markdown/backslashes literal. Unicode JSON escapes remove
    # span/table/HTML delimiters without changing the decoded stored value.
    text = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)
    for char, escaped in [('`', r'\u0060'), ('|', r'\u007c'), ('<', r'\u003c'), ('>', r'\u003e'), ('&', r'\u0026')]:
        text = text.replace(char, escaped)
    return '`' + text + '`'


def render_comparison(comparison: dict, output_format: str = 'json') -> bytes:
    """Format a comparator-owned result; not an untrusted summary intake API."""
    if type(output_format) is not str or output_format not in ('json', 'markdown'):
        raise CompareError('COMPARE_FORMAT')
    if output_format == 'json':
        return canonical(comparison)
    r = comparison
    lines = ['# CORE10 저장 패키지 비교', '', '비교 판정: ' + _cell(r['comparison_status']), '',
        '왼쪽 저장 case/status: ' + _cell(r['left']['case_id']) + ' / ' + _cell(r['left']['saved_status']),
        '오른쪽 저장 case/status: ' + _cell(r['right']['case_id']) + ' / ' + _cell(r['right']['saved_status']),
        '전체 차이: ' + _cell(r['difference_count']) + ' / 표시 차이: ' + _cell(r['reported_difference_count']),
        '차이 상세 잘림: ' + _cell(r['differences_truncated']),
        '구분별 차이: ' + _cell(r['difference_counts']), '신규 모델 실행: 0 / 신규 reference 실행: 0', '',
        '| 경로 | 구분 | 변경 종류 | 왼쪽 존재 | 왼쪽 저장값 | 오른쪽 존재 | 오른쪽 저장값 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for d in r['differences']:
        lines.append('| ' + ' | '.join(_cell(d[key]) for key in
            ('path', 'section', 'kind', 'left_present', 'left', 'right_present', 'right')) + ' |')
    lines.extend(['', '첫 256개만 표시하며 전체 차이 수는 모두 셉니다. 배열은 위치 기준입니다.',
        '저장 판정 비교일 뿐 새 수치 판정·성능 평가·원본/현재 소스 인증이 아닙니다.',
        '일관된 조작·저장 산술의 진위는 인증하지 않습니다. 실제 입력/실차 활성화 금지.',
        'R_BUDGET=UNRESOLVED; Static Evidence Gate=FAIL; 실제 r/T2/scale=null.', ''])
    return '\n'.join(lines).encode()
