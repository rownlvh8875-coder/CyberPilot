# Hurdle Stage1 V3 retrospective execution

V3에서는 새 모델을 학습하지 않았다. V1의 Stage1/Stage2 모델과 normalizer를
한 바이트도 바꾸지 않고 재사용했다. 달라진 것은 TRAIN에서 threshold를 고를 때
**V1이 잡았던 MOVE TP 이상을 유지해야 한다**는 이미 동결된 조건뿐이다.

두 번의 독립 실행 결과는 byte-exact로 같았다. 32개 job 중 31개는 평가를
완료했고, 1개는 feasible threshold가 없어 fallback 없이 닫혔다.
평가된 31개 모두 V2보다 missed-MOVE가 줄었지만 exact-hit는 나빠졌다.
Fold A와 Fold B 모두 전체 gate 통과가 0/16이었으므로 **admissible 0개,
selected candidate null**이다. 이 결과로 새 설계나 차량 적용을 시작하지 않는다.

## Identity and scope

Cyber Validation; branch `feature/cyber-autotune`. Execution HEAD:
`4835c148c74fcd841c467004aca70cc82dabcc47`. Its exact-HEAD
[Actions run 38512367120](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/38512367120)
completed successfully before the external authorization was created.
Baseline `3acd6543eff2b88b8128f6fb71a2b60f08ac5617` remains an ancestor.

Same repository and license, no new dependencies or submodule changes.
The additive E storage amendment is separate from the frozen decision policy.
No numerical implementation changed during execution. Model class, coefficients,
normalizers, features, 16 structures, folds, anchors, projection, rollout,
32-clause gate, both-fold admission and selection are unchanged.

## Source, migration and authorization

The authoritative successful V1 manifest remains
`c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6`.
Migration verified only declared members against existing migration records and
authoritative manifests: **23,273 members / 2,677,113,133 bytes**. Causal/derived
payloads inside the E-backed WSL image were also transported to explicitly
recorded direct-E roots, preserving originals. No arrays were reconstructed,
refitted or re-extracted from raw logs. No filesystem-wide source scan occurred.

Migration receipt:
`f147cb4121a5e34f57d663c8fa631ab26805d30c9157515802f7a0cf7529adc9`.
Storage amendment receipt:
`5b109186575c4b50b7095a4e99d6028fd8a8f21e4e944fb6ca5ec59d6a4a26e5`.
The admitted storage is **E_EXTERNAL_SSD**, with exact kernel mount and live
Windows volume identity, explicit non-overlapping roots, and capacity preflight.
Required upper bound including both runs, atomic peak, metadata and reserve:
**17,638,766,452 bytes**. Available capacity exceeded this bound.

Authorization was minted by a one-shot process outside the executor after
amendment commit/push/clean exact-HEAD CI success. It opened zero numeric arrays.
Trusted authorization receipt:
`6540a48e484a125b42f458be9ff1f147d4600bdb457ff9225c175000dce40601`.
It binds the execution HEAD/code, base policy receipts, migration/amendment,
source file sets, all model/normalizer receipts, 32 job/reference/anchor bindings,
four root identities, live volume, runtime, capacity, compression and firewall.
The executor has no authorization-minting command or implicit trusted receipt.

Python **3.12.13**, NumPy **2.5.3**, OpenBLAS/OMP threads **1**, float64, C-order,
RNG NONE. Pinned BLAS identity:
`704bde2afe24c22d171cc7d2508517db81b7db455743b2cb0e5de9dda88da7a2`.

## Frozen execution and TRAIN decision

Each run independently replayed the exact V1 Stage1 model on exact TRAIN anchors.
Saved receipt-bound V1 TRAIN probability arrays were compared byte-exact wherever
present. Stage2 used its unchanged MOVE-only TRAIN normalizer and coefficients
to predict deltas for **all TRAIN anchors**, including STATIC rows.

The threshold candidate set remains the sorted unique union of 0, 1 and finite
TRAIN probabilities. MOVE iff probability is strictly greater than threshold.
Feasibility requires all five frozen conditions:

1. TRUE-MOVE RMSE <= HOLD_LAST.
2. TRUE-MOVE MAE <= HOLD_LAST.
3. TRUE-MOVE p95 <= HOLD_LAST.
4. ALL RMSE < HOLD_LAST.
5. Python-int selected TP >= immutable candidate/fold V1 TRAIN reference TP.

