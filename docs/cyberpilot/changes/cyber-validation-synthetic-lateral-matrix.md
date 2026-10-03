# Cyber Lateral deterministic synthetic scenario matrix

## Purpose

This change freezes deterministic offline input scenarios for lateral validation
without requiring new vehicle logs. It creates no controller callback, plant
execution, tuning candidate, profile write, CAN path, runtime acceptance or
promotion authority.

The public implementation is:

```text
openpilot/tools/cyber_autotune/synthetic_lateral_scenarios.py
```

The catalog is intended to drive later controller/plant adapters under the same
predeclared input basis. It is not evidence that any controller performs well.

## Frozen matrix

- scenarios: 14
- nominal scenarios: 12
- explicit rejected-input scenarios: 2
- catalog SHA-256: `c92cb9e71a9e9c0273f56a6ca3966b7d92fda5c67aa47742aa852a0b3a14928c`
- aggregate result SHA-256: `c00d753a6c2057dc22e398cd4a193eaeb61661fc880548d789306e406ad730ac`

## Coverage

The matrix covers every required preflight stratum:

```text
straight, left_curve, right_curve, gentle_curve, tight_curve,
low_speed, medium_speed, high_speed, entry, apex, exit,
lane_change, driver_override, steering_release, reengagement, saturation
```

The stress axes are:

```text
s_curve, ramp, delay_high, friction_low, friction_high,
sensor_dropout, timebase_gap
```

Nominal scenarios use a uniform 10 ms timebase and finite bounded values.
The two fault scenarios are isolated from performance inputs:

- `sensor_dropout`: a declared invalid-sensor interval;
- `timebase_gap`: exactly one declared discontinuity.

Left/right gentle and tight curves are sign-symmetric. The S-curve crosses both
curvature signs. The ramp has entry, apex and exit phases. Driver override,
release and reengagement are explicit frame states.

## Verification

TDD evidence:

```text
RED: 11 failures because the module did not exist
GREEN: 11 passed / 4 subtests
Ruff: PASS
```

Tests bind complete stratum/stress coverage, deterministic catalog and frame
hashes, nominal timebase/domain validity, curve symmetry, maneuver state changes,
fault semantics, duplicate IDs, non-finite/out-of-domain rejection and
order-sensitive catalog identity.

## Authority boundary

The result remains:

```text
SYNTHETIC_MATRIX_READY
```

with blocker:

```text
SYNTHETIC_ONLY_NO_PHYSICAL_QUALIFICATION
```

`controller_executed`, `plant_executed`, `vehicle_or_can_write`,
`performance_qualified`, `candidate_generation_allowed`, `runtime_accepted` and
`promotable` are all false. Subsequent work must run the same catalog through
repository-owned adapters and retain these authority boundaries until separate
closed-loop and shadow gates pass.
