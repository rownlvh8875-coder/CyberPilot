# CORE7 — 선언 상태를 유지하는 연속 합성 전이 검사

계산 상태 자체를 이어가는 별도 합성 실험은
[CORE27 rollout](SYNTHETIC_SEQUENCE_ROLLOUT_CORE27_KO.md)을 사용한다.
CORE7의 선언 entry 기반 진단과 과거 결과는 그대로 유지한다.

`integration_tools.synthetic_sequence_check.check_synthetic_sequence(frames,contexts)`는
여러 호출의 인접 전이를 검사한다. [CORE5](SYNTHETIC_MODEL_INPUT_CORE5_KO.md)로
전체 입력을 사전 검증하고 [CORE6](SYNTHETIC_TRANSITION_CORE6_KO.md)로 각 현재 saved
명령/counter를 한 합성 step과 비교한다. 기존 모델·CORE3~6·동결 wheel은 바꾸지 않는다.

## 필수 입력과 처리 순서

frames는 CORE4 frame의 exact tuple, 길이2..4096이다. contexts는 CORE5 context의
exact tuple이며 길이는 frames-1이다. context i는 previous frame i/current frame i+1의
문맥이다. 첫 frame은 자기 전이를 계산하지 않은 anchor다. tuple subclass·list·generator·
빈 입력·단일 frame·잘못된 context 수는 거절한다. 기본 문맥이나 rate policy는 없다.

1. 모든 인접 pair를 CORE5로 사전 검증한다. 뒤쪽 요청/설정/상태/시각/문맥/flag/auxiliary
   오류도 public model step을 시작하기 전에 거절한다.
2. 모든 입력이 유효한 뒤 명시된 model_index가 연속인지 확인한다. model_index는 capture
   sequence나 timestamp에서 계산하지 않는다. epoch/reset 경계를 자동 연결하지 않는다.
3. 각 pair를 CORE6에 한 번 전달한다. CORE6도 다시 입력을 검증한다. DIFFERENT가 나와도
   이후 pair를 빠뜨리지 않고 검사한다.
4. 모든 결과가 MATCH일 때만 aggregate MATCH다. DIFFERENT가 하나라도 있으면 aggregate
   DIFFERENT이며 differing_transition_indices에 모든 차이 위치를 순서대로 보존한다.

여기서 위치 i는 **0부터 시작하는 전이 순번**이다. target frame 순번은 i+1이며, 원래
capture sequence/model index가 아니다. 결과 checked_transition_count와 합성 step 수는
완료된 경우 frames-1이다. 4,096frames는 4,095전이를 검사한다.

## 선언 기반 진단과 computed rollout의 차이

다음 호출에는 그 frame의 **선언된 entry 상태**를 사용한다. 앞 호출의 계산 결과로
선언값을 고쳐 넣지 않는다. 따라서 중간 차이가 나면 이후 결과는 선언된 입력에 대한
개별 진단이며, 계산 결과를 연속 feed한 corrected simulation이 아니다.

예: 첫 target의 entry-2는 계산 saved2를 만들지만 선언 saved10인 경우 첫 결과는
DIFFERENT다. 다음 frame의 선언 entry10을 사용하면 후속 computed 명령5를 얻을 수 있다.
계산값2로 entry를 바꿔 후속 결과를 다르게 만들지 않는다. 원래 frames와 contexts,
각 CORE6 결과 및 차이는 모두 보존한다.

모두 MATCH라면 제공된 anchor 이후의 인접 선언 상태 연결과 각 현재 두 상태값이
합성 입력에 일관됨을 뜻한다. 첫 anchor의 자기 전이·prehistory는 여전히 미검증이며
전체 output/projection/trace/steer-request, 실제 source 관측의 인증도 아니다.

## 오류와 작업량

`SequenceCheckError.code`:

- SEQUENCE_TYPE: 정확한 결과 class가 아님.
- SEQUENCE_CONTAINER: frames/contexts가 exact tuple이 아님.
- SEQUENCE_COUNT: frame 수 또는 context 수가 계약과 다름.
- SEQUENCE_INPUT:i:&lt;CORE5 code&gt;: 전체 입력 사전 검증 중 i번째 오류.
- SEQUENCE_MODEL_ORDER:i: context i의 model_index가 직전+1이 아님.
- SEQUENCE_TRANSITION:i:&lt;CORE6 code&gt;: 실제 i번째 전이 검사 중 오류.

사전 검증 실패는 public model step0이지만 요청 양자화/validation은 비영일 수 있다.
후반 모델 오류에는 이미 계산한 prefix/실패 중 일부 작업이 있을 수 있다. 이때 완료된
부분 sequence나 성공 결과를 내보내지 않으며 0회 작업이라고 주장하지 않는다.
기타 예상하지 못한 예외는 전파하고 MATCH/DIFFERENT로 바꾸지 않는다.

`SyntheticSequenceCheckV1(frames,contexts)`의 정상 직접 생성자와
`dataclasses.replace`도 전체 검증·계산을 다시 한다. derived checks/status/counts/차이
목록과 고정 claim을 생성자에서 주입할 수 없다. frozen/slotted cooperative 경계이며
악의적 Python 변조·동시성·serialization 인증 sandbox나 영속 registry는 아니다.

validation_claim은
`ADJACENT_DECLARED_CURRENT_TRANSITIONS_ONLY_NOT_COMPUTED_ROLLOUT`다.
first_frame_transition_checked/prehistory_checked/source_identity_reauthenticated와
V4/F61/실차 허용은 모두 false다. CLI/JSON reader·stream/checkpoint·자동 repair는 없다.

실제 r/T2/vehicle_scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71 및 실제 활성화=NOT_ALLOWED를 유지한다.
합성 계산은 비영이며 실제 차량·F61·Controller·Runtime·CAN·실제 r 계산은 0이다.
