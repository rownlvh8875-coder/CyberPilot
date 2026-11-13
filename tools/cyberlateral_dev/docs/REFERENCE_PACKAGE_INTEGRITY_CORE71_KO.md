# CORE71 — 저장 참조 패키지의 무결성 조회

[CORE70](RECORDING_REFERENCE_WORKFLOW_CORE70_KO.md)가 저장한 정확한 세 파일을
모델·참조 재실행 없이 검산한다. 외부 Manifest SHA로 JSON과 한국어 요약을 함께
고정하며,파일 배치·크기·정규 JSON·UTF8·필수 제한 상태를 확인한다.

## 사용

`tools/cyberlateral_dev`에서 실행한다. CORE70 가이드의 출력 폴더와 해당 실행의
stdout 저장 영수증이 필요하다. 영수증의 `files["SHA256SUMS.txt"]["sha256"]` 값을
신뢰할 전달 경로로 확보해 expected 값으로 사용한다.

```bash
.venv/bin/python -B tools/reference_package_inspect.py \
  --input-root /absolute/external/reference_report \
  --expected-manifest-sha256 "$CORE70_EXPECTED_MANIFEST_SHA256"
```

위 경로와 변수는 실제 출력·전달받은 SHA로 공급한다. 현재 파일의 SHA를 직접
계산해 자신과 비교하면 원래 전달본임을 입증하지 못한다. JSON SHA만 고정하면
요약과 Manifest 교체를 막지 못하므로 이 명령은 Manifest 자체의 외부 SHA를 받는다.

성공 stdout은 CORE71_REFERENCE_PACKAGE_INTEGRITY_INSPECTION_V1 canonical JSON이다.
세 파일의 캡처 SHA/크기,Manifest SHA,검사 범위·제한 상태를 보고한다. 저장된
audit가 MATCH인지 DIFFERENT인지와 무관하게 **무결성 조회 성공은 exit0**이다.
손상·형식·사용법·운영·출력 실패는 exit2이며 성공 영수증이 아니다.

## 무엇을 확인하는가

- 정확히 REFERENCE_AUDIT.json/SUMMARY_KO.md/SHA256SUMS.txt 세 regular 파일.
- JSON1..2097152bytes,요약1..65536bytes,Manifest1..512bytes의 단일 bounded 캡처.
- 외부 Manifest SHA,정확한 두 sorted checksum 행,캡처 JSON·요약의 SHA.
- canonical JSON object,CORE69 schema_version1/contract_id/scope,최상위 여섯 권한False,
  최상위 GATES가 기존 GATES와 같은 제한 상태. 요약은 strict UTF8 text.

`envelope_validation=CORE69_IDENTIFICATION_AND_CLOSED_AUTHORITY_FLAGS_ONLY`다.
다른 body 필드·추가 key는 의미를 검증하지 않는다. 저장 행·audit 판정·과거 작업량·
source identity를 현재 검사 결과의 신뢰 필드로 복사하지 않는다. 요약의 뜻이 JSON과
같은지도 검사하지 않으므로 `audit_semantics_validated=False`,
`summary_consistency_checked=False`,`recorded_work_counts_validated=False`를 명시한다.

무결성이 맞는 자료에도 잘못된 주장이 담길 수 있다. 이 명령은 데이터 repair,
모델/참조 검산,원본 입력 확인,source/build 출처 인증이나 차량 승인 명령이 아니다.
기존 [CORE69 실제 참조 검사](RECORDING_DIAGNOSTICS_REFERENCE_CORE69_KO.md)의 역할은
별도로 유지한다. 이 조회는 새로운 모델0/reference0이고 원본 producer의 작업은
별개의 과거 사실이다. 무결성·형식 검산 자체의 작업은 비영이다.

## 파일·실패 경계

SHA 문법을 caller path보다 먼저 확인한다. 기존 read-only capture helper를 사용해
각 파일을 한 번씩 읽고 before/after layout·root inode를 확인한다. 모든 descriptor를
닫은 뒤 캡처 bytes를 검사한다. symlink/ancestor symlink·FIFO·directory·extra/missing
파일은 거절하며,검사 후 path가 바뀌어도 이미 캡처한 bytes로 판정한다. atomic한
hostile filesystem snapshot이나 이후 path 내용의 보증은 아니다.

파일 쓰기·cache/temp·추출·subprocess·모델/helper/checker 실행은 없다. 알고리즘
모듈이나 NumPy 없이 cold `-S`에서도 조회할 수 있다. CLI는 위 두 flag 각각1회만
받고 --run/축약/중복/r/dt/context override를 거절한다. 도움말·사용법 검사는 project
import 전이다. path/bytecode 설정을 복원하고 전체 stdout16384bytes 이하를 만든 뒤
쓴다. positive short write는 완료하고 오류에는 재시도하지 않는다. exit2의 일부
stdout prefix는 유효한 성공 영수증이 아니다.

CORE71은 오프라인 개발 번호이며 **F-71 실차 단계 승인과 다르다**.
R_BUDGET=UNRESOLVED,Static Gate=FAIL,실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED,NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/F70V/F71·실차 활성화
NOT_ALLOWED 유지. 실제 Controller/Runtime/CAN/F61/차량 input·capture/actual r·dt/
install/deploy0. fixture 생성과 전체 unit/gate 합성 작업은 비영·미집계다.
