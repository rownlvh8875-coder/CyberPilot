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

`E2_NUMERICAL_ROOT_CAUSE_IDENTIFIED`. 사전 HEAD `f77ce9921f8e8008cfc3533c62e1eac30523940e`의 CI [39133199735](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39133199735)가 completed/SUCCESS인 것을 확인한 뒤 새 process에서 HRI_D00_L01 / FOLD_B / TRAIN 한 job을 1회 진단했다. 기존 E2는 resume하지 않았다.

| 검사 | 실제 한 job 결과 |
| --- | --- |
| Source hash/schema/recorded-order anchor | PASS |
| A/B/C 변환 입력 행 | byte-exact |
| B chunk-selected vs A cache | 실제 floating-point 값도 불일치; signed-zero만의 차이가 아님 |
| C original whole-job selected vs A cache | byte-exact |
| Whole-job all-row vs A cache | byte-exact |
| 각 경로의 frozen projected tick | 동일 |

따라서 실제 장애는 입력/행 정렬 또는 정규화 결과 차이로 설명되지 않는다. 동일 변환 행·계수에 대한 배치/layout에 민감한 NumPy `@` 수치 계산 단계로 국소화됐다. 특정 OpenBLAS kernel, FMA 또는 CPU 명령을 직접 추적해 확정한 것은 아니다. 합성 L1 fixture 자체에서는 B/A가 재현되지 않았고, 실제 L1의 결론은 이 별도 제한 진단에 근거한다.

**Case 5에 해당한다.** 원래 D0 전체 선택 행 계산 C와 cache A는 이 job에서 같다. B는 D0 comparator 계산도 아니고 D2 loss에 쓰이는 cache 값도 아니며, E2가 추가한 qualification이다. B/A 실패를 원래 D0 C/A 실패라고 주장할 수 없다. 이번 결과는 기존 E2를 소급 PASS로 바꾸거나 아직 검사하지 않은 나머지 job의 C/A 동등성을 증명하지 않는다.

원본 source reads는 metadata 179개/5,015,070 bytes, numeric members 681개/27,349,143 bytes, 합계 860개/32,364,213 bytes다. 실행 process의 별도 control-record reads는 19개/2,381,873 bytes다. 사전 승인 binding 준비와 저장 receipt 검증은 이 source 집계에서 분리한다. 원본 writes 및 forbidden attempts는 0이다. D0 TRAIN reconstruction은 허용된 한 job에서 1회 수행했고 원래 private threshold는 읽지 않았다. 실제 Stage2 호출 경로별 수, 차이의 행 수·최댓값·ULP·layout·source ledger는 비공개 receipt에만 보존했다. Gate에 의존하는 호출 telemetry도 공개하지 않는다.

상세 private result는 0600 sealed receipt, 별도 output directory는 0700이고 binding/result는 exclusive creation이다. 저장 result/binding의 seal·head·protocol 연결을 다시 확인했다. 이 검증에서 source reread/inference/recompute는 0이다. DEV, mixed TRAIN receipt, Stage1 model 및 D2 selector 접근은 0이다.

## 수정 방향의 판정

| 방법 | 원래 D0 의미와의 관계 | 이번 결정 |
| --- | --- | --- |
| A. 기존 byte-exact 유지 | original whole-job selected-row 호출을 보존해야 한다. 모든 배치의 동일 결과를 현재 NumPy/BLAS 식만으로 보장할 근거는 없다. | 실제 한 job의 C/A는 byte-exact였다. 이 원래 comparator를 유지하고 추가 B 검사의 필요성을 별도 계약 검토할 근거가 생겼다. 아직 수정/채택하지 않음. |
| B. canonical row별 연산 | 일정한 reduction은 가능하지만 원래 BLAS D0 출력과 같다고 보장할 수 없다. 모델 계수가 같아도 수치 의미의 재검증이 필요하다. | 별도 수치 계약·비교·실행 승인 필요. |
| C. 비교 계약 개정 | tick equality만으로 continuous delta/SSE/SAE guard 동등성을 보장하지 못한다. 임의 tolerance/epsilon은 허용하지 않는다. | 별도 정책/실행 계약 승인 필요. |
| D. 현 계약으로 재개 불가 | 현 V1은 B/A도 필수여서 이 job에서 계속 fail closed다. 나머지 job에서 C/A까지 다르면 B 검사만 조정하는 방향으로 해결할 수 없다. | fail closed 유지. E2 자동 재실행 금지. |

