# Physical optical-center height observation

## Identity and purpose

Cyber Validation/UI; implemented, formal physical evidence incomplete.
The user reports a repeated physical ground-to-comma4 road-camera optical-center
height mean of **1.385 m**. Store exactly that observation without fabricating
individual repeats, their count, timestamp, instrument, operator, survey method,
ground validation, or a conservative uncertainty.

Branch: feature/cyber-autotune; baseline
99670290150be22de2bd65c88490d7d263ece175. The patch and validation receipt bind
the new source files; no detector or holdout generation is rerun.

## Original references

Repository: https://github.com/rownlvh8875-coder/CyberPilot,
verified branch/baseline above; existing repository license/attribution applies.
The physical source is the current user report, separately hashed in the
observation receipt. No new third-party code, dependency, model, or submodule
change.

Call path: user report → physical_height_observation.observation() →
explicit wizard import / diagnostic context / versioned comparison and synthetic
sensitivity derivative. The existing camera_calibration_evidence.admit remains
the authoritative complete-evidence admission layer. It rejects this standalone
observation. physical_projection_uncertainty.report remains unchanged and
requires admitted calibration plus validated pixel registration.

Reuse the existing coarse diagnostic projection and coordinate adapter for
synthetic normalized rays. Do not replace the independent admission schema with
a partially filled observation.

## Changes and expected effect

- physical_height_observation.py: exact user mean, pending metadata, immutable
  receipt construction, pinned historical file identities, diagnostic precedence,
  consistency comparison, additive sensitivity, future target-height comparison,
  and fail-closed readiness.
- Wizard/backend/assets: explicit “load recorded physical mean” action, source
  binding in tool identity and draft note. Blank drafts remain blank. The action
  replaces only the height input, clears stale height uncertainty/method/instrument
  fields, and preserves other draft inputs. No admitted package can be changed.
- New JSON receipts: observation, mixed-provenance context, coarse consistency,
  synthetic sensitivity derivative and additive readiness. Existing files stay
  byte-identical. New versions are required for later reports.
- New tests cover provenance, pending values, strict admission, unchanged
  historical evidence, source drift, diagnostic determinism, wizard persistence
  and admitted immutability.

**1.385 m is a physical observation with uncertainty pending.** It outranks the
1.40 m coarse prior for an explicitly selected diagnostic context, but does not
become an admitted calibration. Per-unit device identity is still unverified.
The previous 1.40 m prior and 1.33–1.47 m grid remain historical diagnostics.
The observed mean differs from the coarse nominal by **−0.015 m** and falls inside
that historical range. This is no validation of either the prior or its range.

Mount lateral remains approximately 0 m by user declaration. Roll 0°, pitch 2.34°
and yaw 0.2° remain **MODEL_DERIVED_EXTRINSICS_PRIOR**, with the existing explicit
frame adapter. Only the height component is physically observed. Height uncertainty
is null; the diagnostic sweep is not a measurement uncertainty.

The new sensitivity derivative adds 1.385 m at the four historical fixed synthetic
normalized-ray pairs, anchored to the original 1.40 m nominal at 5/10/20/30 m.
It copies the original nominal rows from the pinned historical artifact and
computes only the new rows. Holding those rays fixed, forward/lateral ray scales
change by the ratio 1.385/1.40. These are assumed flat-ground/pinhole algebraic
diagnostics with model-derived orientation, not private pixel projection, detector
meter error, a continuous bound, or a physical uncertainty budget. Actual
detector meter error and total conservative uncertainty remain null.

Future target_height_consistency compares a supplied solved height to 1.385 m;
it never fits/constrains the solver to this mean. No discrepancy threshold is
invented. A caller must declare a diagnostic comparison bound before a
HEIGHT_POSE_CONSISTENCY_WARNING can be generated. It is not a physical uncertainty
or automatic admission/rejection criterion. No target solve was run here.

## Regression risk and acceptance

Risks: reusing an old height bound, silently changing draft values, treating the
physical mean as full independent pose, source drift, or conflating synthetic
meter-valued algebra with measured detector error. Acceptance requires exact
mean/provenance preservation, null unprovided metadata, unchanged old artifacts,
explicit import, no strict admission or meter promotion, and source-drift
rejection. No detector threshold or qualification threshold is added.

The observation is not a complete measurement submission. Users must supply
actual uncertainty, instrument/method and supporting evidence; pitch/roll/yaw,
ground, intrinsics/distortion and target validation remain separately pending.
No private raw data, images, lane coordinates, paths, or timestamps are read or
published. Historical private assisted holdout outputs are unchanged.

Rollback: revert this additive increment; existing coarse results and authoritative
admission remain available. Existing wizard roots are never silently migrated:
the new tool identity requires a new versioned local workspace. Retain old
admitted packages as history. Required independent source review found a runtime
source-drift identity defect; a failing regression reproduced it and an executed
source hash guard corrected it.

## Validation method and actual results

See physical-height-validation-v1.json for exact source/receipt/log hashes,
commands, environment and final local counts. Browser tests use a new TEST_ONLY
workspace without actual calibration admission or private route inputs.

| Check / stage | Method | Scope / limitation |
| --- | --- | --- |
| Focused/regression/build | unittest, AutoTune + controls, Ruff, compileall, SCons, diff | Final results in validation receipt |
| Browser | Chromium desktop and mobile DPR2; explicit load, empty uncertainty, save/reload, eight stages, pending preflight, process restart | Synthetic form only; zero external requests/JS errors; clean shutdown |
| Publication/privacy/authority | publication checker and changed-file audit | Only authorized height and redacted receipts; historical files/controllers unchanged |
| Replay | Existing 16 focused replay tests | No replay reference changes |
| Simulation / closed loop | NOT RUN | No controller/candidate change |
| Shadow / vehicle | NOT RUN | No runtime or actuator authority |
| GitHub Actions | New commit run checked after push | CI result reported in final handoff |

## Handoff

Implemented: physical observation recorded and higher diagnostic precedence,
wizard explicit import with pending uncertainty, versioned diagnostics.
Actual complete calibration submissions: **0**. Independent validation: **NOT RUN**.

PHYSICAL_HEIGHT_OBSERVATION_AVAILABLE coexists with
CALIBRATION_UNCERTAINTY_PENDING,
INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE and INDEPENDENT_REFERENCE_UNAVAILABLE.
Actual registration remains PIXEL_GEOMETRY_REGISTRATION_PARTIAL /
STRUCTURAL_ONLY; height alone cannot resolve it.

Next: obtain actual conservative height uncertainty and measurement provenance,
independent pose/target validation, intrinsics/distortion applicability and
validated qcamera mapping/residual. No automatic uncertainty values or additional
physical measurements have been generated.

Sealed reference: NOT_GENERATED.
Vehicle: NOT_READY, REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.
No new private inputs opened this increment. Vehicle application is not authorized.
