# Independent reference blocker dependency plan

## Identity and purpose

- Area: Cyber Validation, offline reference evidence infrastructure.
- Status: IMPLEMENTED software contracts; PENDING EVIDENCE; actual qualification BLOCKED.
- Scope: stationary metadata and known-construction fixtures only; no vehicle applicability
  or activation. feature/cyber-autotune baseline ec1b1e7741adac93675e19cc18d0eef7fcdcb702.
- Patch identity: new reference_infrastructure_readiness.py source SHA and schema/policy SHA bound in published receipts.

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

- Added openpilot/tools/cyber_autotune/reference_infrastructure_readiness.py and corresponding focused tests.
- Integration is offline-only, using existing JSON sealing/durable-storage and ray kernels.
  Alternative automatic truth/default calibration/private execution was excluded by evidence requirements.
- No controller state/history/reset/physical delay queue changes. New metadata functions
  are stateless; explicitly versioned immutable stores have no silent overwrite/migration.
- Original production controller, comparator, A3 rejection, candidate history and existing
  evidence artifacts are unchanged. No CAN/Params/CarController/device/network write.
- Maintenance: source/schema pins intentionally invalidate stale receipts; changes require
  versioned experiments rather than silently accepting old provenance.

### IMPLEMENTED
[NEXT_BLOCKER_PLAN_V2_REFERENCE_INFRASTRUCTURE](independent-reference-next-blocker-plan-v2.json)
is a new deterministic snapshot; old NEXT_BLOCKER_PLAN_V1 is byte-identical and hash-pinned.
All old blockers remain. New contracts count as PASS_STRUCTURAL_ONLY, never evidence PASS.
Exact-current validation prevents resealed status/private/reference promotion.
DAG sorting rejects unknown dependencies/cycles.

Critical path: independent physical observation -> independent calibration validation ->
metric calibration and projection budget -> road registration -> independent lane-center
reference. Parallel prerequisites: ego identity/association validation, desired-path
provenance, uninformed blind reviewer, official CULane benchmark and justified detector
qualification. A supplied structural measurement alone advances none of these truth gates.

Actual states are calibration PENDING, ego VALIDATION_PENDING, road BLOCKED,
private PROPOSED_NOT_RUN, reference UNAVAILABLE. Future state names are design vocabulary,
not implemented/authorized transitions. No source data was opened to create readiness.
Next work is actual independent physical instrument/target evidence plus validators;
in parallel acquire ego-identity GT/road survey/center-definition provenance.
A private diagnostic execution would require a separate explicitly authorized increment,
manifest/privacy executor and nonqualifying contract; there is no automatic permission.

### Label-completeness audit
[New metadata audit](comma10k-label-completeness-dependency-v1.json) binds old provenance.
Of2000 imgs2 masks,1400 share the identical all-undrivable blob;601 unique blobs are
consistent with these counts. The original119 subset includes13 such shared masks
with zero pred-to-GT samples. Identical bytes do not independently verify that lanes
are absent; imgs2 completeness provenance remains unavailable. No image was reopened,
no frame filtered and no historical metric invalidated.

### PENDING EVIDENCE / BLOCKED
Retained: CULane official reproduction/access, blind reviewer, comma10k ego identity,
label completeness, PUBLIC_PIXEL_QUALIFICATION_THRESHOLD_UNJUSTIFIED, independent
extrinsics/calibration, road registration, desired-path reference and private human
validation. Historical full/assisted review completion remains supporting diagnostic:
11888 full; assisted labels29/29; AI concordance18/29 is not independent AI accuracy.
No new acceptance threshold, independent label or private domain validation is invented.

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
