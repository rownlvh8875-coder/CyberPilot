# Physical calibration field wizard

## Identity and purpose

- Area: Cyber Validation / local offline tooling.
- IMPLEMENTED software workflow; actual CALIBRATION_MEASUREMENT_PENDING.
- Branch feature/cyber-autotune; fetched/equal/clean baseline
  926b86e0de1120fe195a1648fc02eb1a3a985e21. New source identity is bound in the
  [validation receipt](physical-calibration-wizard-validation-v1.json).
- Concrete use: stationary human measurement entry, positive uncertainty and provenance,
  preview, editable draft, immutable structural admission. No measured numbers this increment.

## Original references

- https://github.com/rownlvh8875-coder/CyberPilot, branch/baseline above; repository
  licensing retained. No external model, solver, calibration library or new dependency.
- Reuse unchanged camera_calibration_evidence.py, lane_public_storage.py and original
  lane-reference-independent-physical-calibration.md. Static camera/hardware source
  hashes and exact mici/sensor mapping come from the existing validator.
- Call flow: local browser explicit fields/attachments → draft mapping → authoritative
  c.intrinsics/c.admit → prepared local package → ImmutableCalibrationStore → final marker.
- Python3.12.13 existing WSL environment; browser uses bundled Playwright and installed
  Chrome only for validation. Existing submodule gitlinks remain byte-identical.

## Changes and expected effect

- physical_calibration_wizard.py owns blank drafts, explicit unit conversion,
  tier/instrument compatibility, observation/evidence binding and crash recovery.
- physical_calibration_wizard_ui.py serves fixed routes on 127.0.0.1, exact Host/Origin
  and nonce for mutations, bounded payloads, no-store/CSP and quiet request logging.
- physical_calibration_assets contains local HTML/CSS/JS. Eight stages cover device,
  position, angles, survey targets, ground/distortion, static source, attachments, preview.
- [Field guide](physical-calibration-field-guide.md) follows actual measurement order.
  Printable local checkerboard is nominal-only; printed geometry requires remeasurement.
- Existing validators remain authoritative. The form adds explicit completeness guards,
  never relaxes admission or supplies fake physical defaults. No production caller added.

### Data flow and identity

Raw entered degrees and bounds are frozen alongside converted radians in the local
submission. Rz(yaw)Ry(pitch)Rx(roll), RH vehicle X forward/Y left/Z up, optical
X right/Y down/Z forward and surveyed datum remain unchanged.
Each observation requires explicit value/unit, positive absolute bound, method/source,
instrument type/resolution/unit, independent evidence hashes and uncertainty review.
Typed instruments reject phone/informal claims, wrong dimensions/tier and missing
target geometry even when only one observation uses a surveyed target method.

Static intrinsics are explicitly selected pinned source values, not measured intrinsics.
Per-unit uncertainty is still required. Distortion UNKNOWN and missing ground survey
remain pending; residual/ground zero-centered bound definitions are not zero-error truth.

Tool SHA binds model/UI Python, all three assets and authoritative validator identity.
Sessions refuse live source drift and silent migration. Attachments use content-derived
opaque ID/SHA/byte size only; chosen filename is not transmitted. Binary storage is
local/private, outside repository, owner-only; no private comma4 inputs are discovered.

### Persistence and boundaries

Draft is atomically editable until prepared admission; admitted snapshots are immutable.
Prepared package is durable before existing store admission, final marker last.
Interrupted admission recovers only the same validated package. Source/config bindings,
root inode/resolved path, no-follow reads, reserved-file symlinks, evidence hash/index,
writer lease and atomic fsync/rename reject stale/conflicting/corrupt artifacts.
This is a local evidence tool, not a sandbox against a privileged filesystem attacker.

Transport limits are 1 MiB JSON and 32 MiB selected attachment, 5 s socket timeout:
resource limits, not measurement/performance thresholds. No hidden numeric defaults,
automatic calibration/model import, physical delay queue, profile/controller writes,
CAN/Params/CarController/device access, external asset/cloud request or upload.
Production controller, comparator, candidate history and A3 rejection are unchanged.

PUBLIC SUMMARY is a hash/status allowlist. LOCAL EVIDENCE package retains explicit
values and original input. Attachment binaries remain local; JSON export does not
embed them. Opaque input IDs/notes are local, omitted from public summary.
No actual calibration submission is published. Numerical browser/unit fixtures are TEST_ONLY.

## Regression risk and acceptance

- Structural/declaration admission cannot verify measurement accuracy or independence.
  Missing ground/distortion/uncertainty/metrology evidence remains blocked.
- Exact unit/tier/hash/state rules derive from the existing protocol and this frozen form;
  no detector/controller qualification threshold is added.
- Rejected inputs, source drift, duplicate/conflicting admissions, symlink/root substitution
  and interrupted storage are covered by focused tests. Browser exercises all eight stages.
- Reset means a separate versioned local session; existing admitted history is retained.
- Rollback removes isolated new wizard files; all baseline contracts/results stay intact.
- Separate read-only reviewer checks safety/privacy/immutability; physical validation and
  vehicle promotion authority are not supplied by this code review.

## Validation method and actual results

Executed checks and log/source hashes are in the
[validation receipt](physical-calibration-wizard-validation-v1.json).

| Check / stage | Method | Actual result and limits |
| --- | --- | --- |
| TDD / focused | Explicit failed tests, model/UI/recovery guards | 40 new tests PASS |
| Actual browser | Existing Playwright + Chrome, loopback, TEST_ONLY form | 8 stages, invalid preflight, save/reload, attachment, preview/admission/immutability PASS; no JS errors, external requests or failed resources; server closed |
| Full regression / build | tools/test_runner.py -j2, SCons with .venv PATH | 1399/1399 PASS; SCons 100% PASS; log SHA/exit codes in receipt |
| Ruff / syntax / publication / privacy / diff | New source/assets and full AutoTune checks | Actual outcomes in final receipt |
| Independent review | Separate read-only reviewer | No outstanding Critical/Important findings after regression fixes |
| Replay / simulation / shadow | Production paths unchanged; no real inputs | NOT_RUN; unit numerical values are constructed TEST_ONLY |

## Handoff

- Verified software effect: explicit local entry persists; incomplete/stale inputs and inputs
  declaring forbidden model/candidate sources cannot produce admitted evidence;
  undisclosed contamination cannot be certified absent; structural admission cannot mark independent
  validation complete.
- PENDING EVIDENCE: actual camera/device survey, independent physical/metrology values,
  ground/distortion bound, target survey and independent validation.
- BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Blind reviewer and official CULane
  blockers remain; unchanged blocker DAG has no newly satisfied physical evidence.
- NOT RUN: real calibration measurement, private comma4 input, sealed reference,
  actual vehicle qualification. Readiness is bound in
  [pending state](physical-calibration-wizard-pending-v1.json).
- Logical commits follow the baseline; recorded in Git history. No vehicle application
  authorization: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
