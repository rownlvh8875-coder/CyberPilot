# Empirical plant V3 retrospective route development

## Identity and purpose

Cyber AutoTune / Validation, offline plant model development. Baseline is
2c3bdad7d66a62d0de4dbf91a97f1603e8030330 on feature/cyber-autotune.
This generation is **RETROSPECTIVE_MODEL_DEVELOPMENT**. It was authorized after
V2's frozen DEVELOPMENT route produced zero common design rows. V2 remains
permanently MODEL_SELECTION_BLOCKED: its roles, receipts, fits and empty model
maps are immutable. V3 does not fill in or repair V2's selection.

V3 reuses exactly the two admitted V2 TRAIN routes. It does not open another
route, a holdout, an image, GPS, a model/planner payload or a controller candidate.
It cannot establish empirical plant readiness or real-vehicle model validity.

## Original references

Repository: https://github.com/rownlvh8875-coder/CyberPilot, verified feature branch
and baseline above. The existing source-semantics audit and V2 public receipt pins
are input evidence. Public source/license identities remain in those immutable
receipts; no new source adaptation or source audit is performed.

Reused code: empirical_plant_model.py (ARX/FIR design, least-squares, stability,
statistics), empirical_v2_signals.py (aligned actuator runs),
empirical_signal_crosscheck.py and empirical_v2_generation.py (discrete yaw
correspondence). Exact source file hashes are in the V3 policy. NumPy and Python
versions, solver and BLAS settings are bound privately to every fold receipt.
Submodule gitlinks and production code are unchanged.

Data flow: pinned V2 split → exactly two TRAIN routes → immutable cache/source
verification → per-segment valid runs → whole-route inverted folds → TRAIN fit →
opposite-route DEVELOPMENT predictions → route-equal structure selection →
directional gate → conditional pooled refit → CLOSED future holdout package.

## Changes and expected effect

New empirical_v3_policy, empirical_v3_cache, empirical_v3_models,
empirical_v3_generation and empirical_v3_publication modules implement this
separate generation. They do not modify an existing empirical or controller
algorithm. The V2 DEVELOPMENT route is explicitly
V2_ZERO_SUPPORT_DEVELOPMENT_CONTEXT_ONLY and is never scored or fitted in V3.

FOLD_A trains on the lexical first V2 TRAIN route and develops on the second.
FOLD_B is the exact inverse. Full IDs come from the pinned split, without
hard-coded prefixes. No history crosses a route, segment, speed bin or invalid
mask. Source files are hashed without decoding logs again. Cached numeric
receipts are anchored through the publicly pinned V2 result → route → segment
chain; adapter, profile, source, opening and policy identities are rechecked.

All old policies remain: 100 Hz integer grid, latest-past only, maximum 20 ms
source age, no interpolation, unknown limits remain unknown. LOW is 5–15 m/s,
MEDIUM 15–25 m/s, HIGH at least 25 m/s. Each bin has the same eight configurations:
ARX1 and FIR25 at delays 0/5/10/20. Common DEVELOPMENT support is at least 201.
Delay is publish-time empirical lag including source/alignment age, not an
independent physical dead-time measurement.

Structure ranking minimizes worst-route one-step DEVELOPMENT RMSE, then equal
arithmetic mean of the two route RMSEs, then parameter count, family lexical and
delay. Sample count cannot dominate this ranking. ZERO_RESPONSE, HOLD_LAST_OUTPUT
and TRAIN_STATIC_GAIN share exactly the model's target origins.

Before fitting, the private policy freezes directional admission on both folds:
one-step and 1 s endpoint RMSE must strictly beat hold-last, MAE/p95 must not
worsen; all three metrics must not worsen against zero/static references. All four
endpoint horizons must have positive shared support and finite metrics; primary
scopes need 201 rows. This reuses strict no-worse principles without percentage
or absolute effect thresholds. A failed gate never enters the holdout package.

Only an admitted structure permits one pooled refit with the same family/delay.
A pooled model has no DEVELOPMENT metric claim because both routes train it.
Fold metrics remain the selection evidence. No fallback structure is selected
after the gate fails.

