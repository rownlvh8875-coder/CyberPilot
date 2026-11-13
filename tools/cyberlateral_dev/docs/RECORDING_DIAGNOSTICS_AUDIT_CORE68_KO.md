# CORE68 — 원래 합성 입력으로 저장 진단 재계산·대조

CORE66 조회는 저장된 관계를 확인한다. 이 명령은 공급된 완전 합성 입력을 현재
알고리즘으로 명시적으로 다시 계산하고, 저장된 전체 CORE61 진단과 대조한다.
같은 알고리즘의 재현 검사이며 독립 수치 oracle·원본 출처·실차 인증은 아니다.

## 실행

`tools/cyberlateral_dev`에서 [CORE61 예제](RECORDING_INPUT_CLI_CORE61_KO.md)의
첫 Python block으로 새 외부 폴더에 합성 입력을 생성하고,
[CORE64 저장 명령](RECORDING_INPUT_WORKFLOW_CORE64_KO.md)으로 `saved`를 준비한다.
그 뒤 실행한다. 이 명령의 `--run`은 **새 합성 모델 실행**을 명시한다.

```bash
core68_input_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/INPUT.json" | cut -d ' ' -f 1)
core68_diagnostics_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/saved/DIAGNOSTICS.json" | cut -d ' ' -f 1)
.venv/bin/python -B tools/recording_diagnostics_audit.py --run \
  --input-file "$CORE61_EXAMPLE_DIR/INPUT.json" --expected-input-sha256 "$core68_input_sha" \
  --diagnostics-root "$CORE61_EXAMPLE_DIR/saved" --expected-diagnostics-sha256 "$core68_diagnostics_sha"
```

두 SHA는 서로 다른 파일의 SHA다. 위 직접 계산은 사용 예제이며, 실제 전달 시
신뢰할 별도 경로로 확보한 expected SHA와 대조해야 한다. 파일과 SHA를 함께
바꾼 조작의 원래 출처까지 인증하지는 않는다.

문서의2frame 예제는 `audit_status=REPRODUCED`, exit0,
`new_synthetic_model_steps=1`, `new_reference_steps=0`이다.
원본 입력과 저장 파일은 변경하지 않는다. 결과 JSON은 stdout으로만 출력한다.

## 결과 해석

| 검사 결과 | Exit | 의미 |
| --- | --- | --- |
| REPRODUCED | 0 | 현재 알고리즘이 같은 입력에서 저장된 진단 전체를 재현함 |
| DIFFERENT | 1 | 유효한 저장 진단과 새 진단의 header 또는 row가 다름 |
| 고정 오류 code | 2 | 무결성·입력 의미·사용법·실행·출력 오류; 성공 결과 아님 |

`saved_diagnostic_status`와 `recomputed_diagnostic_status`는 각각 기존 진단의
MATCH/DIFFERENT다. 저장된 진단 자체가 DIFFERENT라도 정확히 재현되면 **audit는
REPRODUCED/exit0**이다. audit 성공을 합성 진단 MATCH로 바꾸어 해석하지 않는다.

양쪽 전체 진단을 `stored_record`와 `recomputed_record`에 보존하고,
`differing_header_fields`와 `differing_transition_indices`에 차이 위치를 남긴다.
누락 row도 차이에 포함하며, 저장된 선언을 계산 결과로 고치지 않는다.
`recorded_model_steps`는 과거 저장 작업량, `new_synthetic_model_steps`는 이번
실행의N-1step이다. 전체 unit/gate의 작업량과는 별개다.

## 처리 순서와 경계

두 SHA 문법→CORE66 저장 두 파일 단일 캡처·검증→입력 SHA 선언 대조→CORE61 입력
단일 캡처·실제 SHA와 크기 대조→전체 입력 preflight→현재 합성 모델N-1step→전체
진단 대조 순서다. SHA/크기·형식·뒤쪽 문맥의 의미 오류도 모델 prefix0으로 거절한다.
기존 regular-file·symlink·크기 제한을 그대로 사용한다. 캡처 후 경로를 다시 읽지
않으므로 이후 경로 변경은 캡처한 bytes를 바꾸지 않는다. atomic snapshot이나
악의적 동시 경로 교체 방어를 보장하는 것은 아니다.

필수 flag는 각각1회다. `--run` 생략·축약·중복·잘못된 SHA·r/dt/context override는
project import나 모델 실행 전에 거절한다. 도움말도 모델을 실행하지 않는다.
전체 출력은2097152bytes 이하로 직렬화 후 내보낸다. 양의 short write는 끝까지
처리하지만 출력 실패 시 audit를 재실행하거나 prefix를 지우지 않는다. exit2의
stdout은 유효한 결과로 사용하지 않는다. 늦은 실행/출력 오류에는 이미 비영 합성
작업이 있을 수 있어 `DIAGNOSTICS_AUDIT_FAILED_WORK_MAY_BE_NONZERO`로 구분한다.

`arithmetic_recomputed=True`, `supplied_input_bytes_verified=True`는 이번에
공급한 합성 bytes와 현재 알고리즘에 한정한다. independent_numerical_oracle,
source_identity_reauthenticated, first_frame_transition_checked, prehistory_checked,
v4_payload_allowed, f61_input_allowed, actual_activation_allowed는 모두False다.
첫 anchor 이전 이력·실제 소비 설정·source/build·물리 응답의 검증은 추가하지 않는다.
CORE61/64/66·public wheel·모델 수식·선언 entry feed는 변경하지 않는다.

Linux/Python3.12 개발 tree 명령이며 설치 wheel의 새 entry가 아니다.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
F70UH/F70V/F71 및 실차 활성화=NOT_ALLOWED 유지.
실제 input/capture/Controller/Runtime/CAN/F61/actualdt/r/install/deploy=0이다.
