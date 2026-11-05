# R70 — 저장된 단계 관찰 요약

완성된 R31 결과 디렉터리의 여섯 파일을 읽고 JSON 또는 Markdown을 stdout으로
출력하는 별도 DEV 도구입니다. 새 모델·선택 소스 reference·F61을 실행하지 않습니다.
기존 public0.3.0 모델·wheel·R31/R32 동작은 바꾸지 않습니다.

## 실행

저장소 root에서 기존 개발 venv로 실행합니다. `SAVED_R31`은 파일이나 portable
공유 subset이 아니라 아래 여섯 파일이 있는 완전한 디렉터리입니다.

```sh
tools/cyberlateral_dev/.venv/bin/python -B tools/cyberlateral_dev/tools/scenario_trace_summary.py --input /absolute/SAVED_R31
tools/cyberlateral_dev/.venv/bin/python -B tools/cyberlateral_dev/tools/scenario_trace_summary.py --input /absolute/SAVED_R31 --format markdown
```

필요한 파일: `INPUT.json`, `RESULTS.json`, `TRACE.csv`, `SUMMARY_KO.md`,
`RECEIPT.json`, `SHA256SUMS.txt`. 추가·누락·손상·한도 초과 파일, symlink와
비정규 파일은 거절합니다. 경로의 symlink ancestor도 허용하지 않습니다.
CPython3.12.13·Linux·binary64가 필요합니다. 기존 read-only R31 reader의
Manifest·schema·CSV·상태·Gate 교차 검증을 모두 통과한 후에만 집계합니다.
입력 파일·설정·기존 결과를 수정하거나 자동 복구하지 않습니다.

기본값은 canonical UTF8 JSON 한 줄과 newline입니다. `--format markdown`은
한국어 표를 출력합니다. `--output`, r/dt/scale 옵션이나 축약 옵션은 없습니다.
정상 exit0·stderr 없음, 입력/옵션/출력 IO 오류 exit2입니다. 검증 오류는 stdout이
비어 있고 stderr에 안전한 `REJECTED: <code>`만 남깁니다(옵션 오류는 usage도 표시).
출력 bytes를 완성한 뒤 쓰지만 stdout의 원자적 publication을 보장하지는 않습니다.
완성된 출력 뒤 임시 cache 정리만 실패하면 결과를 취소하지 않고 경고합니다.

CLI의 backend import는 별도 임시 bytecode cache를 사용하고 이전 prefix를 복원합니다.
직접 API를 import하는 호출자는 자기 interpreter/cache 수명주기를 관리합니다.

## 일곱 관찰 항목

각 항목은 `count`와 `first_sample_index`를 반환합니다. 횟수가 0이면 최초 index는
JSON `null`·Markdown `-`입니다. 첫 index는 선언된 sample index입니다.
resumed 단일 sample의 index가 5이면 최초 index도 5이지 row offset 0이 아닙니다.

| event key | 비교하는 저장값 |
| --- | --- |
| `driver_clip_numeric_changed` | driver clip의 x와 result, 정확한 숫자 비교 |
| `driver_clip_representation_changed` | 같은 두 값의 scalar kind/value 표현 비교 |
| `rate_clip_numeric_changed` | rate clip의 x와 result, 정확한 숫자 비교 |
| `rate_clip_representation_changed` | 같은 두 값의 scalar kind/value 표현 비교 |
| `rate_to_limited_numeric_changed` | rate result와 정수 limited_command 숫자 비교 |
| `fault_condition_true` | 기록된 downstream fault_condition이 true |
| `angle_counter_reset` | 준비된 counter>0이고 저장된 next counter=0 |

int는 float로 반올림하지 않고 정확한 정수로 비교합니다. finite hex float는 해당
binary64의 정확한 유리수 값으로 비교합니다. kind만 다른 값과 -0/+0은 숫자는
같지만 표현은 다릅니다. int64의 2**53+1을 binary64의 2**53과 같다고 처리하지
않습니다. clip·rounding·limit 산술을 다시 실행하지 않습니다.

비교 대상은 같은 정수 command 단계입니다. normalized request와 정수 command를
서로 비교하지 않으며 물리 torque·초당 rate로 바꾸지 않습니다. 이벤트는 겹칠 수
있으므로 합계를 배타적 원인이나 비율로 해석하지 않습니다. fault 조건이 실차 고장은
아니며 request suppression이 최종 command=0이라는 뜻도 아닙니다.

기존 R32의 `recorded_summary`(steps/inactive/limiter/fault suppression)는 별도로
그대로 유지합니다. `recorded_model_steps`는 과거 기록의 호출 수입니다.
`summary_model_executions=0`, `summary_reference_executions=0`은 이 도구의 새
실행 수입니다. sample index는 시간·실제 10ms 주기·dt가 아닙니다.

## 신뢰와 운영 경계

여섯 파일의 bounded bytes를 한 번 캡처하고 그 bytes만 검증·집계합니다. receipt나
producer metadata 경로를 열거나 현재 소스와 대조하지 않습니다. `source_hashes`는
캡처한 여섯 파일의 SHA이며, `source_identity_reauthenticated=false`입니다.
이는 협조적 파일 snapshot의 교차 일관성 검사이지 atomic snapshot·서명·원본
출처 인증이 아닙니다. 잘못된 산술을 모든 중복 기록과 함께 일관되게 재봉인하면
통과할 수도 있습니다. 독립 수치 검증은 별도 R38/R39 범위입니다.

전체 unit/dev gate는 기존 합성 모델·reference를 실제 실행하므로 작업량이 NONZERO입니다.
이 도구의 read-only 검증과 전체 개발 검증의 실행량을 혼동하지 않습니다.

R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, actual_r/T2/vehicle_scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO, D2=PERFORMANCE_NOT_EVALUATED,
F19=LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY=NOT_PROVEN을 유지합니다.
실차 입력·Controller·Runtime·CAN·F61·r/dt 계산과 F70UH/F70V/F71·실차 활성화를
열지 않습니다. 결과 요약 PASS는 차량 안전·성능·배포 승인이 아닙니다.
