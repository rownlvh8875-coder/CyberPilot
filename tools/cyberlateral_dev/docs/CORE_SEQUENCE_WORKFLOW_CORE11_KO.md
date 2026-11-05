# CORE11 — 고정 합성 예제의 실행·저장·조회·비교

`check`는 [CORE9](CORE_SEQUENCE_INSPECT_CORE9_KO.md) 검사와 선택적
[CORE10](CORE_SEQUENCE_COMPARE_CORE10_KO.md) 비교만 수행한다. `run`만
[CORE8](CORE_SEQUENCE_CLI_CORE8_KO.md)의 고정 합성 예제를 새로 실행한다.
두 모드는 자동 전환되지 않으며 실제 차량/F61/r 정책 입력 기능이 아니다.

## 사용

개발판 디렉터리와 기존 Python 환경에서 예시 경로를 실제 폴더로 바꿔 실행한다.

```bash
# 읽기 전용: 신규 모델 import/실행·새 패키지 생성 없음
python -I -B tools/core_sequence_workflow.py check --input /tmp/saved-core8/sign-cycle
python -I -B tools/core_sequence_workflow.py check --input /tmp/saved-core8/sign-cycle --baseline /tmp/baseline/sign-cycle

# 명시적 합성 실행: 새 출력 폴더만 가능
python -I -B tools/core_sequence_workflow.py run --case sign-cycle --output /tmp/new-core11/sign-cycle
python -I -B tools/core_sequence_workflow.py run --case sign-cycle --output /tmp/new-core11/repeat --baseline /tmp/new-core11/sign-cycle
```

출력의 parent `/tmp/new-core11`은 먼저 준비되어 있어야 한다. 기존 출력·symlink
parent·없는 parent·checkout 내부 출력을 거절한다. 출력은 기존 CORE8 세 파일뿐이다.
baseline 자체 또는 그 하위 폴더도 출력으로 사용할 수 없다. 기준 패키지의 파일 집합을
변경하지 않도록 실행 전에 거절한다. 새 출력은 별도의 sibling 폴더 등에 둔다.
workflow 영수증은 JSON stdout이다. shell로 저장한다면 **패키지 밖**에 저장한다.
출력 폴더 안에 영수증을 더하면 CORE9의 정확한 세 파일 검사를 통과하지 못한다.
`--case`는 sign-cycle,declared-difference,late-invalid만 허용한다. `check`에
`--output`/`--case`를 주거나,모드를 생략해 실행할 수 없다. r/기간/차량 옵션도 없다.

## 세 종류의 상태를 구별하기

| 필드 | 의미 |
| --- | --- |
| mode / execution_requested | 검사만인지 새 합성 실행을 요청했는지 |
| saved_status | 저장된 MATCH/DIFFERENT/REJECTED,새 권한/성능 판정 아님 |
| recorded_model_steps | 현재 패키지가 기록한 과거 steps |
| new_synthetic_model_steps | 이번 workflow의 신규 합성 steps;check는0,run은3/3/0 |
| workflow_status / comparison | 조회 성공 또는 baseline과의 전체 저장 기록 비교 |

exit0은 유효한 workflow(no baseline 또는 동일),exit1은 baseline 차이,
exit2는 인자/패키지/작업 오류다. **run에서도 저장 DIFFERENT/REJECTED가 exit0일 수
있다.** 기존 CORE8의 수치 판정별 exit0/1/2와 다르다. saved_status를 반드시 읽는다.
baseline 미지정은 regression comparison 미수행이다. 기본 기준/정답/정책은 없다.

baseline이 있으면 왼쪽 baseline/오른쪽 current로 비교한다. 입력·결과·identity
metadata 모두 비교하므로 개발 소스 목록/해시 변경만으로도 DIFFERENT일 수 있다.
이를 수치 개선/성능 저하/계산 오류로 자동 해석하거나 identity 차이를 숨기지 않는다.
배열은 위치 기준,첫256상세와 전체개수 규칙도 CORE10과 같다.

## 캡처·실패·권한 경계

각 role을 한 번 캡처하며 검증된 파일을 다시 열지 않는다. run baseline은 모델 호출/
출력 생성 전에 검증한 owned bytes를 끝까지 사용한다. 이후 디스크 baseline이 달라져도
이번 보고서는 그 캡처를 비교한 것이며 최신 live/atomic snapshot 주장이 아니다.
run의 producer 반환값과 저장 RESULTS 및 요청 case가 일치하는지도 확인한다.

잘못된 input/baseline은 WORKFLOW_INPUT/WORKFLOW_BASELINE 고정 오류다.
실행 중/후의 실패는 WORK_MAY_BE_NONZERO를 유지하며 이미 생성된 폴더를 지우거나
덮어써 재시도하지 않는다. 부분 출력은 성공 패키지가 아니며 새 경로로 조사/재실행한다.
stdout 실패도 이미 전달된 bytes를 되돌릴 수 없다. exit2 출력은 성공 영수증이 아니다.
임시 cache 정리까지 완료한 뒤 성공 영수증을 출력한다. cache 정리가 실패해도 생성된
합성 패키지는 보존하며,check/run에 맞는 고정 오류·exit2를 반환한다.

check는 producer/model 실행 path를 import하지 않는다. reader 모델/reference 실행0은
명시적 run의 합성 모델 steps나 전체 unit/gate/fixture 작업량0을 뜻하지 않는다.
전체 개발 검증의 합성 작업은 nonzero다. 관측 source metadata는 source 인증이 아니며
일관되게 조작한 기록의 산술/출처를 보증하지 않는다. CORE9 direct tuple Minor,
cooperative filesystem/atime/non-atomic 한계도 유지한다.

Python API는 integration_tools.core_sequence_workflow의 check_saved_sequence,
run_closed_sequence,exit_code다. CORE10의 private captured 비교 helper는 loader-owned
records 전용이며 arbitrary dict intake/qualification 기능이 아니다.

유지:R_BUDGET=UNRESOLVED,Static Evidence Gate=FAIL,실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000,Candidate/Runtime=NO_GO,D2=PERFORMANCE_NOT_EVALUATED,
F19=LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY=NOT_PROVEN,F70UH/F70V/F71·실차 활성화 금지.
