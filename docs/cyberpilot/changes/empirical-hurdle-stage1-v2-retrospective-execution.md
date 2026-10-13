# Hurdle Stage1 V2 retrospective execution

V2에서는 새 모델을 학습하지 않았다. V1에서 사용한 Stage1/Stage2 모델과
normalizer를 한 바이트도 바꾸지 않고 재사용했다. 바뀌는 것은 MOVE/STATIC을
나누는 threshold의 선택 목표다. V2는 TRAIN에서 MOVE 오차를 보호하고 전체
RMSE를 개선하는 threshold 중 projected tick exact-hit를 우선한다.

32개 jobs 모두 실행됐다. V1보다 exact-hit는 모두 개선됐지만, 두 folds의
모든 기준을 함께 통과한 구조는 없었다. V2도 NO_ADMISSIBLE이며, V1의
NO_ADMISSIBLE 판정 역시 영구 보존한다.

## Identity and purpose

- Area: Cyber Validation / AutoTune, retrospective route-level development.
- Branch: feature/cyber-autotune; baseline f203450ceea5a1d26bea0617fc7d8e097f2e63b3.
- Status: 32 jobs executed in each independent run; V2 NO_ADMISSIBLE.
- Scope: threshold-policy-only execution of exactly 16 tied structures and two
  route folds. No vehicle applicability or deployment authority.
- Immutable successful V1 manifest:
  c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6.
- Execution policy:
  b0f838bf1c981cc5f137416f1f6397398dd5c3c5867cfed3f649f1ccc815346e.
- Design policy:
  463ac0c2f34b59b67c1a1d7365c5662d717a49de328cabfd9101f185bff2bf19.

## Original references and traced execution

CyberPilot repository: https://github.com/rownlvh8875-coder/CyberPilot,
feature/cyber-autotune at the baseline above. Reuse the immutable
empirical_hurdle_fit_cv_math/data/gates modules and their S2-RI feature/metric
primitives under existing repository licenses. No upstream/submodule change or
new numerical dependency is needed.

Authorization and metadata admission precede numeric decoding. Immutable model
and normalizer receipts lead to TRAIN feature construction and normalized
feature-byte verification. Stage1 probabilities are replayed and compared to
saved probabilities. Stage2 inference covers every TRAIN anchor, including
STATIC rows, using its original MOVE-only normalizer. The frozen V2 objective
selects a private fold-local threshold; its receipt is finalized before opening
DEVELOPMENT numerically. All valid evaluations continue despite gate failures.

## Changes and numerical semantics

Four additive modules implement the exact threshold sweep, private I/O and
authorization, execution/resume, and aggregate publication. Two focused test
modules exercise synthetic inputs only. Existing policies and evidence remain
unchanged.

Threshold candidates remain {0,1} union unique finite TRAIN probabilities.
MOVE uses strict p > threshold. Feasibility requires true-MOVE RMSE/MAE/p95
non-worse than HOLD_LAST and ALL RMSE strictly better, without epsilon.
Lexicographic objectives are projected exact-hit count, negative STATIC
projected false-move count, within-one-tick count, then higher threshold.
Balanced accuracy has reporting authority only. An empty feasible set fails
the fold without fallback.

