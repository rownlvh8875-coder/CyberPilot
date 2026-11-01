# R34 — 로컬 구현 검증 기록

R34는 [저장된 합성 batch 비교 도구](SCENARIO_REGRESSION_R34_KO.md)입니다.
전체 CyberPilot 완성, 독립 산술 증명, 실제 후보/차량/배포 승인이 아닙니다.

## 수행한 검증

- 변경 전 기본 suite523 tests PASS.
- 신규33 tests: owned input10, exact comparison13, real CLI10. 기능 부재의
  RED를 확인한 뒤 구현했고, root producer identity 보완2건도 RED→GREEN으로
  확인했습니다. 기존 R31/R32와 공개 계산 모듈 회귀를 포함한 전체556 tests PASS.
- Ruff·Ty·Codespell, 자체 Python172파일 compile PASS. 원본 Controller/schema
  executable compile0. 새 dependency나 타입 검사 ignore는 추가하지 않았습니다.
- imported77파일의 봉인 identity 불변. 공개 wheel 두 번 빌드·설치 검증 PASS,
  두 bytes 동일,46,646bytes/27entries, SHA256
  `3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c`.
- 실제 보존한 완전한 R33 batch 두 개를 새 CLI로 독립2회 비교했습니다.
  각 MATCH, 동일 입력 sample5개, 차이0개, 비교기의 새 모델 실행0회.
- 두 회차 `COMPARE.json` SHA256은
  `b48792ab2a140f5605aff8eaaf2c4a0475ae5093a19d575d4876e8c78a1414db`,
  `SUMMARY_KO.md` SHA256은
  `52aeb259ab9a4300504f06d317e764fa7725cd2947b18fb682a62b03f8cf567b`로
  각각 byte-identical입니다. private receipt/전체 Manifest는 출력 경로에 따라
  달라지므로 전체4파일이 byte-identical이라고 표현하지 않습니다.
- 별도의 명시적 변형 fixture에서 index1의 limited_command를 -2→-3으로
  바꾸고 저장 중복 투영/체크섬을 갱신했습니다. 비교는 DIFFERENT, 정확한 해당
  field/값을 보고했습니다. 이는 의도적으로 변형한 저장 기록이며 새 모델 계산이나
  올바른 수치 결과로 제시한 자료가 아닙니다.
- fresh isolated CLI에서 모델/native import를 차단해도 비교가 완료됐습니다.
  입력 파일 전후 bytes, 출력 전체 Manifest, 경로 이동 후 portable 일치,
  늦은 손상·누락·추가·symlink/FIFO·출력 충돌·부분 쓰기 거부를 검사했습니다.

비교기 실행0과 전체 작업의 실행량을 혼동하지 않습니다. unit test와 기존
전체 개발 gate는 기존 합성 모델 작업을 수행했습니다. 전체 작업의 합성 모델
호출 총계는 별도로 집계하지 않았으며0으로 보고하지 않습니다.

## 범위와 남는 제한

검증은 로컬 개발 소스/환경의 제한된 synthetic 동작입니다. GitHub CI 실행,
main 병합, 노트북 실행 또는 브라우저 화면 검증으로 승격하지 않습니다.
이번 기능은 새 HTML을 만들지 않으며 기존 R33/R32 화면을 수정하지 않았습니다.

MATCH는 저장된 수치/거절 기록의 정확 일치입니다. 코드 identity의 변화는
별도 표시하고, missing bytes는 verified match로 간주하지 않습니다. baseline의
올바름·출처를 인증하거나 모든 미래 모델 버전/입력에 대한 적격성을 보장하지 않습니다.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/vehicle scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.
실차 입력/활성화·F61·r/dt·Controller/Runtime/CAN 실행은 없습니다.
