# CORE49 — 완료된 합성 기록의 명시적 전이 진단

CORE46은 입력 호환성만 검사하며 모델을 실행하지 않는다. 이 별도 API는 호출자가
명시적으로 요청한 경우에만 완료된 합성 기록 전체를 다시 검사한 뒤 기존 CORE7의
모든 인접 전이 진단을 실행한다. 새로운 계산기·계산식·결과 schema·CLI는 만들지 않는다.

## 개발 tree에서 사용

`tools/cyberlateral_dev` 디렉터리에서 import를 확인한다. 설치 wheel의 새 API가 아니다.

```bash
PYTHONPATH=src .venv/bin/python -B -c 'from integration_tools.offline_recording_diagnostics import check_recorded_synthetic_sequence; print("CORE49_IMPORT_OK")'
```

아래의 finished와 contexts는 호출자가 이미 명시적으로 만든 합성 선언이다.
파일/차량 데이터에서 자동으로 읽거나,누락 metadata를 추정하지 않는다.

```python
from integration_tools.offline_recording_diagnostics import check_recorded_synthetic_sequence

# finished: FinishedSyntheticRecordingV1, contexts: exact tuple[SyntheticModelContextV1, ...]
result = check_recorded_synthetic_sequence(finished, contexts)
assert result.checked_transition_count == len(finished.records) - 1
assert result.actual_activation_allowed is False
```

호출 자체가 별도의 명시적 오프라인 연산이다. 기존 recording/CORE46 receipt의 false
권한을 true로 바꾸거나,그 receipt를 실행 capability로 해석하지 않는다. receipt를
첫 인자로 주면 거절한다. 원래 recording과 contexts를 매번 새로 검증한다.

## 순서·결과·오류

1. CORE46 preflight_recording_input으로 recording metadata/전체 records/인접 링크/
   exact contexts/모든 입력/model-index 순서를 검사한다. 2..128개 기록만 허용한다.
2. 모두 통과하면 checked records/contexts로 기존 CORE7 check_synthetic_sequence를
   호출한다. CORE7은 자체 사전검증도 수행하며 입력 규칙을 변경하지 않는다.
3. 기존 SyntheticSequenceCheckV1을 그대로 반환한다. contract_id는 CORE7이고 새
   CORE49 결과나 성공 receipt를 만들지 않는다. MATCH/DIFFERENT와 모든 차이 위치,
   declared-state feed,원래 객체 identity를 그대로 보존한다.

N개 기록의 정상 호출은 정확히 N-1개 합성 모델 step을 실행한다. model simulate나
별도 reference 실행은 추가하지 않는다. 반복 numeric validation은 비영이며 집계하지 않는다.
늦은 입력 오류는 호환 prefix도 실행하지 않고 CORE46 오류를 그대로 전파한다.
RecordingPreflightError 및 모델 단계의 SequenceCheckError/예상 밖 예외를 새 코드로
덮지 않는다. 예컨대 세 번째 모델 호출의 domain 실패는 기존
SEQUENCE_TRANSITION:2:TRANSITION_MODEL_FAILURE가 된다.

모델 단계가 나중에 실패하면 앞선 합성 작업은 이미 수행됐을 수 있다. 성공 prefix나
부분 성공 결과는 반환하지 않지만 계산을 되돌리거나 실패 작업량0이라고 주장하지 않는다.

## 비교의 한계

선언된 current entry를 각 호출에 그대로 사용한다. 앞선 computed state로 바꿔 넣지
않으며 saved 결과를 고치지 않는다. 이른 DIFFERENT 뒤의 전이도 계속 검사한다.
이는 CORE27의 computed-state rollout이나 실제 native replay가 아니다.

MATCH는 인접 current saved state/counter 비교만 통과했다는 뜻이다. 첫 anchor 전이,
prehistory,전체 trace/output,실제 source 소비·원본 인증·차량 성능을 증명하지 않는다.
source_identity_reauthenticated/v4_payload_allowed/f61_input_allowed/
actual_activation_allowed/first_frame_transition_checked/prehistory_checked는 false다.

raw binary32의 signed zero/subnormal·int64 시각·live/replay label·별도 model index를
보존한다. 시각은 순서만 검사하며 dt/seconds/정확10ms/T2/r이나 timestamp 기반 index를
계산하지 않는다. import와 기존 recording/preflight 생성은 이 실행 함수를 자동 호출하지 않는다.
협력적 단일 스레드 API이며 악성 Python 변조·동시 mutation의 보안 경계나 atomic capture가 아니다.

## 검증과 유지 제한

```bash
.venv/bin/python -B -m unittest discover -s project -p 'test_offline_recording_diagnostics.py' -v
.venv/bin/python -B dev.py verify --output /absolute/NEW-output
```

실제 Controller/Runtime/CAN/F61/차량 input·capture·dt/r/설치·배포는0이다.
합성 모델 작업은 위에 명시한 대로 비영이고 전체 DEV gate도 별도의 합성/reference 작업을 수행한다.
실제 r/T2/vehicle scale=null,R_BUDGET=UNRESOLVED,STATIC_EVIDENCE_GATE=FAIL,
SOURCE_SCHEMA_UNQUALIFIED=6000,Candidate/Runtime=NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,
actual activation/F70UH/F70V/F71 NOT_ALLOWED 유지.
