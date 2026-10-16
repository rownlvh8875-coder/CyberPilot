V4는 학습 자체에는 문제가 없었다.
STATIC/MOVE 두 모델 모두 32개 작업에서 정상적으로 학습됐다.

그런데 실제 예측에서는 exact-hit이 모두 실패했고,
50~200 step 장기 예측은 거의 모든 지표에서 실패했다.

이번 작업은 새 모델을 만드는 게 아니다.

이미 저장된 V4 결과를 다시 읽어서,
정지 상태에서 쓸데없이 움직인 것이 문제인지,
움직여야 할 때 놓친 것이 문제인지,
조향 크기가 틀린 것이 문제인지,
한 번의 예측 오류가 다음 context를 바꿔
장기적으로 누적되는지가 어디에서 시작되는지 분해한다.

여기서 움직임과 크기는 source-grid tick 변화의 의미다. 물리적 EPS 움직임,
실제 적용 torque, 부호가 증명된 물리적 steering rate로 해석하지 않는다.

## 결과와 범위

모든 head의 support/rank/non-separation/convergence가 정상인 상태에서 발생한 예측 오류다.
STATIC exact-hit 손실은 571,317, MOVE exact-hit 이득은 228,164, 순손실은 343,153이다.
32개 작업 모두 손실이 이득보다 컸다. 이는 정확한 정수 항등식이며 새 threshold 실험이 아니다.

Overall ranking은 모든 작업에서 개선됐지만, previous-STATIC 내부 ranking은 13개 개선/19개 악화다.
Previous-MOVE 내부 ranking은 32개 모두 개선됐다. 따라서 dual-head가 모든 상태의 ranking을
일관되게 개선했다고 말할 수 없다. 장기 실패에는 gate 불일치, projected movement/context 변화와
조건부 magnitude 잔여 위험이 함께 관찰된다. Stage2만의 원인이나 개입 효과로 단정하지 않는다.

아래 합계는 candidate/job별 관측 행·경로 수의 합이다. 서로 겹치는 anchor가 있으므로 독립 표본 수가 아니다.
Metric 평균은 별도 표기가 없으면 job metric의 산술 평균이며 pooled RMSE/AUC 또는 pooled final refit이 아니다.
전체 per-job/fold 수치와 정확한 분모는 동반 JSON에 보존했다. 유의성 검정이나 임의의 good-AUC 기준은 사용하지 않았다.

## Identity and purpose

- Area: Cyber Validation / AutoTune; REPORT_ONLY.
- Repository: https://github.com/rownlvh8875-coder/CyberPilot; branch `feature/cyber-autotune`.
- Original EXECUTION_HEAD: `bd8045ef2a0da62a92603439f38e7740f5923622`.
- Baseline RESULT_PUBLICATION_HEAD and analysis HEAD: `3943f5c2f4ef641e673ca6a47b24b44a359765c8`.
- Analysis recipe: the exact `analysis_sources` SHA256 map in every public artifact, bound before analysis; the new additive source was then uncommitted.
- Current RESULT_PUBLICATION_HEAD: the Git commit containing this report; resolved in the final handoff and exact-commit CI, avoiding self-reference.
- Original authorization SHA256: `a23e88b37ba1b2b57f5eb29bc37508166a6a392354826d00bb4444d8efcdc34c`.
- Original actual manifest: `fd3639f93944edecfdfa573818d29fbc8a91ab23208e2d561f8a69726eb0dc64`.
- Attribution input lock: `fbf8d37135b6aaca7f9c8a175197b6d67f5e2229193eb0d12971f5bf194f5fc6`.
- Shared attribution manifest: `cdab4ff4db4df9da9bdefc1d3ecf0c9626c89d9a094dd52df2a19e3d4b456e53`.
- Attribution repeatability receipt: `ade026b5e0503f508959570a79d87a47c74f230ea6da9145e6223efb14585d4b`.
- Attribution resume receipt: `5c9c4274f253272550bc5c7f324645d3ff4f0cc64e7e108f82688424791a83a9`.

Original outcome remains HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE / MODEL_SELECTION_FAILED_CLOSED; selected candidate null.

## Original references, changes and expected effect

Additive `empirical_hurdle_v4_attribution_math.py`, `empirical_hurdle_v4_attribution.py`, and
`empirical_hurdle_v4_attribution_publication.py` reuse the repository's V2 exact score-group AUC,
saved-array verification and canonical receipt mechanism at the baseline commit above. Existing repository
license/attribution apply. No dependency, submodule, model, normalizer, fitting policy or controller interface changed.

Call path: exact public baseline Git blobs and receipts -> migration-bound direct E roots/live volume ->
actual replica byte/content equality -> saved V4 repeat-1 plus aligned V1 populations -> descriptive reductions ->
two fresh independent aggregate runs -> trapped verify-only resume -> explicit aggregate publication.
Actual repeat-2 is an integrity replica, not a second sample to average.

