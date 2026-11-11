# CORE58 — 저장된 완전 합성 입력 묶음의 명시적 진단

CORE55 canonical 입력 bytes에 들어 있는 기록과 문맥을 함께 복원해 기존
CORE49/CORE7 진단에 전달한다. 사용자가 별도 문맥을 다시 짝지을 필요가 없다.
`check_serialized_recording_input(raw)` 호출 자체가 명시적 합성 진단 요청이다.
단순 codec 복원과 달리 유효한 N개 기록에 N-1모델 step을 실행한다.

## 완전한 두 기록 예제

`tools/cyberlateral_dev`에서 실행한다. 모든 값은 합성 선언이며 실제 차량 데이터가 아니다.

```bash
PYTHONPATH=src .venv/bin/python -B - <<'PY'
from integration_tools.request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1
from integration_tools.limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
from integration_tools.offline_call_recorder import FinishedSyntheticRecordingV1
from integration_tools.offline_recording_input_codec import encode_recording_input
from integration_tools.offline_recording_diagnostics import check_serialized_recording_input
from integration_tools.synthetic_model_input import SyntheticModelContextV1

context = SyntheticRequestContextV1(
    1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY', 'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1',
    'demo-capture', 'demo-controller', 'demo-config', 'DECLARED_LIVE_MONOTONIC_NS',
    'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
settings = SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
frames = []
for sequence, time_ns, word, entry, saved, counter, next_counter in (
    (7, -9, 'be800000', 7, -2, 3, 4),
    (8, -8, '3f000000', -2, 2, 4, 5),
):
    request = SyntheticRequestSnapshotV1(context, sequence, time_ns, bytes.fromhex(word), True, False, False)
    frames.append(SyntheticLimiterSnapshotV1(
        request, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
        'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', entry, saved, counter, next_counter, True))
recording = FinishedSyntheticRecordingV1(tuple(frames))
contexts = (SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', 5, -4, 1.5, 85.0),)
raw = encode_recording_input(recording, contexts)
result = check_serialized_recording_input(raw)
assert result.actual_activation_allowed is False
assert result.f61_input_allowed is False
print(result.status, result.synthetic_model_steps, len(result.frames))
PY
```

예상 출력:`MATCH 1 2`. 모델1step은 위 명시적 진단의 작업이며 codec 자동 실행이 아니다.

## 입력 형태를 구분한다

| 진단 API | 입력 | 유효한 N기록의 실행 |
|---|---|---|
| CORE49 check_recorded_synthetic_sequence | recording 객체+명시 contexts | N-1step |
| CORE52 check_serialized_synthetic_recording | CORE41 recording bytes+명시 contexts | N-1step |
| CORE58 check_serialized_recording_input | CORE55 완전 입력 bytes1개 | N-1step |

CORE55 encode/decode는 여전히 모델/reference0step이다. 새 API는 CORE41-only bytes,
객체,receipt,문자열을 입력 묶음으로 자동 추측하거나 변환하지 않는다. contexts,
rate_budget_per_s,dt,T2,actual_scale 같은 override 인자나 기본 raw 입력도 없다.
개발 tree API이며 파일 reader,CLI,result 저장,설치 wheel export를 추가하지 않았다.

## 검증·진단의 의미

- 먼저 변경하지 않은 CORE55 decoder가 exact bytes·1..1048576bytes·canonical
  JSON/header·CORE41 내부 기록·문맥 wire·CORE46 전체 호환성을 검증한다.
  기록2..128개,문맥1..127개와 기존 범위·dyadic·역할·순서·pair 규칙을 유지한다.
- 구조 오류는 기존 RecordingInputCodecError/code,의미 오류는 기존
  RecordingPreflightError/code다. late invalid 입력도 모델 prefix0으로 거절한다.
- 검증 후 기존 CORE49/CORE7이 모든 인접 전이를 진단한다. DIFFERENT가 있어도
  뒤의 검사를 생략하지 않고,각 선언 entry state를 사용한다. 계산된 상태로
  rollout하거나 선언을 고치지 않는다. binary32 words,int64 ns,clock label,
  auxiliary float의 정확한 표현은 보존하며 실제 dt나 period를 계산하지 않는다.
- 실행 중 늦게 실패하면 이미 일부 모델 작업이 끝났을 수 있다. 기존 fixed
  transition error나 예상 밖 exception identity를 유지하고 부분 성공·재시도·
  raw ValueError 누출로 바꾸지 않는다. 입력 거절의0step과 실행 실패를 혼동하지 않는다.
- 결과는 기존 CORE7_COUNTERFACTUAL_DECLARED_SEQUENCE_V1이며 새 schema가 아니다.
  MATCH는 선언된 인접 전이 일치일 뿐 source 인증/첫 anchor/prehistory/native
  replay/실차 적합성 증명이 아니다. 입력 codec이나 호환성 receipt 권한을 승격하지 않는다.

협력적 단일 스레드 API이며 hostile/concurrent mutation이나 atomic capture 보안
경계가 아니다. numeric validation은 비영/미집계이고 명시적 합성 진단의 모델 작업은
N-1step이다. 실제input/capture/Controller/Runtime/CAN/F61/actualdt/r/install/deploy0,
실제r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,
actual activation/F70UH/F70V/F71 NOT_ALLOWED 유지.