The exact reference guard remains `20 * reference_tp > positive_count`.
References were verified, never recomputed or tuned. Feasible thresholds use
the frozen order: maximum projected exact-hit count, minimum STATIC projected
false movement, maximum within-one-tick count, then maximum threshold.
There is no epsilon, default, alternative objective, relaxed constraint or fallback.
p95 retains exact NumPy linear-percentile semantics and the existing bounded V2
numeric primitives. Canonical check thresholds and the selected threshold were
verified by the frozen executor.

The threshold receipt was finalized before DEVELOPMENT was opened. DEVELOPMENT
and all four recursive rollout horizons used identical V1 anchors and models,
with only the V3 gate changed. Future measured ticks/deltas/labels were scoring
inputs only. Logged exogenous input advance and projected-history recursion
retain the frozen semantics. No oracle output influenced admission.

## Job accounting and no-feasible result

Both independent runs recorded the same 32 jobs in lexical candidate order,
Fold A then Fold B: **31 EXECUTED_COMPLETE + 1 NO_FEASIBLE_THRESHOLD**.

`HRI_D20_L01 / FOLD_A` has no feasible threshold. Its threshold is null,
feasible count is zero, and its DEVELOPMENT/rollout metrics were **not evaluated**.
All 32 clauses fail closed for this job. No V1/V2 threshold, 0.5, refit or
second-choice fallback was used. The remaining jobs continued without a
performance early stop.

All **31 finalized thresholds satisfy the TP reference constraint**. Public
threshold receipts expose reference/selected TP and aggregate objective counts;
actual threshold values remain private.

## DEVELOPMENT and direct comparison

V1/V2/V3 comparisons are report-only, using the same candidate/fold/anchors.
Historical DEVELOPMENT results never entered V3 threshold selection.
This isolates a retrospective threshold-policy comparison; it is not independent
causal or vehicle validation.

| Measure | Fold A | Fold B |
|---|---:|---:|
| Job count | 16 | 16 |
| DEVELOPMENT evaluated | 15 | 16 |
| V3 recall range | 57.1627–65.5974% | 7.3977–12.0832% |
| V3 complete gate pass | 0/16 | 0/16 |
| Historical V2 complete gate pass | 0/16 | 14/16 |

Against V2, among **31 comparable evaluated jobs**, missed-MOVE improved in 31;
projected exact-hit improved in 0, stayed equal in 0, and worsened in 31.
The no-feasible job is not included in metric-change comparisons.
These are observed tradeoffs, not evidence that the V3 policy solved admission.

A closed-clause failure includes the one unevaluated no-feasible fold.
An evaluated failure is an actual metric comparison. Both counts are published:

| One-step clause | V1 failures /32 | V2 failures /32 | V3 evaluated failures /31 | V3 closed failures /32 |
|---|---:|---:|---:|---:|
| ALL RMSE | 4 | 1 | 3 | 4 |
| ALL MAE | 20 | 1 | 19 | 20 |
| ALL p95 | 16 | 0 | 15 | 16 |
| ALL exact-hit | 32 | 18 | 31 | 32 |
| ALL within-one-tick | 8 | 10 | 7 | 8 |
| TRUE-MOVE RMSE | 0 | 0 | 0 | 1 |
| TRUE-MOVE MAE | 0 | 0 | 0 | 1 |
| TRUE-MOVE p95 | 0 | 0 | 0 | 1 |

Thus TRUE-MOVE protection passed in all **31 evaluated V3 jobs**; the extra
closed failure is unevaluated, not a measured MOVE regression. Historical
32/32 V1/V2 protection records remain unchanged.

## Rollout, gate and selection

All four horizons (25/50/100/200 at 100 Hz) and OVERALL/PATH_MOVED populations are
published per job. The 200-step counts show the remaining long-horizon tradeoff:

| 200-step population/metric | V1 failures /32 | V2 failures /32 | V3 evaluated failures /31 | V3 closed failures /32 |
|---|---:|---:|---:|---:|
| OVERALL RMSE | 21 | 5 | 20 | 21 |
| OVERALL MAE | 22 | 5 | 21 | 22 |
| OVERALL p95 | 18 | 1 | 18 | 19 |
| PATH_MOVED RMSE | 21 | 5 | 20 | 21 |
| PATH_MOVED MAE | 22 | 5 | 21 | 22 |
| PATH_MOVED p95 | 17 | 0 | 17 | 18 |

