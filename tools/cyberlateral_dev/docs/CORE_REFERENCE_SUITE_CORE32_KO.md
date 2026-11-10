# CORE32 — 여섯 합성 참조 검증의 단일 회귀 명령

[CORE30](CORE_ROLLOUT_REFERENCE_CORE30_KO.md)과 [CORE31](CORE_BOUNDARY_ROLLOUT_CORE31_KO.md)을
수정하지 않고 한 번씩 실행해 결과를 묶는다. 새 계산식/참조값/차량 입력/정책은 없다.
전체 DEV 테스트를 대체하지 않는 빠른 고정 예제 회귀 명령이다.

## 실행

기존 개발 환경을 준비한 뒤 repository root에서:

```bash
tools/cyberlateral_dev/.venv/bin/python -I -B tools/cyberlateral_dev/tools/core_reference_suite.py --run
```

`--run`은 정확히 한 번 필요하다. --help는 계산 없이 도움말을 출력한다.
case 선택/입력/출력/rate/format 옵션·축약·중복·위치 인자는 없다. stdout은 canonical JSON이다.
Python API는 `integration_tools.core_reference_suite.run_reference_suite()`이며 호출 자체가
명시적 합성 실행이다. 저장 폴더·temp·네트워크 작업은 없고 기존 owned reference를 읽는다.

| 순서 | case | 정상 observed rollout | 정상 reported model steps |
|---|---|---|---|
| CORE30 | sign-cycle | MATCH | 3 |
| CORE30 | declared-difference | DIFFERENT | 3 |
| CORE30 | late-invalid | REJECTED | 0 |
| CORE31 | inactive-resume | MATCH | 3 |
| CORE31 | fault-reset | MATCH | 4 |
| CORE31 | rounding-ties | MATCH | 6 |

정상 audit는6MATCH지만 observed rollout은4MATCH/1DIFFERENT/1REJECTED다. 의도한 차이와
사전 거절이 참조와 맞으면 회귀 suite는 성공이다. 두 종류의 판정을 합치지 않는다.
정상 reported model19steps,reference assembly model0이다. late-invalid도 numeric preflight는
비영이며 모든 unit/gate/단계 전체 작업을19또는0으로 주장하는 것이 아니다.

## 판정과 출력

- exit0/CLOSED_REFERENCE_SUITE_MATCH: 여섯 audit 모두 참조와 일치.
- exit1/CLOSED_REFERENCE_SUITE_DIFFERENT: 정상 처리된 audit 중 차이가 있음. 나머지 case도
  모두 처리하며 완전한 JSON을 출력한다. 성능·차량 적합성 판정이 아니다.
- exit2: 구문/receipt/운영/출력 오류. 부분 성공 JSON을 제공하지 않는다. 단, stdout 중간
  실패로 이미 출력된 prefix는 회수할 수 없으므로 exit와 전체 JSON을 함께 확인한다.

reports는 순서대로 group/case_id/원문 report를 보존한 detached copy다. audit_counts와
observed_rollout_counts,전체 difference_count와reported_difference_count,어느 case의
differences_truncated 여부를 따로 집계한다. case별 앞256경로 한도를 바꾸거나 추가로
flatten하지 않는다. expected_reference_model_steps0과reported_synthetic_model_steps도 분리한다.
reported_work_is_runtime_attestation=false다. 별도 profile 증거이지 receipt 자체가 호출 감시기는 아니다.

receipt의 exact field set/schema/contract/case/reference ID·SHA/scope/판정·개수·truncation/
경로/denial flags와 GATES의 exact type을 확인한다. MATCH에서는 정해진 model count와
observed 판정을 확인한다. 입출력 identity는 내부 계약 shape이며 새 외부 출처 인증이 아니다.
DIFFERENT는 보존·계속 처리하고,exception이나 잘못된 receipt는 즉시 중단한다.
reference 검산은 각 기존 audit에서 수행하며 suite 전체의 atomic 선행 검산이 아니다.
뒤 case 실패 전에 합성 작업이 이미 실행될 수 있다. retry/fallback/부분 성공은 없다.

case 실패는 REFERENCE_SUITE_CASE_FAILED:<group>:<case>:WORK_MAY_BE_NONZERO,
receipt 실패는 REFERENCE_SUITE_RECEIPT_INVALID:<group>:<case>:WORK_MAY_BE_NONZERO다.
CLI 구문 오류는 REFERENCE_SUITE_USAGE_NO_MODEL_EXECUTION,기타 오류는
REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO다. BaseException은 전파한다.
고정 code/str 외 chained developer traceback에는 진단 경로가 남을 수 있다.

CLI는 parser부터 출력까지 bytecode 쓰기를 억제하고 sys.path/flag를 finally에서 복원한다.
초기 imports/cache는 호출자 책임이므로 -I -B를 유지한다. short descriptor write는 완료하며
help/stderr/stdout 실패를 성공으로 처리하지 않는다. shell redirection은 명령 밖의 동작이다.
코드/참조 원본에 stdout을 redirect하지 않는다. trusted in-process API이지 임의 객체 validator,
Python/filesystem sandbox·스레드 격리·atomic snapshot·filesystem deadline은 아니다.

실제 r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71·실차 활성화 NOT_ALLOWED.
실제 inputs/F61/Controller/Runtime/CAN/실제 r/dt0. 합성 모델/검증 작업은 비영이다.
