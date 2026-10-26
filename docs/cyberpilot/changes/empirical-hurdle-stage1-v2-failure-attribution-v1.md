# Hurdle Stage1 V2 residual failure attribution

V2 threshold는 V1보다 32개 모든 job의 exact-hit를 개선했지만, 매우 보수적인
gate를 선택해 DEVELOPMENT MOVE의 약 97–100%를 놓쳤다. 이번 분석은
분류 score의 MOVE/STATIC 순위정보와 선택된 threshold의 결과를 분리한다.
남은 exact-hit 손실과 놓친 MOVE의 크기·방향, 저장된 장기 경로도 함께 확인한다.

새 모델이나 threshold를 만들지 않는다. 아래 결과는 기존 V1/V2 evidence를
읽어서 얻는 retrospective descriptive diagnostics이며 candidate 재선택 권한이 없다.

## Identity and purpose

- Area: Cyber Validation / AutoTune; HURDLE_STAGE1_V2_FAILURE_ATTRIBUTION_V1.
- Branch: feature/cyber-autotune.
- Baseline: 6176dbef998e7957f9ef1a605c081ced0857cb7b; startup exact-HEAD CI SUCCESS.
- Scope: 16 structures × 2 ordered route folds; four stored rollout horizons.
- Status: HURDLE_STAGE1_V2_FAILURE_ATTRIBUTION_V1_COMPLETE; READ_ONLY_ATTRIBUTION_COMPLETE.
- Source V1 manifest: c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6.
- Source V2 manifest: 7d28c7d07c72a1080e6769165af8539f3568e14688b82f782d0d29aed8d84b9b.
- Vehicle applicability: none. Model fitting, threshold reselection, replay,
  rollout regeneration, candidate selection and HOLDOUT access are forbidden.

## Original references and traced inputs

Source repository: https://github.com/rownlvh8875-coder/CyberPilot, branch and
exact baseline above. Reuse the repository's empirical_hurdle_attribution_io,
empirical_hurdle_attribution_math and aggregate schema helpers under the existing
repository license. No upstream code, submodule SHA or dependency changes.

Manifest admission → full source file hash verification → receipt-bound gzip
decode with compressed/NPY/content SHA, dtype, shape and C-order checks → aggregate
attribution → immutable per-job receipts → summary/readiness → manifest-last.
Two independent runs reread immutable inputs. Each run hashes both source stores
before and after analysis. Source bytes are never written.

TRAIN scores use the saved V1 TRAIN probability array, whose content SHA must
equal the V2 replay probability identity. V2 saved TRAIN gates and projected ticks
are read directly. TRAIN truth comes only from the same candidate's opposite-fold
V1 DEVELOPMENT truth: anchor SHA and ordered route/segment/run/index identities
must match exactly. Opposite-fold models, probabilities and gates are not borrowed.
DEVELOPMENT V1/V2 probability bytes must match.

V2 did not persist per-row continuous TRAIN Stage2 predictions, only their SHA.
TRAIN continuous feasibility slack therefore uses the immutable selected metrics
and the stored truth's HOLD_LAST metrics. It never reconstructs a missing output.
The selected private V2 threshold is read only to validate stored gate identity;
no alternative threshold is evaluated and its number is never published.

## Changes and diagnostic semantics

Three additive modules provide mathematical reductions, admitted read-only
execution/resume and aggregate publication. Synthetic tests cover exact ranking,
integer hit identities, magnitude/sign partitions, persistence and execution traps.
No actuator or control caller is added. Existing numerical artifacts remain immutable.

Exact-hit counts obey MOVE_HIT_GAIN − STATIC_HIT_LOSS = candidate hits − HOLD_LAST
hits. One-tick/multi-tick and positive/negative are separate overlapping axes.
FN delta is zero, projected tick equals current tick and continuous error bytes
equal HOLD_LAST. TP projected exactness and signed delta correctness describe
the already executed Stage2 branch. Within-one-tick changes are partitioned into
STATIC projected motion/hold, one-tick FN, multi-tick FN and TP; FN contributes
zero change relative to HOLD_LAST, verified from integer ticks.

