# CyberPilot 핵심 개발 기준과 남은 작업

검토 기준 main: `eed06ee21765d9f61d0691824146725c1767e18d`.
CORE1은 오프라인 개발 구분명이며 금지된 F-71 단계가 아니다.
전체 제품 요구사항 기준과 전체 완성률: **NOT_ESTABLISHED**.

## 확인된 목적과 이번 개발 선택

확인된 요청은 복구된 F61 계약을 바꾸지 않고 production 요청·이전 상태·시각을
연결하며, rate 정책과 차량 정적 근거를 분리하는 것이다. 아직 설치되지 않았다는
이유나 deployment receipt 부재로 오프라인 개발을 막지 않는다. 차량 활성화 허용과
오프라인 개발 허용은 별개다. upstream openpilot README의 기능 목록은 CyberPilot의
추가 기능 구현 증거가 아니다.

이번 작성자의 선택은 이미 승인·봉인된 합성 Adapter V4 참조를 현재 개발판으로
옮기는 것이다. 이것을 사용자가 새 제품 요구사항 전체를 확정한 것으로 표현하지
않는다. 새 인지·경로계획·학습 기능이나 기존 제어기 교체를 임의로 요구하지 않는다.

## 요구사항 ↔ 현재 코드

| 요구사항/경계 | 현재 코드 또는 원문 근거 | 확인된 범위 | 남은 것 |
|---|---|---|---|
| F61 원본/API 보존 | F70UGHR 봉인 `recovered/synthetic_rate_constraint_feasibility_v1.py` | SHA/6735bytes/18개 필수 필드, AST 확인 | 원본은 외부 근거에 보존; 현재 public 모델 API가 F61은 아님 |
| 순수 합성 명령·상태 전이 | `../src/cyberlateral_dev/api.py::step`, `../src/cyberlateral_dev/_r4/state_model.py` | 공급된 합성 상태에서 계산 | 실제 이전 적용값·소비 설정의 출처 증명 아님 |
| 입력·이전 상태 구분 | `../integration_tools/message_boundary_types.py`, `../integration_tools/owned_message_boundary.py` | 합성 요청/previous_applied 분리, 호출 순서 검사 | 실제 요청·제한 출력·현재 소비 상태의 결속 없음 |
| native 메시지 입력 | `../integration_tools/native_adapter.py::_SyntheticAdapter` | 내부 생성 binary32 합성 메시지, 제한된 native qualification | 외부 차량 메시지/실제 로그/적용 이력의 범용 reader 아님 |
| 연속 합성 상태 인계 | `../integration_tools/adapter_sequence.py` | 등록된 두 합성 시퀀스 | 임의 production stream/실제 시각 인계 없음 |
| 시나리오 실행/회귀 | `../integration_tools/scenario_input.py`, `scenario_workflow_run.py`, `scenario_campaign_run.py` | 선언 합성 입력, 모델/참조 회귀 | 호출 index를 초/10ms로 해석할 수 없음 |
| 저장 결과 설명 | `../integration_tools/scenario_report_run.py`, `scenario_trace_summary.py` | 저장 기록 일관성·표시·변화 요약 | 원본 출처/산술/차량 성능 인증 아님 |
| F61 요청 stage/previous/time projection | 새 `../integration_tools/f61_signal_adapter_v4.py::adapt` | 기존 승인 V4 합성 subset, 독립 oracle 대조 | 실제 입력·전체 F61 constructor·계산 실행은 비허용 |
| per-invocation → per-second rate 정책 | F70UGJ 원문 정책 분리; 위 adapter는 `rate_budget_per_s` 입력 거절 | rate 입력과 신호 변환 분리 | 승인된 실제 T2·scale·r 미확정 |
| 실제 연속 두 호출의 근거 | F70UGS 제한 검색 결과, F70UGZ 개발 전용 validator | 기존 검색 범위에서 완전 pair 미발견 | raw 로그 전체 부재 판정 아님; 새 관측/수집 미수행 |
| 실제 차량/배포 qualification | 기존 Gate 기록 | 오프라인 기능에서 허용하지 않음 | Static Gate FAIL; 실제 target/install/replay/성능 별도 |

