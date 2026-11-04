"""Pure Korean reading aid for an R66 comparison, not byte or visual verification."""

import re

from browser_probe import PROFILES, WIDTHS
from browser_verify import FILES, MAX_FILE_BYTES


def _need(condition):
    if not condition:
        raise ValueError('BROWSER_COMPARISON_SUMMARY_INVALID')


def _integer(value, minimum=0, maximum=None):
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def _hash(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _receipt(receipt):
    _need(type(receipt) is dict)
    _need(receipt.get('status') == 'R64_SAVED_BROWSER_BUNDLE_VALID')
    _need(receipt.get('recorded_status') in ('R60_BROWSER_SMOKE_PASS', 'R60_BROWSER_SMOKE_FAIL'))
    _need(_integer(receipt.get('cases')) and receipt['cases'] == len(PROFILES) * len(WIDTHS))
    _need(_integer(receipt.get('recorded_case_failures'), maximum=receipt['cases']))
    _need(_integer(receipt.get('recorded_failure_records')))
    _need((receipt['recorded_status'] == 'R60_BROWSER_SMOKE_FAIL') == bool(receipt['recorded_failure_records']))
    _need(not receipt['recorded_case_failures'] or receipt['recorded_failure_records'] > 0)
    _need(_integer(receipt.get('verified_files')) and receipt['verified_files'] == len(FILES))
    _need(_hash(receipt.get('result_sha256')))
    _need(_integer(receipt.get('reader_browser_model_F61_vehicle_executions'), maximum=0))
    _need(receipt.get('source_identity_reauthenticated') is False)
    _need(receipt.get('scope') == 'SAVED_BYTES_AND_RECORD_CONSISTENCY_NOT_NEW_BROWSER_OR_ORIGIN_ATTESTATION')


def render_comparison_summary(result: dict) -> bytes:
    """Render only validated-shape R66 facts; this API cannot authenticate their source."""
    _need(type(result) is dict)
    _need(type(result.get('schema_version')) is int and result['schema_version'] == 1)
    _need(result.get('comparison') == 'EXACT_SAVED_BYTES')
    _need(_integer(result.get('compared_files')) and result['compared_files'] == len(FILES))
    _need(_integer(result.get('changed_files'), maximum=len(FILES)))
    _need(_integer(result.get('unchanged_files'), maximum=len(FILES)))
    _need(result['changed_files'] + result['unchanged_files'] == result['compared_files'])
    expected = 'R66_SAVED_BROWSER_BYTES_DIFFERENT' if result['changed_files'] else 'R66_SAVED_BROWSER_EXACT_BYTES_MATCH'
    _need(result.get('status') == expected)
    _need(result.get('quality_assessment') == 'NOT_PERFORMED')
    _need(result.get('source_identity_reauthenticated') is False)
    _need(_integer(result.get('comparator_browser_model_F61_vehicle_executions'), maximum=0))
    _need(result.get('scope') == 'SAVED_BYTES_COMPARISON_NOT_VISUAL_OR_ORIGIN_ATTESTATION')
    differences = result.get('differences')
    if type(differences) is not list:
        raise ValueError('BROWSER_COMPARISON_SUMMARY_INVALID')
    _need(len(differences) == result['changed_files'])
    paths = []
    for row in differences:
        _need(type(row) is dict and type(row.get('path')) is str and row['path'] in FILES)
        paths.append(row['path'])
        for side in ('baseline', 'candidate'):
            item = row.get(side)
            _need(type(item) is dict and _hash(item.get('sha256'))
                  and _integer(item.get('byte_size'), maximum=MAX_FILE_BYTES))
    _need(paths == sorted(set(paths)))
    for side in ('baseline', 'candidate'):
        _receipt(result.get(side + '_verification'))
    result_delta = next((row for row in differences if row['path'] == 'RESULT.json'), None)
    if result_delta is None:
        fields = ('recorded_status', 'cases', 'recorded_case_failures', 'recorded_failure_records', 'result_sha256')
        _need(all(result['baseline_verification'][field] == result['candidate_verification'][field] for field in fields))
    else:
        _need(all(result_delta[side]['sha256'] == result[side + '_verification']['result_sha256']
                  for side in ('baseline', 'candidate')))

    parts = ['# 저장 묶음 비교 요약', '',
             '비교 상태: `' + result['status'] + '`',
             f'비교 파일: {result["compared_files"]} · 변경: {result["changed_files"]} · 불변: {result["unchanged_files"]}', '',
             'MATCH는 화면 PASS가 아닙니다. 동일한 FAIL 묶음도 MATCH입니다.',
             'DIFFERENT는 새 화면 회귀 판정이 아닙니다. 로그·Manifest·JSON 표현도 정확한 바이트 비교 대상입니다.',
             'exit 0: MATCH · exit 1: DIFFERENT · exit 2: 입력/형식 오류(비교 결과 아님, 요약 미생성).', '',
             '## 양쪽의 원래 화면 검사 기록', '',
             '새로 평가한 상태가 아닙니다. 전체 FAIL은 개별 실패 case가 0개여도 존재할 수 있습니다.',
             'baseline은 기준 묶음, candidate는 비교 묶음이며 차량 candidate 승인이 아닙니다.', '',
             '| 구분 | 원래 기록 상태 | case 수 | 실패 case 수 | 전체 실패 기록 수 | RESULT SHA256 |',
             '|---|---|---|---|---|---|']
    for side in ('baseline', 'candidate'):
        receipt = result[side + '_verification']
        parts.append(f'| {side} | `{receipt["recorded_status"]}` | {receipt["cases"]} | '
                     f'{receipt["recorded_case_failures"]} | {receipt["recorded_failure_records"]} | '
                     f'`{receipt["result_sha256"]}` |')
    parts.extend(['', '## 변경 파일', ''])
    if differences:
        parts.extend(['단위는 bytes입니다. 경로는 입력 묶음 내부의 고정 상대 경로이며 링크가 아닙니다.', '',
                      '| 파일 | baseline SHA256 | baseline 크기(bytes) | candidate SHA256 | candidate 크기(bytes) |',
                      '|---|---|---|---|---|'])
        for row in differences:
            before, after = row['baseline'], row['candidate']
            parts.append(f'| `{row["path"]}` | `{before["sha256"]}` | {before["byte_size"]} | '
                         f'`{after["sha256"]}` | {after["byte_size"]} |')
    else:
        parts.append('변경 파일 없음. 모든 소유 파일의 저장 바이트가 같습니다. 원래 화면 상태는 위 표와 별개입니다.')
    parts.extend(['', '## 범위와 제한', '',
                  'quality_assessment=NOT_PERFORMED · source_identity_reauthenticated=false.',
                  '이 요약은 R66 비교 기록의 읽기 보조물입니다. 단독 문서로 원본 bytes나 출처를 인증하지 않습니다.',
                  '새 브라우저/모델/F61/실제 r·dt/Controller/Runtime/CAN/차량 실행: 0.',
                  '전체 unit/gate의 별도 합성 작업은 NONZERO/미집계입니다.',
                  '화면·픽셀 유사도, 발행자 인증, 실제 실행·물리 시간·차량 적격성 검증이 아닙니다.',
                  '입력 snapshot은 순차적이며 atomic/concurrent-writer 보호가 없습니다. 비교 중 편집하지 마세요.',
                  'R_BUDGET=UNRESOLVED · Static Gate=FAIL · 실제 r/T2/scale=null · Candidate/Runtime NO_GO.',
                  'F70UH/F70V/F71 및 실차 활성화 NOT_ALLOWED.', ''])
    return '\n'.join(parts).encode('utf-8')
