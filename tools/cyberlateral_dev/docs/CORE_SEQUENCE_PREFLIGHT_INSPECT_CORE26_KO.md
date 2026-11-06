# CORE26 저장 입력 검증 묶음 읽기 전용 검사

[CORE25](CORE_SEQUENCE_PREFLIGHT_WORKFLOW_CORE25_KO.md)의 세 파일을
명시적으로 제공한 원래 ZIP·전체 SHA와 다시 대조한다. 체크섬만 맞는 변조 보고서는
수용하지 않는다. 기존 CORE21/23 결과를 다시 생성해 정확한 bytes를 비교한다.

## 명령과 API

전용 개발 환경에서 실행한다. 원본 ZIP과 저장 폴더가 모두 필요하다.

```bash
.venv/bin/python -I -B tools/core_sequence_preflight_inspect.py \
  --input-root /absolute/saved-preflight-folder \
  --archive /absolute/original-suite.zip \
  --sha256 FULL_LOWERCASE_SHA256
```

각 옵션은 정확히 한 번·비어 있지 않게 전달한다. SHA는 별도로 확인·전달한 원래
ZIP의 전체64자리 소문자 SHA256이다. 약어·중복·positional·run/export/output/rate
옵션은 거절한다. 원본 ZIP이나 파일을 추출·수정하거나 폴더를 생성하지 않는다.
출력은 stdout의 canonical JSON receipt뿐이다. Shell redirection은 caller 작업이며
원본 파일을 출력 대상으로 지정하면 별도로 덮어쓸 수 있으므로 주의한다.

API는 `integration_tools.core_sequence_preflight_inspect.inspect_preflight_report(
input_root: Path, input_archive: Path, expected_sha256: str) -> dict`다.

## 검사와 판정

1. SHA 형식을 caller 경로 접근보다 먼저 검사한다.
2. nonsymlink root와 정확한 regular-file3개 레이아웃을 원래 ZIP capture보다 먼저 확인한다.
3. 기존 CORE23 Path API를 한 번 호출한다. ZIP capture/verifier/renderer 각1회,
   CORE21의 세 case 현재 입력 의미 검증을 수행한다. 산술 재실행이 아니다.
4. 원래 JSON·Markdown·이름순2-entry checksum bytes를 생성한다. 저장된 각 파일은
   CORE18 bounded reader로 한 번 capture하고 전체 bytes를 대조한다.
5. root fd/path dev·inode와 종료 레이아웃을 검사하고 모두 일치해야 receipt를 반환한다.

필수 파일은 `PREFLIGHT.json`, `SUMMARY_KO.md`, `SHA256SUMS.txt`뿐이다.
checksum은 앞의 두 파일만 포함하고 자기 자신은 제외한다. CORE25 stdout receipt는
네 번째 파일이 아니며 요구하거나 authority로 사용하지 않는다.
symlink/FIFO/directory/누락/추가 파일은 거절한다. file cap은 재생성한 해당 bytes 길이,
읽기 한도는 cap+1이며 regular-file/size를 읽기 전에 확인한다. 변경된 root도 거절한다.
현재 checkout 안의 폴더도 읽기 전용이면 검사할 수 있으며 새로운 쓰기 허용이 아니다.

| 종료값 | 뜻 |
|---|---|
| 0 | 원래 ZIP에서 재생성한 결과와 저장3파일이 정확히 일치 |
| 2 | 사용법·무결성·보고서 크기·경로·정합성·운영 오류 |

검사 종료값1은 없다. **검사 성공0과 현재 입력 호환은 다르다.** 기본 묶음은
호환2/거절1이고,정상 저장된 거절 보고서를 검사하면 exit0이다. receipt에는
`preflight_status=INPUTS_REJECTED`, `preflight_exit_code=1`을 그대로 남긴다.
과거 저장 label/step이나 CORE25의 저장 완료 상태는 현재 입력 판정의 근거가 아니다.
현재 입력 판정이 달라진 개발 소스로 과거 보고서를 검사하면 불일치로 거절할 수 있다.
보고서를 고치거나 과거 판정을 새 소스로 자동 승격하지 않는다.

## receipt와 오류

CORE26_SAVED_PREFLIGHT_REPORT_INSPECTION_V1 / SAVED_PREFLIGHT_REPORT_CONSISTENT,
inspection_exit_code0,execution_requested false,현재 preflight0/1,원래 archive SHA/size,
case/prefix/기록 수,세 파일의 SHA/size,작업량,원래 false authority flags/Gates를 담는다.
입력 경로·현재 시각은 포함하지 않아 동일 bytes는 다른 경로에서도 같은 receipt다.

PREFLIGHT_INSPECT_REPORT_MISMATCH는 재생성 보고서 불일치,
PREFLIGHT_INSPECT_ROOT_IDENTITY는 최종 root identity 불일치다.
CORE18/CORE12 경로·레이아웃·size 오류는 PREFLIGHT_INSPECT:<원래code>,
일반 OS/값/실행 오류는 PREFLIGHT_INSPECT_INPUT으로 감싼다.
원래 ArchivePreflightError·PreflightReportError는 code를 그대로 보존한다.
내부 programming error는 API에서 전파하며 CLI는 고정 운영 오류2로 처리한다.
CLI 사용법은 PREFLIGHT_INSPECT_USAGE_NO_MODEL_EXECUTION,
그 밖의 운영 실패는 PREFLIGHT_INSPECT_FAILED_NO_MODEL_EXECUTION이다.
raw caller 경로나 예외 원문은 진단에 노출하지 않는다. short write는 완료하고,
실패한 stdout/help/stderr도 운영2다. 이미 전달된 stdout prefix는 회수할 수 없으므로
완전한 JSON과 exit를 함께 확인한다. 오류에 입력을 삭제·수정·재시도하지 않는다.

## 보장하지 않는 것

CLI main의 parser부터 출력까지 bytecode 억제·원래 flag/path 복원,
temp/cache/probe 및 파일시스템 쓰기0이다. 초기 import는 caller-managed(-I -B예제).
새 producer/publisher/model/reference/F61/실제r-dt/Controller/Runtime/CAN 작업0,
numeric validation·전체 unit/gate fixture 작업은 별도 NONZERO_NOT_AGGREGATED다.
Linux CPython3.12.13/cooperative 환경의 captured bytes 정합성이다.
atomic snapshot·atime 보존·적대적 경로 경쟁/hooks·동시 globals·다른 플랫폼·
브라우저 visual·출처·저장 산술·prehistory·computed rollout·차량 성능 인증이 아니다.
실제r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
Candidate/Runtime=NO_GO,F70UH/F70V/F71·실차 활성화 NOT_ALLOWED를 유지한다.
