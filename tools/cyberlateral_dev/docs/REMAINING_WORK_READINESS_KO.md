# CORE38 — 오프라인 전달과 남은 실제 사용 작업

2026-11-11 Asia/Seoul. 개발판 정리와 실제 차량 qualification은 별개다.
설치되지 않았다는 사실이나 deployment receipt 부재로 오프라인 개발을 막지 않는다.
반대로 합성 테스트 PASS가 실제 source/state/time·정책·차량 근거를 대신하지 않는다.

## 이번 정리

CORE37 M1의 assertion 진단을 보강했다. sample_index/field와 prefix_end를
표시하되 기존 기대값·assertion 순서·fail-fast·subTest 흐름은 유지한다.
실제 합성 결과 사본의 fault_condition/counter를 잘못 바꾼2개 회귀 테스트는
기존 helper에서 실패하고 메시지 보완 후 통과한다. Runtime/API/계산식·수동
fixture/cut·wheel·F61 계약은 변경하지 않는다. 전체 DEV와 이전 정상 관측 해시의
실제 실행 결과는 별도 evidence에 보존한다.

## 남은 단계의 진입 조건

| 순서 | 현재 판정 | 다음에 필요한 것 |
|---|---|---|
| GitHub 전달 | 검증된 새 브랜치 push와 명시적 오프라인 CI 대상 | 최종 검증 HEAD와 원격 HEAD 일치·해당 CI의 terminal 결과 |
| PR/main 통합 | upstream 전체 빌드 CI 범위 때문에 보류 | 오프라인 변경에 적용할 CI 범위를 별도로 정리;기존 checks 우회 금지 |
| 실제 production binding | BLOCKED | 같은 실행의 인접 요청2개,별도 이전 applied/limited/gated 상태,실제 소비 설정,source/build/epoch,apply 시각·순서 |
| 실제 numeric rate policy | BLOCKED | 명시적으로 승인된 exact tau_policy,qualified S_prev/S_cur,driver/history/capacity/gating 문맥 |
| 차량 정적 qualification | FAIL 유지 | 적용 차량의 독립 platform/firmware/gateway/context authority |
| F61 연결·실제 평가 | NOT_ALLOWED | 실제 binding·rate·static Gate와 별도 calculator invocation 전제조건 |
| 설치·배포 | NOT_ALLOWED | 앞선 Gate PASS,실제 replay/응답/성능 검증,정확한 설치 대상/build·시험 범위·롤백 |

새로운 실제 입력이 공급되지 않았으므로 이 문서는 근거가 없는 단계를 실행한
것이 아니다. 필요한 자료를 기존 기록 또는 별도로 범위를 정한 수집 설계로
확보해야 한다. raw 로그 디코드,차량 연결,Controller 계측·실행은 이번 범위가 아니다.

## 대조한 기존 근거와 그 한계

- F70UGJ 대화 승인 R2:정책 정의와 T2 **개념**은 승인됐으나 실제 기간·scale·r
  숫자 승인 flag는 false다. 현재 GitHub 쓰기 권한 확인은 과거 차량/Owner
  attestation을 소급해서 증명하지 않는다.
- F70UGK symbolic readiness와 synthetic numeric subset readiness:합성 정의·참조
  검증이 존재하지만 actual_numeric_r/scale/policy_period는 null이다.
- F70UGM cloud intake:설정 백업409/DELTA4/6/LC0과 CP/log metadata는 부분 근거다.
  실제 같은 호출에서 소비됐다는 증거나 현재 T2 기간 승인으로 승격하지 않는다.
- F70UGS bounded notebook-search report:당시 검색 범위에서 완전한 연속 pair를
  찾지 못했다. 모든 노트북/로그에 없다는 뜻도,이번에 노트북을 새로 검색했다는
  뜻도 아니다. 기존 검색을 무차별 반복하지 않는다.

이 정확한5개 기록의 bytes/크기/SHA와 읽기 범위를 별도 intake receipt에 남긴다.
현재 actual r/T2/scale은 모두 null이다. DT_CTRL=0.01,backup409,합성 test 값을
실제 정책 숫자로 채우거나 r=0 fallback을 만들지 않는다.

## GitHub/CI 경계

시작 시 원격 main은 eed06ee21765d9f61d0691824146725c1767e18d이고 CORE1~37의
91commits/218files가 로컬에만 있었다. 변경은 오프라인 component와 plan 문서다.
CORE38은 여기에 진단·readiness 정리를 추가한다. 변경량이나 테스트 수는 전체
제품 완성률이 아니다. 최신 원격 상태/실제 전달 결과는 별도 receipt를 기준으로 한다.

새 브랜치는 fix/core38-offline-release-readiness다. 이 브랜치 push에 해당하는
현재 YAML push trigger는 없고,기존 cyberlateral-dev.yaml/cloud.yaml의 명시적
workflow_dispatch만 선택한다. PR을 열면 활성 tests.yaml의 upstream openpilot
전체 빌드·테스트도 실행되므로 현재는 PR/main 통합을 보류한다. 이 경계를 해결하려고
workflow를 끄거나 수정하거나 skip-ci/force push를 하지 않는다. 관계없는 PR1도
수정하지 않는다. 외부 webhook 전체의 동작까지 검증했다고 주장하지 않는다.

유지:R_BUDGET=UNRESOLVED,StaticGate=FAIL,SOURCE_SCHEMA_UNQUALIFIED=6000,
Candidate/Runtime=NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71·실차 활성화 NOT_ALLOWED.
