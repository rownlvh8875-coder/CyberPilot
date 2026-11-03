# R37 — 모델 실행 없는 합성 입력 사전 검사

R31 V1 합성 JSON을 편집한 뒤 **입력 계약만** 먼저 검사하는 DEV 모드입니다.
기존 read_scenario의 필드·타입·범위·초기 상태·호출 순서·파일 제한을 재사용합니다.
새 schema/coercion이나 public0.3.0 API는 추가하지 않습니다.

## 사용

기존 CPython3.12.13/uv DEV 환경, 저장소 또는 부분 export root에서 실행합니다.

```bash
r37_component="$PWD/tools/cyberlateral_dev"
uv run --project "$r37_component" --locked --offline python -B "$r37_component/tools/scenario.py" --input "$r37_component/examples/synthetic_sign_cycle_v1.json" --validate-only
```

검사 전용 모드는 --output 없이 사용합니다. --output과 함께 지정하면 입력을
읽기 전에 usage error/exit2입니다. 기존 모델 실행은 --validate-only 없이
반드시 --output 새 경로를 지정하며 기존 실행·출력 규칙은 유지합니다.
설치 wheel의 `python -m cyberlateral_dev`에는 이 DEV 옵션이 없습니다.

## 결과와 종료 코드

정상적인 검사 요청은 stdout에 canonical JSON 한 줄을 출력합니다.

| 결과 | exit | status | rejection_code |
|---|---|---|---|
| 입력 계약 충족 | 0 | SCENARIO_INPUT_VALID | null |
| 기존 입력 검사 거절 | 2 | SCENARIO_INPUT_REJECTED | 기존 SCENARIO_* 코드 |
| CLI 옵션 오류 | 2 | JSON 없음; argparse stderr | 해당 없음 |

검사 거절은 traceback 없이 JSON으로 전달하며 stderr는 비어 있습니다.
예상하지 못한 구현 오류는 정상 검사 결과로 숨기지 않습니다.
의도적 불량 fixture의 exit2를 성공으로 바꾸거나 무조건 무시하지 않습니다.

contract_id는 F70UGZ_R37_SCENARIO_INPUT_VALIDATION_V1, schema_version은1입니다.
accepted는 bool, model_executions는0, gates는 기존 닫힌 정책의 사본입니다.
accepted일 때 input_raw_sha256/scenario_id/sample_count/first_index/last_index는
검사한 bounded snapshot의 값입니다. 거절 시 다섯 필드는 모두 null입니다.
first/last index는 호출 순서이지 초·주기·timestamp가 아닙니다.
개인 파일 경로·receipt·모델 출력은 JSON에 포함하지 않습니다.

R51의 입력 열기 경계 보완으로 NUL·인코딩 불가 경로도 SCENARIO_INPUT_FILE로
거절합니다. stdout은 기존 canonical 거절 JSON, stderr는 빈 bytes, exit2이며 다섯
identity 필드는 null, 모델 실행은0입니다. parser나 후속 구현 오류의 일반 ValueError를
검사 거절로 숨기지 않습니다. 입력 스키마·수치 계약·출력 형식은 바뀌지 않습니다.

R52의 R31 실행 경로 UTF8 receipt 제약은 이 검사 모드에 적용하지 않습니다.
유효한 Linux surrogateescape 입력 파일도 기존 reader로 검사할 수 있으며, R37 PASS가
그 경로를 R31 실행 metadata에 직렬화할 수 있다는 뜻은 아닙니다.

validation_scope:
INPUT_SCHEMA_AND_DOMAIN_ONLY_NOT_MODEL_RUNTIME_OR_ORIGIN

input_origin:
CALLER_DECLARATION_NOT_AUTHENTICATED

## PASS의 정확한 의미

PASS는 입력 형식·제한을 만족한다는 뜻뿐입니다. 모델, engine, runner,
source identity 또는 실행 환경 verifier를 import/실행하지 않습니다.
따라서 모델이 없는 최소 export에서도 검사할 수 있지만 그 export가 모델
실행에 필요한 파일을 갖췄다고 판단하지 않습니다. 실제 실행은 기존 R31의
source/runtime 검증을 별도로 통과해야 합니다.

입력에 SYNTHETIC_ONLY라고 쓰는 것은 입력자 선언이며 실제 출처 인증이 아닙니다.
SHA는 reader가 확보한 bytes snapshot에 대한 값이지 현재 파일의 atomic 상태나
실제 이력·차량 데이터의 진위 증명이 아닙니다. 범용 모델 산술 oracle, feasibility,
성능·물리 안전·차량 사용 승인을 뜻하지 않습니다.

모드 자체는 결과 디렉터리·HTML·receipt·Manifest를 만들지 않습니다. 기존 CLI의
일시적 private bytecode cache 공간만 허용하며 종료 시 정리합니다. stdout을
파일로 저장하는 것은 호출자가 선택하는 별도 동작입니다.

이번 DEV module 추가로 일반 R31/R33 결과의 observed_dev_source_hashes는 바뀝니다.
기존 모델 수치와 wheel은 그대로지만 과거 RESULTS.json bytes 전체와 동일하다고
주장하지 않습니다. 같은 현재 source의 반복 출력·수치를 비교해야 합니다.

## 유지 제한

R31의 bare integer/float token 구분, state/범위/순서, unknown field 거절은
그대로입니다. rate_budget_per_s·dt·timestamp·실차 설정을 새로 받지 않습니다.
실제r/T2/scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.
검사 모드 모델 호출0과 전체 unit/gate의 합성 모델 작업 NONZERO는 구분합니다.

[현행 사용 안내](OFFLINE_QUICKSTART_CURRENT_KO.md) ·
[기존 R31 입력·실행 안내](SYNTHETIC_SCENARIO_CLI_R31_KO.md)
