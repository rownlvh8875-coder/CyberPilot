# CORE41 — 오프라인 합성 호출 기록기

`integration_tools.offline_call_recorder`는 이미 materialize한 합성 요청과 완료
snapshot을 메모리에서 모으는 개발용 API다. 실제 Controller를 감싸거나 source
객체/getter를 읽는 수집기가 아니다. 기존 CORE3/4 carrier·검증을 재사용하고
call 시작/완료/중단·개수 상한과 정확한 JSON 보존을 추가한다.

## 바로 확인하기

component 폴더에서 기존 Python 환경으로 실행한다.

```bash
.venv/bin/python -I -B tools/offline_call_recorder_demo.py
```

다른 cwd에서도 interpreter와 script를 절대 경로로 지정할 수 있다. 출력은 고정
합성 예제 2호출의 canonical JSON 한 줄뿐이다. 외부 input/source/log/vehicle/r/period/
runtime/output 경로 인자는 없고 알 수 없는 인자는 exit2로 거절한다. 모델이나 원본
helper를 호출하지 않으며 파일·원격 저장소를 쓰지 않는다.

예제의 요청 `80000000`(negative zero), `00000001`(positive subnormal)은 MSB-first
binary32 word다. sequence7/8, timestamp -9/-8, scale16과 state12/-2/4 등은 새로
작성한 허구의 합성 값이다. 실제 scale·T2·r·차량 한계·limiter 산술 결과가 아니다.

## API와 완료 경계

```python
from integration_tools.offline_call_recorder import SyntheticCallRecorderV1
from integration_tools.offline_recording_codec import decode_recording, encode_recording

# previous/current는 CORE4의 명시적 counterfactual frame이다.
recorder = SyntheticCallRecorderV1(capacity=2)
recorder.begin(previous.request)
recorder.complete(previous)
recorder.begin(current.request)
recorder.complete(current)
finished = recorder.finish()
raw = encode_recording(finished)
decoded = decode_recording(raw)
```

`begin`에는 CORE3 요청, `complete`에는 같은 요청을 포함한 CORE4 완료 frame을 명시한다.
complete의 entry state와 settings는 **호출자 선언으로 그때 제공된 값**이다. begin에서
설정을 읽었다거나 소비 경계에서 독립 관측했다는 뜻이 아니다. request와 별도의
previous limited/gated state·saved state·counter·settings를 서로 바꿔 쓰지 않는다.

기록 수는 필수 exact built-in int capacity2..128로 제한된다. 원래 CORE3/4 bounded
subset·type·flag·scope/profile·context·인접 sequence·원래 timestamp 순서·reset/loss·
설정 및 saved→entry state/counter 연결을 검사한다. 사전 단일 frame 검사에는 같은
package의 CORE3/4 검증 helper를 재사용하되 기존 파일/예외 계약은 수정하지 않았다.
첫 호출도 검사하며 시각은 비교만 한다. dt·seconds·주기·r을 계산하지 않는다.
10ms 순서 검사를 통과해도 V4 exact-seconds subset이 해결된 것이 아니다.

finish는 pending 호출이 없고 완료 기록이 2개 이상일 때만 frozen tuple 결과를 반환한다.
다음은 성공 prefix를 내보내지 못한다.

- 중복 begin, begin 없는 complete, 시작 요청과 다른 완료 요청
- 잘못된 첫 요청/frame, context·순서·시각·reset·loss 또는 settings/state/counter 불일치
- pending 상태에서 finish, 완료 기록0/1개, capacity 초과

이런 검증 실패는 해당 기록기를 영구 FAILED로 만든다. 첫 오류는 고정 code이며 이후
호출은 RECORDER_FAILED다. abort는 영구 RECORDER_ABORTED, 성공 finish 뒤에는
RECORDER_CLOSED다. 재시도/resume/backfill/reset·오래된 기록 축출은 없다. 새 인스턴스는
새 선언 history이며 과거 손실을 복구하지 않는다. 결과 직접 생성자도 모든 record와
연결을 검증하고 권한 필드를 constructor 인자로 받을 수 없다.

이는 단일 thread의 cooperative Python 계약이다. 악의적 object 재구성·monkeypatch·
동시 변경을 막는 sandbox, 실제 source의 atomic snapshot·정확한 단일 read·무영향
계측이나 지연 상한을 제공하지 않는다. 실제 출력이 정상 산술 결과인지도 검증하지 않는다.

## 정확한 JSON 경계

`encode_recording`은 검증된 exact 결과 type만 내보낸다. `decode_recording`은
262144bytes 이하 exact bytes의 canonical UTF-8 JSON만 수용한다.

- sorted keys·compact separators·ensure_ascii=False·allow_nan=False·끝 newline1개
- request word는 소문자 hex8자리. 부호 있는 zero/subnormal을 numeric float로 바꾸지 않음
- sequence·sample_time_ns·reset/loss generation은 exact decimal **문자열**
- 나머지 bounded 정수는 JSON int, flag는 JSON bool
- duplicate key·비정규 표현·큰 입력·추가/누락 field·NaN·잘못된 UTF-8·actual scope·권한/Gate 변경은 거절
- decode는 typed carrier를 다시 검증하고 encode(decoded)가 원래 bytes와 정확히 같아야 함

decoder 오류는 입력을 노출하지 않는 RECORDER_SERIALIZATION이다. 이는 provenance
인증이 아니다. 실제 데이터를 SYNTHETIC으로 재라벨링하면 안 되며 label의 진위를
인증할 수 없다. CLI에는 임의 JSON을 받는 경로도 추가하지 않았다.

## 해결하지 않은 실제 수집 문제

실제 collector에는 별도로 source/build/CP/config epoch, 읽기·소비·쓰기 지점,
일관성·누락·reset/exception 처리, clock provenance, 실행 영향/버퍼/overflow·privacy
검증과 허용된 관측 범위가 필요하다. 이 도구를 차량에 설치하거나 hook로 연결하지 않는다.
표현 보존·transaction·링크 검증 PASS는 실제 호출 binding PASS가 아니다.

출력 source_identity_reauthenticated/model_input_allowed/v4_payload_allowed/
f61_input_allowed/actual_activation_allowed는 false다. R_BUDGET=UNRESOLVED,
Static Evidence Gate=FAIL, 실제 r/T2/vehicle scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, actual activation/F70UH/F70V/F71=NOT_ALLOWED를 유지한다.

## 검증

```bash
.venv/bin/python -B -m unittest discover -s project -p 'test_offline*' -v
.venv/bin/python -B dev.py verify --output /absolute/NEW-output
```

첫 명령은 기존 offline 테스트도 포함한다. 새 recorder/codec/demo 테스트와 기존 전체
DEV gate의 합성 모델/reference 작업을 구분하며, 후자는 NONZERO_NOT_AGGREGATED다.
새 기록 계층 자체는 모델/helper/F61·실제 dt/r 연산을 하지 않는다.
