# S2-RI read-only failure attribution V2

## 쉽게 보는 결과

기존 32개 candidate/fold job은 큰 오차를 줄여 RMSE를 개선했지만,
움직이지 않은 관측값에도 작은 변화량을 예측해 MAE와 정확한 grid 일치를
악화시켰다. 평가 anchor의 85.23–85.90%가 STATIC이었다.
32개 job 모두 MOVE의 SSE는 감소하고 STATIC의 SAE와 exact-hit는 악화됐다.

다만 rollout의 p95 실패를 STATIC false motion 하나로 설명할 수는 없다.
25-step에서 PATH_FLAT의 p95는 candidate와 HOLD_LAST 모두 0이었지만,
PATH_MOVED의 p95는 29/32 job에서 악화됐다. 긴 horizon에서는 이동 경로의
SSE가 악화되는 job도 늘었다. 두 현상은 별도로 보아야 한다.

따라서 결과는 ZERO_STATIC_TRANSITION_TRADEOFF_STRICT이며,
사전 정의된 HURDLE_FAMILY_DESIGN_REVIEW_SUPPORTED 조건을 충족한다.
이는 별도 설계 검토를 뒷받침한다는 뜻이다. Hurdle 구현·학습·threshold
선택을 승인하거나 기존 candidate를 다시 admit한 것이 아니다.

## Identity and purpose

