# R46 — 저장된 캠페인 비교 리포트

완전한 R44 V1 결과를 읽어 브라우저용 한국어 HTML을 생성합니다. 원래 캠페인이나
receipt에 적힌 경로를 다시 열지 않으며 모델·참조 worker·F61을 실행하지 않습니다.

```bash
tools/cyberlateral_dev/.venv/bin/python -I -B \
  tools/cyberlateral_dev/tools/scenario_campaign_compare_report.py \
  --input /absolute/complete-r44-result --output /absolute/new-r46-report
```

새 디렉터리의 `index.html`을 브라우저에서 엽니다. 출력은 네 파일입니다.

- `index.html`: 자체 포함 HTML. JS·외부 리소스·원래 경로 링크 없음.
- `VIEW.json`: 부모/하위 보존 기록 전체와 입력 파일 SHA. 정확한 값과 존재 여부 보존.
- `RECEIPT.json`: 실행 경로·Python·renderer 소스 identity를 담은 private 기록.
- `SHA256SUMS.txt`: 나머지 세 파일의 닫힌 checksum 목록.

전체 출력은 private receipt를 포함하므로 자동 공유하지 마세요. HTML/VIEW를 따로
복사하면 원래 입력 패키지나 닫힌 출력 Manifest를 대체하지 않습니다. 업로드 기능 없음.
기존 출력·입력 내부·개발 소스 내부·symlink 경로에는 쓰지 않습니다.

## 판정과 종료 코드

리포트 생성 성공은 exit0, `REPORT_COMPLETE`입니다. 기록된 전체 판정이 ERROR나
DIFFERENT여도 exit0일 수 있습니다. 출력에 전체 판정과 회귀 판정을 함께 표시합니다.
원본 ERROR/DIFFERENT를 동일 실패 기록의 회귀 MATCH로 정상 승격하지 않습니다.
불완전하거나 모순된 입력·IO 오류는 exit2, `CAMPAIGN_REPORT_*`로 거절합니다.
초기 입력 거절은 출력을 생성하지 않습니다. 출판 중 실패는 부분 파일을 보존하지만
완료 `index.html`은 없습니다. HTML bytes를 모두 쓴 뒤 배타적 hard link로 마지막에
게시합니다. 게시 후 임시 파일 정리 오류는 경고이며 완료를 실패로 뒤집지 않습니다.
전체 디렉터리 원자성·fsync·crash 내구성·악의적 동시 writer 방어 보장은 아닙니다.

## 검증 범위

R44 V1의 루트4파일, paired run별 COMPARE.json/Manifest만 허용합니다. 최대4run,
12파일·합계32MiB·파일별16MiB, 하위 case16개·step256개, 상세256개입니다.
추가/누락 파일·디렉터리·symlink·FIFO·잘못된 hash·중복 key·비정규 JSON·NaN·
과도한 중첩·미지원 schema를 거절합니다. strict bool/int, 고정 gate/claim, 명시적
위치·source alert·부모/하위 건수·identity 플래그·보존 상세의 문맥 일관성을 검사합니다.
입력 bytes와 renderer 소스를 전후 및 최종 게시 직전에 재확인합니다.
상세 잘림에도 source/reference/batch 순서와 차이 배분을 확인합니다. R43 V1의
알려진 source metadata는 조건·판정·findings에 결속합니다. 실패한 참조 작업량은
성공 보고 step으로 세지 않으며, 미제공 reference 값의 진실을 복원하지 않습니다.

이 검사는 **보존 기록의 구조/일관성**이며, 원래 캠페인으로 비교를 재계산하거나
수치의 진실·출처·현재 source identity를 인증하지 않습니다. 해시를 일관되게 다시
만든 위조 입력은 이 범위 밖입니다. Markdown 의미·private narrative 동등성 및
미보존 상세는 확인하지 않습니다. 큰 입력의 최악 성능·모든 브라우저는 입증하지 않습니다.

표는 모바일에서 내부 가로 스크롤됩니다. 상세는 펼침 항목이며 값은 정확한 JSON
표현과 type·존재 여부로 표시합니다. missing은 present null과 다릅니다. 새 차트나
반올림·허용오차는 없습니다. index는 호출 순서이지 초·10ms·실제100Hz가 아닙니다.

## 유지 제한

리포트의 새 모델/참조 실행은0입니다. 테스트 fixture·전체 gate·CI의 합성 작업은
별도이며0이라고 주장하지 않습니다. public0.3.0 모델/원래 producer/comparator,
wheel·lock·의존성·차량 설정은 변경하지 않습니다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null. Candidate/Runtime
NO_GO, SOURCE_SCHEMA_UNQUALIFIED=6000. F61·실제 r/dt·차량 입력/활성화·
F70UH/V/F71은 허용되지 않습니다. 화면이 정상이어도 실차 자격은 바뀌지 않습니다.
