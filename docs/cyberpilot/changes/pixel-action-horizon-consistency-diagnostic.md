# Pixel action-horizon consistency diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: descriptive software diagnostic only; no vehicle qualification or runtime use.
- Purpose: compare an already-computed model-lane action-horizon convergence
  observation with caller-owned image-derived lane-relative offset and slope.
- Scope: immutable upstream diagnostic state plus two finite pixel-reference
  scalars. The module does not decode images, detect lanes, estimate calibration
  or latency, select frames, tune parameters, generate curvature, or issue
  vehicle commands.
- Branch / baseline: feature/cyber-autotune from
  b402fbef6ed220e3060732ade3c4d656769e3255.

## Motivation

Private read-only cross-checking first showed that the original low-speed
pixel-valid representative frames could not directly validate the action
horizon: their latency-aware action points projected below the qcamera image.
No image threshold was relaxed to force those frames into the test.

A new fixed frame set was therefore selected before pixel decoding using only
logged control/model/calibration metadata and action-horizon visibility. The
repository pixel detector was then applied without backfill after detector
failure. Every detector-valid frame in that fixed cross-check agreed between
model-lane and image-derived references on both local convergence state and the
sign of path offset at the action horizon. The public consistency primitive does
not propagate the upstream recenter outcome because that boolean cannot be
independently reconstructed from ActionHorizonConvergenceObservation alone.

This supports a bounded consistency statement only. The image-derived lane
midpoint is not surveyed lane-center ground truth, the projected path remains a
model output, and the sample is not sufficient for vehicle qualification.

## Implementation

- Added openpilot/tools/cyber_autotune/pixel_action_horizon_consistency.py.
- observe_pixel_action_horizon_consistency():
  - accepts only an already-valid DESCRIPTIVE_ONLY
    ActionHorizonConvergenceObservation;
  - revalidates upstream safety/readiness fields, exact convergence identities,
    offset-side state and hidden turn-normalization consistency;
  - accepts signed finite pixel lane-fraction offset and its longitudinal slope;
  - classifies pixel local state as CENTER, FLAT, CONVERGING or DIVERGING using
    the exact coordinate-invariant rule offset * slope < 0;
  - reports exact model/pixel convergence-state agreement;
  - reports model/pixel offset-sign agreement when both offsets are non-zero;
  - fails closed on non-finite inputs or derived multiplication overflow.
- Pixel offset sign is caller-defined in image-x coordinates compatible with
  model/calibrated lateral +right. The module performs no calibration or
  projection itself.
- No epsilon, magnitude threshold, acceptance gate, tuning value or runtime hook
  is introduced.
- Output is frozen and hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.

## TDD and risk coverage

Synthetic public-safe tests cover:

- matching convergence and divergence;
- explicit disagreement without promotion;
- offset-sign agreement and zero-offset indeterminacy;
- CENTER and FLAT exact states;
- mirrored lateral coordinate conventions;
- non-finite pixel inputs and finite-input multiplication overflow;
- blocked and forged upstream convergence observations;
- forged turn-normalization, convergence and authority fields;
- immutable non-authoritative output.

TDD red phase produced 10/10 expected failures before the module existed.

## Evidence boundary

Private route/image analysis is descriptive motivation only and is not a
software acceptance fixture. No route identifier, raw image, raw log, location,
private path, action-horizon selection fixture or private-derived numeric test
vector is included in this change.

The image-derived lane reference is independent of model lane-line geometry but
is not surveyed lane-center truth. Camera calibration and the fixed straight-line
lower-ROI detector can bias the supplied pixel offset/slope. Agreement therefore
does not prove model causality or authorize a steering correction.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 10/10 expected failures before implementation |
| Pixel-action-horizon + action-horizon + action-geometry + recenter + pixel-reference/path-observer targeted tests | 66/66 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 925/925 PASS in 217.94 s |
| Native SCons build | PASS; existing non-fatal PWD warning only |
| Default verified-public suite | 1832 passed / 42 skipped / 1 xfailed / 0 failed in 329.59 s |
| Private predeclared pixel/action-horizon cross-check | 11 fixed frames; detector PASS 6, fail-closed 5; comparable 6/6 matched convergence state and offset sign |

The private cross-check first attempted the existing pixel-valid representative
frames and found that their low-speed action horizons projected below qcamera.
A new visibility-qualified set was therefore locked before pixel decoding using
only model/control/calibration metadata. Detector failures were not backfilled.

The 6/6 agreement result is descriptive evidence, not a statistical acceptance
rate. Five of eleven predeclared frames were rejected by the unchanged public
pixel detector, and the image-derived midpoint remains an imperfect independent
reference.

Final review found one integrity issue before publication: the first draft
propagated the upstream recentered boolean even though this primitive cannot
independently reconstruct it. That field was removed from the output before the
final regression gates. No remaining Critical or Important issue was found.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
