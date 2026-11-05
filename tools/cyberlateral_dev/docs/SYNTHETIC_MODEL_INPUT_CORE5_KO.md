# CORE5 — 명시적 합성 모델 입력 연결

이 DEV API는 [CORE4](LIMITER_SNAPSHOT_CORE4_KO.md) counterfactual pair와 필수
추가 문맥을 받아 기존 public `cyberlateral_dev` 0.3.0의 **현재 한 호출 입력**을 만든다.
기존 CORE3·CORE4·모델·동결 wheel은 수정하지 않는다. 실제 source의 관측이나 배포
검증이 아니며, CORE4의 설정 선언을 실제 소비 설정으로 인증하지 않는다.

## 필수 입력과 mapping

`integration_tools.synthetic_model_input.prepare_model_input(previous,current,context)`를
사용한다. `previous/current`는 기존 CORE4 frame이다. 추가 carrier
`SyntheticModelContextV1`의 아래 다섯 필드는 모두 필수다. 기본값·fallback·coercion은 없다.

| 추가 입력 | 범위/의미 | 실제 모델 역할 |
|---|---|---|
| scope | `COUNTERFACTUAL_MODEL_INPUT_ONLY` | 합성 선언 경계; 실제 origin 인증 아님 |
| model_index | exact int, 1..4095 | 현재 sample과 entry state의 index; capture sequence에서 추론하지 않음 |
| previous_integer_request | exact int, [-2048,2048] | 이전 요청의 정수 양자화값; previous_applied와 다른 역할 |
| current_driver | exact finite float, abs<=1024, dyadic denominator<=256 | 모델 driver 입력; 물리 단위/실측값 authority 아님 |
| current_angle_deg | exact finite float, abs<=180, dyadic denominator<=256 | 기존 합성 모델의 angle_deg 입력 |

별도 값이므로 이전 제한 출력·현재 요청·0을 previous_integer_request 대신 넣지 않는다.
제공값이 이전 raw 요청과 request_scale에 대한 기존 합성 quantizer 결과와 일치하는지
검사한다. 양자화는 binary64 곱셈 → ties-to-even round → int라는 기존 식을 그대로
사용한다. 누락 필드를 채우는 규칙이나 실제 차량 rate 정책이 아니다.

| 기존 frame에서 읽는 값 | 모델에 연결되는 값 |
|---|---|
| current.request.requested_binary32 | big-endian IEEE binary32를 binary64에 정확히 embed한 current request |
| current.limited_state_at_entry | state.previous_applied |
| current.angle_counter_at_entry | state.angle_counter |
| current.inactive_gate_active | input.lat_active; 아래 active 호환 조건 필요 |
| current.settings.limiter_scale | limits.STEER_MAX |
| current.settings.delta_up / delta_down | limits.STEER_DELTA_UP / STEER_DELTA_DOWN |
| current.settings.driver_allowance/factor/multiplier | 대응하는 STEER_DRIVER 설정 |

scale·상태·설정 범위는 R31/CORE4 합성 subset이다. OEM 또는 원래 production helper의
상한이 아니다. raw signed zero와 subnormal은 보존하며 clamp·임의 정규화·부호 반전은
없다. current saved 상태/counter를 entry state나 계산된 next_state로 쓰지 않는다.
결과에 `next_state`는 없다. 재개 상태를 현재 scale에 clamp하지 않는다. model_index0의
canonical 초기화는 이 API에 넣지 않으며 별도 기존 모델 초기화 API의 역할이다.

## 지원하지 않는 문맥과 거절

기존 모델은 active 하나만 받는다. 이전·현재 각각에서 request_active와 별도
inactive_gate_active가 같아야 한다. 서로 다른 두 호출의 active는 달라도 된다.
한 호출 내부 두 read가 다르면 `MODEL_ACTIVE_READS`, 어느 frame이든 override가 true면
`MODEL_OVERRIDE`로 거절한다. CORE4 자체가 그런 선언을 보존하는 기능은 바꾸지 않았다.

거절 순서는 exact result type → CORE4 pair 재검증 → exact context/scope → index →
previous integer request domain → driver → angle → override → active read 호환 →
모델 version → 이전 요청 양자화 일치다. 코드는 `ModelInputError.code`로 제공하며
원시 입력을 오류 문구에 포함하지 않는다. CORE4 오류는 `MODEL_LIMITER:<원래 code>`다.
0.3.0 version 검사는 API 호환성 검사일 뿐 같은 문자열의 임의 패키지를 인증하지 않는다.

## 실행 경계

결과는 `PreparedSyntheticModelInputV1(previous,current,context)`이며
`limiter_pair`, `model_state`, `model_input`을 검증 후 파생한다. 직접 생성 및
`dataclasses.replace`도 재검증한다. 입력 carrier 생성만으로 검증됐다고 간주하지 않는다.
`synthetic_model_input_allowed=true`는 **합성 모델 입력 적합성만** 뜻한다.
validation_claim은 `CURRENT_INPUT_COMPATIBILITY_NOT_DECLARED_OUTPUT_PARITY`다.
source_identity_reauthenticated 및 V4/F61/실차 허용은 모두 false로 유지한다.

입력 준비 코드는 model.step/simulate·limiter·oracle을 호출하지 않는다. binary32 decode와
이전 요청의 합성 양자화 검사는 비영 작업이다. unit test 중 한 건은 입력이 기존 순수
합성 모델에서 실제 소비되는지 확인한다. 전체 DEV gate도 기존 합성 계산을 실행하므로
이번 단계의 모든 계산이 0이라고 표현하지 않는다. 실제 차량·Controller·Runtime·CAN·
F61 실행 및 실제 r 계산은 0이다.

raw 요청·시각·epoch·설정·현재 saved 선언은 원래 pair에 그대로 보존한다. timestamp는
CORE3의 순서 검사만 통과한 값이며 이 API에서 dt·10ms·nominal period·r/T2로 변환하지
않는다. 영속 history/중복 registry/serialization 인증/악의적 Python 변조 방지 sandbox는
없다. CLI·JSON reader·actual observation→V4/F61 bridge는 이 단계에서 추가하지 않는다.

현재 R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/vehicle_scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71 및 실제 활성화=NOT_ALLOWED다.

다음 오프라인 작업은 준비한 입력에 대한 **선언된 상태 전이의 합성 산술 일치 검사**다.
이 입력 수용만으로 이전·현재 saved 상태가 모델 출력과 같다고 주장하지 않는다.
