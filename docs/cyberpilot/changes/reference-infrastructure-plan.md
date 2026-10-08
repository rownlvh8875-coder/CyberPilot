# Independent reference infrastructure implementation plan

Goal: prepare physical-measurement admission, geometry contracts and closed
private metadata preparation from ec1b1e7741adac93675e19cc18d0eef7fcdcb702.
The user's full specification supplies design and authority; no approval pause.
No private input locations, image materialization, detector run or real measured
values. Existing evidence, schemas, policies and production paths stay untouched.

Architecture: new isolated offline contracts with strict exact-key/hash/unit/
provenance admission; existing ray/Jacobian kernel is unchanged. Numerical
geometry outputs are known-by-construction diagnostics only. Real metric
registration/centerline gates remain blocked by independently validated
calibration, ego association, projection budget, road/time registration and
other reference prerequisites. Structural admission is not metrology validation.

Task1 — camera_calibration_evidence.py + tests:
- TDD uncertainty/provenance/unit/device/source/nonfinite rejection.
- STATIC_INTRINSICS freezes actual mici sensor mapping and nominal source SHA;
  distortion is UNKNOWN, not zero. INDEPENDENT_PHYSICAL_EXTRINSICS records
  height/position/Euler radians, absolute uncertainty bounds, instrument/target/
  ground survey/operator hashes, explicit human acknowledgement and independence.
- admit(None) returns PENDING. Separate exact-unit observation fields and
  immutable single-measurement store, rejecting duplicate/conflicting saves.
- projection_budget binds admitted evidence to original Jacobian and5/10/20/30m;
  contributions remain first-order; no certified total without validated remainder.

Task2 — independent_lane_geometry.py + tests:
- TDD independent ego proposal schema/context ambiguity/no single-side filling.
  No nearest-side algorithm or qualification; EGO_PAIR_AVAILABLE is candidate-only.
- Explicit RH vehicle/road x-forward,y-left,z-up, optical x-right,y-down,z-forward.
  Rz(yaw)Ry(pitch)Rx(roll) mapping; surveyed road yaw/origin with uncertainty.
- Known-by-construction ray→ground→vehicle→road tests, straight/curved/symmetric
  cases and sign/axis/unit/origin negatives. Real meter registration requires
  calibration + independently validated ego association + certified budget.
- Exact-common-longitudinal midpoint only; no missing-side extrapolation,
  smoothing, long-gap filling or planner assistance. Lane center ≠ optimal path.

Task3 — private_lane_diagnostic_preparation.py + tests:
- Exact completed-public CLRerNet identity source/weight/config/environment/
  preprocessing/postprocessing pin. No detector execution or private opener API.
- Metadata-only sampling policy caller supplies justified deterministic interval/
  offset and holdout disjoint modular partition; freeze before metadata/image/
  detector exposure; reject content/confidence-based selection.
- Hash/opaque segment/frame ordinal/time metadata only in local manifest;
  publish manifest SHA/count/identity only, not private frame/route hashes, raw
  timestamps, paths, GPS/EXIF. Explicit separate local/private/public dirs checked
  lexically without reading/crawling those dirs.
- Human holdout PENDING, no generated labels; private outputs declare availability/
  geometry stability only, no localization error absent GT or validation promotion.

Task4 — reference_infrastructure_readiness.py + tests:
- Copy immutable existing NEXT_BLOCKER_PLAN_V1 as historical input; bind new
  protocol/pending receipts into a new snapshot, deterministic DAG and exact
  states. No child removed or actual PASS created.
- Independently recheck all-undrivable-mask provenance metadata, no image reads
  or filtering. Label completeness and pixel-threshold blockers remain.
- Calibration→metric calibration→road registration→lane-center; ego validation
  and independent desired-path provenance parallel. Private execution false.

Task5 — actual pending metadata artifacts and six feature records:
- Publish only source/protocol/pending/dependency/validation metadata.
- Source freeze before full tests to avoid source-binding guard rejection.
- Focused/full AutoTune (>1301), Ruff/syntax/publication/privacy/authority/diff/
  SCons and separate read-only reviewer. Fix findings with regression tests.
- Logical commits; normal push; fetch and verify equal local/origin and clean tree.

Review focus: forged physical independence, zero/default unknown uncertainty,
Euler/Jacobian parameterization mismatch, nominal distortion mistaken for
calibrated rays, ego candidate mistaken for truth, sparse-common sampling
concealing gaps, private identity/path publication and implicit execution permits.

Interfaces:
calibration.intrinsics(camera), admit(measurement,intrinsics), validate_admitted,
projection_budget(receipt, localization_bounds), ImmutableCalibrationStore.save.
geometry.ego_contract / assess_pair; known_registration / midpoint_fixture;
registration_gate / lane_center_gate (real evidence remains BLOCKED).
private.freeze_policy / freeze_manifest / publication_summary / human_holdout /
require_execution (always rejects this increment).
readiness.snapshot() (constructs only actual pending receipts) validates graph and exact readiness states.
