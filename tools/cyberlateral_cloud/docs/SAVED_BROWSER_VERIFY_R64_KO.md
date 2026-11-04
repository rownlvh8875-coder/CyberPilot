# R64 — 저장된 브라우저 결과의 읽기 전용 검산

브라우저 검사를 다시 실행하지 않고 이미 저장한 결과 폴더를 검산합니다.
Python 표준 라이브러리만 사용하며 Playwright·Chromium·app venv·HF 인증은
필요하지 않습니다. 설치·네트워크·모델·F61·Controller·Runtime·CAN 호출은 없습니다.
입력에 쓰거나 새 폴더·요약·checksum·FAILURE 기록을 만들지 않습니다.

## 실행

이 명령이 추가된 새 Git 도구 checkout에서 실행합니다. 고정 R62 복구 도구
commit `1b244fe8e2dee8636ce7811529978d9499cfedc8`에는 이 새 명령이 없습니다.
기존 [고정 복구 안내](RECOVERY_R62_KO.md)의 tool/source pins를 바꾸지 마세요.
아래는 Linux cloud의 일반 `python -B` 진입입니다. `python -I script.py`는
인접 도구 모듈을 검색하지 않으므로 이 실행 방식에 포함하지 않습니다.

```bash
python -B tools/cyberlateral_cloud/browser_verify.py \
  --input /workspace/EXISTING-browser-check
```

입력은 새 출력 경로가 아니라 기존 브라우저 결과 폴더입니다. API는
`verify_saved_browser(root: Path) -> dict`입니다. stdout JSON은 경로·시각을
추가하지 않아 같은 bytes에 대해 결정적이며, 거절 시 stdout은 비어 있습니다.
stderr의 `REJECTED: BROWSER_BUNDLE_*`는 traceback이나 원본 예외를 노출하지 않습니다.

## 결과 해석

- exit0: 무결성/기록 연결이 유효하며 원래 상태가 `R60_BROWSER_SMOKE_PASS`입니다.
- exit1: 무결성/기록 연결은 유효하지만 원래 상태가 `R60_BROWSER_SMOKE_FAIL`입니다.
- exit2: 부분·손상·읽기 불가·지원하지 않는 형식입니다. 성공으로 사용하지 마세요.

유효한 묶음은 `R64_SAVED_BROWSER_BUNDLE_VALID`, `recorded_status`, 10개 case,
저장된 개별/전체 실패 수, 검산한38파일과 RESULT SHA를 반환합니다.
VALID는 **새 화면 검사 PASS가 아닙니다**. 전체 실패만 있고 개별10건이 PASS여도
원래 FAIL과 exit1을 유지합니다. case의 metrics를 다시 판정하지 않으며 unknown
failure code·null·미관측을 임의의 정상/0으로 바꾸지 않습니다.

## 검산 범위

현재 R62 요약 형식과 RESULT schema1에 맞는 완료 폴더만 지원합니다. 원본 RESULT,
현재 표현과 일치하는 SUMMARY, root/중첩 checksum, 두 프로필의 fixture-inputs와
reports, 캡처12개, child 로그3개가 필요합니다. 총38개 일반 파일/7개 디렉터리의
정확한 소유 범위입니다. pre-summary R60·다른 과거/미래 요약 형식·ZIP 파일·기타
보고서를 자동 변환하거나 복구하지 않습니다. 추가 디버그 파일/빈 폴더도 거절합니다.

- 파일별8MiB·전체32MiB 한계, 경로/부모/leaf symlink와 특수 파일 거절.
- Linux no-follow/nonblocking regular-file read로 leaf-link/FIFO 대기를 방지.
- 닫힌 canonical root와 중첩 checksum, RESULT의 input/report/capture SHA 연결.
- strict UTF8 JSON: 중복 key·NaN/Infinity·overflow·지나친 중첩 거절.
- 정확한 타입의 version/선언된 무실행·source 불변 field와 source SHA 기록16개.
- 기존 pure summary 함수의 구조 검사와 SUMMARY bytes 일치, 원래 판정 유지.

`source_identity_reauthenticated=false`입니다. source SHA 기록은 문법만 검사하며,
그 원본 source bytes나 실행 환경을 새로 확보해 인증하지 않습니다. child VIEW/receipt의
수치·schema·origin을 독립 재평가하는 명령도 아닙니다. 캡처는 bytes만 검산하며 다시
열어 화면을 관찰하거나 모든 PNG의 의미를 검증하지 않습니다.

일관되게 위조하고 재봉인한 기록은 통과할 수 있습니다. checksum은 발행자 서명,
실제 브라우저 실행/출처 인증, 독립 수치 정답이나 실차 적격성 증명이 아닙니다.
동시 writer에 대한 atomic snapshot도 제공하지 않습니다. 검산 중 입력을 편집하지
말고, 실패 폴더는 보존한 채 원래 생성 도구에서 새 출력 경로로 재시도하세요.

기존 [실제 브라우저 검사](BROWSER_SMOKE_R60_KO.md)와 역할이 다릅니다.
R_BUDGET=UNRESOLVED · Static Gate=FAIL · 실제r/T2/scale=null,
Candidate/Runtime NO_GO · F70UH/F70V/F71 및 실차 활성화 NOT_ALLOWED를 유지합니다.
