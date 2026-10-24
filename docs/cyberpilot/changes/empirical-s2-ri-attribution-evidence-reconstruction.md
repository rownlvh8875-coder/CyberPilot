# S2-RI attribution evidence reconstruction

## Identity and purpose

Cyber Validation, additive evidence reconstruction on feature/cyber-autotune,
baseline 7f94a485bca02b4974b7ea0442d14602df22846a. Implemented and locally validated. Exact-HEAD CI is recorded on the published commit.

The historical attribution audit reported ATTRIBUTION_INPUT_INSUFFICIENT:
one-step storage lacked explicit current tick, target tick and context, and
rollout storage retained endpoints/errors without observed or projected paths.
That audit remains an immutable, correct statement about its input store.

This separately authorized increment replays existing fold models to complete
evidence. It does not fit models, refit normalizers, select candidates, or perform
failure attribution. Hurdle hypotheses and triggers are not evaluated.

## Original references

Source: https://github.com/rownlvh8875-coder/CyberPilot, exact baseline above.
The a50d fit manifest is
9466e4578842b4c8a300bb843338e53b42a2fc75200879360f8212c7c2605c97.
The frozen fitting policy receipt is
05cf63752587105d188bff2f81baec32e8192a689cbf09543caf1f954656ac96.

The independent replay modules reuse pure helpers from
empirical_s2_ri_fit_cv_math.py: anchors, features, transform, prediction,
projection and metrics. The old execution entrypoint is blocked. Coefficients
and normalizers are loaded without transformation or reordering from their
original model/normalizer receipts. These remain empirical predictive parameters; physical EPS application is unavailable.
No new dependency, submodule or upstream production change is introduced. Repository licensing and attribution remain.

Flow: sealed public/private metadata → separate replay authorization → exact
rlog derived identities and bound command/speed arrays → original anchor
identity verification → frozen transform and coefficients → new immutable
evidence → byte comparisons against old buffers → aggregate publication.

## Changes and expected effect

New reconstruction math, execution/persistence and publication modules preserve
the 16 candidates, two inverted route folds, feature order and all policies.
Every job verifies one-step and four rollout anchor SHAs before predicting.
The fixed execution order is lexical candidate, FOLD_A, FOLD_B.

The canonical continuous error remains predicted delta minus observed delta,
as previously clarified by the user. One-step prediction, projected tick,
candidate error and comparator error must match the original dtype, shape,
C order and bytes. Reconstructed metrics are compared only for replay
equivalence; historical gate results remain authoritative and selection is
never called.

Private buffer names retain the historical convention: one-step prediction is
predicted_delta_tick_continuous, projected is projected_next_tick, error is the
canonical continuous delta error, and comparator_error is its hold-last
counterpart. New current_tick, target_next_tick and actual_delta_tick fields
are explicit. In rollout populations, projected means the endpoint; the new
projected_path and observed_path fields contain every tick including step zero.

Recursive replay preserves historical 512-anchor chunks and direct binary64
half-to-even integer-tick projection. Feedback consists exclusively of projected
ticks and their differences. Only initial measured history enters recursive
state. Future recorded normalized commands and vEgo form the
LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT. Future measured angles are copied
separately into observed paths, never used as recursive features.

Full observed/projected/hold-last paths have H+1 columns for H=25,50,100,200,
including the initial tick. Observed current/target/path ticks come directly
from the immutable derived angle_tick arrays; no error inversion, interpolation
or padding is permitted. Original endpoint, candidate error, comparator error
and metrics must match exactly.

Attribution-only context includes opaque route/segment identity, anchor order,
speed and frozen speed bin, rail flag, previous measured tick increment,
normalized command history, S2-RI run and within-run index, and model eligibility.
Added context does not change prediction. Neither steeringRate nor controller
request is read or used. Qlog/raw-log access is blocked.

Private storage is external, absolute, non-overlapping with source stores and
raw roots, and rejects symlink components and traversal. Array writes are
atomic and do not overwrite conflicting bytes. Population receipts, job
manifests and run manifests commit last. Exact resume validates saved evidence
without source/model array loading, projection or prediction.

