# Stationary target capture and distance-dependent uncertainty

## Identity and purpose

Cyber Validation/local tooling. IMPLEMENTED; actual physical measurements NOT_RUN.
Branch feature/cyber-autotune; baseline6da307858. No detector/controller/profile/runtime changes.
Frozen60 assisted reference,44 unchanged/16 modified decisions, predictions/matching/evaluation unchanged.

## Original references

Reuse camera_calibration_evidence.py, existing physical wizard/protocol,
lane_projection_diagnostics.py and final assisted aggregate. Static camera source SHA:
1de3f9e6147f28195c71673ae5c8ec38e65ede997ac98d2e1e3b114eda873ec4.
Hardware source SHA:d357b90f878ef7b8ea1df5a537cdf986df2243bc4b20b37c7ed88175020cadd8.
Submodule gitlinks and licenses unchanged. No copied solver source/new dependencies.

Normalized planar DLT → homography scale → SVD proper rotation → surveyed vehicle transform.
This is a NumPy implementation, not an OpenCV reproduction.
[OpenCV pose documentation](https://docs.opencv.org/4.4.0/d9/d0c/group__calib3d.html) describes
multiple planar pose solutions; [calibration tutorial](https://docs.opencv.org/5.0/main_modules/calib.html)
uses several views for intrinsic calibration. Single fit never establishes independent validation.

## Changes and expected effect

- stationary_target_calibration.py: six observed labeled corners, measured spans and surveyed
  target transform/bounds; repeated height observations; residual/conditioning/source-bound pose
  candidate; distinct-capture comparison; private crash-safe content-addressed store.
- stationary_target_ui.py and stationary_target_assets: separate responsive loopback-only
  raw PNG import/marking, blank physical fields, drafts/reload, preview, immutable local capture/export.
  Existing wizard and admission identities/contracts unchanged.
- physical_projection_uncertainty.py: frozen assisted quantiles, exact admitted calibration gate,
  explicit road/annotation bounds and evidenced source-camera affine pixel mapping;
  distances5/10/15/20/25/30m, first-order terms, nonlinear probes and interval enclosure.
- New synthetic tests and human field guide.

Flow: explicit raw PNG + human survey fields → capture validation → pinhole pose candidate →
immutable local package. Existing authoritative physical admission remains separate.
No device capture, CAN/Params/CarController use, private log crawl or actual private image opening.
Browser uses constructed TEST_ONLY image, not a private frame.
All real measurements, target solves and meter diagnostics remain NOT_RUN.

Vehicle X forward/Y left/Z up; optical X right/Y down/Z forward; existing Rz Ry Rx convention.
Board x right/y down/normal forward. Six observed points are top/middle/bottom left/right
inner corners; measured spans6 horizontal/4 vertical squares. Printed nominal size is not truth.
No synthesized/interpolated corner observations.

## Regression risk and predeclared gates

ONE_SHOT_PHYSICAL_CALIBRATION_V1 is source-bound before actual data exists.
Finite inputs, exact sensor/source/original resolution, positive uncertainty bounds,
nondegenerate DLT/pose numerical rank, forward-facing optical axis and observed height consistency
are necessary gates. Maximum reprojection residual≤sqrt(2)×declared per-axis corner bound follows
two-dimensional observation bounds, **not a qualification/metrology acceptance criterion**.
Conditioning/singular values are reported; no arbitrary metrology cutoff is invented.
Weak geometry requires external review. Single-plane ambiguity is unresolved even with exact residual.

STATIC_INTRINSICS_PRIOR differs from INDEPENDENT_TARGET_DERIVED_CANDIDATE_NOT_VALIDATED.
DISTORTION_UNVERIFIED stays explicit: pinhole diagnostics do not assert zero distortion.
Pose uncertainty stays null pending external physical review. Height/placement/ground bounds
must be observed; print size, RMS, instrument resolution and repeat spread do not create bounds.
The target result cannot satisfy the unchanged physical admission schema.

Store root/source/UI/assets/admission/NumPy binding, no-follow reads, fsync/atomic writes,
immutable image/JSON identities and restart revalidation are enforced. Orphan image writes
are not completed captures. Repeated-capture comparison requires distinct image/capture receipts.
TEST_ONLY scope cannot become physical scope, including preview.

## Uncertainty semantics

Historical aggregate receipt:
6e15a7caf6af342696906da5add686d775578844058e6eb8dd0df10dacb14562.
Center median1.937923236290544px,p955.053136006631054px,available44/55,unavailable11 remain unchanged.
All group quantiles/coverage retained; missing group statistics stay null.
No rerun, tuning, re-selection or confidence threshold change.

Source pixels526×330 differ from native intrinsics. PIXEL_GEOMETRY_REGISTRATION_PENDING
requires independent sensor/stream/crop/resize mapping plus residual bound.
Query rays must lie within mapped observed support. Arbitrary rescaling is not calibration.
Actual mapping evidence is absent in this increment.

Numeric meter diagnostics require existing admitted physical evidence, explicit road/annotation
bounds and mapping. TEST_ONLY fixtures are test scoped. Absent actual calibration produces only
PIXEL_TO_METER_PREPARATION_V1 with null numeric rows. Numeric
PRIVATE_ASSISTED_PIXEL_TO_METER_DIAGNOSTIC_V1 is not generated for the real holdout yet.

At each defined nominal ground query, matched detector-equivalent p50/p95 uses lateral Jacobian
and evidenced image scale at fixed y. These are **conditional equivalent quantiles**, not measured
meter residuals at actual lane distances or absolute bounds. Unavailable11 are never filled.
Assisted reference does not become independent after conversion.

Separate contributions: intrinsic fx/fy/cx/cy; height/pitch/roll/yaw/mount;
distortion; pixel mapping; annotation; ground survey; grade/camber/nonplanarity.
Caller must supply physically reviewed bounds, none are invented.
Two full box corners plus all axis endpoints provide deterministic sampled nonlinear residuals.
This sampling is not an exhaustive certificate. Outward-guarded interval arithmetic/trig enclosure
covers the declared pinhole/plane box with conservative dependency overestimation; a triangle
enclosure supplies a loose conditional nonlinear remainder bound.
These model bounds do not certify actual camera/road/annotation assumptions.
Horizon/nonforward/zero-focal crossings fail closed, no clipping/fallback.
Total detector+calibration absolute bound remains null because p95 is not an absolute detector bound.

## Validation method and actual results

Focused35/35 PASS. Exact synthetic pose/sign, degeneration, repeated captures, original image/SHA,
Jacobian finite differences, monotonicity/horizon/interval rounding, missing mapping, unavailable
coverage and p95-vs-bound separation tested. Full regression/build results in companion receipt.

Actual Chrome/Playwright synthetic TEST_ONLY browser PASS:5 stages, blank inputs, missing-value
rejection, original PNG, six original-coordinate observations, undo, save/reload, pose preview,
stale preview invalidation, immutable capture, duplicate rejection,390px responsive layout,
local printable sheet. JS errors0/external requests0/failed resources0; server clean shutdown.
Synthetic handler events exercise subpixel coordinate mapping. Browser success is not physical accuracy.

Independent RED/GREEN fixes: repeated duplicate capture; stale UI preview; reversed-corner
rear-facing pose; cosine interval rounding/outward box; preview scope binding.
Browser found sealed intrinsics float0.0→JS0 SHA mismatch: UI now passes SHA only and server
reconstructs the pinned receipt. Canonical hash validation unchanged. Canvas border offset removed.
Early harness failures (hidden field filling, integer mouse quantization, synthetic event target)
were corrected; no actual acceptance threshold changed.
Final independent review35/35 PASS, no remaining actionable findings.

Replay/simulation/shadow: no control changes, prior evidence preserved.
New actual physical capture, independent validation, real meter/vehicle stages NOT_RUN.

## Handoff

CALIBRATION_TOOL_READY coexists with:
CALIBRATION_MEASUREMENT_PENDING → INDEPENDENT_CALIBRATION_VALIDATION_PENDING →
METRIC_CALIBRATION_UNAVAILABLE → ROAD_REGISTRATION_UNAVAILABLE.
PIXEL_GEOMETRY_REGISTRATION_PENDING, EGO_ASSOCIATION_VALIDATION_PENDING, assisted-human limitation,
second blind reviewer, CULane official benchmark, desired-path evidence and sealed admission
remain separate gates. INDEPENDENT_REFERENCE_UNAVAILABLE stays BLOCKED.

Next: actual stationary survey/capture and independent uncertainty review; no detector tuning.
Single-image draft fit does not solve multi-view ambiguity/intrinsics/distortion validation.
Full survey may take longer than the5–10minute minimal capture checklist.
Existing approximate/coarse compare_physical diagnostics can consume a later admitted physical
receipt; no approximate prior enters this solver.
Rollback removes only new standalone modules/assets/records. Existing authority unchanged.

Actual measurements NONE. Actual pose/meter result NOT_RUN. Sealed reference NOT_GENERATED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
