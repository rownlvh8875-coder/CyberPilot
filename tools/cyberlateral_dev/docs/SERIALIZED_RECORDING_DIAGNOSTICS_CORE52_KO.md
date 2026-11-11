# CORE52 — canonical 합성 기록 bytes의 명시적 진단

CORE41 codec의 정확한 bytes를 기존 CORE49 진단에 연결한다. 새 파일 reader나
차량 로그 importer가 아니다. 개발 tree의 Python API이며 설치 wheel API는 아니다.

## 완전한 합성 예제

`tools/cyberlateral_dev`에서 다음을 실행한다. 모든 값은 명시적 합성 선언이다.
encode_recording의 결과를 사용하며,실제 차량 기록이나 추정한 문맥을 넣지 않는다.

```bash
PYTHONPATH=src .venv/bin/python -B - <<'PY'
from integration_tools.request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1
from integration_tools.limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
from integration_tools.offline_call_recorder import FinishedSyntheticRecordingV1
from integration_tools.offline_recording_codec import encode_recording
from integration_tools.offline_recording_diagnostics import check_serialized_synthetic_recording
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
raw = encode_recording(FinishedSyntheticRecordingV1(tuple(frames)))
contexts = (SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', 5, -4, 1.5, 85.0),)
result = check_serialized_synthetic_recording(raw, contexts)
print(result.status, result.synthetic_model_steps, result.checks[0].computed_next_state.previous_applied)
assert result.actual_activation_allowed is False
PY
```

예상 출력은`MATCH 1 2`다. 정확히1개의 기존 합성 모델 step을 실행한다.
첫 기록은 anchor이며 그 이전 전이는 검사하지 않는다. 표본 시각의 차이나 초/10ms,
T2/r은 계산하지 않고 model index5는 별도 선언값이다.

## 검증 순서와 오류

`check_serialized_synthetic_recording(raw: object, contexts: object)`는
`decode_recording(raw)` 후 기존`check_recorded_synthetic_sequence`를 호출한다.
exact bytes·1..262144bytes·canonical CORE41·2..128records만 허용한다.
str/bytearray/dict/path/receipt는 자동 변환하지 않는다. 문맥은 별도 exact tuple의
CORE5 객체이며 bytes에서 복원·추론하지 않는다. 모든 입력을 매 호출 재검증한다.

1. bytes의 canonical 형식·전체 records/링크·metadata/false 권한을 먼저 검사한다.
   손상·중복 key·비canonical JSON·권한 변조는 기존
   RecorderError의`RECORDER_SERIALIZATION`으로 거절한다. 문맥보다 우선한다.
2. CORE46이 모든 문맥·입력·연속 model index를 검사한다. 늦은 오류도 모델 prefix0이다.
3. 모두 통과한 N개 기록은 N-1개 합성 step을 수행하고 기존 CORE7 결과를 반환한다.
   모든 차이 위치를 보존하고 각 declared entry를 사용한다. repair/rollout은 아니다.

CORE46/CORE7 오류와 예상 밖 모델 예외를 새 코드로 덮지 않는다. 늦은 모델 실패는
앞선 비영 작업 후 발생할 수 있으며 부분 성공을 반환하지 않는다. zero-work 실패와
구분해야 한다. numeric validation도 비영이며 별도 집계하지 않는다.

canonical 일치는 소유 합성 표현의 일관성이지 실제 출처 인증이 아니다. MATCH도
first anchor/prehistory/전체 trace·output/native replay/실차 성능을 인증하지 않는다.
raw signed zero/subnormal·int64 ns·선언 clock label을 보존하지만 실제 clock authority는
추가하지 않는다. 협력적 단일 스레드 API이며 적대적 Python/동시 변조의 보안 경계가 아니다.

실제 Controller/Runtime/CAN/F61/차량 input·capture·dt/r/설치·배포0 유지.
실제 r/T2/vehicle scale=null,R_BUDGET=UNRESOLVED,STATIC_EVIDENCE_GATE=FAIL,
SOURCE_SCHEMA_UNQUALIFIED=6000,Candidate/Runtime=NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,
actual activation/F70UH/F70V/F71 NOT_ALLOWED 유지.
