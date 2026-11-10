# CORE27 — 계산 상태를 이어가는 순수 합성 rollout

고정 세 예제의 전체 model output을 독립 literal 기대값과 대조하려면
[CORE30 audit](CORE_ROLLOUT_REFERENCE_CORE30_KO.md)를 사용한다. 별도 명시 실행이며,
아래 CORE27 MATCH의 제한된 의미나 실제 차량 Gate를 바꾸지 않는다.

고정 합성 예제를 명령으로 실행·저장하려면
[CORE28 명령](CORE_ROLLOUT_RUN_CORE28_KO.md)을 사용한다.
CORE27 API와 계산식은 그대로 유지하며 CLI는 별도 --run을 요구한다.

`integration_tools.synthetic_sequence_rollout.rollout_synthetic_sequence(frames,contexts)`는
첫 선언 entry에서 시작하고,그 후에는 직전 모델의 `output.next_state` 객체를 그대로
다음 호출에 전달한다. 기존 [CORE7](SYNTHETIC_SEQUENCE_CORE7_KO.md)은 바꾸지 않는다.

CORE7은 각 호출의 **선언된 entry**를 사용하는 독립 진단이고,CORE27은 **계산된 상태**를
연결하는 별도 합성 실험이다. 입력 선언을 자동 수정하거나 실제 차량 이력을 복구하지 않는다.

## 사용과 명시적인 작업량

기존 전용 환경에서 Python API로 사용한다. 새 CLI·JSON reader·차량 stream은 없다.

```python
from integration_tools.core_sequence_cases import build_case
from integration_tools.synthetic_sequence_rollout import rollout_synthetic_sequence

frames, contexts = build_case('declared-difference')
result = rollout_synthetic_sequence(frames, contexts)  # public synthetic model 3 steps
print(result.status)  # DIFFERENT
print(tuple(row.output.next_state.previous_applied for row in result.steps))  # (2, -2, 2)
print(result.entry_differing_transition_indices)   # (1, 2)
print(result.output_differing_transition_indices)  # (0, 1, 2)
```

MODULE/함수 import는 caller-managed다. 명시적으로 API를 호출하면 합성 모델을 실행한다.
성공 시 `synthetic_model_steps=checked_transition_count=len(frames)-1`이며 0이 아니다.
원래 F61·Controller·Runtime·CAN·실제 차량·실제 r/dt 계산은 실행하지 않는다.

## 검증과 상태 전달

1. frames/contexts는 exact tuple,frames2..4096개,contexts는 frames-1개다.
2. 기존 CORE5로 **모든** 인접 입력을 사전 검증한 뒤 model_index 연속성을 검사한다.
   후반 오류도 모델 실행 전 거절하며,사전 양자화·numeric validation은 비영일 수 있다.
3. 첫 entry는 첫 prepared.model_state다. 이 선언 seed의 이전 이력·anchor 전이는 미검증이다.
4. 각 sample로 기존 public model.step을 한 번 실행한다. CORE6 결과 검사로 next_state의
   exact type/index/정수 범위를 확인한다. 이후 entry는 계산된 next_state다.
5. 차이가 생겨도 나머지를 계산한다. 다음 선언 entry로 reseed하거나 원본을 repair하지 않는다.

model_index는 capture sequence·timestamp에서 계산하지 않는다. nominal 10ms나 실제
차량 주기로 승격하지 않으며,reset/epoch/설정 불일치는 기존 CORE5 규칙으로 거절한다.
4096frames의4095전이는 명시 index1..4095를 공급하면 마지막 next_state.index4096이다.

## 결과와 차이의 의미

frozen/slotted `SyntheticSequenceRolloutV1`은 원래 frames/contexts와 steps를 보존한다.
각 step은 prepared,entry_state,원래 model output,두 차이 목록과 status를 가진다.

| 차이 목록 | 비교하는 값 |
|---|---|
| entry_differences | 선언 entry의 previous_requested/previous_applied/angle_counter와 실제 전달한 계산 상태 |
| output_differences | 현재 선언 saved_limited_state/saved_angle_counter와 계산 next_state |

차이는 field/declared/computed 정수 record이며 위 순서대로 보존한다.
해당 차이가 있으면 row DIFFERENT,하나라도 DIFFERENT면 전체 DIFFERENT다.
entry/output 각각의 전이 위치와 합집합 differing_transition_indices를 따로 반환한다.
위치는0부터 시작하는 **전이 순번**이며 target frame 순번은 i+1이다.
initial_declared_state/final_computed_state로 시작 선언과 최종 계산 상태를 구별한다.

declared-difference에서 CORE7은 선언 entry10/5를 사용해 computed 명령2/5/4를 얻는다.
CORE27은 계산 상태2/-2를 이어 명령2/-2/2를 얻고 entry 위치1/2,output 위치0/1/2의
차이를 기록한다. 어느 쪽도 다른 쪽을 덮어쓰거나 실제 차량 정답이라고 주장하지 않는다.
MATCH는 이 합성 체인의 entry3필드·현재 saved2필드 일치이지 전체 projection/trace/
steer-request·원본 산술·실차 성능 인증이 아니다. 원래 output은 별도로 보존한다.

## 오류와 보호

SequenceRolloutError.code는 ROLLOUT_TYPE/CONTAINER/COUNT,
ROLLOUT_INPUT:i:<CORE5code>,ROLLOUT_MODEL_ORDER:i다. 이 단계의 public model step은0이다.
ROLLOUT_MODEL_FAILURE:i:WORK_MAY_BE_NONZERO와
ROLLOUT_MODEL_RESULT:i:<CORE6code>:WORK_MAY_BE_NONZERO는 prefix/실패 호출의 작업이
비영일 수 있음을 뜻한다. 부분 성공 결과를 반환하지 않고 재시도·복구하지 않는다.
예상하지 못한 예외는 그대로 전파한다.

정상 직접 constructor와 dataclasses.replace는 전체 사전 검증·계산을 다시 실행한다.
derived fields는 constructor에서 주입할 수 없다. row/difference는 API 소유 결과용이며
임의 외부 record validator가 아니다. frozen/slotted는 적대적 Python sandbox가 아니다.
계산된 합성 chain은 true지만 first_frame_transition_checked/prehistory_checked/
source_identity_reauthenticated/V4/F61/actual activation 허용은 모두 false다.
파일 I/O·캐시·stream/checkpoint/실제 source bridge·차량 qualification을 추가하지 않는다.

실제 r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED=6000,Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED,F19=LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY=NOT_PROVEN,
F70UH/F70V/F71·실차 활성화 NOT_ALLOWED를 유지한다. 합성 rollout은 실제 native replay가 아니다.