Every job retains the exact 32-clause V1 gate and both folds are required.
Report-only V1→V3 and V2→V3 transition tables account for all **1,024 clause checks**
per comparison: recovered/newly_failed/unchanged_pass/unchanged_fail.
No-feasible transitions are explicitly marked fail-closed, not observed metric
regressions. No clause was removed and no counterfactual admission was calculated.

The unchanged selector admitted **0 candidates**; selected candidate **null**.
Current states: `HURDLE_STAGE1_V3_NO_ADMISSIBLE_CANDIDATE`,
`MODEL_SELECTION_FAILED_CLOSED`. No inadmissible-candidate ranking or
near-winner claim is published.

## Persistence, repeatability, resume and immutability

Both authoritative replicas are retained. V3-specific evidence uses C-order NPY,
deterministic gzip level 1, mtime zero, no embedded filename, and compressed,
decoded-NPY/content hashes plus dtype/shape/order. V1 models, truth, HOLD_LAST,
anchors and exogenous payloads are referenced rather than duplicated.

Both run manifests:
`1db0c8f383ccb72de184e37ee3d24c17f27c424cc5f8f4cf1b335e75f0c80557`.
**874 manifest-listed files** and their decoded/content identities matched.
Public aggregate projections were also independently compared byte-exact.

Both saved runs passed resume with source/model loaders, predictors, threshold
sweep, DEVELOPMENT, rollout, metric and selection functions trapped:
**recompute 0**. Cleanup eligibility was checked; **deletion 0, repeat-2 retained**.

Full before/after source proof:
`d952790a270e4f135bda0ad73d7bab7f4a4f6571eff4fd009aa0de3cf9976128`.
All **23,273 members / 2,677,113,133 bytes** remained identical. Source, causal,
derived and model writes: **0**. Stage1/Stage2/normalizer refit calls and
raw/qlog/HOLDOUT openings: **0**. Private paths, coefficients, normalizer values,
threshold numbers, probabilities, raw ticks/gates/predictions/paths and commands
are absent from public artifacts.

## Validation and review

Storage amendment: focused 121, combined empirical 1,889, full AutoTune/controls
4,748 and lateral replay 16 passed, with lint/syntax/JSON/privacy/diff/SCons and
independent review. Numerical source files were byte-unchanged.
Historical synthetic D exclusion paths became E aliases after migration;
successful local regressions used a private mount namespace masking D only.
No global mounts, data or historical safety guards were changed.
The actual run used the normal E namespace.

New public-only actual result validation: **10 tests passed**.
Final full AutoTune/controls: **4,758 passed**. Focused V3: **131 passed**
(187 subtests). Combined empirical: **1,899 passed** (812 subtests). Lateral
replay: **16 passed**. Ruff, compileall, JSON, publication/privacy/authority,
diff check and SCons passed. Independent numeric/result and storage/authority/
privacy reviews found no important or blocking findings; both were read-only.
No actual numerical executor was edited after authorization or between runs.

## Authority and handoff

Historical S2-RI, V1 and V2 NO_ADMISSIBLE / FAILED_CLOSED records remain immutable.
`STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS` remains; Stage2 is not independently
validated by this experiment. `NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT`,
`FINAL_POOLED_REFIT_NOT_AUTHORIZED`, `SEARCH_NOT_AUTHORIZED` and
`COMPOSITION_NOT_AUTHORIZED` remain.

HOLDOUT CLOSED; opening/discovery 0; FUTURE_UNTOUCHED_HOLDOUT_REQUIRED.
Vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED;
authority NONE. No V4, calibration model, pooled refit, shadow/controller
integration or vehicle operation was started.

Public receipts and per-job aggregates are in
[readiness](empirical-hurdle-stage1-v3-retrospective-execution-readiness.json),
[thresholds](empirical-hurdle-stage1-v3-threshold-results.json),
[comparison](empirical-hurdle-stage1-v3-v1-v2-comparison.json) and
[repeatability](empirical-hurdle-stage1-v3-repeatability.json).
