# R33 · 로컬 화면 증거 수신·검산 기록

STATUS: R33_LOCAL_VISUAL_EVIDENCE_VERIFIED_PASS

이 폴더는 지정된 정적 화면의 검증 완료 기록입니다. 캡처·원본 ZIP은 외부에
보존하고 저장소에는 개인 경로를 확대하지 않는 보고서·영수증·해시만 넣었습니다.
전체 evidence의 대체본이나 출처/OS 인증 자료가 아니며 차량 승인이 아닙니다.

## 원본 연결

- 구현 기준 commit: `3783461edcf0fa921adab92c8d1959c5a7262ebb`.
- 입력: `R33_LOCAL_VISUAL_KIT.zip`,78,559bytes/60member, SHA256
  `8e1ac69e16e0ef164f401d73abd2d1bc5b55956755bc79f7dfb17f60824e2d28`.
- 로컬 결과: `R33_LOCAL_VISUAL_EVIDENCE.zip`,1,418,409bytes/24member, SHA256
  `73ad2c415bbaded1933a043fc79ed51b08af83e21dd9a9a2abc13c7043d9890b`.
- 결과 CRC와23개 Manifest 항목 PASS. 원본 input의13개 Manifest/중복 포함
 165개 hash 항목,60파일 before/after 및5개 대상 HTML SHA가 일치합니다.
-10개 case의 체크는 PASS85/N/A45, 미확인 필수 항목0입니다.
- 캡처20개(고유 PNG bytes SHA18개), 실제 report 탐색6회와 링크48개 record를
  대조했습니다.20개 PNG를 cloud에서도 직접 열어 눈에 띄는 문제를 발견하지 못했습니다.

## 보존 파일

- [로컬 보고서 원문](LOCAL_VISUAL_CHECK_KO.md)
- [Cloud 판정 영수증](CLOUD_ACCEPTANCE_RECEIPT.json)
- [결과 ZIP/Manifest 수신 영수증](INTAKE_RECEIPT.json)
- [캡처별 SHA·크기와 검토 범위](SCREENSHOT_REVIEW.json)
- [이 폴더의 보존 파일 검산](SHA256SUMS.txt)

로컬 보고서 원문은 bytes를 보존했습니다. JSON 영수증은 이전 수신 회차에서
검증한 구조를 저장소용으로 다시 직렬화했으며 metadata 사실은 바꾸지 않았습니다.
캡처 해시/크기는 원본 PNG를 연결하지만 캡처 생성 이벤트 자체의 독립 증명은 아닙니다.

Cloud 영수증의 repository_changes0, PR_updates/Commit/Push/CI/main_merge NOT_RUN
등은 **당시 외부 evidence 수신 회차**의 관찰입니다. 이후 현재 문서 commit/push를
하지 않았다는 뜻이 아닙니다. 이 구분은 원래 회차의 주장을 현재 회차로 넓히지 않기 위함입니다.

검사 환경은 Windows Chrome156/DPR1·zoom100%,1440×1250 및390×844입니다.
다른 환경/임의 시나리오나 제품 계산을 재검증한 것이 아닙니다. cloud 브라우저
정책 차단은 우회하지 않았고 제공된 PNG·기록만 검토했습니다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/vehicle scale=null,
Candidate/Runtime NO_GO, 실제 활성화/F70UH/F70V/F71 NOT_ALLOWED 유지.
