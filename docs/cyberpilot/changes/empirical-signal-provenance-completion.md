# Empirical signal provenance completion

## Identity and purpose
Cyber Validation / AutoTune; baseline 4fdd74a07, feature/cyber-autotune.
Read-only numeric provenance audit; no historical regeneration, actuator
refit, controller execution or production authority. Audit completed; no empirical counterfactual admitted.

## Original references
Recorded ajouatom/openpilot commit 5a970f1ad25d9f07d055955d7a7c14603b6b7813,
HYUNDAI_SANTA_FE_2022 legacy torque, OS19.8-carrot-bt1. Rebind committed blobs:
CarController, values, CarState, car/card.py, car.capnp, ESP12 DBC, sensor
schema/producer, interface and parameter-default source. Existing permissive
current-branch definitions are not substituted.

## Design and alternatives
Use separate frozen policy, whitelisted numeric reader, statistical crosscheck
and private runner. Prefer actual same-message raw/normalized command pairs;
reject assumed384 scaling or continuous result-driven scale fitting.
CarController has a runtime CustomSteerMax override: bind the recorded initData
whitelisted setting; missing runtime provenance gives PARTIAL, not CONFIRMED.
Bridge checks use exact Float32 storage-rounding semantics plus exact numeric
residuals. Requested/post-output differences cannot identify safety/rate/driver
reason without a source-proven matching request.

Yaw hypotheses are exactly +deg/s, -deg/s, +rad/s, -rad/s. Direct sensor source
must prove radians and sensor source/union. Compare all three axes and signs
with causal publish/sensor-clock alignment and declared nonnegative lags.
No fitted continuous scale, bias correction or independent rigid-transform
claim. Kinematic steering/speed yaw is supporting only, no angle-offset learner.

## Split and leakage
Reuse old TRAIN/DEVELOPMENT only for correspondence/model selection.
Old actuator HOLDOUT is COMMAND_BRIDGE_ONLY and never yaw selection/validation.
Old EMBARGO becomes new yaw HOLDOUT, frozen before its numeric payload access;
keep the previously rejected final segment rejected. This does not restore
route independence or temporal separation: adjacent route segments and
autocorrelation remain limitations. Segment histories never cross boundaries.
Prior yaw fields were read in actuator numeric parsing but not analyzed;
therefore old actuator HOLDOUT is not called a new untouched yaw holdout.

## Execution/acceptance policy
Freeze hypotheses, axis/sign/lag candidates, resampling, masks, support,
selection/tie-break, crosscheck metrics and optional model grid before numeric
analysis. Source facts and metadata alone determine constants.
Gyro/kinematic agreement can support unit correspondence only; vehicle frame
always remains partial without independent rigid calibration.
At most existing eight ARX1/FIR25 configs per speed bin, TRAIN coefficients,
DEVELOPMENT selection, new yaw HOLDOUT once after correspondence/model freeze.
Yaw fitting is blocked unless development unit/sign support and all declared
gates exist. Stage C composed rollout remains blocked because historical
Stage A strict READY gate failed. No TA/SG empirical execution.

## Regression risks and verification
Risks: runtime normalization override; requested/output publish ordering;
uncalibrated gyro/device axes; empty DBC yaw unit; reused holdout; missing limit
reason; single-route bias; future alignment; private publication/cache drift.
Tests first, frozen source execution, exact extraction/evaluation repeats,
resume/no-overwrite, independent review, full AutoTune/controls, lateral replay,
Ruff, syntax, SCons, publication/privacy/authority and clean diff.
Rollback removes only additive modules/artifacts. No browser UI planned.

## Validation method and actual results
Policies and source receipt were committed at 63621f96b before this generation's
numeric inspection. The source SHA is 5a970f1ad25d9f07d055955d7a7c14603b6b7813.
Execution was frozen before payload reads; final execution binding is
35e8847f07105059f0a7f8d30f638f4467cabef9e64409f627d7995ad2460202.
All 13 new public receipts are pinned by empirical_signal_publication.py.

### Raw / normalized command bridge
RAW_TO_NORMALIZED_COMMAND_CONFIRMED. Source default STEER_MAX is **409** for
this legacy Santa Fe profile, not the ALT_LIMITS default384. Runtime initData
CustomSteerMax provenance was available. All 564,149 eligible same-message
pairs across 94 complete segments exactly match Float32(raw /409). Exact
unrounded double equality holds for 109,134 pairs; the difference is storage
quantization, not a fitted scale. Sign/domain conflicts:0.
Residual median =6.5124e-10, p95 =5.4285e-9, maximum =2.97295e-8 normalized units.
This confirms logged post-CarController command representation, not physical
EPS application/acknowledgment.

POST_CONTROLLER_LIMITING_ONLY_OBSERVABLE: 563,702 causal publish-associated
request/output pairs, 461,076 unequal. Differences include quantization and
publish timing; card.py publishes last actuators output before controls_update.
This is not an exact request-transaction link or a count of known safety/rate/
driver-limit interventions. Source gaps are excluded. Limit reasons remain null,
CLEAN_LIMIT_MASK is not confirmed, historical clean-primary-valid0 unchanged.

### Source, direct gyro and kinematic evidence
CarState copies ESP12 YAW_RATE unchanged. Pinned DBC: unsigned13-bit little
endian at bit40, factor0.01, offset-40.95, range[-40.95,40.96], **unit empty**.
The source receipt preserves that empty string; the public verdict uses
EMPTY_DBC_UNIT_UNVERIFIED as a serialization enum.

