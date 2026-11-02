# R41 — Combined boundaries and longer synthetic sequences

## Intent and scope

Extend the existing R35 selected-literal regression pack through the unchanged
R40 workflow. The user approved this direction and delegated routine design
choices; implementation proceeds without another design/permission round.
The specific cases and lengths below are implementer choices, not owner policy.

Keep the public 0.3.0 wheel, model, CLI, selected production sources, and all
existing examples unchanged. No new dependencies or runtime adapter. Every
number in this pack is a declared synthetic fixture, never vehicle authority.

## Approaches

1. Add more isolated unit cases: cheap, but largely duplicates R35.
2. Add a bounded fixed pack to existing input/engine/workflow/reference paths:
   chosen because it exercises interacting conditions and persistent history
   without adding an execution layer.
3. Add randomized generation or a new runner: deferred; seed management and a
   new oracle surface are not needed for this small, reproducible increment.

## Fixed pack

All use STEER_MAX=16, UP=2, DOWN=5. These are synthetic command units per
invocation, not an r policy or time conversion.

- `combined_boundaries_v1.json`: 12 samples, indices 50..61; declared previous
  request12/applied6/counter88. Allowance0, driver factor/multiplier1. Combine
  fractional driver boundaries, asymmetric history clipping, sign changes,
  fault counter89/90/91, inactive clearing, signed zero, and nearest-even ties.
- `repeated_inactive_crossing_v1.json`: 128 samples, indices100..227. Repeat a
  hand-derived eight-step cycle16 times. Each cycle ends with request16/applied2/
  counter0, so its state genuinely carries into the next cycle. Driver0;
  allowance7/factor1/multiplier3. Previous requested must not replace applied.
- `long_fault_cycles_v1.json`: 184 samples, indices0..183; request0.25/driver0,
  active throughout and alternating angles+85/-85. With the selected source's
  fault89/mismatch2 rule, suppression occurs at offsets89,90,180,181. Counter
  resets twice; output remains4 after the initial2, including suppressed flags.

Preregister independent hand-derived selected rows, repeating literal cycle,
counter rule, and final states in `reference/r41_regression_expected_v1.json`
before executing these new scenarios. Never generate expected values from the
model or auto-update them after a failure. Typed JSON/hex comparison, no tolerance.
R39 separately compares complete outputs against its selected-source worker.

## Tests and negative controls

Test real parser/engine behavior, then run R40 twice independently and a third
time against a complete first batch baseline. Check saved rows/VIEW, full nested
manifest closure, portable bytes, reference accounting, and unchanged inputs.
Full private receipts are not required to be byte-identical across directories.

On separate saved copies, inject a coherent wrong applied-history transition and
a coherent wrong fault-counter transition. Regenerate only duplicate saved
projections/checksums, never model expectations. R38 must report DIFFERENT and
derive its own next state rather than ingest the wrong saved state. Mutations
do not alter the source model, references, or registered inputs.

## Non-goals and limits

This is bounded source-parity/regression evidence, not a generic oracle,
exhaustive property proof, physical performance, elapsed-time test, or native
replay. 184 invocations are not 1.84 seconds. No F61, r/dt calculation,
Controller, Runtime, CAN, vehicle data, deployment, or candidate evaluation.
R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/scale=null, activation and
F70UH/V/F71 NOT_ALLOWED remain unchanged. Source/API discrepancies are reported,
not silently repaired by changing expected vectors.

## Delivery

Implementation and local verification on an isolated feature branch. Document
commands and the bounded coverage. No push, merge, or CI activation in this task.
