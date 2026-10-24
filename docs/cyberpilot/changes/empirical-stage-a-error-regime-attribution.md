# Empirical Stage A error regime attribution

## Identity and purpose

Cyber Validation / AutoTune; implemented and independently reviewed aggregate attribution; local required checks passed.
Baseline branch feature/cyber-autotune, commit 9d887fc8a1233c16e545e434974faa7a7da314b2.
Increment: EMPIRICAL_STAGE_A_ERROR_REGIME_ATTRIBUTION_V1.

The frozen V3 selected ARX1/delay5 structures lower one-step RMSE in both old routes
and all three speed bins while increasing MAE. This increment explains that tradeoff
using only their preserved DEVELOPMENT target/prediction/design derivatives.
It does not refit, rescore the other seven configurations, reopen raw logs or admit a model.
V1/V2/V3 results, source audit, TA-B/SG-A and reference evidence remain immutable.

Final attribution: **STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED**.
Quantized unchanged observations dominate MAE cost. Both one-quantum and multi-quantum
transitions provide MSE benefit. The frozen stronger multi-quantum dominance witness
does not hold in every route/bin. The available causal half-quantum condition fails
consistent separation; the other requested causal fields are unavailable.

## Original references

- Source repository https://github.com/ajouatom/openpilot, exact recorded commit
  18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29; recorded source branch identity remains
  bound by the existing source audit, with no branch-name substitution.
- Exact DBC: opendbc_repo/opendbc/dbc/hyundai_kia_generic.dbc,
  SHA256 1590039abb51cbfc3dc8ab4151ab78e7f549088fec878480ab4d6f850b18898a.
- CarState: opendbc_repo/opendbc/car/hyundai/carstate.py,
  SHA256 018ba9c239f8ab378de26354e3dd9c7eafe40ac513be1213d38f59a4c3a9e374.
- Schema: opendbc_repo/opendbc/car/car.capnp,
  SHA256 db5444005dcff5fdbbecf617ea031eb90852e51a848a9d832a02756ddc6bc024.
- Recorded license blob SHA256
  716ce815a0467219c59ec2433e6bce7f32efc45240725c6d3141a52b111d2558;
  retain upstream MIT attribution. Source definitions are audited, not integrated into production.
- Source path: SAS11.SAS_Angle → legacy CarState direct copy → steeringAngleDeg @7 Float32
  → preserved V3 latest-past aligned targets. Current CANFD/angle paths are not substituted.
- Existing submodule gitlinks remain unchanged. NumPy is the existing numerical dependency;
  no solver or RNG is used in this increment.

## Changes and expected effect

New empirical_stage_a_regime.py implements pure paired accounting, outcome partitions,
causal-field availability, equal-route summaries and nonexecuting contract schemas.
New empirical_stage_a_attribution.py binds recorded source, freezes a private policy,
reads only six selected derivative pairs, verifies receipt/hash/support identity,
persists private derived rows atomically and publishes aggregates.
New empirical_stage_a_publication.py pins the six public receipts without private dependencies.
New synthetic/publication tests exercise privacy, leakage, reconstruction, repeatability and
immutable history. No upstream integration point, UI or runtime controller hook is added.

The source defines SAS_Angle as signed little-endian 16-bit, start bit 0, factor
0.1 degrees, offset 0, range -3276.8 to 3276.7 degrees. CarState copies it without
sign/scale/offset conversion on the admitted legacy path; schema storage is Float32.
These are source facts, not a value-distribution estimate. No physical sensor accuracy
or unquantized rack-angle truth is inferred. Unchanged aligned targets can also reflect
physical steady steering, publisher repetition or latest-past resampling. These derivatives
cannot causally separate those mechanisms; the result establishes an observation/error
pattern, not proof that hardware quantization alone caused the model regression.

Grid diagnostics compare the untouched target against a source-defined nearest grid
and Float32 representation. Tolerance is exact Float32 grid equality or half adjacent
Float32 ULP; it is not fitted to errors. Nearest grid indices label posthoc transitions
only; targets and ARX predictions are never replaced or rounded.

There is no new dynamic state, reset or physical delay. Every derivative row remains
within existing V3 support. Preserved arrays concatenate valid runs without boundary
indices: adjacent rows cannot supply a safe current-command delta or measured-angle
history. Those fields and current source steering rate/intervention state stay null/
UNAVAILABLE. No V2 numeric cache is opened to fill them.

## Regression risk and acceptance

