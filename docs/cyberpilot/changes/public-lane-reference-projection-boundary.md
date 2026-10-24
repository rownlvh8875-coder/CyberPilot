# Lane marking metrics and camera projection independence boundary

## Identity and purpose
Cyber Validation / AutoTune; IMPLEMENTED pure offline diagnostics, source/projection reviewed.
Purpose: prepare deterministic pixel localization and camera-ground sensitivity mathematics while retaining unavailable calibration/GT/error budget. Baseline0673adeee on feature/cyber-autotune. This increment does not supply metric lane reference or modify production behavior.

## Original references
- comma10k source/config/weight roster and exact public hashes are in public-lane-reference-source-audit.json and public_lane_reference_policy.json.
- Camera/hardware/model/calibration/reference files are unchanged and individually SHA-bound in public-lane-reference-calibration-audit.json at the stated baseline. CameraConfig has nominal width/height/focal and centered K; no distortion, mount survey or per-unit uncertainty.
- Pinned hardware.py identifies mici=comma4. camera.py admits ar0231/ox03c10 narrow1928x1208 f2648 cx964 cy604, or os04c10 narrow1344x760 f1141.5 cx672 cy380. Device name alone does not select a sensor. Existing qcamera526x330 pixels need an explicit crop/resize transform.
- Neural model pose/road_transform/wide_from_device_euler → cameraOdometry (fill_model_msg.py177-192) → calibrationd pitch/yaw/height/wide rotation (203-247) → extrinsicsCalibration → model warp (modeld367-374). Roll zero/default height1.22m and internal convergence status are not independent observations.
- External dependency NumPy already present; no third-party detector/projection implementation copied, no license change, all submodules unchanged.

## Changes and expected effect
lane_marking_metrics.py accepts exact RGB category2 palette or bool marking masks and explicit original-pixel (x,y-row) samples. Each contiguous row run uses its midpoint; symmetric nearest-run distances report median/p95(linear)/maximum. Coverage denominator is every visible GT run, numerator runs actually containing an explicit detector point. Off-marking/unsupported predictions and missing-row GT runs are separately counted. Empty GT/support yields null distributions and REFERENCE_UNAVAILABLE, not a perfect score.
There is no automatic ego lane association, F1 instance matching, skeleton ambiguity resolution, meter conversion, confidence filtering, temporal fill or polyline sampling adapter. Sampling density and geometry must be prefrozen before cross-detector comparison; raw kernels are not detector scores. A wide stripe's midpoint is a deterministic representation convention, not an annotated ego center.
Aggregate reports verify SHA plus exact schema, count/domain/coverage/status/distribution consistency. This is structural consistency, not execution/pixel authenticity. Invalid/antialiased mask colors are rejected, not canonicalized. MAX_PIXELS6,000,000 is a resource cap covering audited image geometries, not a physical/qualification domain.
lane_projection_diagnostics.py provides explicit optical x-right/y-down/z-forward → road x-forward/y-left/z-up ray intersection and analytical lateral Jacobian, including pixel, focal/principal point, camera height/lateral position and infinitesimal world-axis rotations (radians). Reject nonfinite/nonproper rotations, invalid K, horizon/behind-camera/nonforward intersections. Proper orthogonality tolerance1e-9 and ray-z numerical1e-12 are floating-point guards, not calibration certification.
For camera center C and ray r=R K^-1 p, ground P=C-(Cz/rz)r; lateral Y=Cy-Cz*ry/rz. Thus derivative -Cz*((d ry)*rz-ry*(d rz))/rz². No lens/ground-plane correction is assumed verified.
first_order_budget separates nominal detector and calibration L1 Jacobian contributions only. Projection nonlinear/distortion/ground-model remainder is unknown; projection error and total conservative uncertainty remain null/BLOCKED even with supplied finite local bounds. No claim that first-order sum is a conservative meter error. No measured bounds are assigned in public report.
Aligned, flat, undistorted nominal sensitivity is distance/focal (absolute m/px); reported at5,10,20,30m for both audited focal branches. This is a distance-dependent illustration, not measured accuracy, not a global pixel-to-meter multiplier.
All functions are stateless; no queue/reset/history/fallback. Controller plant still owns its physical delay. Alternatives of reusing live calibration or heuristic pixel detector thresholds were rejected because they do not authenticate independent geometry/error.

## Regression risk and acceptance
- Jacobian coordinate/sign convention is tested against finite differences for pixel, intrinsics and world rotations. y-left is not copied into reference left<center<right arrays without a separate convention transform.
- Stock strict curvature_yaw_reference_input exact keys remain unchanged; richer provenance must live in a separately sealed reviewed manifest, bound through existing manifest/review/source SHA. encode_reference_document is only a serializer; calling it does not qualify detector estimates.
- Existing reference additionally requires independent desired-path series, common time-registered road frame, independent geometry sources, reviewed half-width and all16strata. A camera-relative lane pair alone does not provide them or a shared road map for three counterfactual trajectories.
- REAL_GROUND_TRUTH_QUALIFIED and vehicle acceptance are unavailable. Model-derived live extrinsics retain dependence even when detector is external.
- Rollback removes new pure diagnostics and associated tests/receipts. Independent-review authority is needed for future calibration, error budget and truthful reference role, not automatically granted by this implementation.

## Validation method and actual results
| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression / build | RED missing modules; RED invalid boolean/rehash/background-support/unknown-Jacobian cases; focused pytest and full AutoTune; SCons | New3test modules; no private data | Focused27/27 PASS with21 subtests; full1009/1009 PASS281.87s; SCons100% PASS; Ruff/py_compile/publication/authority/privacy/diff PASS |
| Replay vs baseline | Exact source SHA and schema preservation; old blocked report cannot decode as strict reference JSON | Existing reference admission unchanged | Boundary preserved; no public detector benchmark executed |
| Simulation / closed loop | Hand-constructed masks and pinhole geometry, finite-difference oracles | Analytical tests, not dataset measurements | Pixel/rotation/intrinsic derivative and unavailable semantics PASS |
| Shadow | Not applicable: pure calculations/report, no actuator or live process path | No runtime hooks/writes/network | No vehicle use |

## Handoff
IMPLEMENTED: deterministic marking-only metrics, ray/Jacobian diagnostics and calibration/admission provenance.
SYNTHETIC SCREENING: mathematical fixtures only; no public/private measured detector accuracy, domain gap or meter error.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Private sensor identity, independent height/orientation/distortion uncertainties, conservative remainder, road registration and independent desired path remain unavailable in this chain.
REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Next freeze a justified protocol and complete public reproduction, then separately human holdout/calibration review; no reference JSON asserting independent_primary_position_truth emitted, no production controller/comparator/A3 changes.
