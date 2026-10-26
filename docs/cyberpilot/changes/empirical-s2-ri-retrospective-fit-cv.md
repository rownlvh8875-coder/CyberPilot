# S2-RI retrospective fit and route-level development CV

## Scope and upstream relationship

This increment executes the frozen S2_RI_V1 policy against the existing,
previously exposed two-route development pool. It adds offline validation
modules only. No upstream controller, cereal schema, vehicle interface, device
or safety authority changes. All historical artifacts remain immutable.

Source repository: rownlvh8875-coder/CyberPilot, feature/cyber-autotune.
Startup baseline: d954267e692d9a9faf74b56a7e22bd5489b98988.
Exact baseline CI: 38203411742, completed/success. Existing licenses and
submodule identities are retained; no external implementation was imported.

Frozen fitting policy receipt:
05cf63752587105d188bff2f81baec32e8192a689cbf09543caf1f954656ac96.
The authorization artifact binds the complete historical contract chain,
source/derived dataset identities and executor source hashes.

## Fixed experiment and parameter meaning

Exactly sixteen configurations combine command offsets 0, 5, 10, 20 samples
with equal command/delta history lengths 1, 5, 15, 45. Candidate IDs are the
frozen S2RI_Dxx_Lxx names; lexical order is followed, with FOLD_A then FOLD_B.
There are 32 jobs per independent execution. No additional candidate, delay
search, history search, gate change or regularization is permitted.

FOLD_A trains route 7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677
and develops on 962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c.
FOLD_B reverses these roles. These are retrospective development folds, with
prior numeric exposure on both routes.

Features are intercept; logged normalized post-CarController command history
oldest to newest; observed signed angle-increment history oldest to newest;
current angle tick; current vEgo. Nominal parameter counts are 5, 13, 33 and 93.
The primary scope includes all active/no-override eligible rows, including rail
rows. The non-rail scope never controls admission or selection.

A command offset is an empirical history coordinate, not physical EPS delay.
The command is a logged representation; physical EPS application remains
unavailable. Steering-rate, controller request and duplicate raw-command
features are absent. Coefficients are empirical predictive parameters under
closed-loop identification bias, not physical actuator coefficients.

## Admission, normalization and fitting

Only the exact 154-rlog causal cache and its immutable S2-RI derived identity
are admitted. Qlog identities are denied before array access. The frozen final
readiness resolver and source/profile/config/segment receipts are checked.
A private execution authorization is sealed before arrays are opened.

History uses the family-specific rate-free run and eligible streak, within one
route and rlog segment at exact 100 Hz. The historical generic rate-dependent
run identity is not a modeling gate. No raw log or HOLDOUT opening occurs.

Each candidate/fold computes float64 population mean/std from its TRAIN design
rows only. Intercept remains one. Exact constant TRAIN columns are removed
before rank/solve and receive zero nominal coefficients. Development variation
in a TRAIN-constant column is reported without refitting. Effective input rank
must equal column count; condition number is descriptive, without a cutoff.

The solver is pinned NumPy 2.5.3 numpy.linalg.lstsq with rcond=None, float64,
OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. Invocation is recorded separately
from success, including numerical failures. No optimizer or pooled refit exists.

## Error, projection and recursive rollout

Before actual metric execution the user resolved an operation-order conflict
in favor of the frozen contract: predicted delta minus observed delta is the
canonical binary64 error buffer. One-step delta and continuous next-angle
metrics alias that same buffer; they are not independent evidence. Historical
metric receipts were not modified.

Projection applies direct half-to-even rounding to the binary64 next tick,
then enforces signed16 tick range. There is no clipping or epsilon. Any
nonfinite prediction or invalid projection invalidates the entire fold.

Recursive state is the projected integer tick; delta history uses differences
of projected ticks. Only initial measured history is used. Future measured
angle/delta cannot enter the recursive API. Recorded command and vEgo advance
as exogenous sequences: LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT.
This is not autonomous future-driving prediction.

Rollout horizons are exactly 25, 50, 100, 200 updates, scored at endpoint k+H.
Entire history and future horizon must share the eligible continuity interval.
HOLD_LAST_ANGLE holds the initial observed tick constant. Candidate and
comparator share the exact ordered anchor SHA at each population. Every
development population requires at least 201 anchors.

Metrics use float64 tick error: RMSE, MAE and linear-percentile p95 absolute
error. One-step projected metrics count exact hits and within-one-tick hits.
No sample with a bad prediction is dropped.

## Frozen admission and selection

Both folds must independently satisfy strict one-step RMSE improvement,
non-worse one-step MAE/p95 and grid hit rates, and non-worse RMSE/MAE/p95 at
each rollout horizon. Comparisons use computed finite floats without epsilon.
All ties fail the strict RMSE gate.

