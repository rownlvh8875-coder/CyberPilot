# Approximate vehicle geometry diagnostic

## Identity and purpose

- Area: Cyber Validation / offline diagnostic geometry and local visualization.
- IMPLEMENTED: APPROX_GEOMETRY_DIAGNOSTIC_V1. Approximate prior AVAILABLE;
  actual independent calibration remains PENDING / BLOCKED.
- Baseline feature/cyber-autotune at 4190c7c65ad5ee1c58cae37a62846fc06bc22e6e:
  fetched, local/origin equal, clean before edits.
- Purpose: preserve user's mirror-lower/center mounting declaration and reported
  calibration angles, evaluate algebraic height/orientation/mount sensitivity,
  prepare comparison with future explicit stationary wizard evidence.
- Source/config/output identity: [validation receipt](approximate-geometry-validation-v1.json).
  No controller/candidate performance evaluation or physical reference production.

## Original references

- Repository https://github.com/rownlvh8875-coder/CyberPilot, exact baseline above.
  Repository license retained; existing transformation/projection APIs reused,
  no external code/assets/models/dependency copied or installed.
- common/transformations/README.md documents device and calibrated FRD axes:
  forward/right/down; view axes right/down/forward; car origin below device on road.
- common/transformations/camera.py: device_frame_from_view_frame,
  get_view_frame_from_calib_frame; common/transformations/model.py:get_warp_matrix;
  common/transformations/orientation.py and transformations.py: Euler conversion.
- selfdrive/locationd/calibrationd.py:handle_cam_odom derives pitch/yaw from
  cameraOdometry motion, composes device-from-calib RPY, publishes rpyCalib through
  extrinsicsCalibration. modeld/modeld.py consumes this device_from_calib_euler.
  User's “liveCalibration” is preserved as reported prior, not parsed live/log data.
- Existing camera_calibration_evidence.py and lane_projection_diagnostics.py are
  authoritative independent admission and diagnostic ray/Jacobian kernels, unchanged.
- Source hashes bound in new prior. Existing NumPy/Python3.12.13 environment.
  Existing six submodule gitlinks unchanged; no model weight/data used.

## Changes and expected effect

- approximate_geometry_diagnostic.py: separate frozen prior/firewall, exact frame
  adapter, symbolic height ray, bounded deterministic parameter matrix, declared
  vehicle-spec sanity hook, future physical consistency comparison and additive
  blocker snapshot.
- approximate_geometry_visualizer.py and approximate_geometry_assets: fixed-route
  127.0.0.1 form/table/schematic with explicit algebraic heights, original vs mapped
  angles, unknown height and closed reference/private gates.
- Two new test modules; four current diagnostic/pending receipts under changes.
- No integration into wizard/independent admission/runtime. Separate facade keeps
  prior values out of independent structural calibration.
- No controller/delay/state/reset changes, CAN/Params/device/CarController writes,
  live imports, route discovery, external requests, tuning or acceptance changes.
  Production controller/comparator, v1/v2 history and A3 rejection remain unchanged.
- Maintenance: source/schema changes require versioned artifacts; loaded model/UI/
  assets/convention drift is rejected. Fixed asset snapshots are served; a running
  old handler cannot relabel itself with a new disk source hash.

### USER DECLARATION

Mount below interior rear-view mirror; approximately vehicle center plane.
mount_y nominal0 m is USER_DECLARED_APPROX_GEOMETRY /
USER_DECLARED_APPROX_CENTER_MOUNT. It is not a surveyed datum or a physical
measurement. mount_x and optical-center height remain null.
No range/bound has been supplied. Caller-defined mount offsets are explicitly
DIAGNOSTIC_SENSITIVITY_RANGE, never PHYSICAL_UNCERTAINTY.

### VEHICLE SPEC

Native/replay/test sources pin HYUNDAI_SANTA_FE_2022 for existing software
experiments. This does not establish the actual camera-bearing vehicle's exact
model year/variant/spec identity. Current VEHICLE_SPEC_IDENTITY_PENDING has
null overall length/width/height/wheelbase and no fabricated manufacturer URL.
No manufacturer spec request can be scoped accurately until identity is established.

