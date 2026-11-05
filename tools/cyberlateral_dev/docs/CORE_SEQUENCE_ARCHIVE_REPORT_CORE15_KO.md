# CORE15 — 저장 ZIP 비교의 읽기 쉬운 요약

CORE14의 검증·비교 결과를 한국어 Markdown으로 보여 준다. 입력은 CORE13 saved-suite
ZIP 두 개와 각각의 외부 전체 SHA다. 원본을 재열거나 압축 해제·모델 재실행하지 않는다.
기존 CORE14 JSON/CLI와 모든 Python은 변경하지 않았다.

## 사용

기존 개발 환경의 프로젝트 폴더에서 실행한다. SHA 자리에는 신뢰하는 인계 경로의
전체64hex 소문자 SHA256을 넣는다. 자기 checksum만으로 출처가 인증되지는 않는다.

```bash
.venv/bin/python -I -B tools/core_sequence_archive_report.py \
  --left-archive /external/baseline.zip --left-sha256 FULL_LEFT_SHA256 \
  --right-archive /external/current.zip --right-sha256 FULL_RIGHT_SHA256
```

stdout은 UTF8 Markdown이다. exit0은 검증된 ZIP bytes 동일, exit1은 검증된 차이,
exit2는 오류·미지원이다. 셸로 출력 파일에 저장할 수 있지만 CLI에 output/덮어쓰기 API는
없다. 별도 프로그램에서 사용할 때는 API를 사용한다.

`integration_tools.core_sequence_archive_report.report_suite_archives(left: Path,
left_sha256: str, right: Path, right_sha256: str)`는 `(comparison, markdown_bytes)`를
반환한다. byte 입력용 `report_suite_archive_bytes`도 같은 순서·반환값이다.
첫 값은 변경되지 않은 CORE14 dict이며 완전한 원문 비교를 확인하는 데 사용한다.
임의 dict/JSON 파일을 읽어 보고서를 승인·재구성하는 public renderer는 없다.

## 표시 규칙

전체 SHA·size, 저장 M/D/R·과거 step, case별 집계, INPUT/RESULT/IDENTITY 전체 수,
CORE14가 보존한 상세 수와 요약에 표시한 수를 구분한다. 같은 ZIP에 저장 DIFFERENT/
REJECTED가 있어도 exit0일 수 있다. 이는 새 수치 MATCH·성능·출처·실차 승인이 아니다.

case별 첫20개, 전체 최대60개 상세를 보여 준다. 예를 들어 전체900개, CORE14 상세768개,
요약60개이면 CORE14 상세 중 미표시는708개이고 CORE14 한도 밖은132개다. 생략을
숨기거나 전체 차이 수를 표시 수로 바꾸지 않는다. missing/null은 존재 열로 구분하고
false/0은 JSON 타입 표현을 그대로 유지한다. pointer는 case와 함께 읽는다.

case별 집계 표에도 INPUT/RESULT/IDENTITY 전체 합계를 별도 열로 표시한다. 이 값은
각 case의 원문 비교에서 가져오며, 요약 첫20개에 특정 분류의 상세가 없어도 그 분류의
전체 수는 숨기지 않는다. 예를 들어 IDENTITY25개와 RESULT1개이면 전체26/INPUT0/
RESULT1/IDENTITY25/CORE14상세26/요약20으로 표시한다.

셀은 원문 전체가 아닌 표시용 JSON 발췌다. escape 후 ASCII payload 최대160자로
제한하며 잘리면 PREVIEW_TRUNCATED marker와 잘림 수를 보여 준다. 발췌가 완전한 JSON일
필요는 없다. Unicode/control/bidi는 JSON escape, backtick/pipe/HTML delimiter도
literal Unicode escape로 표시하고 code span 안에 넣어 table/HTML 삽입을 막는다.
정확한 전체 경로/값은 반환된 CORE14 비교를 확인한다. 요약 전체 한도는65536bytes다.
초과하면 ARCHIVE_REPORT_SIZE/exit2/no summary이며 원문을 clamp·변경하지 않는다.

CORE14의4MiB 상세 진단 한도도 그대로 적용한다. 요약이 작아질 수 있다는 이유로
거절된 비교를 재실행·우회·부분 표시하지 않는다. 양쪽 SHA 형식은 입력 접근 전 검사하고
role별 한 번만 캡처·검증한다. CLI private cache는 입력 접근과 별개의 기반 작업이다.

Markdown 소스의 문법·escape·개수 검사는 모든 renderer에서의 시각 품질 증명이 아니다.
새 HTML/화면/브라우저를 만들지 않았고 browser visual PASS도 주장하지 않는다.

## 오류와 범위

입력 비교 오류는 기존 ARCHIVE_COMPARE_LEFT/RIGHT/DETAIL_BYTE_LIMIT 코드를 보존한다.
예상하지 못한 CLI 오류는 ARCHIVE_REPORT_FAILED_NO_MODEL_EXECUTION이다. 캐시 생성 오류는
ARCHIVE_REPORT_CACHE_IO_NO_MODEL_EXECUTION이다. cleanup·렌더·exit 계산 후에만 stdout을
쓰며, 쓰기 도중 실패한 이미 전송된 prefix는 되돌리지 못하므로 exit code를 확인한다.

원본 bytes/mode 보존의 read-only 범위다. Python3.12/POSIX/cooperative filesystem 외의
플랫폼·atomic snapshot·적대적 부모/alias 경쟁·atime 불변·반복 CLI embedding은 보장하지
않는다. origin/산술/현재 source·build·deployment 인증은 없고 일관된 위조는 통과할 수 있다.

실제 r/T2/vehicle_scale=null, R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL을 유지한다.
F61·Controller·Runtime·CAN·실제 r/차량 input·활성화는 실행·승인하지 않는다.
F70UH/F70V/F71은 NOT_ALLOWED다. 전체 unit/gate fixture 합성 작업은 별개로
NONZERO_NOT_AGGREGATED이며 비교·요약 자체의 신규 모델/reference0과 혼동하지 않는다.
