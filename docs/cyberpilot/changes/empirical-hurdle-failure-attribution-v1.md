# Hurdle failure attribution V1

Hurdle protected error on the samples where the measured angle actually changed,
but all 16 structures failed the overall exact-hit criterion in both folds.
This increment reads the saved evidence to separate a mistaken MOVE gate from a
projection that actually changes the tick. It also separates rollout paths with
gate mistakes from paths whose gate decisions all match the observations.

The analysis is descriptive and retrospective. It does not refit either stage,
choose another threshold, regenerate a prediction, or admit a candidate.

## Identity and purpose

- Area: Cyber Validation / AutoTune; additive read-only failure attribution.
- Baseline: `f5ed849bd27287084efc81ba3dd0275ebfc5ca0a`,
  branch `feature/cyber-autotune`.
- Original repository: <https://github.com/rownlvh8875-coder/CyberPilot>.
- Source private manifest:
  `c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6`.
- Historical repeatability receipt:
  `3b9e8e1f562972268a7a0543f72d3f98fe237a9f3e1c5e045b69e19f9c69949b`.
- Numeric source: the successful compressed repeat-1 only. No source causal
  store, derived store, raw log, qlog, or HOLDOUT is reopened.
- Historical policies, metrics, 32 job receipts, gates and selection are inputs.
  No existing tracked file or private source byte is replaced.
- Vehicle applicability: none; no controller consumer or vehicle authority.

## Original references and call path

The existing Hurdle fit/CV data and math modules define the stored schema and
canonical error primitives. Their fitting, prediction, projection, rollout and
selection entry points are hard trapped during attribution. This implementation
uses Python standard-library IO and the existing pinned NumPy environment.
No external algorithm or new dependency is adopted; repository licensing and
upstream submodule identities remain unchanged.

New CLI → exact public receipt pins and private manifest → per-job metadata →
verified gzip NPY streams → descriptive aggregate reductions → immutable small
JSON receipts → aggregate-only public artifacts. There is no controller hook.

The new modules are `empirical_hurdle_attribution.py`, `_io.py`, `_math.py`,
`_schema.py` and `_publication.py` under `openpilot/tools/cyber_autotune/`.
The focused test file is `tests/test_empirical_hurdle_attribution.py`.
These files are independent of the immutable historical executors.

## Frozen analysis method

STATIC is exactly zero stored actual delta; MOVE is nonzero. Positive/negative
and one-tick/multi-tick classes partition MOVE without a tuned threshold.

Gate confusion uses stored predicted gates. Projected movement separately compares
the stored next tick with the current tick. STATIC is split into TN,
FP-with-projected-hold and FP-with-projected-movement. FN integrated errors must
equal HOLD_LAST bytes. TP diagnostics include continuous and projected sign
accuracy, error sums, and grid-hit metrics.

Exact-hit accounting uses integer counts:
`NET_HIT_DELTA = MOVE_HIT_GAIN - STATIC_HIT_LOSS`.
A job has the requested static-loss mechanism only when static loss exceeds move
gain and the immutable historical exact-hit clause failed.

One-step errors are the stored integrated delta minus actual delta, preserving
the frozen binary64 operation order. Errors are reduced in original anchor order
as contiguous float64 arrays. P95 uses NumPy linear interpolation. SAE and SSE
partition checks prove each row belongs to exactly one class and preserve the
original contribution bytes. Both original-order and partition-order sums and
their exact floating-point residual are reported; no tolerance is introduced.
P95 is not additive.

Stored oracle deltas provide continuous Stage2 diagnostics on true MOVE.
Oracle projected metrics are referenced from the pinned original job aggregate;
no new oracle projection is generated. Oracle-to-integrated SAE/SSE differences
are diagnostic comparisons, not an admission or threshold experiment. Batched
stored oracle and integrated predictions retain their original numerical
semantics; the difference is not presented as a causal intervention.

TRAIN confusion comes from the frozen threshold receipt. DEVELOPMENT uses the
stored probabilities and gates; the single historical strict-greater-than
decision is checked for consistency. No alternate threshold is computed.
Rates and prevalence are compared in each route-transfer direction separately.

## Recursive path analysis

At each horizon, true movement is the difference between consecutive stored
observed ticks. GATE_PERFECT requires every stored gate step to match those
observed transitions. It does not imply that predicted movement magnitudes or
the projected trajectory are correct.

First events use steps 1 through H, with zero meaning no event. The six exhaustive
relations are gate mismatch before divergence, simultaneous events, divergence
before gate mismatch, gate mismatch alone, divergence alone, or neither.
Endpoint errors are checked against the stored original errors and original
overall/PATH_MOVED metrics.

PATH_MOVED means any observed tick differs from the initial tick, including paths
that return to that tick. PATH_FLAT, GATE_PERFECT PATH_MOVED, GATE_ERROR PATH_MOVED,
and first FP/FN classes retain separate descriptive metrics.
Nonempty support below 201 is marked SMALL_SUPPORT_DESCRIPTIVE_ONLY; empty
subsets have null metrics. These metrics never enter a new admission decision.

