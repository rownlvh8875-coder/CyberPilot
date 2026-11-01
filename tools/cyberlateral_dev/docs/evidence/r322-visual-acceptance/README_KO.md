# R32.2 — 로컬 화면 PASS 수신·검산 기록

STATUS: R322_VISUAL_EVIDENCE_VERIFIED_PASS

R321의 모바일 축 가독성 문제 V01은 아래의 제한된 검사 범위에서 종료했다.
이 기록은 문서·PR 정리용이며 제품 코드 변경, 전체 제품 완성 또는 차량 승인이
아니다. 이전 FAIL·pre-local pending 봉인은 역사적 입력으로 수정 없이 보존한다.

## 원본 Evidence 연결

- 로컬 결과: `R322_LOCAL_VISUAL_EVIDENCE.zip`,764,328bytes.
- 결과 ZIP SHA256:
  `35ef85d36d4a0793ece24cf4417ed6e69c132a74903ab598f522c240e445cfb8`.
- 전달 kit: `R322_LOCAL_RECHECK_KIT.zip`,32,251bytes, SHA256
  `2e75a224226146d74d4067b5df57e7798d115c88c35b35e6f4e716fca07fccc0`.
- 수정 코드/봉인 기준 head: `98df520480ffc81e0ce8084f2f2dac662f20a023`.
- sign HTML SHA256:
  `b8535cde724968f3877b83cb893ba75d9a0b4bf96db2e0ca9e9f487bbf041eea`.
- resumed HTML SHA256:
  `5a0b6507c26e04fd767356d85facf49fa749aa3cfbbc0a360b614b0488150122`.

전체 ZIP·관측 JSON·캡처12개는 외부 evidence로 보존한다. 저장소에는 개인정보가
불필요하게 확대되지 않도록 아래의 보고서와 검산 영수증만 넣었다. 이 폴더는
전체 원본 ZIP의 대체본이 아니며 SHA256도 출처·OS의 인증 수단은 아니다.

## 검산 결과와 범위

- Windows Chrome156.0.8078.79, DPR1,1440x1250 및390x844.
- sign/resumed 각 두 크기,4개 case:54개 PASS·6개 NOT_APPLICABLE.
- 결과 ZIP30member CRC PASS. Manifest4개,49개 hash 항목 불일치0.
- 원래 전달 kit의15파일과 byte-identical. 리포트8파일과 이전 VIEW도 동일.
- 캡처12개 SHA·PNG 크기와 결과 metadata를 대조하고 제공된 이미지를 열었다.
  긴 전체 페이지2개는 cloud 미리보기에서 축소됐고 chart/table 캡처도 별도
  확인했다. 로컬 브라우저의 원본 크기 검사·실제 스크롤은 제공된 로컬 관찰이다.
- 다른 브라우저·font·zoom·모든 valid scenario·접근성 전체는 검증하지 않았다.
- 새 cloud 브라우저·제품·F61·Controller·Runtime·CAN·r/dt 실행은 없었다.

## 보존 파일

- [로컬 보고서 원문](LOCAL_VISUAL_CHECK_KO.md)
- [Cloud 수신·판정 영수증](CLOUD_ACCEPTANCE_RECEIPT.json)
- [ZIP/Manifest/kit 대조 영수증](INTAKE_RECEIPT.json)
- [제공 캡처 검토 기록](SCREENSHOT_REVIEW.json)
- [이 폴더의 보존 파일 체크섬](SHA256SUMS.txt)

이 JSON의 `repository_writes_this_turn=0`, Commit/Push/CI NOT_RUN은 당시 외부
수신 검산 회차의 관찰이다. 이후 현재 문서 commit/push까지 금지하거나 하지
않았다는 뜻이 아니다. 당시 원문 bytes를 유지해 이력의 구분을 보존한다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/vehicle scale=null,
Candidate/Runtime=NO_GO, 실제 활성화 및 F70UH/F70V/F71=NOT_ALLOWED를 유지한다.
