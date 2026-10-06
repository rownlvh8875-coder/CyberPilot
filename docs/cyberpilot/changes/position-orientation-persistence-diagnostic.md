# Position / orientation persistence diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: descriptive temporal grouping only; no runtime use or vehicle qualification.
- Purpose: measure how long already-classified position/orientation separation
  states remain unchanged across consecutive samples.
- Scope: timestamped PositionOrientationSeparationObservation values plus one
  caller-owned maximum inter-sample gap.
- The module does not choose persistence thresholds, tune parameters, rank
  candidates, modify model output, or issue vehicle commands.
- Branch / baseline: feature/cyber-autotune from the current
  position/orientation separation diagnostic.

## Motivation

Private read-only follow-up tested whether the position/orientation mismatch
observed in strong turn-inside DIVERGING geometry was merely a one-frame artifact.

The majority LESS_TURN_THAN_LANE relation persisted across consecutive model
frames often enough that a substantial share of frames belonged to multi-frame
runs extending for a few tenths of a second, with a smaller subset persisting
for about a second or longer. This rules out an explanation based only on
isolated frame noise.

An independent pixel-reference follow-up reused a frame set that had been locked
before the orientation analysis. On detector-valid comparisons, model-lane and
image-derived lane tangents usually agreed on whether orientation asked for
more or less turn than the lane tangent. One disagreement remained, reinforcing
that the model-lane tangent is not absolute ground truth.

These observations motivate a generic run-duration primitive only. They do not
authorize a control correction.

## Implementation

- Added openpilot/tools/cyber_autotune/position_orientation_persistence.py.
- observe_position_orientation_persistence():
  - accepts timestamped PositionOrientationSeparationObservation values;
  - validates every upstream observation's safety/readiness fields and numeric
    identities before using it;
  - requires finite strictly increasing timestamps;
  - accepts a finite positive caller-owned max_gap_s;
  - starts a new run whenever the combined descriptive state changes or the
    inter-sample gap exceeds max_gap_s;
  - returns immutable run records containing state identity, start/end time,
    actual span and sample count.
- The module deliberately does not contain 0.25 s, 0.5 s, 1.0 s or any other
  persistent/non-persistent decision threshold.
- No epsilon, acceptance rule, candidate ranking, action correction, optimizer,
  runtime hook, Params write, CAN write, or vehicle authority is introduced.
- Output hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.

## TDD and risk coverage

Synthetic public-safe tests cover:

- grouping identical states within a caller-owned gap;
- splitting on state changes;
- splitting on excessive time gaps;
- mirrored turn normalization preserving the same descriptive state;
- empty input;
- invalid/non-finite max gap;
- non-finite, duplicate and decreasing timestamps;
- forged authority and forged numeric identities;
- immutable result/run records with no command/tune/threshold surface.

TDD red phase produced 10/10 expected failures before implementation, followed
by 10/10 PASS after implementation.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 10/10 expected failures before implementation |
| Persistence + position/orientation + action-horizon + pixel/action + tracking-geometry + affine + recenter/path-observer targeted tests | 100/100 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 966/966 PASS in 225.88 s |
| Native SCons build | PASS; existing non-fatal PWD warning only |
| Default verified-public suite | 1873 passed / 42 skipped / 1 xfailed / 0 failed in 339.01 s |

Final staged source review found no remaining Critical or Important issue. The
module only groups already-descriptive states and has no action/correction or
vehicle-decision surface.

## Evidence boundary

Private temporal-run and pixel-reference aggregate evidence is descriptive
motivation only and is not embedded as a public acceptance fixture.

The run primitive says only that a model-output relationship persisted for a
measured span. It does not prove causal steering error, vehicle lane position,
or that changing either position or orientation would improve centering.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