Risks are target leakage, undocumented quantization tolerance, nonadditive RMSE
attribution, hidden sample weighting and unsupported causal assertions. The policy
was persisted before numerical attribution; its source and executor hashes are checked
on restart. V3 private-tree byte identities match before/after both executions.
Private stores must be outside the repository and disjoint; aliases are rejected.

No performance threshold, optimized command/rate boundary, recent-window selection,
condition combination or model selection is allowed. The inherited 201-row minimum
is retained for causal branch support and the frozen transition-dominance witness.
Outcome regimes cannot authorize a selector. All raw/controller/vehicle authority stays false.

Rollback removes only this additive attribution increment; immutable previous evidence
remains the baseline. Independent reviewer checks source, contribution math, causal
availability, publication and holdout closure. No vehicle promotion is authorized.

## Source grid and route/fold outcomes

449,426 paired targets: all 449,426 are Float32-tolerant source-grid compliant,
zero off-grid targets. All 449,426 continuous ARX predictions are off-grid by the same
diagnostic. Exact decimal-grid counts and residual median/p95/max are disclosed separately
in the quantization artifact; Float32 decimal rounding is not a source conflict.

Report order is route → fold → speed bin; prefixes here are display abbreviations only,
and complete opaque IDs are bound in the policy.

| Route | Fold | Speed | Paired N | Unchanged | One quantum | Multi quantum |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 7ae11bd9… | FOLD_B | HIGH | 80971 | 89.267% | 9.465% | 1.268% |
| 7ae11bd9… | FOLD_B | LOW | 27217 | 77.613% | 15.788% | 6.599% |
| 7ae11bd9… | FOLD_B | MEDIUM | 146878 | 84.468% | 12.157% | 3.375% |
| 962f2448… | FOLD_A | HIGH | 29975 | 88.897% | 9.735% | 1.368% |
| 962f2448… | FOLD_A | LOW | 85107 | 82.583% | 12.473% | 4.944% |
| 962f2448… | FOLD_A | MEDIUM | 79278 | 88.154% | 9.904% | 1.941% |

Outcome partitions use future target only for explanation. Sign reversal is a separate
overlapping diagnostic; large transition explicitly equals at least two source quanta.
Overlapping groups are never summed as if they were partitions.

## MAE and MSE contribution

Each contribution is the regime's summed ARX-minus-hold-last error divided by global
paired N within that route/bin. RMSE contributions divide MSE contributions by the
sum of the two global RMSE values; the exact zero-denominator case contributes zero.
Thus partition contributions reconstruct the global metric difference without
mislabeling a subgroup RMSE difference as additive. No epsilon is selected.

| Scope | Unchanged MAE contribution (deg) | One-quantum MSE contribution (deg²) | Multi-quantum MSE contribution (deg²) |
| --- | ---: | ---: | ---: |
| FOLD_A LOW | 0.025502338 | -0.000284759 | -0.002814965 |
| FOLD_B LOW | 0.019362842 | -0.000572510 | -0.001919539 |
| FOLD_A MEDIUM | 0.014876658 | -0.000252611 | -0.000194828 |
| FOLD_B MEDIUM | 0.007454684 | -0.000226455 | -0.000351106 |
| FOLD_A HIGH | 0.005850124 | -0.000089433 | -0.000035559 |
| FOLD_B HIGH | 0.005412062 | -0.000095882 | -0.000035092 |

In all six scopes hold-last is exactly correct on unchanged targets; ARX creates small
continuous errors. These dominate the positive MAE contribution; errors below half
the source quantum contribute more than the other unchanged-sample errors.
H1 is supported. ARX lowers MAE and RMSE in the transition partitions, although
one-quantum p95 worsens in all six scopes and multi-quantum p95 worsens in two.

The policy's H2 witness is deliberately stronger than merely finding benefit on changed
targets: multi-quantum negative MSE contribution must exceed other negative partition
contributions in every route/bin. It fails MEDIUM FOLD_A and both HIGH scopes, where
one-quantum benefit is larger. Thus the results do not support attributing RMSE benefit
exclusively to sparse >one-quantum tails. This failed witness is not repaired after results.

Primary interpretation uses equal-route arithmetic means separately per speed bin.
Sample-weighted summaries are supporting only. Mean route p95 is explicitly not a
pooled p95; average route RMSE difference is not pooled RMSE.

| Speed | Equal-route unchanged fraction | ARX−hold MAE (deg) | ARX−hold MSE (deg²) | Mean route RMSE difference (deg) |
| --- | ---: | ---: | ---: | ---: |
| LOW | 80.098% | 0.015153647 | -0.001486671 | -0.008403926 |
| MEDIUM | 86.311% | 0.009032947 | -0.000230988 | -0.002038894 |
| HIGH | 89.082% | 0.005023745 | -0.000069649 | -0.000895149 |