## Regression risk and acceptance

The main risks are floating-point operation-order changes, anchor drift,
future observed-state leakage, stale source lineage, and accidental publication
of private numeric arrays. Acceptance requires all 32 jobs, exact old-buffer
equality, complete paths/context, two independent byte-identical runs and
trapped verify-only resume. No tolerance or acceptance-gate relaxation exists.

Public outputs contain counts, dimensions, availability, opaque hashes and
equality states only. Coefficients, normalizer statistics, targets, predictions,
paths, timestamps, local paths and per-anchor identities remain private.

Input immutability checks cover the exact original fit manifest and frozen
causal/derived file pins before and after replay. Unopened raw/qlog historical
stores receive no byte-identity claim. Existing historical tracked artifacts
are unchanged. New evidence can be ignored without modifying any prior result.

## Validation method and actual results

| Check | Method | Result |
| --- | --- | --- |
| Focused replay | Synthetic frozen coefficients, all candidate forms, rate overlays, no-refit traps, direct targets, paths, persistence/resume | 64 passed |
| Empirical replay | Two full 32-job executions, original byte and metric equality | PASS: 32/32 jobs in each run; identical run manifest |
| Resume | Source/coefficient loader and predict/project/recursion traps | PASS: same manifest without recomputation |
| Regression/build | Full AutoTune + controls: 4160; combined empirical: 1444 + 321 subtests; lateral replay: 16; Ruff, syntax, SCons | PASS; final receipt records JSON and publication checks |
| Independent review | Fresh reviewer; two P1 resume/publication findings reproduced with five RED tests, then fixed | PASS; header/payload hashes and typed bindings verified |
| Browser | No UI changed | NOT_APPLICABLE |
| Vehicle simulation/shadow/road | No controller execution or vehicle authority | NOT_AUTHORIZED |

Run manifest (both independent executions):
5452d24a4d72ee8680d3b98048c1095113ab934e9bf132f2b91740a0d3baa178.
Repeatability/resume receipt:
aa47bac5a33e7c8add13c26c3b75ac638e4c9058b0b030d3c971512b4eb2cc95.
Each run contains 32 one-step and 128 rollout populations and 3,777 files.
Full observed/projected/hold-last paths, context arrays and all receipt bytes
match across runs. Original fit input and bound causal/derived file hashes
remain unchanged. Review corrections were completed before either real run.

The final focused suite additionally checks every intermediate projected tick
of nonconstant synthetic trajectories for all four horizons. This test-only
extension does not change the replay executor or frozen policy.

## Handoff

The historical S2_RI_NO_ADMISSIBLE_CANDIDATE,
MODEL_SELECTION_FAILED_CLOSED and
FROZEN_S2_RI_LINEAR_FAMILY_FAILED_RETROSPECTIVE_DIRECTIONAL_GATE verdicts remain.
The underlying dataset remains PARTIAL. S1, historical S2, S3 and Stage B remain
blocked; prior ARX1/FIR25 observation track remains closed. TA-B and SG-A retain
tradeoff-only verdicts; composition and search remain unauthorized.

Calibration/reference blockers remain: calibration uncertainty, independent
calibration validation and pixel registration pending; metric calibration and
independent reference unavailable. Sealed reference is NOT_GENERATED.

A successful replay prepares FAILURE_ATTRIBUTION_V2_INPUT_READY only. Failure
attribution itself remains NOT_RUN, Hurdle trigger NOT_EVALUATED, pooled refit
NOT_AUTHORIZED. The next possible increment requires separate authorization
for read-only V2 attribution. HOLDOUT remains CLOSED with opening_count=0.
No model is admitted for future HOLDOUT; untouched future HOLDOUT is required.
Vehicle remains NOT_READY, REAL_VEHICLE_UNVERIFIED and
VEHICLE_ACTIVATION_BLOCKED, with no production or vehicle authority.