AUC uses ascending exact score groups and Python integer pair counts:
AUC_NUM2 = 2 × concordant pairs + tied pairs; AUC_DEN2 = 2PN. No pair matrix,
threshold search, calibration fit, quantization or epsilon is used. Chance and
TRAIN→DEV rank comparisons use exact integer fractions; floats are for reporting.
Brier and score means preserve the original contiguous float64 row order.

The only suppression cutoff is the user's explicit missed-move rate > 0.95.
No arbitrary "good AUC" cutoff is introduced. Classifier review support is
predeclared as at least one job with TRAIN AUC > 0.5 and DEVELOPMENT AUC ≤ 0.5.
This narrow route-transfer signal is review evidence, not significance, causality
or proof that another classifier would succeed. Threshold-policy review requires
32/32 exact-hit improvements, historical NO_ADMISSIBLE and 32/32 extreme suppression.

Rollout analysis uses stored observed/projected/HOLD_LAST/gate paths only. True
gate means adjacent observed ticks differ. First mismatch and first departure
from HOLD_LAST use one-based steps; zero denotes no event. Every horizon retains
separate ALL, PATH_MOVED, any/no predicted MOVE and gate-perfect subsets. Nonempty
support below 201 is SMALL_SUPPORT_DESCRIPTIVE_ONLY; zero is EMPTY. Adequate support
without regression is distinguished from insufficient support. No Stage2 redesign
is automatically authorized by these diagnostics.

## Observed exact-hit and MOVE mechanisms

All 32 jobs improved exact-hit relative to V1 by reducing STATIC hit loss more
than the accompanying reduction in MOVE hit gain. MOVE hit gain did not increase:
Fold A lost 5,004–8,487 MOVE hits while avoiding 16,228–46,830 STATIC losses;
Fold B lost 892–1,629 MOVE hits while avoiding 1,832–3,766 STATIC losses.
These are per-job ranges, not pooled counts or candidate rankings.

| DEVELOPMENT evidence | Fold A, 16 jobs | Fold B, 16 jobs |
| --- | --- | --- |
| Exact-hit failures | 16 | 2 |
| Complete frozen gate passes | 0 | 14 |
| STATIC hit loss | 6–586 | 1–10 |
| MOVE hit gain | 5–211 | 0–75 |
| Exact-hit deficit among failing jobs | 1–375 | 1 in each failing job |
| Exact-hit surplus across all jobs | 0 | 0–68 |
| Within-one-tick failures | 10 | 0 |
| Missed MOVE rate | 96.8248–99.9422% | 99.4070–99.9899% |
| Predicted MOVE fraction | 0.013064–0.788186% | 0.001859–0.092649% |
| True MOVE fraction | 14.0966–14.4686% | 14.3144–14.7662% |

The remaining 18 exact-hit failures satisfy the integer identity
STATIC_HIT_LOSS > MOVE_HIT_GAIN. Residual false projected motion therefore still
costs more exact hits than the few correctly projected MOVE rows recover. FN rows
are HOLD_LAST-identical: their error is a missed opportunity, not an additional
loss relative to HOLD_LAST. The analysis does not assume that opening those gates
would have produced correct Stage2 predictions.

One-tick MOVE accounts for 76.91–78.79% of FN in Fold A and 78.48–79.78% in Fold B;
the remainder is multi-tick MOVE. Negative MOVE accounts for 49.36–51.17% and
49.37–49.74%, respectively. Misses occur in both directions. TP support is only
16–1,172 rows in Fold A and 4–243 in Fold B. Conditional projected exactness is
7.14–31.25% and 0–40%; within-one-tick rates are 20–83.33% and 5.56–80%.
These conditional rates describe selected TP rows, not all MOVE or an oracle claim.

One-tick FN remains within one tick; multi-tick FN does not. Both have exactly zero
within-one-tick change relative to HOLD_LAST. The ten failing jobs' net count is
fully reconciled from STATIC projected-motion loss and TP Stage2 changes, with
all magnitude/sign and TP/FN counts available in the public decomposition artifacts.
Historical true-MOVE RMSE/MAE/p95 protection remains 32/32 PASS.

## Score ranking, transfer and selected decision

