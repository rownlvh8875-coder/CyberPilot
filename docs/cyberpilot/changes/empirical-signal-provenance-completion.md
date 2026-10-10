# Empirical signal provenance completion

## Identity and purpose
Cyber Validation / AutoTune; baseline 4fdd74a07, feature/cyber-autotune.
Read-only numeric provenance audit; no historical regeneration, actuator
refit, controller execution or production authority. Implementation pending.

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
PENDING. No numeric payload inspected for this generation yet.
No image/video/GPS/model/fused pose payload access is authorized.

## Handoff
Keep Stage A strict gate failure, TA/SG tradeoff, V1/V2 verdicts and all
calibration/reference blockers. Sealed NOT_GENERATED; vehicle NOT_READY.
