# Curvature / yaw closed-loop transcript adapter

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline closed-loop validation.
- Parent primitive: `curvature_yaw_plant.py`.
- Status: structural evidence adapter only; no runtime or vehicle qualification.
- Purpose: bind a frozen plant configuration, initial state, input/timebase,
  controller identity, and stepwise controller transcript to the existing
  `ClosedLoopReceipt` admission contract.

Vehicle decision remains:

`NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED`

## Design correction before commit

The first local draft accepted a Python controller callback and executed it
in-process. That design was rejected before commit because arbitrary callback
code could perform external I/O, making the adapter unable to substantiate its
own non-actuation claims.

The committed design does **not** execute controller code. It accepts an immutable
external transcript. Every row contains:

- step index and timestamp;
- SHA-256 of the exact feedback state visible immediately before the command;
- requested normalized torque.

The adapter recomputes the feedback state from the plant, verifies the row hash,
checks timebase and command bounds, and only then advances the plant. Therefore
the public adapter has no controller execution, CAN, Params, device, network,
subprocess, profile-write, or vehicle-write API.

This does not authenticate the external transcript producer and does not prove
that producer-side execution was non-actuating. Both remain explicit blockers.

## Evidence bindings

`CurvatureYawRunContract` binds:

- controller identity SHA-256;
- expected plant-config SHA-256;
- expected initial-state SHA-256;
- expected complete controller-transcript SHA-256;
- explicit controller-to-plant sign convention;
- contract version.

The existing `ClosedLoopBinding` additionally binds software, controller,
adapter, plant, calibration, domain, inputs, reset, metric, environment and
timebase identities.

The reset binding must equal the canonical initial-state digest. Input and
timebase digests must match the supplied `ClosedLoopFrame` sequence.

## Stepwise causal consistency

For each frame, the adapter constructs:

`CurvatureYawControllerFeedback(step, time, curvature, yaw rate, lateral accel, heading, pose_y)`

The controller transcript row's `feedback_sha256` must equal the canonical hash
of that exact state. A mismatch fails closed before the corresponding plant step.

The requested command is sign-mapped into the curvature/yaw plant. The plant owns
the only physical actuator-delay FIFO. Delayed command is mapped back into
controller coordinates for the structural receipt.

Heading and lateral pose are descriptive observer states:

- heading is integrated from plant yaw rate;
- lateral pose is integrated from speed and heading.

They are not independent lane truth and do not establish lane-centering quality.

## Fail-closed behavior

The adapter returns `BLOCKED` for:

- malformed contract, binding, frames, state or transcript;
- plant configuration / initial state / transcript digest mismatch;
- controller or reset binding mismatch;
- plant/domain delay, timestep, speed or command-domain mismatch;
- input or timebase binding mismatch;
- transcript cardinality, row timestamp/index or feedback-hash mismatch;
- command outside normalized bounds;
- any plant rejection;
- non-finite descriptive pose state;
- any downstream structural receipt admission failure.

Successful structural admission still carries:

- `PLANT_CALIBRATION_DESCRIPTIVE_ONLY` or review-required equivalent;
- `INDEPENDENT_REFERENCE_UNVERIFIED`;
- `PERFORMANCE_GATE_NOT_EVALUATED`;
- `CONTROLLER_PRODUCER_AUTHENTICITY_UNVERIFIED`;
- `CONTROLLER_PRODUCER_NONACTUATION_UNVERIFIED`;
- `CURVATURE_YAW_ADAPTER_OFFLINE_ONLY`.

All qualification, runtime and promotion flags remain false.

## Validation

| Check | Result |
| --- | --- |
| New adapter tests | 7/7 PASS |
| Adapter + plant + structural admission focused set | 23/23 PASS |
| Ruff changed Python files | PASS |
| `git diff --check` | PASS |
| AutoTune package regression | 838/838 PASS in 371.35 s |
| Runtime/CAN/Params/profile call sites introduced | none by design |
| Vehicle qualification | NOT RUN / NOT AUTHORIZED |

## Interpretation and next gate

This closes the immediate software gap between the descriptive curvature/yaw
plant and the existing structural closed-loop receipt format without introducing
an executable controller callback into the adapter.

It does **not** close the scientific or vehicle-readiness gates. Before candidate
comparison can be qualified, the external controller producer still needs
reviewed isolation/authenticity evidence, the plant coefficients and calibration
need qualified provenance, the initial state must come from an admissible source,
and an independent path reference plus frozen performance criteria are still
required.

No runtime controller, CAN path, profile activation, safety-limit change, shadow
promotion, or vehicle deployment is authorized by this increment.
