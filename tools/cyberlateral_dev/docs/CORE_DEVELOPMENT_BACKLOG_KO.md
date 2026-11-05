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
| CORE1 | 기존 V4 신호 경계의 개발판 통합 | 정확한 기존 알고리즘/승인 subset 유지, literal·독립 oracle·전체 DEV gate 검증 | 구현 및 검증 대상 |
| CORE2 | V4와 관측-record 계약의 연결 설계 | source-set별 stage/previous request/previous limited/time/flags/settings 매핑, 비호환 항목과 거절 조건 명시 | 다음 우선 작업; 임의 실제 reader를 먼저 만들지 않음 |
| CORE3 | source-bound 오프라인 관측 seam | 한 번 소비된 값을 추가 reread 없이 보존하는 순수 seam을 합성 counterfactual로 검증, reset/loss/epoch 경계 명시 | CORE2 이후; Controller 실행·CAN·실차 capture 없음 |
| RATE | rate 정책 구현과 근거 | 승인 정책 ID·기간 의미·normalization authority·단위·비대칭 축약·no fallback 확인 | 실제 T2/scale/r은 미정; 신호 통합과 분리 |
| STATIC | 차량 정적 근거 qualification | 적용되는 platform/firmware/gateway/context 근거의 독립 authority | 오프라인 개발 선행조건 아님; 실차 사용의 별도 Gate |
| INTEGRATION | 실제 source/state/time binding | 실제 source/build/context와 완전한 연속 pair, actual consumed settings 및 요청/제한 상태 역할 검증 | 현재 미충족; 합성 label/PASS 선언으로 대신하지 않음 |
| EVALUATION | replay·차량 응답·성능·배포 검증 | 별도 승인 범위에서 실제 환경·결과·안전 한계·롤백 기준 검증 | 현재 비허용; 합성 parity로 완료 처리하지 않음 |

CORE2에서 먼저 재사용 검토할 기존 원문은 F70UGHR의
`F70UGHR_ADAPTER_V4_CONTRACT.json` 및 F70UGY/F70UGZ의 관측 schema·field inventory·
read-order/branch 규칙이다. F70UGZ checker는 이미 record/pair **합성 일관성**을
검사하므로 새로 중복 작성하지 않는다. 실제 source profile과 V4의 두 historical
commit은 자동 동치가 아니며 helper bytes 일치만으로 전체 profile을 승격하지 않는다.

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