Horizons 25, 50, 100 and 200 remain separate. Recorded command/vEgo conditioning
and the historical `LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT` interpretation
remain unchanged. No future trajectory is generated here.

## Persistence, repeatability and privacy

All private attribution results are on D. Full paths are streamed in fixed
512-row chunks; only small per-population count/event vectors live in memory.
No source array, full path or per-row prediction is copied into the new store.

Each compressed file is checked against its manifest hash. Decoded NPY and raw
array hashes, dtype, shape and C-order are verified before rows are yielded.
Run/job/population receipts preserve source lineage. Before/after hashing covers
the exact manifest-listed source bytes plus authorization and repeatability
metadata, without claiming identity of unopened raw/qlog/HOLDOUT stores.

Each independent run computes all 32 jobs. Resume validates saved aggregate
schemas, all required horizons, policy/executor/authorization identities and file
hashes with source loaders, decoder and analysis functions trapped.
Partial output is never used to fill another run.

Publication uses an explicit aggregate-key contract, JSON-native types only,
a ban on per-row field names/numeric vectors, and embedded private-path checks.
Threshold values, coefficients, normalizers, probabilities, gates and raw paths
remain private.

## Actual results

All 32 jobs reconcile exactly with the original one-step, oracle, overall rollout
and PATH_MOVED metrics and historical failure counts. STATIC represents
85.2338–85.9034% of each candidate-specific development population.

Every job loses more STATIC exact hits than it gains on MOVE. Thus
`HURDLE_EXACT_HIT_STATIC_LOSS_ALL_JOBS` holds. True-MOVE protection remains
32/32 PASS, and STATIC projected false movement exists in all 32 jobs. The frozen
conjunction yields `STAGE1_GATE_REDESIGN_REVIEW_SUPPORTED`, for design review only.

| Development result, range across 16 structures per fold | FOLD_A | FOLD_B |
|---|---:|---:|
| STATIC exact hits lost | 16,319–47,150 | 1,833–3,767 |
| MOVE exact hits gained | 5,141–8,633 | 898–1,693 |
| Gate false-MOVE rate | 45.5981–55.7334% | 1.87247–3.05936% |
| Gate missed-MOVE rate | 34.4026–42.8373% | 87.9168–92.6023% |
| Balanced accuracy | 0.549320–0.563501 | 0.527626–0.546621 |

These are separate ranges, not matched endpoints or candidate rankings.
Candidate-specific anchor populations overlap and must not be treated as
independent samples when comparing structures.

Gate FP and projected movement differ substantially. In FOLD_A, 83,920–143,280
STATIC rows receive MOVE, but 61,616–96,130 of those rows still project to the
same tick. Projected false movement on STATIC rows occurs on 16,319–47,150 rows. In FOLD_B these
three ranges are 5,406–6,912, 2,044–3,973 and 1,833–3,767 respectively.
A held projection can still have nonzero continuous error; the public
TN/FP-held/FP-moved decomposition preserves that distinction.

On FN rows, stored integrated errors equal HOLD_LAST bytes exactly. On TP rows,
both SAE and SSE improve in all 32 jobs. On all true MOVE rows, integrated SAE
and SSE exceed the stored Stage2 oracle values in all 32 jobs: the differences
range from 1,437.52 to 17,844.94 for SAE and 5,044.69 to 44,359.71 for SSE.
This diagnoses missed access to Stage2 benefit; it does not evaluate another
deployable gate. Integrated one-tick MOVE SAE improves in 32 jobs and SSE in 24;
multi-tick MOVE improves both sums in all 32.

### Frozen-threshold transfer

No threshold number is published or reselected. Each comparison uses its fold's
single historical TRAIN threshold.

| TRAIN → DEVELOPMENT transfer | FOLD_A | FOLD_B |
|---|---:|---:|
| TRAIN predicted-MOVE fraction | 24.1146–42.7422% | 6.58019–10.5260% |
| DEV predicted-MOVE fraction | 47.3857–57.1606% | 2.66337–4.28133% |
| DEV−TRAIN false-MOVE rate | +14.9284 to +28.4284 percentage points | −5.30157 to −3.05322 points |
| DEV−TRAIN missed-MOVE rate | −23.7106 to −11.2589 points | +8.96310 to +12.3039 points |
| DEV−TRAIN balanced accuracy | −0.0241284 to −0.0110918 | −0.0394549 to −0.0289150 |

The direction asymmetry is visible in both confusion and historical rollout
failures. At 25 steps, overall RMSE/MAE/p95 fails in 15/16/16 FOLD_A jobs and
0/7/5 FOLD_B jobs. At 200 steps these counts are 16/16/10 and 5/6/8.
These are descriptive transfer associations, not proof of a single causal source.

### Gate errors and remaining trajectory error

