# Rate-independent Hurdle family design V1

## 쉽게 보는 설계

기존 S2-RI는 실제 각도가 변한 MOVE 관측에서는 큰 오차를 줄였지만,
전체 평가 관측의 약 85.23–85.90%인 STATIC에서도 불필요한 변화를 만들어
MAE와 exact-hit 기준을 통과하지 못했다. 32개 candidate/fold 모두 같은
tradeoff를 보였으므로, 관측값의 변화 여부와 변화량을 분리하는 새 family를 설계했다.

HURDLE_RI_V1은 먼저 다음 source-grid tick이 변할 확률을 판단하고,
predicted gate가 MOVE인 경우에만 conditional signed delta model을 사용한다.
STATIC이면 현재 tick을 정확히 유지한다. MOVE여도 grid projection 결과가
현재 tick과 같을 수 있으며, 인위적으로 최소 1 tick 움직이게 만들지 않는다.

이번 결과는 설계 계약이다. private arrays를 열거나 학습·예측·rollout·평가를
실행하지 않았다. probability threshold는 0.5로 가정하지 않고 UNSET이다.
optimizer, convergence, solver, threshold 동률 처리, acceptance와 selection은
별도 HURDLE_FITTING_POLICY_V1에서 실제 성능을 보기 전에 동결해야 한다.

Hurdle은 STATIC false movement 문제를 직접 다루려는 구조이지만 장기 rollout
문제의 해결책으로 검증된 것은 아니다. V2에는 PATH_MOVED의 장기 오차 악화도
있다. 기존 S2_RI_NO_ADMISSIBLE_CANDIDATE 판정은 그대로 유지한다.

## Identity and purpose