단순 파일명 참조는 같은 `integration_tools` 디렉터리다. 이 표는 코드 검토 기준이지
전체 upstream tree의 정적 분석 완료나 차량 기능 시험을 뜻하지 않는다.

## 개발 순서와 각 완료 조건

| 순서 | 개발 항목 | 완료 조건 | 이번 범위 |
|---|---|---|---|
| CORE1 | 기존 V4 신호 경계의 개발판 통합 | 정확한 기존 알고리즘/승인 subset 유지, literal·독립 oracle·전체 DEV gate 검증 | f3ac2341에서 완료; 합성 범위만,927 tests는 당시 기록 |
| CORE2 | V4와 관측-record 계약의 연결 설계 | source-set별 stage/previous request/previous limited/time/flags/settings 매핑, 비호환 항목과 거절 조건 명시 | [대응 계약](F61_OBSERVATION_BINDING_CORE2_KO.md) 작성;41 leaf/35 role, bridge 미구현 |
| CORE3 | 요청 snapshot의 명시적 합성 경계 | raw 요청·active/override/reset/context 보존과 pair 인접성·시각 순서 검사 | [요청-only 구현](REQUEST_SNAPSHOT_CORE3_KO.md); 실제 source 관측·단일 read 증명·state/settings 연결은 미구현 |
| CORE4 | 요청과 분리된 제한 state·settings 선언 연결 | 이전 saved/current entry state·counter 연결, 별도 scale/read/gate 역할 보존 | [합성 연결 구현](LIMITER_SNAPSHOT_CORE4_KO.md); limiter 산술·실제 소비·모델 입력 변환은 미구현 |
| CORE5 | 현재 한 호출의 합성 모델 입력 연결 | driver·angle·modelindex·이전 정수 요청을 필수 선언, active read/override 호환 조건과 양자화 일치 검증 | [입력 준비 구현](SYNTHETIC_MODEL_INPUT_CORE5_KO.md); 상태 전이 실행·saved 출력 parity·실제 source bridge는 미구현 |
| CORE6 | 현재 선언 상태와 합성 전이 비교 | CORE5 재검증 후 한 step, 현재 post-gate saved 상태/counter exact 비교·차이 보존 | [현재 전이 검사](SYNTHETIC_TRANSITION_CORE6_KO.md); 이전 전이·prehistory·전체 output/source parity는 미검증 |
| CORE7 | 연속 선언 합성 전이 검사 | 전체 입력·명시 model index 사전 검증, 모든 인접 진단과 차이 위치 보존 | [연속 검사](SYNTHETIC_SEQUENCE_CORE7_KO.md); declared entry 유지, computed rollout/anchor prehistory/source 인증은 아님 |
| CORE8 | 고정 합성 실행·저장 CLI | 세 named fixture의 실제 실행·세 portable 파일·exit0/1/2·no overwrite | [실행 안내](CORE_SEQUENCE_CLI_CORE8_KO.md); arbitrary input reader/차량 정책/실차 권한 추가 없음 |
| CORE9 | 저장된 합성 결과 읽기 전용 조회 | captured bytes checksum·저장 스키마/행/집계 관계·JSON/Markdown·신규 모델/reference0 | [조회 안내](CORE_SEQUENCE_INSPECT_CORE9_KO.md); 저장 M/D/R 모두 조회 exit0, 산술/원본 출처/현재 소스 인증 아님 |
| CORE10 | 두 저장 패키지의 차이 위치 비교 | 양쪽 CORE9 검증 후 전체 입력/결과/identity exact-type 차이·첫256상세/전체개수·exit0/1/2 | [비교 안내](CORE_SEQUENCE_COMPARE_CORE10_KO.md); positional 비교, 신규 계산/성능/출처 인증 아님 |
| CORE11 | 고정 합성 실행·저장·조회·비교 단일 workflow | check/run 명시 분리·baseline 사전 캡처·기존 산술 재사용·작업량/저장판정/비교 분리 | [통합 안내](CORE_SEQUENCE_WORKFLOW_CORE11_KO.md); exit0은 orchestration 성공,baseline 없으면 회귀 비교 미수행 |
| CORE12 | 고정 세 case 묶음의 회귀 요약 | 전체 기준 사전 검증·고정 순서·저장판정/비교/신규·과거 작업량 집계·case별 보고 보존 | [묶음 안내](CORE_SEQUENCE_SUITE_CORE12_KO.md); check0/run6,기준 없으면 차이null,부분 실패 보존/실차 권한 추가 없음 |
| CORE13 | 기존 suite의 portable ZIP 생성·검증 | 원본9파일 보존·저장-only 요약·고정11member·외부 전체 SHA·bounded CRC/Manifest·게시 readback | [인계 안내](CORE_SEQUENCE_PORTABLE_CORE13_KO.md); 신규 모델0,추출/산술/출처 인증 없음,실차 Gate 유지 |
| CORE14 | 검증된 두 ZIP의 저장 결과 비교 | 양쪽 SHA 사전검사·role별 단일 캡처/검증·세 case INPUT/RESULT/IDENTITY 집계·상세256/case | [ZIP 비교 안내](CORE_SEQUENCE_ARCHIVE_COMPARE_CORE14_KO.md); exit0/1/2,저장 M/D/R 유지,신규 모델/추출0·출처 인증 아님 |
| CORE15 | 비교의 한국어 Markdown 요약 | 전체/CORE14상세/요약 개수 분리·case별 INPUT/RESULT/IDENTITY 합계·20/case·typed safe160자 발췌·65536bytes 한도 | [요약 안내](CORE_SEQUENCE_ARCHIVE_REPORT_CORE15_KO.md); 원문 JSON 불변·생략 명시·기존 budget 유지·browser visual PASS 아님 |
| CORE16 | ZIP 검증·비교·요약의 단일 저장 명령 | role별 단일 캡처·원문JSON/MD/체크섬3파일·exclusive/no overwrite·bounded readback·deterministic receipt | [통합 저장 안내](CORE_SEQUENCE_ARCHIVE_WORKFLOW_CORE16_KO.md); 신규 모델0·부분 실패 보존·산술/출처/차량 인증 아님 |
| CORE17 | 고정 합성 실행부터 ZIP·기준 비교까지 연결 | 기준 SHA/단일 캡처/복사 검산 후 고정6step·현재 ZIP·CORE16 요약·명시적run·부분 작업량 구분 | [실행 연결 안내](CORE_SEQUENCE_ARCHIVE_RUN_CORE17_KO.md); 기존 알고리즘 재사용·임의/차량 입력/F61 없음·실차 권한 추가 없음 |
| CORE18 | 저장 실행 폴더14파일 정합성 조회 | 양쪽 SHA 사전검사·단일캡처·suite↔현재ZIP·재생성비교↔저장JSON/MD/checksum exact·신규모델0 | [검증 안내](CORE_SEQUENCE_RUN_INSPECT_CORE18_KO.md); 조회0과저장비교0/1구분·실행/산술/출처 인증 아님 |
| CORE19 | 저장 합성 입력의 현재 의미 검증 | CORE9 단일 capture 후 exact float 복원·CORE3~5 입력 규칙 재검증·과거 판정과 분리·신규모델/reference0 | [입력 사전 검증](CORE_SEQUENCE_INPUT_PREFLIGHT_CORE19_KO.md); numeric validation 비영·산술 재실행/실제 source bridge/F61 연결 아님 |
| CORE20 | 저장 입력 사전 검증의 단일 CLI | CORE19 JSON 불변·현재 판정 exit0/1·운영 오류2·cold parser부터 bytecode 억제·cache 생성0 | [명령 안내](CORE_SEQUENCE_INPUT_PREFLIGHT_CLI_CORE20_KO.md); source/path 설정 복원·모델/F61 실행·정책값/실차 권한 추가 없음 |
| CORE21 | portable ZIP의 세 case 입력 의미 검증 | 전체 CORE13 검산 후 소유 records로 CORE19 재사용·단일 archive capture·모든 case 처리·추출/신규모델0 | [ZIP 사전 검증](CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CORE21_KO.md); 기존 폴더/CLI JSON 유지·numeric validation 비영·산술/출처/실차 인증 아님 |
| CORE22 | portable 입력 사전 검증의 단일 CLI | 전체 SHA/단일 ZIP capture·CORE21 JSON 불변·현재 판정 exit0/1·운영2·cache 생성0 | [명령 안내](CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CLI_CORE22_KO.md); cold bytecode 억제·실패 stream 처리·모델/F61/실차 권한 추가 없음 |
| CORE23 | 현재 입력 사전 검증의 한국어 Markdown 요약 | CORE21 원문 JSON 불변·모든 현재/과거 case·prefix/기록/신규 작업 분리·안전한 셀·65536bytes 한도 | [요약 안내](CORE_SEQUENCE_PREFLIGHT_REPORT_CORE23_KO.md); 단일 검산·신규모델0·시각/산술/출처/실차 인증 아님 |
| CORE24 | 한국어 입력 검증 요약의 단일 CLI | CORE23 Markdown 불변·현재 입력 exit0/1·무결성/표시/운영2·cold cache 생성0 | [명령 안내](CORE_SEQUENCE_PREFLIGHT_REPORT_CLI_CORE24_KO.md); 단일 검산·stream 실패 처리·기존 JSON CLI/계산/실차 권한 유지 |
| CORE25 | 입력 검증 JSON·요약·checksum 저장 workflow | CORE21/23 원문3파일·CORE16 exclusive/readback 재사용·NEW 외부 폴더·현재 판정0/1·운영2 | [저장 안내](CORE_SEQUENCE_PREFLIGHT_WORKFLOW_CORE25_KO.md); 덮어쓰기/자동삭제0·부분 실패 보존·신규모델/실차 권한 없음 |
| CORE26 | 저장 입력 검증 묶음과 원본 ZIP 대조 | 원본 SHA·단일 검산 후 재생성 JSON/MD/checksum exact·regular bounded capture·정합성0/오류2 | [검사 안내](CORE_SEQUENCE_PREFLIGHT_INSPECT_CORE26_KO.md); 현재 입력 판정과 구분·쓰기/추출/신규모델0·실차 권한 없음 |
| CORE27 | 순수 합성 computed-state chain | 전체 사전 검증·첫 선언 seed 이후 computed next_state만 feed·entry/output 차이 분리·모델Nstep | [연결 계산 안내](SYNTHETIC_SEQUENCE_ROLLOUT_CORE27_KO.md); CORE7 불변·anchor/prehistory/실제 native replay/차량 권한 추가 없음 |
| CORE28 | 고정 합성 rollout 명시 실행·저장 | --run 필수·고정3case·정확한 INPUT/RESULTS/checksum·CORE16 exclusive/readback·결과0/1/2 | [실행 안내](CORE_ROLLOUT_RUN_CORE28_KO.md); 실제 입력/계산식 변경 없음·부분 실패/비영 작업 구분·실차 권한 없음 |
| CORE29 | 고정 CORE28 저장 bytes 검사 | size/SHA 핀·bounded capture·JSON 해석/모델0·과거 판정과 검사 exit 분리 | [검사 안내](CORE_ROLLOUT_INSPECT_CORE29_KO.md); 현재 입력/산술/출처 인증 없음·실차 권한 없음 |
| CORE30 | 고정 rollout 전체 출력의 독립 literal 대조 | 수동 preregistered vectors·모델3/3/0·projection/trace/상태/차이위치 exact-type 비교 | [참조 대조](CORE_ROLLOUT_REFERENCE_CORE30_KO.md); 기존 CORE27 MATCH와 별도·범용 oracle/실차 인증 아님 |
| RATE | rate 정책 구현과 근거 | 승인 정책 ID·기간 의미·normalization authority·단위·비대칭 축약·no fallback 확인 | 실제 T2/scale/r은 미정; 신호 통합과 분리 |
| STATIC | 차량 정적 근거 qualification | 적용되는 platform/firmware/gateway/context 근거의 독립 authority | 오프라인 개발 선행조건 아님; 실차 사용의 별도 Gate |
| INTEGRATION | 실제 source/state/time binding | 실제 source/build/context와 완전한 연속 pair, actual consumed settings 및 요청/제한 상태 역할 검증 | 현재 미충족; 합성 label/PASS 선언으로 대신하지 않음 |
| EVALUATION | replay·차량 응답·성능·배포 검증 | 별도 승인 범위에서 실제 환경·결과·안전 한계·롤백 기준 검증 | 현재 비허용; 합성 parity로 완료 처리하지 않음 |

