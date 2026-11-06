# CORE23 ZIP 입력 사전 검증의 한국어 요약

[CORE21](CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CORE21_KO.md) 검증 결과를 한국어 Markdown으로
함께 반환한다. 원래 JSON·검증 규칙·[CORE22 CLI](CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CLI_CORE22_KO.md)는
변경하지 않았다. 새 HTML/CLI/모델 실행·F61 계산 기능이 아니다.

## API

`integration_tools.core_sequence_preflight_report`:

- `report_preflight_archive(input_archive: Path, expected_sha256: str) -> tuple[dict, bytes]`
- `report_preflight_archive_bytes(raw: bytes, expected_sha256: str) -> tuple[dict, bytes]`

첫 값은 변경 없는 CORE21 receipt, 두 번째는 UTF8 Markdown이다. 해당 CORE21 API를
한 번 호출한 뒤 검산된 소유 기록만 표시한다. 임의 dict/JSON 파일용 public renderer는
없으며, ZIP을 다시 열거나 추출·수정·모델 재실행하지 않는다.

기존 tools/cyberlateral_dev 전용 환경과 cwd에서:

```bash
.venv/bin/python -I -B -c '
import sys
from pathlib import Path
sys.path[:0] = [str(Path.cwd()), str(Path.cwd() / "src")]
from integration_tools.core_sequence_preflight_report import report_preflight_archive
receipt, markdown = report_preflight_archive(Path(sys.argv[1]), sys.argv[2])
sys.stdout.buffer.write(markdown)
' /absolute/suite.zip FULL_LOWERCASE_SHA256
```

이 API 예제의 exit0은 **보고서 생성 완료**이지 현재 입력 호환 판정이 아니다.
현재 판정은 `receipt['preflight_status']`에서 확인한다. 자동화의 판정별 exit0/1/2가
필요하면 기존 CORE22 CLI를 사용한다. SHA는 별도로 전달·확인한 전체64자리 소문자
SHA256이며 prefix나 ZIP 내부 manifest hash로 임의 대체하지 않는다.
출력 저장은 caller 책임이며 shell redirection을 입력 ZIP에 걸면 실행 전에 손상시킬 수 있다.

## 표시 의미

계약은 CORE23_PORTABLE_INPUT_PREFLIGHT_SUMMARY_V1이다. 다음을 구분한다.

- 현재 aggregate 입력 판정, 전체/호환/거절 case 수와 전체 처리 여부.
- 성공한 입력 검증 prefix 합계와 선언된 전이 수. 전이 실행 횟수가 아니다.
- 과거 recorded model steps와 요약의 신규 model/reference0, numeric validation 비영.
- 전체 archive SHA/size/member 수와 과거 저장 M/D/R 개수.
- 고정 순서의 모든 세 case: 현재 판정/거절, 검증 prefix/선언 전이,
  과거 판정/거절/기록 model steps.
- 모든 권한 flag와 유지 Gate. null/false/0을 서로 다른 JSON 타입으로 표시한다.

기본 묶음은 현재 호환2/거절1·검증8/선언9·과거 steps6이다. 과거 DIFFERENT도
현재 입력이 호환일 수 있고, 과거 REJECTED인 정합 사본도 현재 입력만 호환일 수 있다.
현재 모두 거절이면 세 행 모두 표시한다. 과거 label을 다시 계산·정정하거나
현재 호환 판정으로 과거 저장 산술/출처를 승인하지 않는다.

## 안전한 표시와 오류

CORE15의 기존 safe preview를 그대로 재사용한다. 모든 동적 표 셀은 typed JSON
ASCII로, control/bidi·backtick·pipe·HTML delimiter를 escape한다. escape 후 payload
160자 한도 밖은 PREVIEW_TRUNCATED와 잘림 수로 표시한다. 원문 전체가 아닌 발췌이며
정확한 값은 함께 반환한 **원래 JSON**을 사용한다. JSON 원문을 clamp·변경하지 않는다.
요약 최대65536UTF8bytes. 초과하면 `PreflightReportError.code=PREFLIGHT_REPORT_SIZE`로
거절하며 부분 요약을 반환하지 않는다. 기존 SHA/ZIP/schema/의미 검사 오류와 예상하지
못한 helper/renderer 오류는 숨기거나 정상 판정으로 바꾸지 않고 전파한다.

## 범위와 Gate

Markdown 소스 검사이지 browser visual PASS가 아니다. 문서 예제는 -I -B를 쓰며
module import 인프라는 caller-managed다. Linux CPython3.12.13/cooperative API 외의
이식성·hostile hooks·atomic snapshot·atime 보존·적대적 경로 경쟁은 보장하지 않는다.
요약 API의 신규 model/reference/F61/실제r-dt/Controller/Runtime/CAN/차량 작업은0이다.
입력 numeric validation과 전체 unit/gate fixture 작업은 별도 NONZERO_NOT_AGGREGATED다.
실제r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
Candidate/Runtime=NO_GO,F70UH/F70V/F71·실차 활성화 NOT_ALLOWED 유지.
