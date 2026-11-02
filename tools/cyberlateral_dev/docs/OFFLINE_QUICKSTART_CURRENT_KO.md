# 현재 오프라인 개발판 사용 안내

구현 설명의 검토 기준은 commit `8082ec3651aad95885512fe0060036f112b65bd9`입니다.
실행 결과는 매번 새로 생성한 SUMMARY/RESULTS/Manifest로 확인합니다. 문서나 source
inventory만으로 테스트 PASS, 최신 GitHub 상태 또는 실차 적격성을 판정하지 않습니다.

이 개발판은 CyberLateral0.3.0 순수 합성 command/state 모델과 별도의 개발 도구입니다.
전체 CyberPilot 완성판·openpilot 설치본·물리 시뮬레이터가 아닙니다. 저장소 root에
남아 있는 upstream 차량 설치 안내를 이 개발판의 설치 절차로 사용하지 마세요.

추가 DEV 기능 R38은 [별도 참조 검사 안내](SCENARIO_REFERENCE_R38_KO.md)를 따릅니다.
위 검토 commit과 source inventory의 R31–R37 기록을 R38 실행 증거로 사용하지 않습니다.
추가 R39는 [완전한 저장 batch의 일괄 참조 검사](SCENARIO_BATCH_REFERENCE_R39_KO.md)입니다.
위 historical source inventory를 R39 구현·실행 증거로 사용하지 않습니다.

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

공개 wheel과 DEV 도구를 혼동하지 마세요. wheel은 설치 가능한0.3.0 모델/API와
고정 CLI이며 R31~R34나 native 어댑터를 payload에 포함하지 않습니다. `python -m
cyberlateral_dev --input ...` 대신 저장소/개발용 부분 export의 R31 경로를 사용합니다.

[기능·근거 source 목록](OFFLINE_CAPABILITY_INVENTORY_CURRENT.json)은 위 차이와
미구현/미확정 영역을 구분합니다. R30 문서·목록은 R30 당시 기록으로 보존돼 있습니다.

## 1. 준비와 출력 위치

아래는 Bash, 저장소 root 또는 `tools/cyberlateral_dev`가 있는 부분 export root 기준입니다.
기존 private uv0.12.23·CPython3.12.13/Linux x86_64/binary64 DEV 환경을 사용합니다.
이전 venv/cache/STEP7을 덮어쓰거나 전역 PATH/shell rc/CURRENT를 바꾸지 않습니다.
uv가 private 위치에 있다면 현재 작업 세션 PATH만 보완합니다.

```bash
test -f tools/cyberlateral_dev/dev.py
r36_component="$PWD/tools/cyberlateral_dev"
r36_output="$(mktemp -d /tmp/cyberlateral-use-XXXXXX)"
```

출력 부모는 존재해야 하고 각 하위 출력은 **새 경로**여야 합니다. batch/compare 출력은
컴포넌트와 입력 밖에 둡니다. 기존·부분 출력을 삭제/재사용/덮어쓰지 말고 새 경로로
재시도합니다. mktemp 경로는 이번 작업 예시이지 전역 기본 환경 전환이 아닙니다.

의존성이 준비되지 않았다면 새 환경에서 기존 lock으로 bootstrap한 뒤 진행합니다.
root openpilot 설치, submodule/LFS, Docker, native wheel, 차량 장치는 필요하지 않습니다.
아래 명령은 준비된 개발 환경의 --locked --offline 실행 예입니다.

## 2. 모델 실행 없는 입력 사전 검사

```bash
uv run --project "$r36_component" --locked --offline python -B "$r36_component/tools/scenario.py" --input "$r36_component/examples/synthetic_sign_cycle_v1.json" --validate-only
```

exit0은 입력 계약 충족, exit2의 SCENARIO_INPUT_REJECTED는 기존 입력 거절입니다.
검사 JSON은 stdout 한 줄이며 일반 검사 거절의 stderr는 비어 있습니다.
--output은 필요 없으며 함께 지정하면 입력을 읽기 전 usage error/exit2입니다.
PASS는 모델/source/runtime 준비·산술 정답·출처 인증이나 실차 승인이 아닙니다.
상세 필드·거절·제한은 [R37 안내](SCENARIO_VALIDATION_R37_KO.md)를 따릅니다.
정상 실행에는 다음 R31 명령처럼 --output을 별도로 지정해야 합니다.

## 3. 전체 개발 검증

```bash
uv run --project "$r36_component" --locked --offline python -B "$r36_component/dev.py" verify --output "$r36_output/verify"
```

exit0과 `verify/SUMMARY.json`, 전체 checksum을 함께 확인합니다. 실제 테스트 수·자체
compile 수·Ruff/Ty/Codespell/wheel 결과는 해당 SUMMARY와 로그가 기준입니다. 이 검토 기준의
로컬 기록은579 tests/176 compiles였지만 미래 실행에 그 숫자를 고정된 성공 조건으로 대입하지
않습니다. 이것은 컴포넌트 검증이며 전체 openpilot/native/실차 CI가 아닙니다.

