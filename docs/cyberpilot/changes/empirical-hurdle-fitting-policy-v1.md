# Hurdle fitting policy V1

새 Hurdle 모델은 먼저 다음 source-grid 관측에서 핸들 각도 tick이 변할지를
분류하고, MOVE로 판단할 때만 변화량을 계산한다. 이번 단계에서는 실제로
학습하지 않고, 학습 방법과 threshold 선택 방법, 통과해야 할 평가 기준을
사전에 고정했다.

기존 관측의 약 85.23–85.90%가 STATIC이었다. STATIC의 작은 오차를 줄이는
것만으로 MOVE 성능이나 장기 rollout 문제까지 해결됐다고 볼 수 없다.
따라서 전체 평가 외에 실제 MOVE 관측과 PATH_MOVED trajectory를 보호하는
조건을 함께 둔다. 기존 S2-RI의 NO_ADMISSIBLE 판정은 그대로다.

## Identity and purpose

- Cyber Validation / HURDLE_FITTING_POLICY_V1, family HURDLE_RI_V1.
- Baseline: cce79c2762e4e83f39fa2239f7129253fb5b713b, branch feature/cyber-autotune.
- Status: policy implemented; actual fitting, threshold selection, prediction,
  rollout, CV and candidate selection NOT_RUN.
- Scope: public-only declarative policy, validator and synthetic tests.
  No vehicle applicability or control-interface change.
- Effect: remaining fitting freedoms are predeclared; no empirical improvement
  is claimed or calculated in this increment.

## Original references and lineage

