# Hurdle Stage1 V2 execution policy

V2에서 바뀐 것은 모델이 아니라 MOVE/STATIC을 나누는 threshold 선택 기준뿐이다.
따라서 그 차이를 분리해서 보기 위해 기존 V1 Stage1/Stage2 모델과 normalizer를
한 바이트도 바꾸지 않고 재사용하기로 했다. 향후 새로 계산할 것은 같은 모델의
TRAIN 예측, V2 threshold, 그리고 이를 적용한 DEVELOPMENT/rollout 결과다.
이번 단계는 공개 계약과 synthetic tests만 작성하며 실제 예측이나 threshold는
계산하지 않는다.

## Identity and purpose

Cyber Validation / AutoTune; HURDLE_STAGE1_DECISION_POLICY_V2_EXECUTION_POLICY.
This additive policy freezes execution lineage, comparison, storage, repeatability
and resume before separate actual-execution authorization. Family HURDLE_RI_V1;
change_scope THRESHOLD_OBJECTIVE_ONLY. Branch feature/cyber-autotune;
baseline 32018c9cc4381c779c7001c51e0949b120185525.
Status: implemented and independently reviewed; all local validation passed.
No controller caller or vehicle applicability is introduced.

## Original references

Source: https://github.com/rownlvh8875-coder/CyberPilot, the verified branch and
baseline above. The existing public-only decision-policy builder and its ten
artifacts are immutable inputs. The new builder is
openpilot/tools/cyber_autotune/empirical_hurdle_v2_execution_policy.py; tests are
the corresponding test_empirical_hurdle_v2_execution_policy.py. Twelve new JSONs
use the empirical-hurdle-stage1-v2 prefix. No external code is imported or
adapted; repository MIT licensing/attribution remains unchanged. No new
dependencies or submodule changes.

The public chain binds V1 successful baseline f5ed849bd27287084efc81ba3dd0275ebfc5ca0a,
private manifest identifier c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6,
authorization e4eeaca2f891cc9fdb1370b7ae735d963287af6c09cca85dc689c8e9c560c6ea,
and exact-repeatability receipt 3b9e8e1f562972268a7a0543f72d3f98fe237a9f3e1c5e045b69e19f9c69949b.
Public wrapper receipts are distinguished from the referenced private receipts.
No private receipt is opened.

Attribution baseline 13e1ac7c8b892d3bd61b5e2eab9deba8f4dc08d6 and manifest
07345517d3bca95e90962e0566a58e2b756a8aa6f5c658b8b312f02d4961f77d,
V2 design policy 463ac0c2f34b59b67c1a1d7365c5662d717a49de328cabfd9101f185bff2bf19,
readiness 6963e8a3d0b3ae018a6612e7d07e18143db0f5147d7ccb5b75e90dbc77dc00e8
and future requirements 52586eae8858a3cf31f54c74917dbb7df2d7b792a14a4e39567a5f2b057c74f9
are pinned. The policy resolves the previously deferred strategy additively;
it does not rewrite that historical UNRESOLVED artifact.

Call path: public allowlisted JSONs → byte/receipt verification → declarative
builder → canonical validation → immutable public publication. Numerical
interpretation exists only in synthetic tests. There is no executor, private
source root argument, discovery, fitting or prediction API in this module.

## Changes and expected effect

REUSE_BYTE_IDENTICAL_V1_FITTED_MODELS isolates the threshold-policy effect.
CLEAN_32_JOB_REFIT_WITH_FROZEN_V1_ALGORITHMS is rejected. Stage1 logistic,
Stage2 MOVE-only OLS, separate fitted normalizers, features, 16 tied d/L
structures, two route folds, metric/projection/rollout semantics, 32 clauses
per fold and candidate ranking remain byte/receipt bound to V1.

Each future candidate/fold verifies six model/coefficient/normalizer receipt
identities and bytes against the successful source manifest. Any drift fails
V2_V1_MODEL_IDENTITY_CONFLICT. Stage1, Stage2 and normalizer fitting are forbidden
even in future V2 execution. Historical V1 thresholds never enter the V2 selector.

