# 현재 오프라인 개발판 사용 안내

구현 설명의 고정 검토 기준은 R48 main commit
`d599d53c96dd965545da368ea699b661d1d07907`입니다. R49는 사용 안내만 갱신합니다.
실행 결과는 매번 새로 생성한 SUMMARY/RESULTS/Manifest로 확인합니다. 문서나 source
inventory만으로 테스트 PASS, 현재 HEAD·최신 GitHub 상태 또는 실차 적격성을 판정하지 않습니다.

이 개발판은 CyberLateral0.3.0 순수 합성 command/state 모델과 별도의 개발 도구입니다.
전체 CyberPilot 완성판·openpilot 설치본·물리 시뮬레이터가 아닙니다. 저장소 root에
남아 있는 upstream 차량 설치 안내를 이 개발판의 설치 절차로 사용하지 마세요.

노트북 없이 클라우드에서 개발할 수 있습니다. Git checkout과 준비된 DEV 환경이 있으면
아래 순수 오프라인 흐름을 바로 사용합니다. 새 환경의 고정 HF 복구는
[클라우드 안내](../../cyberlateral_cloud/README_KO.md)의 **고정 R48 복구 기준**을
따릅니다. private Dataset 접근 권한이 필요하며 HF는 전체 openpilot 설치본이 아닙니다.
복구 source는 등록된 읽기 전용 DEV snapshot이지 Git working tree가 아닙니다.
수정은 정확한 baseline에서 만든 별도 개발 branch에서 하고, snapshot을 덮어쓰지 않습니다.

## 어떤 명령을 써야 하나

| 목적 | 사용할 인터페이스 | 모델 작업과 제한 |
|---|---|---|
| 명시적 합성 sample/state 계산 | 공개 Python step / simulate | pure 모델; 실제 이력·시간 증명 아님 |
| 설치한 wheel의 고정 카탈로그 | python -m cyberlateral_dev | 고정 카탈로그만; 사용자 --input 없음 |
| 합성 JSON 사전 검사만 수행 | tools/scenario.py --validate-only (R37) | 입력 계약만; 모델 import/실행0, 결과 파일 없음 |
| 사용자 선언 합성 JSON 실행 | tools/scenario.py (R31) | 별도 DEV 도구; bounded JSON과 명시적 상태 |
| 저장된 R31 결과 보기 | tools/scenario_report.py (R32) | 검산 후 HTML/VIEW 생성; 새 모델0 |
| 여러 파일을 독립 실행 | tools/scenario_batch.py (R33) | 파일 사이에 상태를 전달하지 않음 |
| 완전한 저장 batch 비교 | tools/scenario_compare.py (R34) | 새 모델0; 정확한 저장값 비교이지 산술 증명 아님 |
| 고정 경계 회귀팩 | examples/r35 + 별도 literal (R35) | 정상6개/38호출과 의도적 거절3개 |
| 완전한 저장 R31의 독립 참조 검사 | tools/scenario_reference_check.py (R38) | 새 public 모델0, 참조/helper 계산 NONZERO; 차량 승인 아님 |
| 완전한 저장 batch의 독립 참조 검사 | tools/scenario_batch_reference_check.py (R39) | case별 R38·거절 사유 구분; 새 public 모델0, 참조/helper NONZERO |
| 합성 입력부터 리포트·독립 참조·선택 회귀까지 | tools/scenario_workflow.py (R40) | 실제 모델/참조 작업 NONZERO; 입력 거절·오류·차이를 분리 |
| 복합 경계·긴 상태 전이 고정팩 | examples/r41 + R40 (R41) | 한 회차 324모델/324참조; 실제 시간이나 차량 정책 아님 |
| seed 기반 단일 탐색 | tools/scenario_explore.py (R42) | 기존 모델/독립 참조 NONZERO; 전체 비일치 입력 보존, exhaustive coverage 아님 |
| 명시한 여러 seed의 캠페인 | tools/scenario_campaign.py (R43) | seed/case 사이 상태 독립; 완료 ERROR와 DIFFERENT를 보존 |
| 완전한 저장 캠페인 비교 | tools/scenario_campaign_compare.py (R44) | 새 모델/참조0; 원본 판정과 저장 회귀 판정 분리 |
| 저장 캠페인 비교의 HTML·VIEW | tools/scenario_campaign_compare_report.py (R46) | 새 모델/참조0; 리포트 생성 성공은 원본 수치 성공 아님 |

