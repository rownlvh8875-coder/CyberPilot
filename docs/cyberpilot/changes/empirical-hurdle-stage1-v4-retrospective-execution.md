# Stage1 V4 actual retrospective fitting and CV

The two separately authorized retrospective replicas completed all 32 candidate/fold jobs.
The frozen selector returned **HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE** and
**MODEL_SELECTION_FAILED_CLOSED**. Selected candidate: **null**.

All 64 heads passed fitting preconditions and converged. All 32 jobs received DEVELOPMENT
and 25/50/100/200-step rollout evaluation. No candidate passed all 32 clauses on either fold.

## Execution identity and storage

- EXECUTION_HEAD: `bd8045ef2a0da62a92603439f38e7740f5923622`.
- RESULT_PUBLICATION_HEAD: the Git commit containing this report, resolved in the final
  handoff and exact-commit CI. The containing-commit marker avoids a self-referential Git hash.
- Exact execution-head CI: [completed / success](https://github.com/rownlvh8875-coder/CyberPilot/actions/runs/38665133775).
- External one-shot authorization SHA256: `a23e88b37ba1b2b57f5eb29bc37508166a6a392354826d00bb4444d8efcdc34c`.
- Shared authoritative run manifest SHA256: `fd3639f93944edecfdfa573818d29fbc8a91ab23208e2d561f8a69726eb0dc64`.

| Executor capacity field | Bytes |
| --- | --- |
| atomic_upper_bytes | 309876208 |
| free_bytes | 51654926336 |
| metadata_upper_bytes | 8342693888 |
| required_bytes | 42704404308 |
| reserve_bytes | 2147483648 |
| run1_upper_bytes | 15952175282 |
| run2_upper_bytes | 15952175282 |
| Fresh free after both replicas and full verification | 51017584640 |

Capacity came from the executor's actual capacity(jobs, resource_budget) calculation.
The free-before value was freshly checked before authorization. E_EXTERNAL_SSD identity,
direct mount, exact migration-bound roots and disjoint output root were verified; only
safe identity hashes are public. Both authoritative replicas are retained.

The budget was frozen before numerical access: 395253 certificate integer bits,
134217728 metadata bytes per job, and a 2147483648-byte historical storage reserve.
The pre-execution repair validation records the mathematical bit bound and historical
metadata/reserve provenance. No budget adjustment occurred after observing results.

## Replicas and integrity

| Replica | Completion | Elapsed seconds | Maximum RSS KiB |
| --- | --- | --- | --- |
| repeat-1 | COMPLETE / 32 jobs | 52753.950 | 1922120 |
| repeat-2 | COMPLETE / 32 jobs | 53153.588 | 1972416 |

Byte-exact repeatability: **PASS**. Every authoritative saved file hash and decoded array
identity was verified, including job statuses, coefficients, basis/certificate receipts,
TRAIN scores, threshold receipts, DEV/rollout artifacts, gates, selection and run manifest.
Elapsed time and RSS remain external to scientific identity.

Verify-only resume: **PASS** for both replicas, recompute_calls = **0**. Source/model loaders,
rank/separation generators, Newton, probability, threshold, DEVELOPMENT, recursive rollout
and selector were trapped. Neither authoritative replica was corrupted for testing.

Source immutability: **PASS**, source writes = **0**. All authorized source, causal and derived
manifest members were reverified; V1 model and normalizer bytes remained unchanged.

The actual environment was Python 3.12.13, NumPy 2.5.3, float64 C order, RNG NONE,
OPENBLAS_NUM_THREADS = 1 and OMP_NUM_THREADS = 1. BLAS build identity:
`704bde2afe24c22d171cc7d2508517db81b7db455743b2cb0e5de9dda88da7a2`.
The external grant bound 35 executor source hashes, 23 foundational policy receipts,
13 executor component receipts, all 32 job identities and the storage/environment/capacity proofs.
The executor did not mint the trusted one-shot authorization.

## Job accounting and fitting preconditions

Each replica: EXECUTED_COMPLETE = **32**; V4_STAGE1_FIT_FAILED_CLOSED = **0**;
DEVELOPMENT_OR_ROLLOUT_FAILURE = **0**; ROLLOUT_FAILURE = **0**.
Actual evaluated job count = **32**. No fallback occurred.

| Head | Support pass/fail | Rank pass/fail | No separation/present/inconclusive | Newton converge/fail | Updates |
| --- | --- | --- | --- | --- | --- |
| STATIC | 32/0 | 32/0 | 32/0/0 | 32/0 | 5 to 5 |
| MOVE | 32/0 | 32/0 | 32/0/0 | 32/0 | 3 to 5 |

NOT_REACHED counts, resource-bound failures and numerical failures are zero.
SVD and exact dyadic/Bareiss rank certificates passed; exact non-separation certificates passed.
Both heads were certified before fitting either head. No ridge, Firth, pseudoinverse,
single-head fallback, automatic column dropping or alternate threshold was used.

| L | STATIC parameters | MOVE parameters |
| --- | --- | --- |
| 1 | 4 | 5 |
| 5 | 12 | 13 |
| 15 | 32 | 33 |
| 45 | 92 | 93 |

The STATIC basis retained the intercept and removed only the latest prior-delta structural
column. MOVE retained all V1 effective columns. The V1 TRAIN Stage1 normalizers and
V1 Stage2 model/normalizer were reused byte-identically, with zero refits.

Each job used one global threshold on the new combined original-order V4 TRAIN scores:
strict p > threshold, equality STATIC, maximizing the frozen integer tuple
(BA_NUM, TN, threshold), where BA_NUM = TP*N_negative + TN*N_positive.
TRAIN was durably finalized before DEVELOPMENT access. Actual threshold values and
coefficients remain private. Per-row probabilities, certificate witness integers,
rank row indices and source/rollout sequences are excluded from this publication.

## Gate result and interpretation

Fold A complete gate pass count = **0**; Fold B = **0**; admissible candidates = **0**;
selected candidate = **null**. No near-winner or best failed candidate was selected.

This is a completed predictive-evaluation rejection under the frozen gate. It is not a
fitting-precondition rejection: all heads passed support/rank/non-separation and converged.
TRUE MOVE one-step RMSE, MAE and p95 passed in all 32 jobs, while exact-hit failed in all 32.
OVERALL and PATH_MOVED rollout RMSE failed in all 32 jobs at horizons 50, 100 and 200.
Stage1 discrimination did not establish admissibility for recursive rollout.
No result-driven policy, architecture, regularization, threshold or selector changes occurred.

delta_tick denotes source-grid tick increment/change, not physical EPS movement.
Logged command denotes post-CarController normalized command, not proven physical applied
EPS torque. steeringRateDeg remains SOURCE_NATIVE_RATE_CODE_ONLY /
RATE_SOURCE_CONTRACT_PARTIAL, without proof of signed physical steering rate.
One-step state used the previous observed delta. Rollout initial state used the observed
prior delta; recursive state used projected prior deltas, never future measured truth.
MOVE gate is distinct from movement state.

## V1/V2/V3/V4 frozen comparison

All metric entries use unchanged comparator anchors and population counts. The table shows
evaluated failures / evaluated candidate-fold jobs. V3's one NO_FEASIBLE_THRESHOLD job was
not evaluated; it is not a numerical regression. Closed-gate failure counts and unevaluated
counts are separately preserved in the comparison JSON. These are job counts, not pooled
error statistics, pooled model fits or newly selected configurations.

| Family | Evaluated jobs | Fold A complete pass | Fold B complete pass | Admissible candidates |
| --- | --- | --- | --- | --- |
| V1 | 32/32 | 0 | 0 | 0 |
| V2 | 32/32 | 0 | 14 | 0 |
| V3 | 31/32 | 0 | 0 | 0 |
| V4 | 32/32 | 0 | 0 | 0 |

| Frozen clause | V1 | V2 | V3 | V4 |
| --- | --- | --- | --- | --- |
| MOVE_MAE | 0/32 | 0/32 | 0/31 | 0/32 |
| MOVE_P95 | 0/32 | 0/32 | 0/31 | 0/32 |
| MOVE_RMSE | 0/32 | 0/32 | 0/31 | 0/32 |
| ONE_STEP_EXACT_HIT | 32/32 | 18/32 | 31/31 | 32/32 |
| ONE_STEP_MAE | 20/32 | 1/32 | 19/31 | 20/32 |
| ONE_STEP_P95 | 16/32 | 0/32 | 15/31 | 20/32 |
| ONE_STEP_RMSE | 4/32 | 1/32 | 3/31 | 4/32 |
| ONE_STEP_WITHIN_ONE_TICK | 8/32 | 10/32 | 7/31 | 8/32 |
| OVERALL_100_MAE | 23/32 | 0/32 | 22/31 | 32/32 |
| OVERALL_100_P95 | 25/32 | 1/32 | 24/31 | 32/32 |
| OVERALL_100_RMSE | 20/32 | 0/32 | 19/31 | 32/32 |
| OVERALL_200_MAE | 22/32 | 5/32 | 21/31 | 32/32 |
| OVERALL_200_P95 | 18/32 | 1/32 | 18/31 | 30/32 |
| OVERALL_200_RMSE | 21/32 | 5/32 | 20/31 | 32/32 |
| OVERALL_25_MAE | 23/32 | 6/32 | 22/31 | 32/32 |
| OVERALL_25_P95 | 21/32 | 0/32 | 20/31 | 32/32 |
| OVERALL_25_RMSE | 15/32 | 1/32 | 14/31 | 27/32 |
| OVERALL_50_MAE | 22/32 | 0/32 | 21/31 | 32/32 |
| OVERALL_50_P95 | 24/32 | 0/32 | 23/31 | 32/32 |
| OVERALL_50_RMSE | 16/32 | 0/32 | 15/31 | 32/32 |
| PATH_MOVED_100_MAE | 23/32 | 0/32 | 22/31 | 32/32 |
| PATH_MOVED_100_P95 | 25/32 | 1/32 | 24/31 | 32/32 |
| PATH_MOVED_100_RMSE | 19/32 | 0/32 | 18/31 | 32/32 |
| PATH_MOVED_200_MAE | 22/32 | 5/32 | 21/31 | 32/32 |
| PATH_MOVED_200_P95 | 17/32 | 0/32 | 17/31 | 30/32 |
| PATH_MOVED_200_RMSE | 21/32 | 5/32 | 20/31 | 32/32 |
| PATH_MOVED_25_MAE | 23/32 | 4/32 | 22/31 | 32/32 |
| PATH_MOVED_25_P95 | 21/32 | 2/32 | 20/31 | 32/32 |
| PATH_MOVED_25_RMSE | 14/32 | 0/32 | 13/31 | 25/32 |
| PATH_MOVED_50_MAE | 22/32 | 0/32 | 21/31 | 32/32 |
| PATH_MOVED_50_P95 | 23/32 | 1/32 | 22/31 | 32/32 |
| PATH_MOVED_50_RMSE | 16/32 | 0/32 | 15/31 | 32/32 |

The following strict apples-to-apples view uses only jobs evaluated by all four families
for each clause. Same-anchor per-job numerical metrics and gate results are also retained
in the companion comparison JSON. Historical result files remain byte-identical to
EXECUTION_HEAD.

| Frozen clause | Common jobs | V1 failures | V2 failures | V3 failures | V4 failures |
| --- | --- | --- | --- | --- | --- |
| MOVE_MAE | 31 | 0 | 0 | 0 | 0 |
| MOVE_P95 | 31 | 0 | 0 | 0 | 0 |
| MOVE_RMSE | 31 | 0 | 0 | 0 | 0 |
| ONE_STEP_EXACT_HIT | 31 | 31 | 17 | 31 | 31 |
| ONE_STEP_MAE | 31 | 19 | 1 | 19 | 19 |
| ONE_STEP_P95 | 31 | 15 | 0 | 15 | 19 |
| ONE_STEP_RMSE | 31 | 3 | 1 | 3 | 3 |
| ONE_STEP_WITHIN_ONE_TICK | 31 | 7 | 10 | 7 | 7 |
| OVERALL_100_MAE | 31 | 22 | 0 | 22 | 31 |
| OVERALL_100_P95 | 31 | 24 | 1 | 24 | 31 |
| OVERALL_100_RMSE | 31 | 19 | 0 | 19 | 31 |
| OVERALL_200_MAE | 31 | 21 | 5 | 21 | 31 |
| OVERALL_200_P95 | 31 | 18 | 1 | 18 | 30 |
| OVERALL_200_RMSE | 31 | 20 | 5 | 20 | 31 |
| OVERALL_25_MAE | 31 | 22 | 5 | 22 | 31 |
| OVERALL_25_P95 | 31 | 20 | 0 | 20 | 31 |
| OVERALL_25_RMSE | 31 | 14 | 0 | 14 | 26 |
| OVERALL_50_MAE | 31 | 21 | 0 | 21 | 31 |
| OVERALL_50_P95 | 31 | 23 | 0 | 23 | 31 |
| OVERALL_50_RMSE | 31 | 15 | 0 | 15 | 31 |
| PATH_MOVED_100_MAE | 31 | 22 | 0 | 22 | 31 |
| PATH_MOVED_100_P95 | 31 | 24 | 1 | 24 | 31 |
| PATH_MOVED_100_RMSE | 31 | 18 | 0 | 18 | 31 |
| PATH_MOVED_200_MAE | 31 | 21 | 5 | 21 | 31 |
| PATH_MOVED_200_P95 | 31 | 17 | 0 | 17 | 30 |
| PATH_MOVED_200_RMSE | 31 | 20 | 5 | 20 | 31 |
| PATH_MOVED_25_MAE | 31 | 22 | 3 | 22 | 31 |
| PATH_MOVED_25_P95 | 31 | 20 | 2 | 20 | 31 |
| PATH_MOVED_25_RMSE | 31 | 13 | 0 | 13 | 24 |
| PATH_MOVED_50_MAE | 31 | 21 | 0 | 21 | 31 |
| PATH_MOVED_50_P95 | 31 | 22 | 1 | 22 | 31 |
| PATH_MOVED_50_RMSE | 31 | 15 | 0 | 15 | 31 |

## Stage1 diagnostics

Ranges below summarize the existing frozen DEVELOPMENT diagnostics across 32 jobs.
They are not pooled row statistics. No AUC was invented.

| Diagnostic | V4 job range |
| --- | --- |
| missed_move_rate | 0.302850233 to 0.551616180 |
| false_move_rate | 0.097502684 to 0.452267180 |
| recall | 0.448383820 to 0.697149767 |
| specificity | 0.547732820 to 0.902497316 |
| precision | 0.202308949 to 0.440452369 |
| balanced_accuracy | 0.619094754 to 0.678796227 |

## Publication validation and independent reviews

Actual integrity: **PASS**. Publication validation: **PASS**.
The final result commit is made only after all required regression checks and both
independent actual-result reviews pass. Its own exact-commit CI is verified separately.

| Check | Exit code | Passed tests/items |
| --- | --- | --- |
| actual_focused | 0 | 12 |
| combined | 0 | 2159 |
| compileall | 0 | None |
| diff-check | 0 | None |
| full | 0 | 5018 |
| historical_immutability | 0 | None |
| json | 0 | 744 |
| lateral | 0 | 16 |
| prior | 0 | 315 |
| publication | 0 | None |
| publication_serialization | 0 | None |
| ruff | 0 | None |
| scons | 0 | None |
| source_immutability | 0 | None |
| v4_executor | 0 | 64 |

| Independent review | Status | Private report SHA256 |
| --- | --- | --- |
| authority | APPROVED | 29a86adb08713b7b0d0f8e9b94cb95d0ecd260c210cb1437f1f3f4d67b0deb2b |
| numerical | APPROVED | 0d92b3b134620d44d75f8530dad9a5a6ecd5f8ced71f41493642b2788bd77fa3 |

## Authority and next step

Actual threshold values remained private. Coefficients remained private.
Hugging Face: **NOT_REQUIRED / NOT_USED**; no setup, login, repository, upload or download.

Recommended single next step: a separately scoped, report-only causal-rollout and Stage1
error-attribution review. This increment ends with the result; no further fitting or tuning occurs.

HOLDOUT: **CLOSED**, opening_count = **0**, holdout_discovery = **0**.
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED; NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT;
FINAL_POOLED_REFIT_NOT_AUTHORIZED; COMPOSITION_NOT_AUTHORIZED.
Vehicle: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED;
vehicle_authority = **NONE**. No controller integration, deployment or activation.
