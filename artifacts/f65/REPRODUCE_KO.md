# F-65 검증 절차
상태는 Source-only partial pass이며 r/후보/Runtime은 미적격 상태다.
PRE_HOLDOUT_COMMIT=687d0efe213b3825993cf48849a8a6dab0584364.
기존 로컬 Repository의 해당 Commit과 최종 증거 Commit을 사용한다. GitHub에는 Push하지 않았으므로 원격에 있다고 가정하지 않는다.

- Source Manifest136파일의 실제 bytes/SHA 및 Git pre-commit blob를 확인한다.
- protected_before/after JSON 및 sha256 텍스트가 동일한지 확인한다. 원본413파일은 별도 로컬 자료이며 전달 ZIP에 원시 자료를 올리지 않는다.
- 공개 테스트: python3.12 -B -m tools.cyberpilot.run_f65_source_separation_v1 --tests
- 기존 F64 공개 회귀: python3.12 -B -m tools.cyberpilot.f64.entry --tests
- 봉인 bundle 검증: python3.12 -B -m tools.cyberpilot.run_f65_source_separation_v1 --verify-bundle artifacts/f65/evaluation
마지막 명령은 고정된 Source/지표의 무결성 재현이며 새로운 seed 선택이나 adaptive evaluation이 아니다. 실제 차량/Controller/RLOG는 사용하지 않는다.
- status 실패를 넣으면 CLI는 nonzero여야 한다. 이전 F64_HOLDOUT_FAIL을 성공으로 변환하면 안 된다.
- FILE_MANIFEST.json은 ZIP 내부 상대경로 기준이다. source_snapshot은 검토용 코드와 pin이며 완전한 Git clone이 아니다; Git proof에는 기존 Repository history/보호 baseline이 필요하다.
- ZIP CRC·멤버 집합·경로 탈출·symlink·파일별 크기/SHA를 검증한다. ZIP 생성순서 정렬, timestamp1980-01-01, regular0644, DEFLATE9.
- ZIP 자신·ZIP SHA 파일·해시가 기입된 최종 보고서/seal은 순환 참조 방지를 위해 ZIP 외부에 있다.
- SOURCE_SCHEMA_UNQUALIFIED6000, D2/F19/native-exact/runtime 판정은 유지한다.