The lsm6ds3/trc producer converts raw angular velocity to rad/s and publishes
device [sensorY,-sensorX,sensorZ]. Independent device-to-vehicle rigid transform
is unavailable. TRAIN/DEVELOPMENT selected YAW_H1 (+deg/s) and device -Z,
causal lag10 samples using frozen publish/acquisition-age rules. This lag is
a correspondence alignment, not independently measured physical dead time.

| Role | Common valid / total | Gyro correlation | Kinematic correlation |
|---|---:|---:|---:|
| TRAIN | 40,430 /257,947 | -0.099351 | 0.991722 |
| DEVELOPMENT | 20,351 /95,990 | -0.009710 | 0.957798 |
| New yaw HOLDOUT | 21,627 /114,156 | 0.005021 | 0.947294 |

Holdout gyro RMSE =0.0229286 rad/s, MAE =0.0159563, p95 =0.0446455.
Holdout kinematic RMSE =0.00541294 rad/s, MAE =0.00357460, p95 =0.0127681.
The magnitude comparison strongly separates deg/s from unconverted rad/s,
but **near-zero gyro correlation does not establish dynamic axis
correspondence or independently confirm yaw units**. Steering/speed kinematics
support the discrete deg/s hypothesis only: static wheelbase/ratio, unknown
angle offset, tire slip/compliance/understeer remain limitations.
No continuous scale/bias fitting, fused pose or learned angle-offset input.

### Conservative adjudication and model outcome
The frozen automatic policy output was YAW_UNIT_SUPPORTED_FRAME_PARTIAL.
That output compares discrete magnitudes and is retained verbatim. Public-only
independent review found the conjunction insufficient for unit/frame admission.
The additive empirical-signal-provenance-adjudication-v1.json binds all original
receipts and states:
- EMPIRICAL_YAW_SIGNAL_PARTIAL
- YAW_UNIT_LIKELY_NOT_CONFIRMED
- EMPIRICAL_YAW_MODEL_BLOCKED / BLOCKED_NO_CONTIGUOUS_SUPPORT
- EMPIRICAL_PLANT_PARTIAL; full_plant_ready=false

The predeclared yaw fit attempts (8 configurations per bin) all returned
INSUFFICIENT_SUPPORT, before coefficient fitting. Maximum TRAIN design rows82,
below the frozen minimum201 (FIR needs additional dimension-based support).
No model was selected. Development scoring did not run: reported development
count0 is a placeholder, **not measured zero development support**.
No model coefficients or holdout model predictions/metrics exist.
The raw automatic summary's EMPIRICAL_YAW_MODEL_REJECTED remains immutable;
the adjudication clarifies that this is blocked coverage, not observed model
performance rejection. No family, delay, metric, threshold, mask or split was
changed after looking at results.

### Integrity, split and interrupted execution
One homogeneous route only; no additional homogeneous route found in the
declared root. TRAIN43, DEVELOPMENT16, old actuator HOLDOUT16 command-only,
new yaw HOLDOUT20 old EMBARGO segments. One preexisting truncated final segment
was rejected whole;19 complete new yaw holdout segments evaluated for signal
crosschecks. These are adjacent same-route segments, not route-independent
generalization or temporally independent validation.

The first execution stopped in TRAIN after three numeric receipts because one
gyro acquisition timestamp regressed. Its binding/receipts remain private and
unchanged; holdout had not opened. A new attempt binds that failure receipt.
The only handling change rejects that entire segment's 5,518 gyro messages:
no sorting, interpolation, clock repair or relaxed age policy. Original numeric
evidence is retained; command/state remain eligible, gyro support unavailable.
The regression and independent review passed before continuation.

TRAIN/DEVELOPMENT extraction repeated exactly; holdout numeric opened once
after correspondence/model freeze. Analysis repeated exactly from cached numeric
receipts. Resume was run with raw-event parsing patched to raise; all receipt
SHAs remained exact without raw payload reopening. Atomic numeric receipts are
recovered before any payload parse. Public/private alias paths and stale
source/cache identities fail closed. Old split/inventory/metadata/binding are
anchored to historical public pins, not merely self-sealed hashes.

No images/video, GPS/location, modelV2, liveCalibration, cameraOdometry,
planner/fused-pose payloads were used. Raw signals, paths, timestamps, route
names and model data stay private. Public receipts contain aggregates/hashes.

### Independent review and remaining gates
Independent public-code and aggregate review covered source identities, unknown
fields, gyro clocks, historical split authenticity, holdout freeze/resume,
publish-time gaps, serialization, weak gyro association and model availability.
Regressions cover every actionable finding. No UI changed; browser check N/A.

Stage A remains EMPIRICAL_ACTUATOR_MODEL_ONLY with its original strict READY
failure; no refit or gate relaxation. Stage C is blocked by both Stage A and yaw
admission. TA/SG empirical execution, composition, candidate search and frozen
candidate evaluation remain unauthorized. Future work needs a new route/split
and predeclared gap/support policy, plus source-proven unit/frame evidence;
the same holdout must not be used to relax support or select another model.


## Handoff
Keep Stage A strict gate failure, TA/SG tradeoff, V1/V2 verdicts and all
calibration/reference blockers. Sealed NOT_GENERATED; vehicle NOT_READY.

## Completed local verification
- New signal provenance tests93; combined empirical focused187 PASS.
- Full AutoTune2556 + controls142 =2698 PASS (910.45s).
- Lateral replay16 PASS.
- Privacy/authority/publication focus299 PASS,140 subtests.
- Ruff, compileall syntax, SCons, staged publication_check PASS (966 files,0 findings).
- Independent code and public aggregate review: no remaining actionable findings.
- Historical artifact and production-path diff empty; no browser UI changed.
- Exact cached resume PASS with raw-event reader forbidden.