공개 wheel과 DEV 도구를 혼동하지 마세요. wheel은 설치 가능한0.3.0 모델/API와
고정 CLI이며 위 source DEV 도구나 native 어댑터를 payload에 포함하지 않습니다. `python -m
cyberlateral_dev --input ...` 대신 저장소/개발용 부분 export의 R31 경로를 사용합니다.

[기능·근거 source 목록](OFFLINE_CAPABILITY_INVENTORY_CURRENT.json)은 위 차이와
미구현/미확정 영역을 구분하며 각 source SHA는 **위 검토 commit의 bytes**입니다.
작업 중인 파일과 자동 비교하는 gate가 아니며 실행·출처 인증을 대신하지 않습니다.
R30 문서·목록은 R30 당시 기록으로 보존돼 있습니다.

## 1. 준비와 출력 위치

아래는 Bash, 저장소 root 또는 `tools/cyberlateral_dev`가 있는 부분 export root 기준입니다.
기존 private uv0.12.23·CPython3.12.13/Linux x86_64/binary64 DEV 환경을 사용합니다.
이전 venv/cache/STEP7을 덮어쓰거나 전역 PATH/shell rc/CURRENT를 바꾸지 않습니다.
uv가 private 위치에 있다면 현재 작업 세션 PATH만 보완합니다.

```bash
test -f tools/cyberlateral_dev/dev.py
r49_component="$PWD/tools/cyberlateral_dev"
r49_output="$(mktemp -d /tmp/cyberlateral-use-XXXXXX)"
```

출력 부모는 존재해야 하고 각 하위 출력은 **새 경로**여야 합니다. batch/compare 출력은
컴포넌트와 입력 밖에 둡니다. 기존·부분 출력을 삭제/재사용/덮어쓰지 말고 새 경로로
재시도합니다. mktemp 경로는 이번 작업 예시이지 전역 기본 환경 전환이 아닙니다.

의존성이 준비되지 않았다면 새 환경에서 기존 lock으로 bootstrap한 뒤 진행합니다.
root openpilot 설치, submodule/LFS, Docker, native wheel, 차량 장치는 필요하지 않습니다.
아래 명령은 준비된 개발 환경의 --locked --offline 실행 예입니다.

## 2. 모델 실행 없는 입력 사전 검사

```bash
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario.py" --input "$r49_component/examples/synthetic_sign_cycle_v1.json" --validate-only
```

exit0은 입력 계약 충족, exit2의 SCENARIO_INPUT_REJECTED는 기존 입력 거절입니다.
검사 JSON은 stdout 한 줄이며 일반 검사 거절의 stderr는 비어 있습니다.
--output은 필요 없으며 함께 지정하면 입력을 읽기 전 usage error/exit2입니다.
PASS는 모델/source/runtime 준비·산술 정답·출처 인증이나 실차 승인이 아닙니다.
상세 필드·거절·제한은 [R37 안내](SCENARIO_VALIDATION_R37_KO.md)를 따릅니다.
정상 실행에는 다음 R31 명령처럼 --output을 별도로 지정해야 합니다.

## 3. 전체 개발 검증

```bash
uv run --project "$r49_component" --locked --offline python -B "$r49_component/dev.py" verify --output "$r49_output/verify"
```

exit0과 `verify/SUMMARY.json`, 전체 checksum을 함께 확인합니다. 실제 테스트 수·자체
compile 수·Ruff/Ty/Codespell/wheel 결과는 해당 SUMMARY와 로그가 기준입니다. 고정 R48 기준의
기록은804 tests/225 compiles이며 미래 실행에 그 숫자를 고정된 성공 조건으로 대입하지
않습니다. 이것은 컴포넌트 검증이며 전체 openpilot/native/실차 CI가 아닙니다.

