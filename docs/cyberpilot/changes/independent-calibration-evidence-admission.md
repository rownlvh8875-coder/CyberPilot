# Independent physical calibration evidence admission

## Identity and purpose

- Area: Cyber Validation, offline reference evidence infrastructure.
- Status: IMPLEMENTED software contracts; PENDING EVIDENCE; actual qualification BLOCKED.
- Scope: stationary metadata and known-construction fixtures only; no vehicle applicability
  or activation. feature/cyber-autotune baseline ec1b1e7741adac93675e19cc18d0eef7fcdcb702.
- Patch identity: new camera_calibration_evidence.py source SHA and schema/policy SHA bound in published receipts.

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

- Added openpilot/tools/cyber_autotune/camera_calibration_evidence.py and corresponding focused tests.
- Integration is offline-only, using existing JSON sealing/durable-storage and ray kernels.
  Alternative automatic truth/default calibration/private execution was excluded by evidence requirements.
- No controller state/history/reset/physical delay queue changes. New metadata functions
  are stateless; explicitly versioned immutable stores have no silent overwrite/migration.
- Original production controller, comparator, A3 rejection, candidate history and existing
  evidence artifacts are unchanged. No CAN/Params/CarController/device/network write.
- Maintenance: source/schema pins intentionally invalidate stale receipts; changes require
  versioned experiments rather than silently accepting old provenance.

### IMPLEMENTED
Existing stationary physical protocol is reused without changing it. Physical measurement
metadata must explicitly identify device, actual sensor, optical-center mounting reference,
UTC observation time, opaque operator, survey method and source/instrument hashes. Each
observation separates value, exact unit, method/provenance and a positive independently
reviewed ABSOLUTE_BOUND. Height and mounting x/y use meters; pitch/roll/yaw use radians.
Nominal focal/principal point values use pixels, STATIC_INTRINSICS provenance, and separately
reviewed uncertainty. No zero uncertainty, quantile-to-bound substitution or implicit unit conversion.

API: intrinsics(camera) pins static source/mapping; admit(None) produces PENDING;
admit(measurement,intrinsics) admits only structure/declared provenance or returns REJECTED.
validate_admitted reconstructs the exact receipt, rejecting source/device/schema changes.
Receipts detach caller inputs. ImmutableCalibrationStore is an explicit local one-snapshot
store: durable atomic JSON writes, writer lease, no-follow reads, source/schema binding,
and root device/inode/resolved-path checks on each access. Duplicate/conflicting saves
are refused; new measurements require separate versioned stores. It is not an adversarial
filesystem sandbox; real artifact/instrument trust must be reviewed independently.

### PENDING EVIDENCE
The [submission protocol](independent-calibration-submission-protocol-v1.json) has null
actual device/operator/time/values/uncertainties. The [admission receipt](independent-calibration-pending-v1.json)
is CALIBRATION_MEASUREMENT_PENDING. Synthetic TEST_ONLY values live only in tests.
Missing uncertainty/provenance, nonfinite or degenerate geometry, unsupported units,
model/candidate-derived observations, ambiguous method, mismatched hardware/intrinsics,
or conflicting snapshots reject. Accepted metadata never means the measured numbers are true.

STATIC_INTRINSICS binds common/transformations/camera.py and hardware/comma/hardware.py
with full SHA-256, exact mici sensor mapping and resolution. Nominal ar0231/ox03c10 uses
1928x1208/focal2648; os04c10 uses1344x760/focal1141.5. This is hardware nominal source
evidence, not a per-unit calibration. Distortion is UNKNOWN_NOT_ASSUMED_ZERO. The
measurement schema additionally requires independently bounded undistorted residual
and surveyed ground approximation; no distortion fit/correction or physical holdout
was executed. MODEL_DERIVED_EXTRINSICS/live calibration stays inadmissible as physical truth.

### Projection connection
projection_budget binds receipt and caller-provided independent pixel absolute bounds
to existing analytic Jacobian at5/10/20/30m. Separate detector, four intrinsic, height,
pitch, roll, yaw, lateral mounting, ground-plane and distortion terms use the actual
Euler derivative axes RzRyRx. Central finite differences independently check nonzero
Euler coupling. A public p95 is not an absolute bound and cannot populate this budget.
First-order subtotal is diagnostic. Nonlinear projection remainder and total conservative
uncertainty stay null even for a structurally admitted measurement. Pending has all
terms null; [pending budget](independent-projection-budget-pending-v1.json) certifies nothing.
Independent metrology, road-domain ground validation and bounded remainder remain BLOCKED.

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
