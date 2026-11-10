# CORE37 — 합성 fault counter의 연결·재개 경계

새 runtime 기능이 아니라 기존 public `simulate`의 회귀 테스트다. 기존의
단독 fault/counter88 seed/catalog 검사는 보존하고, canonical0부터 시작하는
양·음100호출에서 driver·inactive·조건 해제·복귀를 연결한다.

## 수동 선언한 경로

합성 scale16,UP2/DOWN5,allowance7/factor1/multiplier3이다. 처음88호출은
요청±1,angle±85,active true이며 applied는±2/4/6/8/10/12/14 이후±16이다.
counter1..88은 고정된 수동 progression으로 선언한다. 다음12호출은:

| index | 조건/전이 | counter | request | 양수 경로 limited/final |
|---|---|---|---|---|
| 88 | exact85 | 89 | true | 16/16 |
| 89 | exact85,fault 억제 | 90 | false | 16/16 |
| 90 | exact85,wrap | 0 | false | 16/16 |
| 91 | exact85,복귀 | 1 | true | 16/16 |
| 92 | inactive | 0 | false | 16/0 |
| 93 | active,반대 부호 exact85 | 1 | true | 2/2 |
| 94 | 84.99609375 magnitude | 0 | true | 4/4 |
| 95 | exact85 복귀 | 1 | true | 6/6 |
| 96 | opposing driver12.5 | 2 | true | 1/1 |
| 97 | inactive | 0 | false | 3/0 |
| 98 | active,UP/DOWN0 | 1 | true | 0/0 |
| 99 | UP2/DOWN5,요청 부호 반전 | 2 | true | -2/-2 |

음수 경로는 별도로 선언한 반대 명령/angle/driver 부호와 limited/final 벡터를
사용한다. counter/flag 경로는 같다. limiter previous는 수동 final 벡터의 직전
항목으로 검사하며,기대 상태를 실제 feed에 사용하지 않는다. F61r=0이나 실제
차량 scale·시간·안전 동작의 권한이 아니다. 특히 fault request=false가 active
정수 명령을 자동으로0으로 만들지 않는다는 **이 합성 모델의** 계약을 검사한다.

## 분할과 기대값의 역할

각 경로에서16개 single cut,critical multi-cut1개,100singleton schedule1개를
검사한다. 총36schedules이지100호출의 모든 partition은 아니다. 또 두 history를
singleton으로 교차 실행한다. 각 반환 state를 다음 batch로 그대로 전달하고,
동등한 immutable 내부 복사본은 허용한다. 파일 checkpoint·프로세스 재시작·
동시 실행을 구현하거나 보장하지 않는다.

모든 counter/fault/request flag·limited/final/projected integer·양자화 정수·
limiter previous·반환 state를 수동 progression/tail과 비교한다. 전체 output과
최종 state의 uninterrupted parity도 별도로 검사하지만 이는 동일 구현 비교다.
full independent oracle가 아니다. 기대 벡터는 모델/quantizer/oracle로 생성하지
않고 새 실행 전에 AST/testSHA로 freeze한다. 이전 source 검토·과거 baseline은
있으므로 blind 평가/외부 승인을 주장하지 않는다.

## 변형과 작업량

incoming counter 초기화,stale counter 반환,fault가 active command까지0으로
만듦,exclusive85,inactive도 count,조건 해제 시 counter 유지의6종을 메모리의
함수 AST에만 적용한다. 모두 유효 domain에서 assertion RED/오류0이어야 하며
원래 callable/source 복원 전후는 GREEN이어야 한다. Runtime source는 수정하지 않는다.

새2method 한 실행은4200model/quantizer,494simulate,42초기화,452실제 반환
batch-state 인계다. 한 proof는 정상 전후+6변형의8modes/33600model 호출,
두 proof는67200model/quantizer다. 추가 unit/gate/reviewer 실행은 비영/미합산이며
이 수는 전체 작업 총계나 성능 지표가 아니다. 순서별 model 입력/상태/출력과
batch 입력/반환 상태/출력 개수의 rolling SHA256을 비교한다. 전체 반복 trace는
저장하지 않고 원문 실패 로그를 보존한다. elapsed-time logs는 byte 재현 대상이 아니다.

## 실행과 제한

현재 디렉터리를 `tools/cyberlateral_dev`로 두고:

```sh
PYTHONPATH=project:src .venv/bin/python -B -m unittest test_fault_lifecycle -v
.venv/bin/python -B dev.py verify --output /tmp/core37-dev-verify
```

첫 명령은 새2method만,두 번째는 상속된 합성·선택 source-reference 검사도 포함하는
전체 DEV gate다. 실제 결과는 별도 evidence에 보존한다. 이 두 fixed chain은
임의 입력/seed/scale/각도/길이·invalid/exhaustion 전체나 다른 환경/native/실차의
증명이 아니다. 선택 integer/state 외 독립 수치 정확성은 추가하지 않는다.

기존 runtime/API/계산식/test/reference/wheel/CORE32..36/cloud는 불변이다.
F61 import/compile/계산,실제 입력·r/dt,Controller/Runtime/CAN은 실행하지 않는다.
브라우저 검증은 API/test-only 범위에서 NOT_RUN. 실제 r/T2/scale=null,
R_BUDGET=UNRESOLVED,Static Gate=FAIL,Candidate/Runtime=NO_GO,
F70UH/V/F71·실차 활성화=NOT_ALLOWED를 유지한다. Unsigned 증거는 자체 일관성
기록이지 적대적 입력의 출처 인증이나 차량 안전 인증이 아니다.
