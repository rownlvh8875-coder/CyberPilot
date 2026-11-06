"""Bounded Korean view of owned CORE21 receipts, not a new numerical verdict."""

from pathlib import Path

from .core_sequence_archive_preflight import preflight_suite_archive, preflight_suite_archive_bytes
from .core_sequence_archive_report import _preview

REPORT_CAP = 65536


class PreflightReportError(ValueError):
    """Fixed presentation failure; inherited preflight errors remain unchanged."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _markdown(receipt: dict) -> bytes:
    """Private preflight-owned result only, never an arbitrary JSON/dict reader."""
    r = receipt
    clipped = 0

    def row(values):
        nonlocal clipped
        cells = []
        for value in values:
            cell, truncated = _preview(value)
            cells.append(cell)
            clipped += truncated
        return '| ' + ' | '.join(cells) + ' |'

    lines = ['# CORE23 ZIP 입력 사전 검증 요약', '', '계약: CORE23_PORTABLE_INPUT_PREFLIGHT_SUMMARY_V1', '',
        'ZIP 전체 검산 후 현재 합성 입력의 의미만 재검증합니다. 저장 산술·출처·차량 성능의 인증이 아닙니다.', '',
        '## 현재 입력 판정과 작업량', '', '| 항목 | 값 |', '| --- | --- |',
        row(['current_status', r['preflight_status']])]
    for key in ('case_count', 'compatible_case_count', 'rejected_case_count', 'all_cases_processed',
                'validated_transition_count', 'declared_transition_count', 'recorded_model_steps',
                'new_synthetic_model_steps', 'new_reference_steps', 'numeric_validation_work'):
        lines.append(row([key, r[key]]))
    lines.extend(['', '검증 prefix는 각 case의 성공한 입력 검증 수의 합이며, 전이를 실행한 횟수가 아닙니다.',
        'recorded_model_steps는 과거 기록입니다. 신규 모델/reference0은 요약 작업에 해당하며 전체 unit/gate fixture 작업은 별도 비영입니다.',
        'numeric validation은 NONZERO_NOT_AGGREGATED이며 전체 프로세스의 수치 작업0을 주장하지 않습니다.', '',
        '## ZIP 정합성과 과거 저장 기록', '', '| 항목 | 값 |', '| --- | --- |'])
    archive = r['archive']
    for key in ('archive_sha256', 'archive_byte_size', 'member_count'):
        lines.append(row([key, archive[key]]))
    for status in ('MATCH', 'DIFFERENT', 'REJECTED'):
        lines.append(row(['saved_' + status, archive['suite']['saved_status_counts'][status]]))
    lines.extend(['', '## case별 현재 입력과 과거 판정', '',
        '| case | 현재 입력 판정 | 현재 거절 발췌 | 검증 prefix | 선언 전이 | 과거 저장 판정 | 과거 거절 발췌 | 과거 model steps |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |'])
    for case in r['case_reports']:
        lines.append(row([case[k] for k in ('case_id', 'preflight_status', 'rejection_code', 'validated_transition_count',
            'declared_transition_count', 'saved_status', 'saved_rejection_code', 'recorded_model_steps')]))
    lines.extend(['', '세 case를 모두 표시합니다. 과거 MATCH/DIFFERENT/REJECTED는 현재 입력 호환 여부를 결정하지 않습니다.',
        '셀은 원문 전체가 아닌 표시용 JSON 발췌입니다. 정확한 원문은 함께 반환한 변경 없는 CORE21 JSON을 사용하세요.',
        'null/false/0을 구분하며, escape 후160자 한도 밖은 PREVIEW_TRUNCATED로 표시합니다.', '',
        '## 권한 경계', '', '| 항목 | 값 |', '| --- | --- |'])
    for key in ('source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked',
                'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
        lines.append(row([key, r[key]]))
    lines.extend(['', '## 유지 Gate', '', '| Gate | 값 |', '| --- | --- |'])
    lines.extend(row([key, value]) for key, value in sorted(r['gates'].items()))
    lines.extend(['', '표시용 셀 발췌 잘림 수: ' + str(clipped), '',
        '실제 r/T2/scale=null; R_BUDGET=UNRESOLVED; Static Evidence Gate=FAIL; 실차 활성화 금지.',
        '출처·저장 산술·prehistory·computed rollout·현재 source/build/deployment·차량 성능을 인증하지 않습니다.',
        'atomic snapshot·atime 보존·적대적 Python hooks/경로 경쟁·다른 플랫폼·모든 Markdown renderer의 시각 품질은 보장하지 않습니다.', ''])
    raw = '\n'.join(lines).encode('utf-8')
    if len(raw) > REPORT_CAP:
        raise PreflightReportError('PREFLIGHT_REPORT_SIZE')
    return raw


def report_preflight_archive_bytes(raw: bytes, expected_sha256: str) -> tuple[dict, bytes]:
    """Preflight once and return unchanged CORE21 result plus bounded Markdown."""
    receipt = preflight_suite_archive_bytes(raw, expected_sha256)
    return receipt, _markdown(receipt)


def report_preflight_archive(input_archive: Path, expected_sha256: str) -> tuple[dict, bytes]:
    """Capture/preflight once, with no extraction, extra reads or model steps."""
    receipt = preflight_suite_archive(input_archive, expected_sha256)
    return receipt, _markdown(receipt)
