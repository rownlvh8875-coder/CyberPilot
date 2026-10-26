# Fixed source-grid observation diagnostic

## Identity and purpose

Cyber Validation / AutoTune: **FIXED_SOURCE_GRID_OBSERVATION_DIAGNOSTIC_ONLY**,
implemented and executed twice. Baseline 47f18dd0499c5230523b39b0191caf75305000ad
on feature/cyber-autotune. This additive one-step diagnostic tests whether
source-grid observation emission resolves the selected continuous ARX tradeoff.
It grants no model, controller, reference or vehicle authority.

Earlier causal recovery proved 449,426 row origins but found no global
single-condition separator. Its CAUSAL_CONTEXT_RECOVERED_PARTIAL verdict and
prior attribution STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED remain historical.
V3 remains STAGE_A_CV_TRADEOFF_ONLY. Existing files are unchanged.

## Original references

Exact recorded source: [ajouatom/openpilot](https://github.com/ajouatom/openpilot),
commit 18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29. Existing receipts bind
opendbc_repo/opendbc/dbc/hyundai_kia_generic.dbc SAS11.SAS_Angle,
Hyundai CarState direct assignment and car.capnp Float32 storage. DBC SHA:
1590039abb51cbfc3dc8ab4151ab78e7f549088fec878480ab4d6f850b18898a.
Source slices, profile, class and license SHA are repeated in the new policy.
Reuse existing source facts; no new source adaptation or dependencies.
Current submodule pins remain unchanged.

Call path: persisted policy → selected V3 one-step/design arrays →
existing exact recovered origin receipt/array hash → fixed emission →
three-arm same-support metrics → aggregate publication. No production caller.

## Changes and expected effect

New empirical_grid_analysis.py owns stateless projection and paired metrics;
empirical_grid_emission.py owns freeze, immutable private derivatives and two-run
raw-reader firewall; empirical_grid_publication.py checks public/historical pins.
Three test modules and four versioned JSON artifacts are added. No UI.

### Source grid and fixed rule

SAS11 signed 16-bit code range = -32768…32767; step = 0.1 steering-wheel degree;
offset = 0°; decoded range = -3276.8…3276.7°. Fixed emission:

    q = float64(existing_prediction) / float64(0.1)
    n = round_half_to_even(q)
    emitted = Float32(float64(n) * float64(0.1))

Ties are exact fractional-half of the **binary64 quotient**, without epsilon.
For example .15/.1 is slightly below 1.5 in binary64 and is not a tie.
This convention was frozen before array deserialization. Alternative rounding,
hysteresis, learned quantizers and rule search are forbidden. Out-of-range codes
fail without clipping. An exhaustive synthetic test round trips all 65,536
source codes.

No latent state or recursion is implemented. Existing continuous predictions
and coefficients remain unchanged. Emitted arrays are Float32; metrics subtract
in Float64. Targets are audited, never rounded. Existing source Float32 grid
representation tolerance is reused for target auditing; no tolerance is used in
directional metric comparisons.

### Policy and integrity

Policy receipt:
77d99c602047b7bda5a47e8ac6d5c869884d049bac9dcc397b05fdde98876339.
It was atomically saved outside Git before selected arrays were loaded. Bindings:
V3 policy/folds/results, selected array hashes, causal policy/result, origin map,
DBC/grid/profile, metrics, executor and environment.

Four distinct symlink-free historical stores (V2, V3, attribution, causal recovery)
are hash checked before/after both runs. V2 is hash-only; no aligned V2 arrays are
decoded. Only selected V3 ARX1/delay5 arrays and existing recovery origins are
deserialized. SHA, shape, previous measurement, fold, route, receipt and count are
checked. Historical byte-exact target/design/prediction origin proof is reused
without refit or nearest-row matching. Raw-source freshness is not rehashed;
cached prior attestation is reused to avoid reopening raw logs.

Both full runs succeed while raw decoder/numeric-reader APIs throw exceptions
and a filesystem audit hook rejects raw roots and rlog/qlog paths.

## Regression risk and acceptance

Risks: wrong Float32 decode order, substituted support, clipping, changed historical
predictions and premature admission. HOLD_LAST_OUTPUT, CONTINUOUS_ARX and
SOURCE_GRID_ARX use identical target/order/mask/count. Only the existing two routes
and three bins are permitted. Support minimum 201 is unchanged.

Frozen strict gate requires **all six scopes**: grid RMSE strictly below hold-last,
MAE/p95 no higher, finite metrics, unchanged coverage and no range violations.
No epsilon, percentage threshold or search. Constant-signal correlation may be
null with disclosed support; other metrics must be finite. Four or more failing
scopes is the predeclared majority rejection category; fewer failures is tradeoff.
Equal-route means within each speed bin are primary; sample-weighted means are
supporting only. Route p95 means are not pooled quantiles.

These are retrospective development routes, with no independent holdout.
Rollback means ignoring additive diagnostic files; no runtime path changed.
Independent review/full regression precede delivery; vehicle authority stays blocked.

## Validation method and actual results

### Six-scope result

449,426/449,426 targets are Float32-tolerant source-grid compliant. All continuous
predictions change under projection; none already equals its emitted value.
Ties = 0, range violations = 0. All arms have identical coverage.

Units below: steering-wheel degrees. Display values are rounded; gates use exact
machine-readable values.

| Route / fold / bin | N | Arm | RMSE | MAE | p95 |
| --- | ---: | --- | ---: | ---: | ---: |
| 7ae11bd9… / FOLD_B / LOW | 27,217 | HOLD_LAST_OUTPUT | 0.094164137 | 0.034893633 | 0.200000003 |
| 7ae11bd9… / FOLD_B / LOW | 27,217 | CONTINUOUS_ARX | 0.085079454 | 0.046811998 | 0.160168244 |
| 7ae11bd9… / FOLD_B / LOW | 27,217 | SOURCE_GRID_ARX | 0.088137992 | 0.038523713 | 0.199999809 |
| 7ae11bd9… / FOLD_B / MEDIUM | 146,878 | HOLD_LAST_OUTPUT | 0.059021786 | 0.020329797 | 0.100000381 |
| 7ae11bd9… / FOLD_B / MEDIUM | 146,878 | CONTINUOUS_ARX | 0.055073896 | 0.025732866 | 0.104416367 |
| 7ae11bd9… / FOLD_B / MEDIUM | 146,878 | SOURCE_GRID_ARX | 0.057548798 | 0.020052015 | 0.100000381 |
| 7ae11bd9… / FOLD_B / HIGH | 80,971 | HOLD_LAST_OUTPUT | 0.038656980 | 0.012080868 | 0.100000001 |
| 7ae11bd9… / FOLD_B / HIGH | 80,971 | CONTINUOUS_ARX | 0.037652573 | 0.016870651 | 0.096971054 |
| 7ae11bd9… / FOLD_B / HIGH | 80,971 | SOURCE_GRID_ARX | 0.038656980 | 0.012080868 | 0.100000001 |
| 962f2448… / FOLD_A / LOW | 85,107 | HOLD_LAST_OUTPUT | 0.090935345 | 0.027340874 | 0.100002289 |
| 962f2448… / FOLD_A / LOW | 85,107 | CONTINUOUS_ARX | 0.083212176 | 0.045729802 | 0.145535943 |
| 962f2448… / FOLD_A / LOW | 85,107 | SOURCE_GRID_ARX | 0.085216183 | 0.035210969 | 0.100002289 |
| 962f2448… / FOLD_A / MEDIUM | 79,278 | HOLD_LAST_OUTPUT | 0.044481535 | 0.014145160 | 0.100000024 |
| 962f2448… / FOLD_A / MEDIUM | 79,278 | CONTINUOUS_ARX | 0.044351639 | 0.026807986 | 0.095300439 |
| 962f2448… / FOLD_A / MEDIUM | 79,278 | SOURCE_GRID_ARX | 0.045325669 | 0.015856859 | 0.100000024 |
| 962f2448… / FOLD_A / HIGH | 29,975 | HOLD_LAST_OUTPUT | 0.040253574 | 0.012667222 | 0.100000024 |
| 962f2448… / FOLD_A / HIGH | 29,975 | CONTINUOUS_ARX | 0.039467685 | 0.017924929 | 0.098435333 |
| 962f2448… / FOLD_A / HIGH | 29,975 | SOURCE_GRID_ARX | 0.040253574 | 0.012667222 | 0.100000024 |

| Route / fold / bin | Strict gate | Failed metrics vs hold-last |
| --- | --- | --- |
| 7ae11bd9… / FOLD_B / LOW | FAIL | MAE:HOLD_LAST_GATE |
| 7ae11bd9… / FOLD_B / MEDIUM | PASS | none |
| 7ae11bd9… / FOLD_B / HIGH | FAIL | RMSE:HOLD_LAST_GATE |
| 962f2448… / FOLD_A / LOW | FAIL | MAE:HOLD_LAST_GATE |
| 962f2448… / FOLD_A / MEDIUM | FAIL | RMSE:HOLD_LAST_GATE, MAE:HOLD_LAST_GATE |
| 962f2448… / FOLD_A / HIGH | FAIL | RMSE:HOLD_LAST_GATE |

**SOURCE_GRID_OBSERVATION_REJECTED**, 1/6 gates pass. Only route 7ae11bd9… /
FOLD_B / MEDIUM passes. All six scopes lower continuous ARX MAE but increase RMSE:
GRID_TRADES_RMSE_FOR_MAE. LOW still loses MAE to hold-last on both routes.
Route 962f2448… / MEDIUM loses RMSE and MAE. Both HIGH scopes equal hold-last on
primary metrics, so strict RMSE improvement fails.

### Unchanged and transition explanation

These outcome partitions explain results only. They cannot select a rule, alter
a gate or create a selector. Multi-quantum/large-transition labels overlap;
sign reversal is an additional overlapping diagnostic.

| Route / bin | Unchanged fraction | Unchanged continuous MAE | Unchanged grid MAE | One-quantum grid RMSE | Multi-quantum grid RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7ae11bd9… / LOW | 0.776133 | 0.024947854 | 0.013307133 | 0.089226498 | 0.287789750 |
| 7ae11bd9… / MEDIUM | 0.844681 | 0.008825447 | 0.000421553 | 0.098845257 | 0.248761302 |
| 7ae11bd9… / HIGH | 0.892665 | 0.006062812 | 0.000000000 | 0.099999995 | 0.207831115 |
| 962f2448… / LOW | 0.825831 | 0.030880819 | 0.018142109 | 0.094193142 | 0.293100301 |
| 962f2448… / MEDIUM | 0.881543 | 0.016875695 | 0.003356848 | 0.095778172 | 0.209240728 |
| 962f2448… / HIGH | 0.888974 | 0.006580758 | 0.000000000 | 0.099999997 | 0.217468810 |

Emission removes many small continuous errors in unchanged samples but does not
globally beat hold-last. Quantized transitions introduce a different tradeoff.
The diagnostic establishes no physical EPS response truth.

### Execution and checks

Two complete runs match exactly: integer codes, Float32 emitted bytes, metric
tables, counts, verdict and receipt SHA. Historical input trees are unchanged.
Result receipt:
e87c48274d072231fd72c3615b096b25af46dee1db6544a6907118619ac847da.

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression / build | Focused unittest; AutoTune/controls test_runner; Ruff; compileall; SCons; publication; diff check | New policy/code/result SHA and private verification record | New focused 48 PASS; empirical focused 741 PASS; controls 142 PASS; Ruff/syntax/publication/privacy PASS; SCons PASS. Full AutoTune 3,110 PASS (949.73 s); before/after source binding identical. |
| Replay vs baseline | Existing two Cyber lateral replay unittest modules | References unchanged | 16 PASS; references unchanged |
| Simulation / closed loop | Not run | One-step observation only | No recursive endpoint rollout authorized |
| Shadow (candidate cannot actuate) | Not run | No controller integration | Vehicle/device operations prohibited |

## Handoff

Supporting state: **CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED**.
This closes only the current ARX1/FIR25 track, fixed source-grid emission and
predeclared single-condition selectors. It does not claim all actuator,
nonlinear or state-space models fail. Historical causal recovery remains PARTIAL;
this closure is additive under the separately approved emission test.

No V4 contract is generated: 6/6 did not pass. No model admission, refit, pooled
model, freeze, selector or holdout-package addition. No sequential rollout or
Stage B/yaw/gyro analysis. Latent-versus-emitted recursion semantics remain pending.

NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, CLOSED_MISSING_ADMISSIBLE_MODEL,
HOLDOUT_OPENING_CLOSED, FUTURE_UNTOUCHED_HOLDOUT_REQUIRED and
STAGE_B_SIGNAL_ADMISSION_BLOCKED remain in force. Future model development needs
separate authorization/policy; new routes are not opened here.

TA-B = TA_STANDALONE_TRADEOFF_ONLY; SG-A = SG_CLOSED_LOOP_TRADEOFF_ONLY.
CURRENT = BASELINE_EXACT; historical V1 = TRADEOFF_ONLY; V2 = REJECTED with 37
violations. COMPOSITION_NOT_RECOMMENDED, COMPOSITION_NOT_AUTHORIZED,
SEARCH_NOT_AUTHORIZED and FROZEN_EVALUATION_NOT_AUTHORIZED remain unchanged.
No TA/SG empirical execution.

Calibration uncertainty, independent calibration validation and pixel registration
remain pending. Metric calibration and independent reference remain unavailable.
Sealed reference = NOT_GENERATED. Vehicle = NOT_READY, REAL_VEHICLE_UNVERIFIED,
VEHICLE_ACTIVATION_BLOCKED. No production/controller/CAN/Params/device writes.

Public evidence has aggregates, source facts, opaque IDs and hashes only.
Per-row codes/emissions, target/prediction/residual values, origins, timestamps
and private paths remain outside Git. All historical evidence is immutable.
Commit and exact-HEAD CI references are provided in the delivery handoff.


### Verification notes

Local SCons initially lacked capnpc/cythonize on PATH. Activating the prepared
virtual environment resolved the invocation; the full build completed. The failed
invocation log is retained privately. Publication initially flagged two synthetic
test path literals. They were replaced by assembled synthetic path strings,
without changing diagnostic code, policy, rules or results; the 13 affected tests
passed again. Final publication audit: 1,106 files, zero findings.

Independent review passed: 48 focused tests, independently recomputed public
six-scope gates, route-equal aggregates, coverage and outcome counts. The reviewer
read only public evidence/code and no private inputs. No actionable findings.


The first full AutoTune invocation reported 3,109 passes and one error:
test_comfort_history.TestComfortHistory.test_complete_history_report_preserves_all_cases_and_prior_rejection
raised HISTORY_SOURCE_CHANGED. That guard hashes the broad Python/native
dependency tree; the invocation overlapped rebuilding and test-source cleanup.
After both stopped, the identical test passed unmodified (15.099 s).
A fresh full invocation uses explicit before/after source-binding receipts and
no concurrent code or native build changes. The first failure log is retained;
no test/reference/threshold was changed to suppress it. The fresh full run passed all 3,110 tests in 949.73 s; before/after source bindings are identical.