Stage1 TRAIN p_move is prediction-only replay from the immutable V1 model,
using exact ordered V1 feature/target arrays and anchors. A receipt-bound saved
V1 TRAIN p_move, if present, must match the replay byte for byte; otherwise
V2_STAGE1_TRAIN_PREDICTION_IDENTITY_FAILURE. The replay is canonical.
Python 3.12.13, NumPy 2.5.3, single-thread BLAS/OMP and the V1 BLAS fingerprint
are bound. Operation order/batching cannot be reassociated silently.

Stage2 predictions cover ALL candidate-specific TRAIN anchors, including true
STATIC rows. Its original MOVE-only TRAIN normalizer and coefficients stay
fixed. A true STATIC row can take the predicted MOVE branch; computing Stage2
only for true MOVE would corrupt the task objective. True labels serve masks,
constraints and diagnostics, never inference branching.

Threshold candidates, strict p_move > threshold, four feasibility conditions
and four ordering keys are unchanged from V2 design. Feasibility protects
true-MOVE RMSE/MAE/p95 as non-worse and requires strict ALL RMSE improvement.
Then maximize projected exact-hit count, minimize STATIC projected false-move
count, maximize within-one-tick count and maximize threshold. No feasible
threshold fails the fold with no V1/BA/0.5 fallback.

The canonical memory-bounded reference evaluates one threshold at a time with
V1 ordered float64 reductions and np.percentile(abs(error),95,method="linear").
It does not retain an N-by-threshold matrix. Sorted sweeps are optional future
optimizations only after synthetic byte-exact comparison of every metric,
feasibility result, objective count and selection. Cumulative SAE/SSE arithmetic
is not assumed equivalent to the canonical reduction. Approximate quantiles,
binning, epsilon, rounding and probability quantization are forbidden.
No optimized evaluator is implemented or claimed here.

DEVELOPMENT opens only after immutable TRAIN threshold finalization. It uses
the same V1 model bytes and exact V1 ordered anchors with the V2 gate.
Recursive rollout still uses projected integer ticks and projected delta
history, immutable Stage1 at every step and Stage2 only on predicted MOVE;
STATIC holds exactly. Future measured angle/delta/MOVE labels are scoring-only.
Recorded command/vEgo remain exogenous. No adaptive threshold, hysteresis or
online normalization; horizons remain 25/50/100/200 at 100 Hz.

V1/V2 direct comparison is report-only and requires identical candidate/fold/
anchor identities. TRAIN, DEVELOPMENT, overall/PATH_MOVED rollout metrics and
recovered/new/unchanged clause sets are reported separately. V1 TRAIN task
metrics may use receipt-bound aggregates or a comparison-only fixed historical
V1 threshold on the same replay, strictly after V2 finalization. Missing
comparison lineage fails closed. No alternative threshold is searched and V1
metrics have no V2 selection authority. Threshold values remain private.
Descriptive improvements do not imply design success or independent causal
validation.

Future storage is compact and D-only, outside and nonoverlapping with inputs.
Model, truth, HOLD_LAST, anchor and exogenous bytes use immutable references
instead of redundant copies. Only V2-specific outputs persist: private threshold,
selected TRAIN gate/projection, replay identities, DEV predictions/errors and
V2 rollout paths/gates/errors. C-order NPY uses lossless gzip level 1, mtime=0,
no filename; compressed, decoded and content hashes bind dtype/shape/order.
Absolute-volume proof, free-space guard, symlink/traversal rejection, atomic
no-overwrite writes and receipt/job-manifest/run-manifest-last apply.

RUN-1 is authoritative and complete. RUN-2 independently repeats all computation;
large D-side scratch may be removed only after all corresponding byte/hash/
manifest comparisons pass and permanent run2/comparison/equality/threshold/
result receipts are durable. Failure keeps scratch. Canonical logical manifests
exclude run root/number/timing so their bytes can match; run-role/cleanup metadata
lives in separate audit receipts. The current increment deletes no private data.

Verify-only resume verifies saved V2 payloads and receipt/manifest/readiness
chains, with model/source/predictor/threshold/DEV/rollout/scorer/selector trapped.
External references are checked against saved sealed lineage without dereferencing
V1. It returns the same manifest/readiness, not a claim about current unopened
source bytes. Incomplete/corrupt saved evidence fails without recomputation.