## Outcome versus causal separation

A through E (current raw-command change/reversal, normalized command change, current
measured-angle change, current source steering-rate zero/nonzero) cannot be recovered
safely from the V3 selected derivatives. Their availability is UNAVAILABLE, with no
fabricated false/zero values and no cross-run adjacent-row inference.

F uses only frozen ARX prediction minus its preserved past measurement, compared
against source half quantum 0.05 degrees. The future target does not enter this label.
Its movement-at-least-half branch has N 18,424 / 4,785 (LOW),
3,393 / 1,500 (MEDIUM), and 0 / 0 (HIGH), for FOLD_A / FOLD_B.
MAE worsens in three supported large-movement scopes and improves only MEDIUM FOLD_B;
HIGH provides no large-movement support. H3 fails; no causal hybrid review is admitted.

H4 remains unresolved because missing causal fields cannot prove only a noncausal
separator exists. H5 is not established: quantization-related steady cost is supported.
H6's frozen narrow contribution-direction check finds no sign contradiction in unchanged
MAE versus multi-quantum MSE; it does not assert that all p95 metrics or causal conditions
are consistent. Counts/support and contrary p95/causal evidence remain visible.

## Architecture readiness and family status

The frozen quantization-aware review rule requires both H1 and the stronger H2 witness;
only H1 passes. No V4 architecture artifact is generated. No rounding rule, half-LSB
hold rule, latent update, hybrid switch, parameter or algorithm is selected.

The available evidence explains a substantial part of the tradeoff, but cannot establish
a route/speed-consistent causal separator. Missing causal inputs prevent declaring that
no separator exists or that this family must be permanently closed. The result remains
STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED and NO_ADMISSIBLE_MODEL_REVIEW_ONLY.
No fitted model is admitted; existing V3 CV verdicts are unchanged.

## Future holdout and preserved tracks

CLOSED_MISSING_ADMISSIBLE_MODEL, NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT,
FUTURE_UNTOUCHED_HOLDOUT_REQUIRED and HOLDOUT_OPENING_CLOSED remain.
Stage B remains STAGE_B_SIGNAL_ADMISSION_BLOCKED; yaw/gyro were not reanalyzed.
TA-B remains TA_STANDALONE_TRADEOFF_ONLY; SG-A remains SG_CLOSED_LOOP_TRADEOFF_ONLY.
Composition remains NOT_RECOMMENDED and NOT_AUTHORIZED. Candidate search and frozen
candidate evaluation remain NOT_AUTHORIZED.

CALIBRATION_UNCERTAINTY_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE and
INDEPENDENT_REFERENCE_UNAVAILABLE remain. Sealed reference NOT_GENERATED;
vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

## Validation method and actual results

Policy receipt: 0cb9cfa6c281f3ba034397790a33ea5742f06ccc0304dc6d495b817ccc8456f4
Result receipt: 13ef725672a3baaf9118442530652f4b4de9e393db74eba03b6c9bb732a25a9a
Two complete deterministic executions matched regime assignments, private paired bytes,
counts, metrics, contribution decompositions, causal audit, verdict and receipt SHA.
No raw route/log was reopened; no refit, model selection or holdout opening occurred.

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression / build | focused tests, full AutoTune, controls, Ruff, syntax, publication, SCons | single-thread NumPy; frozen policy above | new focused 79 / combined empirical 591 / full AutoTune 2960 / controls 142 passed; Ruff, syntax, publication (0 findings), privacy/authority, diff and SCons passed; independent review PASS |
| Replay vs baseline | two lateral process-replay unittest modules | existing references unchanged | 16 passed; no reference update |
| Simulation / closed loop | no candidate or plant simulation | attribution of immutable V3 arrays only | NOT_RUN, unauthorized |
| Shadow (candidate cannot actuate) | no device or controller integration | authority firewall all false | NOT_RUN, unauthorized |

## Handoff

The completed attribution explains unchanged-observation MAE cost and transition MSE
benefit without changing historical results. A causal selector and nonexecuting V4 review
remain unsupported under this frozen policy. Future work needs separate authorization
and preserved causal context; current attribution cannot open a holdout or admit a model.
Private paired derivatives remain outside Git; only aggregate evidence and hashes are published.
Commit/CI identity is recorded in delivery evidence after validation. Vehicle use is not authorized.
