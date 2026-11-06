# CORE22 Portable ZIP 입력 사전 검증 명령

[CORE21 API](CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CORE21_KO.md)의 원래 JSON을 단일 명령으로
출력한다. ZIP 추출·합성 실행·F61 계산 명령이 아니며 기존 API/CLI를 바꾸지 않는다.

## 사용

tools/cyberlateral_dev의 기존 전용 환경에서:

```bash
.venv/bin/python -I -B tools/core_sequence_archive_preflight.py \
  --archive /absolute/suite.zip \
  --sha256 FULL_LOWERCASE_SHA256
```

`--archive`와 `--sha256`은 각각 정확히 한 번, 비어 있지 않게 전달한다.
SHA는 별도로 전달·확인한 전체64자리 소문자 SHA다. ZIP 내부 manifest의 hash나
생략된 prefix로 대체하지 않는다. 옵션 순서와 `--archive=...` 형식은 허용한다.
약어·중복·positional·run/export/output/rate 옵션은 거절한다. `--help`는 입력을
열거나 프로젝트 API를 import하지 않고 설명을 출력한다.

| 종료 코드 | 의미 | stdout |
|---|---|---|
| 0 | 현재 세 입력이 모두 호환 | 원래 CORE21 canonical JSON |
| 1 | 현재 하나 이상 입력의 의미 거절 | 원래 CORE21 canonical JSON, 세 case 모두 포함 |
| 2 | 사용법·파일·SHA·ZIP·운영 오류 | 정상 receipt 없음; 출력 도중 실패하면 prefix가 남을 수 있음 |

기본 고정 ZIP은 호환2/거절1이므로 **exit1이 기대값**이다. 과거 saved MATCH/
DIFFERENT/REJECTED나 recorded step으로 exit를 결정하지 않는다. 과거 REJECTED여도
현재 모든 입력이 호환인 별도 정합 사본이면0이며, 전부 의미 거절이면1이다.
이는 과거 결과의 재계산·정정·출처 승격이 아니다.

## 검증·오류 경계

CLI는 CORE21 Path API를 한 번 호출한다. API는 SHA 형식을 경로 접근보다 먼저
확인하고 ZIP을 한 번 bounded read하며, 전체 CORE13 검산 후 세 case를 검사한다.
caller ZIP/원본 case 파일은 수정하거나 추출하지 않는다.

진단은 stderr의 고정 한 줄이다.

- 사용법: `REJECTED: ARCHIVE_PREFLIGHT_USAGE_NO_MODEL_EXECUTION`
- 저장/검산: `REJECTED: ARCHIVE_PREFLIGHT:<기존 PORTABLE code>`
- 그 밖의 운영 실패: `REJECTED: ARCHIVE_PREFLIGHT_FAILED_NO_MODEL_EXECUTION`

원래 예외 메시지·caller 경로를 진단에 노출하지 않는다. 예상하지 못한 상태/예외를
정상 의미 거절로 바꾸지 않는다. 전체 JSON 직렬화 후 descriptor로 완전히 출력하며
짧은 write는 이어 쓴다. 후속 stdout 실패 때 이미 전송한 prefix는 되돌릴 수 없다.
호출자는 exit와 완전한 JSON을 함께 확인해야 한다. 실패/닫힌 stderr에 진단을
전달하지 못해도 운영 exit2를 유지한다. help 출력 실패도2다.

## 실행 환경과 권한

parser 생성부터 API import/출력까지 bytecode를 억제하고 sys.path와 원래 flag를
복원한다. 임시/cache 생성·probe 없이 pycache_prefix·temp 환경 설정은 유지한다.
module import 인프라는 caller 책임이므로 문서 명령은 -I -B를 사용한다.
Python embedding의 hostile hooks/전역 동시 변경·적대적 경로 경쟁·atomic snapshot·
atime 보존·설정된 Linux CPython3.12.13 밖의 이식성은 보장하지 않는다.
caller가 직접 입력 경로에 shell redirection을 하면 실행 전에 훼손할 수 있다.

입력 숫자 해석·양자화 검증은 NONZERO_NOT_AGGREGATED다. 명령의 새 model/reference
step·F61·실제 r-dt·Controller/Runtime/CAN/차량 실행은0이며, 전체 unit/gate fixture
작업은 별도 비영이다. 출처·저장 산술·prehistory·차량 성능 인증을 추가하지 않는다.
실제 r/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
Candidate/Runtime=NO_GO,F70UH/F70V/F71·실차 활성화 NOT_ALLOWED 유지.
