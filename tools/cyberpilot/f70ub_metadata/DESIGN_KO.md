# F70UB Static Source Boundary V1 설계

이 설계는 사용자가 승인한 source 경계 검토 초안을 구현한다. 기존 F70UB instance 게시 성공 조건과 독립적인 외부 로컬 계약 작업이다.

## 목적과 접근

정적 context metadata와 봉인된 synthetic reference 설명 정보를 구분해 검증한다. 고정 registry의 canonical payload SHA256과 일치하는 두 record만 metadata로 받아들인다. 계산기 입력이나 명령은 생성하지 않는다.

기존 reference에 production source를 추가하는 방법은 기존 봉인/입력 gate를 바꾸므로 배제한다. 새 모듈을 외부 디렉터리에 독립 구현한다. 새 숫자 평가 adapter는 별도 정책·입력 계약이 필요하므로 이 작업에 포함하지 않는다. 이 범위 선택은 기존 금지조건을 유지하기 위한 구현자의 선택이며, 새로운 r 정책 결정이 아니다.

## 입력과 출력

- 입력: `source_boundary_contract.json`과 JSON envelope의 bytes 또는 plain JSON object.
- 허용 class: `REGISTERED_STATIC_CONTEXT_METADATA`, `REGISTERED_SYNTHETIC_REFERENCE_DESCRIPTOR`.
- 각 envelope: schema_version, contract_id, source_class, record_id, payload.
- 고정 registry는 실제 정적 metadata record와 기존 tracked reference 파일 hash를 설명하는 descriptor를 지정한다.
- contract 자체도 외부 사전등록 SHA256으로 검증한다.
- 출력: metadata-only admission, record/contract hash, 기존 instance/r-budget unresolved와 F70V/F71 비허용 유지.

production/log/CAN/candidate numeric sample과 평가용 numeric vector는 새 모듈에서 수용하지 않는다. 기존 synthetic 계산기의 자체 경로는 그대로다. metadata의 hash 일치는 source/record identity 검증이며, 물리적 차량·조직 권한·metadata 진실성의 cryptographic attestation은 아니다.

## 방어와 결정론

중복 JSON key, 잘못된 UTF-8, 비정수 숫자, NaN/Inf, 비문자 key, 과도한 크기/깊이, unknown field, registry/record/contract 변조를 거부한다. parser resource bound는 계산/정책 threshold가 아니다.

core module은 표준 라이브러리만 사용하며 file/network/subprocess/Controller/Runtime/reference evaluator를 호출하지 않는다. UTF-8, sorted keys, compact JSON, 단일 LF로 canonicalize한다. wall-clock, PID, 임시 경로는 결과에 넣지 않는다.

## 검증과 한계

테스트 우선 구현, source relabel·숨긴 numeric field·승격 flag·tampered hash 거부, IO/network sentinel, 독립 2회 byte-identical 검증을 수행한다. 기존 202개 고유 테스트는 기존 exact runner/ledger로 재검증한다.

외부 설계·구현·테스트·증거 bundle을 전달한다. 원래 F70UB의 worktree/Commit/Push Gate는 미충족이므로 저장소 branch·기존 파일·CI는 변경하지 않는다. 실제 차량 instance, r, 성능, F70V/F71 상태는 승격하지 않는다.
