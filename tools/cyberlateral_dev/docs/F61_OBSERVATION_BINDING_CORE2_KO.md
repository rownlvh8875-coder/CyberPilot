# CORE2 — 관측 기록과 F61 신호 Adapter V4의 연결 계약

STATUS: STATIC_RECONCILIATION_COMPLETE_BRIDGE_NOT_IMPLEMENTED

CORE1 기준 `f3ac2341cd62f50ded786dc1f8d205cf7aeb45e3`에서 계약을 대조했다.
결과는 [정적 대응표](F61_OBSERVATION_BINDING_CORE2.json)이며 변환기·관측기·새 reader가
아니다. CORE2는 금지된 F-71과 무관한 오프라인 개발 구분명이다.

## 결론

V4 입력의 leaf field41개를 모두 분류하고 UGY의 read role35개를 모두 검토했다.
직접 요청값과 명시적 호출 시각은 후보가 있지만, 기존 관측 기록만으로 완전한
V4 입력을 만들 수 없다. source profile·request-stage active·override·reset·context·
control-mode 근거와 추가 precision 검사가 필요하다. 모든 mapping은 현재 ineligible이다.

이 미해결 상태는 **기존 관측 기록 → V4 bridge**의 차단 조건이다. 노트북의 실제
배포 receipt가 없다는 이유로 합성 seam 개발까지 차단하는 조건이 아니다.
실제 차량 값의 synthetic 재라벨링, fake receipt의 authority 승격은 허용하지 않는다.

## 확인한 원문과 source 차이

| 원문 | ZIP SHA256 |
|---|---|
| F70UGHR | `a2686fe18fe094ef3a9a5b452c71fd36b19f5d340e4aa90d3e95e4abfa879192` |
| F70UGY | `e32eaff919ddbf56a8a8693f9c13e459cef1cd638e6f7f45ff3d989f1986c954` |
| F70UGZ_R1 | `0220fac5e427d4c493fe86ad039dcd2b4b1f3904572990889d60268d44affaad` |

CRC·전체 Manifest·seal을 검산했다. UGY schema/reference-set/field-inventory/read-order
4개 JSON은 UGZ_R1에 들어 있는 사본 및 기존 개발 폴더 사본과 bytes가 같다.
source는 읽기/AST 분석만 했다. F61 원본은 기존 canonical SHA·6735bytes를 확인했고
import·계산·실행 가능한 bytecode compile은 하지 않았다.

UGY의 reference-set은 서로 다른 관찰 시점의 **per-file content 목록**이다.
coherent Git tree나 실행 module-load/build/deployment receipt가 아니다.

| STEP7 reference path | STEP7 bytes | V4 두 historical commit의 같은 path와 비교 |
|---|---:|---|
| `opendbc_repo/opendbc/car/__init__.py` | 7085 | 두 버전 모두 bytes 다름 |
| `opendbc_repo/opendbc/car/car.capnp` | 21300 | 두 버전 모두 bytes 다름 |
| `opendbc_repo/opendbc/car/hyundai/carcontroller.py` | 11291 | 두 버전 모두 bytes 다름 |
| `opendbc_repo/opendbc/car/hyundai/values.py` | 39403 | 두 버전 모두 bytes 다름 |
| `opendbc_repo/opendbc/car/interfaces.py` | 15725 | 두 버전 모두 bytes 다름 |
| `openpilot/selfdrive/car/card.py` | 10134 | 두 버전 모두 bytes 다름 |
| `opendbc_repo/opendbc/car/lateral.py` | 9367 | V4 봉인 ZIP에 해당 path member 없음 |

공통 path6개 × commit2개 =12건 모두 raw bytes 불일치다. 일치 symbol이나 helper
이름을 근거로 STEP7을 V4의 `6ca11a4...` 또는 `1dac44b...` commit으로 기록하면 안 된다.
마지막 행은 **해당 ZIP에 없음**만 뜻하며 전체 Git history의 파일 부재 판정이 아니다.
두 full commit 및 source/document hash는 대응표의 `authorities`/`source_profiles`를 따른다.

## 핵심 대응과 대체 금지