The sweep preserves original row order for binary64 reductions with a
point-update pairwise tree. It does not subtract/add floating totals in
probability order. Leaves call NumPy; parent operations follow the pinned
NumPy pairwise ordering. The exact order-statistic structure stores original
binary64 error values with integer multiplicities; linear p95 interpolation
matches np.percentile(method="linear"). The source reference for reduction
semantics is [NumPy v2.5.3 loops_utils.h.src](https://github.com/numpy/numpy/blob/v2.5.3/numpy/_core/src/umath/loops_utils.h.src).
No NumPy source was copied into the implementation.

Synthetic tests compare every threshold against the canonical evaluator.
Actual execution checks deterministic boundary/interior thresholds and the
selected threshold exactly. The latest execution instruction requires any
equivalence mismatch to stop with V2_THRESHOLD_EVALUATOR_EQUIVALENCE_FAILURE;
no approximation or silent policy fallback is permitted.

## Lineage, storage and execution boundaries

The preflight authorization permits only metadata inspection. The complete
execution authorization binds HEAD, code hashes, all policy receipts, exact
source manifests, model receipts, root identities, environment and capacity.
Model, normalizer and source array bytes are checked against immutable receipts
before their authorized decoding. Standardized TRAIN feature hashes must match
the saved Stage1 ALL-TRAIN and Stage2 MOVE-TRAIN hashes. Saved TRAIN probability
bytes must match replay.

Initial integrity binding uses historical manifest-listed hashes. It does not
pre-open DEVELOPMENT payloads before threshold finalization. After all jobs,
every manifest-listed V1 member and authorized source/derived member is hashed
against those bindings. This is not a new pre-run full-store byte scan.

All results reside on D. Signed16 range checks permit lossless int16 persistence
of projected ticks and paths; calculations retain the frozen float64/int64
semantics. C-order NPY uses gzip level 1, mtime zero and no embedded filename.
Each member binds compressed, decoded NPY and array-content hashes. V1 models,
truth, HOLD_LAST paths and exogenous data are references, never duplicated.

Capacity admission budgets two incompressible payloads, gzip overhead, an atomic
member peak, metadata and a 2 GiB reserve. RUN2 admission budgets the remaining
run only. Each run recalculates from immutable V1 inputs without using RUN1
prediction or threshold caches. RUN2 payloads are retained unless separately
verified cleanup completes; storage economy never drops required evidence.

The immutable policy artifact named empirical-hurdle-stage1-v2-execution-readiness.json
is preserved. Actual readiness is published additively as
empirical-hurdle-stage1-v2-retrospective-execution-readiness.json.

## Regression risk and acceptance

The final DEVELOPMENT gate retains all 32 clauses per fold: ALL one-step,
true-MOVE integrated, overall rollout and PATH_MOVED rollout at 25/50/100/200
steps. Both folds must pass. Candidate ranking retains the original seven keys.
V1/V2 comparisons are report-only and cannot influence numerical threshold
choice, admission or selection.

Risks include reduction-order drift, model/anchor mismatch, source leakage,
privacy exposure and recursive long-horizon error. STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS.
No thresholds, coefficients, normalizer values, per-row data or private paths
are public. Historical V1 results remain immutable. Rollback removes only this
additive increment; it never resets historical evidence.


## Actual retrospective results

Both runs accounted for 32/32 EXECUTED_COMPLETE jobs, with no precondition,
numerical, support, diagnostic or no-feasible-threshold failure. Every job
replayed saved Stage1 TRAIN probabilities byte-exactly and evaluated Stage2
on ALL TRAIN anchors. TRAIN and DEVELOPMENT populations range from 183,711
to 336,941 anchors per job. Threshold candidate counts range from 183,713 to
336,889; feasible counts range from 73,037 to 300,539. Actual threshold numbers
remain private.

TRAIN projected exact-hit and DEVELOPMENT projected exact-hit improved versus
V1 in 32/32 jobs. This comparison is against V1, not proof of acceptance:
18/32 V2 jobs still failed the HOLD_LAST exact-hit clause. True-MOVE
RMSE/MAE/p95 protection passed 32/32. Fold A passed the complete gate in 0/16
jobs and Fold B in 14/16; no structure passed both folds. Admissible count is
0, selected_candidate is null, and the outcome is
HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE / MODEL_SELECTION_FAILED_CLOSED.

The gate became much more conservative. DEVELOPMENT false-move rate ranges
are 0.0000380194–0.00389388 in Fold A and 0.00000346368–0.0000631608 in Fold B.
Missed-move rates are 0.968248–0.999422 and 0.994070–0.999899 respectively.
Balanced accuracy ranges are 0.500256–0.513929 and 0.500048–0.502933.
These diagnostics explain the tradeoff; they have no admission authority.

The 1,024 paired clause results comprise 519 recovered, 10 newly failed,
438 unchanged pass and 57 unchanged fail. The following table counts failed
jobs, retaining each horizon and population separately.

| Clause | V1 failures / 32 | V2 failures / 32 |
| --- | ---: | ---: |
| ONE_STEP_RMSE | 4 | 1 |
| ONE_STEP_MAE | 20 | 1 |
| ONE_STEP_P95 | 16 | 0 |
| ONE_STEP_EXACT_HIT | 32 | 18 |
| ONE_STEP_WITHIN_ONE_TICK | 8 | 10 |
| MOVE_RMSE | 0 | 0 |
| MOVE_MAE | 0 | 0 |
| MOVE_P95 | 0 | 0 |
| OVERALL_25_RMSE | 15 | 1 |
| OVERALL_25_MAE | 23 | 6 |
| OVERALL_25_P95 | 21 | 0 |
| OVERALL_50_RMSE | 16 | 0 |
| OVERALL_50_MAE | 22 | 0 |
| OVERALL_50_P95 | 24 | 0 |
| OVERALL_100_RMSE | 20 | 0 |
| OVERALL_100_MAE | 23 | 0 |
| OVERALL_100_P95 | 25 | 1 |
| OVERALL_200_RMSE | 21 | 5 |
| OVERALL_200_MAE | 22 | 5 |
| OVERALL_200_P95 | 18 | 1 |
| PATH_MOVED_25_RMSE | 14 | 0 |
| PATH_MOVED_25_MAE | 23 | 4 |
| PATH_MOVED_25_P95 | 21 | 2 |
| PATH_MOVED_50_RMSE | 16 | 0 |
| PATH_MOVED_50_MAE | 22 | 0 |
| PATH_MOVED_50_P95 | 23 | 1 |
| PATH_MOVED_100_RMSE | 19 | 0 |
| PATH_MOVED_100_MAE | 23 | 0 |
| PATH_MOVED_100_P95 | 25 | 1 |
| PATH_MOVED_200_RMSE | 21 | 5 |
| PATH_MOVED_200_MAE | 22 | 5 |
| PATH_MOVED_200_P95 | 17 | 0 |

The comparison artifact preserves candidate/fold-level TRAIN objective metrics,
confusion, threshold receipt identities, DEVELOPMENT metrics and all four
rollouts side by side. V1 performance never enters V2 threshold selection.
This is THRESHOLD_POLICY_ISOLATED_RETROSPECTIVE_COMPARISON, not independent
validation, causal proof or vehicle validation. Long-horizon failures remain,
including five 200-step RMSE failures in both overall and PATH_MOVED populations.

The authorization receipt is
9a70195aa396a633269c4ce46a5ae2c7870e26b3ee3501a9e181f6bee9a32869.
Both run manifests are
7d28c7d07c72a1080e6769165af8539f3568e14688b82f782d0d29aed8d84b9b.
The repeatability receipt is
a6c3e3852d585d089b14ce36b853429afefeb1646aeb8d8008042c092ebe6aae.
Both saved stores passed verify-only resume with all computation trapped.
Stage1/Stage2/normalizer refit calls, raw/qlog/HOLDOUT openings and source writes
are zero. The full two-run compressed store is approximately 263 MB; both payloads are
retained on D, with no need to delete RUN2 scratch. Source bytes remain unchanged.

## Validation method and actual results

| Check | Method | Result |
| --- | --- | --- |
| Focused synthetic executor | pytest test_empirical_hurdle_v2_threshold.py and test_empirical_hurdle_v2_execution.py | 40 tests and 9 subtests passed before actual execution |
| Actual 32 jobs × 2 | Separate D stores, exact receipts and all compressed/content hashes | PASS; 898 corresponding members byte-exact |
| Verify-only resume | All model/source loaders and computation trapped | PASS, both saved runs |
| Full AutoTune/controls | Repository test runner, one worker | 4,591 passed |
| Combined empirical | pytest empirical suites | 1,732 tests and 625 subtests passed |
| Lateral replay | Existing unittest suites | 16 passed |
| Ruff, compileall, JSON, publication, diff, SCons | Existing toolchain | PASS |
| Independent review | Source, synthetic tests, aggregate results, documentation and publication boundary | PASS; no outstanding findings |
| Shadow / vehicle | Not authorized in this increment | NOT_RUN |

## Handoff

V2 execution completed with no admissible candidate; no follow-on execution is authorized.
Final pooled refit remains NOT_AUTHORIZED. HOLDOUT remains CLOSED, opening and
discovery counts zero; no model is admitted for future HOLDOUT. Vehicle authority
is NONE with NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Further redesign, HOLDOUT access, controller integration and vehicle use require
separate authorization.
