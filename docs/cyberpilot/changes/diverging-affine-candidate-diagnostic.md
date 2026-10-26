# Diverging affine candidate diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: descriptive virtual candidate only; no runtime use or vehicle qualification.
- Purpose: construct minimal affine path-shape candidates only when an already
  observed model path is both turn-inside and locally diverging from the model
  lane center at a caller-owned action horizon.
- Scope: caller-owned PathQualityInput, action-horizon station and requested
  curvature sign. No log loading, latency estimation, model inference, parameter
  search, planner/control integration, Params/CAN/device write or actuator output.
- Branch / baseline: feature/cyber-autotune from
  aa3ec2ed4f426f585013526522247fb93d3d464e.

## Motivation

Earlier private virtual candidates established two important boundaries.

- Exact lane-center replacement removed lateral bias but usually made spatial
  curvature continuity substantially worse.
- Constant mean-shift preserved same-frame curvature exactly but its frame-to-frame
  shift was too discontinuous for runtime use.

Private root-cause work then showed that turn-inside DIVERGING geometry is the
largest descriptive failure group. This motivated a narrower correction family
that changes only the local path-minus-lane slope while keeping the path value
at the action horizon fixed.

The first predeclared private comparison used:

- FLAT_AFFINE: set local offset slope to zero;
- RECENTER_6P75_AFFINE: choose a slope intended to recenter over 6.75 m.

RECENTER_6P75_AFFINE was rejected before public implementation because it left
the model lane envelope too often and required large corrections. It is not
exposed by this module.

FLAT_AFFINE retained high lane-envelope coverage and nearly invariant spatial
curvature. A separate follow-up hypothesis, MIRROR, then set the local offset
slope to the same magnitude with the opposite sign. MIRROR increased recentering
tendency while remaining materially more bounded than the rejected full-recenter
candidate. No gain search was performed.

## Implementation

- Added openpilot/tools/cyber_autotune/diverging_affine_candidate.py.
- build_diverging_affine_candidate():
  - validates PathQualityInput with the existing path-quality observer;
  - requires a finite nonzero requested-curvature sign;
  - requires the action horizon to lie inside the centered-slope interpolation
    axis;
  - derives model-path minus model-lane-center offset and centered local slope;
  - requires turn-inside offset and local DIVERGING geometry;
  - FLAT sets target offset slope to zero;
  - MIRROR sets target offset slope to negative of the observed slope;
  - applies one affine correction anchored to zero correction at the action
    horizon;
  - blocks any candidate that leaves the observed ego-lane envelope;
  - returns immutable descriptive geometry only.
- The candidate can alter near-field path samples before the action horizon.
  This is explicitly measured and is one reason the module remains offline.
- No epsilon, correction cap, gain, optimizer, smoothing or promotion threshold
  is introduced.
- Output hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.

## Private evidence boundary

Private route-wide evaluation used existing user-owned logs without modifying
them. Aggregate findings:

- turn-inside DIVERGING frame set: 7,675 frames;
- FLAT stayed inside the model lane envelope on about 99% of frames and changed
  same-frame curvature metrics only at very small relative levels;
- MIRROR stayed inside the lane envelope on about 97% of frames and produced
  greater future offset reduction than FLAT;
- the rejected full-recenter affine candidate stayed inside the lane envelope
  on only about 61% of frames;
- fixed-distance temporal correction changes for FLAT and MIRROR were lower than
  the earlier constant mean-shift diagnostic, including the strong-curve subset.

These aggregates are descriptive only. Model lane center is not independent
ground truth, and no private route identifier or numeric log fixture is included
in the public tests.

## TDD and risk coverage

Synthetic public-safe tests cover:

- FLAT slope neutralization with action-horizon offset preservation;
- MIRROR slope reversal with action-horizon position preservation;
- mirrored turn conventions;
- turn-outside and already-converging inputs;
- candidate lane-envelope violation;
- invalid/non-finite horizon and requested curvature;
- unsupported candidate mode;
- invalid upstream lane-change geometry;
- immutable output with no command/tune/profile surface.

TDD red phase produced 11/11 expected failures before implementation. Initial
green execution then exposed two overly strict exact-float assertions; those
tests were corrected to numerical comparison without changing candidate logic.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 11/11 expected failures before implementation |
| Initial green follow-up | 9/11 passed; two exact-float assertions corrected to approximate numeric checks, then 11/11 PASS |
| Affine + tracking-geometry + pixel/action-horizon + virtual-recenter + path-observer targeted tests | 104/104 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 946/946 PASS in 223.84 s |
| Native SCons build | PASS; existing non-fatal PWD warning only |
| Default verified-public suite | 1853 passed / 42 skipped / 1 xfailed / 0 failed in 339.62 s |

Final staged source review found no remaining Critical or Important issue in the
bounded offline candidate module. The candidate remains disconnected from
planner/control and cannot authorize vehicle activation.

## Generic closed-loop screening follow-up

A later private synthetic screen compared ORIGINAL, FLAT and MIRROR through the
existing native LatControlTorque plus the repository generic lateral plant.

The first zero-state comparison was intentionally treated as insufficient
because all arms began from zero lateral/heading error. A second screen therefore
used an identical 2 m ORIGINAL pre-roll for every arm, then branched only after
the action horizon for the following 6.75 m. The plant integrated lane error
against one common model-lane-center curvature reference so each arm was compared
against the same reference.

The screen used 12 predeclared strong DIVERGING+INSIDE frames selected only from
baseline metadata, with one frame per distinct segment and balanced requested-
curvature signs. Candidate results were not used for selection or backfill.

Results were effectively neutral:

- FLAT median final absolute lane-error ratio vs ORIGINAL was about 1.00003;
- MIRROR median final absolute lane-error ratio was about 1.00005;
- post-window RMSE ratios were also approximately 1.00001 for both candidates;
- neither candidate increased saturation in the selected generic-plant runs;
- per-frame improvement direction was mixed rather than monotonic.

This does not invalidate the earlier geometry-only benefits, but it does reject
a stronger claim that FLAT or MIRROR has demonstrated closed-loop lane-centering
improvement. The generic plant is not vehicle calibrated, uses static one-frame
geometry convected at constant speed, and starts from a synthetic pre-roll state.
Accordingly no candidate is promoted or connected to runtime control from this
screen.

## Remaining limits

- Affine correction changes the full observed path, including samples before the
  action horizon.
- Far-horizon correction grows with station distance.
- Lane-envelope containment does not establish physical drivable-space safety.
- The candidate is not closed-loop validated against vehicle dynamics.
- The model lane center and model path are related model outputs.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
