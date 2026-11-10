# CORE35 — 운전자 제한·비활성화·복귀의 실제 합성 상태 인계

[CORE34](DRIVER_RATE_BOUNDARIES_CORE34_KO.md)의 단일 호출 seed 검사와 달리,
[새 테스트](../project/test_driver_state_chain.py)는 canonical initial_state부터
각9회 호출하는 양·음 방향 시퀀스다. 매번 실제 result.next_state 객체만 다음
입력으로 넘기며 예상 상태로 교체하지 않는다. 2개 unittest method/18model calls다.
Runtime/API/계산식/wheel/기존 참조는 바꾸지 않는다.

모든 입력은 scale16,allowance7,factor1,multiplier3,angle0.0,합성 요청±1이다.
기본 invocation UP2/DOWN5와 명시적0/0만 사용한다. index는 호출 순서이며 초·ms가 아니다.

| index | 설정/사건 | 양 방향 최종값 | 음 방향 최종값 |
|---|---|---|---|
| 0 | canonical0에서 시작 | 2 | -2 |
| 1 | 같은 방향 요청 | 4 | -4 |
| 2 | 같은 방향 요청 | 6 | -6 |
| 3 | opposing driver12.5·UP/DOWN0 | 6 | -6 |
| 4 | driver 유지·UP2/DOWN5 복원 | 1 | -1 |
| 5 | driver0·inactive | 0 | 0 |
| 6 | active·UP/DOWN0 | 0 | 0 |
| 7 | UP2/DOWN5 복원 | 2 | -2 |
| 8 | 요청 부호 전환 | -2 | 2 |

index3/4는 driver clip0과 rate/final±6/±1을 구분한다. index5는 limited±3과
final/next applied0을 구분하며 previous request±16을 적용 이력으로 쓰지 않는다.
index6은 비활성화 후 실제0을 유지한다. 변화량0을2/5로 대체하는 fallback은 없다.
UP/DOWN0은 호출당 limiter 설정이지 F61 r=0이나 실제 rate 정책이 아니다.

정확한 incoming request/applied,index/counter,driver/rate 각 단계의 integer tag/value,
limited/final/projected integer,next request/applied/index/counter와 bool flags를 검사한다.
기대값 두 테이블은 별도로 수동 작성하고 새 실행 전에 AST/SHA로 고정·커밋했다.
모델 출력으로 기대값을 만들지 않았다. 과거 코드 검토/baseline은 있으므로 blind
평가나 외부 인증은 아니다. 전체 serialization/float projection/fault threshold 검증은 아니다.

기존 준비된 환경에서 repository root 기준:

```bash
tools/cyberlateral_dev/.venv/bin/python -B -m unittest discover -s tools/cyberlateral_dev/project -p test_driver_state_chain.py
```

별도 in-memory own-model 변형6종으로 이력 오용·pre-gate 저장·inactive gate 오류·
stale history·zero-budget fallback을 탐지하고 정상 모델을 복원한다. 계측은 각 mode의
18public calls/18quantizer calls/16실제 상태 객체 연결을 확인한다. 두 초기화는 별개다.
요약·observed JSON만 재현 byte 비교하며 진단 log의 시간은 제외한다. 이 검증은
이 두 finite 합성 경로의 연속성이지 실제 차량/state/time/source custody 증명이 아니다.

실제 r/T2/scale=null,R_BUDGET UNRESOLVED,StaticGateFAIL,SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71·실차 활성화 NOT_ALLOWED.
실제 inputs/F61/Controller/Runtime/CAN/실제r/dt0,합성 작업 비영;새 CLI/차량 reader는 없다.