The new E sink is disjoint from all inputs. The predeclared aggregate allowance is 100,663,296 bytes;
the existing explicitly bound reserve is 2,147,483,648 bytes. Capacity/reserve and exclusive JSON writes
are enforced before writes. Only safe root/mount/volume hashes are public. All actual and attribution replicas are retained.
Saved coefficient arrays are decoded only by the original actual integrity verifier to check identity, not loaded as executing models.
Integrity-only numeric opens are not described as zero numeric access; model execution is zero.

## Saved input coverage and regression risks

V4 saved one-step probability/gate/integrated delta/projected tick/error and rollout path/gate/error were used.
V1 supplied exact aligned truth/current/target/prior delta/observed path/comparator errors and fixed scores.
TRAIN uses saved V4 combined probability plus V1 TRAIN labels/context. Stored TRAIN aggregate confusion is reused.

INPUT_INSUFFICIENT: V4 TRAIN rowwise gates, rollout stepwise probability, continuous branch delta and direct saved context trace.
None was regenerated. Recursive context is mechanically derived from saved projected differences and the saved initial prior delta,
consistent with the immutable executor contract; no independent saved per-step head/context trace is claimed.

One-step continuous error is integrated_delta - observed_delta; projected tick error is projected_next_tick - target.
They differ after quantization. MOVE gate does not imply projected movement. FP projected HOLD is harmless for tick movement,
but does not prove its continuous delta error is zero. Integer arrays widen before differences. Empty/small subsets remain explicit.

## One-step exact-hit and STATIC false movement

candidate_hits = HOLD_LAST_hits - STATIC_HIT_LOSS + MOVE_HIT_GAIN.
HOLD_LAST_hits equals true STATIC count. All 32 identities reconcile exactly with the original frozen exact-hit metrics.

| Scope | STATIC truth | MOVE truth | STATIC loss | MOVE gain | Net hits | Gate FP | FP projected HOLD | Harmful / FP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FOLD_A | 3,104,210 | 518,169 | 364,248 | 121,218 | -243,030 | 1,270,842 | 906,594 | 28.662% |
| FOLD_B | 3,764,182 | 648,787 | 207,069 | 106,946 | -100,123 | 391,393 | 184,324 | 52.906% |
| ALL_JOBS | 6,868,392 | 1,166,956 | 571,317 | 228,164 | -343,153 | 1,662,235 | 1,090,918 | 34.370% |

Gate FP 1,662,235 중 1,090,918은 projected HOLD였다. 실제 harmful false movement 571,317만 STATIC hit loss다.

## Onset / continuation와 MOVE 오류

Previous observed delta != 0으로 네 진실 집단을 구분했다. 아래 count 합계는 겹치는 job 행을 포함한다.

| Fold | Truth context | N | TN | FP | FN | TP | Recall(MOVE) / FPR(STATIC) | Harmful false movement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FOLD_A | PREV_MOVE_MOVE_CONTINUATION | 231,012 | 0 | 0 | 0 | 231,012 | 100.000% | 0 |
| FOLD_A | PREV_MOVE_TRUE_STATIC | 286,580 | 0 | 286,580 | 0 | 0 | 100.000% | 144,852 |
| FOLD_A | PREV_STATIC_MOVE_ONSET | 287,157 | 0 | 0 | 171,735 | 115,422 | 40.195% | 0 |
| FOLD_A | PREV_STATIC_TRUE_STATIC | 2,817,630 | 1,833,368 | 984,262 | 0 | 0 | 34.932% | 219,396 |
| FOLD_B | PREV_MOVE_MOVE_CONTINUATION | 289,866 | 0 | 0 | 4 | 289,862 | 99.999% | 0 |
| FOLD_B | PREV_MOVE_TRUE_STATIC | 358,706 | 0 | 358,706 | 0 | 0 | 100.000% | 193,892 |
| FOLD_B | PREV_STATIC_MOVE_ONSET | 358,921 | 0 | 0 | 351,214 | 7,707 | 2.147% | 0 |
| FOLD_B | PREV_STATIC_TRUE_STATIC | 3,405,476 | 3,372,789 | 32,687 | 0 | 0 | 0.960% | 13,177 |

Previous-MOVE -> true STATIC에서 두 fold 모두 gate FP가 100%였다. Continuation은 거의 모두 TP였지만,
onset recall은 A 약 40.2%, B 약 2.15%였다. MOVE-head의 ranking 개선이 stop/continuation의 실제 gate 구분으로
연결되지 않은 operating-point 사실이다. 실제 threshold 값이나 다른 threshold의 효과는 계산/공개하지 않았다.
FN은 저장된 delta=0 및 projected tick=current인 HOLD 항등식을 확인했다. 양/음 부호는 source-grid delta 부호다.

