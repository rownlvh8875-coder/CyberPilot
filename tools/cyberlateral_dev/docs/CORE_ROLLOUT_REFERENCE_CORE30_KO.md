# CORE30 — 고정 rollout의 독립 참조 대조

[CORE27](SYNTHETIC_SEQUENCE_ROLLOUT_CORE27_KO.md)의 MATCH는 entry3필드와 saved2필드의
일치다. [CORE29](CORE_ROLLOUT_INSPECT_CORE29_KO.md)는 과거 bytes 일치만 검사한다.
CORE30은 별도로 모델을 명시 실행하고 고정 세 예제의 전체 model output과 상태 전달을
손으로 도출해 미리 고정한 값에 대조한다. 범용 수치 oracle·실제 source/차량 인증이 아니다.

## 사용과 작업량

기존 개발 환경에서 Python API로 사용한다. 새 CLI나 임의 파일 입력은 없다.

```python
from integration_tools.core_rollout_audit import audit_rollout_case

receipt = audit_rollout_case('declared-difference')
print(receipt['audit_status'])             # CLOSED_REFERENCE_MATCH
print(receipt['observed_rollout_status'])  # DIFFERENT
print(receipt['synthetic_model_steps'])    # 3
```

| case | observed rollout | observed exit | 새 합성 모델 step | 참조와 일치할 때 audit exit |
|---|---|---|---|---|
| sign-cycle | MATCH | 0 | 3 | 0 |
| declared-difference | DIFFERENT | 1 | 3 | 0 |
| late-invalid | REJECTED | 2 | 0 | 0 |

관측된 DIFFERENT/REJECTED가 참조 대조 실패를 뜻하지 않는다. 참조와 다른 필드가 있으면
CLOSED_REFERENCE_DIFFERENT/audit_exit_code1이다. 호출자는 audit 판정과 원래 rollout
판정을 구별해야 한다. Late-invalid도 사전 검증·양자화는 비영이며, 모델0은 전체 작업0이
아니다. expected reference는 모델/quantizer/oracle0이다. import/bytecode는 호출자 관리다.
`-I -B`는 초기 cache 쓰기도 억제한다. API 자체는 reference 읽기 외 출력/temp/네트워크가 없다.

## 기대값의 독립성

reference/core30_rollout_expected_v1.json을 모델 실행 전에 별도 커밋으로 고정했다.
SHA256: `3ba18d20fb93f6c5ee0d432ecacbaa314df40046a9289264b7c1954f4762e5b3`,2132bytes.
`integration_tools.rollout_reference`는 target/model/quantizer/oracle/CORE27을 import·실행하지
않는다. vector를 구조적으로 조립하고 float.fromhex로 정확한 표현만 복원한다. clip·round·
limiter 산술로 기대값을 계산하지 않는다. 이 SHA는 vector bytes의 핀이며 assembly source나
외부 origin의 서명은 아니다. 일반 입력의 정답을 계산하는 함수도 아니다.

수동 계산 근거:

- 합성 scale16, UP2, DOWN5, allowance7, factor1, multiplier3, driver1.5다.
  driver bounds raw41.5/-32.5가 각각16/-16으로 제한된다.
- 요청1/2,-1/2,1/4의 정수 요청은8,-8,4다. dyadic이므로 rounding 모호성이 없다.
- 이전 적용값-2,2,-2의 rate clip 구간은[-4,2],[-2,4],[-4,2],결과는2,-2,2다.
- ±2/16=±1/8의 binary32는3e000000/be000000,정수±2 표현은40000000/c0000000다.
- index5..7은6..8로,counter4..6은5..7로 간다. angle85/active true라 fault condition true,
  counter<=89라 steer request true다. fault flag와 inactive gate를 혼동하지 않는다.
- declared-difference의 선언 entry-2/10/5,saved10/5/4는 계산 상태를 reseed하지 않으며,
  entry 차이는1/2,output 차이는0/1/2다. late-invalid의 driver0.1은 dyadic 제약을 위반한다.

이 독립 literal 기대값의 적용 범위는 좁다. 전체 입력 영역/원래 helper/실차 산술의 보편적
정확성이나 성능을 인증하지 않는다. 기존 계산식과 모델·producer·CLI는 불변이다.

## 실행·비교·오류

case exact built-in str 검사 → owned reference bounded single capture/size/SHA 검사 후 JSON
해석 → catalog 생성 → CORE28 INPUT canonical size/SHA 대조 → CORE27 한 번 → 대조.
입력 identity는 기존 CORE28 serializer를 재사용한 구조적 guard이며 독립 산술이 아니다.
catalog bytes가 바뀌면 ROLLOUT_AUDIT_INPUT_IDENTITY로 막고 새 핀을 자동 생성하지 않는다.

비교 대상: 초기/최종 상태,전이 수/위치/판정,각 row model index·선언/계산 entry·saved상태·
두 차이 목록·전체 LateralOutput(projection/quantization/두 clip/fault/request/final/nextstate),
CORE27 contract/authority metadata. prepared 전체 객체/입력 provenance 의미가 전부 이 record
비교에 포함되는 것은 아니다. 입력 bytes guard는 별도이며 실제 source authority도 아니다.
기존 CORE27 MATCH의 의미를 확대하지 않는다.

exact type으로 bool/int를 구별하고 float.hex로 ±0까지 구별한다. 허용오차는 없다.
순서는 객체 key 정렬·list 위치 기준,JSON pointer에서 ~/를 escape한다. 모든 차이를 세고
앞256개 경로만 반환한다. difference_count/reported_difference_count/differences_truncated를
구분한다. 경로는 관측 구조의 차이 위치이지 성능/물리 단위가 아니다.

오류: ROLLOUT_AUDIT_CASE/REFERENCE/SETUP/INPUT_IDENTITY.
다른 모델/preflight 예외는 ROLLOUT_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO,
결과/비교 예외는 ROLLOUT_AUDIT_RESULT_FAILED_WORK_MAY_BE_NONZERO다.
예상 late-invalid/code 외 예외를 정상 거절로 바꾸지 않는다. 실패 prefix를0작업이나 부분
성공으로 돌려주지 않는다. BaseException은 전파한다. 고정 메시지에 raw/private path는 없다.
trusted in-process API이며 Python sandbox·파일시스템 deadline을 제공하지 않는다.

실제 r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71·실차 활성화 NOT_ALLOWED.
실제 차량 입력·F61·Controller·Runtime·CAN·실제 r/dt0. 오프라인 합성 모델 작업은 비영이다.
