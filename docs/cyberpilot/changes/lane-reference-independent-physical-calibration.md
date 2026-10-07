# Independent physical calibration and projection validation

## Identity and purpose

Cyber Validation; IMPLEMENTED software diagnostics/protocol, physical calibration measurement pending. feature/cyber-autotune, baseline b885a914adeb5cd5b2332ffb6a18a5a546f8aa99. Bound what pixel localization can mean in meters without treating model-derived camera pose as independent truth. No new driving data required by this protocol; no physical measurement has occurred.

## Original references

- Existing [calibration provenance audit](public-lane-reference-calibration-audit.json) and [projection boundary](public-lane-reference-projection-boundary.md) unchanged.
- comma4 narrow sensor-dependent nominal intrinsics in common/transformations/camera.py; calibrationd cameraOdometry/live extrinsics originates from driving model. Model pose cannot establish strict independent camera calibration.
- Pandar128 Configuration.yaml nominal intrinsics/height from prior pinned audit. Actual distortion/coordinate/time/GT registration remains unverified. The new fixture uses its numeric K/height with an explicitly constructed optical-to-ground orientation; **not** the dataset's actual calibrated camera transform.
- NumPy analytic ray kernel reused without changes; external OpenCV4.8.1 forward projectPoints supplies a separate numerical cross-check. No production dependency added or adapted code copied.

## Changes and expected effect

lane_projection_validation.py and tests create known ground points at5/10/20/30m, forward project them, invert the ground ray and compare analytic derivatives to central finite differences. Pixel/focal step.001px, rotation step1e-6rad, height step1e-5m; numerical checking parameters, not calibration uncertainty bounds.

Camera convention: optical x-right/y-down/z-forward; road x-forward/y-left/z-up. Rotation Jacobians are left perturbations about road-world axes. Height derivative shifts camera z while retaining observed pixel. Pose offset/lateral target1.5m is a constructed test point, not a real lane.

No state/history/actuator delay or production integration. Failure invalid geometry/behind/horizon/nonfinite → reject; unknown uncertainty remains null, never zero-filled. Existing sealed reference and comparator policies untouched.

## Regression risk and acceptance

Numerical consistency is not accuracy qualification. Forward/back error checked below1e-10m, central-difference agreement below1e-5 in each declared derivative unit, also rotated rig fixture. The tolerances concern floating arithmetic only. Measured intrinsics/extrinsics/road plane/distortion uncertainty and projection remainder are absent; no total conservative bound certified.

Rollback: remove new checks/protocol; original ray/Jacobian module remains unchanged. Independent review found no projection sign/unit issue.

## Independent stationary measurement protocol

1. Identify actual comma4 road sensor/device and frame geometry from independent hardware metadata. Nominal K is available but per-unit focal/principal point/distortion uncertainty is not. Do not infer camera generation from image dimensions alone.
2. Survey stationary camera optical-center height and vehicle coordinate axes with calibrated ruler/level/target geometry. Record measurement instrument, scale, repeated observations, operator/review identities, date and uncertainty. Default height1.22m is not a measurement.
3. Use surveyed checkerboard or AprilTag corners on a level stationary target/ground arrangement. Observe multiple target poses/depths across the camera FOV; independently solve intrinsic/distortion and camera pitch/roll/yaw relative to surveyed vehicle/ground axes. Do not use modelV2/cameraOdometry/live calibration as labels or constraints.
4. Keep independently surveyed targets/depths outside the fitting subset for projection validation. Compare projected/observed corners by range and report residual tails/unavailable geometry. Do not use an assumed standard lane width as a measured dimension; independently surveyed geometry only.
5. Measure level/grade/camber and document where a flat-plane approximation is valid. A single stationary floor calibration does not certify all later road grades. Explicitly bound or exclude unsupported road-plane conditions, never model-fill.
6. Freeze observations/source hashes before fit/review; privately retain calibration images. Human measurement/review is required: CALIBRATION_MEASUREMENT_PENDING. No synthetic automatic physical labels.
7. Only after public detector/private human validation gates pass may a private calibrated estimator be considered. Camera-frame ego left/right polylines still require validated association, independent road registration and separately reviewed desired-path provenance to become the existing complete metric reference series.

