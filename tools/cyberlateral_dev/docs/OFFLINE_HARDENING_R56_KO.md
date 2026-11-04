# R56 기준 오프라인 경로·캐시 오류 사용 안내

구현 설명의 고정 기준은 main
`6dfb5174a6516c53f64cc0351ac10382cc9485ef` (PR29 통합)입니다.
R57은 이 보충 안내와 진입 링크만 추가합니다. 아래 설명이나 과거 테스트 수를
현재 HEAD·실행 PASS·실차 적격성의 증거로 사용하지 않습니다. 실행 판정은 해당
회차의 종료 코드·JSON·전체 Manifest/receipt로 확인합니다.

[기존 사용 안내](OFFLINE_QUICKSTART_CURRENT_KO.md)는 R49 작성 당시의 R48 검토
기준을 유지합니다. [고정 source 목록](OFFLINE_CAPABILITY_INVENTORY_CURRENT.json)의
SHA를 R56 SHA로 덮어쓰지 않으며, 이 문서가 목록을 재인증하는 것도 아닙니다.
공개 wheel0.3.0은 고정 카탈로그/API입니다. 아래 `tools/` 명령은 별도 DEV 도구이며
wheel에 사용자 `--input` 기능이 생겼다는 뜻이 아닙니다.

## 무엇이 달라졌나

다음은 해당 경계에서 새로 제한한 **미분류 오류**의 설명입니다. 기존의 더 구체적인
거절 코드·우선순위·분류된 오류 객체와 원인은 유지합니다. 모든 실패를 IO 하나로
바꾸거나 parser·후속 worker 결함을 일괄 숨기는 공통 프레임워크가 아닙니다.

| 보완 | 경계와 대표 코드 | 상세 안내 |
|---|---|---|
| R50 | R34 비교의 사전 경로 `OSError`/`ValueError` → `COMPARE_IO` | [저장 batch 비교](SCENARIO_REGRESSION_R34_KO.md) |
| R51 | 입력 reader의 파일 열기 오류 → `SCENARIO_INPUT_FILE`; R37 거절 JSON의 identity는 null | [R31 입력](SYNTHETIC_SCENARIO_CLI_R31_KO.md), [R37 검사](SCENARIO_VALIDATION_R37_KO.md) |
| R52 | R31 실행 metadata 경로: 출력 → `SCENARIO_OUTPUT_PATH`, 입력 → `SCENARIO_INPUT_FILE` | [R31 실행](SYNTHETIC_SCENARIO_CLI_R31_KO.md) |
| R53 | 저장 리포트 reader → `REPORT_INPUT_FILE`; R32 frontend의 출력 metadata/해석 → `REPORT_OUTPUT_PATH` | [R32 리포트](SCENARIO_REPORT_R32_KO.md) |
| R54 | public 참조 사전 검사 → `REFERENCE_IO` / `BATCH_REFERENCE_IO` | [R38 참조](SCENARIO_REFERENCE_R38_KO.md), [R39 참조](SCENARIO_BATCH_REFERENCE_R39_KO.md) |
| R55 | 공통 R33 경로 사전 검사 → 새 DEV `BATCH_IO`; R40 baseline의 `WORKFLOW_PATH_ENCODING`/`WORKFLOW_BASELINE_LOCATION`; R42/R43 출력 사전 검사 → 기존 `EXPLORATION_IO`/`CAMPAIGN_IO` | [R33](SCENARIO_BATCH_R33_KO.md), [R40](SCENARIO_WORKFLOW_R40_KO.md), [R42](SCENARIO_EXPLORATION_R42_KO.md), [R43](SCENARIO_CAMPAIGN_R43_KO.md) |
| R56 | 아래 네 CLI의 임시 캐시 **생성자** `OSError` → 각 기존 IO 코드, exit2 | 아래 캐시 경계 설명 |

R54에서 긴 입력 경로는 non-strict 해석 후 기존 owned reader까지 도달해
`REPORT_INPUT_FILE`/`COMPARE_INPUT_FILE`로 거절될 수 있습니다. 긴 출력은 사전 검사
IO 코드입니다. 모든 경로 오류가 입력 읽기 전에 발생한다고 일반화하지 않습니다.

## Unicode·surrogateescape·NUL을 구분하세요

일반 Unicode 경로는 지원합니다. 유효한 Linux surrogateescape 파일명은 generic
입력 reader/R37 또는 경로를 receipt에 쓰지 않는 직접 리포트 reader/R38에서 지원할
수 있지만, R31 실행·R32 frontend·R39 등의 strict UTF8 metadata 제약과는 다릅니다.
R37 입력 검사가 통과해도 같은 경로를 R31 receipt로 표현할 수 있다는 보장은 없습니다.
자세한 위치별 우선순위는 위 원본 안내를 따릅니다.