[CyberPilot](https://github.com/rownlvh8875-coder/CyberPilot) at the exact baseline
above supplies all references. The 14 Hurdle design artifacts are pinned by
file SHA256 and canonical receipt SHA256, together with the historical S2-RI
route-CV, metric and direct-tick grid contracts (17 public inputs).
The design readiness receipt is
8d08f9c06583983e237cbdf92dc6028865a3d87a9a289aaba00ea895ede9fd2a.
Historical design still says threshold UNSET; this additive fitting policy
resolves that deferred rule without rewriting the design receipt.

The upstream V2 trigger is ZERO_STATIC_TRANSITION_TRADEOFF_STRICT, 32/32 jobs.
PATH_MOVED SSE improvement/regression counts at 25/50/100/200 are respectively
25/7, 18/14, 17/15 and 7/25. They motivate protection gates; no private data
or historical model is reopened. Original licensing and attribution remain.
No scipy/sklearn, dependency changes, submodule/gitlink changes or new LFS assets.

Call path: allowlisted public JSON → exact byte/receipt/state verification →
declarative contracts → complete-bundle validation → immutable JSON publication.
Equations are strings. The policy CLI cannot fit, score, select or open private
numeric arrays. Numerical formula interpretation is confined to synthetic tests.

## Changes and expected effect

New empirical_hurdle_fitting_contracts.py holds the declarations;
empirical_hurdle_fitting_policy.py pins inputs, derives exact candidate identities,
validates complete bundles and publishes atomically with the validation receipt
last. Publication preflights every destination, refuses overwrite, symlinks and
traversal, and permits only byte-identical resume. New focused tests check
synthetic semantics, mutations, publication and the execution firewall.
All previous tracked evidence is unchanged.

### Structures, features and route folds

Exactly 16 structures remain: HRI_D00_L01/L05/L15/L45,
HRI_D05_L01/L05/L15/L45, HRI_D10_L01/L05/L15/L45 and
HRI_D20_L01/L05/L15/L45. Both stages share d and L; no 256-pair expansion.
Each stage has P=2L+3 nominal coefficients (5,13,33,93); totals are 10,26,66,186.
The threshold is a separate decision-policy parameter and is excluded from 2P.

Feature order is intercept, u[k-d-L+1..k-d] oldest to newest,
delta[k-L..k-1] oldest to newest, current angle tick and current vEgo.
delta[k]=tick[k+1]-tick[k]. Feature order/target/grid/causal continuity
remain bound to immutable design receipts. d denotes command history offset,
not physical EPS delay. SteeringRate and controller request are absent.
Primary scope remains SCOPE_ALL_ACTIVE_NO_OVERRIDE; NON_RAIL is diagnostic only.

FOLD_A TRAIN is
7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677;
DEVELOPMENT is
962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c.
FOLD_B reverses those identities. No random, segment or pooled development split.
Future execution is lexical candidate ID, then FOLD_A, then FOLD_B: 32 jobs
with explicit success/failure accounting, no performance-driven early stop.

### Stage 1 logistic Newton

Algorithm: DETERMINISTIC_FLOAT64_UNREGULARIZED_LOGISTIC_NEWTON.
Target is exactly delta_tick != 0; all candidate-specific TRAIN anchors are used.
Both STATIC and MOVE TRAIN counts must be >=201. Effective standardized X must
have full numerical rank before the solver can run. Initial beta is all zeros.
No warm start, weights, balancing, regularization, ridge damping or coefficient
clipping. Python 3.12.13 / NumPy 2.5.3 are required, with
OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1; no RNG. Future execution must record
the exact BLAS build and demonstrate byte-exact repeatability.

z=X@beta; BCE=mean(logaddexp(0,z)-y*z). Stable sigmoid evaluates only the appropriate
branch: 1/(1+exp(-z)) for z>=0; exp(z)/(1+exp(z)) otherwise.
g=X.T@(p-y)/n; w=p*(1-p); H=X.T@(w[:,None]*X)/n.
Newton direction is numpy.linalg.solve(H,g), and beta_new=beta-alpha*direction.
No pinv/lstsq fallback exists. Nonfinite values or dot(g,direction)<=0 fail
the entire fold as MOVE_GATE_NUMERICAL_FAILURE.

Convergence requires max(abs(g))<=1e-8. There are at most 100 accepted Newton
updates; the gradient at the result of update 100 is checked before declaring
MOVE_GATE_NONCONVERGENCE. Line search starts at alpha=1 and permits up to 20
halvings: exponents 0..20, 21 trials including the initial trial. The first
finite trial satisfying loss_new<=loss_old-1e-4*alpha*dot(g,direction) is accepted.
A nonfinite trial is numerical failure, not silently skipped. No accepted trial
means MOVE_GATE_LINE_SEARCH_FAILURE. These iteration boundary conventions are
frozen before performance is observed.

### Separate TRAIN-only normalization and Stage 2

Both stages retain an exact unscaled intercept. Population mean and std(ddof=0)
are computed only on each stage's own TRAIN population, in canonical anchor order.
Stage 1 uses STATIC+MOVE; Stage 2 uses true MOVE only. Stage 1 normalizer is never
reused by Stage 2. Exact constant TRAIN columns are excluded from effective solve
coordinates and represented by nominal coefficients fixed to zero. Constant
detection precedes division; nonconstant zero std is numerical failure.
DEVELOPMENT constant drift is report-only, without refitting or changing masks.

Stage 2 is DETERMINISTIC_FLOAT64_MOVE_ONLY_OLS, target signed actual delta_tick.
MOVE TRAIN support must be >=max(P,201). Rank must equal the effective column
count before numpy.linalg.lstsq(X,y,rcond=None). Returned rank must also match.
NumPy 2.5.3 rcond=None uses float64 machine precision times max(M,N) as the
relative singular-value cutoff; matrix_rank uses its documented default
S_max*max(M,N)*eps tolerance. No tolerance retry, regularization, weighting,
or bad-row dropping. Nonfinite normalizer/coefficient/singular value/prediction
fails the whole candidate-fold. Normalizers, coefficients and actual thresholds
belong to separate private model receipts in a separately authorized future run.

### TRAIN-only threshold

Each candidate/fold's threshold candidates are {0,1} union all unique finite
TRAIN predicted probabilities, sorted ascending. There is no default 0.5 and
no fixed grid. MOVE iff p_move>threshold; equality means STATIC. Threshold 1
therefore represents all-STATIC decisions, without adding a structural candidate.

Let P=true MOVE count and N=true STATIC count. Maximize
BA_NUM=TP*N+TN*P using unbounded Python integers (convert NumPy count scalars before
multiplication). The common denominator 2*P*N is not used for ordering.
Tie-break: maximize TN, then maximize numerical threshold. Displayed balanced
accuracy is diagnostic only. No DEVELOPMENT, integrated metric, rollout or
HOLDOUT information may choose the threshold. Actual threshold values stay
private; only receipt SHA, candidate count, TRAIN confusion aggregates and the
rule may be published later.

Required DEVELOPMENT Stage 1 diagnostics include precision TP/(TP+FP).
If no MOVE is predicted, precision is undefined even when both true classes
exist. The explicit requested fail-closed rule applies:
STAGE1_DIAGNOSTIC_UNDEFINED invalidates the fold. The all-STATIC threshold remains
a legal TRAIN threshold candidate; no synthetic precision is substituted.

### Hard composition and recursive rollout

Predicted STATIC gives exact zero delta and holds the current projected tick;
Stage 2 is not called. Predicted MOVE invokes Stage 2 and directly rounds
binary64(current_tick+delta) half-to-even to an integer tick. No minimum +/-1
movement, clipping, epsilon, debounce, hysteresis or soft probability mixture.
Projection failure or signed16 range violation invalidates the whole fold.

Recursive steering state consists only of projected integer ticks and their
differences. Stage 1 runs each step; Stage 2 only on predicted MOVE. Actual future
angle/delta/true MOVE labels never select branches or become features.
Recorded normalized post-CarController command and vEgo are exogenous:
LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT. Horizons are 25/50/100/200
transitions from k to k+H, with H+1 ticks in each path, at 100 Hz.
Entire history and horizon must remain in one route/segment/S2-RI run/eligible
streak with exact timing and required inputs. No short padding or interpolation.

### Metrics, comparator and admission

HOLD_LAST_ANGLE uses the exact same ordered anchors as the candidate for every
population. One-step holds observed current tick; rollout holds initial tick.
Canonical continuous error is final integrated predicted delta minus actual
delta in float64. Continuous next-angle error is an alias of that buffer;
adding current angle then subtracting next angle is not a second calculation.
RMSE=sqrt(mean(error²)), MAE=mean(abs(error)),
p95=np.percentile(abs(error),95,method="linear"). Projected exact-hit and
within-one-tick rates use integer comparisons. One tick is 0.1 degree.
Reductions preserve route, source-segment content SHA and ascending anchor index
on contiguous float64 arrays. Rollout metrics use endpoint errors only.

Every candidate/fold requires >=201 DEVELOPMENT ALL, STATIC and MOVE anchors.
Each rollout horizon requires >=201 overall and >=201 PATH_MOVED anchors.
PATH_MOVED means any observed tick differs from the initial tick; that
ground-truth mask is for scoring only. All values must be finite, error metrics
nonnegative and grid rates in [0,1].

Each fold must pass all 32 comparisons:

| Population | Required comparison to same-anchor HOLD_LAST |
| --- | --- |
| ALL integrated one-step | RMSE strictly lower; MAE and p95 no higher; exact-hit and within-one-tick no lower |
| True-MOVE one-step, **integrated predicted-gate output** | RMSE, MAE and p95 no higher |
| Overall rollout, each of 25/50/100/200 | RMSE, MAE and p95 no higher |
| PATH_MOVED rollout, each of 25/50/100/200 | RMSE, MAE and p95 no higher |

Both folds must pass every comparison and support/numerical precondition.
No epsilon, percentage allowance or statistical margin. PATH_FLAT and STATIC
retain visible diagnostics but add no separate hard admission threshold.
Gate false-move and projected false-movement are explicitly distinguished.
Stage 2 true-MOVE oracle metrics are diagnostic only and cannot admit or rank
a candidate. Stage 1 balanced accuracy is likewise not an admission shortcut.
This is a separately predeclared Hurdle gate, not automatic historical S2-RI gate
inheritance; no historical gate or verdict changes.

### Deterministic selection and failure

Only candidates admissible in both folds participate. Ascending lexicographic
keys are: worst PATH_MOVED rollout RMSE ratio across two folds/four horizons;
worst overall rollout RMSE ratio; worst integrated one-step p95 ratio;
total nominal coefficients 2P; L; d; lexical candidate ID.
Ratios use float64, 0/0=1, positive/0=POSITIVE_INFINITY (serialized as a tag).
Negative/nonfinite metric inputs or positive-denominator overflow invalidate
the candidate. No graph-based preference, local search or policy change.

Zero admissible candidates means HURDLE_NO_ADMISSIBLE_CANDIDATE and
MODEL_SELECTION_FAILED_CLOSED. One means HURDLE_SINGLE_ADMISSIBLE_CANDIDATE;
multiple use the frozen ranking. Any selection is retrospective configuration
selection only. Gate relaxation, new candidates, weights, ridge, removed
PATH_MOVED protection or expanded d/L search require separate redesign authority.
No pooled A+B model or pooled threshold may be produced.

## Regression risk and acceptance

Risk: a declaration may be misinterpreted by a future executor. Exact source
and contract hashes, literal equations, boundary cases and synthetic tests
make interpretation reviewable. The future executor still needs separate
authorization and actual-data repeatability; synthetic success is no empirical
evidence. Both routes have prior numeric exposure, so this is retrospective
development, never independent validation.

No controller/safety/actuator interface is touched. S3 stays source-mechanism
blocked. Both stage coefficients remain EMPIRICAL_PREDICTIVE_PARAMETERS;
the threshold is a model decision threshold, not a physical EPS deadzone.
CLOSED_LOOP_IDENTIFICATION_BIAS_RISK remains. Existing calibration/reference,
TA/SG/H1, HOLDOUT and vehicle blockers are preserved in readiness.

Rollback means ceasing use of this additive policy; never rewriting historical
evidence. Policy completion cannot start fitting. Final pooled refit remains
NOT_AUTHORIZED; HOLDOUT CLOSED, opening_count=0, no HOLDOUT metadata search.
Vehicle authority NONE; NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED remain.

## Validation method and actual results

Validation results and log hashes are recorded in the separate additive
empirical-hurdle-fitting-policy-regression-validation-v1.json after all checks.
Checks: focused synthetic/policy tests, design and S2-RI reconstruction/attribution,
combined empirical, full AutoTune+controls, lateral replay, Ruff, compileall,
JSON/publication/privacy/authority, diff --check, SCons and independent review.
Browser and actual private fitting are not applicable/not authorized.

Replay, simulation and shadow vehicle qualification: NOT_RUN, no authority.
The lateral test suite is software regression evidence only.
Commit/push and exact-HEAD CI are verified after the implementation checks;
the pre-commit receipt does not preclaim future CI success.

## Handoff

HURDLE_FITTING_POLICY_FROZEN with 16 tied structures and 32 future jobs.
Optimizer, convergence, threshold algorithm, Stage 2 solver, all admission
populations and selection order are frozen. No actual threshold, coefficient,
normalizer, support, metric, prediction or winner was computed.
A separately authorized fitting increment is required before execution.

## Completed local validation

- Focused Hurdle fitting policy: 40 tests + 64 subtests PASS.
- Prior Hurdle design and S2-RI reconstruction/attribution: 180 PASS.
- Combined empirical test files: 1,515 tests + 385 subtests PASS.
- Full AutoTune + controls runner: 4,374 PASS.
- Focused lateral replay: 16 PASS.
- Ruff, compileall, all public JSON parsing, publication/privacy/authority,
  git diff --check and SCons: PASS.
- Two separate policy CLI processes: identical publication bytes and exact resume.
- Independent whole-change review: no important/blocking findings. The requested
  explicit z=X@beta field was added with a failing-then-passing synthetic test.
- Historical tracked artifacts remain byte-identical; private stores were not
  opened and no filesystem-wide byte-preservation claim is made.

Commands used the supported Ubuntu 24.04 environment, Python 3.12.13 and
NumPy 2.5.3. Full regression used
python tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j 1.
Combined empirical used pytest on test_empirical_*.py; focused tests used pytest.
Build used scons -u -j2. Logs/source/artifact hashes are bound in the separate
regression-validation receipt. Exact-HEAD CI is checked after push.
