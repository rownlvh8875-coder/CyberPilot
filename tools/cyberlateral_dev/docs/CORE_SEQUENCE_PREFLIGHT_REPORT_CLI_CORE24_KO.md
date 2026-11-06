# CORE24 한국어 입력 검증 요약 명령

[CORE23 API](CORE_SEQUENCE_PREFLIGHT_REPORT_CORE23_KO.md)의 원래 Markdown을 단일
명령으로 출력한다. 기존 [CORE22 JSON CLI](CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CLI_CORE22_KO.md)와
모든 검증·표시·계산 규칙은 유지한다. 새 HTML/모델 실행/출력 폴더 publisher가 아니다.

## 사용

기존 tools/cyberlateral_dev 전용 환경에서:

```bash
.venv/bin/python -I -B tools/core_sequence_preflight_report.py \
  --archive /absolute/suite.zip \
  --sha256 FULL_LOWERCASE_SHA256
```

두 옵션은 각각 정확히 한 번, 비어 있지 않게 전달한다. 순서와 `--archive=...` 형식은
허용하지만 약어·중복·positional·run/export/output/format/rate 옵션은 거절한다.
SHA는 독립적으로 전달·확인한 **입력 ZIP**의 전체64자리 소문자 SHA256이다.
--help는 프로젝트를 import하거나 입력을 열지 않고 설명을 출력한다.

| exit | 뜻 | stdout |
|---|---|---|
| 0 | 현재 세 입력이 모두 호환 | 원래 CORE23 UTF8 Markdown |
| 1 | 현재 하나 이상 입력의 의미 거절 | 원래 CORE23 Markdown, 세 case 모두 표시 |
| 2 | 사용법·파일·SHA·ZIP·표시·운영 오류 | 정상 요약 없음; 출력 도중 실패 시 prefix가 남을 수 있음 |

기본 ZIP은 현재 호환2/거절1이므로 **기대 exit1**이다. CORE23의 Python 예제는
생성 완료 시0이지만, 이 명령은 paired CORE21의 **현재 입력 판정**으로0/1을 정한다.
과거 saved MATCH/DIFFERENT/REJECTED나 기록 step으로 exit를 결정하지 않는다.
stdout은 CORE23 bytes 그대로이며 JSON을 붙이거나 다시 표시하지 않는다.

## 오류와 입력 보호

CORE23 Path API를 한 번 호출한다. CORE21의 bad SHA-before-path, 단일 bounded ZIP
capture/verifier, 전체 검산 후 세 case 판정, CORE23의 단일 renderer와 표시 한도는
그대로다. 원본을 추출·재열기·수정하지 않는다.

- 사용법: `REJECTED: PREFLIGHT_REPORT_USAGE_NO_MODEL_EXECUTION`
- 기존 무결성: `REJECTED: ARCHIVE_PREFLIGHT:<기존 PORTABLE code>`
- 표시 크기: `REJECTED: PREFLIGHT_REPORT_SIZE`
- 그 밖의 운영 실패: `REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION`

진단은 고정 한 줄로 caller 경로/원래 예외 텍스트를 노출하지 않는다. 전체 API 결과와
상태 확인 후에만 descriptor로 출력하며 짧은 write는 이어 쓴다. 후속 실패 시 이미
전송된 bytes는 되돌리지 못하며 UTF8 문자 중간에서 끊길 수도 있다. 호출자는 항상
exit와 완전한 Markdown을 함께 확인한다. 실패/닫힌 stderr가 운영2를 flush exit120으로
바꾸지 않으며 help 출력 실패도2다. 입력에 shell redirection을 걸면 Python 시작 전에
원본이 훼손될 수 있으므로 출력은 반드시 다른 경로로 보낸다.

## 서로 다른 SHA

입력 ZIP SHA, 원래 CORE21 receipt JSON SHA, acceptance 검증 JSON SHA,
출력 Markdown SHA와 evidence ZIP SHA는 **서로 다른 파일의 식별자**다.
특히 이전 CORE23 인계 문서의 “Summary SHA23041...”은 acceptance JSON을 가리키며
Markdown을 가리키지 않는다. 이전 봉인 bytes는 수정하지 않고 새 외부 근거의
CORE23_HASH_LABEL_CLARIFICATION.json/KO 보충 문서에서 실제 파일명·SHA를 명시한다.
체크섬 일치만으로 출처나 산술·차량 authority가 생기지 않는다.

## 범위

parser 생성부터 API import/출력까지 bytecode 억제, 원래 sys.path/flag 복원,
temp/cache 생성·probe0, pycache_prefix/temp 설정 불변이다. 초기 module import는
caller-managed이므로 예제는 -I -B를 사용한다. 설정된 Linux CPython3.12.13의
cooperative API만 확인하며 적대적 hooks/동시 전역 변경/atomic/atime/경로 경쟁/
다른 플랫폼/임의 embedded stdout adapter는 보장하지 않는다. browser visual PASS도 아니다.
새 command의 model/reference/F61/실제r-dt/Controller/Runtime/CAN/차량 작업0,
numeric validation과 전체 unit/gate fixture 작업은 별도 NONZERO_NOT_AGGREGATED다.
실제r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
Candidate/Runtime=NO_GO,F70UH/F70V/F71·실차 활성화 NOT_ALLOWED 유지.