- Area: Cyber Validation; HURDLE_FAMILY_DESIGN_V1.
- Family: HURDLE_RI_V1 / RATE_INDEPENDENT_HURDLE_DELTA_ANGLE_MODEL_V1.
- Baseline: 49f6909af65874e3c2b3cc2de2c621b137fb04fc,
  feature/cyber-autotune,
  [CyberPilot](https://github.com/rownlvh8875-coder/CyberPilot).
- Scope: additive, public-only machine-readable contracts and their validator.
  No production interface, private numeric access or vehicle applicability.
- Completion means READY_FOR_SEPARATE_FITTING_POLICY, never MODEL_READY.

## Original references and lineage

The builder pins exact file SHA256 and canonical receipt SHA256 of 49f public
attribution readiness, mechanism summary, Hurdle review trigger and validation,
plus S2-RI source-signal/grid/causal-identity/row-admission/target/history/route-CV
and fitting-feature/direct-tick-grid contracts. Historical fit readiness and
selection are also pinned. All remain immutable.

The trigger is actual evidence: 32/32 jobs have MOVE delta SSE < 0, STATIC
delta SAE > 0 and worse STATIC exact-hit than HOLD_LAST. It supports a design
review; it does not authorize training.

Public V2 rollout evidence has these PATH_MOVED SSE counts:

| Horizon | Improvement jobs | Regression jobs | PATH_FLAT SSE regression jobs |
| --- | ---: | ---: | ---: |
| 25 | 25 | 7 | 32 |
| 50 | 18 | 14 | 32 |
| 100 | 17 | 15 | 32 |
| 200 | 7 | 25 | 32 |

The request's 100-step summary says 16/16. The SHA-pinned 49f artifact says
17/15; this design preserves the artifact and explicitly records the discrepancy.
There is no recomputation from private evidence.

Source code reuses local canonical JSON hashing/immutable persistence and
pinned public feature layout definitions. Existing repository licensing and
attribution apply. No external code, dependencies, gitlinks, LFS objects or
upstream control interfaces are changed.

Call path: fixed public JSON files → byte/receipt/state validation →
declarative contract construction → closed bundle validation →
atomic additive public publication. No model executor or private store loader
is imported or exposed.

## Changes and expected effect

New empirical_hurdle_design.py owns fixed evidence admission, complete-bundle
validation and immutable publication. empirical_hurdle_contracts.py defines
the new family; the test module exercises authority, leakage, lineage,
structural and storage invariants.

The expected effect is a reproducible, reviewable family definition with
unresolved fitting freedoms explicitly deferred. There is no claimed empirical
performance improvement for Hurdle, and no actual support calculation.

### Targets and populations

Stage 1, HURDLE_MOVE_GATE_V1, is conceptually BINARY_LOGISTIC_MOVE_GATE:

move_label[k] = 1 if delta_tick[k] != 0, else 0.

delta_tick[k] = tick[k+1] - tick[k]. It denotes
MEASURED_SOURCE_GRID_TICK_CHANGED_NEXT_SAMPLE, not physical EPS movement,
steering-rate activity or actuator acknowledgement. No magnitude tolerance,
speed threshold or alternative label boundary is allowed.

Stage 1 TRAIN includes all eligible anchors with valid next targets,
STATIC and MOVE. Stage 2, HURDLE_CONDITIONAL_DELTA_V1, is conceptually
CONDITIONAL_LINEAR_DELTA_REGRESSION and trains only the exact Stage 1 TRAIN
subset whose true move_label equals one. Its target is signed delta_tick.
STATIC zero-target rows are excluded from Stage 2 training. Old S2-RI
coefficients and normalizers are historical evidence, never Stage 2 initialization
or a ready conditional model.

No class weights, resampling, synthetic balancing, SMOTE, duplicated support,
magnitude weighting or sign weighting are allowed. Stage 1 requires both
classes present. Stage 2 future minimum support must be based on max(P,201);
the exact sufficiency comparison and failure behavior must be frozen by the
future fitting policy, before results. Actual counts are NOT_COMPUTED here.

### Features, timing and scope

Both stages share one chronological feature vector:

1. Intercept.
2. Commands u[k-d-L+1 .. k-d], oldest to newest.
3. Prior observed increments delta[k-L .. k-1], oldest to newest.
4. Current integer angle tick[k].
5. Current vEgo[k], m/s.

Command is LOGGED_POST_CARCONTROLLER_NORMALIZED_COMMAND. A tick is the
source-proven SAS_Angle 0.1-degree measurement grid. Past signed increments
are observed differences, not physical steering-rate sensor readings.
steeringRateDeg and SAS_Speed have no feature, label, admission or reset role.

Controller request, request-output difference, raw command duplication,
driver torque, numeric pressed/fault indicators, gyro/yaw, modelV2/planner/path/lane,
future measured state and qlog are forbidden features. No speed interaction,
speed-bin one-hot or angle polynomial is added. Driver/activity/fault fields
remain eligibility/context only.

The inherited rate-free identity is used as pinned; historical generic
rate-dependent causal IDs remain immutable references. Primary scope is
ALL_ACTIVE_NO_OVERRIDE: active, no steeringPressed or EPS faults, drive gear,
existing speed minimum 5 m/s, diagnostic/source/grid validity, frozen latest-past
20 ms health, exact 154 RLOG identity admission and zero qlog support.
No raw extraction or private admission is performed during this design.

Histories and targets stay within the same route, segment, S2-RI run,
eligible streak and exact 100 Hz grid. Inactive/override/fault/gap/reengagement
and boundaries reset history. No padding, interpolation or carry across reset.
d is COMMAND_HISTORY_OFFSET_SAMPLES, not a physical EPS delay.
REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE and
PHYSICAL_EPS_APPLICATION_UNAVAILABLE remain.

### Sixteen tied structures and normalization

d is one of 0,5,10,20 and L is one of 1,5,15,45.
Both stages share d and L, with Lu=Ldelta=L. Exact HRI_Dxx_Lxx IDs are
published in lexical order. There is no 16×16 independent-stage expansion,
search execution or selected configuration.

| L | P per stage | Total nominal coefficients |
| --- | ---: | ---: |
| 1 | 5 | 10 |
| 5 | 13 | 26 |
| 15 | 33 | 66 |
| 45 | 93 | 186 |

P=2L+3. Threshold is a separate decision-policy parameter, not a coefficient.

Future Stage 1 normalization uses its TRAIN population only; Stage 2 uses
its TRAIN MOVE subset only. No forced shared normalizer, DEVELOPMENT,
pooled or HOLDOUT statistics. Population mean/std are conceptual, intercept
is one and unscaled, train-constant columns remain frozen zero, and
development drift is report-only. Exact effective-column/solver treatment
belongs in fitting policy. No mean/std is computed now.

### Hard composition and recursive state

Threshold value and equality direction are both UNSET. There is no hidden
default 0.5 or threshold search. A separately frozen rule must map p_move
to the predicted branch.

STATIC returns exact zero delta and the current projected tick, without
calling Stage 2 or projection. MOVE applies the Stage 2 TRAIN normalizer and
conditional predictor, adds its continuous delta to the current projected
tick, then uses DIRECT_ROUND_HALF_TO_EVEN_TO_INTEGER_TICK.
No epsilon, clipping or forced minimum movement; signed16 tick-range and
finite-input failures must fail closed. MOVE can still project to zero change.

No p_move × delta soft mixture, debounce, sticky gate, hysteresis thresholds
or minimum on/off durations. Temporal context comes only from causal history.

Recursive rollout initializes from observations through anchor k. At every
step it constructs features from projected state/history, calls Stage 1,
uses the frozen threshold rule, calls Stage 2 only for predicted MOVE, updates
projected delta history and advances recorded command/vEgo. Future measured
angle/delta is never fed back; actual future angles are scoring references only.

This is LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT, not autonomous driving
prediction. Horizons 25/50/100/200 mean endpoints k+H after H transitions at
100 Hz. Entire history and horizon must remain eligible and continuous.
There is no short-horizon padding. Long-horizon performance must be evaluated
separately; one-step improvement alone cannot establish success.

### Evaluation, diagnostics and unresolved fitting policy

Primary future evaluation uses integrated predicted-gate output on ALL
eligible development anchors and HOLD_LAST on the exact same ordered anchors.
Continuous RMSE/MAE/p95 and projected exact-hit/within-one-tick are required,
as are endpoint angle RMSE/MAE/p95 at all four rollout horizons.
STATIC/MOVE and false/missed-motion diagnostics remain visible.

Stage 1 confusion, precision/recall, specificity and balanced accuracy;
Stage 2 true-MOVE error/sign/grid diagnostics; and an optional future oracle
true-label gate are diagnostic only. Oracle cannot admit, rank or select a
candidate and is not deployable. True labels may select diagnostic populations,
but cannot select branches in primary inference.

HURDLE_ACCEPTANCE_POLICY=REQUIRES_SEPARATE_PREDECLARATION. The old S2-RI gate
is not copied automatically. Future policy must freeze both solvers and their
failure/convergence rules, threshold semantics and permitted finite search,
stage normalizers, minimum support, exact structures/folds, metric reductions
and undefined-rate semantics, full rollout evaluation, acceptance, deterministic
selection and zero-candidate behavior before performance is observed.

Route-CV binds the existing opaque fold identities: A trains/B develops,
then B trains/A develops. No random row/segment or pooled split.
Both routes have prior exposure: RETROSPECTIVE_ROUTE_LEVEL_DEVELOPMENT,
not independent validation or HOLDOUT.

## Regression risk and acceptance

Risks are accidental execution authority, hidden rate dependence, label leakage
into primary branch selection, normalizer leakage, silent structural expansion,
or treating a design trigger as model readiness. Closed validation rebuilds
the complete canonical bundle; even resealed unauthorized fields are rejected.
Public inputs require both exact byte and receipt hashes plus authoritative
state checks. Publication preflights every destination, rejects symlinks and
traversal, allows byte-exact resume and never overwrites differing evidence.

Tests trap solvers/imports/numeric array loading and restrict builder reads to
fixed public inputs and its two source files. No private store is scanned to
claim immutability: private evidence is simply not accessed or written.
Historical tracked files remain byte-identical because this increment is
additions only. Rollback is ceasing use of this new design; no controller or
historical state needs restoration.

CLOSED_LOOP_IDENTIFICATION_BIAS_RISK persists. Parameters would be
EMPIRICAL_PREDICTIVE_PARAMETERS, not physical EPS coefficients. STATIC branch
or future probability threshold is not a physical deadzone. S3 remains blocked.

## Validation method and actual results

Actual local results: 54 focused design tests; 126 prior reconstruction and
attribution tests; 1,560 combined empirical tests plus 321 subtests; 4,334 full
AutoTune/controls tests; and 16 lateral replay tests PASS. SCons, Ruff, syntax,
JSON and publication/privacy checks PASS. Independent review found no critical
or important issues. Two public generation processes produced exact bytes and
verified immutable resume. No private numeric inputs were used.

Commands: python -m unittest for focused modules; pytest -q on the empirical
test files; python tools/test_runner.py openpilot/tools/cyber_autotune/tests
openpilot/selfdrive/controls/tests -j 1; scons -j2; repository Ruff/compileall
and tools/cyberpilot/check_publication.py --base origin/main.
Environment: Ubuntu 24.04, repository .venv, OPENBLAS_NUM_THREADS=1 and
OMP_NUM_THREADS=1 for regression. NumPy is used only by synthetic/regression
tests, not by the design builder.

Check counts and log hashes are recorded in the additive
design regression validation receipt. Required checks are focused design tests,
prior reconstruction/attribution and combined empirical regression, full
AutoTune/controls, lateral replay, Ruff, syntax, JSON, publication/privacy,
diff whitespace, SCons and independent review. Exact-HEAD CI is verified after
push and is not preclaimed by design generation.

Replay/simulation/shadow/vehicle tests and actual fitting are NOT_AUTHORIZED
for this design-only task. Browser is NOT_APPLICABLE.

## Handoff

Expected status: HURDLE_FAMILY_DESIGN_READY_FOR_SEPARATE_FITTING_POLICY.
MOVE_GATE_THRESHOLD_POLICY and HURDLE_ACCEPTANCE_POLICY remain NOT_YET_FROZEN.
Model/move-gate/conditional-delta/normalizer fitting, threshold selection, CV,
prediction, rollout and selection remain NOT_RUN.

Preserve S2_RI_NO_ADMISSIBLE_CANDIDATE, MODEL_SELECTION_FAILED_CLOSED,
the strict V2 tradeoff and its design-review trigger; original 7f94 insufficient,
1134 reconstruction and a50d fit/CV evidence remain historical facts.

Dataset PARTIAL, NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, closed ARX1/FIR25 track,
original S1/S2 rate blocks, S3 source-mechanism block, Stage B block,
TA_STANDALONE_TRADEOFF_ONLY, SG_CLOSED_LOOP_TRADEOFF_ONLY,
COMPOSITION_NOT_RECOMMENDED / NOT_AUTHORIZED, SEARCH_NOT_AUTHORIZED and
FINAL_POOLED_REFIT_NOT_AUTHORIZED remain.

HOLDOUT is CLOSED, opening_count=0, future untouched HOLDOUT required.
Calibration/independent-calibration/pixel-registration remain pending;
metric calibration and independent reference unavailable.
Sealed reference NOT_GENERATED. Vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED. No next fitting-policy or model execution begins
automatically.
