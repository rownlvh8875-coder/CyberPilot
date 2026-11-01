# R33 · 일괄 실행 기능과 제한된 화면 검증

STATUS: R33_LOCAL_VISUAL_EVIDENCE_VERIFIED_PASS

R33의 실제 화면 검사 대기 항목은 지정된5페이지/두 viewport 범위에서
해소됐습니다. 공개0.3.0 계산 모듈/API/wheel은 그대로이며, 전체 CyberPilot
완성·실차 설치·물리 안전·성능·production 적격성 승인이 아닙니다.

## 구분되는 검증

- 구현 기준 commit: `3783461edcf0fa921adab92c8d1959c5a7262ebb`.
- 해당 구현의 과거 전체 검증:523 tests, Ruff/Ty/Codespell 및164 own compiles
  PASS. 원래 검증은 [CI41293956477](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/41293956477)에 연결됩니다.
- wheel은46,646bytes/27entries, SHA256
  `3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c`.
- 로컬 화면 검사는 별도 회차입니다. 모델·F61·r/dt·기존 테스트를 재실행하지
  않고 저장된 HTML과 기록만 확인했습니다. 과거 테스트/CI/R32.2 PASS를
  이번 화면 PASS로 승격하지 않았습니다.
- 이 문서 정리 회차의 회귀 검증·CI는 별도입니다. PR의 현재 head에 연결된
  결과를 확인하며 과거 CI를 새 head의 실행 결과라고 표현하지 않습니다.

## 실제 화면 검증 범위

Windows10.0.26300, Chrome156.0.8078.79, Playwright Core1.62.1에서
1440×1250·390×844, DPR1, zoom100%로 검사했습니다. 범위는 성공 목록,
일부 거절 목록, 전체 거절 목록, sign/resumed 개별 보고서입니다.

-5페이지×2크기=10개 case. 필수 항목 미확인0, PASS85/N/A45(사유 포함).
- 실제 캡처20개를 로컬에서 직접 열고, cloud에서도 제공된20파일을 열었습니다.
  고유 PNG SHA는18개이며 desktop success/rejected의 full/focus는 각각
  문서 전체가 화면 안에 들어와 동일합니다.20개가 모두 다른 장면이라는 뜻은 아닙니다.
- 로컬 실제 report 탐색6회, 로컬 링크48회. cloud는 제공된 탐색 record와
  연결 파일의 SHA를 대조했으며 브라우저 탐색을 재실행하지 않았습니다.
- 한글·긴 파일명/SHA 줄바꿈·상태·거절 코드·그래프 축/범례·표/스크롤과
  제한 문구를 확인했습니다. resumed의 단일 sample은 index5이며 실제 초가 아닙니다.
- 전달 input60파일의 로컬 전후 SHA·크기·집합이 cloud 전달 bytes와 일치합니다.
  이는 로컬 관찰과 보존 자료의 일관성이며 atomic snapshot/OS 인증은 아닙니다.

## 근거와 남는 경계

[로컬 보고서·cloud 영수증·캡처 해시·Manifest](evidence/r33-visual-acceptance/README_KO.md)를
보존합니다. 원본 ZIP/PNG 전체는 외부 evidence에 있고 저장소에는 넣지 않았습니다.
다른 OS/브라우저/font/DPR/zoom, 모든 허용 입력, 접근성 전체는 검증하지 않았습니다.
향후 renderer·입력·표시 규칙이 바뀌면 이 PASS를 새 화면에 자동 적용하지 않습니다.

R_BUDGET=UNRESOLVED, Static Evidence Gate=FAIL, actual r/T2/vehicle scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO,
D2 PERFORMANCE_NOT_EVALUATED, F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN, 실제 활성화/F70UH/F70V/F71 NOT_ALLOWED 유지.
이 결과로 main 병합이나 차량 사용을 자동 승인하지 않습니다.
