# Road-frame registration and coordinate contract

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
[Real registration gate](independent-road-registration-pending-v1.json) is BLOCKED.
Structural calibration admission is insufficient: independent metric metrology,
ego-association validation, projection remainder and surveyed road/time registration
must exist. Current implementation has no route to a real meter reference.

known_registration is explicitly KNOWN_BY_CONSTRUCTION_ONLY. It checks:
original top-left image u-right/v-down pixels -> dimensionless optical ray with z=1
(not a unit-length ray) -> camera optical x-right/y-down/z-forward ->
ground intersection -> vehicle x-forward/y-left/z-up ->
road-relative yaw/origin transform. All frames are right handed.
Camera rotation is Rz(yaw)Ry(pitch)Rx(roll) times pinned optical/vehicle basis.
Angles are radians; positions/ground intersections are meters; rotation is unitless.

Every mathematical transform carries units, origin/axes/convention and source SHA;
road yaw/origin has explicit survey bounds. Ground z=0 is known only by construction,
total physical uncertainty is null. No nominal projection silently becomes a meter
reference. No runtime controller or delay is touched.

Known-fixture tests independently project and register straight/parallel/symmetric
boundaries and left/right curves, pitched/rolled camera and road yaw/origin.
Negative fixtures cover left/right inversion, axis swap/nonforward ray, degrees,
wrong pixel origin/Y convention, out-of-image and horizon/behind geometry.
Coordinate metadata checks cannot prove that a physically supplied proper rotation
actually describes the device; independent survey validation remains necessary.

### PENDING EVIDENCE / BLOCKED
Actual camera extrinsics, road registration/time association and road-plane domain
are absent. Structural transforms and fixture signs are implemented; real registration
is not STRUCTURALLY_READY or VALIDATED. METRIC_CALIBRATION_UNAVAILABLE plus independent
ego identity/validation explicitly precede ROAD_REGISTRATION_UNAVAILABLE.

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