vehicle_sanity accepts an explicitly declared source URL/hash/model/dimensions/
same-ground-inside-cabin assumption. This is a diagnostic document-prior check;
it does not authenticate the source or verify the user vehicle match.
Overall height is only a declared sanity boundary and never creates a camera
height point estimate, interval or “height × coefficient” derivation.
No coarse camera-height prior is justified or generated in this increment.

### MODEL-DERIVED PRIOR and convention

Original reported degrees: roll~0.00°, pitch~+2.34°, yaw~+0.2°.
Original rounded radians: pitch~0.0408, yaw~0.00349; no reported roll radian.
Degrees are explicitly the primary approximate report; exact math conversion
does not make their physical precision exact. Observed timestamp and uncertainty
are unknown. Prior source is USER_REPORTED_LIVE_CALIBRATION_NOT_LOG_CAPTURE,
MODEL_DERIVED_EXTRINSICS_PRIOR, independent=false.

Let E=Rz(yaw)Ry(pitch)Rx(roll) be device_from_calib, V optical/view_to_device
and F=diag(1,-1,-1) convert FRD→FLU. Then the diagnostic ray rotation is

~~~text
R_optical_to_diagnostic_road = F E^T V
A_relative_physical_Euler_rotation = F E^T F
R = A BASE_ROTATION
~~~

This assumes calibrated axes aligned with a hypothetical road frame; it is not
independent road registration. For a pure source pitch/yaw the physical-relative
angle is positive; pure source roll becomes negative. Composite rotations
reverse order on inversion: Euler extraction is coupled. Direct reuse of the
three source angles is wrong. The nominal combined report produces approximately
roll+0.00817°, pitch+2.33999°, yaw+0.200167° in the existing physical-style Euler
parameterization. These mapped values remain MODEL-DERIVED, not physical readings.

### APPROXIMATE GEOMETRY / symbolic height

[Current prior](approximate-geometry-prior-v1.json) has PARTIAL_APPROX_GEOMETRY,
camera_height_m=null, no measurement uncertainty, actual sensor unknown.
STATIC_HARDWARE_SOURCE only pins the existing source; unknown actual sensor means
no automatically chosen camera matrix/focal or assumed zero distortion.

[Symbolic example](approximate-geometry-symbolic-height-v1.json) uses synthetic
normalized optical (u=0,v=0.2), not an observed pixel. For rotated ray d:

~~~text
forward_from_camera_footpoint = h * (-d_x / d_z)
lateral_from_declared_center_plane = declared_mount_y + h * (-d_y / d_z)
~~~

Upward/horizon/nonforward rays fail closed. Origin is the camera vertical
footpoint for longitudinal analysis, not a surveyed vehicle datum. Ground is
assumed planar, rays pinhole/undistorted. Neither assumption is validated here.

parameter_policy freezes explicit positive algebraic heights, original source
RPY degree choices, mount offsets, rationale, stable enumeration and5/10/20/30m
camera-relative lookahead. No default height, plausible interval or arbitrary
uncertainty is created. Maximum256 rows is a resource limit, not a quality threshold.
Equivalent numeric duplicate parameters, nonfinite/invalid/empty grids fail closed.
Policy SHA and prior/source SHA bind each report.

At each parameter/lookahead the synthetic ground point is reprojected; derivatives
hold that resulting normalized ray fixed. Diagnostic reports expose normalized-u lateral
sensitivity, fixed-ray height sensitivity and world-axis rotation derivatives.
Pixel sensitivity stays coefficient/actual_fx_px because focal is not verified.
No detector error, physical uncertainty or conservative projection budget is
computed. Fixed-ray height/pitch changes and reprojected-distance derivatives
are different questions and are labelled separately.

### PHYSICAL MEASUREMENT comparison

compare_physical requires an existing authoritative admitted receipt; malformed
or approximate priors cannot replace it. The original physical receipt and prior
remain separate, immutable content identities. Reported source angles are mapped
to the existing physical convention before reporting wrapped angular differences.

The [current comparison](approximate-geometry-physical-comparison-pending-v1.json)
is PHYSICAL_MEASUREMENT_COMPARISON_PENDING; no actual receipt exists.
Future CLI --physical-wizard-workspace requires an explicitly named existing
stationary wizard store and revalidates its package/source/hash bindings.
No private route/camera discovery is performed.

