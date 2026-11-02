# R38 — 저장된 합성 시나리오의 독립 계산·상태 검증

R31로 만든 **완전한 저장 결과**를 기존 선택 source 참조와 대조합니다.
R34의 같은 저장값 비교와 달리 독립 참조 계산을 실제 수행합니다.
모든 입력에 대한 증명·전체 Controller 동등성·물리 차량 안전 검증은 아닙니다.

## 실행

준비된 기존 CPython3.12.13/NumPy2.5.3 DEV 환경에서 저장소 또는 부분 export root 기준:

```bash
r38_component="$PWD/tools/cyberlateral_dev"
r38_output="$(mktemp -d /tmp/cyberlateral-reference-XXXXXX)"
uv run --project "$r38_component" --locked --offline python -B "$r38_component/tools/scenario.py" --input "$r38_component/examples/synthetic_sign_cycle_v1.json" --output "$r38_output/saved"
uv run --project "$r38_component" --locked --offline python -B "$r38_component/tools/scenario_reference_check.py" --input "$r38_output/saved" --output "$r38_output/check"
```

첫 명령의 모델 작업은4회입니다. 둘째 명령의 **새 public 모델 작업은0**이지만
참조는4 sample을 계산하고 limiter/fault helper를 각각4회 실행합니다.
unit/gate의 추가 합성 모델·참조 작업은 별도이며 프로젝트 전체 작업0회가 아닙니다.
추가 설치/전역 설정/실차 장치는 필요하지 않습니다. 공개 wheel CLI의 옵션은 아닙니다.

입력은 R31의 INPUT/RESULTS/TRACE/SUMMARY/RECEIPT/SHA256SUMS 6파일이 모두 있는
완전한 결과 폴더입니다. 공유 portable 부분집합·batch root·raw JSON은 받지 않습니다.
사용자 JSON은 기존 R37 사전 검사와 R31 실행 후 결과를 검사하세요.
기존 출력/부분 출력을 삭제·덮어쓰기·resume하지 않고 새 경로를 사용합니다.
출력 부모는 존재해야 하며 출력은 입력/컴포넌트 밖이어야 합니다.

## 무엇을 검증하는가

전체 입력의 크기/파일 형태/checksum/schema/중복 표현을 R32와 동일하게 검산한 후,
별도 `-I -B` worker가 현재 검증된 독립 참조를 사용합니다.
bit 기반 양자화·projection, source helper 2개, 별도 state wiring을 재사용합니다.
원본 Controller/schema 전체는 import/compile/실행하지 않습니다.
예상 상태는 참조 자체의 이전 결과로 이어지며 저장된 모델 상태를 따라가지 않습니다.
resumed 시작 상태는 선언된 합성 값일 뿐 실제 과거 이력을 인증하지 않습니다.

모든 prepared sample/state 및 model_output의 정수 명령·clip·fault/request·inactive·
projection·다음 상태와 최종 상태를 exact typed canonical/hex로 비교합니다.
임의 허용오차·clamp·coercion·baseline 갱신은 없습니다. 이름이 oracle인 모델 backend를
다시 호출하는 것이 아닙니다. source/runtime/worker가 없거나 바뀌면 거절합니다.

checksum이 맞는 것도 출처 인증은 아닙니다. 예전 producer identity를 현재 참조와 같다고
가정하지 않으며 저장 metadata의 source/receipt 경로를 따라가지 않습니다.
현재 source hash와 전후 관찰 일치는 협조적 프로세스의 관찰이지 OS/atomic 인증이 아닙니다.

R38 DEV 파일 추가로 R31/R33의 observed_dev_source_hashes와 전체 RESULTS bytes는
이전 버전과 달라집니다. 모델 수치와 public wheel은 그대로이며 과거 digest를 자동 갱신하지
않습니다. 같은 입력 6파일 bytes·현재 참조 source/runtime에서 반복한 검사끼리 비교하세요.
원래 producer의 개인 receipt가 달라지면 입력 hash와 검사 보고서도 달라질 수 있습니다.

## 출력과 종료 코드

`REFERENCE_CHECK.json` 및 이를 덮는 `SHA256SUMS.txt`를 생성합니다.
JSON에는 현재 참조 identity, 입력 파일 hashes, expected-result SHA, 전체 차이 수,
첫 차이와 최대256개 field 차이, reference/helper counts, 닫힌 Gate가 들어갑니다.
개인 경로는 포함하지 않습니다. expected/before와 recorded/after의 방향으로 차이를 표시합니다.

| exit | 의미 |
|---|---|
| 0 | MATCH: 해당 한정 합성 시나리오의 저장값과 참조 일치 |
| 1 | DIFFERENT: 참조와 다른 field가 있음; 정상적으로 완료한 불일치 판정 |
| 2 | 요청/입력/source/runtime/worker/쓰기 오류; MATCH로 대체하지 않음 |

잘못된 입력은 기존 REPORT_* 코드, 새 요청/참조 오류는 REFERENCE_* 코드입니다.
오류가 나면 성공 보고서는 만들지 않으며 쓰기 중 실패의 부분 폴더는 보존합니다.
Manifest와 JSON을 함께 확인하세요. 재계산 결과가 달라도 기대값을 자동 수정하지 않습니다.

## 유지 제한

실제 r/T2/vehicle scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/V/F71 NOT_ALLOWED.
F61·실제 r/dt·Controller·차량 Runtime·CAN·실차 입력/활성화·후보 성능 평가는0입니다.
