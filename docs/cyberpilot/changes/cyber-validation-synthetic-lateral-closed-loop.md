# Native controller over the generic synthetic lateral plant

## Purpose and authority boundary

The committed runner connects the actual `LatControlTorque` implementation to the
repository-owned generic synthetic plant at 100 Hz. Every scenario starts with a
fresh controller and fresh plant state. Native torque sign is translated explicitly
into the generic plant coordinate system; the plant remains the only physical-delay
owner.

This is a software diagnostic, not a calibrated-vehicle result. It cannot activate
a profile, write Params, forward CAN, qualify shadow operation or authorize vehicle
use.

## Frozen identity

- source HEAD: `8bb0576b76748eeeadd2d8487aaf2d70928af2b8`
- scenario catalog SHA-256: `c92cb9e71a9e9c0273f56a6ca3966b7d92fda5c67aa47742aa852a0b3a14928c`
- CarParams SHA-256: `fb13c87310903b14558ff169a5f7da6a66c388b690ec8a12aaacb8538c3fec54`
- aggregate result SHA-256: `5b287382df84d7d95f253479dcce3be93447fd9477de132426ca9a9953d123f5`
- internal report SHA-256: `2421a5399f33fb7b523f8f4b4e486c0f9d717c70edd3a89750cbe49c03e8bdfd`

The complete 14-scenario execution repeated byte-for-byte.

## Outcome

```text
status                   SYNTHETIC_CLOSED_LOOP_DIAGNOSTIC
nominal completed        12 / 12
fault inputs rejected     2 / 2
blocked scenarios         0
qualified closed loop     false
performance qualified     false
candidate generation      false
runtime accepted          false
promotable                false
```

Straight low/high and the low-friction straight case remained exactly zero. Left
and right gentle/tight curves were sign-symmetric. During the explicit driver
override interval the native requested torque remained exactly zero; delayed plant
input may persist only through the single plant-owned queue.

## Stress findings

| Scenario | lateral RMSE | max lateral error | steering jerk RMSE | saturation ratio |
|---|---:|---:|---:|---:|
| gentle left/right | 0.4806 m | 1.4320 m | 932 deg/s³ | 0.000 |
| tight left/right | 22.8730 m | 53.9449 m | 1,899 deg/s³ | 0.800 |
| S-curve | 0.7482 m | 1.1557 m | 2,607 deg/s³ | 0.4517 |
| ramp | 20.7519 m | 48.6119 m | 1,377 deg/s³ | 0.790 |
| lane change | 0.3878 m | 0.6014 m | 2,861 deg/s³ | 0.325 |
| driver override | 2.1675 m | 5.1214 m | 95,569 deg/s³ | 0.010 |

These values expose software-stress weaknesses but are not estimates of real-road
meters, comfort or safety because the plant is generic and uncalibrated. In
particular, tight-curve/ramp saturation and driver-override jerk prevent treating
the current controller as a synthetic performance pass.

## TDD and regression verification

```text
RED                         10 failures: module absent
focused GREEN               10 passed
AutoTune + controls         531 / 531 passed
Ruff                        PASS
SCons                       100% complete
privacy/publication audit   186 files / 0 findings
```

Fault scenarios are rejected before CarParams decoding or controller execution.
Nominal scenarios bind actual torque-controller execution, plant execution, one
physical delay owner, ordered trace digest and fresh-state isolation. Scenario
order does not change each scenario trace.

## Next gate

This result becomes the frozen synthetic baseline. Before any new candidate is
run, CyberPilot must freeze a relative non-regression policy requiring identical
scenario/fault coverage, no authority escalation, no material regression in
lateral error, jerk, saturation or inactive torque, retained left/right symmetry,
and explicit improvement on the declared stress scenarios.

No result here permits use on a vehicle. The generic plant must remain clearly
separate from descriptive D3Y evidence and from any future prospective real-world
evaluation.
