# S2-RI retrospective fitting policy

## Identity and purpose

Cyber Validation / AutoTune, policy implementation. Baseline is CyberPilot
feature/cyber-autotune at 68fdcdc1334f682f9300b2f6bf3230074f79922c.
This additive increment freezes future S2_RI_V1 fit/CV/selection decisions before
performance can be inspected. It creates no coefficients, predictions, metrics,
normalizers, rollout or selected candidate. Private arrays and raw logs are not
opened. No vehicle applicability or physical EPS qualification is conferred.

## Original references

The source is https://github.com/rownlvh8875-coder/CyberPilot at the baseline above.
Fourteen S2-RI public input files are bound by exact file SHA-256 and canonical
receipt SHA-256 in empirical_s2_ri_fitting_policy.py. These include design,
signal, angle grid, rate-free identity, row admission, target, history/reset,
support, structural diagnostics, route CV, future metrics, readiness, execution
validation and regression validation. Receipt or byte drift fails closed.

The existing empirical_plant_policy canonical JSON/seal/immutable persistence
helper is reused. No simulator coefficients, candidate ranking or external code
are imported. Upstream layout, license, dependencies and submodule gitlinks stay
unchanged. There are no production integration points.

Call path: manual policy CLI → fixed public JSON binding → declarative contracts
and candidate definitions → closed bundle validator → immutable public JSON.
It does not import numeric extraction, model execution or controller modules.

## Frozen candidates and features

The user predeclared d in {0,5,10,20} and L in {1,5,15,45}, with Lu=Ldelta=L:
exactly 16 candidates in lexical ID order, each followed by FOLD_A then FOLD_B.
All 32 jobs must eventually have receipts, including precondition failures; no
early stopping after a promising candidate. This increment executes zero jobs.

d is a COMMAND_HISTORY_OFFSET_SAMPLES parameter. Its descriptive 100 Hz mapping
is 0/50/100/200 ms, not physical EPS delay. L fixes command and observed increment
history length. Parameter count P=2L+3 is 5/13/33/93; d adds no coefficient.

For target delta[k]=tick[k+1]-tick[k], exact fitting column order is:
intercept, u[k-d-L+1..k-d] oldest first, delta[k-L..k-1] oldest first,
current angle_tick[k], current vEgo[k]. Historical structural audits used
newest-first history columns; this is an explicit within-history permutation of
the same feature set. Historical source and artifacts are not rewritten.
The per-candidate ordered column list and digest are bound.

The primary scope is SCOPE_ALL_ACTIVE_NO_OVERRIDE: exact rate-free source
identity and source grid, active, no pressed/fault state, drive gear, vEgo>=5 m/s,
fresh latest-past source data (20 ms), exact 10 ms grid, same rlog/segment/run.
All history must remain eligible; reset, gap, inactive or reengagement cannot
carry stale history. SCOPE_NON_RAIL_ACTIVE_NO_OVERRIDE is diagnostic only and
cannot affect admission, ranking or selection.

No steeringRate, request, request-output difference, raw-command duplicate,
driver torque, flag numeric features, speed-bin model, interaction, polynomial,
future angle/command, gyro/yaw, planner/modelV2 or qlog feature is allowed.
torqueOutputCan remains bridge provenance. The primary command is a logged
post-CarController normalized representation, not physical applied EPS torque.
Transaction linkage remains unavailable.

## Fitting and normalization declarations

The future method is deterministic float64 ordinary least squares, declared as
numpy.linalg.lstsq, NumPy 2.5.3, rcond=None. Its documented default relative
cutoff is float64 machine epsilon times max(M,N) of the effective standardized
TRAIN matrix. OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1 are required; no RNG.

Only candidate-specific TRAIN anchors provide population means and population
standard deviations (ddof=0). Intercept remains one, unscaled. Constant TRAIN
features map to FROZEN_TRAIN_ZERO_COLUMN, including on DEVELOPMENT; observed
development variation is report-only, never a normalizer refit. No pooled,
development or HOLDOUT statistics and no target normalization are permitted.