| Fold | Gate class | N | One tick | Multi tick | Positive | Negative | Exact target | Within one tick |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FOLD_A | TP | 346,434 | 250,787 | 95,647 | 181,758 | 164,676 | 121,218 | 290,342 |
| FOLD_A | FN | 171,735 | 148,158 | 23,577 | 79,599 | 92,136 | 0 | 148,158 |
| FOLD_B | TP | 297,569 | 207,958 | 89,611 | 141,416 | 156,153 | 106,946 | 249,715 |
| FOLD_B | FN | 351,218 | 304,236 | 46,982 | 186,980 | 164,238 | 0 | 304,236 |

## Score ranking과 TRAIN -> DEV transfer

AUC는 saved score의 exact tie groups와 Python integer numerator/denominator로 계산했다. 비교는 exact cross multiplication이다.

| Context | TRAIN AUC job mean | DEV AUC job mean | Fixed DEV AUC job mean | Improved | Equal | Decreased |
| --- | --- | --- | --- | --- | --- | --- |
| OVERALL | 0.707438 | 0.702174 | 0.561609 | 32 | 0 | 0 |
| PREV_STATIC | 0.554846 | 0.545865 | 0.542041 | 13 | 0 | 19 |
| PREV_MOVE | 0.592356 | 0.574285 | 0.564933 | 32 | 0 | 0 |

Overall 개선을 모든 상태 내부의 개선으로 해석하지 않는다. 특히 previous-STATIC에서 19/32 작업은 fixed-score보다 ranking이 낮았다.

| Context | Population | Mean p | MOVE prevalence | Calibration bias | Brier | MOVE score mean | STATIC score mean | Score gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OVERALL | train | 0.145001 | 0.145001 | 0.000000 | 0.107146 | 0.260899 | 0.125349 | 0.135550 |
| OVERALL | development | 0.148984 | 0.145001 | 0.003983 | 0.108285 | 0.261783 | 0.129884 | 0.131899 |
| PREV_MOVE | train | 0.446295 | 0.446295 | -0.000000 | 0.239276 | 0.463723 | 0.432265 | 0.031458 |
| PREV_MOVE | development | 0.448176 | 0.446295 | 0.001881 | 0.244034 | 0.461420 | 0.437492 | 0.023927 |
| PREV_STATIC | train | 0.093946 | 0.093946 | 0.000000 | 0.084753 | 0.097623 | 0.093562 | 0.004061 |
| PREV_STATIC | development | 0.098363 | 0.093946 | 0.004416 | 0.085282 | 0.101096 | 0.098080 | 0.003015 |

Per-job/context TRAIN/DEV AUC 및 차이, score/calibration/Brier 변화는 [score-transfer JSON](empirical-hurdle-stage1-v4-score-transfer.json)에 모두 보존했다.

| Fold | Population | True MOVE | Gate MOVE | Recall | Specificity |
| --- | --- | --- | --- | --- | --- |
| FOLD_A | development | 14.292% | 44.876% | 66.959% | 58.807% |
| FOLD_A | train | 14.708% | 23.080% | 53.750% | 82.209% |
| FOLD_B | development | 14.708% | 15.647% | 45.902% | 89.570% |
| FOLD_B | train | 14.292% | 17.601% | 48.887% | 87.616% |

TRAIN 값은 저장된 global TRAIN decision의 집계다. missing TRAIN row gates에 threshold를 적용하지 않았다.

## Fold A/B와 historical mechanism

| Version | Fold | Evaluated jobs | FPR job mean | FNR job mean |
| --- | --- | --- | --- | --- |
| V1 | FOLD_A | 16 | 49.458% | 39.071% |
| V1 | FOLD_B | 16 | 2.599% | 89.555% |
| V2 | FOLD_A | 16 | 0.108% | 98.572% |
| V2 | FOLD_B | 16 | 0.002% | 99.678% |
| V3 | FOLD_A | 15 | 49.432% | 39.073% |
| V3 | FOLD_B | 16 | 2.599% | 89.555% |
| V4 | FOLD_A | 16 | 41.193% | 33.041% |
| V4 | FOLD_B | 16 | 10.430% | 54.098% |

V1은 STATIC false movement와 MOVE miss의 tradeoff, V2는 거의 모든 MOVE를 놓치는 suppression,
V3는 V1 수준으로 MOVE coverage를 되돌리며 STATIC loss도 되돌린 결과다. V3 Fold A의 미평가 1개는 수치 회귀로 세지 않았다.
V4는 fixed V1 대비 missed-move rate가 32/32 개선됐고, false-move rate는 16개 개선/16개 악화였다.
A는 FPR/FNR 모두 낮아졌고 B는 FNR을 줄인 대신 FPR이 늘었다. 버전별 전체 평가 분모와 공통 31-job 성능 비교는
기존 [V1/V2/V3/V4 comparison](empirical-hurdle-stage1-v4-v1-v2-v3-comparison.json)을 그대로 유지한다.

