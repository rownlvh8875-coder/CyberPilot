# CORE19 저장 합성 입력의 의미 사전 검증

`integration_tools.core_sequence_input_preflight.preflight_saved_sequence(input_path: Path) -> dict`
는 저장된 CORE8 고정3파일을 한 번 읽고 CORE3~5 입력 규칙을 다시 검사한다.
[CORE9 조회](CORE_SEQUENCE_INSPECT_CORE9_KO.md)의 checksum·schema·저장 관계 검증과
다르며, 기존 조회/비교/API/모델/wheel을 바꾸지 않는다. 실행 CLI나 범용 차량 reader가 아니다.

## 사용과 결과 구분

별도 [CORE20 CLI](CORE_SEQUENCE_INPUT_PREFLIGHT_CLI_CORE20_KO.md)는 아래 Python recipe
없이 같은 API receipt를 출력하며 현재 입력 판정을 exit0/1, 운영 오류를2로 구분한다.
이 API 자체와 그 규칙·반환 JSON은 변경하지 않았다.

기존 tools/cyberlateral_dev 전용 환경과 해당 디렉터리에서:

```bash
.venv/bin/python -I -B -c '
import sys
from pathlib import Path
sys.path[:0] = [str(Path.cwd()), str(Path.cwd() / "src")]
from integration_tools.core_sequence_input_preflight import preflight_saved_sequence
from integration_tools.scenario_output import canonical
sys.stdout.buffer.write(canonical(preflight_saved_sequence(Path(sys.argv[1]))))
' /absolute/saved-core8-case
```

입력은 INPUT.json/RESULTS.json/SHA256SUMS.txt 세 파일의 완전한 CORE8 case다.
ZIP·CORE17 root·partial portable subset은 직접 입력이 아니다. 모델의 **타입과 입력
검증/양자화 코드**는 import하지만 model.step·reference·생산자는 실행하지 않는다.
이 API는 import/cache 인프라를 관리하는 CLI가 아니므로 위 명령은 -I -B로 실행한다.

| 필드 | 의미 |
|---|---|
| preflight_status | 현재 입력 규칙에 INPUTS_COMPATIBLE 또는 INPUTS_REJECTED |
| rejection_code | 현재 의미 거절; 호환이면 null |
| validated_transition_count | CORE5를 성공한 prefix 길이; 전체 성공3 |
| saved_status / saved_rejection_code | 별도로 보존한 과거 기록의 판정/거절 |
| recorded_model_steps | 저장 기록의 과거 수치; 실행 사실 인증 아님 |
| captured_sha256 | 이번에 읽은3파일 raw bytes SHA |
| new_synthetic_model_steps / new_reference_steps | 이 사전 검증의 실행 수0 |
| numeric_validation_work | float 해석·양자화 검증은 NONZERO_NOT_AGGREGATED |

저장 MATCH라도 driver가0.1 같은 허용 subset 밖이면 INPUTS_REJECTED다.
저장 DIFFERENT는 입력이 호환될 수 있다. 저장 REJECTED label도 현재 검사 결과를
대신하지 않는다. 예전 late-invalid는 현재 SEQUENCE_INPUT:2:MODEL_DRIVER로 거절하고
validated_transition_count2를 반환한다. 이것은 모델 결과 재계산이 아니다.

## 검증 순서와 오류

1. CORE9를 한 번 호출한다. 기존65536/524288/512byte cap, canonical JSON, 중복 key/
   symlink/FIFO/extra 파일 거절, closed schema와 stored 관계 검증을 그대로 적용한다.
   model index 연속성도 여기서 먼저 검사한다.
2. captured record로 소유 CORE3/4 선언을 복원한다. 요청은 원래 binary32 word bytes다.
   두 auxiliary 값은 float.fromhex로 읽고 `.hex()` round trip이 원문과 exact해야 한다.
   overflow·underflow·비canonical zero alias는 INPUT_PREFLIGHT_FLOAT_ENCODING:i로
   거절한다. signed zero는 유지한다. 이 decoding 단계 거절의 validated count는0이다.
3. CORE5를 모든 인접 pair에 순서대로 적용한다. range/dyadic·previous request 양자화·
   active read·override·state/settings/context/시각 순서 규칙을 바꾸지 않는다.
   첫 실패는 SEQUENCE_INPUT:i:&lt;MODEL code&gt;, 성공한 prefix 수를 반환한다.

저장 capture/schema 오류는 `InputPreflightError.code`의
INPUT_PREFLIGHT_SAVED:&lt;기존 INSPECT code&gt; 예외다. 이 경우 의미 판정 receipt는 없다.
예상하지 못한 내부 오류도 전파하며 compatible/일반 input rejection으로 숨기지 않는다.
원문 path/입력값을 오류에 덧붙이지 않는다. 부분 prepared 객체나 constructor args는
내보내지 않는다. 파일을 수정·수리·추출하거나 기본 r/T2/scale을 만들지 않는다.

## 범위

CORE3는 int64 시각의 순서만 검사한다. 실제 dt·주기·F61 time projection이 아니므로
10ms를 F61 호환이라고 주장하거나 nominal 간격으로 대체하지 않는다.
compatible은 입력 검증이지 저장 명령의 산술 진실, anchor/prehistory, computed rollout,
V4 연결, 현재 source 인증, 과거 실행 사실 또는 차량 성능 검증이 아니다.
일관되게 다시 만든 위조 기록도 출처를 인증하지 않는다. 값의 synthetic label은 실제
차량 값을 재라벨링할 권한이 아니다. byte/layout/mode는 수정하지 않지만 atime, 적대적
경로 경쟁/alias, atomic snapshot, import hook과 악의적 Python 객체는 보장하지 않는다.

독립 사전 검증의 모델/reference/F61·actualr/dt·Controller/Runtime/CAN·차량 작업0.
전체 unit/gate 합성 fixture 실행은 NONZERO_NOT_AGGREGATED로 별개다.
실제 r/T2/scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
Candidate/Runtime=NO_GO, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED 유지.