CORE2에서 먼저 재사용 검토할 기존 원문은 F70UGHR의
`F70UGHR_ADAPTER_V4_CONTRACT.json` 및 F70UGY/F70UGZ의 관측 schema·field inventory·
read-order/branch 규칙이다. F70UGZ checker는 이미 record/pair **합성 일관성**을
검사하므로 새로 중복 작성하지 않는다. 실제 source profile과 V4의 두 historical
commit은 자동 동치가 아니며 helper bytes 일치만으로 전체 profile을 승격하지 않는다.

CORE2 대조 결과 공통6 path를 V4의2 commit과 비교한12건은 모두 bytes가 다르고,
lateral.py는 해당 V4 archive에 없다. override/reset/request-stage active 등은 기존
record만으로 결속되지 않는다. 다음 CORE3의 counterfactual capture seam은 이 metadata를
명시적으로 공급받아야 하며 기존 관측 기록이나 V4 pin을 임의로 수정하지 않는다.

CORE3의 새 carrier는 위 누락 metadata를 **counterfactual 선언값**으로 필수 수용한다.
원래 기록의 실제 flag를 복구하거나 source 불일치를 해소한 것은 아니다. 다음 개발
경계인 CORE4는 요청과 다른 역할의 제한 state·소비 settings를 별도 소유 carrier로
선언하고 pair 연결을 검사한다. 실제 Controller 계측이나 차량 실행과는 구분한다.
CORE5는 driver·angle·이전 정수 요청·model index를 별도로 공급받아 기존 합성 모델의
현재 입력 구조를 만든다. 한 frame의 두 active read가 다르거나 override가 true이면
거절한다. 기존 CORE4 pair 수용만으로 모델 호환성은 생기지 않으며, CORE5 수용도
declared saved 출력과의 산술 parity나 실제 소비 설정을 해결하지 않는다.
CORE6는 준비된 현재 입력으로 합성 모델 한 step을 실행하고 현재 선언된 saved 명령과
counter를 exact 비교한다. 차이는 덮어쓰지 않고 DIFFERENT로 보존한다. MATCH도 이전
전이·prehistory·전체 output/source parity는 입증하지 않는다. CORE7는 각 호출 문맥을
명시적으로 공급받아 전체 입력을 먼저 검증하고 모든 인접 전이를 검사한다. 차이가 나도
선언 상태를 고치지 않으며 다음 진단을 생략하지 않는다. 첫 anchor 전이·prehistory와
실제 source qualification은 미해결이다. CORE8은 고정 정상/불일치/사전 거절 예제를
명령 한 번으로 실행하고 INPUT/RESULTS/체크섬을 새 외부 폴더에 보존한다. 임의 입력이나
차량 데이터 reader는 열지 않았으며 source 관찰과 실제 차량 authority를 구별한다.

## 종료/성공 판정

- CORE1 성공은 신호 경계의 합성 개발 기능 완료이지 production binding 완료가 아니다.
- CORE2/CORE3도 실제 입력·차량 사용 권한을 발행하지 않는다.
- F61 계산을 열려면 별도 calculator invocation 전제조건과 승인 정책/근거가 필요하다.
- 실제 활성화는 Adapter 실제 binding, Rate Policy, Static Evidence 세 Gate 모두의
  적합 판정이 필요하다. 현재 합성 PASS만으로는 어느 것도 우회하지 않는다.

현재 유지: R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, F70UH/F70V/F71 및 실차 활성화=NOT_ALLOWED.