NUL은 OS argv에 전달할 수 없습니다. 해당 회귀 검사의 fresh-child `main(argv)`
호출을 일반 셸 argv 실행과 혼동하지 마세요. 경로를 자동 정규화·교정하거나 입력
bytes·identity를 추정해서 거절을 우회하지 않습니다.

## 캐시 생성 실패는 어디까지 처리하나

| CLI | 캐시 생성 실패의 stderr | 종료 코드 |
|---|---|---|
| R33 `scenario_batch.py` | `REJECTED: BATCH_IO` | 2 |
| R40 `scenario_workflow.py` | `REJECTED: WORKFLOW_IO` | 2 |
| R42 `scenario_explore.py` | `REJECTED: EXPLORATION_IO` | 2 |
| R43 `scenario_campaign.py` | `REJECTED: CAMPAIGN_IO` | 2 |

argparse 옵션 검사가 먼저이고, 캐시 생성은 domain parameter 검사보다 먼저입니다.
이 표는 `TemporaryDirectory` 생성자에서 난 `OSError`에 한정됩니다. R56은 새 오류
코드나 Python 표준 임시 경로 선택 외의 추가 fallback을 만들지 않습니다. R40의
다른 단계가 공통 R33 `BATCH_IO`를 전달할 수 있으므로 R40의 모든 실패를
`WORKFLOW_IO`라고 해석하지 않습니다.

manager entry/exit·후속 import/worker/출력·프로그래머 오류·interrupt 전파는 기존과
같습니다. stderr 자체가 고장 나면 위 진단 전달도 실패할 수 있습니다. 정리 성공,
crash 복구·동시성·원자성·영속성·출처 인증을 새로 보장하지 않습니다. 기존 결과가
있거나 부분 출력이 남으면 삭제/덮어쓰기/재개하지 말고 새 출력 이름을 사용하세요.
전역 임시 경로·권한·검사 설정을 바꾸는 자동 우회 절차는 제공하지 않습니다.

## 안전한 확인 예제

준비된 저장소 root에서 실행합니다. CPython3.12.13·uv0.12.23/Linux와 기존 lock의
DEV 의존성이 필요하며, 설치·다운로드·차량 연결 명령은 포함하지 않습니다.
각 Bash 블록은 같은 셸에서 순서대로 실행합니다. 두 번째의 의도적 exit2를 기록해야
하므로 `set -e` 자동화에서는 예상 거절을 별도로 처리하고 성공으로 덮지 마세요.
`mktemp`는 새 빈 작업 폴더만 만들며, 아래 R37 명령은 제품 결과 폴더를 만들지 않습니다.

```bash
r57_component="$PWD/tools/cyberlateral_dev"
r57_scratch="$(mktemp -d /tmp/cyberlateral-r57-check-XXXXXX)"
uv run --project "$r57_component" --locked --offline python -B "$r57_component/tools/scenario.py" --input "$r57_component/examples/synthetic_sign_cycle_v1.json" --validate-only
```

예상: exit0, stdout의 `SCENARIO_INPUT_VALID`/`accepted=true`, 모델 실행0.
이는 입력 계약 검사이지 독립 수치 검증이나 실제 출처 인증이 아닙니다.

```bash
uv run --project "$r57_component" --locked --offline python -B "$r57_component/tools/scenario.py" --input "$r57_scratch/missing.json" --validate-only
```

예상: exit2, stdout의 `SCENARIO_INPUT_REJECTED`와 `SCENARIO_INPUT_FILE`, stderr는
빈 bytes입니다. input SHA·scenario ID·sample 수·처음/마지막 index는 null이고 모델
실행0입니다. 이 R37 JSON 방식을 다른 CLI의 stderr `REJECTED: <code>`와 구분하세요.

```bash
(cd "$r57_component" && uv run --project . --locked --offline python -B -m unittest discover -s project -p test_scenario_producer_cli_cache.py -v)
```

이 명령은 **기존** R56 회귀10개를 실행하며 새 테스트나 새 API가 아닙니다. 실제
mode000 검사는 비특권 Linux actor가 필요합니다. root에서 건너뛴 검사를 PASS로
계산하지 마세요. 캐시 거절뿐 아니라 기존 후속 오류 전파도 검사합니다. R37 명령의
모델0과 전체 unit/gate의 추가 합성 작업 NONZERO/미집계는 구분합니다.

## 유지 제한

실제 r/T2/scale=null, R_BUDGET=UNRESOLVED, STATIC_EVIDENCE_GATE=FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN입니다.
F70UH/F70V/F71·실차 설치/활성화·실제 F61 계산·Controller/Runtime/CAN 실행을
허용하지 않습니다. 합성 입력 승인·문서 링크·checksum 일치가 차량 승인으로 바뀌지 않습니다.
