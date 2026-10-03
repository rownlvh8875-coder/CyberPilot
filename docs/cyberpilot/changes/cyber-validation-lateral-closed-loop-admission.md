# Cyber Lateral closed-loop structural admission

## Identity and purpose

- Area: STEP7/STEP9 offline lateral closed-loop validation.
- Public source HEAD: `5e0dcc3f8fa42a4fd1a5f3bb7f8a387f00804573`.
- Purpose: admit aggregate-only external plant/controller receipts to the
  repository comparison pipeline without importing private logs or plant code.
- This is not a plant implementation, model calibration, performance approval,
  shadow scheduler, profile writer, CAN transport or vehicle-use authorization.

The repository now owns the receipt contract in
`openpilot/tools/cyber_autotune/lateral_closed_loop.py`. A private offline runner
may produce a receipt, but the receipt fails closed unless its domain, inputs,
timebase, trace and authority boundaries match this contract.

## Structural contract

The contract binds:

- software, controller, adapter, plant, domain and environment SHA-256 identities;
- immutable reset, input, metric and timebase SHA-256 identities;
- contiguous frame indices and the declared fixed control period;
- speed and normalized-command bounds from the frozen domain;
- controller prediction delay as metadata, not a second physical delay queue;
- exactly one physical actuator-delay owner: `PLANT`;
- ordered trace samples and their content digest.

Every receipt must also assert all of the following as false:

- `sendcan_forwarded`
- `live_can`
- `vehicle_write`
- `parameter_write`
- `runtime_accepted`
- `promotable`

A structurally valid receipt returns `STRUCTURAL_ADMISSION`, not qualification.
The result always retains these blockers until separate evidence exists:

1. `PLANT_CALIBRATION_AUTHENTICITY_UNVERIFIED`
2. `INDEPENDENT_REFERENCE_UNVERIFIED`
3. `PERFORMANCE_GATE_NOT_EVALUATED`

## TDD and focused verification

The test was first run before the module existed and failed 8/8 with
`ModuleNotFoundError`. After implementation:

```text
public admission contract  8 passed / 12 subtests
private D3Y focused suite  29 passed
Ruff                      PASS
```

Covered failures include duplicate/no physical delay owner, a controller-side
physical delay queue, discontinuous timebase, out-of-domain speed, mismatched
input/domain/timebase/trace digests, invalid trace values, cardinality mismatch,
non-completed runs and every forbidden authority flag.

## Current-HEAD six-window revalidation

The existing external D3Y adapter and frozen development manifest were rerun
against the public CyberPilot source after adding the public contract. Private
route identities, raw logs and plant implementation remain outside the repository.

| Check | Result |
|---|---:|
| frozen development windows | 6 |
| samples per arm/window | 1,000 |
| baseline structural admissions | 6/6 |
| candidate structural admissions | 6/6 |
| strict A0/A0 repeatability | 6/6 PASS |
| A0/A3 repeatability | 6/6 PASS |
| A3 performance gates | 0/6 PASS; candidate rejected |
| shadow promotion | false |
| active-control promotion | false |

Every one of the 12 arm receipts retained the three structural blockers and
reported `qualified_closed_loop=false`, `runtime_accepted=false` and
`promotable=false`.

The complete aggregate result repeated byte-for-byte with SHA-256:

```text
c72d3045c6bab27fd769a3743f8d0a2a098605c0098327557eb0cb12f3c92468
```

Compared with the prior corrected six-window result, every A0/A3 ordered trace
hash, strict A/A receipt, A/B repeatability field, comparison field and metric
record was unchanged. The public-source integration introduced no observed
closed-loop behavior drift.

## Interpretation and next gate

This work closes a structural integration gap only. It proves that an external
closed-loop producer can be checked against a repository-owned, single-delay,
non-actuating receipt contract. It does not prove that the private plant is a
calibrated representation of the current vehicle or that its path reference is
independent ground truth.

The previously tested A3 candidate remains rejected. The new contract must not
be used to relabel its repeatability as a performance pass.

Remaining mandatory gates are:

- authenticate plant calibration and applicability to the exact vehicle/software;
- provide independent center/edge or equivalent primary path truth;
- evaluate an accepted candidate against frozen regression thresholds;
- qualify uncertainty and complete replay/closed-loop evidence;
- only then evaluate continuous non-actuating shadow non-interference.

No current result permits profile activation, CAN output, safety-limit changes or
vehicle operation.

## Final regression verification

```text
public admission contract       8 passed / 12 subtests
private D3Y focused suite      29 passed
AutoTune + controls           483 / 483 passed
Ruff                           PASS
SCons                          100% complete
Git whitespace check           PASS
```

The sanitized machine-readable result is
`cyber-validation-lateral-closed-loop-admission-result.json`, SHA-256
`9b658c0e84bd5e234fc6e1175850056eed6353f831af32dea13ae008ff57b1c0`.
It contains no route identity, log path, raw trace or private plant implementation.