A의 mean-score transfer는 +0.017882, calibration-bias transfer는 +0.022050;
B는 각각 -0.009916, -0.014084다. 반대 방향 score/calibration shift는 남아 있다.
One-step predicted MOVE prevalence는 두 fold 모두 truth보다 높아, 고정된 one-step operating-bias 반대방향 조건의
formal V4_FOLD_TRANSFER_ASYMMETRY_PERSISTS state는 설정하지 않았다. 이것이 rollout fold 비대칭이 없다는 뜻은 아니다.
아래에서 A의 gate 과활성과 B의 MOVE 억제가 다시 뚜렷하게 갈린다. V4가 fold transfer를 해결했다고 결론 내리지 않는다.

## Recursive rollout: gate, realized movement, context

| H | Gate mismatch job mean | Movement mismatch job mean | Context divergence job mean | First context median | p95 | No divergence paths | Path count sum | First context step 2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 25 | 28.936% | 17.775% | 17.758% | 3.0 | 21.0 | 2,214,101 | 7,226,640 | 1,179,346 |
| 50 | 29.426% | 17.869% | 17.871% | 5.0 | 40.0 | 1,073,666 | 6,856,705 | 1,120,359 |
| 100 | 29.830% | 17.636% | 17.641% | 9.0 | 70.0 | 310,865 | 6,404,766 | 1,045,508 |
| 200 | 29.966% | 17.283% | 17.284% | 11.0 | 93.0 | 48,505 | 5,826,219 | 949,615 |

First-event는 1-based step, 0=none이다. 위 median/p95는 none=0도 포함한다. Initial context는 observed history와 같고,
h>=2에서 projected context divergence는 직전 movement-pattern mismatch와 정확히 같다. 마지막 step mismatch는
다음 context가 horizon 밖이라 NO_CONTEXT_DIVERGENCE에 포함될 수 있다. 모든 path의 terminal_error = sum step_delta_error를 정확히 검증했다.
Early는 4*first_step <= H인 구조적 첫 사분면이다. 모든 horizon/32개 작업에서 early와 no-divergence subset이 각각 >=201이고,
early의 RMSE/MAE/p95가 더 컸다. 이는 ASSOCIATED_WITH이며 개입 효과나 독점적 원인이 아니다.

| Fold | H | Gate MOVE | Projected MOVE | True MOVE | Gate mismatch | Context divergence |
| --- | --- | --- | --- | --- | --- | --- |
| FOLD_A | 25 | 42.442% | 15.114% | 14.041% | 41.449% | 19.639% |
| FOLD_A | 50 | 43.542% | 15.171% | 13.885% | 42.512% | 19.847% |
| FOLD_A | 100 | 44.416% | 14.376% | 13.593% | 43.432% | 19.476% |
| FOLD_A | 200 | 44.512% | 13.065% | 13.201% | 43.858% | 18.908% |
| FOLD_B | 25 | 6.466% | 5.426% | 14.722% | 16.423% | 15.877% |
| FOLD_B | 50 | 5.381% | 4.544% | 14.721% | 16.341% | 15.894% |
| FOLD_B | 100 | 4.619% | 3.846% | 14.710% | 16.228% | 15.805% |
| FOLD_B | 200 | 4.041% | 3.298% | 14.736% | 16.074% | 15.659% |

Gate와 실제 movement 비율은 크게 다르다. H=200 전체 job mean은 gate MOVE 24.277%, projected MOVE 8.181%, truth MOVE 13.969%다.
B는 recursion에서 gate/projected MOVE가 감소하며 많은 onset을 놓친 STATIC context에 머무는 패턴과 연관된다.
A는 높은 MOVE gate 비율을 유지하지만 많은 MOVE gate가 projected HOLD로 변환된다. Projected movement가 다음 head/context를
기계적으로 결정하므로 gate 오류와 Stage2/quantization realization을 함께 봐야 한다. 새 경로를 생성한 비교가 아니다.

## TP magnitude와 disjoint step errors

아래는 projected integer step-delta error의 job metric 평균이다. One-step continuous delta error와 직접 혼합하지 않는다.
Onset/continuation은 observed previous context로 정의했다. Continuous recursive branch delta가 없으므로 이를 Stage2 weights만의 오차로 분리하지 않는다.

