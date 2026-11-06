# CORE25 입력 검증 JSON·한국어 요약 저장 묶음

입력 ZIP을 [CORE21](CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CORE21_KO.md)로 검증하고
[CORE23](CORE_SEQUENCE_PREFLIGHT_REPORT_CORE23_KO.md)의 원래 JSON·Markdown을
체크섬과 함께 **새 외부 폴더**에 저장한다. 모델 실행이나 원본 추출 명령이 아니다.

## 사용

기존 tools/cyberlateral_dev 전용 환경에서, 출력 parent가 이미 존재할 때:

```bash
.venv/bin/python -I -B tools/core_sequence_preflight_workflow.py \
  --archive /absolute/suite.zip \
  --sha256 FULL_LOWERCASE_SHA256 \
  --output-root /absolute/NEW-preflight-folder
```

옵션은 각각 정확히 한 번·비어 있지 않게 전달한다. 중복·약어·positional·run/export/
format/rate 옵션은 거절한다. SHA는 별도로 확인·전달된 입력 ZIP의 전체64자리 소문자
SHA256이다. 출력은 현재 checkout 밖의 NEW 경로여야 하며 기존 빈 폴더도 재사용하지
않는다. symlink·없는 parent·잘못된 Path/NUL/UTF8은 기존 저장기 규칙으로 거절한다.

저장 파일은 다음 세 개뿐이다.

- `PREFLIGHT.json`: 변경 없는 CORE21 canonical JSON.
- `SUMMARY_KO.md`: 변경 없는 CORE23 UTF8 Markdown.
- `SHA256SUMS.txt`: 위 두 파일의 이름순 전체 SHA256, 자기 자신 제외.

stdout은 별도 **저장 receipt**다. CORE25_PREFLIGHT_WORKFLOW_V1 계약과
PREFLIGHT_REPORT_PUBLISHED 상태,현재 입력 판정/exit,case 수와 검증 prefix,
입력 archive SHA/size,세 파일의 SHA/size,작업량/권한 flag/Gate를 담은 canonical JSON이다.
입력 JSON·출력 Markdown·저장 receipt·checksum 파일의 SHA는 각각 다른 파일의 식별자다.

| exit | 뜻 | 출력 폴더 |
|---|---|---|
| 0 | 저장/readback 성공 + 현재 모든 입력 호환 | 검산된3파일 |
| 1 | 저장/readback 성공 + 현재 하나 이상 의미 거절 | 검산된3파일,실패 저장이 아님 |
| 2 | 사용법·입력·표시·경로·저장·운영 오류 | 없을 수도,빈/부분/완전 폴더가 남을 수도 있음 |

기본 묶음은 현재 호환2/거절1이라 기대 exit1이다. 과거 저장 M/D/R나 기록 step은
이 exit를 정하지 않는다. PREFLIGHT_REPORT_PUBLISHED는 파일 저장 성공이지 산술·
실차 PASS가 아니며,현재 의미 거절도 원래 진단을 보존해 정상 저장한다.

## API와 순서

`integration_tools.core_sequence_preflight_workflow.publish_preflight_report(
input_archive: Path, expected_sha256: str, output_root: Path) -> dict`.

1. SHA 형식은 caller 입력·출력 경로 접근보다 먼저 검사한다.
2. 기존 CORE16 `_output`으로 출력 경로를 검증한다. 기존 출력 거절 시 입력을 읽지 않는다.
3. CORE23 Path API를 한 번 호출한다. 입력 ZIP 단일 capture/verifier,세 case 판정,
   단일 renderer를 유지하며 원본을 재열거나 추출·수정하지 않는다.
4. 현재 상태와 저장할 JSON·Markdown·manifest bytes를 준비한 뒤에만 mkdir한다.
5. 변경 없는 CORE16 `_publish`가 exclusive/nofollow 쓰기와 bounded readback을 수행한다.
   요청 mode는 디렉터리0700·파일0600이며 실제 권한은 환경의 umask 등에도 영향을 받는다.
6. 저장 성공 후 receipt를 반환한다. CLI의 receipt 직렬화/stdout 전달은 저장 후 작업이다.

정확한 file set·regular-file·size·전체 bytes와 root fd/path identity를 검사한다.
JSON/MD를 임의로 clamp하지 않으며 readback 한도는 생성한 각 파일 길이+1이다.
같은 입력을 다른 NEW 경로에 저장해도 세 파일과 receipt는 byte-identical하다.

## 실패·보존 경계

무결성 오류는 기존 ArchivePreflightError의 `ARCHIVE_PREFLIGHT:<PORTABLE code>`,
표시 크기는 PreflightReportError의 PREFLIGHT_REPORT_SIZE,출력/저장은 기존
ArchiveWorkflowError의 ARCHIVE_WORKFLOW_* 코드를 그대로 보존한다.
CORE16 오류명은 재사용한 저장기 namespace이며 비교·모델 실행을 뜻하지 않는다.

PUBLICATION_FAILED_PARTIAL_DIRECTORY_POSSIBLE는 빈/부분 폴더가 남을 수 있음을,
PUBLICATION_CHECK_FAILED_DIRECTORY_MAY_EXIST는 파일이 있어도 검산 성공이 아님을 뜻한다.
CLI 사용법 오류는 PREFLIGHT_WORKFLOW_USAGE_NO_MODEL_EXECUTION,그 밖의 운영 실패는
PREFLIGHT_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION이다.
raw caller 경로·예외 메시지는 진단으로 노출하지 않는다.

자동 삭제·재시도·덮어쓰기를 하지 않는다. exit2의 폴더는 보존해 조사한다.
저장 후 receipt encoding/stdout 실패는 **완전한3파일도 남길 수 있다**. stdout prefix는
되돌릴 수 없으므로 exit와 완전한 receipt를 함께 확인한다. 실패/닫힌 stderr나 help
출력도 운영2를 유지한다. caller가 shell redirection으로 원본을 덮어쓰는 일은 별도 위험이다.

## 권한·범위

CLI는 parser부터 출력까지 bytecode 억제,원래 sys.path/flag 복원,temp/cache 생성·
probe0이다. 초기 import는 caller-managed이므로 예제는 -I -B를 쓴다.
기존 계산·검증·표시·저장기 코드와 CLI는 변경하지 않는다. 신규 ZIP/reader/브라우저
visual PASS나 출처·산술·prehistory·computed rollout·차량 qualification은 추가하지 않는다.
Linux CPython3.12.13/cooperative filesystem 범위이며 atomic snapshot/fsync·crash durability/
atime 보존·적대적 hooks/동시 globals/경로 경쟁/다른 플랫폼은 보장하지 않는다.
이 workflow의 새 model/reference/F61/실제r-dt/Controller/Runtime/CAN/차량 작업0,
numeric validation과 전체 unit/gate fixture 작업은 별도 NONZERO_NOT_AGGREGATED다.
실제r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
Candidate/Runtime=NO_GO,F70UH/F70V/F71·실차 활성화 NOT_ALLOWED 유지.