## 4. 합성 입력 사본 → 실행 → 읽기 전용 리포트

등록 examples는 보존하고 사본만 편집합니다. 아래는 **편집하지 않은 사본**의 예입니다.

```bash
mkdir "$r49_output/user-scenarios"
cp "$r49_component/examples/synthetic_sign_cycle_v1.json" "$r49_output/user-scenarios/my_sign.json"
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario.py" --input "$r49_output/user-scenarios/my_sign.json" --output "$r49_output/single"
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_report.py" --input "$r49_output/single" --output "$r49_output/single-view"
```

R31은4회 순수 모델 작업으로 JSON/CSV를 저장하며 이 예제의 최종 명령은 `[2,-2,0,2]`입니다.
R32는 저장 결과를 검산해 표시할 뿐 모델을 재실행하지 않습니다. `single-view/index.html`을
로컬 브라우저에서 엽니다. 실제 GUI/브라우저 확인은 CLI 결과의 검산과 별개입니다.

입력 계약·bare integer와 float token 구분·초기/재개 상태는
[R31 안내](SYNTHETIC_SCENARIO_CLI_R31_KO.md)를 따릅니다. previous_requested와
previous_applied를 합치거나 누락된 이력을 추정하지 않습니다. r/dt/timestamp/차량 설정
필드는 받지 않습니다. SYNTHETIC_ONLY는 입력자 선언이지 실제 출처 인증이 아닙니다.

## 5. 독립 batch 두 회차 → 정확한 저장 결과 비교

```bash
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_batch.py" --input "$r49_component/examples/synthetic_sign_cycle_v1.json" --input "$r49_component/examples/synthetic_resumed_v1.json" --output "$r49_output/batch-one"
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_batch.py" --input "$r49_component/examples/synthetic_sign_cycle_v1.json" --input "$r49_component/examples/synthetic_resumed_v1.json" --output "$r49_output/batch-two"
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_compare.py" --baseline "$r49_output/batch-one" --candidate "$r49_output/batch-two" --output "$r49_output/comparison"
```

기본 예제의 각 batch는2완료/거절0/모델5호출/exit0입니다. 파일별 initial_state가
독립적이며 동일 scenario_id라도 상태를 공유하지 않습니다. 출력 index.html에서 각
리포트를 열 수 있습니다. 이 비교는 MATCH/sample5/차이0/새 모델0이 기대값입니다.
같은 입력의 반복 일치이지 정답·성능·출처 인증이 아닙니다. 입력 bytes가 바뀌면 같은
입력 회귀로 취급하지 않습니다. --candidate는 파일 역할 이름이며 차량 Candidate가 아닙니다.

## 6. R35 회귀팩과 종료 코드

위 단계를 한 명령으로 연결하려면 [R40 안내](SCENARIO_WORKFLOW_R40_KO.md)의
`tools/scenario_workflow.py --input ... --output <새 폴더> [--baseline <완전한 R33 batch>]`를
사용합니다. workflow root/공유 portable ZIP이 아니라 그 안의 완전한 batch가 baseline입니다.
R40은 mixed 입력에 exit1, 전부 거절에는 NO_COMPLETED_CASES/exit1을 내며 수치 성공으로
표현하지 않습니다. 추가 모델·참조 수와 전체 nested checksum은 종합 결과를 확인하세요.

정확한9개 입력 순서·literal·counter1→0 검증은
[R35 안내](SYNTHETIC_REGRESSION_PACK_R35_KO.md)를 따릅니다. 임의 glob으로 순서를 정하거나
의도적 불량3개를 고쳐서 모두 성공하게 만들지 않습니다. 각 batch는6완료/3거절/모델38호출/
예상 exit1입니다. 완전한 두 회차를 비교하면 MATCH/sample38/차이0/새 모델0이 기대값입니다.