| H | TP context | Event count sum | Exact delta | Within one tick | RMSE job mean | MAE job mean | p95 job mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 25 | ONSET | 3,744,468 | 34.983% | 82.900% | 1.377145 | 0.920465 | 2.625000 |
| 25 | CONTINUATION | 4,554,067 | 27.989% | 71.437% | 1.805404 | 1.231835 | 3.593750 |
| 50 | ONSET | 6,928,167 | 34.242% | 83.033% | 1.388754 | 0.941471 | 2.593750 |
| 50 | CONTINUATION | 7,573,180 | 26.381% | 70.253% | 1.860093 | 1.287370 | 3.750000 |
| 100 | ONSET | 12,559,550 | 33.468% | 84.224% | 1.326595 | 0.921035 | 2.468750 |
| 100 | CONTINUATION | 12,533,465 | 25.854% | 71.377% | 1.787782 | 1.266884 | 3.500000 |
| 200 | ONSET | 21,967,581 | 31.994% | 85.223% | 1.256243 | 0.893839 | 2.406250 |
| 200 | CONTINUATION | 20,198,046 | 25.485% | 73.234% | 1.661738 | 1.220998 | 3.312500 |

[Step-error JSON](empirical-hurdle-stage1-v4-rollout-step-error.json)은 TP/FP/FN/TN 각각 event count, signed sum, SAE/SSE, MAE/p95를 보존한다.
Step SAE/SSE를 terminal RMSE의 기여율로 합산하지 않는다. 누적 오차의 cross terms가 있기 때문이다.

## Gate-perfect / projected-movement-perfect support와 잔여 위험

관찰된 saved path를 부분집합으로 나눈 결과다. 완벽한 gate를 강제로 넣은 counterfactual rollout이 아니다.
Gate MOVE가 projected HOLD가 될 수 있어 두 perfect 집합은 서로 일반적으로 포함 관계가 아니다.
0=EMPTY, 1..200=SMALL_SUPPORT_DESCRIPTIVE_ONLY, >=201=FULL_DESCRIPTIVE_SUPPORT는 job별 기준이다.
Metric tuple은 RMSE/MAE/p95의 nonempty-job 평균이다. SMALL도 포함하므로 support 열과 함께 읽어야 한다.

| H | Subset | Path count sum | Full/small/empty jobs | Candidate tuple | HOLD tuple |
| --- | --- | --- | --- | --- | --- |
| 25 | GATE_PERFECT | 1,763,443 | 32/0/0 | 5.291190/0.331402/0.000000 | 12.942962/0.859006/0.000000 |
| 25 | GATE_PERFECT_PATH_MOVED | 17,310 | 32/0/0 | 49.739772/28.351326/120.032812 | 123.166421/75.094929/286.892187 |
| 25 | PROJECTED_MOVEMENT_PATTERN_PERFECT | 2,149,462 | 32/0/0 | 4.126408/0.203085/0.000000 | 10.646778/0.559350/0.000000 |
| 25 | PROJECTED_MOVEMENT_PATTERN_PERFECT_PATH_MOVED | 14,867 | 32/0/0 | 49.056733/27.980809/116.206250 | 123.570557/74.032522/293.632812 |
| 50 | GATE_PERFECT | 830,132 | 32/0/0 | 3.624658/0.140016/0.000000 | 14.404922/0.619834/0.000000 |
| 50 | GATE_PERFECT_PATH_MOVED | 4,645 | 5/27/0 | 46.960836/24.112896/113.914062 | 187.518128/107.452023/348.829688 |
| 50 | PROJECTED_MOVEMENT_PATTERN_PERFECT | 1,046,685 | 32/0/0 | 2.761778/0.079836/0.000000 | 11.030884/0.362815/0.000000 |
| 50 | PROJECTED_MOVEMENT_PATTERN_PERFECT_PATH_MOVED | 3,748 | 0/32/0 | 43.472311/20.653973/110.009375 | 173.873128/93.777683/347.932812 |
| 100 | GATE_PERFECT | 223,520 | 32/0/0 | 0.068976/0.004647/0.000000 | 0.068390/0.004462/0.000000 |
| 100 | GATE_PERFECT_PATH_MOVED | 1,023 | 0/32/0 | 1.051819/1.036060/1.156250 | 1.048382/0.991000/1.250000 |
| 100 | PROJECTED_MOVEMENT_PATTERN_PERFECT | 304,267 | 32/0/0 | 0.036105/0.000921/0.000000 | 0.066357/0.003142/0.000000 |
| 100 | PROJECTED_MOVEMENT_PATTERN_PERFECT_PATH_MOVED | 830 | 0/32/0 | 0.952313/0.741968/1.395312 | 1.377027/1.264066/2.142187 |
| 200 | GATE_PERFECT | 26,510 | 32/0/0 | 0.038990/0.002119/0.000000 | 0.038990/0.002119/0.000000 |
| 200 | GATE_PERFECT_PATH_MOVED | 60 | 0/25/7 | 1.000000/1.000000/1.000000 | 1.000000/1.000000/1.000000 |
| 200 | PROJECTED_MOVEMENT_PATTERN_PERFECT | 47,798 | 32/0/0 | 0.002046/0.000067/0.000000 | 0.036260/0.002201/0.000000 |
| 200 | PROJECTED_MOVEMENT_PATTERN_PERFECT_PATH_MOVED | 71 | 0/24/8 | 0.083333/0.083333/0.083333 | 1.000000/1.000000/1.000000 |