| Score diagnostic | Fold A | Fold B |
| --- | --- | --- |
| TRAIN AUC | 0.589778–0.595460 | 0.562527–0.568209 |
| DEVELOPMENT AUC | 0.560425–0.575462 | 0.548629–0.561169 |
| TRAIN → DEVELOPMENT AUC decreased | 16/16 | 16/16 |
| TRAIN Brier | 0.120657–0.123816 | 0.118064–0.121263 |
| DEVELOPMENT Brier | 0.122804–0.123714 | 0.121143–0.124871 |
| DEVELOPMENT mean probability minus prevalence | +0.028596 to +0.042141 | −0.025724 to −0.014840 |
| DEVELOPMENT MOVE-minus-STATIC mean score | +0.012950 to +0.019350 | +0.009958 to +0.012282 |

Ranking decreased across routes in every job but remained above chance in every
job. The predeclared classifier-review condition, TRAIN above chance followed by
DEVELOPMENT at/below chance, has zero qualifying jobs. This does not establish
that the classifier generalizes adequately; it avoids treating modest AUC as an
arbitrary redesign cutoff. The score-transfer artifact publishes integer pair
numerators/denominators and per-job comparisons.

The selected decisions meet EXTREME_MOVE_SUPPRESSION in 32/32 jobs. Thus retained
rank information and sparse MOVE decisions coexist. Threshold-policy review is
supported by the exact predeclared conjunction; classifier redesign is not triggered
by this narrower condition. Class imbalance is visible in the 14–15% MOVE prevalence,
but this read-only analysis cannot prove it caused the objective to select these
decisions. No alternative threshold or objective was evaluated.

Selected TRAIN feasibility slack is also asymmetric. Fold A ALL RMSE improvement
is 0.000004041–0.031979, MOVE RMSE slack 0.000180–0.084435, MOVE MAE slack
0.00008194–0.026862, and MOVE p95 slack exactly zero. Fold B values are
0.072145–0.132762, 0.190065–0.354402, 0.040361–0.102032 and 0–0.010452,
respectively. These saved selected-threshold facts do not evaluate any rescue
threshold. Fold A/B gate asymmetry therefore cannot be reduced to rank alone:
Fold A actually has the higher DEVELOPMENT AUC range, yet no complete gate pass.

## Stored rollout evidence

Across jobs, HOLD_LAST-identical full paths account for 98.54–100% at 25 steps,
98.47–100% at 50 steps, 98.47–100% at 100 steps and 98.52–100% at 200 steps.
No-predicted-MOVE paths are verified HOLD_LAST-identical, with zero endpoint
SAE/SSE change. ANY_PREDICTED_MOVE paths carry the endpoint change.

The five 200-step RMSE/MAE regressions are all Fold A. The following table is in
historical lexical order and describes failure mechanisms only.

| Candidate | HOLD_LAST-identical paths | ANY_MOVE support | ANY_MOVE delta SSE | First FP / first FN / no mismatch |
| --- | --- | --- | --- | --- |
| HRI_D00_L45 | 99.9210% | 116 | +6,792 | 7 / 143,453 / 2,156 |
| HRI_D05_L45 | 99.9021% | 149 | +2,252 | 10 / 142,962 / 2,148 |
| HRI_D10_L15 | 99.9110% | 132 | +16,146 | 6 / 146,119 / 2,199 |
| HRI_D20_L05 | 99.8921% | 162 | +22,789 | 10 / 146,115 / 2,199 |
| HRI_D20_L15 | 99.9000% | 148 | +4,668 | 8 / 144,821 / 2,186 |

In those five jobs, predicted MOVE event counts have median/p95 zero and maximum
3–5; FN counts have median 21, p95 67–68 and maximum 139; FP counts have median/p95
zero and maximum 1–2. Sparse interventions explain where the additional endpoint
SSE is located, without proving whether a different gate or delta model would fix it.
All five ANY_MOVE supports are SMALL_SUPPORT_DESCRIPTIVE_ONLY.

GATE_PERFECT PATH_MOVED support across all 32 jobs ranges from 0–210 at 25 steps,
0–36 at 50, 0–2 at 100 and exactly zero at 200. No 50/100/200-step job reaches 201.
There is no adequately supported long-horizon gate-perfect population here to
isolate a Stage2 residual regression. The review state is
INSUFFICIENT_GATE_PERFECT_SUPPORT; STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS.
Per-job V1/V2 event-count and HOLD_LAST-path comparisons are report-only.

## Regression risk and acceptance

