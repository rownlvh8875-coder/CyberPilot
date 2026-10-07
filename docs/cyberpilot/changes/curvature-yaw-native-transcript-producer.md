# Isolated native curvature/yaw transcript producer

## Purpose

This increment connects the real native `LatControlTorque` controller core to
the descriptive curvature/yaw closed-loop adapter without introducing a live
vehicle path. A bounded child process produces an immutable controller transcript;
the public parent adapter independently replays that transcript against the same
frozen plant contract and verifies every feedback-state hash.

Vehicle decision remains:

`NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED`

## Boundary

The producer receives exact source and CarParams bindings, a frozen plant
configuration, an explicit initial state, and a fixed frame sequence. Recorded
steering angle/rate are forbidden. Instead, each step derives the steering angle
from the current plant curvature using the native `VehicleModel` inverse so that
`LatControlTorque` sees closed-loop plant feedback.

The child preserves one controller instance across the sequence, therefore PID,
lateral-acceleration history and jerk-filter state evolve natively. The only
physical actuator-delay queue remains in the curvature/yaw plant.

The child has no CAN, Params, CarController, profile mutation, network, device or
runtime activation API. The parent process is a bounded supervisor using the
existing owned-process cleanup contract.

## Evidence bindings

The strict request binds:

- native source HEAD, opendbc HEAD and selected controller source hashes;
- exact CarParams bytes SHA-256 and vehicle fingerprint;
- selected producer/support module hashes;
- plant configuration and initial state;
- controller-to-plant sign convention;
- all controller input frames.

The result binds:

- request SHA-256;
- controller identity SHA-256;
- plant configuration and initial-state SHA-256;
- ordered controller transcript SHA-256;
- final closed-loop state SHA-256;
- support-file set SHA-256.

Each transcript row binds the exact feedback state visible before its command.
The parent adapter recomputes that state and rejects any mismatch.

## Remaining blockers

Structural admission does not establish:

- physical plant calibration qualification;
- independent lane/path truth;
- controller-producer authenticity beyond the local source/hash contract;
- prospective vehicle evidence;
- performance acceptance;
- uncertainty qualification;
- shadow or active-control permission.

No vehicle/CAN write, profile activation, safety-limit change or deployment is
authorized by this increment.

## Validation results

| Check | Result |
| --- | --- |
| New isolated producer / protocol / adapter integration tests | 7/7 PASS |
| Native + curvature/yaw + structural focused regression | 51/51 PASS |
| Ruff changed Python files | PASS |
| `git diff --check` | PASS |
| Publication/privacy audit | 342 changed files / 0 findings |
| New-code authority-path search | no Params/sendcan/CarController/socket/HTTP/vehicle-write call sites |
| AutoTune package regression | 845/845 PASS in 374.18 s |
| Vehicle qualification | NOT RUN / NOT AUTHORIZED |

The feedback inversion consistency check allows only the numerical difference
introduced when the native Cap'n Proto `steeringAngleDeg` field stores the
computed angle as float32. The check uses `rel_tol=2e-6` and `abs_tol=2e-10` on
reconstructed curvature. This is a wire-format consistency tolerance, not a
plant-performance, controller-quality, lane-centering, or vehicle-acceptance
threshold.
