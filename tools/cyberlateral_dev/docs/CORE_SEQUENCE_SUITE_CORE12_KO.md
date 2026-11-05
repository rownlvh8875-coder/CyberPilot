# CORE12 — 고정 세 case 묶음 실행·검사·회귀 요약

기존 [CORE11](CORE_SEQUENCE_WORKFLOW_CORE11_KO.md)을 세 case에 고정 순서로
적용한다. 단일 case는 CORE11을 사용하고,이 명령은 subset/임의 manifest를 받지 않는다.
모델·F61·차량 정책을 새로 구현한 것이 아니다.

## 폴더 구조와 실행

root는 정확히 다음 세 폴더만 포함한다. 각 case 안에는 기존 CORE8 세 파일만 둔다.
root에 summary.json이나 다른 파일/폴더를 추가하면 검사를 거절한다.

```text
suite-root/
├── sign-cycle/           INPUT.json, RESULTS.json, SHA256SUMS.txt
├── declared-difference/  INPUT.json, RESULTS.json, SHA256SUMS.txt
└── late-invalid/         INPUT.json, RESULTS.json, SHA256SUMS.txt
```

기존 Python 환경과 개발판 디렉터리에서 실행한다. 예시 새 경로는 존재하지 않아야 한다.

```bash
# 명시적 실행: 세 고정 합성 case를 새 root에 저장,신규 public step 합계6
python -I -B tools/core_sequence_suite.py run --output-root /tmp/core12-baseline
python -I -B tools/core_sequence_suite.py run --output-root /tmp/core12-repeat --baseline-root /tmp/core12-baseline

# 읽기 전용: producer/model import·신규 실행·출력 폴더 생성 없음
python -I -B tools/core_sequence_suite.py check --input-root /tmp/core12-repeat
python -I -B tools/core_sequence_suite.py check --input-root /tmp/core12-repeat --baseline-root /tmp/core12-baseline
```

영수증은 JSON stdout이다. shell redirection으로 저장한다면 suite **밖**에 둔다.
run은 새 root/기존 nonsymlink parent/checkout 밖만 허용하며 baseline 자체나 그
하위 폴더에는 출력할 수 없다. root parent를 자동 생성하지 않는다.

## 무엇을 읽어야 하나

| 필드 | 뜻 |
| --- | --- |
| mode / execution_requested | 저장 검사만인지 명시적 새 합성 실행인지 |
| saved_status_counts | 실제 저장 MATCH/DIFFERENT/REJECTED 개수,성능/권한 판정 아님 |
| comparison_counts | NOT_REQUESTED/IDENTICAL/DIFFERENT case 개수 |
| new_synthetic_model_steps | 이번 묶음의 신규 steps;check0,현재 고정 run6(3/3/0) |
| recorded_model_steps | 현재 저장 패키지에 기록된 과거 steps의 합계 |
| difference_count / difference_counts | 기준과의 전체/INPUT·RESULT·IDENTITY 차이 합계 |
| reports | 생략하지 않은 case별 CORE11 전체 영수증 |

baseline이 없으면 comparison NOT_REQUESTED3,difference_count/difference_counts는
null이다. 이는 차이0이나 regression PASS가 아니다. exit0은 유효한 조회/전체 동일,
exit1은 하나 이상의 baseline 차이,exit2는 인자/패키지/작업 오류다. 저장 D/R를 새
실패/성공으로 승격하지 않는다. 현재 예제의 저장 M/D/R는 각각1개이며 정상 묶음이다.
개발 source metadata 변경도 차이에 포함하므로 이를 수치 regression/성능 변화로
자동 해석하지 않는다. [CORE10 비교 경계](CORE_SEQUENCE_COMPARE_CORE10_KO.md)를 유지한다.

## 전체 사전 검증과 실패 보존

선택적 baseline의 세 case를 **모두** 읽고 검증한 뒤에만 root 생성/계산을 시작한다.
마지막 baseline이 손상되면 신규 작업0/출력 미생성이다. 각 role의 casefiles는 한 번
캡처하며 그 owned records를 재사용한다. root 이름/디렉터리 종류만 끝에 재확인한다.
검증 후 외부 actor가 baseline을 바꿔도 이번 비교는 이미 확보한 bytes 기준이다.
실시간/atomic/hostile filesystem attestation이나 atime 불변 주장은 아니다.

root는 고정 세 디렉터리,각 패키지는 [CORE9](CORE_SEQUENCE_INSPECT_CORE9_KO.md)의
caps/canonical JSON/정확한 타입/닫힌 Gate/저장 관계 검사를 통과해야 한다. 저장 case_id와
폴더 이름도 일치해야 한다. symlink/FIFO/추가/누락/다른 case로 바꾼 폴더는 거절한다.

중간 case가 작업 후 실패하면 이전 완성 case와 부분 root를 보존하고 뒤 case를
실행하지 않는다. 마지막 case가 원래0step이라도 앞서6steps가 수행됐을 수 있으므로
run 실패는 WORK_MAY_BE_NONZERO를 유지한다. 부분 root를 덮어쓰거나 자동 재시도하지
않는다. 개별 조사에는 CORE11을 사용하고 새 실행은 새 root를 지정한다.
cache 정리/exit 계산까지 끝나야 성공 stdout을 내며,장치 출력 실패로 이미 전달된
bytes는 되돌릴 수 없다. exit2 출력은 완성된 성공 영수증으로 사용하지 않는다.

Python API는 integration_tools.core_sequence_suite의 check_closed_suite,
run_closed_suite,exit_code다. private helpers는 검증된 owned records용이며 외부 dict
validator/sandbox가 아니다. 기존 직접 CORE9 tuple Minor도 이 변경의 해결 범위가 아니다.
unit/gate/fixture의 합성 작업은 nonzero다. reader0을 전체 개발 과정0으로 표현하지 않는다.

유지:R_BUDGET=UNRESOLVED,Static Evidence Gate=FAIL,실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000,Candidate/Runtime=NO_GO,D2=PERFORMANCE_NOT_EVALUATED,
F19=LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY=NOT_PROVEN,F70UH/F70V/F71·실차 활성화 금지.