| Horizon | Jobs with GATE_PERFECT PATH_MOVED support | Support range per job | SSE better / worse / equal | p95 nonworse / worse |
|---|---:|---:|---:|---:|
| 25 | 32 | 134–497 | 32 / 0 / 0 | 32 / 0 |
| 50 | 32 | 20–100 | 28 / 4 / 0 | 28 / 4 |
| 100 | 32 | 2–19 | 24 / 5 / 3 | 27 / 5 |
| 200 | 2 | 0–1 | 2 / 0 / 0 | 2 / 0 |

Counts in the last columns cover only nonempty subsets. At 25 steps eight jobs
have support below 201; at 50 and 100 all 32 do. At 200 steps only two jobs have
one such path each; the other 30 have no support and null metrics. The 200-step
result cannot establish that Stage2 dynamics are sound. Regressions at 50 and
100 show that correct gate labels do not guarantee a correct trajectory, with
the stated small-support limitation.

Across job populations, the median first gate-mismatch step ranges from 1–5,
1–7, 1–9 and 1–10 at the four horizons. The corresponding median first projected
divergence ranges are 3–5, 4–7, 6–9 and 7–10. These medians exclude paths without
the respective event. The six exact event-order counts remain separate in the
divergence artifact: a gate mismatch need not immediately move the tick, and a
magnitude error can diverge before any gate mismatch.

Every job contains PATH_FLAT projected false motion at every horizon.
Per-job counts range from 429–9,593 at 25 steps to 14–389 at 200 steps.
Different horizons use different eligible populations, so those counts do not
form a longitudinal accumulation curve. Gate FP/FN and observed/projected
movement-count distributions, first-error-type endpoint metrics, and
gate-perfect/gate-error subsets are published per candidate, fold and horizon.

This is evidence for reviewing Stage1, alongside a separate small-support
residual dynamics observation. It neither ranks candidates nor authorizes
Stage1/Stage2 implementation, threshold changes, or another model fit.

## Validation and receipts

Both complete independent runs produced byte-identical receipts and manifests.
Verify-only resume passed with source loaders, compressed decoding and analysis
functions trapped. Manifest-listed source bytes were unchanged before/after.
The common run manifest is
`07345517d3bca95e90962e0566a58e2b756a8aa6f5c658b8b312f02d4961f77d`.

Repeatability/resume receipt:
`aab7ec583b7ae4c9cb6b568293f5d29be5edee8a213889176cffd809f7b91ea3`.

Two earlier development attempts were invalidated after independent review
strengthened saved-result completeness and publication checks. No partial
outputs were reused. The accepted evidence comes from two fresh full runs
of the final executor. Independent review also rejected all 1,696 required-field
deletion mutations across saved job, summary and readiness schemas.

Validation completed: 50 focused tests (114 subtests), 1,628 combined empirical
tests (564 subtests), 4,487 AutoTune/controls tests and 16 lateral replay tests.
Ruff, compileall, SCons, strict JSON/receipt verification, publication/privacy/
authority checks and git whitespace checks passed. The empirical/full suites
include Hurdle fitting/design/policy and S2-RI historical regressions.
The only final test-fixture edit replaced synthetic private-looking path literals;
the focused suite was rerun and the execution code/evidence remained unchanged.

Independent review checked the implementation, all aggregate figures in this
document, and all 14 publication payloads. No finding remains open. Private
attribution output is 3.54 MB, with no copied source arrays or paths. The public
bundle is about 2.03 MB of aggregate JSON. All refit, threshold reselection,
model replay, selection, raw-log, qlog, causal-source and HOLDOUT calls are zero.
Post-push exact-HEAD CI is checked separately; no future CI result is asserted
by this pre-commit receipt.


## Regression risk and authority

Risks are misclassified path events, conflating gate MOVE with projected movement,
floating reduction-order mistakes, incomplete resume, and private-data exposure.
Hand-checked synthetic examples, mutation tests, historical metric reconciliation,
source hashes, independent repeatability and independent review address these.

The exact-hit mechanism state is all-jobs only for the specified 32/32 conjunction.
Stage1 redesign review is supported only if true-MOVE protection passed in all jobs,
exact-hit failed in all jobs, static loss exceeded move gain in all jobs, and all
jobs contain STATIC projected false movement. The trigger grants design review
only, not implementation or fitting. No automatic Stage2 trigger is created.

`HURDLE_NO_ADMISSIBLE_CANDIDATE`, `MODEL_SELECTION_FAILED_CLOSED`, and
`FROZEN_HURDLE_RI_V1_FAILED_RETROSPECTIVE_GATE` remain authoritative.
S2-RI historical results and all calibration, rate-semantics, TA/SG, composition
and source-mechanism blockers remain unchanged. HOLDOUT is CLOSED with zero
openings; future untouched HOLDOUT remains required. Pooled refit is unauthorized.
Vehicle remains NOT_READY, REAL_VEHICLE_UNVERIFIED and VEHICLE_ACTIVATION_BLOCKED.

Browser, simulation, shadow execution and vehicle deployment are not applicable
to this read-only increment. Rollback is removal of this additive implementation
and its new publication only; historical evidence is untouched.