H=25의 GATE_PERFECT_PATH_MOVED는 32개 모두 full descriptive support이고 전체 rollout 실패와 달리 세 metric 모두 개선했다.
H=50에서는 그 support가 5개 작업뿐이며, H=100은 전부 small, H=200은 25 small/7 empty다.
ALL gate-perfect는 STATIC path가 대부분이다. H=100에서 223,520 중 PATH_MOVED는 1,023, H=200에서는 26,510 중 60뿐이다.
따라서 ALL의 작은 RMSE나 일부 strict residual 증가를 모든 움직인 경로의 Stage2 대실패로 확대하지 않는다.
H=200 gate-perfect는 저장된 HOLD와 metric이 같으며 강한 Stage2 단독 실패 증거가 아니다.

고정 판정에서 gate-perfect 개선/전체 악화는 H25 32개, H50 2개 작업에서 지원됐다.
Nonexclusive magnitude residual risk는 H50 12개, H100 21개에서 지원됐다. 이는 any strict metric excess 조건이며
효과가 크거나 통계적으로 유의하다는 뜻이 아니다. Context drift association은 모든 horizon의 32개 작업에서 지원됐다.
단일 원인을 확정하거나 terminal RMSE를 gate/Stage2에 인과적으로 배분할 수 없으므로 mixed review를 권고한다.

## Feedback association과 streaks

P(gate MOVE at next step | projected MOVE/STATIC), 그리고 observed TRUE MOVE의 대응 conditional probability를 보존했다.
아래 값은 event-count 합계의 조건부 비율이며 겹치는 job/path 관측을 포함한다. Within-path adjacent step만 사용한다.
이것은 conditional association이다. 실제 projected movement -> 다음 z의 연결만 기계적으로 정확하다.

| Fold | H | Gate next given projected MOVE | Gate next given projected STATIC | True next given true MOVE | True next given true STATIC |
| --- | --- | --- | --- | --- | --- |
| FOLD_A | 25 | 100.000% | 31.852% | 43.784% | 9.191% |
| FOLD_A | 50 | 100.000% | 33.270% | 43.324% | 9.143% |
| FOLD_A | 100 | 100.000% | 35.002% | 42.544% | 9.040% |
| FOLD_A | 200 | 100.000% | 36.143% | 41.371% | 8.917% |
| FOLD_B | 25 | 100.000% | 0.625% | 44.428% | 9.594% |
| FOLD_B | 50 | 100.000% | 0.622% | 44.302% | 9.616% |
| FOLD_B | 100 | 100.000% | 0.667% | 44.129% | 9.636% |
| FOLD_B | 200 | 100.000% | 0.694% | 44.103% | 9.660% |

Streak는 path 경계에서 reset하며, projected context streak는 initial observed context와 직전 projected movement를 사용한다.

