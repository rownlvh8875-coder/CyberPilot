# Santa Fe coarse camera height diagnostic

## Identity and purpose

IMPLEMENTED: additive Cyber Validation / offline UI increment on
feature/cyber-autotune, baseline a24f12e20cfb8fab2c82488dce43ab06aefa9096.
The user explicitly approved a nonmeasured optical-center height of 1.40 m and
a diagnostic sensitivity range of 1.33–1.47 m for a user-declared 2021
The New Santa Fe TM with comma4 below the interior mirror, near the center plane.

This is APPROXIMATE / NON-QUALIFYING. Existing UNKNOWN-height receipts, detector
results, assisted reviews, calibration admission, controller history, comparator,
A3 rejection, and the CI unittest fix are preserved. No production caller is added.

## Original references and traced flow

- CyberPilot repository https://github.com/rownlvh8875-coder/CyberPilot,
  feature/cyber-autotune at the baseline above.
- Existing approximate_geometry_diagnostic.py and lane_projection_diagnostics.py
  supply the source-bound frame adapter and projection Jacobian; their existing
  license/attribution remains unchanged. No external detector/controller code adopted.
- [Hyundai official 2021 Santa Fe history/specification page](https://www.hyundai.com/kr/ko/brand/brandstory/model/santafe-history/2021-santafe)
  was read on 2026-10-08. Its 2021.12 Smartstream D2.2 2WD/FWD example reports
  4,785 / 1,900 / 1,685 mm length/width/height, 2,765 mm wheelbase and 235/60 R18.
  Full downloaded HTML identity is in santa-fe-vehicle-spec-context-v1.json;
  the HTML is held outside Git. Actual user's trim/VIN match is unverified:
  VEHICLE_SPEC_PROVENANCE_PARTIAL. A source hash is not per-vehicle verification.
- Only nominal tire-size arithmetic is used: sidewall 235×0.60 = 141 mm;
  wheel 18×25.4 = 457.2 mm; outer diameter 739.2 mm; unloaded nominal radius
  369.6 mm. Actual loaded wheel center and optical-center height are unmeasured.
- New coarse_camera_height_diagnostic.py reads these declarations and the existing
  orientation/mount prior → freezes a bounded policy → evaluates synthetic rays
  → emits detached SHA receipts → local visualizer displays them. No dataset,
  camera frame, route, Params, CAN, or model/planner runtime input is read.
- No new package, model weight, submodule change, or runtime network dependency.

## Changes and expected effect

Height has USER_APPROVED_COARSE_GEOMETRY_PRIOR provenance, mount-y has
USER_DECLARED_APPROX_CENTER_MOUNT provenance, and reported roll/pitch/yaw retain
MODEL_DERIVED_EXTRINSICS_PRIOR provenance. They are not merged into independent
physical provenance. measurement_uncertainty and physical_uncertainty remain null.
Overall vehicle height and tire radius never derive the camera prior.

The original source convention remains:
E=device-from-calib; V=optical-to-device; F=FRD-to-FLU;
R=F E^T V, relative physical Euler rotation F E^T F.
Positive reported pitch is not blindly inserted into an independent Euler frame;
combined rotations use the full matrix adapter. Coordinates are assumed road FLU
(X forward, Y left, Z up), camera vertical-footpoint origin, not surveyed vehicle datum.

Frozen height grid: 1.33, 1.35, 1.375, 1.40, 1.425, 1.45, 1.47 m.
Frozen reported pitch grid: 1.84, 2.34, 2.84 degrees.
Four nominal forward distances: 5, 10, 20, 30 m. 84 height×pitch×distance cells.
Separate roll [-0.5, 0, 0.5] and yaw [-0.3, 0.2, 0.7] degree 1D probes: 24 cells.
The ±0.5 degree probes are arbitrary bounded algebraic sensitivity experiments,
declared before execution, not empirically justified physical uncertainty intervals.
No optimization, acceptance threshold, or outcome-dependent grid change.

Nominal rays to center and a synthetic +1 m lateral probe are held fixed across
the matrix, rather than regenerating rays to make every result equal the target.
The +1 m probe is not a lane boundary/width. World-axis Jacobians and central
differences of reported pitch (1e-6 rad step) are named separately.
Pixel sensitivity remains a coefficient divided by actual fx, which is unknown.
Undistorted pinhole, planar ground, and calibration-aligned road are assumptions.

NOMINAL_APPROX_GEOMETRY_RESULT and DIAGNOSTIC_SENSITIVITY_ENVELOPE have separate
receipt SHAs. Sampled min/max envelopes are not continuous-domain or physical
uncertainty bounds. All promotion, qualification, vehicle activation, private
input and sealed-reference permissions are false.

At fixed nominal orientation, the height-only endpoints scale intersections
by exactly 0.95 / 1.05. Combined sampled height/pitch intersections:

| Nominal forward ray | Sampled forward intersection |
| --- | --- |
| 5 m | 4.5952–5.4321 m |
| 10 m | 8.9316–11.2117 m |
| 20 m | 16.8835–24.0056 m |
| 30 m | 24.0002–38.7614 m |

These are diagnostic geometry coordinates, not measured distance errors.
Yaw probes produce approximately ±0.2621 m center lateral displacement at 30 m;
roll probes approximately ±0.0122 m in this assumed geometry. No real lane claim.

Future valid physical receipts can be compared against 1.40 m (physical minus
coarse) and the range. Outside-range physical values are never rejected/clamped.
Physical provenance takes precedence for a future matched device; the current
prior lacks per-unit identity, so comparison explicitly does not select or
activate any calibration, validate live calibration, or qualify a reference.
TEST_ONLY physical fixtures remain identified as such.

## Regression risk and acceptance

Principal risks: accidental prior promotion, old receipt mutation, ray retargeting
that hides height effects, pitch/roll sign mixing, inferred camera height from
overall height, and treating the sampled envelope as measurement uncertainty.
TDD covers missing/mutated/resealed/stale priors and policy, fixed-ray scaling,
signs, immutable original prior, independent admission rejection, physical values
outside the range, source drift, source-bound UI state and closed private gates.

Acceptance is structural/numerical diagnostic correctness only; no new pixel,
lane, controller or performance threshold. No real-vehicle scenario or private
holdout is used. Rollback is reverting this additive increment; old independent
contracts and historical receipts remain intact. Independent read-only review
checks source/config binding, unit/sign handling and qualification separation.

## Validation method and actual results

Verification results are recorded in coarse-height-validation-v1.json.
Commands use the existing Ubuntu 24.04 WSL .venv.

| Stage | Method | Actual status / limits |
| --- | --- | --- |
| TDD | unittest coarse geometry and UI | RED observed, followed by focused PASS |
| Regression | tools/test_runner.py AutoTune + controls -j2 | See validation receipt |
| Static/privacy | Ruff, compileall, publication_check, authority/scope, diff | See validation receipt |
| Build | PATH="$PWD/.venv/bin:$PATH" .venv/bin/scons -j2 | See validation receipt |
| Browser | Chrome via actual local 127.0.0.1 server | selectors, nominal/envelope, refresh, console and same-origin assets tested |
| Replay / closed-loop controller | Not applicable | Controller/evidence work unchanged |
| Shadow / vehicle | NOT RUN | No live/vehicle authority |

## PENDING EVIDENCE / BLOCKED / NOT RUN / VEHICLE STATUS

CALIBRATION_MEASUREMENT_PENDING and
INDEPENDENT_CALIBRATION_VALIDATION_PENDING remain.
INDEPENDENT_EXTRINSICS_UNAVAILABLE and METRIC_CALIBRATION_UNAVAILABLE remain.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
Existing CULane, independent blind-reviewer, ego association, road registration,
desired path and private validation blockers are not resolved by these diagnostics.

Private comma4: NOT_OPENED. Sealed reference: NOT_GENERATED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

Local launch:
.venv/bin/python -m openpilot.tools.cyber_autotune.approximate_geometry_visualizer
The tool prints its loopback URL. Original historical UNKNOWN-height data remains
available separately; the new coarse panel shows user-approved defaults explicitly.
The next required evidence is independently observed physical calibration plus
independent validation, not additional tuning of these coarse parameters.
