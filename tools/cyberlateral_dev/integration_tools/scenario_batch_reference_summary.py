"""Path-free Korean summary of a classified saved-batch reference check."""


def summary(record: dict) -> bytes:
    first = record['first_difference']
    location = '없음' if first is None else first['case_id'] + ' / ' + first['field']
    lines = ['# 저장된 합성 batch 독립 참조 검사', '', f'상태: {record["status"]}', '',
             f'완료 sample 참조 계산: {record["reference_steps"]}. 새 public 모델 실행:0.', '',
             f'일치 {record["matched_cases"]}, 수치 불일치 {record["different_cases"]}, 실행 오류 {record["error_cases"]}.', '',
             (f'입력 거절 확인 {record["input_rejections_confirmed"]}, 미확인 {record["input_rejections_unverified"]}, '
              f'거절 사유 불일치 {record["rejection_mismatch_cases"]}.'), '',
             f'수치 field 차이: {record["numerical_difference_count"]}. 첫 차이: {location}', '',
             '| case | 판정 | 참조 sample | 수치 차이 | 거절/오류 코드 |',
             '|---|---|---:|---:|---|']
    for row in record['cases']:
        code = row['error_code'] or row['observed_rejection_code'] or row['rejection_code'] or '-'
        count = '미확정' if row['reference_steps'] is None else str(row['reference_steps'])
        differences = '-' if row['difference_count'] is None else str(row['difference_count'])
        lines.append(f'| {row["case_id"]} | {row["status"]} | {count} | {differences} | {code} |')
    lines += ['', '참조/helper 합계는 성공한 참조 보고서만 집계합니다. 오류 호출의 작업은 NONZERO일 수 있으며 합계 미확정입니다.',
              '거절만 있는 batch 또는 원본 bytes가 없는 거절을 전체 수치 MATCH로 승인하지 않습니다.',
              '입력 거절 확인은 보존된 JSON의 현재 parser 판정이며 과거 파일 I/O 실패 사실을 인증하지 않습니다.',
              'case별 REFERENCE_CHECK.json의 상세 차이는 기존256개 cap을 따르며 전체 수치 차이 수는 별도 보존합니다.',
              '같은 완전한 입력 bytes의 반복만 전체 hash를 비교합니다. 개인 receipt가 바뀌면 전체 hash도 바뀔 수 있습니다.', '',
              '한정 합성·선택 source parity이며 전체 Controller/실차 안전/실제 과거 이력·출처 인증이 아닙니다.',
              '호출 index는 초·실제10ms 주기가 아닙니다. 허용오차·기준 자동 갱신·fallback은 없습니다.',
              'R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제r/T2/차량scale=null.',
              '실차 입력·활성화·F61·r/dt·F70UH/V/F71은 허용하지 않습니다.', '']
    return '\n'.join(lines).encode()
