# V4 E2 Stage2 수치 동등성 원인 분석

같은 행을 계산해도 행렬곱을 호출하는 배치 구성이 다르면 부동소수점 마지막 비트가 달라질 수 있다. 고정 합성 자료에서 이를 재현했다. 실제 Fold B 원인 판정은 별도로 승인된 한 TRAIN job 진단 결과와 구분한다. D2 성능은 평가하지 않았고 기존 E2 실패 판정은 그대로다.

## Identity / purpose / scope

Cyber Validation의 독립 진단 도구다. 저장소 `rownlvh8875-coder/CyberPilot`, 브랜치 `feature/cyber-autotune`, baseline `7adba76d5b1400f35fbd03c420e5f331cf0c7272`, original V4 execution `bd8045ef2a0da62a92603439f38e7740f5923622`를 기준으로 한다. 기존 executor/model/controller/acceptance/workflow를 변경하지 않는다. 차량 적용 권한은 없다. 원본 소스의 라이선스/attribution과 submodule gitlinks를 보존한다.

## 원래 D0와 세 경로

- 원래 `empirical_hurdle_v4_execution.integrated`와 `empirical_hurdle_fit_cv_math.integrated`: 전체 one-step population에서 gate가 선택한 행을 원래 순서로 모은 뒤 한 번 `predict_delta(x[gate])`를 호출한다.
- A: E2의 원래 segment/order 512행 단위 전체 행 cache. B: 같은 chunk의 D0 선택 행만 계산. C: 원래 D0의 전체 job 선택 행 계산. 추가 대조는 전체 job의 모든 행 계산이다.
- 입력은 float64/C-order다. `empirical_s2_ri_fit_cv_math.transform`은 행별 고정 mean/std 변환 후 C-order `z`를 만들고, `predict_delta`가 `z @ coefficients`를 계산한다. 행 순서·변환 결과·출력을 각각 검사한다.
- 기존 Fold B는 B/A에서 중단되어 C/A에 도달하지 못했다. 이 과거 사실을 C/A 실패로 해석하지 않는다.

B/A 일치는 C/A 일치에 **추가된** 계약이다. 두 조건이 논리적으로 동치인 것은 아니다. B/A를 삭제하거나 완화하지 않았다.

## 사전 고정 synthetic evidence

Seed 20261018, L=1/5/15/45, 차원 5/13/33/93, 1537행, 512행 chunk, 세 계수 scale, 다섯 mask를 고정했다. 중복/근접한 값, 양수/음수, 한 행 tail을 포함한다. 원래 60개 중 35개는 auxiliary whole-job 비교에서 달랐고 B/A는 모두 같았다. 이를 실제 Fold B 재현으로 주장하지 않았다.

후속 실험은 원래 자료/seed를 유지하고 full chunk 첫 mask bit만 뒤집는 60개 대조를 실행 전에 고정했다. 이 중 44개에서 B/A 차이가 발생했다. 64바이트 정렬을 동일하게 통제한 행렬/계수 대조에서도 44개였다. 변환 행은 모두 byte-exact, B/A 최대 차이는 80 ULP, projected tick 차이는 0이었다. 별도의 합성 반올림 경계 테스트에서는 1 ULP 차이로 tick이 바뀔 수 있음을 확인했다. 작은 차이도 byte 검사는 FAIL이다.

Python 3.12.13 / NumPy 2.5.3 / x86_64 / OpenBLAS 0.3.34.106.0, single-thread 설정이다. 자세한 공개 요약은 [synthetic JSON](empirical-hurdle-stage1-v4-e2-numerical-synthetic.json)에 있다. 특정 BLAS kernel의 내부 명령 순서는 추적하지 않았다. backend 설정만으로 실제 사용 kernel이나 FMA 부재를 증명하지 않는다.

## 실제 Fold B 진단

PRE_EXECUTION_PENDING. 정확한 private handoff, 한 job의 TRAIN source/member allowlist, 두 독립 리뷰 및 사전 exact-head CI를 확인한 뒤 별도 1회 진단한다. 기존 실패 실행은 resume하지 않는다. DEV, mixed TRAIN receipt, private 원본 threshold, D2 selector에는 접근하지 않는다. 상세 수치/행/경로/계수는 공개하지 않는다.

## 수정 방향의 판정

| 방법 | 원래 D0 의미와의 관계 | 이번 결정 |
| --- | --- | --- |
| A. 기존 byte-exact 유지 | original whole-job selected-row 호출을 보존해야 한다. 모든 배치의 동일 결과를 현재 NumPy/BLAS 식만으로 보장할 근거는 없다. | 구현/채택 안 함. 실제 C/A 진단 필요. |
| B. canonical row별 연산 | 일정한 reduction은 가능하지만 원래 BLAS D0 출력과 같다고 보장할 수 없다. 모델 계수가 같아도 수치 의미의 재검증이 필요하다. | 별도 수치 계약·비교·실행 승인 필요. |
| C. 비교 계약 개정 | tick equality만으로 continuous delta/SSE/SAE guard 동등성을 보장하지 못한다. 임의 tolerance/epsilon은 허용하지 않는다. | 별도 정책/실행 계약 승인 필요. |
| D. 현 계약으로 재개 불가 | 실제 C/A도 다르면 기존 qualification과 cache를 그대로 사용해 진행할 수 없다. | fail closed 유지. E2 자동 재실행 금지. |

## 검증 / 위험 / handoff

변경은 새 differential harness, 제한된 diagnostic adapter, synthetic tests, protocol, 공개 합성 결과 및 이 보고서에 한정한다. Runtime integration은 없다. 원본 입력은 read-only이며 출력은 원본과 분리된 0700/0600 exclusive private receipt다. Python audit와 openat2 보호의 범위를 OS 전체 sandbox로 주장하지 않는다.

New focused tests 28 PASS; full/current regression 및 독립 최종 검토/CI는 최종 결과에서 갱신한다. 합성 검증은 실증 성능 개선을 뜻하지 않는다. Replay/simulation/shadow/차량 검증은 이 진단 범위에 없으며 적용 권한도 없다. 원본 모델/원본 결과/32-clause gate를 유지하므로 rollback은 신규 진단 도구를 사용하지 않는 것이다.

`selected_candidate = null`, `selected_policy = null`, historical TRAIN gate `NOT_SAVED`, HOLDOUT `CLOSED`, vehicle `NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED`, authority `NONE`, Hugging Face `NOT_REQUIRED / NOT_USED`. Source-grid tick은 물리 EPS 움직임이 아니다. Logged command는 post-CarController normalized command이며 applied EPS torque가 아니다. SteeringRateDeg는 SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL이다.
