# CyberPilot V4 D2: projected tick 손실을 고려하는 판단 정책 설계

D1은 움직임 종료의 MOVE 오판을 줄였지만, 정지 유지 구간의 MOVE 오판과 one-step·TRUE MOVE 오차가 커졌다. 분류가 맞는 것과 최종 source-grid tick이 맞는 것은 다르다. D2는 같은 모델을 유지하면서 TRAIN에서 HOLD와 MOVE의 최종 tick 손익을 비교하는 정책이다. 이번에는 설계와 synthetic 계약만 확정한다. 실제 decision, Stage2 potential outcome, 새 예측과 rollout은 계산하지 않는다.

## 기준과 공개 근거

- Repository `rownlvh8875-coder/CyberPilot`, branch `feature/cyber-autotune`, baseline `f09caa202032c5d1f23c9d82a61589bcd8ed7137`. Fetch 후 local/origin 일치, index/worktree clean을 확인했다. Baseline [CI 39101175458](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/39101175458)는 completed/success다.
- Original execution `bd8045ef2a0da62a92603439f38e7740f5923622`. 정책 JSON의 `input_lock` 17개와 `source_lock` 12개가 공개 입력의 raw SHA256·canonical receipt 및 코드 위치를 고정한다. 원래 mathematical source 6개의 bytes를 execution HEAD와 대조했다. Workflow는 변경하지 않는다.
- Frozen E protocol `V4_E_D0_D1_PROTOCOL_V2`, raw SHA256 `2933aaf1eb40addcd1e872e831901da3ff6b778147cdfe46150fc4c1251a37a5`.
- [기존 E 결과](empirical-hurdle-stage1-v4-e-results.json) `/metric_families`, `/transitions`, `/acceptance_by_job`: `E_EXECUTION_COMPLETE_D1_NOT_ADMISSIBLE`, D1 job 합격 0/32, both-fold 후보 0/16, ONE_STEP_EXACT_HIT 실패 32/32. STATIC_HOLD false-MOVE는 증가하고 termination false-MOVE는 감소했다. One-step·TRUE MOVE RMSE/MAE는 악화했고 일부 긴 horizon RMSE는 개선됐다. 이 관찰은 Stage2의 독립 인과 기여율이나 D2 개선 효과를 증명하지 않는다. Onset/continuation의 억제된 수치는 재공개하지 않는다.
- [기존 E validation](empirical-hurdle-stage1-v4-e-validation.json), [D1 정책](empirical-hurdle-stage1-v4-d-transition-aware-policy.json), [D 평가 계약](empirical-hurdle-stage1-v4-d-offline-evaluation-contract.json), [R01–R17](empirical-hurdle-stage1-v4-decision-policy-requirements-spec.json), [22 검증 영역](empirical-hurdle-stage1-v4-decision-policy-future-validation.json)을 유지한다. 설계 traceability는 성능 합격을 뜻하지 않는다.

## 세 정책과 하나의 변경

| Arm | TRAIN decision | 역할 |
| --- | --- | --- |
| D0 | Job별 combined TRAIN BA로 정한 공통 decision 하나 | Original frozen V4, 원본 결과 보존 |
| D1 | Job·이전 STATIC/MOVE별 BA decision 두 개 | 이미 실패한 frozen E 비교 정책 |
| D2 | 같은 두 context에서 projected-tick exact-hit를 우선하고 D0 대비 TRAIN 보호 제약 적용 | 이번 유일한 신규 가설, 미실험 |

모든 arm은 16 candidates × Fold A/B = 32 jobs를 유지한다. Stage1 dual heads, feature 순서, normalizer, Stage2, quantization과 history는 같다. `raw_prior_delta == 0` / `!= 0`으로 head와 decision을 함께 선택한다. Strict `p > decision`이며 equality는 STATIC이다. 실제 inference에 supervised truth state를 넣지 않는다.

## TRAIN의 HOLD/MOVE 손익

[정책 명세](empirical-hurdle-stage1-v4-d2-loss-aware-policy.json)의 `/potential_outcomes`, `/objective`, `/guards`가 규범이다. 각 TRAIN row의 current tick c, next target t, 기존 score p, frozen Stage2 signed delta u를 사용한다.

