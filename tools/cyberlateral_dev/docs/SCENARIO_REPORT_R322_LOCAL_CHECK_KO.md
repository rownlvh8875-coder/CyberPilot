# R32.2 — 로컬 Codex용 모바일 화면 재검증 프롬프트

아래 내용을 첨부한 `F70UGZ_R322_EVIDENCE.zip`과 함께 로컬 Codex에 전달한다.
사용자의 직접 검사가 아니라 로컬 Codex의 실제 화면 검사다. 수정 후 화면 PASS는
아직 발행되지 않았다.

---

작업: R322_LOCAL_MOBILE_CHART_RECHECK

첨부 ZIP과 sidecar SHA256을 먼저 대조하라. 외부 새 evidence 폴더에만 안전하게
추출하고 CRC, 중복/경로 탈출/symlink, root 및 nested Manifest를 검산하라.
기존 저장소·원본 ZIP·리포트는 수정하지 마라. 광범위한 파일 검색은 하지 마라.
입력이 없거나 checksum이 다르면 중단하고 해당 상태를 보고하라.

검사 대상은 새 ZIP의 다음 두 파일뿐이다.

- `report-local-sign-1/index.html`
- `report-local-resumed-1/index.html`

`local-visual-input/`은 수정 전 FAIL 증거다. 수정 후 대상으로 혼동하지 마라.
새 리포트 VIEW.json은 해당 이전 리포트 VIEW와 byte-identical이어야 한다.
HTML SHA256:

- sign: `b8535cde724968f3877b83cb893ba75d9a0b4bf96db2e0ca9e9f487bbf041eea`
- resumed: `5a0b6507c26e04fd767356d85facf49fa749aa3cfbbc0a360b614b0488150122`

설치된 허용 브라우저와 기존 자동화 도구만 사용하라. 별도 새 임시 프로필에서
file://로 직접 열고 viewport1440x1250 및390x844, DPR1로 검사하라. 사용자
로그인·기존 탭/프로필은 사용하지 마라. 관리자 차단이면 즉시 BLOCKED로 중단하며
보안 설정 변경, HTTP 미러, 다른 전송 경로 등으로 우회하지 마라.

각 조합에서 실제 캡처를 만들고 직접 열어 다음을 확인하라.

1. 축 눈금·모델 호출 index 설명이 원본 크기에서 읽힌다. `.y-ticks`,
   `.x-ticks`, `.axis-caption`, `.legend`의 computed font-size와 bbox를
   기록하라.14CSS px는 구현 목표이며 실제 가독성 판정을 대체하지 않는다.
2. 축 글자가 카드·선·제목·범례와 겹치거나 잘리지 않는다. 페이지 전체 가로
   overflow가 없으며, 표의 가로 스크롤은 별도로 정상이다.
3. 그래프2개, sign 부호 전환, resumed 단일 점과 가운데 index5가 보인다.
   같은 값의 limited/final 점 겹침은 데이터와 대조해 구분하라.
4. 이전 요청/이전 출력은 별도 열이며 모든 표 셀이 VIEW와 일치한다.
   sign final=[2,-2,0,2], resumed final=-2, counter89→90, steer_request=false.
5. 범례는 항목 단위로 줄바꿈되며 단어 일부가 다음 줄로 끊기지 않는다.
6. 한글, 페이지 스크롤, 본문 제한·NOT seconds·단위 구분이 유지된다.
   내부 세로 스크롤이 없으면 NOT_APPLICABLE로 정확하게 기록하라.

desktop/mobile/mobile-charts/mobile-full/table-previous 캡처를 두 리포트에
대해 보존하라. 실제 viewport와 full-page 이미지 크기를 구분하라.
캡처를 합성·편집해 증거로 만들지 마라. 각 검사의 PASS/FAIL/BLOCKED 또는
NOT_APPLICABLE과 관찰 근거를 JSON으로 기록하고, 전후 리포트8개 파일 SHA도
대조하라. 새 외부 결과 ZIP과 Manifest 및 ZIP SHA를 만들라.
실제 화면을 확인하지 못하면 PASS를 발행하지 마라.

금지: 코드 수정, 모델/원본 계산기/F61 import·실행·compile, Controller,
Runtime, CAN, 실제 차량/주행 로그, r/dt 계산, benchmark, 설치·배포, 저장소
변경/commit/push/CI. 브라우저만 읽기 전용으로 사용하고 만든 프로세스만 종료한다.

유지: R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/vehicle scale=null,
Candidate/Runtime=NO_GO, 실제 활성화 및 F70UH/F70V/F71=NOT_ALLOWED.

최종 첫 줄은 실제 결과에 맞게 사용하라.

- `STATUS: R322_LOCAL_VISUAL_CHECK_PASS`
- `STATUS: R322_LOCAL_VISUAL_CHECK_FAIL`
- `STATUS: R322_LOCAL_VISUAL_CHECK_BLOCKED`

이는 표시 검증이며 모델 산술·물리 안전·실차 성능·배포 승인이 아니다.
