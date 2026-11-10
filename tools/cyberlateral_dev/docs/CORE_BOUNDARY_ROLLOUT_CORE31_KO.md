# CORE31 — 합성 상태 전이 경계의 참조 대조

CORE30과 이 세 case를 한 번에 실행하려면 [CORE32 고정 회귀 명령](CORE_REFERENCE_SUITE_CORE32_KO.md)을
사용한다. 이 API·참조·계산식은 그대로이며 전체 suite의 명시 실행은 별도19model steps다.

[CORE30](CORE_ROLLOUT_REFERENCE_CORE30_KO.md)을 보존하고 별도 세 예제를 추가한다.
기존 모델·CORE27 계산식·CORE28/29/30·CLI·wheel은 바꾸지 않는다. 새 Python API이며
임의 파일 reader나 새 CLI·실차 stream·F61 연결이 아니다.

```python
from integration_tools.core_boundary_audit import audit_boundary_case

result = audit_boundary_case('fault-reset')
print(result['audit_status'])           # CLOSED_BOUNDARY_REFERENCE_MATCH
print(result['synthetic_model_steps'])  # 4
```

## 예제와 수동 기대값

모두 합성 scale16,UP2/DOWN5,driver allowance7/factor1/multiplier3,driver1.5다.
driver raw bounds41.5/-32.5가16/-16으로 제한된다. 실제 차량 한계나 승인 scale이 아니다.

| case | 모델 step | 수동 기대값 |
|---|---|---|
| inactive-resume | 3 | limited2/-2/2와 final0/-2/2 구분; 복귀 entry는 post-gate0; counter0/1/2 |
| fault-reset | 4 | counter89/90/0/1,steer request true/false/false/true; final2/-2/2/-2 |
| rounding-ties | 6 | products±0.5/±1.5와±0을 ties-to-even으로0/2/0/-2/0/0 |

Inactive 예제는 active false/true/true,angle85다. 첫 limited2가 gate 이후0이 되고,
복귀 호출은 이전 limited2가 아니라 final0을 소비한다. bounds는[-4,2]/[-2,2]/[-4,2]다.
Fault 예제는 active true/angle85,seed counter88이다. counted<=89에서 request가 true이고,
counted91에서 counter가0으로 돌아간다. false steer request는 active torque를0으로 만들지 않는다.
이는 합성 모델의 규칙이지 물리적 안전 제한의 인증이 아니다.

Rounding 예제의 요청은1/32,3/32,-1/32,-3/32,+0,-0이고,angle0/active true다.
입력 binary32 words3d000000/3dc00000/bd000000/bdc00000/00000000/80000000을 보존한다.
요청/product의 -0x0.0p+0은 유지되지만 int(round(...))의 zero와 projected output은+0이다.
출력 float.hex와 binary32도 비교한다. signed zero를 근사값 비교로 합치지 않는다.

## 참조와 실행 순서

reference/core31_boundary_expected_v1.json,5357bytes,
SHA256 `a9acf091ecf2cd2bb4a5ae37fcadfcd9c292bbab6534f43d926f2bb9ddb79745`.
수동 기대값과 구조적 입력 identities는 새 boundary 모델/audit 실행 전에 커밋했다.
기존 baseline·과거 결과는 이미 있으므로 blind evaluation/외부 독립기관 인증은 아니다.
입력 SHA는 factory 생성 bytes의 구조적 guard이며 독립 수치 oracle가 아니다.

Factory는 기존 typed snapshots를 조립할 뿐 model/quantizer를 호출하지 않는다.
선언 timestamp는 invocation-order marker이며 actual dt나10ms control period 증거가 아니다.
초기 frame/seed의 anchor transition·prehistory는 실행/검증하지 않는다.
structural input_record는 CORE28 serializer를 재사용하지만 contract를
CORE31_CLOSED_BOUNDARY_INPUT_V1로 명시한다. 새 case를 CORE28 API에 추가한 것이 아니다.

reference assembly는 model/target/quantizer/oracle를 import·실행하지 않는다. 기존 model-free
표현 helper와 수동 literal/float.fromhex만 사용한다. SHA는 vector bytes의 핀이며 assembly
source/외부 출처에 대한 서명이 아니다. ref 파일은 정규 파일 bounded single capture 후
size/full SHA를 확인하고 JSON 해석한다. 임의 사용자 reference 경로는 받지 않는다.

audit_boundary_case 순서는 exact built-in case 검사 → ref identity → catalog/input size+SHA
guard → CORE27 한 번 → 기존 CORE30 관측/비교 helper다. 전체 LateralOutput과 상태 역할·
차이 목록·계약 metadata를 exact type/float.hex로 비교한다. prepared 내부 객체 전체나 실제
provenance 의미의 일반 validator는 아니다. 모든 차이를 세고 정렬된 JSON pointer 앞256개를
보고하며 truncated flag를 구분한다. 기존 CORE27 MATCH 의미도 확대하지 않는다.

정상 세 예제는 observed rollout MATCH/audit0이다. 출력 차이는 audit1이며 원래 rollout
판정과 별도다. 여기에는 정상으로 처리할 rejection case가 없다. case/reference/setup/input
오류는 BOUNDARY_AUDIT_CASE/REFERENCE/SETUP/INPUT_IDENTITY,
실행/결과 오류는 BOUNDARY_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO 또는
BOUNDARY_AUDIT_RESULT_FAILED_WORK_MAY_BE_NONZERO다. 부분 성공/거짓0작업/retry/fallback은 없다.
BaseException은 전파한다. 고정 code/str 외 chained traceback에는 개발 진단 경로가 남을 수 있다.

reported model steps는 기존 CORE27 계약에 의존하며 독립 runtime attestation이 아니다.
별도 검증에서 실제 호출을 profile한다. 참조 assembly model/quantizer0과 actual audit의
3/4/6 model steps를 혼동하지 않는다. numeric preflight/unit/gate 작업도 비영이다.
API invocation은 owned ref 읽기 외 출력/temp를 만들지 않는다. 초기 import/cache는 호출자
책임이며 -I -B 사용을 권장한다. trusted in-process API이지 Python/filesystem sandbox,
atomic snapshot 또는 filesystem deadline은 아니다.

실제 r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71·실차 활성화 NOT_ALLOWED.
실제 inputs/F61/Controller/Runtime/CAN/실제 r/dt0,합성 계산/검증 작업은 비영이다.