| Fold | H | Streak | Count sum | Median | p95 | Max |
| --- | --- | --- | --- | --- | --- | --- |
| FOLD_A | 25 | observed_context | 6,339,493 | 1.000000 | 4.000000 | 25 |
| FOLD_A | 25 | predicted_gate_move | 2,413,761 | 15.000000 | 25.000000 | 25 |
| FOLD_A | 25 | projected_context | 1,942,345 | 1.000000 | 24.000000 | 25 |
| FOLD_A | 25 | projected_move | 1,809,163 | 1.000000 | 25.000000 | 25 |
| FOLD_A | 25 | true_move_streak | 6,341,128 | 1.000000 | 4.000000 | 25 |
| FOLD_A | 50 | observed_context | 11,549,590 | 1.000000 | 4.000000 | 50 |
| FOLD_A | 50 | predicted_gate_move | 3,314,328 | 3.000000 | 50.000000 | 50 |
| FOLD_A | 50 | projected_context | 2,785,501 | 1.000000 | 47.000000 | 50 |
| FOLD_A | 50 | projected_move | 2,658,108 | 1.000000 | 48.000000 | 50 |
| FOLD_A | 50 | true_move_streak | 11,551,494 | 1.000000 | 4.000000 | 50 |
| FOLD_A | 100 | observed_context | 20,821,861 | 1.000000 | 4.000000 | 66 |
| FOLD_A | 100 | predicted_gate_move | 5,118,777 | 2.000000 | 100.000000 | 100 |
| FOLD_A | 100 | projected_context | 4,259,729 | 1.000000 | 56.000000 | 100 |
| FOLD_A | 100 | projected_move | 4,144,681 | 1.000000 | 57.000000 | 100 |
| FOLD_A | 100 | true_move_streak | 20,822,752 | 1.000000 | 4.000000 | 66 |
| FOLD_A | 200 | observed_context | 36,868,346 | 1.000000 | 4.000000 | 66 |
| FOLD_A | 200 | predicted_gate_move | 8,500,564 | 2.000000 | 200.000000 | 200 |
| FOLD_A | 200 | projected_context | 6,743,899 | 1.000000 | 56.000000 | 200 |
| FOLD_A | 200 | projected_move | 6,640,503 | 1.000000 | 57.000000 | 200 |
| FOLD_A | 200 | true_move_streak | 36,869,279 | 1.000000 | 4.000000 | 66 |
| FOLD_B | 25 | observed_context | 8,680,063 | 1.000000 | 4.000000 | 25 |
| FOLD_B | 25 | predicted_gate_move | 988,881 | 2.000000 | 25.000000 | 25 |
| FOLD_B | 25 | projected_context | 733,754 | 2.000000 | 25.000000 | 25 |
| FOLD_B | 25 | projected_move | 499,521 | 8.000000 | 25.000000 | 25 |
| FOLD_B | 25 | true_move_streak | 8,680,489 | 1.000000 | 4.000000 | 25 |
| FOLD_B | 50 | observed_context | 16,520,687 | 1.000000 | 4.000000 | 41 |
| FOLD_B | 50 | predicted_gate_move | 1,339,216 | 1.000000 | 50.000000 | 50 |
| FOLD_B | 50 | projected_context | 804,577 | 2.000000 | 50.000000 | 50 |
| FOLD_B | 50 | projected_move | 578,512 | 4.000000 | 50.000000 | 50 |
| FOLD_B | 50 | true_move_streak | 16,521,419 | 1.000000 | 4.000000 | 42 |
| FOLD_B | 100 | observed_context | 31,136,746 | 1.000000 | 4.000000 | 41 |
| FOLD_B | 100 | predicted_gate_move | 2,135,020 | 1.000000 | 55.000000 | 100 |
| FOLD_B | 100 | projected_context | 977,747 | 1.000000 | 98.000000 | 100 |
| FOLD_B | 100 | projected_move | 763,255 | 2.000000 | 100.000000 | 100 |
| FOLD_B | 100 | true_move_streak | 31,138,175 | 1.000000 | 4.000000 | 42 |
| FOLD_B | 200 | observed_context | 57,109,758 | 1.000000 | 4.000000 | 40 |
| FOLD_B | 200 | predicted_gate_move | 3,557,852 | 1.000000 | 42.000000 | 200 |
| FOLD_B | 200 | projected_context | 1,315,656 | 1.000000 | 101.000000 | 200 |
| FOLD_B | 200 | projected_move | 1,118,156 | 1.000000 | 110.000000 | 200 |
| FOLD_B | 200 | true_move_streak | 57,110,724 | 1.000000 | 4.000000 | 40 |

## d / L 구조별 descriptive trends

동일 anchor로 교차 L/d를 재평가하지 않았다. Eligibility/population이 달라질 수 있으므로 아래는 group job 평균이며 인과 효과나 hyperparameter 선택이 아니다.

| Axis | Value | Prev STATIC DEV AUC | Prev MOVE DEV AUC | FPR | FNR | H200 context divergence | H200 RMSE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| d | 0 | 0.545504 | 0.576989 | 25.299% | 43.815% | 17.684% | 48.291815 |
| d | 5 | 0.545749 | 0.575377 | 25.115% | 43.960% | 17.280% | 45.725843 |
| d | 10 | 0.546412 | 0.574037 | 26.104% | 43.380% | 16.955% | 41.977407 |
| d | 20 | 0.545795 | 0.570738 | 26.728% | 43.123% | 17.216% | 42.987959 |
| L | 1 | 0.551311 | 0.572977 | 24.638% | 44.287% | 17.530% | 43.223238 |
| L | 5 | 0.548035 | 0.581061 | 25.112% | 43.933% | 17.301% | 46.970584 |
| L | 15 | 0.545568 | 0.577252 | 26.204% | 43.293% | 16.964% | 42.535257 |
| L | 45 | 0.538547 | 0.565852 | 27.291% | 42.764% | 17.339% | 46.253944 |

L이 길어질수록 모든 metric이 좋아지는 일관된 패턴은 없다. STATIC AUC 저하/FPR 증가와 FNR 감소가 함께 나타나며 rollout RMSE는 비단조적이다. d도 단일 방향의 공통 개선이 아니다. 후보 ranking/선택은 하지 않았다.

## Mechanism states와 단일 다음 검토

