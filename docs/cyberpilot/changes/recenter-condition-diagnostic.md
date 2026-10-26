# Recenter condition diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: descriptive software diagnostic only; no vehicle qualification or runtime use.
- Purpose: attach turn-relative geometry side and control-tracking sign to an
  already-computed recenter observation without introducing thresholds, tuning,
  or candidate selection.
- Scope: immutable recenter observation plus existing scalar model/control
  curvature and speed values only.
- Branch / baseline: feature/cyber-autotune from
  615eb82de76520f8052b8dfd6c61495dfbea40da.

## Motivation

Private read-only analysis of the existing log set found that the strongest
separator of near-field recenter behavior was whether the current model path
started on the inside or outside of the requested turn. That separation
persisted across the predeclared future stations and remained visible in
segment-weighted summaries. Stronger action curvature was associated with lower
recenter frequency for the turn-inside subset.

By contrast, tracking UNDER/OVER showed mixed direction across same-segment
paired comparisons and was less consistent after conditioning on turn-relative
start side. These associations are descriptive only: model path and lane center
share one model source, frames are temporally correlated, and current curvature
is a control/vehicle-model estimate rather than independent trajectory truth.

## Implementation

- Added openpilot/tools/cyber_autotune/recenter_condition.py.
- observe_recenter_condition():
  - accepts an existing DESCRIPTIVE_ONLY RecenterIntentObservation;
  - requires finite model action curvature, controls desired curvature, current
    curvature and non-negative speed;
  - validates the upstream recenter observation's numeric identities and
    non-authoritative safety/readiness fields before using it;
  - fails closed when action or control turn sign is unresolved or the action
    and controls desired-curvature signs disagree;
  - reports start offset in turn-relative coordinates;
  - classifies start side as INSIDE, OUTSIDE or CENTER with no magnitude
    threshold;
  - reports turn-normalized tracking residual and exact sign state
    OVER / UNDER / NEUTRAL with no tracking threshold;
  - copies the recenter result but does not rank, accept, tune or modify it.
- Source-traced convention used by this diagnostic:
  - model/calibrated geometry y is positive to the right;
  - positive current-branch desired curvature corresponds to the right-turn
    direction used for this attribution.
- Output is frozen and hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.

## TDD and risk coverage

Synthetic public-safe tests cover:

- positive and negative turn directions;
- turn-inside and turn-outside mapping;
- UNDER, OVER and NEUTRAL tracking signs;
- zero start offset;
- action/control sign mismatch and unresolved turns;
- non-finite inputs and negative speed;
- blocked, forged and internally inconsistent recenter input propagation;
- immutable, non-authoritative output.

The module contains no curvature magnitude bin, speed bin, confidence gate,
promotion threshold or vehicle-specific tune. Any stratification remains in
private read-only analysis and is not part of runtime behavior.

## Evidence boundary

Private analysis used the existing user-owned log set in read-only mode and is
not a software acceptance fixture. No route, image, raw log, location, private
path or private-derived test vector is copied into this repository. The private
result motivates this primitive but does not authorize a controller change.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 8/8 failed before implementation because the module did not exist |
| Recenter-condition unit tests after consistency hardening | 9/9 PASS |
| Recenter-condition + recenter-intent + path-observer targeted tests | 28/28 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 894/894 PASS in 224.83 s |
| Native SCons build | PASS, exit 0; existing non-fatal PWD warning only |
| Default verified-public suite | 1801 passed / 42 skipped / 1 xfailed / 0 failed in 342.63 s |
| Private condition attribution | turn-relative INSIDE start was a stronger separator of recenter outcome than tracking UNDER/OVER; stronger curvature further lowered recenter frequency in the INSIDE subset |

Review findings fixed before the full gates:

1. A caller could construct an internally inconsistent RecenterIntentObservation
   and still receive a descriptive condition result. The final implementation
   now verifies numeric identities, logical recenter/same-side fields, station
   ordering and blocked authority fields before accepting that input.
2. The public primitive retains exact sign classifications only. Private
   curvature/speed/confidence bins remain outside the repository and do not
   become tuning or promotion thresholds.

Final staged source review found no remaining Critical or Important issue in
this bounded offline diagnostic. The private analysis remains descriptive and
does not prove model causality or authorize a control change.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
