"""Relative-link Korean summary; no private source paths or runtime promises."""


def summary(record: dict) -> bytes:
    regression = record['regression_status'] or 'NOT_REQUESTED'
    text = ('# 선언 합성 시나리오 통합 실행·검증\n\n'
            f'상태: {record["status"]}\n\n'
            f'입력 {record["input_count"]}개 / 완료 {record["completed"]}개 / 거절 {record["rejected"]}개.\n'
            f'새 합성 모델 {record["model_steps"]}steps / 독립 참조 {record["reference_steps"]}steps.\n\n'
            f'R39 참조: {record["reference_status"]} / R34 저장값 비교: {regression}.\n\n'
            '[입력 사전 검사](VALIDATION.json) · [batch 그래프·표](batch/index.html) · '
            '[독립 참조](reference/SUMMARY_KO.md)\n\n')
    if record['regression_status'] is not None:
        text += '[선택 회귀 비교](regression/SUMMARY_KO.md)\n\n'
    text += ('같은 입력의 bounded 합성 source parity이며 범용 독립 oracle·과거 이력·차량 승인이 아닙니다.\n'
             'case 사이 상태는 독립적이고 호출 index는 실제 시간·10ms·100Hz가 아닙니다.\n'
             '입력 전부 거절은 수치 성공이 아니며 mixed 입력은 exit1입니다.\n'
             '참조 count는 성공 child만 포함하며 실패한 작업도 NONZERO일 수 있습니다.\n'
             '전체 결과에는 private receipt와 원형 합성 입력이 있으므로 자동 공유하지 않습니다.\n'
             '같은 source/runtime의 portable summary는 반복 가능하지만 개인 receipt가 다른 full hash는 다를 수 있습니다.\n'
             '허용오차·fallback·자동 baseline 갱신은 없습니다.\n\n'
             '실제 r/T2/scale=null, R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL.\n'
             'F61·실제 r/dt·Controller·차량 Runtime·CAN·실차 입력/활성화·후보 평가는0.\n'
             'F70UH/V/F71 NOT_ALLOWED.\n')
    return text.encode()
