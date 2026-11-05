# CORE6 — 현재 선언 상태와 합성 전이 비교

`integration_tools.synthetic_transition_check.check_synthetic_transition(previous,current,context)`는
[CORE5 입력 준비](SYNTHETIC_MODEL_INPUT_CORE5_KO.md)를 다시 수행한 뒤 기존 public0.3.0
합성 모델의 `step`을 한 번 호출한다. 실제 Controller·Runtime·차량 실행이 아니다.
기존 CORE3~5와 모델/wheel은 변경하지 않는다.

## 무엇을 비교하는가

| 현재 선언값 | 계산값 | 비교 의미 |
|---|---|---|
| current.saved_limited_state | model next_state.previous_applied | inactive gate **이후** final command |
| current.saved_angle_counter | model next_state.angle_counter | 현재 호출이 저장할 angle counter |

두 정수를 exact 비교한다. 차이가 없으면 `MATCH`, 하나라도 다르면 `DIFFERENT`다.
`differences`에는 다른 항목만 `SyntheticTransitionDifferenceV1(field,declared,computed)`로
보존한다. 순서는 saved_limited_state, saved_angle_counter다. 허용오차·보정·clamp·선언
덮어쓰기는 없다. computed_next_state와 원래 선언 pair는 별도로 남는다.

예를 들어 CORE5의 명시적 합성 입력(modelindex5, request+0.5, scale16, 이전 요청 정수-4,
entry 제한 상태-2/counter4, driver1.5, angle85)은 next state `(6,8,2,5)`를 만든다.
saved(2,5)는 MATCH, saved(4,5)는 명령 차이 하나, saved(4,6)는 차이 둘이다.
inactive current는 내부 limiter 결과가 nonzero여도 post-gate0/counter0과 비교한다.
이 숫자는 합성 예제이며 차량 scale·r·T2 정책값이 아니다.

## 입력/실행/거절 경계

입력은 CORE4의 두 frame과 CORE5 `SyntheticModelContextV1`이며 모두 필수다.
별도 prepared 객체를 넣어 재검증을 건너뛰는 경로는 없다. CORE5의 exact type·범위·
이전 요청 양자화 일치·별도 active read 호환·override 거절과 CORE3/4의 문맥·순서·
state/settings 연결을 먼저 확인한다. 입력이 거절되면 public model step은 0회다.

정상 입력은 public `step`을 정확히 1회 호출한다. 완료된 결과의 synthetic_model_steps는
1이며 MATCH/DIFFERENT 모두 동일하다. 직접 생성자나 `dataclasses.replace`도 검증과
계산을 다시 한다. cache/자동 rolling replay/영속 history registry는 제공하지 않는다.

`TransitionCheckError.code`는 다음과 같다.

- TRANSITION_TYPE: 정확한 결과 class가 아님.
- TRANSITION_INPUT:&lt;CORE5 code&gt;: 입력 준비 거절. 원래 오류 code는 유지한다.
- TRANSITION_MODEL_FAILURE: model의 ValueError/ArithmeticError. 원인을 보존하며
  결과는 만들지 않는다. 실패 전 합성 작업은 비영일 수 있으므로 0회라고 주장하지 않는다.
- TRANSITION_MODEL_RESULT: 소비할 반환 output/state의 정확한 class·정수 범위·index
  계약이 맞지 않음. bool/float는 정수로 변환하지 않는다.

그 외 예상하지 못한 예외는 전파되며 자동 MATCH/DIFFERENT가 되지 않는다. 출력 검사는
소비하는 next_state 경계에 한정되며 전체 projection/trace 내부 일관성을 인증하지 않는다.
동일 version 문자열만으로 임의 패키지를 인증하지 않으며 별도 source/wheel custody가 필요하다.

## 결과의 한계

`SyntheticTransitionCheckV1`의 derived 필드는 prepared, computed_next_state,
differences, status다. 호출자가 이 필드나 고정 flag를 생성자에 넣을 수 없다.
정상 직접 생성/replace도 재검증한다. 모든 객체는 frozen/slotted지만 악의적인 Python
변조를 막는 security sandbox는 아니다.

checked_fields는 위 두 항목이다. validation_claim은
`CURRENT_SAVED_STATE_COUNTER_ONLY_NOT_PREHISTORY_OR_SOURCE_PROOF`다.
previous_transition_checked=false, prehistory_checked=false이며 실제 source 인증과
V4/F61/실차 활성화 flag도 false다. MATCH는 supplied synthetic input에 대한 **현재 두
상태값의 일치**만 의미한다. 이전 saved 선언을 계산으로 검증하거나 완전한 이력을
재현한 것이 아니다. 모든 intermediate limiter 값이나 전체 output parity도 아니다.

실제 source/build·단일 read·atomic capture·실제 소비 설정·차량/물리 단위·안전·성능은
이 결과로 해결하지 않는다. raw 시각은 보존된 순서 metadata이며 dt·정확10ms·nominal
주기·r/T2로 변환하지 않는다. 원래 설정을 차량 정책으로 승격하지 않는다.

전체 DEV/unit/acceptance는 합성 계산을 실제 실행한다. 원래 F61 계산, Controller·
Runtime·CAN·실제 차량 입력 및 실제 r 계산은 0이다.
R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, 실제 r/T2/vehicle_scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71 및 실제 활성화=NOT_ALLOWED를 유지한다.

다음 우선 항목은 각 호출의 명시적 문맥을 공급하는 **연속 합성 전이 검사**다.
현재 MATCH 하나로 전체 sequence나 관측된 production pair를 인증하지 않는다.
