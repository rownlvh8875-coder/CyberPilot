# CORE61 — 저장된 완전 합성 입력의 명시적 진단 CLI

CORE55 입력 묶음과 CORE58 진단을 연결하는 개발 tree 명령이다. Linux/WSL2의
Python3.12에서 사용한다. 파일과 SHA를 받되 실제 로그/차량 입력 reader가 아니다.
`--run`은 명시적 **합성 모델 실행**이며 실제 실행·설치 승인이 아니다.

## 완전한 합성 예제

`tools/cyberlateral_dev`에서 실행한다. 새 외부 폴더만 사용하고 기존 입력은 덮어쓰지 않는다.

```bash
export CORE61_EXAMPLE_DIR="$(mktemp -d /tmp/cyberpilot-core61-example-XXXXXX)"
```

다음 block은 입력을 생성하는 예제이지 CLI의 자동 fixture 선택이 아니다.

```bash
PYTHONPATH=src .venv/bin/python -B - <<'PY'
import hashlib
import os
from pathlib import Path

from integration_tools.request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1
from integration_tools.limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
from integration_tools.offline_call_recorder import FinishedSyntheticRecordingV1
from integration_tools.offline_recording_input_codec import encode_recording_input
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
path = Path(os.environ['CORE61_EXAMPLE_DIR']) / 'INPUT.json'
with path.open('xb') as stream:
    stream.write(raw)
print(hashlib.sha256(raw).hexdigest())
PY
```

위 block은 codec 입력 생성만 하므로 모델/reference step0이다. 이어서 명시적으로 실행한다.

```bash
core61_input_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/INPUT.json" | cut -d ' ' -f 1)
.venv/bin/python -B tools/recording_input_diagnostics.py --run \
  --input-file "$CORE61_EXAMPLE_DIR/INPUT.json" --expected-sha256 "$core61_input_sha"
```

예상 결과는 canonical JSON1개, exit0, `status=MATCH`, `frame_count=2`,
`checked_transition_count=1`, `new_synthetic_model_steps=1`이다. 유일한 행의
computed_next_state는 index6/previous_requested8/previous_applied2/angle_counter5다.
요청의 선언 timestamp -9/-8은 실제 경과 시간이나10ms 증거가 아니다.

## 입력·오류·출력 경계

- 각 flag는 정확히1회 필수다. 축약·중복·SHA 대문자/생략·context/rate/dt/출력
  override는 거절한다. 도움말과 잘못된 사용법은 project import·입력 open·모델0이다.
- SHA는 exact64소문자 hex를 path 접근 전에 검사한다. regular file1..1048576bytes,
  symlink/ancestor symlink·directory/FIFO 등은 거절한다. read-only fd1회 캡처하고
  실제 읽기도 cap+1로 제한한다. fd를 닫고 캡처 bytes의 SHA를 확인한 뒤 CORE58을1회 호출한다.
- 파일/SHA/codec/전체 의미 검증 오류는 모델 prefix0이다. 임의 JSON/CORE41-only
  기록을 자동 변환하지 않는다. 저장 후 path 변경은 이미 캡처한 bytes를 바꾸지 않는다.
  이는 atomic 파일 snapshot이나 hostile filesystem/프로세스 보안 경계가 아니다.
- 유효한 N기록은 N-1합성 step이다. DIFFERENT 뒤에도 모든 전이를 검사하며 계산된
  state로 다음 선언을 고치지 않는다. 결과에는 entry/computed/saved 상태와 모든
  차이를 담지만, 입력을 완전히 재생성하는 codec이나 독립 산술 oracle은 아니다.
- MATCH exit0, DIFFERENT exit1, 입력/사용법/실행/운영/출력 실패 exit2다.
  실패 시 성공 JSON을 만들지 않으며 stderr는 고정 code만 출력한다. 실행 중 늦게
  실패하면 이전 모델 작업이 있을 수 있다. 이를0으로 표현하거나 재시도하지 않는다.
- JSON 전체를 먼저 생성하고1048576bytes 이하인지 검사한 뒤 stdout에 쓴다.
  양의 short write는 끝까지 처리하고0/음수/오류는 중단한다. stdout 일부가 이미
  쓰인 뒤 실패한 prefix는 되돌릴 수 없으며 exit2출력은 유효한 결과가 아니다.
- CLI는 파일/캐시/temp를 생성하지 않는다. shell redirection으로 저장하는 경우
  저장 파일 관리와 실패 prefix 처리는 호출자 책임이다. no overwrite 저장 workflow를
  제공하는 명령으로 해석하지 않는다. source path/bytecode flag는 호출 종료 시 복원한다.

SHA는 캡처 bytes의 일치 확인일 뿐 원본 출처 인증이나 이후 path 내용의 증명이 아니다.
권한false·GATES를 유지하고 실제r/T2/scale을 만들지 않는다. 협력적 단일 스레드
개발 API이며 source/math/codec/wheel/dependency/차량 정책 변경은 없다.
이번 기능의 local 완료가 feature 게시/main CI/실차 승인을 뜻하지 않는다.

현재 R_BUDGET=UNRESOLVED,Static Gate=FAIL,실제r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/F70V/F71 NOT_ALLOWED.
실제input/capture/Controller/Runtime/CAN/F61/actualdt/r/install/deploy0.
전체 unit/gate의 합성/model/reference/numeric 작업은 비영/미집계다.