- `V4_STATIC_FALSE_MOVEMENT_EXACT_HIT_LOSS_SUPPORTED`
- `V4_WITHIN_STATE_RANKING_IMPROVEMENT_SUPPORTED`
- `V4_STAGE1_GATE_MISMATCH_LONG_HORIZON_RISK_SUPPORTED`
- `V4_STAGE2_OR_MAGNITUDE_RESIDUAL_RISK_SUPPORTED`
- `V4_RECURSIVE_CONTEXT_DRIFT_ASSOCIATION_SUPPORTED`
- `V4_MIXED_GATE_AND_MAGNITUDE_FAILURE_SUPPORTED`

각 state는 위에 명시한 job/horizon/subset 범위의 근거다. Within-state improvement는 일부 STATIC와 모든 MOVE context 작업에 해당하며 universal improvement가 아니다.

권고하는 단일 다음 검토는 **`MIXED_STAGE1_STAGE2_ARCHITECTURE_REVIEW`**이다. 이 increment에서는 V5 설계나 변경을 시작하지 않는다.

## Validation method and actual results

Both independent attribution replicas: 32/32 COMPLETE; byte-exact repeatability PASS; verify-only resume both PASS, recompute_calls=0.
Source/V4 actual/V1 reference/source-manifest immutability PASS; source writes=0. Original actual replicas and both attribution replicas retained.

The legacy full runner uses unittest discovery: 5,018 tests passed. The new 95 pytest cases passed separately and are now an explicit exact-HEAD CI step with CI-only pinned pytest 9.1.1 (the already-existing local version). The actual local analysis environment was not changed. The combined pytest suite includes all 2,254 empirical cases. An initial Ruff failure was an unused variable in a new test; removing it was followed by another 95-case pass and Ruff PASS. No bound analysis source changed.

Publication validation status: **PASS**.

| Check | Exit | Tests/items |
| --- | --- | --- |
| attribution_after_test_cleanup | 0 | 95 |
| attribution_focused | 0 | 95 |
| combined | 0 | 2254 |
| compileall | 0 | None |
| diff-check | 0 | None |
| full | 0 | 5018 |
| initial_schema_guard_repair | 0 | - |
| json | 0 | 762 |
| known_input_metadata_identity | 0 | - |
| lateral | 0 | 16 |
| prior | 0 | 315 |
| publication | 0 | None |
| ruff | 0 | None |
| scons | 0 | None |
| source_code_and_historical_public_immutability | 0 | - |
| v4_actual | 0 | 12 |
| v4_executor | 0 | 64 |
| validation_driver | 0 | - |

| Independent review | Status | Report SHA256 |
| --- | --- | --- |
| authority | PASS | 386c9283e60e633e1c7999ae983ca0e340abdf0115e1eb004c966dcbb6016ec6 |
| numerical | PASS | a5f30dc1f7dd9dcd3d7a1109bd3e78fd527639247f1e14f59956d53769df857c |

The initial attribution attempt stopped at the privacy boundary before saving its first job because aggregate streak key `true_move`
collided with a raw-array prohibition. The aggregate key became `true_move_streak`; the prohibition was retained.
A synthetic RED-to-GREEN test covers the complete aggregate schema. Reversing the key rename and formatter line wrapping
recovers the exact old math-source SHA256. Policy receipt and input snapshots are unchanged. The incomplete attempt/input lock
are retained; the two successful runs use a new clean E sink/new lock. No numerical rule or model policy changed.

All forbidden-operation counters remain zero:
MODEL_REFIT_CALLS, NORMALIZER_REFIT_CALLS, STAGE2_REFIT_CALLS, THRESHOLD_RESELECTION_CALLS,
PREDICTION_REPLAY_CALLS, ROLLOUT_REGENERATION_CALLS, SELECTION_CALLS, CANDIDATE_SEARCH_CALLS,
RAW_LOG_OPENINGS, QLOG_OPENINGS, HOLDOUT_OPENINGS, HOLDOUT_DISCOVERY, SOURCE_WRITE_COUNT.
Regression fits/inference, where exercised by historical tests, use isolated synthetic fixtures and never actual private inputs.

Replay vs baseline, new closed-loop simulation and shadow/vehicle tests are not applicable and were not newly executed.
Saved retrospective paths were inspected; no replay/path regeneration occurred. Rollback is reverting this additive analysis/publication,
not changing/deleting original scientific evidence. No upstream runtime integration points or safety limits changed.

## Authority and final handoff

Actual threshold values and coefficients remain private. No per-row probability/tick/path/gate/command/timestamp/GPS/witness rows are public.
Hugging Face NOT_REQUIRED / NOT_USED.
HOLDOUT CLOSED; opening_count=0; holdout_discovery=0.
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED; NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT;
FINAL_POOLED_REFIT_NOT_AUTHORIZED; COMPOSITION_NOT_AUTHORIZED.
Vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED; authority NONE.
No V5 design, threshold change, model/normalizer/Stage2/pooled refit, rollout restructuring, controller integration or vehicle work follows automatically.
