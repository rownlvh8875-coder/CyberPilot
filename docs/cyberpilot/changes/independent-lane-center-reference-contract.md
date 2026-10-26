# Independent lane-center reference construction

## Identity and purpose

- Area: Cyber Validation, offline reference evidence infrastructure.
- Status: IMPLEMENTED software contracts; PENDING EVIDENCE; actual qualification BLOCKED.
- Scope: stationary metadata and known-construction fixtures only; no vehicle applicability
  or activation. feature/cyber-autotune baseline ec1b1e7741adac93675e19cc18d0eef7fcdcb702.
- Patch identity: new independent_lane_geometry.py source SHA and schema/policy SHA bound in published receipts.

## Original references

- Repository: https://github.com/rownlvh8875-coder/CyberPilot, feature/cyber-autotune,
  exact baseline above; repository licensing retained, no external detector code copied.
- Existing physical protocol: lane-reference-independent-physical-calibration.md; unchanged.
  Static camera/hardware mapping and analytic lane_projection_diagnostics.py are reused.
- Traced flow: explicit caller metadata -> exact-key/unit/hash validation -> detached
  receipt -> closed readiness gate. No production callers added.
- Existing NumPy/Python3.12 environment; no new packages. Source dependencies are hashed.
  Relevant submodules remain at baseline msgq0e266c1, opendbc4134c0, panda92eb565,
  rednose8671, teleop1aa8, tinygrad9d044; full SHAs remain in Git gitlinks.

## Changes and expected effect

- Added openpilot/tools/cyber_autotune/independent_lane_geometry.py and corresponding focused tests.
- Integration is offline-only, using existing JSON sealing/durable-storage and ray kernels.
  Alternative automatic truth/default calibration/private execution was excluded by evidence requirements.
- No controller state/history/reset/physical delay queue changes. New metadata functions
  are stateless; explicitly versioned immutable stores have no silent overwrite/migration.
- Original production controller, comparator, A3 rejection, candidate history and existing
  evidence artifacts are unchanged. No CAN/Params/CarController/device/network write.
- Maintenance: source/schema pins intentionally invalidate stale receipts; changes require
  versioned experiments rather than silently accepting old provenance.

### IMPLEMENTED
[Centerline contract](independent-lane-center-contract-v1.json) defines
INDEPENDENT_LANE_CENTER_REFERENCE, never optimal driving path or driving ground truth.
Only two independently validated boundaries on identical longitudinal samples may
produce deterministic midpoint points. Road/vehicle y is left-positive: left must be
greater than right on every sample. Smoothing is NONE; there is no tunable hidden path
completion. midpoint_fixture tests numerical construction only, with stable half-sum
arithmetic and explicit caller gap bound; the bound is a TEST_ONLY condition, not a
new real qualification threshold.

Missing one side, mismatched samples, wrong order, insufficient points, excessive
gap, reversed boundaries or nonfinite geometry fail closed; no interpolation, long-gap
bridging, missing-side extrapolation, planner completion or previous-frame carry.
Input hashes, algorithm source and definition bind the fixture result.

### PENDING EVIDENCE / BLOCKED
[lane_center_gate](independent-lane-center-pending-v1.json) returns REFERENCE_UNAVAILABLE
with points null and sealed_reference false. Real road registration, valid left/right
identity, coverage/domain budget and separately reviewed center-reference provenance
are missing. A lane midpoint is not a planned maneuver through a merge/intersection
and cannot claim vehicle-optimal path. DESIRED_PATH_REFERENCE_UNAVAILABLE remains:
a future geometric-center definition must be separately reviewed as the evaluation
reference with acknowledged limits, not borrowed from modelV2/planner/candidate output.
No curvature_yaw_reference_input JSON was generated or admitted.

## Regression risk and acceptance

- Structural completeness does not verify external measurement truth or independence.
  Unit/geometry/hash checks are mathematical acceptance only; no new performance threshold.
- Numerical fixtures are TEST_ONLY/KNOWN_BY_CONSTRUCTION_ONLY and have no promotion route.
- Current source/schema/receipt identity protects against caller mutation and stale input.
  Rollback removes these isolated new modules/artifacts; baseline production is untouched.
- Independent read-only reviewer required; actual promotion requires independent observed
  evidence and future declared validators. No current authority grants vehicle activation.

## Validation method and actual results

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| TDD / focused | pytest four new modules, then related projection/qualification/assisted suites | reference-infrastructure-validation-v1.json | New58/58; expanded98 plus33 subtests PASS |
| Unit / regression / build | tools/test_runner.py -j2; Ruff; py_compile; publication; diff; authority/privacy; SCons -j2 with .venv PATH | [Final validation receipt](reference-infrastructure-validation-v1.json) | Executed results and source/log hashes in receipt |
| Replay vs baseline | No changes to existing native/candidate paths | Historical evidence retained | No new vehicle/performance qualification |
| Simulation / closed loop | Known camera/road/center geometry where applicable | Focused numerical fixtures | Mathematical checking only; no measured calibration |
| Shadow / actual data | No private, physical measurement or new raw detector inputs | Pending receipts | NOT_RUN; no controller actuation |
| Review / browser | Separate read-only reviewer; no UI changes | Final validation receipt | Review fixes tested; browser NOT_RERUN_NO_UI_CHANGE |

## Handoff

- Verified effect: malformed/contaminated/stale inputs fail closed; pending evidence does not promote.
- BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
- NOT RUN: real physical measurements, independent ego/road validation, private diagnostic/holdout.
- Next verification: obtain independent measured artifacts and legitimate validation evidence;
  software schema admission alone cannot resolve truth blockers.
- Commits: logical feature commits following baseline, recorded in branch Git history.
- VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
  Vehicle application is not authorized.