Constant non-intercept columns are removed before effective-rank checking and
solving; their nominal coefficient slots are fixed zero by the schema, not
clipped after fitting. Nonconstant columns plus intercept must have full
numerical rank under the frozen NumPy SVD tolerance. Unexpected deficiency is
FIT_PRECONDITION_RANK_FAILURE, with no solve or tolerance retry. Returned solver
rank must agree. Nonfinite inputs/statistics/outputs invalidate the fold.
Condition number is reported without an invented cutoff.

No ridge, lasso, prior, optimizer, gradient descent, sparsification, coefficient
clipping or pseudoinverse fallback is admitted. Keeping OLS removes additional
regularization/search dimensions.

## Two retrospective folds

Exact opaque route identities are loaded from the historical route-CV receipt.
FOLD_A trains on route A and develops on B; FOLD_B reverses those roles.
Random row/segment splits and pooled development gating are forbidden.
Both routes have prior exposure: these are retrospective development results,
not independent validation or qualification. The declared ordering is route,
source-segment content SHA, then aligned row index; numeric results never set
ordering or weighting.

## Additive direct-tick observation projection

The user approved direct ROUND_HALF_TO_EVEN on the binary64 continuous next tick.
This is a new fitting-grid contract, not a rewrite or a claim of bitwise
equivalence to the historical degree-roundtrip policy. Both historical receipt
identities remain bound. The synthetic contract example 14.5 tick rounds directly
to 14; multiplying by binary64 0.1 then dividing by 0.1 can produce a value above
14.5 and round to 15. No model output was used to choose the rule.

The projected integer must be within signed16 source codes [-32768,32767].
Nonfinite/range failure invalidates the candidate/fold, never clips or removes
anchors. Float32(code*0.1) may display source degrees, but primary evaluation uses
ticks, not display-rounding errors. The historical SOURCE_GRID_OBSERVATION_REJECTED
verdict and its closed ARX1/FIR25 track remain immutable.

## One-step and recursive semantics

One step declares continuous_delta_tick and continuous_next_tick=current_tick+
continuous_delta_tick. The next-angle and delta errors are algebraically the
same; the metric contract uses one canonical error buffer and explicitly reports
the metrics as aliases, not independent evidence.

Rollout starts at observed tick k and history through k. Step 1 predicts k+1.
Each step projects to an integer source tick; that projected tick and differences
of projected ticks become recursive state/history. No continuous feedback and
no future measured angle/delta/rate are allowed in features.

Recorded logged command and vEgo at each recursive step are exogenous sequences.
Their own source-time ordering must remain latest-past at that recorded step.
This is LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT, not autonomous driving
prediction. Future measured angle is a scoring endpoint only.

Horizons 0.25/0.5/1/2 seconds mean exactly 25/50/100/200 updates, ending at k+H.
Primary horizon metrics use projected endpoint errors across eligible anchors,
not the average of intermediate errors. All history and horizon rows must stay
within the same route, rlog segment, S2-RI run, eligible regime and exact grid.
No padding or cross-boundary state. Each candidate/fold/anchor has independent
state.

## Comparator, metrics and gate

HOLD_LAST_ANGLE predicts observed tick k for one step and holds the initial tick
constant for every recursive step. Historical ARX/FIR is not an automatic
comparator. Candidate and hold-last use exactly the same ordered anchor set
and support digest for each fold/horizon. Candidate-specific histories can give
different populations across candidates; counts must be reported, never hidden.
Every development metric population needs at least the existing 201 anchors.
Unavailable support is determined before prediction; numerical failure cannot
shrink the scored population.

Metrics use float64 tick-coordinate errors: sqrt(mean(error squared)),
mean(abs(error)), and NumPy percentile(abs(error),95,method=linear).
One-step projected exact-hit and within-one-tick rates are integer count/N.
Reduction order is fixed. Fold-specific results come first; equal-route summary
is primary, sample-weighted pooled summary supporting only.

Each fold must satisfy:
- One-step continuous next-angle RMSE strictly below hold-last.
- One-step MAE and p95 no worse.
- At every horizon, projected endpoint RMSE, MAE and p95 no worse.
- Projected one-step exact-hit and within-one-tick rates no lower.
- Finite metrics, full effective TRAIN rank, support and identical comparator
  anchors, no source-range violation.

No epsilon, percentage allowance or significance margin. Tying every metric is
not admissible. Pooled or non-rail results cannot rescue a fold.

## Deterministic selection and failure

