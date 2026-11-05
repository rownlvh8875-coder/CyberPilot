# CORE16 저장 ZIP 비교·요약 묶음

두 CORE13 ZIP 검증 → CORE14 비교 → CORE15 한국어 요약 → 새 외부 폴더 저장을
명령 한 번으로 수행한다. 모델을 새로 실행하거나 차량 데이터를 처리하지 않는다.

## 사용

`tools/cyberlateral_dev`에서 기존 전용 Python 환경을 사용한다. 입력 SHA는 별도로
검산·전달된 전체64hex 값을 사용하고, 출력의 부모 폴더는 먼저 존재해야 한다.

```bash
.venv/bin/python -I -B tools/core_sequence_archive_workflow.py \
  --left-archive /absolute/left.zip --left-sha256 FULL_LEFT_SHA256 \
  --right-archive /absolute/right.zip --right-sha256 FULL_RIGHT_SHA256 \
  --output-root /absolute/NEW-comparison-folder
```

`FULL_*`는 사용자가 가진 정확한 전체 SHA로 교체한다. 축약 SHA·생략된 output·
`--run`·`--format`·옵션 축약은 거절한다. 기존 디렉터리도 출력으로 재사용하지 않는다.
폴더에 다음3개만 저장한다.

- `COMPARISON.json`: 변경하지 않은 [CORE14 비교](CORE_SEQUENCE_ARCHIVE_COMPARE_CORE14_KO.md)의 canonical JSON.
- `SUMMARY_KO.md`: [CORE15 요약](CORE_SEQUENCE_ARCHIVE_REPORT_CORE15_KO.md) bytes 그대로.
- `SHA256SUMS.txt`: 위2파일의 이름순 전체 SHA, 자기 자신 제외.

stdout은3파일의 SHA/size·비교 상태·Gate가 담긴 canonical JSON receipt다.
`ARCHIVE_REPORT_PUBLISHED`는 파일 저장/readback 성공이지 산술·차량 PASS가 아니다.
exit0=검증된 ZIP bytes 동일, exit1=유효한 차이도 정상 저장 완료, exit2=거절/실패다.
저장된 MATCH/DIFFERENT/REJECTED는 과거 판정이며 이 exit를 결정하지 않는다.

API `integration_tools.core_sequence_archive_workflow.publish_archive_report(left: Path,
left_sha256: str, right: Path, right_sha256: str, output_root: Path) -> dict`도 같다.
`ArchiveWorkflowError.code`와 기존 `ArchiveCompareError`/`ArchiveReportError`를 보존한다.
같은 입력은 다른 출력 경로에서도3파일과 receipt가 byte-identical하다.

## 저장·실패 경계

양쪽 SHA 형식은 caller path 접근 전에 검사한다. private CLI cache는 별개 기반 작업이다.
출력은 현재 checkout 밖, 기존 parent 아래의 NEW 경로만 허용한다. 경로 구성요소의
symlink·기존 파일/폴더·잘못된 Path/NUL/UTF8을 거절한다. 입력과 같은 외부 parent는
허용하지만 입력을 덮어쓰지 않는다. 각 ZIP role을 한 번만 캡처·검증하고 비교/요약을
마친 뒤 mkdir한다. 입력 실패 때는 출력 폴더를 만들지 않는다.

폴더0700·파일0600, exclusive/no-follow 쓰기, 짧은 쓰기 처리, 고정 file set와
regular-file/size/전체 bytes readback, root fd/path identity를 검사한다. CORE14
상세4MiB·CORE15 요약65536bytes 한도를 그대로 유지하며 JSON은64KiB를 넘을 수 있다.
readback 한도는 각 생성 파일 길이+1이므로 기존 큰 비교를 잘라내지 않는다.

`PUBLICATION_FAILED_PARTIAL_DIRECTORY_POSSIBLE`은 빈/부분 폴더가 남을 수 있다는 뜻이다.
`PUBLICATION_CHECK_FAILED_DIRECTORY_MAY_EXIST` 또는 generic
`ARCHIVE_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION`도 파일이 있을 수 있다.
자동 삭제·재시도·overwrite하지 않는다. exit2면 폴더를 성공 결과로 취급하지 말고 보존해
조사한다. cache cleanup 후 stdout을 쓰지만 stdout 실패 때 이미 저장한 폴더/prefix는
되돌리지 못한다. 한 번 성공한 폴더도 후속 변경에서 보호·서명되는 것은 아니다.

Python3.12/POSIX/cooperative filesystem 범위다. atomic snapshot, crash/power-loss
durability/fsync, 적대적 부모/alias 경쟁, atime 불변, 반복 CLI embedding 및 모든 renderer의
시각 품질은 보장하지 않는다. unsigned checksum은 자기 일관성이지 원본 출처 인증이 아니다.

## 유지 제한

추출·새 모델/reference·F61 import/계산·r/dt·Controller·Runtime·CAN·실차 입력/활성화0.
이는 이 비교·저장 작업만의 수치다. 전체 unit/gate fixture 작업은
NONZERO_NOT_AGGREGATED로 별개다. 실제 r/T2/scale=null, R_BUDGET=UNRESOLVED,
Static Gate=FAIL, Candidate/Runtime=NO_GO, F70UH/F70V/F71=NOT_ALLOWED를 유지한다.
출처·산술·현재 source/build/deployment·성능·차량 qualification을 발행하지 않는다.