## 검증 / 위험 / handoff

변경은 새 differential harness, 제한된 diagnostic adapter, synthetic tests, protocol, 공개 합성 결과 및 이 보고서에 한정한다. Runtime integration은 없다. 원본 입력은 read-only이며 출력은 원본과 분리된 0700/0600 exclusive private receipt다. Python audit와 openat2 보호의 범위를 OS 전체 sandbox로 주장하지 않는다.

New focused 28 PASS, 관련 focused 364 PASS, 최종 코드의 full AutoTune/controls 5,530 PASS(599.14s), lateral synthetic 16 PASS. Ruff/compileall/SCons, 사전 JSON parse 821개/receipt 2개, 결과 추가 후 최종 JSON parse 822개/신규 canonical receipt 3개, source 50개/public input 17개 pin, 원본 수학/실행 3개 byte identity, publication 검사 최종 7개 파일/0 findings, git diff --check PASS. 두 독립 검토는 source/protocol exact bytes를 APPROVED했으며 원본 private payload를 별도로 열거나 재분석하지 않았다. 최종 공개 결과는 추가 privacy 검토 및 publication CI를 따른다. 합성 검증은 실증 성능 개선을 뜻하지 않는다. Replay/simulation/shadow/차량 검증은 이 진단 범위에 없으며 적용 권한도 없다. 원본 모델/원본 결과/32-clause gate를 유지하므로 rollback은 신규 진단 도구를 사용하지 않는 것이다.

`selected_candidate = null`, `selected_policy = null`, historical TRAIN gate `NOT_SAVED`, HOLDOUT `CLOSED`, vehicle `NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED`, authority `NONE`, Hugging Face `NOT_REQUIRED / NOT_USED`. Source-grid tick은 물리 EPS 움직임이 아니다. Logged command는 post-CarController normalized command이며 applied EPS torque가 아니다. SteeringRateDeg는 SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL이다.


## 권장되는 다음 승인 범위와 STOP

다음 단일 작업은 **원래 D0 whole-job byte-exact 의미를 보존하는 E2 qualification 계약 개정 검토**다. 검토 대상은 추가 B/A 조건의 역할이며, Stage2 함수·모델·512행 all-row potential·D2 objective/guard·32-clause acceptance를 편의상 바꾸는 작업이 아니다. 변경 승인 전에는 현재 V1을 그대로 보존한다.

검토에서 새 protocol을 승인하더라도 재실행은 별도 명시적 E2 승인에 결부해야 한다. 모든 32 TRAIN job에서 원래 whole-job C/A byte-exact qualification을 확인하고, 실패 시 중지하며, 그 후 기존 TRAIN/DEV barrier와 fresh two-repeat 절차를 지켜야 한다. 이번 한 job 통과만으로 나머지를 생략할 수 없다. Canonical rowwise 방식이나 tolerance/tick-only 비교를 택한다면 continuous SSE/SAE와 원래 D0 의미가 달라질 수 있으므로 더 넓은 수치 계약·정책 재검증 승인이 필요하다.

실제 수정·삭제·tolerance/epsilon 완화는 **0**이다. D2 decisions/new gates/DEV/rollout, 새 policy search/tuning, refit/calibration, raw/qlog/HOLDOUT/vehicle 및 original source writes는 **0**이다. D2는 `PERFORMANCE_NOT_EVALUATED`, 기존 E2는 `E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED`를 유지한다. 이 진단을 끝으로 STOP하며 E2·D3·V5 또는 정책 채택을 자동 진행하지 않는다.