Cyber Validation, additive read-only interpretation of the 32 historical fold
jobs. Baseline is 1134ca43dd9979048108647898d8cafaa628678d on
feature/cyber-autotune in
[CyberPilot](https://github.com/rownlvh8875-coder/CyberPilot).
No production integration or vehicle applicability is introduced.

The original fit/CV verdict remains S2_RI_NO_ADMISSIBLE_CANDIDATE /
MODEL_SELECTION_FAILED_CLOSED. The earlier 7f94a485b insufficient-input
audit remains correct for its then-available inputs. V2 uses the separately
authorized reconstructed evidence and never rewrites that historical audit.

## Original references and lineage

- Original fit manifest:
  9466e4578842b4c8a300bb843338e53b42a2fc75200879360f8212c7c2605c97.
- Reconstruction manifest:
  5452d24a4d72ee8680d3b98048c1095113ab934e9bf132f2b91740a0d3baa178.
- Reconstruction repeatability/resume:
  aa47bac5a33e7c8add13c26c3b75ac638e4c9058b0b030d3c971512b4eb2cc95.
- Exact reconstruction readiness/equivalence/completeness/schema files and
  original public gate receipts are SHA pinned in the new policy.
- No numeric input comes from the original fit store, causal/derived source,
  raw rlog, qlog, or HOLDOUT. Model/normalizer lineage is an opaque receipt
  reference carried by reconstruction metadata.
- Existing local policy/storage helpers retain repository licensing and
  attribution. No external source code, dependency or submodule change.

Call path: pinned reconstruction metadata → whole-file hash validation →
read-only mmap of one population → pure attribution functions →
new private masks/receipts → closed aggregate publication. No fitting,
prediction, replay, rollout generator or selector is part of this path.

## Implementation and frozen definitions

empirical_s2_ri_attribution_v2.py performs admission, execution traps,
immutable persistence and resume. The math module computes descriptions from
stored values. The publication module permits only declared aggregates and
hashes. A separate JSON-only layout module compacts oversized documents and
splits context aggregates into two fold shards under a SHA-bound index. It
reconstructs the original 32-job aggregate exactly and preserves the existing
publication scanner limit. It is outside the frozen numerical executor.
All are new modules; historical modules/artifacts/stores are unchanged.

The 16 candidate IDs retain historical lexical order, each FOLD_A then FOLD_B.
There are exactly 32 one-step and 128 rollout populations. All rows stay in
their original route → segment SHA → aligned-anchor order.

STATIC/MOVE use exact target delta zero/nonzero; signed and one-tick/multi-tick
classes are fixed. Confusion compares projected next tick with current tick.
Errors come from stored canonical candidate/comparator buffers. No target
recovery from errors and no regeneration of predictions occurs.

Metrics use contiguous float64, NumPy 2.5.3 and linear percentile p95.
SAE/SSE reductions preserve anchor order within each class. Counts partition
exactly. Both direct-all and partition-sum floating reduction differences
are reported; no tolerance gate is invented. p95 is never added across classes.

Paths are read in fixed chunks of 512 anchors. PATH_FLAT means every observed
tick equals the initial tick. Endpoint classes are zero, one, or multiple ticks.
First divergence and first false move use steps 1..H, with 0 privately denoting
no event. Reversals compare successive nonzero increments, ignoring intervening
zero increments. p95 tail membership includes ties (abs(error) >= p95).

Error units are source-grid ticks; one tick is 0.1 measured steering-wheel degree.
SSE uses squared ticks. These are not physical steering-rate or EPS torque
measurements. Command summaries describe logged normalized command only.

## One-step evidence

Historical starting observations are preserved: RMSE failures 0/32, MAE
failures 32/32, exact-hit failures 32/32, p95 failures 27/32, and rollout-25 p95
failures 32/32. No gate is rerun or relaxed.

All ranges below describe the 32 candidate/fold populations, not unique driving
rows and not a candidate ranking. Different histories have different anchors.

- STATIC fraction: **85.2338–85.9034%**.
- STATIC projected false-move fraction: **3.1103–8.5389%**.
- STATIC ΔSAE: **+15,864.64 to +40,060.52**; ΔSSE:
  **+6,124.37 to +18,236.61**.
- MOVE ΔSAE: **−18,847.05 to −4,932.22**; ΔSSE:
  **−103,096.79 to −20,826.02**.
- MOVE missed-motion fraction: **63.2828–79.8602%**.
- Sign accuracy among detected MOVE rows: **57.9237–98.3914%**.

STATIC HOLD_LAST behavior is verified directly from stored ticks and errors:
zero error, exact hit, and within-one-tick for every STATIC anchor.
Its values are not supplied from a theoretical assumption.

| One-step class | Jobs with SSE improvement | Jobs with SAE improvement | Jobs with p95 regression |
| --- | ---: | ---: | ---: |
| STATIC | 0 | 0 | 32 |
| MOVE | 32 | 32 | 0 |
| ONE_TICK_MOVE | 27 | 32 | 32 |
| MULTI_TICK_MOVE | 32 | 32 | 0 |
| MOVE_POSITIVE | 32 | 32 | 1 |
| MOVE_NEGATIVE | 32 | 32 | 1 |

Thus MOVE improvements coexist with STATIC regressions. One-tick p95 also
regresses in every job, even where its mean absolute error improves.
The full per-job confusion, class metrics, grid-hit rates and SAE/SSE
decompositions are in the JSON artifacts; they are not new admission criteria.

STATIC continuous prediction summaries use absolute delta magnitude.
The exact 0.5-tick split comes only from the frozen half-to-even projection.
There are **zero exact-half STATIC occurrences** across these evaluated job
populations. Synthetic tests cover held/moved parity and adjacent binary64
values without an epsilon. The median is reported once, without treating p50
as a separate piece of evidence.

## Rollout evidence

False motion occurs on flat observed paths in every job/horizon, and missed
motion occurs on moving paths in every job/horizon. These are presence
statements, not dominance claims.

| Horizon, steps | Flat-path SSE regression jobs | Moving-path SSE improvement jobs | Moving-path SSE regression jobs |
| --- | ---: | ---: | ---: |
| 25 | 32 | 25 | 7 |
| 50 | 32 | 18 | 14 |
| 100 | 32 | 17 | 15 |
| 200 | 32 | 7 | 25 |

The flat-path false-motion fraction ranges over jobs are 1.3780–2.8738% at
25 steps, 1.1531–2.5835% at 50, 0.8734–2.2480% at 100, and 0.2700–2.3355% at 200.
These populations differ by horizon; the ranges do not imply a monotonic
within-anchor trajectory.

At 25 steps:

| Stratum | Per-job count range | Candidate p95 range, ticks | HOLD_LAST p95 range, ticks | Jobs with p95 regression |
| --- | ---: | ---: | ---: | ---: |
| PATH_FLAT | 57,028–80,286 | 0–0 | 0–0 | 0 |
| PATH_MOVED | 117,224–187,822 | 16–24 | 15–17 | 29 |
| ENDPOINT_STATIC | 76,341–114,665 | 0–12 | 0–0 | 4 |
| ENDPOINT_ONE_TICK | 30,373–45,194 | 1–24 | 1–1 | 4 |
| ENDPOINT_MULTI_TICK | 67,538–108,249 | 20–27 | 22–27 | 10 |
| PATH_MOVED_ENDPOINT_STATIC | 19,313–34,379 | 0–25 | 0–0 | 7 |

These p95 values are separate stratum descriptions, not additive contributions
to overall p95. Flat false motion contributes nonzero error, but a flat-path
p95 of zero cannot alone explain the overall 25-step p95 failure.

At 25 steps, the tied p95 tail contains 5.0436–5.5256% of anchors.
PATH_FLAT accounts for 177–1,363 tail anchors (1.7964–9.8093% of each tail);
PATH_MOVED accounts for 8,917–13,653 (90.1907–98.2036%).
These are exact descriptive compositions, with no majority/dominance cutoff.
Endpoint-static tail fractions are 4.0350–26.6067%, one-tick fractions
3.7713–24.1022%, and multi-tick fractions 49.2911–91.6812%.

Among anchors with divergence, per-job median first-divergence steps range
4–5, 7–7, 9–10 and 9–11 at horizons 25, 50, 100 and 200.
No-event counts, first-false-move summaries, movement/reversal counts and signed
endpoint error distributions are separately persisted and published as
aggregates. Full original trajectories remain private and are never regenerated.

## Frozen context and grouping

Speed bins reuse the persisted LOW/MEDIUM/HIGH codes. Rail and prior-motion
classes are descriptive only. LOW, MEDIUM, NON_RAIL, PRIOR_STATIC and
PRIOR_MOVING each show STATIC SAE regression and MOVE SSE improvement in all
32 jobs. HIGH shows MOVE SSE improvement in 24 jobs. RAIL shows STATIC SAE
regression in 21 and MOVE SSE improvement in 18; empty or sparse strata remain
explicit rather than receiving invented metrics.

Reversal context requires both prior and target increments nonzero.
Command-current and command-feature-newest magnitudes are aggregate
descriptions of STATIC_FALSE_MOVE rows, not threshold features.

The d and L tables report eight jobs per fixed group, condition counts and
rollout mechanism counts only. No best d/L, candidate ranking, closest-to-pass
candidate, alternative gate, or non-rail admission is computed.

## Mechanism and Hurdle trigger

All 32 jobs satisfy the frozen conjunction:

1. MOVE ΔSSE < 0.
2. STATIC ΔSAE > 0.
3. STATIC candidate exact-hit < STATIC HOLD_LAST exact-hit.

Outcome: ZERO_STATIC_TRANSITION_TRADEOFF_STRICT.
Trigger: HURDLE_FAMILY_DESIGN_REVIEW_SUPPORTED.

This supports a separately authorized Hurdle-family **design review only**.
It does not establish that such a family will solve the rollout effects,
authorize its implementation/fitting, or admit any current candidate.
Closed-loop identification bias and physical EPS application unavailability
remain. One-step and rollout mechanisms are reported on separate axes.

## Regression risk and acceptance

Main risks are unintended model execution, altered anchor populations, unsafe
source loading, incorrect partition/tail semantics, and publication of private
values. Admission requires the exact manifest and all 160 complete populations
before decode. Missing/hash-conflicting input fails closed without fallback.

Solvers, fit/normalizer/predict/recursive/selector APIs, reconstruction/fitting
executors and raw-decoder imports are trapped. NumPy loading is restricted to
exact admitted reconstruction files in read-only mmap mode. Resume verifies
saved output files and root authorization/policy/executor lineage with numeric
loaders and analysis functions trapped.

The output is a new external immutable store: atomic writes, receipt/manifest
last, no overwrite, no source overlap or symlinks. Rollback means ceasing use
of the new analysis; no controller state or historical receipt requires repair.

Independent review identified cached recursive API trapping, root
authorization/policy resume binding, and rollout partition reduction accounting.
All three received regression tests and were fixed before actual V2 analysis.

## Validation method and actual results

- Focused V2 unittest: 57 analysis tests and 5 lossless-layout tests PASS.
- Combined empirical: 1,506 PASS plus 321 subtests; includes reconstruction
  regression and all prior empirical tests.
- Full AutoTune/controls: 4,275 PASS after independent-review fixes. The five
  later JSON-layout tests also pass; exact-HEAD CI runs all 4,280 together.
- Lateral replay: 16 PASS.
- SCons, Ruff, compileall: PASS.
- Two independent full attribution runs, exact comparison and trapped resume:
  manifest 031453a4f78ddeaa5d316cb683ef02a90678377451485909b2da6cd2314fa2cc;
  repeatability receipt
  6a7f6029b0ca05f74e46538821c159d4af7483fb06dceb96bcf0c00891e7eeb2.
- JSON, publication/privacy/authority, diff whitespace and exact-HEAD CI:
  required final gates, recorded separately without preclaiming CI success.
- Browser, new simulation/closed-loop execution, shadow and vehicle testing:
  NOT_APPLICABLE / NOT_AUTHORIZED.

## Handoff and preserved states

The analysis is read-only. MODEL_REFIT_CALLS, NORMALIZER_REFIT_CALLS,
MODEL_REPLAY_CALLS, SELECTION_CALLS, RAW_LOG_OPENINGS, QLOG_OPENINGS and
HOLDOUT_OPENINGS remain zero.

Preserve dataset PARTIAL; NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT;
CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED; original S1/S2 rate-semantics
blocks; S3_SOURCE_MECHANISM_BLOCKED; STAGE_B_SIGNAL_ADMISSION_BLOCKED;
TA_STANDALONE_TRADEOFF_ONLY; SG_CLOSED_LOOP_TRADEOFF_ONLY;
COMPOSITION_NOT_RECOMMENDED; COMPOSITION_NOT_AUTHORIZED;
SEARCH_NOT_AUTHORIZED; FINAL_POOLED_REFIT_NOT_AUTHORIZED.

HOLDOUT_OPENING_CLOSED, opening_count=0 and
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED remain. Calibration uncertainty,
independent calibration validation and pixel geometry registration are pending;
metric calibration and independent reference remain unavailable.
Sealed reference is NOT_GENERATED. Vehicle is NOT_READY /
REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

No Hurdle implementation or fitting begins automatically.
