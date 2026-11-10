# CORE36 — 유한 합성 시퀀스의 분할·재개 회귀

기존 `simulate` API를 바꾸지 않고, CORE35의 양/음 방향 9호출 시퀀스를
같은 프로세스에서 여러 batch로 나누어 재개하는 경계를 검사한다.
파일 checkpoint, 별도 프로세스 복구나 새 입력 reader를 구현한 것이 아니다.

## 검사 방법

- 시퀀스 내부 8곳의 모든 cut 조합: 방향별 256개, 총 512개 partition.
- 매 chunk는 비어 있지 않은 tuple이며, 실제 반환 `next_state`를 다음
  chunk에 전달한다. 기대값으로 상태를 교체하지 않는다.
- 모든 출력·최종 상태는 중단 없는 실행과 정확히 비교한다. 각 중간 반환
  상태와 driver/rate/gate/정수 projection·자료형은 변경하지 않은 CORE35
  literal 표와도 비교한다. 동일 구현의 parity만을 독립 oracle이라 하지 않는다.
- 두 방향을 singleton batch로 교차 실행하여 각 history가 유지되는지 확인한다.
- immutable state의 동등한 복사본은 허용한다. 구현 내부의 객체 aliasing을
  새로운 API 보장으로 강제하지 않는다.

CORE35 literal은 이미 이전 단계에서 실행된 알려진 기대값이다. 이번 freeze는
새 partition 테스트/일정의 사전등록이며, 수치 holdout·외부 승인 증거가 아니다.
`test_partition_resume.py`는 기존 TestCase를 가져오지 않으므로 unittest 수를
중복 집계하지 않는다. cut set은 별도의 combinations 열거와 대조한다.

## 변형 민감도

외부 증거 스크립트는 `simulate` 함수 AST만 메모리에서 바꾼다. 원본 class와
source bytes는 유지한다. incoming applied 초기화, previous request로 대체,
inactive gate 이전값 저장, stale 반환 상태, 첫 출력 누락, 출력 역순의 6개
변형은 각각 assertion 실패로 잡혀야 한다. 타입/인덱스 오류로 우연히 RED가
되는 것을 허용하지 않는다. 정상 구현은 전후 모두 GREEN이어야 한다.

두 증거 실행은 정렬된 관측 이벤트의 rolling SHA256과 카운터·실패 목록을
비교한다. 반복된 전체 trace 대신 digest를 보존하며, 원문 실패 로그도 남긴다.
소요 시간이 들어간 로그 bytes는 재현성 비교 대상이 아니다.

새 테스트 2method의 한 실행은 2,582 batch 호출, 4,662 model/quantizer 호출,
518 초기화, 2,064 실제 반환 batch-state 인계를 수행한다. 한 proof는 정상
2회와 변형 6회로 37,296 model 호출이며, 두 proof 합계는 74,592이다.
이 수는 해당 proof에 한정된다. 전체 DEV·별도 focused·reviewer 실행의 추가
합성 작업은 0이 아니며, 여기서 총합이나 성능 지표로 집계하지 않는다.

## 실행

현재 디렉터리를 `tools/cyberlateral_dev`로 두고:

```sh
PYTHONPATH=project:src .venv/bin/python -B -m unittest test_partition_resume -v
.venv/bin/python -B dev.py verify --output /tmp/core36-dev-verify
```

첫 명령은 새 2method만 실행한다. 두 번째는 기존 전체 DEV gate로,
상속된 합성 모델·선택 source-reference 검증 작업도 포함한다. 이 guide는
명령의 실행 결과를 대신하지 않으며, 실제 결과는 봉인된 evidence에 보존한다.

## 한계와 계속 닫혀 있는 Gate

두 고정 시퀀스의 **유한 partition 전체**이지 모든 scale/driver/angle/길이,
fault threshold, 잘못된 입력이나 모든 결함의 증명이 아니다. 새 arbitrary
stream·네이티브 replay·실제 previous-state 출처·실제 시간의 권한도 없다.
기존 invalid-input/fault 테스트는 그대로이며 새 범위에 포함시켜 재명명하지 않는다.
출력 전체 parity는 동일 구현 회귀이며, 독립 literal 검사는 선택 필드에 한정된다.

runtime/API/계산식·기존 테스트/벡터·wheel·cloud consumer는 변경하지 않는다.
F61 원본 import/compile/계산, 실제 입력·r/dt, Controller/Runtime/CAN은 실행하지
않는다. 브라우저 화면 검증은 이번 API/test-only 범위에서 NOT_RUN이다.
actual r/T2/vehicle_scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
Candidate/Runtime=NO_GO, F70UH/V/F71·실차 활성화=NOT_ALLOWED를 유지한다.
증거 ZIP은 unsigned 자체 일관성 기록이며 적대적 입력·외부 인증은 아니다.
