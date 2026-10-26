# F-64 봉인 자료 검증

최종 상태는 F64_HOLDOUT_FAIL이다. 실패를 고치거나 seed를 고르는 재실행 절차가 아니다.

- 원본 브랜치588d6b21c21089065a7d9165d6e7a438e8aa6297과 격리 branch의 pre-holdoutce8360d561cf85433fa2df072059c2bf887ee5b6를 구분한다.
- 원본308개 보호 파일은 공개 before/after 해시 receipt 및 별도 비공개 local audit로 결속했다. 원본 RLOG·비공개 데이터는 전달물에 없다.
- Source/tests/contracts/dependencies53파일은 pre_holdout_source_manifest.json과 Git pre-commit blobs로 검사한다.
- F64_FILE_MANIFEST.json의 각 payload bytes/SHA256, ZIP CRC·중복·경로 탈출·Symlink·정확한 멤버 집합을 확인한다.
- ZIP에는 ZIP 자신·ZIP SHA 파일·최종 해시 기입본 보고서·외부 seal을 넣지 않는다.
- ZIP metadata는1980-01-01 00:00:00, regular0644, 정렬된 ASCII 경로, DEFLATE9로 고정했다.
- 새로 metric/holdout을 평가할 필요 없이 이미 봉인된 두 실행의 fixture/metric/Manifest 바이트를 비교할 수 있다.
- 공개 unit test 검증 명령은 checkout에서 python3.12 -B -m tools.cyberpilot.f64.entry --tests 이다. 이는 Controller 없이 공개 테스트만 실행한다.
- 이번 adjudication은 pre-holdout commit에서 파생한2seed,2preplanned reproduction pass,1combined verdict였고 결과 확인 이후 재시도/수정하지 않았다.
- 후속 artifact integrity 검산은 평가 재시도나 새로운 성능 연구로 표시하지 않는다.
- R_BUDGET_UNRESOLVED, SOURCE_SCHEMA_UNQUALIFIED6000 및 모든 기존 no-go 상태를 보존한다.