## 4. 합성 입력 사본 → 실행 → 읽기 전용 리포트

등록 examples는 보존하고 사본만 편집합니다. 아래는 **편집하지 않은 사본**의 예입니다.

```bash
mkdir "$r36_output/user-scenarios"
cp "$r36_component/examples/synthetic_sign_cycle_v1.json" "$r36_output/user-scenarios/my_sign.json"
uv run --project "$r36_component" --locked --offline python -B "$r36_component/tools/scenario.py" --input "$r36_output/user-scenarios/my_sign.json" --output "$r36_output/single"
uv run --project "$r36_component" --locked --offline python -B "$r36_component/tools/scenario_report.py" --input "$r36_output/single" --output "$r36_output/single-view"
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
uv run --project "$r36_component" --locked --offline python -B "$r36_component/tools/scenario_batch.py" --input "$r36_component/examples/synthetic_sign_cycle_v1.json" --input "$r36_component/examples/synthetic_resumed_v1.json" --output "$r36_output/batch-one"
uv run --project "$r36_component" --locked --offline python -B "$r36_component/tools/scenario_batch.py" --input "$r36_component/examples/synthetic_sign_cycle_v1.json" --input "$r36_component/examples/synthetic_resumed_v1.json" --output "$r36_output/batch-two"
uv run --project "$r36_component" --locked --offline python -B "$r36_component/tools/scenario_compare.py" --baseline "$r36_output/batch-one" --candidate "$r36_output/batch-two" --output "$r36_output/comparison"
```

기본 예제의 각 batch는2완료/거절0/모델5호출/exit0입니다. 파일별 initial_state가
독립적이며 동일 scenario_id라도 상태를 공유하지 않습니다. 출력 index.html에서 각
리포트를 열 수 있습니다. 이 비교는 MATCH/sample5/차이0/새 모델0이 기대값입니다.
같은 입력의 반복 일치이지 정답·성능·출처 인증이 아닙니다. 입력 bytes가 바뀌면 같은
입력 회귀로 취급하지 않습니다. --candidate는 파일 역할 이름이며 차량 Candidate가 아닙니다.

## 6. R35 회귀팩과 종료 코드

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

## 7. 보관·공유·해석 경계

R37 DEV source 추가로 R31/R33의 observed_dev_source_hashes는 바뀝니다. 모델 수치와
wheel은 불변이지만 과거 RESULTS bytes 전체가 같다고 주장하지 않습니다. R34의
기록 비교와 producer identity 변경 표시는 별개입니다.

완전한 batch/compare에는 개인 경로가 있는 receipt와 이를 참조하는 전체 Manifest가
있습니다. 로컬 검증용 원본은 보존하고, 공개할 때는 검토한 portable 부분만 별도 묶음으로
만들어 새 공유 root Manifest를 사용합니다. **portable 공유 ZIP은 완전한 R34 입력이 아닙니다.**
원래 HTML checksum 링크가 공유에서 빠진 파일을 가리킬 수도 있습니다. SOURCE 전체,
venv/cache, 개인 사용 안내/helper/receipt/로그/실차 자료를 공유 묶음에 섞지 않습니다.

각 Manifest는 보통 해당 부모 기준입니다. kit의 SOURCE/KIT Manifest는 kit root,
EXPECTED_BATCH/COMPARE portable Manifest는 해당 reference/output root를 기준으로
검산하는 예외를 구분합니다. REPORT_SHA256SUMS.txt도 빠뜨리지 않습니다.

모델 작업은 위 single4회+기본 batch5회씩이라면 명시적14회입니다. 전체 unit/gate의
추가 합성 모델 작업은 별도 NONZERO이며 전체 작업0회 또는14회로 축약하지 않습니다.
R32/R34의 새 모델0과 모델 실행기 R31/R33의 작업량을 구분합니다. 호출 index는
실제 초·10ms·100Hz를 뜻하지 않습니다.

native R27~R29는 별도 opt-in 고정 합성 경로이며 기본 안내의 필수 단계가 아닙니다.
[기존 native 안내](NATIVE_SUITE_R27.md)를 읽지 않고 pure 환경에 pycapnp를 섞거나,
그 제한된 성공을 범용 외부 메시지·실제 이력·CAN wire 적격성으로 확대하지 않습니다.

실제 r/T2/vehicle scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO,
D2 PERFORMANCE_NOT_EVALUATED, F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN,
F70UH/V/F71 NOT_ALLOWED를 유지합니다. F61/Controller/차량 Runtime/CAN/실차 입력·활성화/
r/dt 산출·후보 성능 평가는 이 사용 흐름의 기능이 아닙니다.