Risks: mismatched crossfold truth, threshold leakage, byte-order drift, missing
payloads, incomplete saved aggregates and overinterpretation of sparse paths.
Admission rejects wrong manifests/jobs/anchors, corrupted compression and missing
required inputs. There is no causal/derived/raw fallback. All 32 historical gate
failure counts must reconcile exactly, including 18 exact-hit and 10 within-one-tick
failures, Fold A 0/16 and Fold B 14/16 complete passes.

Resume verifies saved aggregate schemas, manifest file hashes, source identity
references, policy/source-code identity and fixed readiness authority while source
loaders, gzip decoder and attribution computation are hard-trapped. No analysis is
recomputed during resume. Rollback removes only this additive increment.

## Validation method and actual results

| Check | Method | Result |
| --- | --- | --- |
| Focused synthetic | pytest test_empirical_hurdle_v2_attribution.py | 36 passed |
| Two actual attribution runs | Exact V1/V2 stored evidence, aggregate-only output | 32/32 each; source hashes unchanged |
| Repeatability and trapped resume | All saved receipt/manifest bytes; no source decoding on resume | BYTE_EXACT_PASS; VERIFY_ONLY_RESUME_PASS |
| Combined empirical / full AutoTune and controls | Repository test suites | 1,768 + 625 subtests / 4,627 passed |
| Lateral replay / Ruff / compileall / SCons | Existing toolchain | 16 replay tests; all PASS |
| JSON / publication / privacy / diff | Strict public schema and repository audit | PASS; 15 new public artifacts |
| Independent review | Source/synthetic remediation, actual aggregates, documentation and all 15 public objects | PASS; no substantive findings remain |
| Prediction / model fit / regeneration / shadow / vehicle | Outside authorized scope | NOT_RUN |

The rollout aggregate JSON is serialized compactly after publication generation
(equivalent to Python's `json.tool --compact`). Only whitespace changes: parsed
content and the canonical receipt remain identical. Its 828,267 bytes fit the
existing 1 MiB publication scanner limit, so the entire content is scanned.
No field is omitted and no scanner limit or exclusion is changed.

## Handoff

Machine-readable evidence: [policy](empirical-hurdle-stage1-v2-failure-attribution-policy.json),
[exact-hit](empirical-hurdle-stage1-v2-exact-hit-decomposition.json),
[MOVE misses](empirical-hurdle-stage1-v2-move-miss-decomposition.json),
[score ranking](empirical-hurdle-stage1-v2-score-ranking.json),
[transfer](empirical-hurdle-stage1-v2-score-transfer.json),
[conservatism](empirical-hurdle-stage1-v2-decision-conservatism.json),
[selected slack](empirical-hurdle-stage1-v2-feasibility-slack.json),
[folds](empirical-hurdle-stage1-v2-fold-asymmetry.json),
[rollout](empirical-hurdle-stage1-v2-rollout-attribution.json),
[200-step](empirical-hurdle-stage1-v2-long-horizon-attribution.json),
[mechanisms](empirical-hurdle-stage1-v2-mechanism-summary.json),
[review signals](empirical-hurdle-stage1-v2-next-design-trigger.json),
[repeatability](empirical-hurdle-stage1-v2-failure-attribution-repeatability.json),
[readiness](empirical-hurdle-stage1-v2-failure-attribution-readiness.json), and
[validation](empirical-hurdle-stage1-v2-failure-attribution-validation.json).

Both runs have manifest 97fbc181a8e4ab53ac4cafe7cb0da60990a86502f9360b468f6c8a68c550b284.
Repeatability receipt: 3ed64b2f26d94731973495a6c59505c4cab9bd570b50d4dbef3f54b591c9c7db.
The complete private aggregate output occupies 3,795,083 bytes; source arrays and
paths were not duplicated. All prohibited execution/opening counters are zero.

Historical V1
HURDLE_NO_ADMISSIBLE_CANDIDATE and V2 HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE
remain MODEL_SELECTION_FAILED_CLOSED. No new candidate ranking or counterfactual
admission is produced. STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS.

HOLDOUT remains CLOSED, opening/discovery zero; FINAL_POOLED_REFIT_NOT_AUTHORIZED
and NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT remain. Vehicle authority is NONE:
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED. No V3, calibration
model, nonlinear classifier, Stage2 redesign, controller integration or vehicle
execution starts automatically.
