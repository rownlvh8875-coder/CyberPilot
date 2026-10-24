# Tracking geometry separation diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: descriptive software diagnostic only; no vehicle qualification or runtime use.
- Purpose: keep local model-path geometry state separate from a caller-owned
  future curvature-tracking tendency.
- Scope: an already-valid ActionHorizonConvergenceObservation plus one finite
  future tracking heading-error scalar normalized to the requested turn.
- Branch / baseline: feature/cyber-autotune from
  37d0ca1166102e2677aff7eeb9b7a957e7a5f8f6.

## Motivation

Private read-only analysis integrated logged current-minus-desired curvature over
a fixed traveled-distance window after each latency-aware action horizon.
Curvature error multiplied by traveled distance is a heading-error proxy, not a
measured lateral lane-position error.

The analysis showed two distinct turn-inside states that should not be collapsed:

- local model-path geometry is already DIVERGING away from model lane center;
- local geometry is CONVERGING, but accumulated future tracking error points
  toward the current path-offset side and therefore reinforces that offset.

In the strong-curvature turn-inside subset, geometry-diverging frames were the
larger group. Converging-but-tracking-reinforcing frames remained a distinct
secondary group. This supports separating geometry and tracking diagnostics,
not assigning causal blame to either controller or model.

## Implementation

- Added openpilot/tools/cyber_autotune/tracking_geometry_separation.py.
- observe_tracking_geometry_separation():
  - accepts only an already-valid DESCRIPTIVE_ONLY
    ActionHorizonConvergenceObservation;
  - reuses the existing fail-closed upstream action-horizon validator;
  - accepts one finite caller-owned future tracking heading-error scalar;
  - uses the sign of turn-relative path offset to express tracking error toward
    or away from the current offset side;
  - reports REINFORCES_OFFSET, COUNTERACTS_OFFSET, NEUTRAL or
    OFFSET_UNRESOLVED without any epsilon or magnitude threshold;
  - preserves geometry state independently as CONVERGING, DIVERGING, CENTER or
    FLAT;
  - exposes a combined descriptive separation_state while retaining both source
    dimensions separately.
- The module does not integrate logs, select a distance/time horizon, estimate
  vehicle pose, calculate lane position, tune parameters, rank candidates,
  generate curvature, or alter control.
- Output is frozen and hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.

## TDD and risk coverage

Synthetic public-safe tests cover:

- converging-inside plus tracking reinforcement;
- converging-inside plus tracking counteraction;
- diverging geometry with either tracking direction;
- outside-offset sign reversal;
- exact zero tracking as NEUTRAL;
- exact centered offset as OFFSET_UNRESOLVED;
- non-finite future tracking input;
- blocked and forged upstream observations;
- forged authority, offset-side and turn-normalization fields;
- immutable output with no command/tune/candidate surface.

TDD red phase produced 10/10 expected failures before implementation.

## Evidence boundary

Private route analysis remains descriptive motivation only. Exact route
identifiers, raw logs, distance-integration fixtures, private paths and
private-derived numeric test vectors are not included in this change.

The future tracking scalar is a kinematic heading-error proxy derived from
logged curvature estimates. It is not independent measured lateral position.
Model path and model lane-center are related model outputs. Therefore neither a
DIVERGING geometry label nor a REINFORCES_OFFSET tracking label is causal proof.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 10/10 expected failures before implementation |
| Center-offset fail-closed follow-up | reproduced one failing case, then PASS after OFFSET_UNRESOLVED handling |
| Tracking-geometry + pixel/action-horizon + recenter + path-observer targeted tests | 76/76 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 935/935 PASS in 224.30 s |
| Native SCons build | PASS; existing non-fatal PWD warning only |
| Default verified-public suite | 1842 passed / 42 skipped / 1 xfailed / 0 failed in 332.20 s |

Private future-distance analysis retained 17,314 valid 6.75 m active-control
windows. In turn-inside frames, geometry-diverging was the largest descriptive
group; geometry-converging plus future-tracking-reinforcing remained a smaller
secondary group. Exact private route counts and derived numeric vectors remain
outside the public repository.

Final staged source review found no remaining Critical or Important issue in
this bounded offline diagnostic. The future tracking scalar remains explicitly
caller-owned; this module neither computes nor validates the private 6.75 m
integration protocol.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
