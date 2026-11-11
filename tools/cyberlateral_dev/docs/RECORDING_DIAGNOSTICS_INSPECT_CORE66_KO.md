# CORE66 — 저장된 합성 진단의 읽기 전용 검사

CORE64가 저장한 `DIAGNOSTICS.json`과 `SHA256SUMS.txt`를 검사한다. 모델·reference·
원본 입력을 다시 실행하거나 읽지 않으며, 결과나 캐시·임시 파일을 쓰지 않는다.
이 명령은 실제 로그 reader나 차량 사용 승인이 아니다.

## 실행

CORE64 안내대로 입력을 생성하고 새 폴더에 진단 결과를 저장한 뒤 실행한다.
아래 `$CORE61_EXAMPLE_DIR/saved`는 [저장 안내](RECORDING_INPUT_WORKFLOW_CORE64_KO.md)의 폴더다.

```bash
core66_diagnostics_sha=$(sha256sum "$CORE61_EXAMPLE_DIR/saved/DIAGNOSTICS.json" | cut -d ' ' -f 1)
.venv/bin/python -B tools/recording_diagnostics_inspect.py \
  --input-root "$CORE61_EXAMPLE_DIR/saved" --expected-sha256 "$core66_diagnostics_sha"
```

전달하는 SHA는 원본 `INPUT.json`이 아닌 **DIAGNOSTICS.json의 SHA**다. 전달 전에
신뢰할 경로로 확보해야 한다. 같은 폴더에서 SHA를 다시 계산하는 위 예제는 사용법을
보여줄 뿐, 이미 함께 변조된 파일의 원래 출처를 인증하지 않는다.

유효한 결과는 `inspection_status=SAVED_DIAGNOSTICS_CONSISTENT`, exit0이다.
저장 결과가 DIFFERENT여도 검사 자체는 exit0이며 `saved_status=DIFFERENT`,
`saved_diagnostic_exit_code=1`을 보존한다. 검사 성공을 새 진단 MATCH로 해석하지 않는다.
오류는 exit2와 고정 code이며 성공 JSON을 출력하지 않는다.

## 무엇을 확인하는가

- 외부 SHA 형식을 경로 접근 전에 확인한다. 폴더에는 정해진 두 regular file만
  있어야 한다. root·부모·member symlink, FIFO, 누락·추가 파일을 거절한다.
- 각 파일을 read-only fd로 한 번 캡처한다. JSON 1048576bytes, checksum 512bytes의
  reported/actual 크기 제한을 적용하고, root identity와 파일 집합을 확인한다.
  descriptor를 닫은 뒤 캡처 bytes를 파싱하며 파일을 다시 열지 않는다.
- 외부 SHA와 정확한 내부 Manifest, UTF8·canonical JSON·중복 key·숫자 token·깊이를
  검사한다. float/nonfinite, bool을 int처럼 쓴 값, 누락·추가 key는 수용하지 않는다.
- 기존 CORE61의 schema·상태 범위·행 수·index 순서·저장/계산 상태의 차이 목록과
  전체 요약을 확인한다. 다음 entry의 applied/counter는 이전 **선언 saved state**와
  연결하며 계산된 state로 고쳐 연결하지 않는다.
- 원본의 전체 진단은 `stored_record`에 보존한다. `recorded_model_steps`와 그 안의
  `new_synthetic_model_steps`는 **과거 저장 작업량**이다. 이번 조회의 top-level
  `new_synthetic_model_steps=0`, `new_reference_steps=0`과 구분한다.

파일/SHA 오류는 SAVED_DIAGNOSTICS_EXPECTED_SHA256 / INPUT / CHECKSUM,
JSON 오류는 SAVED_DIAGNOSTICS_JSON, 저장 schema/행 관계 오류는 RECORD / ROWS
접미사를 쓴다. CLI 사용법과 일반 운영 실패도 고정 code만 출력하고 경로나 원문 예외를
stderr로 전달하지 않는다. stdout 일부가 나온 뒤 실패하면 prefix는 되돌릴 수 없으므로
exit2 출력을 유효한 영수증으로 사용하지 않는다. 재시도나 파일 삭제는 하지 않는다.

## 확인하지 않는 것

이 검사는 저장된 값들 사이의 관계만 확인한다. 산술을 재계산하지 않으며 원본 입력
bytes·출처·현재 source·첫 anchor·prehistory를 검증하지 않는다. 계산 결과와 선언값을
함께 일관되게 조작하고 SHA도 다시 만들면 통과할 수 있다.
`arithmetic_recomputed=False`, `original_input_verified=False`를 항상 유지한다.
root identity와 체크섬 검사는 atomic snapshot, 이후 경로 내용 또는 악의적 process에
대한 보증이 아니다. Linux/Python3.12 개발 tree 명령이며 설치형 wheel entry가 아니다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
F70UH/F70V/F71=NOT_ALLOWED를 유지한다. 실제 input/capture/Controller/Runtime/CAN/
F61/actualdt/r/install/deploy=0이다. 새 inspector의 모델 작업은 0이지만 전체 unit/gate의
합성/model/reference/numeric 작업은 비영·미집계다.
