# R40 — 합성 입력부터 독립 검증까지 한 명령

기존 R37 사전 검사 → R33 합성 실행/개별 R32 그래프·표 → R39 독립 참조를 연결합니다.
선택한 완전한 R33 baseline이 있으면 R34 저장값 비교도 합니다. 별도 DEV 도구이며
공개0.3.0 wheel/모델/기존 CLI는 그대로입니다. 추가 설치·차량 장치는 필요하지 않습니다.

## 실행

준비된 CPython3.12.13/Linux x86_64/binary64/NumPy2.5.3 locked DEV 환경에서,
저장소 또는 부분 export root 기준입니다. uv의 PATH는 현재 세션에서만 설정합니다.

```bash
r40_component="$PWD/tools/cyberlateral_dev"
r40_parent="$(mktemp -d /tmp/cyberlateral-workflow-XXXXXX)"
uv run --project "$r40_component" --locked --offline python -B "$r40_component/tools/scenario_workflow.py" --input "$r40_component/examples/synthetic_sign_cycle_v1.json" --input "$r40_component/examples/synthetic_resumed_v1.json" --output "$r40_parent/one"
```

이 예제의 기대값은 VERIFIED /2완료/0거절/합성모델5steps/독립참조5steps/exit0입니다.
`one/SUMMARY_KO.md`가 종합 안내이고 `one/batch/index.html`에서 개별 그래프·표를 엽니다.
별도의 모델 재실행 없이 이미 저장된 리포트를 읽는 것입니다.

같은 입력으로 선택 회귀 비교도 실행하려면 완전한 이전 batch를 지정합니다.
workflow root나 portable 공유 ZIP이 아니라 **그 안의 batch 폴더**입니다.

```bash
uv run --project "$r40_component" --locked --offline python -B "$r40_component/tools/scenario_workflow.py" --input "$r40_component/examples/synthetic_sign_cycle_v1.json" --input "$r40_component/examples/synthetic_resumed_v1.json" --baseline "$r40_parent/one/batch" --output "$r40_parent/two"
```

이 명령도 모델5steps/참조5steps를 새로 수행하고, 별도 R34 비교는 새 모델0입니다.
baseline의 관찰 producer identity가 달라도 기록된 값 MATCH와 구분해 표시합니다.
기준을 자동 수정하거나 차이를 성공으로 바꾸지 않습니다.

## 입력·결과·종료 코드

--input을1..32회 명시하며 합계8192samples 이하 등 기존 R33 제한을 따릅니다.
등록 examples는 수정하지 말고 새 합성 사본을 사용합니다. 파일 사이 상태는 독립적입니다.
원본을 bounded/no-follow 방식으로 한 번씩 읽고 이후에는 소유한 원형 사본을 사용합니다.
읽을 수 없거나 크기를 넘어 원형 bytes를 확보하지 못하면 WORKFLOW_INPUT_UNAVAILABLE /
exit2이며 출력은 만들지 않습니다. 읽힌 불량 JSON은 기존 거절코드를 그대로 보존합니다.
합성 선언은 출처 인증이 아니며 실제 로그/차량/timestamp/r/dt 입력은 지원하지 않습니다.
공통 R33 경로 사전 점검의 미분류 OS/값 오류는 `BATCH_IO`/exit2입니다.
기존 원시 OS 오류의 `WORKFLOW_IO` fallback과 구분하는 새 DEV 진단 코드입니다.
baseline 경로의 UTF-8 오류는 `WORKFLOW_PATH_ENCODING`, 해석 실패는
`WORKFLOW_BASELINE_LOCATION`이며 baseline 읽기·identity·worker 전에 거절합니다.

| 상태 | 뜻 | exit |
|---|---|---|
| VERIFIED | 완료 case 참조 일치, 입력 거절 없음, 선택 회귀도 MATCH | 0 |
| VERIFIED_WITH_INPUT_REJECTIONS | 완료 case는 참조 일치하나 입력 거절이 있음 | 1 |
| REFERENCE_DIFFERENT | 독립 참조와 수치/거절 기록 차이 | 1 |
| REGRESSION_DIFFERENT | 선택 baseline과 저장값/입력이 다름 | 1 |
| INCOMPLETE | 참조에 필요한 증거 불충분 | 1 |
| NO_COMPLETED_CASES | 전부 거절되어 정상 수치 검증 없음 | 1 |
| ERROR | 하나 이상의 참조 계산 오류 | 2 |

우선순위는 ERROR > REFERENCE_DIFFERENT > REGRESSION_DIFFERENT > INCOMPLETE >
NO_COMPLETED_CASES > VERIFIED_WITH_INPUT_REJECTIONS > VERIFIED입니다.
R35 혼합9개를 입력하면6완료/3거절/모델38/참조38이며 의도적 exit1입니다. standalone R39가
같은 mixed 결과에 exit0을 주더라도 R40은 입력 거절을 숨기지 않도록 exit1을 사용합니다.

요청/입력 경로·baseline checksum·source/runtime·worker/IO 실패는 stderr
`REJECTED: <code>`와 exit2입니다. 이 경우 루트 완료 JSON을 만들지 않으며 이미 생성된
부분 폴더는 남깁니다. 출력 중 실패하면 marker가 일부 남을 수도 있으므로 JSON 존재만으로
성공을 판단하지 말고 상태와 전체 root/nested checksum을 함께 확인하세요.

## 보존·정확성·해석 범위

출력 부모가 존재해야 하고 출력은 입력·component·선택 baseline 밖의 새 경로여야 합니다.
기존/부분/깨진 symlink 출력은 거절하며 삭제·덮어쓰기·resume하지 않습니다. 재시도는 새 경로.
baseline은 모델 전에 전체 owned snapshot을 검산하며 이후 원본 경로를 재사용하지 않습니다.
baseline 자체는 읽기 전용으로 component 안에 있을 수도 있습니다.

WORKFLOW.json/VALIDATION.json/SUMMARY_KO.md는 상대 링크·상태·명시적 계산량을 보존합니다.
같은 입력·source/runtime에서는 이 세 파일과 batch portable bytes가 반복 일치합니다.
RECEIPT와 full batch/reference report/전체 Manifest는 개인 경로에 따라 다를 수 있습니다.
whole-runtime 동일성·atomic snapshot·과거 이력 인증은 주장하지 않습니다.

참조/helper 계산은 NONZERO이며 성공 child만 집계됩니다. 실패한 참조 호출도 작업을 했을
수 있으므로 그 count는 미확정입니다. R37/R32/R34/R39 새 public 모델0을 전체 계산0으로
표현하지 않습니다. unit/gate의 추가 합성 작업은 명시적 CLI 실행량과 별도입니다.

전체 SHA256SUMS.txt는 private RECEIPT/원형 합성 입력/nested sums까지 포함합니다.
완전한 결과를 자동 ZIP·공유·publish하지 않습니다. 로컬에 원형을 보존하고 공유 전에
개인 경로·원문·Manifest 참조를 별도로 점검하세요. portable subset은 완전한 baseline이 아닙니다.

이 명령은 bounded 선택 source parity이지 범용 독립 oracle·전체 Controller·물리 차량 안전·
성능 입증이 아닙니다. 실제 r/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/V/F71 NOT_ALLOWED 유지.
F61·실제 r/dt·Controller·차량 Runtime·CAN·실차 입력/활성화·후보 평가는0입니다.