## Regression risk and acceptance

Risks: hidden refit, wrong Stage2 population, row-order drift, numerical
reassociation, DEVELOPMENT leakage, privacy disclosure, unsafe scratch cleanup
or resume recomputation. Synthetic fixtures and resealed-mutation rejection
cover these contracts. The complete bundle is canonical-checked against the
builder, and all public inputs have exact file and receipt pins.

No historical evidence or controller interface changes. Rollback is removal of
this additive policy before any separate execution authorization; historical
V1 remains authoritative. Independent review is required. Missing actual
private availability is intentionally not tested here; no path/file probing
occurs. Separate future authorization must confirm source path, D output root,
free space, manifests, model receipts and input availability.

## Validation method and actual results

Environment: Ubuntu 24.04, Python 3.12.13, NumPy 2.5.3;
OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1. Verification outputs and temporary
test files use the D-backed development volume.

| Check | Method | Result |
| --- | --- | --- |
| Focused policy/synthetic tests | pytest test_empirical_hurdle_v2_execution_policy.py | 31 passed, 34 subtests; independent rerun passed; resume-trap refinement targeted test passed |
| Red-before-implementation | three initial tests before builder existed | 3 failed for missing module as expected |
| Combined empirical | pytest test_empirical_*.py | 1,692 passed, 616 subtests in 74.10 s; before resume-trap refinement, then covered by final full run |
| Full AutoTune + controls | python tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j 1 | 4,551 passed in 1,585.45 s after review fix, with stable source |
| Lateral replay | test_cyber_lateral_card_replay and test_cyber_lateral_native_experiment via unittest | 16 passed |
| Ruff / compileall / SCons | ruff check on AutoTune, cyberpilot tools, Cyber controls/replay; python -m compileall -q openpilot/tools/cyber_autotune tools/cyberpilot; scons -u -j2 | All PASS |
| JSON / publication / privacy / authority | strict JSON, builder.validate; check_publication.py against baseline and origin/main; git diff --check | 568 JSONs valid; 12 new contracts / 35 input pins verified; publication finding lists empty; 15 additions, no historical modifications |
| Independent review | separate read-only review of all contracts and tests | No substantive outstanding findings; disconnected resume mocks replaced by active execution-function traps with mutation controls, remediation re-reviewed |
| Exact-HEAD CI | baseline run 38374439401; final commit checked by head_sha after push | Baseline SUCCESS; final run evidence is reported in the task handoff after push |

Browser is NOT_APPLICABLE. Actual private access, fitting, prediction, threshold
selection, rollout, CV and candidate selection are NOT_RUN. Simulation, shadow,
HOLDOUT and vehicle execution are NOT_AUTHORIZED. Synthetic tests exercise
contract semantics only; they are not empirical V2 evidence.

## Handoff

Readiness: HURDLE_STAGE1_DECISION_POLICY_V2_EXECUTION_POLICY_FROZEN and all ten
subcontract freeze states. Private source access/path discovery/manifest opening
remain zero. The next increment is
HURDLE_STAGE1_DECISION_POLICY_V2_RETROSPECTIVE_EXECUTION,
REQUIRES_SEPARATE_AUTHORIZATION; it must not auto-start.

Historical HURDLE_NO_ADMISSIBLE_CANDIDATE, MODEL_SELECTION_FAILED_CLOSED,
FROZEN_HURDLE_RI_V1_FAILED_RETROSPECTIVE_GATE, S2-RI evidence and all global
rate/source/calibration/reference/TA/SG/composition blockers remain.
STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS: small-support gate-perfect 50/100-step
regressions do not validate Stage2 or authorize its redesign.
No pooled refit, new search, controller integration or vehicle application.
HOLDOUT CLOSED, opening_count=0, discovery=0;
NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT. Vehicle authority NONE:
NOT_READY, REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.

Policy receipt: b0f838bf1c981cc5f137416f1f6397398dd5c3c5867cfed3f649f1ccc815346e.
Readiness receipt: 81e6a953589ec768e8194f5f503292b11796ff074165e7c3fc151d957a5ebc5f.
Validation receipt: 14e3f9a5e7264f8746138058943d71db7defe36e96d2cc20c6d29d1dc746f2ec.
