# Position / orientation separation diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: descriptive software diagnostic only; no runtime use or vehicle qualification.
- Purpose: separate action-horizon position-path geometry from model orientation
  relative to the model-lane-center tangent.
- Scope: an already-valid ActionHorizonConvergenceObservation plus caller-owned
  lane-center slope and model orientation yaw at the same horizon.
- The diagnostic does not create an action correction, choose a target, tune a
  parameter, modify model output, or issue a vehicle command.
- Branch / baseline: feature/cyber-autotune from
  86a8233b0c7f93c48a8249bfd0bb8ab3ef5529d9.

## Motivation

Private read-only source tracing established two materially different model
execution paths.

- The small driving model has no direct action output. Its published lateral
  action is derived from plan orientation and orientation-rate through the
  modeld plan-fallback equation.
- The big external-accelerator model has a direct action output.

The historical evidence used for the current root-cause work was verified to be
small-model data. Replaying the historical plan-fallback equation with the
historical delay/smoothing configuration reproduced logged model action to near
floating-point precision after accounting for message timing.

An attempted bridge from position-path FLAT geometry directly into action was
then rejected. In strong curves, the pre-existing difference between model
orientation yaw and the position-path tangent was often larger than the yaw
change implied by the FLAT position correction. Position tangent therefore
cannot be treated as a sufficiently precise proxy for action orientation.

Direct comparison of model orientation yaw against the model-lane-center tangent
produced a stronger negative result: turn-inside DIVERGING position geometry did
not usually coincide with orientation asking for more turn than the lane
tangent. In the strong-curve subset, only roughly one quarter of those position
frames had orientation farther toward the turn; the majority had orientation
asking for less turn than the lane tangent.

This means position-path divergence and orientation/action direction must be
kept as separate diagnostic axes. A position-path correction must not be
automatically translated into an action correction.

## Implementation

- Added openpilot/tools/cyber_autotune/position_orientation_separation.py.
- observe_position_orientation_separation():
  - accepts only a DESCRIPTIVE_ONLY ActionHorizonConvergenceObservation;
  - revalidates upstream readiness, safety, convergence identity, offset side,
    and hidden turn-normalization consistency;
  - requires a non-centered upstream offset so the requested-turn sign can be
    recovered exactly;
  - converts caller-owned lane-center slope to tangent yaw using atan();
  - compares model orientation yaw against that lane tangent;
  - normalizes the yaw residual by the recovered requested-turn sign;
  - reports MORE_TURN_THAN_LANE, LESS_TURN_THAN_LANE, or
    LANE_TANGENT_MATCH;
  - reports a combined descriptive state such as
    DIVERGING_INSIDE__LESS_TURN_THAN_LANE.
- CENTER is blocked as TURN_UNRESOLVED rather than guessing a turn sign.
- Output is frozen and hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.
- No candidate action, curvature delta, threshold, optimizer, gain, acceptance
  rule, runtime hook, Params write, CAN write, or vehicle authority exists.

## TDD and risk coverage

Synthetic public-safe tests cover:

- DIVERGING+INSIDE with orientation both less-turn and more-turn than lane;
- exact lane-tangent match;
- mirrored left/right turn normalization;
- non-finite orientation/lane geometry;
- centered offset with unresolved turn sign;
- blocked and forged upstream convergence state;
- forged turn normalization and vehicle authority;
- centered forged authority taking precedence over TURN_UNRESOLVED;
- immutable output with no action/correction/tune surface.

TDD red phase produced 9/9 expected failures before implementation. An
additional integrity test then exposed that centered geometry could mask forged
authority behind TURN_UNRESOLVED. Validation ordering was corrected and the
expanded 10-test suite passed.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 9/9 expected failures before implementation |
| Added integrity red/green | centered forged-authority case failed before validation-order fix, then PASS |
| Position/orientation + action-horizon + pixel/action + tracking-geometry + affine + recenter/path-observer targeted tests | 90/90 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 956/956 PASS in 227.75 s |
| Native SCons build | PASS; existing non-fatal PWD warning only |
| Default verified-public suite | 1863 passed / 42 skipped / 1 xfailed / 0 failed in 341.23 s |

Final staged source review found no remaining Critical or Important issue. The
module contains no action/correction output and remains disconnected from
modeld, controlsd, planner and vehicle actuation.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 9/9 expected failures before implementation |
| Centered forged-authority integrity red/green | forged authority initially masked by TURN_UNRESOLVED; validation ordering corrected, then PASS |
| Position/orientation + action-horizon + pixel/action + tracking-geometry + affine + recenter/path-observer targeted tests | 90/90 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 956/956 PASS in 227.75 s |
| Native SCons build | PASS; existing non-fatal PWD warning only |
| Default verified-public suite | 1863 passed / 42 skipped / 1 xfailed / 0 failed in 343.59 s |

Historical small-model source reconstruction and route-level orientation/lane
comparisons remain private descriptive evidence only. No historical log values,
route identifiers, device identifiers, or private fixtures are included in
public tests.

Final staged source review found no remaining Critical or Important issue in
this bounded offline diagnostic.

## Temporal and independent-reference follow-up

Private follow-up analysis tested whether the position/orientation separation was
only a single-frame artifact.

In strong turn-inside DIVERGING geometry, the LESS_TURN_THAN_LANE state was the
majority orientation relation. More than half of its frames belonged to runs
lasting at least 0.25 s, more than one third belonged to runs lasting at least
0.5 s, and a smaller but material subset persisted for at least 1 s. The state
therefore cannot be explained only as isolated model-frame noise.

Future model-lane-relative recenter remained rare in both orientation groups.
The MORE_TURN_THAN_LANE subgroup was especially adverse, but the much larger
LESS_TURN_THAN_LANE subgroup also overwhelmingly failed to recenter. This keeps
position DIVERGENCE as the primary descriptive separator rather than turning the
orientation relation into a standalone causal rule.

A second follow-up reused the previously locked pixel-reference frame set
without detector retuning or backfill. For frames where the unchanged pixel
detector and historical action horizon were both usable, model-lane and
image-derived lane tangents agreed on the orientation MORE/LESS_TURN relation in
five of six comparisons. One frame disagreed because the model-lane tangent and
the image-derived tangent themselves differed enough to cross the orientation
yaw.

The pixel result therefore provides partial independent support, while also
showing why the model-lane tangent must not be treated as absolute ground truth.

## Evidence boundary

Private route-level numeric evidence is not included as a public test fixture.
The lane-center tangent is derived from model lane lines, so it is not
independent surveyed lane-center truth. Model orientation and model position are
also related outputs of the same model family.

The purpose of this diagnostic is therefore separation, not causality: it
records when position geometry and orientation/action imply different lateral
stories at the same horizon.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
