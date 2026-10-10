# Empirical plant V2 TRAIN / DEVELOPMENT generation

## Identity and purpose

Validation-only additive increment from feature/cyber-autotune baseline
cfeb0fc293c8f3fd66b904504a9c5c728e8a48af. Status: implemented; actual numeric
extraction and TRAIN fitting completed, DEVELOPMENT selection blocked.
This is EMPIRICAL_PLANT_V2_TRAIN_DEV_GENERATION, not a repeat of the source audit.

The prior audit is immutable input. Exactly its three admitted, identity-complete,
scoped-equivalent routes with the same full CarParams profile are used. Partial
classes, V1 data, duplicate routes and all other old routes are excluded. These
old routes retain prior-analysis-unknown status and cannot become untouched
holdout. No TA-B, SG-A, composition, candidate evaluation or vehicle action runs.

## Original references

The source audit at the baseline binds public origin
[ajouatom/openpilot](https://github.com/ajouatom/openpilot), exact commits
[18c07cfa](https://github.com/ajouatom/openpilot/tree/18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29)
and
[6ca11a4a](https://github.com/ajouatom/openpilot/tree/6ca11a4aea8223ebfebb1140bd8094ef1b3c5b90),
their schema/adapter identities, relevant source files/symbols and MIT license
provenance. This increment consumes those identities without re-auditing source.
The equivalence scope remains
LEGACY_HYUNDAI_SANTA_FE_2022_SIGNAL_CONTENT_AND_LOGICAL_PUBLICATION_ONLY;
it is not global controller/runtime or physical-hardware equivalence.

Full CarParams SHA:
252dff3c55c39f34e0375d0bf36a7a7792c8b332cca13eda491d57321eb0a542.
Empirical profile SHA:
494ce20b81e7f212ade6f30f89686752817d52d2d0e0e7658ab0a7239c0e35b3.
No production source, submodule gitlink, dependency lock, model or LFS object changes.
Existing source-bound numeric reader, alignment, discrete yaw hypotheses and
low-order least-squares model utilities are reused.

## Changes and expected effect

Five offline modules separate frozen authority/policy, whitelisted signal
extraction, restartable private execution, TRAIN/DEVELOPMENT fitting and redacted
publication. No runtime integration point is added.

The exact three opaque route IDs were sorted lexically; roles were persisted
immutably before any numeric payload getter. Split SHA:
05bbdae01bcf22bab814ac2545514e18eff28afc346e77f1d1d0bceb8198c81f.
Authorization SHA:
fcaee143ecbd280be1ff0c16c19c02b16d47d248b41a6b5b30220f91c680e17a.
The authorization binds selected source sets, source-specific adapters, source/code
closure, whitelist, privacy, timebase, masks and model policy. Unknown routes,
adapters, changed source bytes or stale caches fail closed.

| Opaque route ID (prefix; full ID in split receipt) | Role | Source | Extracted segments |
| --- | --- | --- | ---: |
| 7ae11bd9 | TRAIN | 18c07cfa | 70 |
| 962f2448 | TRAIN | 18c07cfa | 86 |
| eda13cbe | DEVELOPMENT | 6ca11a4a | 1 |

All 157 selected segments were extracted, with zero rejected segments. One selected
stream per original envelope segment is used; histories never cross a segment or
route. Rlog is preferred to qlog for the same envelope segment. Source schemas are
loaded in separate worker processes. Per-segment opening receipts precede numeric
body access, and source bytes are hashed before and after extraction. Private
writes are atomic, immutable and resumable; a mismatched receipt is never replaced.

Allowed numeric access is restricted to command, measured car state, intervention
context and direct gyroscope messages. Additional wheel-speed/steering-rate
availability is counted. Image/video codecs, GPS, model/planner/path/lane, fused pose,
camera odometry, calibration and candidate data are not accessed. Raw paths,
timestamps, traces and all fitted coefficients remain private. Public receipts
contain opaque hashes, aggregate counts/metrics and failure states only.

### Command bridge

Each route independently confirms logged normalized post-controller torque equals
Float32(raw torqueOutputCan / recorded effective STEER_MAX). The runtime setting
and source branch independently resolve 409 in all selected segments; this value
was not chosen by fitting. Eligible pairs all match exactly in Float32. Residuals
below compare logged Float32 to the mathematical unrounded ratio.

| Route | Eligible pairs / exact Float32 matches | Invalid pairs | Median absolute residual | p95 absolute residual | Maximum absolute residual | Raw / normalized magnitude saturation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7ae11bd9 | 415,896 / 415,896 | 10 | 5.8293e-10 | 4.9913e-9 | 2.9729e-8 | 11 / 11 |
| 962f2448 | 501,946 / 501,946 | 19 | 5.2828e-10 | 5.5014e-9 | 2.9729e-8 | 41 / 41 |
| eda13cbe | 5,495 / 5,495 | 10 | 0 | 0 | 0 | 0 / 0 |

All three verdicts are ROUTE_COMMAND_BRIDGE_CONFIRMED; pooled eligible pair count
is 923,337, with zero sign/domain conflicts. This permits Stage A command pooling.
DEVELOPMENT has zero nonzero eligible commands; its scale is source/metadata-bound,
not independently identifiable from zero-command observations. The relation is a
logged post-CarController representation, not EPS acknowledgement,
every-frame transmission, actual rack torque or physical application.

### Timebase, masks and support

The unchanged frozen policy uses a 100 Hz integer grid, latest-past samples only,
maximum source age 20 ms, strictly increasing clocks, no gap interpolation and
no repeated target-output event. Duplicate/regressing mandatory source clocks
reject the segment. Optional gyro clock failure is explicitly excluded rather
than erasing actuator support.

The diagnostic mask requires finite valid messages, forward gear, latActive,
no driver override, no EPS fault, speed in a declared bin and no source gap.
Unknown safety/curvature-limit states remain null. Clean primary support remains
zero. Diagnostic availability must not be represented as independently confirmed
absence of limiting.

LOW is 5 <= speed < 15 m/s, MEDIUM is 15 <= speed < 25 m/s, HIGH is speed >= 25 m/s.
Masks, interventions and bin crossings break histories. Every configuration uses
the same contiguous 45-sample design support. A run of n samples contributes
max(0, n - 44) common design rows. Minimum DEVELOPMENT support stays 201.

| Route / split | LOW common rows | MEDIUM common rows | HIGH common rows |
| --- | ---: | ---: | ---: |
| 7ae11bd9 TRAIN | 27,217 | 146,878 | 80,971 |
| 962f2448 TRAIN | 85,107 | 79,278 | 29,975 |
| TRAIN pooled | 112,324 | 226,156 | 110,946 |
| eda13cbe DEVELOPMENT | 0 | 0 | 0 |
| DEVELOPMENT pooled | 0 | 0 | 0 |

| Route | All grid samples | Diagnostic valid / unavailable | Gap intervals / masked samples | Mask intervals | Intervention intervals | Segment boundaries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7ae11bd9 | 415,844 | 382,025 / 33,819 | 24,642 / 24,661 | 24,014 | 106 | 69 |
| 962f2448 | 512,680 | 328,030 / 184,650 | 17,273 / 29,291 | 14,523 | 423 | 85 |
| eda13cbe | 5,510 | 0 / 5,510 | 40 / 56 | 1 | 2 | 0 |

Break counts denote starts of contiguous invalid-reason intervals, including an
initial invalid interval; they are separate from invalid sample counts. Reasons
overlap. Bin totals exclude unbinned samples, while overall route totals retain
them. Detailed per-bin valid/unavailable, durations, longest runs, design rows and
break accounting are in the coverage receipt.

DEVELOPMENT has 5,510 unbinned samples: LOW_SPEED and NON_FORWARD_GEAR each affect
all 5,510; INACTIVE affects 5,501. Other overlapping reasons include invalid
messages, driver override and timestamp gaps/repeated output events. There is no
eligible driving support. The metadata-only admission could not reveal this.
The third route remains DEVELOPMENT: no result-based reassignment, alternate route
or relaxed mask/minimum is used.

### Stage A fitting and blocked selection

Input is source-confirmed raw CAN command; output is measured steering-wheel angle
in degrees. The unchanged eight configurations are ARX1 and FIR25, each with
delays 0/5/10/20 samples. TRAIN fits coefficients with Float64 NumPy least-squares,
rcond=None, fixed single-thread BLAS, no randomness. Recursive ARX must have
absolute pole below one. These are publish-time empirical delays, not independently
measured physical actuator dead time.

All eight candidates fit in each of three speed bins: 24 TRAIN fits. DEVELOPMENT
uses lowest RMSE with lower parameter count, family lexical order and lower delay
tie-breaks. ZERO_RESPONSE, HOLD_LAST_OUTPUT and TRAIN_STATIC_GAIN share support.

Every bin has zero DEVELOPMENT one-step and 0.25/0.5/1.0/2.0 s endpoint support.
Error/correlation values and finite/bounded validation are unavailable, not zero
errors or evidence of stability. Endpoint evaluation is conditional on observed
exogenous commands; it is not a future-command forecast. All bins therefore end
STAGE_A_MODEL_SELECTION_BLOCKED. No family/delay winner or selected Stage A model
is invented. The private result freezes all TRAIN fits, but the selected-model map
is empty.

### Yaw admission and Stage B

The existing four discrete hypotheses (+deg/s, -deg/s, +rad/s, -rad/s), fixed
gyro axis/sign/causal-lag candidates and source-policy kinematic support are reused.
No continuous scale fit, fused signal, future sample or holdout enters selection.
The conservative per-route admission requires direct gyro correspondence in
addition to kinematic support; kinematic agreement alone cannot establish a yaw
unit or vehicle frame.

DEVELOPMENT has zero eligible yaw/gyro common support. No discrete hypothesis or
axis/sign/lag is selected, yaw admission is YAW_SIGNAL_UNUSABLE for this generation,
and Stage B is STAGE_B_SIGNAL_ADMISSION_BLOCKED. No Stage B coefficients, selection
or model artifact are generated. This does not reinterpret the historical V1
EMPIRICAL_YAW_SIGNAL_PARTIAL result. Device-axis correspondence would still not be
an independently calibrated IMU-to-vehicle transform.

### Future holdout package

Result SHA:
3f727f26b5a140e502921cf282c36ab988a649f94f1c63b10bd6347bba3c7467.
Model-freeze receipt SHA:
0182638b138d4fc1abe590641f294716bfa64d55e1eee3402abe12f51464af50.
Future evaluation-package SHA:
6119dd6a40700318cca9d151ece2effabdab1e850e0cabe807c568e02e2d1cd2.

The package binds split, source class, profile, units/metrics/support policies and
future admission. Both selected-model maps are empty because selection was blocked.
It remains CLOSED and evaluation_execution_authorized=false. It is a prepared
contract with an explicit missing-model prerequisite, not an executable evaluation
or holdout-ready claim. Reselection, refitting, threshold changes and old-route
holdout use are forbidden. No actual future HOLDOUT exists or was opened.
Stage C and TA/SG empirical execution remain NOT_RUN.

## Regression risk and acceptance

Risks include source/profile drift, stale/private cache substitution, clock gaps,
old-route prior-analysis exposure, closed-loop identification bias, weak excitation
and misleading zero-support metrics. Exact route/source authorization, atomic
receipt verification, causal alignment and shared support fail closed.

No performance threshold or READY/VALIDATED verdict is introduced. The gate for
this increment is faithful numeric execution and honest blocked reporting.
Existing V1 actuator holdout, yaw audit, architecture, TA/SG, historical candidates,
meter diagnostics, detector, private holdout and calibration/reference evidence are
unchanged. Rollback removes only this additive increment; private evidence is
retained. Independent review is required before publication; vehicle promotion is
not authorized.

## Validation method and actual results

Ubuntu 24.04 WSL, Python 3.12.13, repository .venv, fixed NumPy solver and single
thread BLAS. Numerical fitting/evaluation ran twice with exact result/freeze/package
SHA equality. Extraction ran once; an actual resume of all three routes reverified source hashes
and sealed caches, reproduced all three route receipt SHAs, and did not overwrite
evidence. This is not an independent second decode.

| Check / stage | Method | Actual result |
| --- | --- | --- |
| Focused V2 | six unittest modules plus public result-chain regression | 63 PASS; combined empirical focused 462 PASS |
| Full AutoTune / controls | tools/test_runner.py, -j 1 | 2,831 AutoTune + 142 controls = 2,973 PASS; 945.06 s |
| Lateral replay | explicit two cyber lateral replay modules | 16 PASS |
| Ruff / syntax | CI paths; compileall | PASS |
| Publication / privacy / authority | check_publication; sealed aggregate chain and history diff | publication_check files=1045 findings=0; privacy/authority PASS |
| Native build | activated .venv; scons -j2 | PASS (exit 0) |
| Independent review | separate reviewer, code and redacted receipts only | PASS; reviewer independently reran 63 tests and verified 10 public seals |
| Candidate replay / closed loop / shadow | outside authorized increment | NOT_RUN |
| Future holdout | package CLOSED; no opening | NOT_RUN |

The initial SCons invocation omitted .venv activation and failed to locate capnpc
and cythonize. The supported activated-environment build is recorded separately;
no source workaround or build requirement was removed.

## Handoff

Actual TRAIN/DEVELOPMENT generation completed, with model selection blocked by
zero DEVELOPMENT driving support. A different dataset/policy requires separate
authorization; the frozen roles and existing holdouts cannot be retrofitted to
produce a model. FUTURE_UNTOUCHED_HOLDOUT_REQUIRED remains mandatory.

Historical states remain CURRENT=BASELINE_EXACT, V1=TRADEOFF_ONLY, V2=REJECTED with
37 violations, TA-B=TA_STANDALONE_TRADEOFF_ONLY, SG-A=SG_CLOSED_LOOP_TRADEOFF_ONLY,
COMPOSITION_NOT_RECOMMENDED, COMPOSITION_NOT_AUTHORIZED, SEARCH_NOT_AUTHORIZED and
FROZEN_EVALUATION_NOT_AUTHORIZED. Reference/calibration retains
CALIBRATION_UNCERTAINTY_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE and
INDEPENDENT_REFERENCE_UNAVAILABLE. Sealed reference remains NOT_GENERATED. Vehicle
remains NOT_READY, REAL_VEHICLE_UNVERIFIED and VEHICLE_ACTIVATION_BLOCKED.
