# CORE18 저장 실행 폴더 읽기 전용 검증

[CORE17](CORE_SEQUENCE_ARCHIVE_RUN_CORE17_KO.md)의 고정14파일을 새 모델 실행 없이
검사한다. 두 ZIP 검산뿐 아니라 suite9파일과 CURRENT.zip의 원문 일치, 비교 JSON·
요약·체크섬이 두 ZIP에서 재생성된 [CORE16](CORE_SEQUENCE_ARCHIVE_WORKFLOW_CORE16_KO.md)
내용과 같은지 확인한다. 개별 checksum만 다시 계산하고 끝내는 조회가 아니다.

## 사용

tools/cyberlateral_dev의 기존 전용 환경에서 실행한다.

```bash
.venv/bin/python -I -B tools/core_sequence_run_inspect.py \
  --input-root /absolute/saved-offline-run \
  --baseline-sha256 FULL_BASELINE_SHA256 \
  --current-sha256 FULL_CURRENT_SHA256
```

두 SHA는 별도로 전달·검산한 전체64hex 값으로 교체한다. 각 ZIP의 hash는 CORE17
receipt의 baseline_verification/current_export에서도 확인할 수 있다. 이는 서명이 아니다.
`--run`, `--output-root`, `--format` 옵션은 없다. 입력 폴더를 수정·수리·추출하거나
비교/모델 결과를 덮어쓰지 않는다. 기존 CLI의 private cache는 별도 임시 기반 작업이다.

CORE18-R1부터 이 Linux 환경의 CLI cache parent는 `/tmp`로 명시한다.
TMPDIR/TEMP/TMP와 cached tempfile.tempdir는 이 CLI에서 사용하지 않으며 변경하지도
않는다. implicit gettempdir probe도 하지 않는다. 두 SHA 형식을 먼저 검사하고,
입력이 존재하는 비심볼릭 디렉터리인지 확인한 뒤 cache를 할당한다. cache parent가
입력과 같거나 입력 내부면 RUN_INSPECT_CACHE_INPUT_OVERLAP_NO_MODEL_EXECUTION,
parent 부재/비디렉터리/생성 불가면 RUN_INSPECT_CACHE_IO_NO_MODEL_EXECUTION으로
exit2, fallback 없이 거절한다. 입력의 상위 디렉터리는 허용하지만 실제 private
cache는 기존 입력과 다른 새 디렉터리여야 한다. 인자 파서의 첫 lazy import부터
bootstrap까지 bytecode 쓰기를 억제하고,
성공/실패 모두 pycache_prefix와 dont_write_bytecode를 원래 값으로 복구한다.

API `integration_tools.core_sequence_run_inspect.inspect_archived_run(input_root: Path,
baseline_sha256: str, current_sha256: str) -> dict`, 오류 `RunInspectError.code`.
두 SHA 형식은 caller path metadata/open 전에 검사한다. BASELINE=LEFT,CURRENT=RIGHT다.

## 정확히 허용하는 구성

root의 BASELINE.zip/CURRENT.zip, suite의 고정3case×INPUT.json/RESULTS.json/SHA256SUMS.txt,
comparison의 COMPARISON.json/SUMMARY_KO.md/SHA256SUMS.txt, 총14파일만 허용한다.
root에 임의 receipt/Manifest/로그를 추가한 폴더도 거절한다. CORE17 stdout receipt를
보관하려면 이14파일 폴더 밖에 둔다. 누락/extra/심볼릭 링크/비정규 파일/FIFO를 거절한다.

성공 시 파일마다 한 번 캡처한다. ZIP은 각2MB, case는 기존65536/524288/512bytes
한도다. suite 캡처에서 canonical ZIP을 메모리 내 재생성해 CURRENT bytes와 exact 비교한다.
비교 JSON/Markdown은 검증 ZIP에서 한 번 재생성한다. 임의 저장 JSON을 해석해 renderer에
넣지 않는다. 실제 report 캡처 한도는 재생성된 각 파일의 정확한 길이이므로 정상 JSON이
64KiB보다 커도 허용하고, 과도한 파일은 bounded read로 거절한다. CORE14 진단4MiB·
CORE15 요약65536bytes 한도는 그대로이며 잘라내거나 fallback하지 않는다.

## 상태와 exit

조회 성공 status는 SAVED_ARCHIVE_RUN_CONSISTENT, CLI exit0이다. 저장 ZIP이 다르거나
저장 M/D/R에 DIFFERENT/REJECTED가 있어도 관계가 맞으면 조회는 성공이다.
receipt의 comparison_exit_code0/1,comparison_status,difference_counts를 별도로 읽는다.
exit2는 거절이며 부분 receipt를 발행하지 않는다. CLI cache cleanup 후 stdout을 쓰고,
stdout 중간 실패는 이미 전송한 prefix를 되돌릴 수 없으므로 종료 코드도 확인한다.

captured_file_sha256은14파일의 캡처 bytes를 식별한다. recorded_current_model_steps는
저장된 과거 수치일 뿐 CORE17 실행 사실을 인증하지 않는다. 조회 자체의
new_synthetic_model_steps/inspection_model_executions/inspection_reference_executions는0,
execution_requested/source_identity_reauthenticated/arithmetic_recomputed는 false다.

## 한계와 Gate

캡처 관계 일관성이지 동시 atomic snapshot, 후속 변경 방지, 원본/현재 소스 인증,
산술 진실·실행 사실·차량 qualification이 아니다. 일관되게 재작성한 records/ZIP/report와
갱신된 외부 SHA를 공급하면 통과할 수 있다. 조회 결과를 출처 인증으로 승격하지 않는다.
bytes/mode는 수정하지 않지만 atime·적대적 alias/경로 경쟁·fsync/정전 내구성·반복
CLI embedding·모든 Markdown renderer의 시각 동작은 보장하지 않는다.

기존 CPython3.12.13/configured Linux/POSIX 환경 기준이다. 조회에서 새 모델/reference/
F61 import·계산·Controller/Runtime/CAN·actualr/dt·실차 입력/활성화0. 전체 unit/gate의
합성 fixture 생성은 NONZERO_NOT_AGGREGATED로 별개다. 실제 r/T2/scale=null,
R_BUDGET=UNRESOLVED, Static Gate=FAIL, Candidate/Runtime=NO_GO,
F70UH/F70V/F71·실차 활성화=NOT_ALLOWED 유지.