Yaw uses only the four existing ±deg/s, ±rad/s hypotheses, source-bound gyro
axis/sign/lag candidates, direct gyro correspondence and supporting kinematics.
Both inverted folds must agree, and every route must pass the existing
conservative gyro admission. Kinematic correlation alone is insufficient. Any
Stage B CV/refit remains separately gated.

## Regression risk and acceptance

Closed-loop observational identification can be biased. Route-CV development on
two old routes is retrospective and does not substitute for an untouched route.
The source age, masks, limited excitation and unknown clean limit mask remain
limitations. There is no controller ranking or weighted candidate score.

Private arrays contain separate TRAIN/DEVELOPMENT design, target and prediction
arrays for each fold/configuration/bin. Coefficients, raw residuals and traces
remain private. Atomic immutable writes reject stale generations and changed
resume data. Exact repeatability requires two complete executions with one BLAS
thread, fixed NumPy least-squares and no RNG.

Rollback removes only this additive generation. All V2 and older evidence is
preserved. Independent review is required; vehicle promotion is not authorized.

## Retrospective development results

The two reused route receipts retain ROUTE_COMMAND_BRIDGE_CONFIRMED with runtime
STEER_MAX 409: 917,842 eligible pairs, all exact Float32(raw/409) matches. This
is the logged post-CarController representation, not EPS acknowledgement. The
excluded V2 DEVELOPMENT route contributes no V3 bridge, fit or scoring samples.

Stage A completed 48 fold fits: 3 speed bins × 8 configurations × 2 folds.
All fitted structures were finite/stable in the declared diagnostics. The minimax
selection in every speed bin was ARX1, delay 5 samples (0.05 s publish-time lag).
Every selected structure failed the frozen directional gate. No pooled final refit
was run, no model was admitted and both model maps are empty.

Route A and B below are the canonical lexical two TRAIN IDs in the fold artifact.
V2's excluded DEVELOPMENT route remains context only.

| Fold | TRAIN route | DEVELOPMENT route | LOW common rows | MEDIUM common rows | HIGH common rows |
| --- | --- | --- | ---: | ---: | ---: |
| FOLD_A | A | B | 85,107 | 79,278 | 29,975 |
| FOLD_B | B | A | 27,217 | 146,878 | 80,971 |

Selected-structure one-step errors, in steering-wheel degrees:

| Bin | Fold | Model RMSE | Hold-last RMSE | Model MAE | Hold-last MAE | Model p95 | Hold-last p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LOW | FOLD_A | 0.08321218 | 0.09093535 | 0.04572980 | 0.02734087 | 0.14553594 | 0.10000229 |
| LOW | FOLD_B | 0.08507945 | 0.09416414 | 0.04681200 | 0.03489363 | 0.16016824 | 0.20000000 |
| MEDIUM | FOLD_A | 0.04435164 | 0.04448154 | 0.02680799 | 0.01414516 | 0.09530044 | 0.10000002 |
| MEDIUM | FOLD_B | 0.05507390 | 0.05902179 | 0.02573287 | 0.02032980 | 0.10441637 | 0.10000038 |
| HIGH | FOLD_A | 0.03946768 | 0.04025357 | 0.01792493 | 0.01266722 | 0.09843533 | 0.10000002 |
| HIGH | FOLD_B | 0.03765257 | 0.03865698 | 0.01687065 | 0.01208087 | 0.09697105 | 0.10000000 |

One-step RMSE is lower than hold-last in all six fold/bin comparisons, but MAE
is higher in all six. LOW FOLD_A and MEDIUM FOLD_B also have higher one-step p95.
At 1 s, LOW FOLD_A MAE worsens, and MEDIUM FOLD_A RMSE/MAE/p95 all worsen.
HIGH 1 s endpoints improve directionally in both folds, which does not override
their one-step MAE failures. All eight structures and all four endpoint horizons,
including zero/static comparisons, coverage, bias and correlation, are preserved
in the aggregate CV-results receipt. The three final states are
STAGE_A_CV_TRADEOFF_ONLY, with NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT.