Comparison is APPROX_PHYSICAL_CONSISTENCY_DIAGNOSTIC, never validation.
Per-unit camera matching is not verified by the unbound prior; cross-device/datum,
ground/frame/slope/model/measurement issues may explain differences.
No automatic discrepancy threshold is invented. API caller can explicitly declare
a diagnostic bound; results report whether it is exceeded without choosing truth
or changing any reference qualification threshold. TEST_ONLY receipt comparisons
remain labelled TEST_ONLY. No LIVE_CALIBRATION_VALIDATED state is created.

### QUALIFICATION firewall / blockers

Every diagnostic receipt enforces qualification_allowed=false,
reference_promotable=false, sealed_reference_allowed=false,
vehicle_activation_allowed=false, private_input_allowed=false.
Original independent admission rejects model-derived/spec/user-declared roles.
No prior is merged into physical receipt or sealed lane evidence.

The [additive blocker snapshot](approximate-geometry-blocker-snapshot-v1.json)
binds the original DAG SHA without editing it. New
APPROX_GEOMETRY_DIAGNOSTIC_AVAILABLE=PASS_DIAGNOSTIC_ONLY resolves no independent
dependency. CALIBRATION_MEASUREMENT_PENDING,
INDEPENDENT_CALIBRATION_VALIDATION_PENDING and METRIC_CALIBRATION_UNAVAILABLE
remain. Ego association/road registration/desired path, blind reviewer, official
CULane and private-domain validation remain blocked. Private input allowed=false.

## Local use

~~~sh
.venv/bin/python -m openpilot.tools.cyber_autotune.approximate_geometry_visualizer
~~~

Open printed 127.0.0.1 URL on the same computer. Height field is blank.
Optional parameter grids require explicit rationale. Symbolic ray mode needs
no height. Refresh resets trial form; nominal prior remains UNKNOWN height.
Static schematic is NOT TO SCALE. Table and original/mapped Euler display are
NON-QUALIFYING. Ctrl-C closes the server. No CDN/remote assets/telemetry/upload.
Future explicit stationary receipt comparison uses --physical-wizard-workspace;
it is not a live calibration or log importer.

## Regression risk and acceptance

- Source conventions and model motion calibration do not supply independent road truth.
  Physical measurement/spec/source assertions are not authenticated by content hashes.
- No new metric/controller/reference acceptance thresholds. Algebraic fixtures and
  finite-difference checks test signs/math, not camera accuracy or driving improvement.
- Exact prior/policy/firewalls reject forged/stale receipts. Root/store protections
  are reused for explicit future wizard comparison; no silent overwrites or migration.
- Loopback exact Host/Origin/nonce, bounded JSON, CSP/no-store/fixed routes, source
  guard and immutable asset snapshots reduce accidental data/network exposure.
- Rollback removes new isolated modules/artifacts; old independent contracts intact.
- Independent read-only review required and completed after source-drift regression fix.
  Physical qualification authority remains unavailable.

## Validation method and actual results

Executed commands, environment/source/output/log hashes and final counts are in
[validation receipt](approximate-geometry-validation-v1.json).

| Check / stage | Method | Actual result / limits |
| --- | --- | --- |
| TDD / focused | New model/UI, independent admission firewall, drift regression | 32 new tests; expanded105 PASS |
| Source convention / sensitivity | Matrix inverse, literal pure-angle signs, coupled Euler, known-ray scaling; independent finite difference review | PASS mathematical checks, no measured camera truth |
| Browser | Existing Chrome154/Playwright, actual loopback | Blank height, symbolic mode,48 TEST_ONLY rows, refresh UNKNOWN, no errors/external requests, server shutdown PASS |
| Full AutoTune / SCons / Ruff / syntax / publication / privacy / diff | Required prepared environment | Executed outcomes in receipt |
| Physical/private/replay/vehicle | No new data or controller inputs | NOT_RUN; no actual calibration measurement |
| Independent review | Separate read-only reviewer | Source-drift fixed; no outstanding Critical/Important |

## Handoff

IMPLEMENTED diagnostic infrastructure. PENDING EVIDENCE: actual physical height,
camera/sensor/unit/vehicle identity, ground/mount/orientation metrology and
independent calibration validation. No justified coarse height or metric budget.

BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
New logical commits follow baseline; recorded in branch history.
No vehicle application authorization or private execution exception is created.
