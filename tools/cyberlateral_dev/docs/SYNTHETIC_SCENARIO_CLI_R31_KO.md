# R31 — 사용자 선언 합성 시나리오 CLI

사용자가 작성한 JSON으로 순수 모델을 호출하고 JSON·CSV를 저장하는 개발 도구입니다.
public0.3.0 패키지·wheel·CLI·산술은 그대로입니다. 검산된 로컬 DEV source 실행이며
설치 wheel 실행이 아닙니다. Linux/CPython3.12.13/binary64만 검증합니다.

## 빠른 실행

CyberPilot 저장소 루트 기준입니다. 출력 부모를 만들고 매번 새 출력 이름을 사용합니다.

```bash
uv sync --project tools/cyberlateral_dev --locked
mkdir -p tools/cyberlateral_dev/out
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/tools/scenario.py --input tools/cyberlateral_dev/examples/synthetic_sign_cycle_v1.json --output tools/cyberlateral_dev/out/r31-sign-1
uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/tools/scenario.py --input tools/cyberlateral_dev/examples/synthetic_resumed_v1.json --output tools/cyberlateral_dev/out/r31-resumed-1
```

sign 예제 final command는 `[2,-2,0,2]`입니다. resumed 예제는 final=-2,
다음 counter=90, steer_request=false입니다. 합성 모델 설명이지 운전·안전 권장값이 아닙니다.
기존 public `python -m cyberlateral_dev`의 고정 catalog 실행은 그대로입니다.

## 입력 V1

[sign 예제](../examples/synthetic_sign_cycle_v1.json)를 복사해 합성값만 편집합니다.
root는 schema_version=정수1, scope="SYNTHETIC_ONLY", scenario_id, limits,
initial_state, samples의 정확한6개 필드입니다. 모든 중첩 키도 예제와 정확히 같아야 합니다.
ID는 영문자로 시작하는1~64자 ASCII 영문/숫자/밑줄/하이픈입니다.
선택·기본·알 수 없는 필드는 없습니다. r/dt/timestamp/차량 문맥/파일 참조를 받지 않습니다.

| 필드 | 명시적 합성 모델 범위 |
|---|---|
| STEER_MAX | builtin int1..2048 |
| STEER_DELTA_UP/DOWN, STEER_DRIVER_ALLOWANCE | builtin int0..64 |
| STEER_DRIVER_FACTOR/MULTIPLIER | builtin int0..8 |
| initial index | int0..4095 |
| previous_applied / 이전 requested | int[-2048,2048] |
| angle_counter | int0..90 |
| sample index | 초기 index부터 인접 증가, 최대4095 |
| request | finite builtin float[-1,1] |
| driver | finite float[-1024,1024], 이진 유리수 분모<=256 |
| angle_deg | finite float[-180,180], 이진 유리수 분모<=256 |
| lat_active | builtin bool |

samples는1..4096개입니다. index0은 previous_requested=null,previous_applied=0,
angle_counter=0이어야 합니다. 재개 상태는 명시적 정수 이전 requested가 필요합니다.
이전 requested/applied를 합치거나 복구하지 않습니다. 제한값·이력은 합성 선언이며
실제 차량 scale/호출 이력/승인 정책의 authority가 아닙니다.

float는 JSON `0.0`, `1.0`, `1e0`처럼 floating token이어야 합니다.
bare `0`, `1`, bool, 문자열은 거부합니다. 한 번 파싱한 binary64를 유지합니다.
`0.3`은 `0x1.3333333333333p-2`이며 R28 Float32 왕복을 하지 않습니다.
signed zero는 입력 hex에 보존되지만 기존 정수 양자화에서 자연히 없어질 수 있습니다.
반올림·제한·정규화·state 전이는 기존 모델 그대로입니다.

파일은 UTF-8 strict JSON, 최대1MiB입니다. BOM/중복 키/NaN/Infinity/overflow/
추가 JSON/주석/float token128자 초과/int token32자 초과/64단계 초과 중첩은 거부합니다.
이는 개발 자원 한도이지 차량 제약이 아닙니다. POSIX nofollow/nonblocking 일반 파일만
한 번 bounded read하며 최종 symlink/FIFO/device/directory는 거부합니다.

## 출력과 실패

- `INPUT.json`: exact raw bytes SHA, typed 입력 투영. float는 hex.
- `RESULTS.json`: 모든 prepared input/state/output, 최종 state, source identity, 닫힌 gate.
- `TRACE.csv`: 고정13개 scalar 열. null은 `null`, bool은 `true/false`.
- `SUMMARY_KO.md`: 범위·모델 호출 수·제한.
- `RECEIPT.json`: 실제 경로·Python 실행파일 hash·import origin·환경. portable이 아닙니다.
- `SHA256SUMS.txt`: 위5개 파일 hash. 소비 전에 CLI 성공과 전체 검산을 모두 확인합니다.

동일 raw bytes/코드의 첫4개 파일은 경로를 옮겨도 같습니다. receipt와 이를 포함한
전체 manifest는 경로에 따라 다르며 동일하다고 주장하지 않습니다. JSON 공백 변경도
raw identity를 바꿉니다. portable 파일은 signed zero/정수/bool 구분을 보존합니다.

기존 출력(깨진 symlink 포함)·부모 부재는 입력 읽기보다 먼저 거부합니다. 전체 입력
검증 후 unchanged p.simulate를 한 번 호출합니다. generic custom 결과는 모델 출력이지
새 독립 수치 oracle의 증명이 아닙니다. 두 예제 literal과 형식·거부·재현성을 검증합니다.
전부 메모리에서 렌더한 뒤 새 출력 경로에 배타적으로 쓰고 `RESULTS.json`을 마지막에
씁니다. 앞선 파일 쓰기 실패 시 결과 marker는 없습니다. crash-atomic/동시성/resume
보장은 없으며 IO/close/crash 중 부분 파일은 남을 수 있습니다. 디렉터리 또는 RESULTS
존재만 성공으로 취급하지 않습니다. 삭제·덮어쓰기 없이 새 출력 이름을 사용해야 합니다.

오류는 stderr `REJECTED: SCENARIO_*`, exit2입니다. suffix는 다음과 같습니다.
KEYS/SCHEMA/SCOPE/ID/DOMAIN/STATE/ORDER/COUNT/JSON/SIZE/INPUT_FILE,
OUTPUT_EXISTS/OUTPUT_PARENT, RUNTIME/SOURCE_IDENTITY/MODEL_IDENTITY/SOURCE_CHANGED,
MODEL_RESULT/MODEL_REJECTED/PUBLICATION_FAILED. 차량 scale·주기·정책 fallback은 없습니다.

## 주장 한계

SYNTHETIC_ONLY는 입력자의 선언이지 실제 출처 인증이 아닙니다. label만 보고 관찰된
actual-input0을 보고하지 않습니다. 이번 검증은 직접 작성한 예제·fixture만 사용합니다.
cooperative process/filesystem 검산이며 악의적 monkeypatch/동시 교체/OS image/
manifest authenticity를 보장하지 않습니다. CLI는 cold private pycache prefix를
사용하나 in-process run_scenario API에는 그 격리 주장이 없습니다.

native/log/CAN wire reader가 아니며 출력은 SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE입니다.
실차 입력/Controller/Runtime/CAN/F61/r/dt 계산은 하지 않습니다.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/차량 scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO, F70UH/V/F71=NOT_ALLOWED입니다.
실차 설치·활성화·성능·물리 안전·전체 CyberPilot 제품 완성은 승인하지 않습니다.

[검증 기록](SYNTHETIC_SCENARIO_CLI_R31_RESULTS.md)