## Validation method and actual results

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Known camera numerical fixture | distance_validation + external cv2.projectPoints | [known-camera result](public-lane-projection-known-camera-validation.json) | 4 distances; forward/back near machine precision; max analytic/FD difference2.2603e-8; OpenCV forward pixel difference6.8213e-13 |
| Unit / regression / build | TDD focused/full AutoTune, Ruff/syntax/publication/diff/SCons | Final validation receipt | See executed final receipt |
| Replay / simulation | Not applicable: mathematical camera fixture | No controller changes | No vehicle/counterfactual improvement inferred |
| Shadow / physical calibration | No measured frames or hardware observations | [blockers](public-lane-detector-blocked-report.json) | NOT_RUN/BLOCKED |

Nominal fixture sensitivities (lateral output in meters; rotations radians):

| Forward m | u px, m/px | fx px, m/px | pitch, m/rad | height, m/m | roll, m/rad |
| --- | --- | --- | --- | --- | --- |
| 5 | -.003726660 | -.001117998 | -6.183017 | 1.236603 | 3.067905 |
| 10 | -.007453319 | -.001117998 | -12.366035 | 1.236603 | 3.067905 |
| 20 | -.014906638 | -.001117998 | -24.732069 | 1.236603 | 3.067905 |
| 30 | -.022359958 | -.001117998 | -37.098104 | 1.236603 | 3.067905 |

These are derivatives at one nominal constructed ray, not fixed comma4 meter multipliers. Pitch sensitivity varies with range; lateral/height/rotation coupling depends on actual K,R,C and observed ray.

## Error budget and blockers

[Symbolic budget](public-lane-detector-error-budget.json) records public pixel median/p95/failure separately from known-fixture sensitivities. Pixel p95 is a statistical quantile, not a deterministic uncertainty bound, and public marking diagnostic error is not private ego-boundary error.

For independently measured bounded inputs, first-order form is sum_i |J_i(distance)|*bound_i plus a certified projection remainder. Detector, intrinsic, extrinsic, height, road-plane/distortion/remainder terms remain distinct. Unknown bounds and total conservative uncertainty are null. Near-horizon/nonplanar geometry may invalidate linearization; no qualification by assigning convenient values.

Children: CAMERA_INTRINSICS_AVAILABLE (NOMINAL_ONLY), CAMERA_EXTRINSICS_MODEL_DERIVED, CAMERA_HEIGHT_UNVERIFIED, CAMERA_MOUNT_PITCH_UNVERIFIED, CAMERA_MOUNT_ROLL_YAW_UNVERIFIED, ROAD_PLANE_ASSUMPTION_UNVERIFIED, DISTORTION_UNCERTAINTY_UNVERIFIED, CALIBRATION_MEASUREMENT_PENDING.

[Metric public dataset status](public-lane-detector-metric-dataset-status.json): Pandar128 metadata exists but usable archive/conventions/GT association are not validated. METRIC_PUBLIC_GT_UNAVAILABLE; actual meter evaluation NOT_RUN. CULane/TuSimple/comma10k calibration absence cannot be bypassed with nominal K.

## Handoff

IMPLEMENTED: range-separated numerical Jacobian validation, explicit provenance children, independent stationary measurement protocol and symbolic budget.
SYNTHETIC SCREENING: not applicable to controller candidates; this is known-by-construction geometry checking only.
BLOCKED: actual independent calibration, metric GT, domain/human validation, association/registration/desired path. No sealed reference JSON.
REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Performance qualification: BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
Commit/review/check identities are recorded in Git/final validation receipt. No private raw data or public weight/dataset binary committed.
