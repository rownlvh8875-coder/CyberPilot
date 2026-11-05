# CORE4 — 제한 state·소비 settings의 명시적 합성 경계

`integration_tools.limiter_snapshot.prepare_limiter_pair(previous, current)`는
[CORE3 요청 snapshot](REQUEST_SNAPSHOT_CORE3_KO.md)에 요청과 다른 역할의 정수 제한
state·counter·선언 settings를 붙여 연속 두 호출의 연결을 검사하는 순수 DEV API다.
여기서 consumed는 **counterfactual 소비값 선언**이며 실제 source가 소비했다는 인증이 아니다.

## 사용

아래 `previous`와 `current`는 CORE3 문서 예제에서 만든 합성 요청이다.
실제 기록을 재라벨링하거나 새 관측을 수행한 값이 아니다.

```python
from integration_tools.limiter_snapshot import (
    SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1, prepare_limiter_pair,
)

settings = SyntheticConsumedSettingsV1(
    request_scale=16, limiter_scale=16, delta_up=2, delta_down=5,
    driver_allowance=7, driver_factor=1, driver_multiplier=3,
)
before = SyntheticLimiterSnapshotV1(
    request=previous, settings=settings,
    state_stage='DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
    settings_origin='DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS',
    limited_state_at_entry=7, saved_limited_state=-2,
    angle_counter_at_entry=3, saved_angle_counter=4, inactive_gate_active=True,
)
now = SyntheticLimiterSnapshotV1(
    request=current, settings=settings,
    state_stage='DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
    settings_origin='DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS',
    limited_state_at_entry=-2, saved_limited_state=4,
    angle_counter_at_entry=4, saved_angle_counter=5, inactive_gate_active=True,
)
pair = prepare_limiter_pair(before, now)
```

숫자는 허구의 합성 fixture다. 승인 scale/r/T2, 차량 한계 또는 실제 limiter 산출값으로
사용하지 않는다. 이 예제도 arithmetic correctness를 주장하지 않는다.

## 구분하는 값과 검사

| 값 | 역할/검사 |
|---|---|
| `request.requested_binary32` | 같은 stage의 raw normalized 요청; 정수 limited state가 아님 |
| `limited_state_at_entry` | 현재 호출이 이전 limited/gated state로 사용했다고 선언한 정수 |
| `saved_limited_state` | 현재 호출 후 저장했다고 선언한 정수; 다음 호출 entry와 일치해야 함 |
| entry/saved angle counter | 별도 software counter; 이전 saved와 현재 entry를 연결 |
| request_scale / limiter_scale | 별도 선언 read; 같은 frame에서 일치해야 하며 하나를 임의 선택하지 않음 |
| settings7개 | 두 frame에서 모두 같아야 함; 같은 config label만으로 변경을 숨기지 않음 |
| request_active / inactive_gate_active | 요청 시점과 이후 gate의 서로 다른 선언 read; 자동 alias 금지 |

CORE3의 공개 pair 검증을 먼저 재사용한다. scope·source profile·clock/controller/config/
epoch·loss/reset·인접 sequence·원래 시각 순서·raw word·필수 flag를 다시 검사한다.
오류는 `LimiterSnapshotError.code`이며 CORE3 오류는 고정 `LIMITER_REQUEST:` prefix와
원래 고정 code를 붙인다. 입력값이나 실제 source 예외를 전달하지 않는다.

설정7개·frame9개 필드는 모두 필수이고 exact built-in type만 허용한다.
입력 생성자는 immutable carrier이며, factory와 검증 결과 직접 생성자는 같은 검사를
실행한다. result의 derived request_pair는 전체 검사 후에만 설정된다.

- scale1..2048, delta/allowance0..64, factor/multiplier0..8이다. 현재 R31
  `scenario_input.validate_spec`의 bounded 합성 subset을 따른다. `_r4/domain.py`의
  `validate_limiter`는 더 넓은 합성 test subset으로 STEER_MAX4096까지 허용한다.
  이4096 역시 실제 원본 helper가 강제하는 상한이나 production 전체 범위가 아니다.
- 정수 제한 state는 [-2048,2048], counter는 [0,90]이다. 현재 scale로 clamp하지
  않으며 capture sequence0이라고 과거 state를 canonical0으로 만들지 않는다.
- inactive_gate_active=false이면 saved_limited_state는0이어야 한다.
  이 flag는 request_active로부터 추정하지 않는다. 둘이 다르게 선언된 경우도
  구분해서 보존하므로 기존 전체 모델과 곧바로 호환된다는 뜻은 아니다.
- 이전 saved state/counter와 현재 entry state/counter가 각각 같아야 한다.
  설정이 같고 수치가 연결돼도 원래 limiter/rounding/fault 산술 결과인지 확인하지 않는다.

일곱 설정값은 stable aggregate 선언이며 실제 원문에서 반복한 모든 read·ordinal·
branch별 DELTA occurrence를 표현한 관측 ledger가 아니다. 같은 값이라도 실제 소비,
atomicity, single-read, 지연/noninterference 또는 배포 source identity는 입증하지 않는다.

## 권한과 아직 하지 않는 작업

출력 contract_id는 `CORE4_COUNTERFACTUAL_LIMITER_PAIR_V1`, validation_claim은
`DECLARED_STATE_LINKS_NOT_LIMITER_ARITHMETIC_OR_SOURCE_PROOF`다.
source_identity_reauthenticated, model_input_allowed, v4_payload_allowed,
f61_input_allowed, actual_activation_allowed는 모두 constructor-fixed false다.
직접 생성·dataclasses.replace를 이용해 derived pair나 permission을 넣을 수 없다.

이전 정수 요청·driver·angle·model index의 명시적 연결과 기존 합성 모델 입력 변환은
아직 하지 않는다. 요청 sequence를 model index로 자동 사용하거나 이전 정수 요청을
limited state에서 역산하지 않는다. 실제 소비 settings, r/T2/normalization authority,
V4/F61 입력·실행·차량 활성화는 해결되지 않았다. UGY/CORE2 원문과 기존 API는 불변이다.

호출자는 선언값을 이미 materialize한 frozen carrier로 공급한다. 실제 source 객체의
getter나 Controller를 읽지 않는다. cooperative Python 경계이며 악의적 object 재구성,
monkeypatch/동시 변조·직렬화 신뢰·지속 history/replay 인증을 제공하지 않는다.

## 검증

locked venv에서 `python -B -m unittest discover -s project -p test_limiter_snapshot.py -v`.
전체 DEV gate는 별도로 검증한다. 신규 경계의 선언·연결 검사는 NONZERO지만 모델/helper/
native-float/dt/r/adapter/F61 연산은0이다. 기존 전체 unit/gate의 합성 모델/reference/time
작업은 NONZERO_NOT_AGGREGATED다. pair PASS는 limiter arithmetic PASS가 아니다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED.
