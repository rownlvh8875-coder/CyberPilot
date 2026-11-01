# R32.2 — 모바일 그래프 표시 수정

STATUS: R322_VISUAL_EVIDENCE_VERIFIED_PASS

수정 후 로컬 화면 검사와 cloud 수신 검산이 완료됐다. 아래 PASS는 두 지정
리포트의 Windows Chrome156,1440x1250·390x844,DPR1 범위에 한정된다.
[완료 근거와 원본 ZIP SHA256](evidence/r322-visual-acceptance/README_KO.md)을 참고한다.

로컬 R321 검사는 두 리포트의390px 화면에서 축 눈금·설명이 너무 작아 FAIL이었다.
제공된 ZIP SHA256은
`08f2f03b20f0148936464d75d784c66e2715982a604385f809e8df5e102241e2`로
일치했다.23개 member CRC, root/nested Manifest28항목을 검산하고 두 실제
모바일 그래프 PNG를 열어 확인했다. 기존 FAIL 증거는 수정하지 않고 보존한다.

## 원인과 변경

720-unit SVG의11-unit 글자가340CSS-px 폭으로 함께 축소되었다. 축 눈금과
설명을 SVG 밖의 일반 HTML로 옮겨14CSS px로 표시하고, 범례도14CSS px의
완전한 항목 단위로 줄바꿈한다. Y축 글자용 별도 grid 열을 예약하며 X축의
끝 눈금은 HTML 안에 둔다. resumed의 단일 index5는 가운데 한 번 표시한다.
기존 polyline/circle 좌표와 수치는 바꾸지 않고 SVG viewBox만 plot 영역으로
조정했다. JavaScript·외부 자산·새 의존성은 없다.

## 실행한 코드 검증

- 수정 전 전체498테스트 PASS. 새 회귀4개 RED 관찰 후 GREEN.
- 리포트30/30 PASS. 전체502/502 PASS, 자체 Python158개 메모리 compile.
  Ruff/Ty/Codespell PASS. 신규 테스트의 음수 float 타입 추론 지적1건은 정확한
  hex fixture로 정리했다. 리포트 실패·누락으로 숨기지 않았다.
- public wheel46,646bytes/27entries, SHA256
  `3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c`
  그대로다. frozen imported77파일 및 원래 보호 경로10개도 그대로다.
- 기존 sign/resumed를 각2회 읽는4프로세스에서 모델/native/NumPy import
  tripwire PASS. 새 reader 모델 실행0. 전체 unit/CI의 기존 합성 모델 작업은
  별도로 NONZERO이며 프로젝트 전체 계산0으로 표현하지 않는다.
- 두 VIEW.json 및 모든 series 좌표·색·단일점 속성은 첨부된 이전 로컬 증거와
  정확히 같다. 원래 입력6개 파일 hash도 그대로다. 새 HTML은 반복 생성 간
  byte-identical이고, 환경별 receipt는 다르며 그대로 보존한다.
- 기존 Python/JSON/build/lock215파일, 원래 소스10개, 원래 checkout/submodule
  HEAD/status 관찰값 불변. atomic snapshot 또는 전체 tree/OS 증명은 아니다.

독립 리뷰도 리포트30테스트와 별도4개 saved-data render를 수행했으며
Critical/Important/Minor0이었다. 새 변경 전체와 관련 branch 통합 경계를 검토한
결과이며 branch45,309추가 행 전체의 line-by-line 감사는 아니다. 별도 committed
fresh 경로에서도 전체502/502·158compile·정적 검사·wheel 검산 PASS,4회 reader의
HTML/VIEW 재현 PASS였다. 최종-head scoped CI 및 ZIP 봉인은 외부 evidence
receipt에 실제 수행 후 기록한다. 미래 결과를 미리 승인하지 않는다.

## 실제 화면 검증 완료

로컬 Codex가 수정된 두 리포트를 별도 Chrome156 프로세스에서 열어 네 화면
조합을 검사하고 캡처12개를 확인했다. 축·설명·범례의 실제 가독성, resumed
단일 점과 중앙 index5, 표 값과 실제 스크롤을 확인했다. 표 내부 세로 스크롤은
모든 행이 보이므로 NOT_APPLICABLE이며 억지로 행이나 CSS를 바꾸지 않았다.

전달된 `R322_LOCAL_VISUAL_EVIDENCE.zip`의 SHA256은
`35ef85d36d4a0793ece24cf4417ed6e69c132a74903ab598f522c240e445cfb8`이다.
cloud에서30개 member CRC,4개 Manifest의49항목을 검산했다. 전달했던15개
파일은 원래 kit과 byte-identical이고, 리포트8개 파일과 이전 VIEW도 그대로다.
결과 JSON의 체크54개 PASS·6개 NOT_APPLICABLE을 대조하고 캡처12개를 열어
확인했다. 긴 전체 페이지 미리보기2개는 도구에서 축소됐으므로 원본 PNG
크기·SHA를 별도 검산하고 chart/table viewport 캡처도 따로 확인했다.

이는 기존 DOM 검사만으로 승격한 PASS가 아니라 새 로컬 브라우저 관찰을
수신해 검산한 결과다. cloud에서 브라우저를 새로 실행하거나 관리자 차단을
우회하지 않았다. R321 FAIL과 당시 pre-local 봉인은 과거 기록으로 그대로
보존한다. 다른 브라우저·입력 전체·zoom·접근성 전체는 미검증이다.
[당시 검사 절차](SCENARIO_REPORT_R322_LOCAL_CHECK_KO.md)는 참고용으로 남긴다.

F61/Controller/Runtime/CAN/실차/r/dt/candidate 평가0. R31 생산기, reader 검증,
public API/모델/native/build/lock/workflow는 변경하지 않았다. R_BUDGET UNRESOLVED,
Static Gate FAIL, 실제 r/T2/차량 scale=null, Candidate/Runtime NO_GO 및
F70UH/F70V/F71·실제 활성화 NOT_ALLOWED를 유지한다. 기능 전체 완성·실차 안전·
성능·설치·배포 승인으로 확대하지 않는다.
