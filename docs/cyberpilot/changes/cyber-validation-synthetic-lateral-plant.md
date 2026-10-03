# Generic synthetic lateral plant

## Purpose and boundary

CyberPilot now contains a deterministic generic lateral plant for offline
software stress testing:

```text
openpilot/tools/cyber_autotune/synthetic_lateral_plant.py
```

It is intentionally **not** the historical D3Y calibration and is not presented
as a current-vehicle model. It provides a transparent, repository-owned response
surface for testing delay ownership, deadzone/friction handling, response lag,
command saturation, symmetry, reset behavior and fail-closed input validation.

The plant does not call the controller, open logs, use CAN, write Params, activate
a profile or grant runtime/shadow/promotion authority.

## Frozen generic configuration

| Item | Value |
|---|---:|
| timestep | 0.01 s |
| physical actuator delay | 0.03 s / 3 steps |
| first-order response time constant | 0.20 s |
| lateral acceleration per normalized command | 3.0 m/s² |
| normalized-command friction deadzone | 0.05 |
| wheelbase proxy | 2.8 m |
| steer-ratio proxy | 16.0 |
| command limit | ±1.0 |

Configuration SHA-256:

```text
87cf9290bf588bbe7a70435865925a3604b4fee96e1a34f77f61797922a4d775
```

## Verified behavior

- zero command on a straight target remains exactly zero;
- one physical delay queue is owned by `PLANT` and there is no controller queue;
- the first three samples remain delayed and the fourth receives the first input;
- command input is clamped to ±1.0 and saturation is explicit;
- commands inside the friction deadzone produce zero effective command;
- left/right responses are sign-symmetric for acceleration, yaw, heading,
  lateral error, steering angle and steering rate;
- reset restores the same deterministic trace;
- lower/higher friction scales produce the expected ordered response;
- non-finite, invalid-speed, invalid-curvature and invalid-friction inputs fail closed.

Sanitized result:

```text
docs/cyberpilot/changes/cyber-validation-synthetic-lateral-plant-result.json
```

Result SHA-256:

```text
2410c5e4d373c9d4eb0af5d0dc5afe0929e0894065c793560315f9e7261b7751
```

## TDD verification

```text
RED     9 failures because the module did not exist
GREEN   9 passed / 12 subtests
Ruff    PASS
```

## Interpretation

This plant is useful for software invariants and deterministic regression. It can
expose double delay, asymmetry, deadzone mistakes, sign errors, reset leakage,
non-finite state and saturation-accounting defects without new road data.

It cannot establish:

- the actual vehicle's friction, tire response, steering ratio or time constant;
- real lane-center or road-edge accuracy;
- real steering jerk, intervention probability or stability margin;
- performance improvement of any Cyber controller candidate.

The result status is:

```text
GENERIC_SYNTHETIC_PLANT_READY
```

with classification:

```text
GENERIC_SYNTHETIC_NOT_VEHICLE_CALIBRATION
```

`vehicle_calibration_claimed`, `controller_executed`, `vehicle_or_can_write`,
`runtime_accepted` and `promotable` remain false. The next step is to connect the
frozen synthetic scenario matrix, actual offline native torque controller and this
plant through a repository-owned runner, while retaining those restrictions.
