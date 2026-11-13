# CORE69 — 선언 합성 진단의 별도 참조 계산 대조

CORE68은 현재 공개 모델로 저장 진단을 재현한다. CORE69는 별도 worker에서 기존
integer-bit 양자화 oracle과 SHA가 고정된 원본 limiter/fault helper를 사용한다.
공개 모델과 같은 산술 오류를 공유하는 경우를 찾기 위한 개발 검사다. 실제 차량,
원본 producer/build 인증, 전체 제어기 또는 전체 입력 영역의 정확성 증명은 아니다.

## 어떤 검사를 사용할까

| 명령 | 새 공개 모델 step | 새 참조 step | 확인 범위 |
| --- | ---: | ---: | --- |
| CORE66 inspect | 0 | 0 | 저장된 관계·무결성 |
| CORE68 audit --run | N-1 | 0 | 현재 알고리즘의 진단 재현 |
| CORE69 reference --run | 0 | N-1 | 별도 선택-source 산술의 next-state 대조 |

N은 완전 입력의2..128frame이다. reference helper·양자화·검증 산술은 비영이며
모델0을 전체 계산0으로 해석하지 않는다. CORE69도 입력 admission은 기존 CORE55/
CORE46/CORE5를 공유한다. parent가 모델과 현재 quantizer를 import할 수 있고,
admission의 버그로 적법 입력을 거절할 가능성은 별도로 남는다.

## 실행

`tools/cyberlateral_dev`에서 [CORE61 입력 생성](RECORDING_INPUT_CLI_CORE61_KO.md)의
첫 Python block과 [CORE64 저장](RECORDING_INPUT_WORKFLOW_CORE64_KO.md)을 실행해
새 외부 폴더의 INPUT.json과 saved 두 파일을 준비한다. 이어서 실행한다.

```bash
core69_input_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/INPUT.json" | cut -d ' ' -f 1)
core69_diagnostics_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/saved/DIAGNOSTICS.json" | cut -d ' ' -f 1)
.venv/bin/python -B tools/recording_diagnostics_reference.py --run \
  --input-file "$CORE61_EXAMPLE_DIR/INPUT.json" --expected-input-sha256 "$core69_input_sha" \
  --diagnostics-root "$CORE61_EXAMPLE_DIR/saved" --expected-diagnostics-sha256 "$core69_diagnostics_sha"
```

위 예제는 REFERENCE_MATCH/exit0, 새 모델0·참조1step이다. helper compile1회/
선택 정의2개·limiter1회·fault1회·clip2회를 구분해 보고한다. 전체 Controller나
원래 helper 모듈을 실행하는 것이 아니라 검산된 두 함수 정의만 제한적으로 사용한다.
직접 SHA를 계산하는 예제는 사용법이며 원래 출처 인증이 아니다. 전달받는 expected
SHA는 신뢰할 경로로 확보해야 한다.

## 상태와 작업량

- audit_status=REFERENCE_MATCH/exit0: 저장 진단이 참조 projection과 일치한다.
- audit_status=REFERENCE_DIFFERENT/exit1: 유효한 자료 사이의 차이를 찾았다.
- 오류 exit2: 무결성·입력·source·worker·사용법·출력 오류이며 성공 결과가 아니다.

saved_diagnostic_status와 reference_diagnostic_status는 진단 MATCH/DIFFERENT다.
진단 DIFFERENT가 그대로 재현돼도 reference audit는 MATCH일 수 있다. 저장된
계산 결과로 다음 상태를 고치지 않고 각 전이의 **선언 entry state**를 사용한다.
R38의 computed-state rollout과 다른 문맥이다.

stored_record를 보존하고 reference_projection과 전체 header/row를 exact canonical
JSON으로 대조한다. differing_header_fields와 differing_transition_indices는 누락/
추가 row도 포함한다. 허용오차·자동 repair·baseline 갱신은 없다. 이 projection은
기존 CORE61 형식의 **대조 기대값**이며 새 producer 실행이나 F61 입력이 아니다.
그 안의 new_synthetic_model_steps=N-1은 형식 대조용 값이다. 이번 실제 모델 작업은
top-level new_synthetic_model_steps=0,참조는 new_reference_steps=N-1로 읽는다.

참조가 독립적으로 계산하는 범위는 양자화된 요청과 적용값·counter·index의
next-state다. 전체 LateralOutput/trace·Controller 분기·실제 source/state/time binding을
대조했다고 확대하지 않는다. first anchor와 prehistory도 미검증이다.

## 실행 경계

두 SHA 문법→CORE66 단일 캡처/검산→입력 identity/단일 캡처/전체 admission→
명시한 source identity→격리 worker→source 변화 검사→closed worker 결과 검산→
대조 순서다. 뒤쪽 입력 의미 오류도 worker 전에 거절한다. parent의 model.step은
실행하지 않는다. worker는 공개 모델/validator·차량 모듈·F61 import를 막는다.

런타임은 Linux/CPython3.12.13/binary64/numpy2.5.3이다. worker는 -I -B와60초
timeout,stdin/수용 stdout1048576bytes 제한을 사용한다. stdout은 캡처 후 크기를
검사하므로 악의적인 임의 프로세스에 대한 메모리 sandbox가 아니다. 신뢰하는
고정 worker와 기존 source를 사용한다. helper의 정확한 SHA/크기/심볼 검사도 유지한다.
source identity는 명시한 코드 bytes의 관찰이며 실제 배포·build·서명 인증이 아니다.

필수 flag는 각각1회다. --run 생략·축약·중복·잘못된 SHA·r/dt/context override는
project import 전에 거절한다. stdout 전체를2097152bytes 이하로 직렬화한 뒤 쓴다.
positive short write는 끝까지 처리하며 오류 시 참조를 재실행하지 않는다. 늦은
source/worker/출력 오류에는 이미 비영 참조 작업이 있을 수 있다. exit2의 stdout
prefix를 성공 영수증으로 사용하지 않는다. 원본/저장 파일과 cache/temp/result 파일을
쓰지 않고 sys.path/bytecode 설정을 복원한다. atomic snapshot·hostile path race·
나중 파일 내용은 보증하지 않는다. 설치 wheel의 새 entry가 아니다.

기존 모델·wheel·CORE61/64/66/68·원본 helper·F61 계약은 불변이다.
R_BUDGET=UNRESOLVED,Static Gate=FAIL,실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000,Candidate/Runtime=NO_GO,
F70UH/F70V/F71·실차 활성화=NOT_ALLOWED 유지.
실제 input/capture/Controller/Runtime/CAN/F61/actualdt/r/install/deploy=0이다.