| 명령 | exit0 | exit1 | exit2 |
|---|---|---|---|
| R31/R32 | 완료 | 사용하지 않음 | 입력/환경/출력 오류 |
| R33 | 모두 COMPLETE | 완료했지만 입력 거절 존재 | 요청/환경/worker/기록 오류 |
| R34 | 기록 MATCH | DIFFERENT 또는 검증 불가 입력 | 잘못된 요청/묶음/환경/쓰기 |

단순 exit값만 보지 말고 완료 JSON·정확한 상태/거절 코드·전체 Manifest도 확인합니다.
R35의 예상 exit1을 worker 오류와 혼동하거나 무조건 무시하지 않습니다. `set -e`로
연결하면 예상 exit1에서도 중단되므로 혼합 batch 명령은 각각 결과를 확인합니다.

## 7. 복합 경계 고정팩

[R41 안내](SYNTHETIC_REGRESSION_PACK_R41_KO.md)의 고정 순서3개를 기존 R40으로 실행합니다.

```bash
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_workflow.py" \
  --input "$r49_component/examples/r41/combined_boundaries_v1.json" \
  --input "$r49_component/examples/r41/repeated_inactive_crossing_v1.json" \
  --input "$r49_component/examples/r41/long_fault_cycles_v1.json" \
  --output "$r49_output/boundaries"
```

실제 `boundaries/WORKFLOW.json`을 확인합니다. 기대값은 VERIFIED/3완료/
0거절/324모델/324선택-source 참조이며, reference_status=MATCH·차이0입니다.
합성 scale16/UP2/DOWN5는 차량 scale·r이 아닙니다. 이 호출 수를 초로 환산하지 않습니다.

## 8. 여러 seed 실행 → 저장 캠페인 비교

[R42](SCENARIO_EXPLORATION_R42_KO.md)는 한 seed의 입력 생성·실행·참조를 연결하고,
[R43](SCENARIO_CAMPAIGN_R43_KO.md)은 명시 순서의 여러 seed를 모읍니다. 다음은 두 회차입니다.

```bash
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_campaign.py" \
  --seed 42 --seed 43 --cases 2 --steps 32 --output "$r49_output/campaign-one"
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_campaign.py" \
  --seed 42 --seed 43 --cases 2 --steps 32 --output "$r49_output/campaign-two"
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_campaign_compare.py" \
  --baseline "$r49_output/campaign-one" --candidate "$r49_output/campaign-two" \
  --output "$r49_output/campaign-comparison"
```

각 R43은 MATCH/128모델/128참조/차이0/exit0을 기대하며, seed/case 사이에 상태를 넘기지
않습니다. seed는 재현 조건이지 차량 설정/정책값이 아닙니다. 실패 case는 전체 sequence를
보존하며 자동 최소화·baseline 갱신·r 튜닝은 없습니다. [R44](SCENARIO_CAMPAIGN_COMPARISON_R44_KO.md)는
완전한 R43 폴더를 비교하며 전체/회귀 MATCH·128samples·차이0·새 모델/참조0을 기대합니다.
원본 참조 계산은 과거 기록이며 비교가 다시 실행한 작업이 아닙니다.

| 명령 | exit0 | exit1 | exit2 |
|---|---|---|---|
| R43 | 원본 MATCH | 원본 DIFFERENT | 완료 ERROR 또는 요청/기록/IO 거절 |
| R44 | 전체 MATCH | 전체 DIFFERENT | 완료 ERROR 또는 요청/기록/IO 거절 |
| R46 | 리포트 생성 완료 | 사용하지 않음 | 입력/기록/환경/출력 거절 |

완료 ERROR의 최종 record와 거절·미완료의 marker 부재는 다릅니다. R44에서
`regression_status=MATCH`여도 원본에 ERROR/DIFFERENT가 있으면 전체 status는 그대로
ERROR/DIFFERENT입니다. 저장값의 반복 일치는 새 수치 oracle이나 출처 인증이 아닙니다.

## 9. 저장 비교 리포트 보기

