# CORE46 — 완료된 합성 기록의 입력 사전검증

CORE41 기록은 요청·설정·상태를 보존하지만 driver·angle·이전 정수 요청·model index를
포함하지 않는다. 이 API는 **그 추가 문맥을 명시적으로 따로 받아** 기존 CORE5와
호환되는지만 확인한다. 기록을 모델/F61에 실행시키는 bridge나 실제 수집기가 아니다.
기존 CORE3~7/CORE41·모델·wheel·fixture·계산식은 변경하지 않는다.

## 사용 경계

```python
from integration_tools.offline_recording_preflight import preflight_recording_input

# finished: CORE41의 FinishedSyntheticRecordingV1
# contexts: 호출자가 별도 선언한 SyntheticModelContextV1의 exact tuple
receipt = preflight_recording_input(finished, contexts)
assert receipt.status == 'INPUTS_COMPATIBLE'
assert receipt.model_input_allowed is False
```

finished는 exact 결과 class만 허용한다. bytes/dict/외부 객체를 자동 decode하지 않는다.
직접 JSON을 만들지 말고,기존 CORE41 codec이 필요한 경우 그 명시적 API를 별도 사용한다.
codec 수용이나 SYNTHETIC label도 원본 출처 인증은 아니다.

record 수는 기존대로2..128이다. contexts는 exact tuple이고 길이는 records-1이다.
각 context의 scope/model_index/previous_integer_request/current_driver/current_angle_deg는
모두 필수이며,현재 CORE5 exact type·범위·finite/dyadic 규칙을 그대로 재사용한다.
값 누락·추정·coercion·fallback은 없다. model index는 capture sequence나 timestamp에서
만들지 않는다. 이전 정수 요청을 previous limited/saved 상태와 바꿔 쓰지 않는다.

## 검사 순서

1. exact 결과 class를 생성 단계에서 확인한다. subclass의 instance getter를 읽지 않는다.
2. CORE41 전체 기록을 재검증한다. 고정 metadata/권한·요청·설정·state/counter link·시각 순서 포함이다.
3. contexts exact tuple과 records-1 개수를 검사한다. foreign container를 순회하지 않는다.
4. 모든 인접 pair에 CORE5 prepare_model_input을 적용한다. 나중 context의 오류도 검사한다.
5. 모든 입력이 통과한 뒤 context model_index의 연속성을 확인한다.
6. 성공한 경우에만 record_count/validated_transition_count를 파생한다.

예:4frames와3contexts면 count4/3이다. 문맥1의 index가 건너뛰더라도 마지막 문맥의
driver가 잘못됐다면 먼저 그 입력 오류가 보고된다. 부분 성공 prefix를 반환하지 않는다.
일부 양자화/validation은 이미 수행됐을 수 있으나 model step은 실행하지 않는다.

## 오류

RecordingPreflightError.code와 메시지는 동일한 고정 code다.

- RECORDING_PREFLIGHT_TYPE: 결과 subclass.
- RECORDING_PREFLIGHT_RECORDING:&lt;CORE41 code&gt;: 기록 재검증 오류.
- RECORDING_PREFLIGHT_CONTEXT_CONTAINER: contexts가 exact tuple이 아님.
- RECORDING_PREFLIGHT_CONTEXT_COUNT: 필요한 context 개수와 다름.
- RECORDING_PREFLIGHT_INPUT:i:&lt;CORE5 code&gt;: 0부터 시작하는 전이 i의 입력 오류.
- RECORDING_PREFLIGHT_MODEL_ORDER:i: context i의 model index가 직전+1이 아님.

필수 인자 누락·새 정책/권한 인자의 추가는 일반 Python TypeError다.
알려진 domain 오류는 원시 입력을 문구에 넣지 않고 감싼다. 예기치 못한 의존성 예외는
그대로 전파하며,임의 호환 판정이나 성공 결과로 바꾸지 않는다.

## 호환 판정과 계산·권한의 차이

결과는 frozen/slotted SyntheticRecordingInputPreflightV1이다. recording/contexts는
원래 객체를 보존하고 직접 생성·dataclasses.replace도 재검증한다. derived count나
고정 claim/권한은 생성자에 넣을 수 없다. prepared model input/state를 결과로 내보내지 않는다.

INPUTS_COMPATIBLE은 **선언 입력의 현재 합성 모델 호환성**이다. 예를 들어 선언 saved10과
다음 entry10이 연결돼 있으면 보존하며,계산 saved2로 고치지 않는다. 저장 출력의 산술
일치·첫 anchor 전이·prehistory·전체 projection/trace·원래 source 소비를 검증한 것이 아니다.

new_synthetic_model_steps=0,new_reference_steps=0이다. 다만 binary32 decode와
이전 요청 양자화 검증은 수행하므로 numeric_validation_work=NONZERO_NOT_AGGREGATED다.
전체 DEV gate는 기존 합성 모델/reference를 실제 실행하므로 전체 작업0이라고 표현하지 않는다.

source_identity_reauthenticated/model_input_allowed/v4_payload_allowed/f61_input_allowed/
actual_activation_allowed/first_frame_transition_checked/prehistory_checked는 모두 false다.
CORE5의 내부 입력 객체를 잠시 만들었다는 사실이 이 결과에 실행 권한을 부여하지 않는다.

raw signed zero/subnormal·시각 정수·live/replay clock 선언을 보존한다.
time_semantics=ORDER_ONLY_NO_DELTA_OR_PERIOD이며 dt/seconds/정확10ms/T2/r은 계산하지 않는다.
single-thread cooperative API이며 malicious Python 변조·동시 mutation을 막는 보안 경계나
실제 source의 atomic capture·일관성·단일 read·물리 제어 주기 보장이 아니다.

## 검증과 후속

```bash
.venv/bin/python -B -m unittest discover -s project -p 'test_offline_recording_preflight.py' -v
.venv/bin/python -B dev.py verify --output /absolute/NEW-output
```

추가 CLI/외부 파일 reader·실제 수집·모델 실행 workflow는 이 단계에 없다.
후속 실행 기능도 별도의 명시적 범위와 검증이 필요하며 이 receipt만으로 열리지 않는다.

실제 차량·Controller·Runtime·CAN·F61·실제 dt/r 실행0이다.
실제 r/T2/vehicle scale=null,R_BUDGET=UNRESOLVED,Static Evidence Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED=6000,Candidate/Runtime=NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,actual activation/F70UH/V/F71 NOT_ALLOWED 유지.
