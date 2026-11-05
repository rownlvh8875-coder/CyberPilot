"""Bounded Korean Markdown of verified saved ZIPs, not a new numerical verdict."""

import json
from pathlib import Path

from .core_sequence_archive_compare import compare_suite_archive_bytes, compare_suite_archives

DETAILS_PER_CASE = 20
CELL_LIMIT = 160
REPORT_CAP = 65536


class ArchiveReportError(ValueError):
    """Fixed presentation rejection; inherited comparison errors are not hidden."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _preview(value) -> tuple[str, bool]:
    encoder = json.JSONEncoder(ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)
    escapes = {'`': r'\u0060', '|': r'\u007c', '<': r'\u003c', '>': r'\u003e', '&': r'\u0026'}
    pieces, size = [], 0
    for chunk in encoder.iterencode(value):
        for char in chunk:
            escaped = escapes.get(char, char)
            if size + len(escaped) > CELL_LIMIT:
                return '`' + ''.join(pieces) + '... [PREVIEW_TRUNCATED]`', True
            pieces.append(escaped)
            size += len(escaped)
    return '`' + ''.join(pieces) + '`', False


def _markdown(comparison: dict) -> bytes:
    """Private comparator-owned result only, never an external JSON/dict reader."""
    r = comparison
    shown = sum(min(DETAILS_PER_CASE, v['comparison']['reported_difference_count']) for v in r['reports'])
    preview_count = 0

    def row(values):
        nonlocal preview_count
        cells = []
        for value in values:
            cell, truncated = _preview(value)
            preview_count += truncated
            cells.append(cell)
        return '| ' + ' | '.join(cells) + ' |'

    lines = ['# CORE15 저장 ZIP 비교 요약', '', '계약: CORE15_ARCHIVE_SUMMARY_V1', '',
        '비교 판정: ' + r['comparison_status'], '',
        'ZIP bytes의 동일/차이만 비교합니다. 새 수치 판정·성능 평가·출처 인증·실차 승인이 아닙니다.', '',
        '전체 차이: ' + str(r['difference_count']) + ' / CORE14 상세: ' + str(r['reported_difference_count']) + ' / 요약 표시: ' + str(shown),
        'CORE14 상세에서 요약 미표시: ' + str(r['reported_difference_count'] - shown)
        + ' / CORE14 상세 한도 밖: ' + str(r['difference_count'] - r['reported_difference_count']),
        '구분별 전체 차이: INPUT=' + str(r['difference_counts']['INPUT']) + ', RESULT=' + str(r['difference_counts']['RESULT'])
        + ', IDENTITY=' + str(r['difference_counts']['IDENTITY']), '',
        'CORE14 진단 bytes: ' + str(r['reported_difference_bytes']) + ' / 한도 ' + str(r['detail_byte_limit']),
        '요약은 case별 첫20개입니다. 셀은 원문 전체가 아닌 표시용 발췌이며, 잘리면 PREVIEW_TRUNCATED를 표시합니다.',
        '정확한 전체 비교는 반환된 CORE14 JSON을 사용하세요. JSON pointer는 case와 함께 읽습니다.', '',
        '## 입력 기록과 작업량', '', '| 역할 | 전체 SHA256 | ZIP bytes | 저장 M/D/R | 기록된 과거 model steps |',
        '| --- | --- | --- | --- | --- |']
    for role in ('left', 'right'):
        receipt = r[role]
        counts = receipt['suite']['saved_status_counts']
        lines.append(row([role, receipt['archive_sha256'], receipt['archive_byte_size'],
            str(counts['MATCH']) + '/' + str(counts['DIFFERENT']) + '/' + str(counts['REJECTED']), receipt['suite']['recorded_model_steps']]))
    lines.extend(['', '저장 M/D/R는 MATCH/DIFFERENT/REJECTED이며 새 실행의 판정이 아닙니다.',
        '신규 모델 실행: 0 / 신규 reference 실행: 0 (비교·요약 작업만 해당)',
        'source_identity_reauthenticated=false / arithmetic_recomputed=false', '',
        '## case별 집계', '', '| case | 왼쪽 저장 판정 | 오른쪽 저장 판정 | 전체 차이 | INPUT | RESULT | IDENTITY | CORE14 상세 | 요약 표시 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |'])
    for item in r['reports']:
        c = item['comparison']
        lines.append(row([item['case_id'], c['left']['saved_status'], c['right']['saved_status'],
            c['difference_count'], c['difference_counts']['INPUT'], c['difference_counts']['RESULT'], c['difference_counts']['IDENTITY'],
            c['reported_difference_count'], min(DETAILS_PER_CASE, c['reported_difference_count'])]))
    lines.extend(['', '## 상세 요약', ''])
    for item in r['reports']:
        c = item['comparison']
        selected = c['differences'][:DETAILS_PER_CASE]
        lines.extend(['### ' + item['case_id'], '',
            '전체=' + str(c['difference_count']) + ' / CORE14 상세=' + str(c['reported_difference_count']) + ' / 요약=' + str(len(selected)), '',
            '| 경로 발췌 | 구분 | 변경 종류 | 왼쪽 존재 | 왼쪽 저장값 발췌 | 오른쪽 존재 | 오른쪽 저장값 발췌 |',
            '| --- | --- | --- | --- | --- | --- | --- |'])
        for d in selected:
            lines.append(row([d[k] for k in ('path','section','kind','left_present','left','right_present','right')]))
        if not selected:
            lines.append('저장 차이 상세 없음 (새 산술 검증을 뜻하지 않음).')
        lines.append('')
    lines.extend(['표시용 셀 발췌 잘림 수: ' + str(preview_count), '',
        '## 유지 Gate', '', 'R_BUDGET=UNRESOLVED; Static Evidence Gate=FAIL; 실제 r/T2/scale=null; 실차 활성화 금지.', '',
        '| Gate | 저장된 제한 |', '| --- | --- |'])
    lines.extend(row([key, value]) for key, value in sorted(r['gates'].items()))
    lines.extend(['', '한계: 저장 bytes/관계 비교일 뿐 출처·산술·현재 source/build/deployment를 인증하지 않습니다.',
        '일관된 위조는 탐지하지 못할 수 있습니다. atomic snapshot·적대적 경로/alias 경쟁·모든 Markdown renderer의 시각 동작은 보장하지 않습니다.', ''])
    raw = '\n'.join(lines).encode('utf-8')
    if len(raw) > REPORT_CAP:
        raise ArchiveReportError('ARCHIVE_REPORT_SIZE')
    return raw


def report_suite_archive_bytes(left: bytes, left_sha256: str, right: bytes, right_sha256: str) -> tuple[dict, bytes]:
    """Compare once and return unchanged CORE14 result plus bounded Markdown."""
    comparison = compare_suite_archive_bytes(left, left_sha256, right, right_sha256)
    return comparison, _markdown(comparison)


def report_suite_archives(left: Path, left_sha256: str, right: Path, right_sha256: str) -> tuple[dict, bytes]:
    """Capture/compare once per role; no extra reading, extraction or model work."""
    comparison = compare_suite_archives(left, left_sha256, right, right_sha256)
    return comparison, _markdown(comparison)
