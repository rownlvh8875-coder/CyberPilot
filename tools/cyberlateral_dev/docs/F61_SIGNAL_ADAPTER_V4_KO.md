# 개발용 F61 신호 Adapter V4

`integration_tools.f61_signal_adapter_v4.adapt(payload: object) -> dict`는 기존
F70UGHR 승인 합성 참조를 DEV에 통합한 순수 함수다. 실행 CLI, 차량 reader, observer,
제어기, F61 계산기 또는 public0.3.0 wheel API가 아니다.

## Authority와 변경 범위

원본 F70UGHR ZIP SHA256:
`a2686fe18fe094ef3a9a5b452c71fd36b19f5d340e4aa90d3e95e4abfa879192`.

| 기존 봉인 member | SHA256 | 현재 위치 |
|---|---|---|
| `code/production_to_f61_adapter_v4_reference.py` | `72e660a0fdf0e8614f312320a7e7f69417cdaca12b4167d950582d95076d74fe` | `../integration_tools/f61_signal_adapter_v4.py` |
| `code/contract_data.py` | `7bbcdae97532e2122dd8477f94a9a945cc8fcb83cac952b452c69036eb05d477` | `../integration_tools/f61_signal_contract_v4.py`의 상수만 |
| `code/independent_oracle.py` | `9c36838a6a4d8ed315252d9e74beb569bd130ca7bcba1b512a5db927c92a9852` | 테스트 전용 `../project/f61_signal_oracle.py` |

위 SHA는 **기존 member**의 값이며 import 경로/서식이 바뀐 현재 파일의 SHA가 아니다.
schema/approval 문서 생성 함수는 옮기지 않았다. F61 source 원본은 수정·반입·실행하지
않고 기존 ZIP 안의 6,735 bytes와 SHA
`f343b0edd5578348c570692f05d655dee8e2b1555492a1d99b218d3f81fab035` 및 AST로 확인했다.

계약 ID는 `F70UGHR_REQUEST_TO_REQUEST_EXACT_SUBSET_V4` 그대로다.
이관은 알고리즘/API/accepted domain을 바꾸지 않는다. 원래 operational contract의
`DRAFT_NOT_APPROVED`는 유지되며 현재 통합도 실제 운용 승인이 아니다.

## 입력과 출력의 의미

입력은 closed Python dict이며 version4, contract ID, synthetic mode, source identity,
current/previous request snapshot, 두 integer now_nanos, synthetic context, reset flag가
모두 필요하다. 자세한 필드와 동작 예제는 `../project/test_f61_signal_adapter.py`의
literal counterfactual pair를 따른다. 이 fixture는 실제 관측값이 아니다.

- stage는 정수 변환·limiter 전 `CC.actuators.torque` 요청이다.
- 이전 값은 같은 stage의 바로 이전 **요청**이며 `self.apply_torque_last`가 아니다.
- native는 binary32에 정확히 포함되는 finite built-in float, [-1,1]이다.
  F61 원본의 일반 int/float domain보다 좁은 승인 합성 subset이다.
- scale1/offset0은 이미 정규화된 요청값의 identity 변환이다. 차량 정수 scale이나
  `CustomSteerMax=409`를 승인한 것이 아니다. signed zero를 보존하며 clamp/round 없음.
- LIVE/REPLAY clock은 구분하며 같은 pair에서 혼합할 수 없다. epoch와 commit도 같아야 한다.
- 두 시각 차이를 이전 시각 기준 0.0초로 옮긴다. exact binary64 초로 표현 가능한
  양수 차이만 허용한다. 예: 1,953,125ns → 1/512초. exact10ms/1ns는 거절한다.
  10ms를 실제 주기나 기본값으로 채우지 않는다.
- 이 기존 in-memory synthetic 계약은 arbitrary-size signed Python integer epoch를
  허용한다. int64-ns production validator 또는 외부 입력 resource cap을 주장하지 않는다.
- active/override/reset을 보존하지만 feasibility 평가·명령 생성은 하지 않는다.

출력 `f61_input`은 marker
`PARTIAL_ADAPTER_SIGNAL_PROJECTION_NOT_CONSTRUCTOR_ARGS`를 가진 **내부 projection**이다.
`current_native` 등은 실제 F61 constructor field명이 아니다. 원본의 필수 18개
field를 모두 갖춘 `FeasibilityInput` 객체나 `**kwargs`로 사용하지 않는다.
`calculator_invocation_allowed`는 모든 경로에서 false다.

실제 vehicle context·ACTUAL_PRODUCTION은 caller가 Gate PASS라고 선언해도 거절한다.
synthetic label은 provenance 인증이 아니며 실제 값을 synthetic으로 재라벨링하면 안 된다.
이 함수는 cooperative in-memory API이지 hostile Python 객체에 대한 보안 sandbox가 아니다.
source labels/hash는 실행 시 재인증한 배포 사실이 아니다.

## 검증과 남은 일

기존 locked venv에서 `python -B -m unittest discover -s project -p test_f61_signal_adapter.py -v`.
테스트 oracle은 별도 integer/IEEE 알고리즘으로 exact parity를 확인하며 adapter,
Fraction, 모델, F61을 import하지 않는다. 상수 데이터 공유만 허용한다.
이 검증은 합성 신호·시각 projection의 검증이며 실제 제어 응답 검증이 아니다.

synthetic time projection 연산은 NONZERO다. F61 import/compile/계산, 실제 r/dt 연산,
Controller/Runtime/CAN/차량 입력은 이 기능에서 0이며 허용되지 않는다.
전체 DEV 검증 SUMMARY의 `dt_calculations=0`에는 F61/실제 production만의 집계라는
`dt_calculation_scope`가 붙고, 합성 pair 시각 연산은 별도
`synthetic_pair_time_projections=NONZERO_NOT_AGGREGATED`로 표시한다.
`rate_budget_per_s`를 입력하면 거절한다. 정책값·기간·normalization을 기본값으로
생성하지 않는다. R_BUDGET=UNRESOLVED, Static Gate=FAIL, 실제 r/T2/scale=null,
Candidate/Runtime=NO_GO, F70UH/F70V/F71·실차 활성화 비허용을 유지한다.

다음 작업과 완료 조건은 [핵심 개발 backlog](CORE_DEVELOPMENT_BACKLOG_KO.md)에 구분했다.
