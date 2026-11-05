# CORE17 고정 합성 실행 → ZIP → 기준 비교

기존 [CORE12](CORE_SEQUENCE_SUITE_CORE12_KO.md) 고정3case 실행,
[CORE13](CORE_SEQUENCE_PORTABLE_CORE13_KO.md) ZIP 생성,
[CORE16](CORE_SEQUENCE_ARCHIVE_WORKFLOW_CORE16_KO.md) 비교·요약을 연결한다.
새 계산 알고리즘이나 임의 입력 reader가 아니다. 저장-only 작업인 CORE16과 달리
CORE17의 성공 실행은 **신규 합성 모델6step**을 수행한다.

## 실행

전용 환경이 있는 tools/cyberlateral_dev에서 명시적인 `run`만 사용한다.

```bash
.venv/bin/python -I -B tools/core_sequence_archive_run.py run \
  --baseline-archive /absolute/baseline.zip \
  --baseline-sha256 FULL_BASELINE_SHA256 \
  --output-root /absolute/NEW-offline-run
```

전체64hex SHA는 별도로 확인·전달된 값으로 교체한다. 출력 parent는 존재해야 하고,
출력 자체는 NEW/checkout 외부여야 한다. 기존 폴더도 재사용하지 않는다.
`run` 생략·`check`·`--format`·임의 입력·차량/r 설정 옵션은 받지 않는다.
모델 실행 없이 두 저장 ZIP만 비교하려면 CORE16을 사용한다.

생성 구조(파일14개):

```text
NEW-offline-run/
  BASELINE.zip             # 실행 전 검증한 원본 bytes의 보존 사본
  CURRENT.zip              # 이번 고정 합성 실행의 CORE13 ZIP
  suite/
    sign-cycle/            # 각 INPUT.json, RESULTS.json, SHA256SUMS.txt
    declared-difference/
    late-invalid/
  comparison/
    COMPARISON.json        # baseline LEFT / current RIGHT
    SUMMARY_KO.md
    SHA256SUMS.txt
```

stdout은 경로 없는 canonical JSON receipt다. 원래 각 단계의 receipt, 신규 합성
step 수, 비교 exit와 유지 Gate를 보존한다. receipt 자체는 폴더에 저장하지 않는다.
출력 폴더 전체의 새 Manifest/서명/atomic snapshot을 발행하지 않는다. 각 ZIP·case·
comparison의 기존 검산과 루트 고정2파일/2디렉터리 확인 범위다.

API는 `integration_tools.core_sequence_archive_run.run_archived_suite(baseline: Path,
baseline_sha256: str, output_root: Path) -> dict`, 오류는 `ArchiveRunError.code`다.

## 순서와 결과

full SHA 형식을 경로 조회보다 먼저 검사하고 원본을 한 번만 캡처·검증한다.
복사한 BASELINE.zip까지 exclusive 쓰기/readback한 다음 모델을 실행한다. 그 뒤 원본
경로가 바뀌어도 캡처한 bytes가 기준이며 비교 때 원본을 다시 읽지 않는다.
private CLI cache 생성은 이 caller-path 검사와 별개의 기반 작업이다.

고정 실행 결과는 정상적으로 MATCH/DIFFERENT/REJECTED 각1개, 신규 steps3/3/0=6이다.
의도된 저장 DIFFERENT/REJECTED가 workflow 실패나 실제 차량 불합격 판정은 아니다.
exit0=검증된 ZIP bytes 동일·workflow 완료,1=유효한 저장 차이·workflow 완료,
2=거절/실패다. 성공 status는 OFFLINE_SYNTHETIC_ARCHIVE_RUN_COMPLETED이며
새 성능/수치 전반/출처/차량 qualification PASS가 아니다.

## 실패와 유지 경계

PREFLIGHT의 NO_MODEL_EXECUTION은 신규 실행/출력 생성0이다. 기존 출력은 보존한다.
BASELINE_COPY의 NO_MODEL_EXECUTION/OUTPUT_MAY_EXIST는 부분 사본이 남을 수 있다.
RUN/EXPORT/COMPARE/FINAL_LAYOUT 및 generic cleanup/stdout 오류는
WORK_MAY_BE_NONZERO/OUTPUT_MAY_EXIST다. 앞선 결과를 지우거나0작업으로 표시하지 않는다.
중단된 폴더를 자동 재시도·재개·수정·덮어쓰기하지 않는다. 새 경로에서만 새로 실행한다.
stdout 전 cache cleanup/serialization을 완료하지만 전송된 prefix는 되돌리지 못한다.

CPython3.12.13/cooperative POSIX filesystem 기준이다. stage별 captured records이지
동시 snapshot·나중 변경 방지·적대적 parent/alias 경쟁·atime 불변·정전/fsync 내구성·
반복 CLI embedding·모든 renderer의 시각 품질을 보장하지 않는다.
CORE13 2MB·CORE14 진단4MiB·CORE15 요약65536bytes 한도는 바꾸지 않는다.

실제 차량 입력·F61 import/계산·Controller/Runtime/CAN·actualr/dt·정책 승인0.
실제 r/T2/scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
Candidate/Runtime=NO_GO, F70UH/F70V/F71·실차 활성화=NOT_ALLOWED 유지.
전체 unit/gate fixture 합성 작업은 NONZERO_NOT_AGGREGATED로 별도다.