Both yaw folds prefer the supporting +deg/s hypothesis. Kinematic correlations
are approximately 0.986 on both routes. Direct-gyro correspondence remains weak
and contradictory: FOLD_A selects device axis 1 / +sign / lag 0, with route
correlations 0.0272 and 0.0748; FOLD_B selects axis 2 / -sign / lag 10, with
correlations -0.0254 and -0.0183. Neither route passes the conservative association
gate. Although contiguous yaw design support exceeds 201 in all route/bin cells,
it cannot replace provenance/admission. Stage B is
STAGE_B_SIGNAL_ADMISSION_BLOCKED; coefficient fitting, CV and refit are NOT_RUN.

The future holdout package is CLOSED_MISSING_ADMISSIBLE_MODEL, with one-time
opening CLOSED and FUTURE_UNTOUCHED_HOLDOUT_REQUIRED. This is retrospective
development evidence, not an independent test or a physical dynamics validation.

## Validation method and actual results

Two complete V3 executions matched exact coefficients, private array bytes, predictions,
metrics, selections, result SHA and package SHA. V2 private store hashes before and
after each execution were identical. The private policy was persisted before fitting;
its receipt is 5c47b1a833dad3803f94e822ff9a45f1b0c6bfd6ea6b75299375415a6085f5f8.
Commands: python tools/test_runner.py openpilot/tools/cyber_autotune/tests -j1;
python tools/test_runner.py openpilot/selfdrive/controls/tests -j1;
unittest discovery test_empirical*.py; the two lateral card/native replay unittest
modules; Ruff check across AutoTune/Cyber controls; compileall; scons -j2;
check_publication.py --base origin/main; git diff --cached --check. All exited 0
in the prepared Ubuntu 24.04 Python 3.12 environment. Aggregate JSON receipts
carry policies, fold metrics, support and hashes.
Private model coefficients are never published.

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression / build | focused tests; full AutoTune and controls; Ruff; compileall; SCons | V3 code and pinned inputs | New focused 50 PASS; empirical focused 512 PASS; controls 142 PASS; Ruff, syntax and SCons PASS; full AutoTune 2,881 PASS (925.70 s) |
| Replay vs baseline | existing lateral native/card replay tests | existing fixtures | 16 PASS; no empirical candidate execution |
| Simulation / closed loop | Not run | Outside authorization | No TA/SG execution or Stage C rollout |
| Shadow (candidate cannot actuate) | Not run | Offline model development only | No vehicle/device authority |

Independent pre-execution and final artifact reviews PASS. Review regressions cover
missing horizons/references, nonfinite references, absent selection/refit handling,
V2 result-to-route cache authentication, and private Windows/UNC path rejection.
Publication checker: 1,063 files, zero findings. All 18 changed files are additive
text files, with no LFS objects or production/submodule changes.

## Handoff

Future holdout must have a new distinct logger-start identity, complete lineage,
numeric payload previously unopened, role assigned before inspection, compatible
audited source/profile and required signals, and no prior analysis use. The old
zero-support route cannot become holdout. A future current-carrot source needs
its own exact source/profile admission, never automatic equivalence.

All holdout packages remain CLOSED; no refit, reselection, threshold/family change
after opening. Stage C is STAGE_C_PENDING_FUTURE_HOLDOUT and NOT_RUN. TA-B remains
TA_STANDALONE_TRADEOFF_ONLY, SG-A remains SG_CLOSED_LOOP_TRADEOFF_ONLY. Composition
remains NOT_RECOMMENDED / NOT_AUTHORIZED; candidate search and frozen evaluation
remain unauthorized. CURRENT=BASELINE_EXACT, V1=TRADEOFF_ONLY, V2=REJECTED with 37
historical violations.

CALIBRATION_UNCERTAINTY_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE and
INDEPENDENT_REFERENCE_UNAVAILABLE remain unchanged. Sealed reference is
NOT_GENERATED. Vehicle remains NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED.
