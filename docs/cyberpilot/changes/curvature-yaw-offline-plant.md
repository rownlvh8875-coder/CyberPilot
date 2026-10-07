# Curvature / yaw offline plant primitive

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline vehicle-dynamics research.
- Status: descriptive software primitive only; no runtime use or vehicle qualification.
- Purpose: advance an immutable curvature/yaw state using caller-owned descriptive
  coefficients, a bounded normalized command, speed, roll, and an explicit command
  delay history.
- The implementation contains no fitted vehicle coefficients, route loader,
  optimizer, parameter search, controller callback, Params access, CAN transport,
  device IO, profile write, acceptance rule, or promotion path.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED

## Motivation

Earlier private low-speed vehicle-dynamics hypotheses were intentionally rejected
when they failed recursive rollout checks even though their one-step correlations
looked strong.

- A direct yaw-rate AR(1) model accumulated more multi-step error than simply
  holding the window-start yaw rate.
- A steering-rate / steering-angle / yaw-lag model also failed the predeclared
  holdout comparison at one second.
- A dynamic-bicycle oracle driven by recorded steering exposed a historical
  Hyundai yaw-rate unit interpretation issue. Correcting that private analysis
  boundary materially reduced yaw residuals, but the oracle alone still did not
  provide a sufficiently robust low-speed closed-loop plant.

A separately predeclared curvature-state hypothesis performed better. The model
treats actual curvature as the actuator/vehicle state, with yaw rate lagging the
kinematic target from that curvature. It was developed on one recorded route,
then frozen before independent-route evaluation.

Private independent-route evidence used metadata-only route selection before
performance evaluation. Three selected routes had sufficient low-speed coverage
and each beat the same-window yaw persistence baseline at both 0.5 s and 1.0 s.
One additional selected route had insufficient low-speed continuous coverage and
was recorded as unavailable without backfill. This evidence motivates exposing
the generic state transition only; it does not qualify any fitted coefficients
for product or vehicle use.

## Public state transition

The caller supplies:

- CurvatureYawPlantConfig
  - time step and explicit integer command-delay length;
  - bounded speed and normalized-command domain;
  - curvature intercept / autoregressive coefficient;
  - command, command-times-speed, command-over-speed, and roll coefficients;
  - yaw residual autoregressive coefficient and bias.
- CurvatureYawPlantState
  - curvature;
  - yaw rate;
  - fixed-length command-history tuple.
- one current command, speed, and roll observation.

For a delayed command u, current curvature k, speed v, and roll r:

k_next = c0 + ak*k + bu*u + buv*u*v + buiv*u/v + br*r

The descriptive yaw target follows the screening sign convention:

target = -k*v

and the next yaw state is:

yaw_next = target_next + ar*(yaw_current - target_current) + bias

The delay FIFO is part of immutable state. A zero-delay configuration uses the
current command directly and keeps an empty history.

## Fail-closed contract

The function returns BLOCKED rather than extrapolating when:

- configuration fields are non-finite or structurally invalid;
- curvature AR magnitude is not strictly below one;
- yaw AR is outside [0, 1);
- time step, speed domain, or normalized command limit is invalid;
- state values are non-finite;
- command-history cardinality does not exactly match the configured delay;
- a historical command exceeds the configured command domain;
- current command, speed, or roll is non-finite or outside the declared domain;
- a derived state becomes non-finite.

Successful output is frozen and hard-codes:

- NOT_READY
- REAL_VEHICLE_UNVERIFIED
- VEHICLE_ACTIVATION_BLOCKED
- vehicle_activation_allowed=False

There is no accepted/candidate decision, controller command, tune, or profile
surface.

## TDD coverage

Public-safe synthetic tests cover:

- exact transition arithmetic and delayed-command FIFO behavior;
- zero-delay behavior;
- mirrored left/right antisymmetry with zero bias;
- invalid and unstable configurations;
- malformed/non-finite state and delay history;
- command/speed/roll domain rejection;
- immutable output and absence of authority surfaces.

TDD red phase produced 7/7 expected failures before implementation. The initial
green implementation then passed all 7 tests.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 7/7 expected failures before implementation |
| New primitive unit tests | 7/7 PASS |
| Related targeted validation set | 107/107 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 973/973 PASS in 226.09 s |
| Native SCons build | PASS; existing non-fatal PWD warning only |
| Default verified-public suite | 1880 passed / 43 skipped / 1 xfailed / 0 failed in 338.44 s |

Final source review found no remaining Critical or Important issue. The public
primitive contains no fitted coefficients, file/log access, controller callback,
runtime hook, candidate verdict, vehicle command, profile/tune mutation, or
promotion surface.

## Evidence boundary

The public module intentionally does not embed private fitted coefficients or raw
route evidence. Coefficient provenance, unit interpretation, calibration domain,
independent-reference validity, and physical closed-loop qualification remain
caller-owned evidence problems.

The private evaluation used recorded feedback and retrospective routes. It is not
a prospective vehicle trial, does not prove lane-centering improvement for a
candidate model, and does not authorize vehicle activation. Before this primitive
can support model/controller comparison, a separate evidence-bound adapter must
bind qualified coefficients, initial state, timebase, and model/controller output
to an offline closed-loop experiment.

No runtime caller is introduced by this change.