```bash
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_campaign_compare_report.py" \
  --input "$r49_output/campaign-comparison" --output "$r49_output/campaign-view-one"
uv run --project "$r49_component" --locked --offline python -B "$r49_component/tools/scenario_campaign_compare_report.py" \
  --input "$r49_output/campaign-comparison" --output "$r49_output/campaign-view-two"
```

[R46](SCENARIO_CAMPAIGN_REPORT_R46_KO.md)은 complete R44를 검산하고 HTML/VIEW를 만듭니다.
`campaign-view-one/index.html`을 열어 전체 판정·저장 회귀 판정·seed별 상세를 봅니다.
stdout의 REPORT_COMPLETE와 exit0은 **화면 생성 완료**이며 원본 ERROR/DIFFERENT를 성공으로
승격하지 않습니다. 새 모델/참조는0이며 원래 campaign 입력을 다시 읽거나 계산하지 않습니다.
같은 saved 입력의 두 리포트 HTML/VIEW는 byte-identical이어야 합니다. 독립 생성 입력의
private receipt hash가 경로에 따라 바뀌면 리포트 전체 bytes가 같다는 주장은 하지 않습니다.
R45는 비교 경계 IO 거절, R47/R48은 결정된 리포트/비교 결과 이후 정리 진단 보완입니다.
경고 전달 자체는 보장하지 않으며 interrupt·primary 출력·process crash를 숨기는 기능이 아닙니다.
기존 화면 검증 범위와 문서의 한계는 유지하며 이 안내 실행이 새 GUI 실측은 아닙니다.

## 10. 보관·공유·해석 경계

DEV 구현 source 변경은 R31/R33의 observed_dev_source_hashes를 바꿀 수 있습니다. 모델 수치와
wheel이 불변이어도 과거 RESULTS bytes 전체가 같다고 주장하지 않습니다. R34의
기록 비교와 producer identity 변경 표시는 별개입니다.

완전한 batch/compare에는 개인 경로가 있는 receipt와 이를 참조하는 전체 Manifest가
있습니다. 로컬 검증용 원본은 보존하고, 공개할 때는 검토한 portable 부분만 별도 묶음으로
만들어 새 공유 root Manifest를 사용합니다. **portable 공유 ZIP은 완전한 R34/R44/R46 입력이 아닙니다.**
원래 HTML checksum 링크가 공유에서 빠진 파일을 가리킬 수도 있습니다. SOURCE 전체,
venv/cache, 개인 사용 안내/helper/receipt/로그/실차 자료를 공유 묶음에 섞지 않습니다.

각 Manifest는 보통 해당 부모 기준입니다. kit의 SOURCE/KIT Manifest는 kit root,
EXPECTED_BATCH/COMPARE portable Manifest는 해당 reference/output root를 기준으로
검산하는 예외를 구분합니다. REPORT_SHA256SUMS.txt도 빠뜨리지 않습니다.

전체 예제를 한 번씩 실행하면 명시적 모델 작업은 single4+batch5씩2회+R41 324+
R43 128씩2회=594이며, 선택-source 참조는 R41 324+R43 256=580입니다. 전체 unit/gate의
추가 합성 작업은 별도 NONZERO/총합 미집계이며 전체 작업을594로 축약하지 않습니다.
R32/R34/R44/R46의 새 모델0과 실행기/참조 검사기의 작업량을 구분합니다. 호출 index는
실제 초·10ms·100Hz를 뜻하지 않습니다.

native R27~R29는 별도 opt-in 고정 합성 경로이며 기본 안내의 필수 단계가 아닙니다.
[기존 native 안내](NATIVE_SUITE_R27.md)를 읽지 않고 pure 환경에 pycapnp를 섞거나,
그 제한된 성공을 범용 외부 메시지·실제 이력·CAN wire 적격성으로 확대하지 않습니다.

실제 r/T2/vehicle scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO,
D2 PERFORMANCE_NOT_EVALUATED, F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN,
F70UH/V/F71 NOT_ALLOWED를 유지합니다. F61/Controller/차량 Runtime/CAN/실차 입력·활성화/
r/dt 산출·후보 성능 평가는 이 사용 흐름의 기능이 아닙니다.
