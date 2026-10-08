# Private pixel diagnostic metadata and privacy preparation

## Identity and purpose

- Area: Cyber Validation, offline reference evidence infrastructure.
- Status: IMPLEMENTED software contracts; PENDING EVIDENCE; actual qualification BLOCKED.
- Scope: stationary metadata and known-construction fixtures only; no vehicle applicability
  or activation. feature/cyber-autotune baseline ec1b1e7741adac93675e19cc18d0eef7fcdcb702.
- Patch identity: new private_lane_diagnostic_preparation.py source SHA and schema/policy SHA bound in published receipts.

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

- Added openpilot/tools/cyber_autotune/private_lane_diagnostic_preparation.py and corresponding focused tests.
- Integration is offline-only, using existing JSON sealing/durable-storage and ray kernels.
  Alternative automatic truth/default calibration/private execution was excluded by evidence requirements.
- No controller state/history/reset/physical delay queue changes. New metadata functions
  are stateless; explicitly versioned immutable stores have no silent overwrite/migration.
- Original production controller, comparator, A3 rejection, candidate history and existing
  evidence artifacts are unchanged. No CAN/Params/CarController/device/network write.
- Maintenance: source/schema pins intentionally invalidate stale receipts; changes require
  versioned experiments rather than silently accepting old provenance.

### IMPLEMENTED
[pending preparation](private-pixel-preparation-pending-v1.json) remains PROPOSED_NOT_RUN,
private_input_allowed=false and execution=NOT_RUN. The unchanged historical design
contract separately retains execution_authorized_this_increment=false.
No private opener/inference API exists; require_execution always refuses this increment.
The existing PRIVATE_PIXEL_DIAGNOSTIC_ONLY_V1 historical contract is unchanged.

freeze_policy requires explicit future interval/offset, holdout modulo/residue and UTC
freeze; no real sampling values are chosen now. freeze_manifest accepts only supplied
pre-existing non-image metadata: opaque route/segment hashes, ordinal, timestamp and
metadata-source SHA. Reject duplicate rows, nonmonotonic segment timestamps, content/
confidence selection or any prior image/output exposure. Policy freezes before inventory,
which freezes before frames/detector results. Deterministic stride and disjoint modular
holdout partition require nonempty diagnostic and holdout sets. These are independence
declarations, not forensic proof; the future executor must enforce access order.

Detector identity is exactly the completed public CLRerNet environment, including source,
weights, config, preprocessing and postprocessing. No private reselection, fine-tuning,
threshold/confidence optimization, ensemble or postprocessing redesign.
Latest completed environment is pinned rather than the interrupted pre-reboot environment.

Local manifest/holdout rows are private. publication_summary uses an aggregate whitelist:
manifest/policy/detector SHA and role counts, no per-frame route hashes, ordinals,
timestamps, paths, GPS or EXIF. Public/private/cache directory separation is lexical
only and accesses no directories; UNC/device/traversal/overlap reject. Actual resolved
no-follow separation must be verified by a future authorized executor. No external
upload, telemetry, production network path or raw repository publication.

### PENDING EVIDENCE / NOT RUN
No real inventory, manifest, sampling policy, storage root or frame was supplied/opened.
Future outputs are PIXEL_DOMAIN_ONLY lane-count/confidence/availability/geometry-stability
diagnostics; without private GT no localization-error-against-truth field is allowed.
The holdout protocol freezes independent samples before inference, contains no labels,
requires original-only uninformed human review, and forbids training use.
Public failure taxonomy is guide context only, not a reason to remove hard frames.

PRIVATE_HUMAN_HOLDOUT_PENDING; qualification/sealed-reference connection is prohibited.
This preparation cannot open inputs even if a caller reseals flags as authorized.

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