- HOLD outcome: c. MOVE outcome: `project(float64(c) + u)`.
- Exact-hit 손익: `int(predicted_tick == t) - int(c == t)`. +1, 0, −1만 가능하다.
- Continuous residual: gated signed delta에서 정수 `t-c`를 float64로 변환한 값을 뺀다. Tick projection 뒤의 오차와 혼동하지 않는다.
- Harmful STATIC: **next truth가 STATIC**이고 projected tick이 c와 다른 경우다. STATIC_HOLD와 MOVE_TERMINATION을 포함하며 따로 보고한다. MOVE gate라도 projection이 HOLD면 harmful count는 0일 수 있다. Continuous residual은 여전히 0이 아닐 수 있다.

Stage2는 원래 [fit_cv_math.py:189](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py#L189)에서 true MOVE TRAIN에 fit됐다. 모든 STATIC TRAIN row에 u를 계산하는 것은 새로운 counterfactual numerical execution이며 외삽 위험이 있다. 이번에 실행하지 않았고, 이미 저장된 산출물이라고 주장하지 않는다. t와 두 hit indicator는 TRAIN supervised selection 및 평가에만 쓴다.

## 보호 제약, 목적함수와 비공집합 증명

각 job/context의 **동일 TRAIN 행**에서 D0 reconstructed baseline 대비 D2는 (1) true-MOVE gate TP 감소 없음, (2) TRUE MOVE continuous SSE 증가 없음, (3) TRUE MOVE continuous SAE 증가 없음, (4) harmful next-STATIC realized movement count 증가 없음을 요구한다. 허용 악화량은 0이다. 새 DEV 합격 cutoff가 아니며 기존 acceptance의 대체물이 아니다.

후보는 `{0,1} ∪ unique finite context TRAIN scores`다. 제약을 만족하는 후보에서 다음 순서로 선택한다.

1. HOLD_LAST 대비 net tick exact-hit gain 최대.
2. 해당 context 전체 continuous SSE 최소.
3. 해당 context 전체 continuous SAE 최소.
4. Harmful next-STATIC realized movement count 최소.
5. 더 큰 TRAIN decision.

가중치·margin·epsilon·D1 blending·사후 guard 완화는 없다. D0와 같은 gate가 최적이어도 유효하다.

D0 global decision을 θ0∈[0,1]라 할 때 context의 `max({0} ∪ {p ≤ θ0})`는 후보 집합에 속하며 D0와 같은 gate를 만든다. p≤θ0인 모든 행은 witness 이하이고 p>θ0인 모든 행은 witness보다 크다. Context에 θ0가 없어도 성립한다. 중복 score, ±0, 끝점 0/1도 strict 비교를 보존한다. 동일 cached potential bytes와 loss 계산을 사용하면 네 제약 모두 equality로 만족한다. 따라서 유효한 입력에서 feasible 후보는 비어 있지 않고, 선택된 TRAIN net gain은 그 witness보다 작지 않다.

이 증명은 두 context에 양성·음성 support가 있고, **모든 행의** Stage2 potential/projection·loss가 유효하다는 조건부 증명이다. D0가 HOLD한 행이라도 invalid potential을 제외하지 않는다. Missing class, NaN/Inf, projection overflow, reduction overflow는 job 전체 fail closed다. Feasible set이 비면 임의 D0 fallback을 쓰지 않고 `D2_TRAIN_FEASIBILITY_CONTRACT_UNRESOLVED`로 처리한다. TRAIN 제약은 DEV/recursive 비악화를 보장하지 않는다.

## D0 재구성과 부동소수점 동등성

Historical TRAIN rowwise gate는 계속 `NOT_SAVED`다. 향후 E2에서 [원래 threshold 함수](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py#L157)의 exact integer `TP*N_negative + TN*P`, TN 최대, larger decision tie-break를 combined TRAIN에 적용해 D0 reference를 새로 만든다. 원래 [V4 train:120](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_execution.py#L120)의 shared decision 계약이다. Private threshold를 열지 않으며, 읽지 않은 원래 threshold bytes와 같다고 주장하지 않는다.

Stage2 matmul은 행 batch 구성에 따라 마지막 bit가 달라질 가능성이 있다. E2는 원래 segment/original-order 512-row chunk에서 all-row u를 한 번 계산하고 고정한다. D0의 원래 `x[gate]` subset 계산과 같은 선택 행의 cached u가 byte-exact한지 별도 numerical qualification을 해야 한다. 불일치하면 tolerance·다른 chunk·재계산으로 맞추지 않고 `E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED`다. Guard의 D0와 모든 D2 후보는 같은 cache를 사용한다. 이 조건은 unread historical TRAIN 결과를 독립 재검증했다는 주장이 아니다.

SSE/SAE의 reduction은 original-order context 행을 고정 leaf로 배치한 binary tree다. 다음 2의 거듭제곱까지 +0.0 padding하고, 각 parent를 float64 `left + right`로 계산한다. Leaf residual·square도 매 연산 round-to-nearest ties-even, no FMA다. D0와 후보는 같은 topology와 같은 leaf 연산을 사용한다. Leaf를 바꿀 때 ancestor를 자식으로부터 다시 계산하며 running sum에서 빼고 더하지 않는다. 같은 gate는 경로에 관계없이 같은 root bits를 만든다.

보호 제약은 이 **정의된 float64 TRAIN tree root**에 대한 비교다. 정확한 실수합이나 기존 NumPy metrics reduction까지 같은 값이라고 주장하지 않는다. 기존 DEV acceptance 수식은 변경하지 않는다. Count는 Python exact integer다.

## 실행 복잡도와 causal state

향후 E2 구현은 scalar score와 original row index를 stable sort하고 equal-score group을 완전히 HOLD로 전환한 뒤 후보를 평가한다. 원본 행 배열을 재정렬하지 않는다. 네 loss tree와 exact counter만 갱신하므로 시간 O(N log N), memory O(N)이다. N×후보 수 행렬은 금지한다. Tree는 `64*next_power_of_two(N)` bytes, N>1이면 128N bytes 미만이다. 전체 input/potential/index/feature buffer와 CPU·wall·disk·reserve의 구체 상한은 E2 입력 접근 전 capacity와 manifest shape에 결부해 추가 동결해야 한다. 이번에는 runner를 작성하지 않는다.

One-step은 observed prior delta로 routing한다. Recursive는 현재 projected tick, 전체 delta history, 마지막 **실제 projected delta**로 head/decision을 선택하고 gate 후 frozen Stage2와 projection을 적용한다. [V4 recursive:185](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_execution.py#L185)의 full history shift/update를 보존한다. Gate bit를 delta로 대체하지 않는다. 미래 truth·oracle potential은 입력이 아니다. Segment 경계를 넘거나 padding하지 않고 horizon/path마다 초기화한다. Supplied command/speed는 차량과 상호 반응하는 closed-loop가 아니다.

[원래 projection:49](../../../openpilot/tools/cyber_autotune/empirical_s2_ri_fit_cv_math.py#L49)는 finite 값을 ties-to-even 반올림한 뒤 signed16 [−32768,32767] 범위를 검사한다. Clip이나 강제 nonzero movement는 없다.

## 확보된 계약과 아직 확인하지 않은 입력

E protocol에는 CAUSAL command/speed, DERIVED tick/streak/eligibility/run/within, frozen model/normalizer가 선언돼 있다. Source의 [features:31](../../../openpilot/tools/cyber_autotune/empirical_s2_ri_fit_cv_math.py#L31)는 intercept, 지연 command L개, observed tick delta L개, current tick, speed를 이 순서로 만든다. [design:76](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_data.py#L76)은 동일 ordered anchors에서 current와 next target을 만든다. 공개 E의 roots 복구와 field 선언은 **전체 TRAIN population의 실제 파일·정렬·counterfactual 입력 확보 증명**이 아니다.

[평가 계약](empirical-hurdle-stage1-v4-d2-evaluation-contract.json) `/additional_TRAIN_inputs`의 8개 범주가 필요한 정확한 source/field와 향후 확인 절차를 명시한다. B1/C의 기존 7개 필드만으로는 부족하다. 상태는 `E2_TRAIN_COUNTERFACTUAL_INPUT_NOT_YET_VERIFIED`다. 이번에는 private handoff나 metadata조차 열지 않았다. 추가 최소 descriptor가 필요하면 E2 grant·reader·privacy review에 명시해야 하며 mixed TRAIN receipt를 우회 parsing하지 않는다.

## E2 계약과 승인 경계

별도 E2 승인은 exact host/root/member/field/model·normalizer·source/anchor identity, 추가 TRAIN current/target/features, Stage2 all-row counterfactual, D0 TRAIN reconstruction, 64개 D2 decision, DEV one-step, H25/50/100/200 full recursive, 두 독립 반복, private output 및 privacy projection을 구체적으로 포함해야 한다. 기존 E 승인이 새 E2 권한으로 이어지지 않는다. 모든 TRAIN decision을 먼저 봉인한 뒤 DEV에 접근한다.

기존 32 clauses(5 one-step + 3 TRUE MOVE + 24 rollout), support 201, epsilon 0, 원래 inequality, same-anchor HOLD_LAST, both-fold 조건을 그대로 유지한다. D0/D1 paired 결과는 추가 진단이다. 네 truth transition, gate→HOLD, harmful movement, hit loss/gain/net, TRUE MOVE magnitude, 모든 OVERALL/PATH_MOVED horizon과 R01–R17/22-domain mapping이 계약에 연결돼 있다. Unsupported population은 NOT_IDENTIFIABLE이고 필수 clause를 PASS하지 않는다. TRAIN 보호 제약이 DEV 통과를 대신하지 않는다.

두 E2 repeat는 독립 TRAIN 선택·one-step·rollout을 수행하고 canonical payload가 byte-exact해야 한다. Verify-only는 stored output seal만 확인하며 source reread/inference/recompute/source write 모두 0이다. 결과를 보고 objective·guard·grid를 바꾸지 않는다. DEV는 이미 관찰했으므로 exploratory retrospective 비교이며 독립 blinded validation이 아니다. 낮은 previous-STATIC score discrimination, Stage2 외삽, projection 및 recursive feedback 위험이 남는다.

공개 제한은 D0/D1/D2와 양 Fold 및 기존 C/E release를 함께 검토한다. Minimum support 201과 complementary suppression을 완화하지 않는다. Onset/continuation, rare exact-hit, decision/coefficients/normalizer, per-row values, sensitive IDs/paths는 우회 공개하지 않는다. Gate 의존 invocation count 역시 private-only다. Job 중복 anchor를 독립 주행 수로 세지 않는다.

## 검증 기록과 종료

현재 변경은 두 JSON 계약, 이 문서, 공개/static 및 8행 이하의 임의 synthetic witness 테스트 한 파일이다. Test witness는 실제 모델 source를 import하거나 scientific input을 받지 않는다. 실제 private input counter 23개는 모두 0이며, 공개 source/receipt 검사와 synthetic historical regression은 별도다. Existing scientific source/model/runtime/workflow는 그대로 유지한다.

검증 실행 결과와 독립 리뷰의 최종 exact-byte receipt는 최종 handoff에서 보고한다. 아직 실행하지 않은 검사를 이 문서에서 PASS로 가정하지 않는다. 최종 exact-head CI는 self-reference 없이 GitHub run으로 확인한다.

Original V4 `HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE`, `MODEL_SELECTION_FAILED_CLOSED`, selected candidate null 및 D1 `E_EXECUTION_COMPLETE_D1_NOT_ADMISSIBLE`은 유지한다. D2는 `DESIGN_ONLY_NOT_EVALUATED`다. Original whole-replica equality는 `REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED`다. HOLDOUT CLOSED / FUTURE_UNTOUCHED_HOLDOUT_REQUIRED / NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, FINAL_POOLED_REFIT_NOT_AUTHORIZED, COMPOSITION_NOT_AUTHORIZED를 유지한다. Vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED, authority NONE이다. Hugging Face NOT_REQUIRED / NOT_USED다.

Source-grid tick은 물리 EPS movement를 입증하지 않는다. Logged command는 POST_CARCONTROLLER_NORMALIZED_COMMAND이며 실제 applied torque가 아니다. steeringRateDeg는 SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL이다.

D2 설계·synthetic 검증·독립 review·GitHub CI 확인 뒤 중지한다. E2 runner 구현, private data 접근, TRAIN counterfactual/decision 계산, rollout, policy adoption, HOLDOUT, 차량, V5를 자동 시작하지 않는다.