| V4 항목 | 관측 후보/관련 role | 현재 판단 |
|---|---|---|
| current/previous request value | 각자 record의 `request_consumption.requested_torque.binary32_hex` / RQ_Q | 같은 stage 후보, profile 해결 후 exact binary32 embedding 검증 필요 |
| previous request | **previous record의 RQ_Q** | current record의 LA_PREVIOUS나 SAVE가 아님 |
| native dtype/unit/stage | RQ_Q, schema readBits32, C_REQUEST70/CAP_TORQUE367 | 후보 metadata; 다른 profile의 실행 사실을 자동 보증하지 않음 |
| sample time | 각 record의 `invocation.now_nanos` / TIME | signed-int64 text를 exact int로 읽는 후보; float epoch 변환 금지 |
| sequence | 각 record의 `invocation.call_seq` | uint64 exact parse/인접성 검사 후보; frame을 시각·sequence 대용으로 사용하지 않음 |
| source identity | UGY identity의 profile/ref/receipt hash | V4 production commit/repository identity를 제공하지 않음 |
| clock domain/source | UGY의 live/replay 및 explicit apply argument | 명시적 label 대응 후보; clock/time 의미의 독립 결속을 대신하지 않음 |
| request-stage active | FA_ACTIVE·GATE_ACTIVE·FAULT_ACTIVE | 서로 다른 후속 read; 임의 하나를 entry flag로 선택하지 않음 |
| override | 기존 closed record에 해당 request metadata 없음 | driver torque threshold·fault·longitudinal cruise override·False 대체 금지 |
| reset_between_samples | reset/loss generation만 존재 | equal generation에서 False를 자동 생성하지 않음 |
| torque control mode | BRANCH_FLAGS | CANFD bit13은 전송 branch이며 torque-mode authority가 아님; bit24/LC/modelDesire도 대체 금지 |
| synthetic context/provenance | 새 counterfactual envelope metadata | 기존 UNQUALIFIED record에서 derive하거나 실제 자료를 재라벨링하지 않음 |

V4의 `f61_input`도 partial projection이지 실제 FeasibilityInput constructor args가 아니다.
이번 대응표는 그 projection이나 V4 payload조차 만들지 않는다.

## 표현·시간·state·설정 경계

readBits32는 native 메모리 byte order를 추정한 값이 아니라 schema가 정한 MSB-first
8자리 word다. 미래 변환은 finite [-1,1]과 signed zero를 보존하는 exact embedding만
허용해야 한다. 관측 기록의 integer_result/limited state를 STEER_MAX로 나눠 이전 요청을
역산하지 않는다. V4의 scale1은 이미 정규화된 요청의 identity이며 차량 정수 scale이 아니다.

UGZ는 pair timestamp를 **비교만** 한다. 그 PASS는 V4가 요구하는 exact binary64
seconds subset을 입증하지 않는다. V4의 exact10ms 거절과 no nominal-dt fallback은
그대로 유지한다. LIVE/REPLAY를 혼합하거나 carOutput·frame×DT_CTRL·wall clock·None
fallback을 원래 now_nanos로 대체하지 않는다. 실제 제어 주기10ms/100Hz를 주장하지 않는다.

UGZ의 active-only conservative subset은 선택된 active/result flag를 모두 true로
요구한다. V4는 inactive/override/reset flags를 그대로 보존할 수 있다. 따라서 두
checker의 허용 domain도 동일하지 않다. UGZ 결과에서 V4의 flag를 기본값으로 만들지 않는다.

capture epoch만 같아도 controller/configuration/loss/reset context가 다를 수 있다.
새 seam은 이 tuple의 정의·경계와 정상 종료/손실/재진입 처리를 명시해야 한다.
지금 receipt 문자열을 trust registry나 실제 target 검증으로 취급하지 않는다.

RQ_SCALE/LA_SCALE과 반복 driver calibration 및 DELTA read occurrence는 각각 보존할
추적 정보다. 이는 숫자가 source 실행에서 실제 소비됐다는 인증이나 rate policy가 아니다.
DELTA_UP/DOWN은 invocation 차원, F61 r은 normalized_command/s다. CustomSteerMax409,
nominal DT_CTRL 또는 test fixture를 승인 scale/T2/r로 승격하지 않는다.

## 거절 의무와 다음 단계

대응표의 B01~B08은 **미래 구현의 설계 의무 ID**다. 새 runtime reason code가 실행돼
통과했다는 뜻이 아니다. source profile 혼동, active stage 대체, override/reset 기본값,
context 혼합, provenance 승격, control-mode 추정, precision/nominal-time 대체에는
V4 payload를 만들면 안 된다. 기존 V4의 코드·검증 순서·허용 domain은 수정하지 않았다.

다음 CORE3는 명시적 counterfactual in-memory capture seam의 설계 후 구현이다.
최소 source/profile, same-stage request active/override, 명시적 reset 의미,
controller/config/capture/clock/loss/reset context와 raw request/time/sequence를 공급받아야
한다. previous limited state와 소비 설정을 다루면 요청값과 다른 역할로 보존한다.
이미 보존된 관측 schema에 없는 flag를 덧붙여 원본처럼 표현하지 않는다.
V4 source pin을 바꾸지 않으며, source profile이 다른 seam 결과를 V4에 바로 주입하지 않는다.

이번 변경은 docs/static JSON뿐이다. 검증은 hash·AST·field/role coverage·schema pointer·
negative metadata control·JSON 결정성·문서 검사이며 새 runtime 기능 테스트가 아니다.
CORE1의927 tests를 재실행한 것으로 보고하지 않는다. 새로운 기록/관측/변환/계산은0이다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED.