Only admissible configurations enter the frozen ordering: worst rollout RMSE
ratio, worst one-step p95 ratio, parameter count, L, d, lexical ID. A zero
comparator denominator gives ratio one for zero/zero and positive infinity
for positive/zero. Zero admissible candidates fails closed without redesign.

## Integrity, privacy and validation

Private persistence is atomic and immutable, with per-job receipts and final
manifest written last. Completed resume verifies exact authorization, job
identity, required files, model lineage and selection consistency, without
loading numeric arrays or recomputing models. Conflicting bytes, symlinks,
traversal and overlapping stores are rejected.

Two complete independent executions are required. Model/normalizer bytes,
prediction and projected rollout hashes, ordered anchors, metrics, gates,
selection and all manifests must match exactly. Only aggregate metrics/counts,
opaque route identities and receipt hashes are public. Coefficients, means,
standard deviations, raw predictions/targets and per-row data remain private.

Pre-execution independent review found two receipt-integrity issues (stale
resume identity validation and solver-invocation accounting). Both were fixed
before real metrics and independently verified. An initial metadata-only
admission attempt also found an incorrect interpretation of the historical
derived receipt-set hash; it was corrected before authorization or arrays.

Final runtime outcomes and regression evidence are recorded in the additive
fit-CV artifacts. They do not change historical verdicts. No selected model is
admitted for future HOLDOUT; untouched future HOLDOUT is still required.
Final pooled refit, TA/SG composition, production and vehicle authority remain
unauthorized.

## Observed execution outcome

All 32 jobs completed with actual solver invocation and full effective rank:
eight jobs each at ranks 5, 13, 33 and 93. There were no numerical,
precondition or insufficient-support failures. Candidate/fold TRAIN and
one-step DEVELOPMENT populations range from 183,711 to 336,941 anchors.

| Rollout updates | Minimum anchors | Maximum anchors |
| --- | ---: | ---: |
| 25 | 174,252 | 268,108 |
| 50 | 167,526 | 255,466 |
| 100 | 157,408 | 240,329 |
| 200 | 143,260 | 219,711 |

Every fold passed the strict one-step RMSE comparison, but all 32 failed
one-step MAE and exact-next-angle hit rate. All 32 also failed the 25-step
rollout p95 condition. Therefore no candidate passes both complete fold gates.
One-step candidate RMSE ranges from 0.43893498069552284 to 0.6317995179740898
ticks; corresponding population HOLD_LAST RMSE values range from
0.580871164714488 to 0.7627907696687036 ticks. These ranges summarize different
populations and are not a substitute for the exact paired per-fold comparisons.

The complete one-step/grid/25/50/100/200 endpoint metrics and comparator values
are in empirical-s2-ri-fit-cv-results-v1.json. Candidate-level failed gates are
in empirical-s2-ri-candidate-gates-v1.json. No ranking key is generated for
inadmissible candidates and no candidate is selected.

Outcome: S2_RI_NO_ADMISSIBLE_CANDIDATE and MODEL_SELECTION_FAILED_CLOSED.
The frozen linear family failed this retrospective directional gate. This
does not authorize adding a candidate, changing the gate or fitting another
family. Further redesign requires a separate request.

Both independent 32-job executions produced identical manifest
9466e4578842b4c8a300bb843338e53b42a2fc75200879360f8212c7c2605c97.
All manifest-listed model/normalizer/prediction/rollout bytes and all receipt,
metric and selection bytes were verified. Repeatability:
FIT_CV_EXACT_REPEATABILITY_PASS.

Completed resume was exercised with eleven compute/decoder paths trapped,
including array loading, OLS, normalization, prediction, rollout and metrics.
It returned the same manifest. The resume verification receipt is
7d6420bc28223d5bec85052e4fa75d1f98b64a9e250dd132d5c875718a919788.

All receipt-listed rlog input files and S2-RI derived files were hashed against
their immutable bindings before and after each execution and on resume.
Unrelated historical stores and qlog stores were not opened or byte-scanned;
no claim of an external writer's global filesystem immutability is made.
Tracked historical artifacts were preserved byte-for-byte.

Final local validation passed: new fit/CV focused 57, frozen policy 56,
combined empirical 1,346, AutoTune 3,978, controls 142, lateral replay 16.
The supported full runner completed 4,120 tests in 1,692.55 seconds.
Ruff, compileall/syntax, JSON seals, SCons, diff whitespace and publication/
privacy/authority checks passed. Independent code, execution-JSON and final
publication reviews had no unresolved findings. Browser validation is not
applicable. Exact pushed-HEAD CI is verified separately after commit.
