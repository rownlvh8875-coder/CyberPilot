# Public lane-reference feasibility and groundwork implementation plan

Goal: audit the proposed public-GT → external detector → private holdout → calibration → sealed reference chain without inventing independent truth.
Architecture: source/config/weight metadata freeze first; explicit missing-evidence receipts; pure pixel localization and ray/Jacobian diagnostics. Existing reference admission remains untouched. This increment does not implement inference, private frame reading or a reference producer while promotion thresholds, independent calibration and road/desired-path evidence remain unavailable.
Tech stack: existing Python/NumPy; no production dependencies or networking.

## Scope and decisions
- CLRerNet DLA34 non-EMA CULane weight is the first reproduction target, not a selected qualified detector. Fixed roster CLRerNet/CLRNet/UFLDv2; no new detector after results.
- Metadata/tree/PNG-header inspection is not GT semantic evaluation. No public mask pixel decode or private image/log open occurs in this audit.
- A source/config freeze is distinguished from a complete execution freeze. Missing weight/environment hashes stay null, never synthetic placeholders.
- Official benchmark matching settings may be reproduced. They do not justify CyberPilot median/p95/coverage/confidence/metric uncertainty promotion thresholds; undefined thresholds block promotion.
- Pixel lane marking localization is not ego boundary association. Pinhole/Jacobian calculations are diagnostic mathematics, not measured meter accuracy or conservative certified uncertainty.
- Stronger provenance would require a separately sealed manifest referenced by the unchanged exact-key reference JSON. No JSON asserting independent_primary_position_truth is emitted here.

## Task 1: source audit and blocked protocol
- [x] Audit pinned official repositories, pair counts, licenses, preprocessing/confidence, weight bytes and calibration/data provenance; no semantic evaluation.
- [x] Write RED tests for exact protocol/roster/threshold schema, identity mutation, missing evidence, forbidden readiness/vehicle promotion and reject report at existing reference admission.
- [x] Implement lane_reference_qualification.py and frozen policy; generate machine-readable audit/blocker deliverables with original source hashes.
- [x] Reviewer checks metadata claims, independence and threshold justification.

## Task 2: pixel and projection groundwork
- [x] Write RED tests for row/run localization, mask palette/geometry, missing rows, no-GT denominator, invalid predictions, deterministic aggregates, ray domain/Jacobian signs and unknown uncertainty.
- [x] Implement lane_marking_metrics.py and lane_projection_diagnostics.py as pure offline functions. No mask interpolation, ego association, temporal carry, calibration substitution or truth promotion.
- [x] Synthetic analytical fixtures only; clearly separate implemented kernels from NOT_RUN public/private accuracy.
- [x] Focused tests; full AutoTune; Ruff/syntax/publication/authority/privacy/diff; SCons; independent review fixes; feature record; commit/push/local-origin equality/clean.

## Review focus
Source declaration vs execution freeze; weight/hash/environment absence; coverage denominators; metric/pixel units; Jacobian coordinate convention; private sample freeze and no-leak claims must never become authentication. Reject malformed or rehashed unsupported protocol. Frozen rule must not be relaxed after actual results. No model/candidate path input accepted.
