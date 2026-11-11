# CORE55 — 합성 기록과 명시적 문맥의 canonical 입력 묶음

CORE52는 recording bytes와 Python 문맥 tuple을 따로 받는다. 이 codec은 두 선언을
하나의 bytes로 보존·복원한다. 원래 CORE41 recording encoding과 CORE46 의미 검증은
바꾸지 않는다. 파일·차량 로그 reader,CLI,설치 wheel API가 아닌 개발 tree 함수다.

## 완전한 두 기록 예제

`tools/cyberlateral_dev` 디렉터리에서 실행한다. 모든 값은 합성 선언이고
저장·복원만 수행한다. 모델·reference step은0이다.

```bash
PYTHONPATH=src .venv/bin/python -B - <<'PY'
from integration_tools.request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1
from integration_tools.limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
from integration_tools.offline_call_recorder import FinishedSyntheticRecordingV1
from integration_tools.offline_recording_input_codec import encode_recording_input, decode_recording_input
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
receipt = decode_recording_input(raw)
assert receipt.model_input_allowed is False
assert receipt.actual_activation_allowed is False
assert encode_recording_input(receipt.recording, receipt.contexts) == raw
print(receipt.status, receipt.record_count, receipt.validated_transition_count)
PY
```

예상 출력:`INPUTS_COMPATIBLE 2 1`.
receipt는 기존 CORE46 사전검증 결과이며 실행 capability가 아니다. 합성 전이 진단이
필요하면 별도 명시적 호출을 해야 한다.

```python
from integration_tools.offline_recording_diagnostics import check_recorded_synthetic_sequence
result = check_recorded_synthetic_sequence(receipt.recording, receipt.contexts)
```

위 별도 호출은 N개 기록에 N-1합성 모델 step을 수행한다. codec의 작업량과 구분한다.
receipt 자체를 recording 인자로 넣는 것은 기존 exact-type 규칙에 따라 거절한다.

## 표현·검증·오류

- `encode_recording_input(recording, contexts) -> bytes`: CORE46 전체 사전검증 후 저장.
- `decode_recording_input(raw) -> SyntheticRecordingInputPreflightV1`: canonical
  구조 검사 후 CORE41 복원과 CORE46 전체 사전검증. 기존 receipt와 false 권한 유지.
- exact bytes·최대1048576bytes·UTF8·정렬된 key·compact JSON·마지막 newline1개다.
  recording2..128개,명시 문맥1..127개이며 문맥 수는 정확히 기록 수-1이어야 한다.
- `recording_json`은 CORE41 canonical UTF8 text 원문과 newline을 포함한다.
  raw binary32 word/int64 ns/clock 선언/정적 gate는 원래 codec 계약으로 보존한다.
- 문맥은 scope/model_index/previous_integer_request/current_driver_hex/
  current_angle_deg_hex의 정확한5field다. 부가 float는 finite canonical float.hex
  text32자 이내이며 음의0도 보존한다. 범위·dyadic·index·이전 요청·pair 검증은 CORE46/5다.
- outer metadata/false 권한과 shape/type은 정확히 일치해야 한다. 중복 key/pretty JSON/
  임의 숫자↔hex 변환/NaN/누락·extra field/권한·Gate 변조는 자동 보정하지 않는다.
- 구조 오류는 RecordingInputCodecError의 고정`RECORDING_INPUT_SERIALIZATION`이다.
  canonical 구조 검사 뒤 의미 검증 오류는 기존 RecordingPreflightError/code를 유지한다.
  encoder의 잘못된 선언도 기존 CORE46 code로 거절한다. 예상 밖 의존성 예외는 덮지 않는다.
- 매 호출 전체를 재검증하며 캐시·prefix 성공·문맥/time/index/state 추론은 없다.
  codec/import는 step/simulate/reference0이지만 numeric validation은 비영/미집계다.

canonical/INPUTS_COMPATIBLE은 source 인증이나 output 산술 MATCH가 아니다. 첫 anchor,
prehistory/전체 output/native replay를 검증하지 않는다. 협력적 단일 스레드 API이며
악성 Python/동시 mutation/atomic capture 보안 경계가 아니다. rate 정책·실제 단위
변환·dt·T2를 추가하지 않는다. 실제 Controller/Runtime/CAN/F61/input/capture/dt/r/
설치·배포0,실제 r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,
actual activation/F70UH/F70V/F71 NOT_ALLOWED 유지.