Only candidates passing both folds enter a lexicographic ascending order:
1. Worst rollout RMSE ratio across both folds and all four horizons.
2. Worst one-step next-angle p95 ratio across both folds.
3. Nominal parameter count.
4. L.
5. d.
6. Lexical candidate ID.

For a zero comparator denominator, 0/0 maps to 1.0, positive/0 to positive
infinity. Nonfinite/negative metric inputs are rejected; JSON represents
infinity with an explicit symbol rather than nonstandard NaN/Infinity tokens.

Zero admissible candidates gives S2_RI_NO_ADMISSIBLE_CANDIDATE and
MODEL_SELECTION_FAILED_CLOSED; no gate relaxation, candidate expansion or
regularization addition. One gives S2_RI_SINGLE_ADMISSIBLE_CANDIDATE. Multiple
give S2_RI_RETROSPECTIVE_CV_SELECTED through the frozen order. These are future
state definitions, not results generated here.

Selected parameters would be EMPIRICAL_PREDICTIVE_PARAMETERS. Closed-loop
identification bias is unresolved. There is no causal torque gain, true plant,
physical EPS coefficient or physical delay claim.

## Regression risk and authority

Main risks are resealed policy drift, hidden runtime imports, historical column
order reuse, degree/tick rounding ambiguity, normalization leakage, skipped
folds/horizons, unequal comparator populations and false model authority.
Strict canonical full-bundle comparison rejects unknown fields and modified
receipts even when resealed. All historical input file hashes are checked.

Rollback consists of leaving this additive policy unused; no existing reader,
dataset or controller is changed. Future S2_RI_RETROSPECTIVE_FIT_AND_CV_V1 needs
separate explicit authorization. FINAL_POOLED_REFIT_NOT_AUTHORIZED remains
frozen even if a future retrospective candidate passes. Handoff would contain
only selected configuration and two fold model lineages, not a pooled final
model or HOLDOUT admission.

HOLDOUT remains CLOSED, opening_count=0, reservation=NONE. Future untouched
HOLDOUT, all calibration/reference blockers and vehicle activation blockers
remain. TA/SG execution/composition, raw and qlog access, production/device
writes remain prohibited.

## Validation method and actual results

All local checks passed after the independent review fix, in Ubuntu 24.04 WSL
with the prepared virtual environment. Exact commands, receipt/log hashes and
counts are in empirical-s2-ri-fitting-policy-regression-validation-v1.json.

| Check | Actual result |
| --- | --- |
| Focused fitting-policy/publication | 56 passed, 48 subtests |
| Combined empirical + future empirical | 1,289 passed, 264 subtests |
| Full official AutoTune + controls runner, one worker | 4,063 passed in 1,571.68 s; AutoTune 3,921 + controls 142 |
| Lateral replay | 16 passed |
| Ruff / compileall / JSON / git diff --check | PASS |
| SCons -j2 | PASS |
| Publication/privacy/authority | PASS, zero findings |
| Two public generation/resume calls | Exact policy SHA and bytes |
| Historical tracked edits | Zero; additive files only |
| Browser / actual fitting | NOT_APPLICABLE / NOT_AUTHORIZED |

Independent read-only review found one P2 publication issue: late .atomic
files were not preflighted by the new publisher. Four tests reproduced
noncanonical resume bytes, late corruption, symlinks and missing postcondition
verification. The additive publisher now checks all final/atomic paths and exact
bytes before any writes, then final bytes before success. RED→GREEN and full
regression passed; the historical persistence helper remains unchanged.
No unresolved findings.

Manual public-only regeneration/resume command:
python -m openpilot.tools.cyber_autotune.empirical_s2_ri_fitting_policy --output docs/cyberpilot/changes

The policy receipt is
05cf63752587105d188bff2f81baec32e8192a689cbf09543caf1f954656ac96.
The commit's GitHub Actions result is verified separately after push; this
precommit record does not claim a future CI result.

## Handoff

No private store was opened or byte-scanned in this increment. Preservation of
private evidence is by zero access/write, not a claimed re-hash of its contents.
Public historical input files are byte-pinned; final Git diff must be additive.
No fitting, selection, CV scoring, prediction, residual, normalizer or rollout
execution occurred. Only policy definitions and a validator were implemented.
