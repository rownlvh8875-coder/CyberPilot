# Cyber Lateral closed-loop structural admission

## Identity and purpose

- Area: STEP7/STEP9 offline lateral closed-loop validation.
- Evaluated public source HEAD: `dfa0ff8ff465962ecb0e0db2a0f2536ac0a746c1`.
- Purpose: admit aggregate-only external plant/controller receipts without
  importing private logs, route identities, raw traces, model coefficients or
  private plant code.
- This is not performance approval, shadow permission, profile activation,
  CAN transport or vehicle-use authorization.

CyberPilot owns two authority-free contracts:

- `plant_calibration.py`: verifies aggregate calibration evidence and its limits;
- `lateral_closed_loop.py`: binds that evidence to immutable closed-loop receipts.

The private producer may calculate a receipt, but it cannot grant qualification,
runtime acceptance or promotion to itself.

## Calibration evidence bound to the receipt

The private D3Y evidence chain was revalidated as an aggregate-only receipt.

```text
status                              DESCRIPTIVE_CALIBRATION_EVIDENCE
evidence-chain receipt SHA-256      db035e6d6c2f763953c6f1d8ac66111d30b5b9bf7402d885bb319d539f961f23
canonical evidence SHA-256          523f0a77eea1a8ea9c75a30b21d14c3e6550d4754a10b2ae561ebc1b9ff4a6ac
development routes                  8
validation routes                   4
validation sequences               17
eligible pose samples               6,359
model stability radius              0.9571762129
validation refit                    false
candidate-output model selection    false
deterministic trace / pose          true / true
```

The evidence is internally consistent and development/validation roles are
disjoint. It is not a calibration qualification because the historical protocol
did not precommit an acceptance threshold, the validation was descriptive, its
position reference was not independent primary truth, external reproduction is
absent, and the exact current platform has not been prospectively revalidated.

## Structural receipt contract

The receipt binds:

- software, controller, adapter, plant and plant-calibration SHA-256 identities;
- domain, input, reset, metric, environment and timebase identities;
- contiguous frame indices and fixed control period;
- speed and normalized-command bounds;
- ordered trace samples and their digest;
- exactly one physical actuator-delay owner: `PLANT`;
- controller prediction delay as metadata, not a second physical delay queue.

Every receipt asserts `sendcan_forwarded`, `live_can`, `vehicle_write`,
`parameter_write`, `runtime_accepted` and `promotable` as false. A producer claim
of `plant_calibration_qualified=true` is rejected as forbidden authority.

`DESCRIPTIVE_CALIBRATION_EVIDENCE` is admitted structurally with
`PLANT_CALIBRATION_DESCRIPTIVE_ONLY`; `CALIBRATION_EVIDENCE_READY_FOR_REVIEW`
would still retain `PLANT_CALIBRATION_REVIEW_REQUIRED`. Neither status creates
closed-loop qualification.

## Calibration-bound six-window revalidation

The existing external D3Y adapter and frozen development manifest were rerun
with the plant-evidence receipt bound to both baseline and candidate arms.

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

All 12 receipts retained:

1. `PLANT_CALIBRATION_DESCRIPTIVE_ONLY`
2. `INDEPENDENT_REFERENCE_UNVERIFIED`
3. `PERFORMANCE_GATE_NOT_EVALUATED`

Every receipt reported `qualified_closed_loop=false`, `runtime_accepted=false`
and `promotable=false`.

The aggregate output repeated byte-for-byte:

```text
06332c1492de07f92b26aae9a833af081063160a454b38cef02eed8f928703c7
```

Compared with the prior corrected result, all A0/A3 ordered trace hashes,
strict A/A records, A/B repeatability fields, comparison fields and metric
records were unchanged. Binding the calibration evidence introduced no observed
closed-loop behavior drift.

## Verification

```text
closed-loop admission tests      9 passed / 12 subtests
plant evidence tests             8 passed / 23 subtests
private D3Y focused suite       29 passed
AutoTune + controls            492 / 492 passed
Ruff                            PASS
SCons                           100% complete
Git whitespace / privacy audit  PASS
```

Sanitized machine-readable receipt:

```text
cyber-validation-lateral-closed-loop-admission-result.json
eed1bf817c37161b47d593e17082ee75514cb6e0de47909d107053cb7670001b
```

## Interpretation and next gate

This closes the plant-evidence identity gap but does not close the plant
qualification gap. The A3 candidate remains rejected and cannot proceed to
shadow.

Remaining mandatory gates are:

- a prospectively frozen or independently reproduced plant-calibration protocol
  with predeclared acceptance limits;
- independent center/edge or equivalent primary path truth;
- an accepted candidate that passes all frozen regression thresholds;
- uncertainty qualification and complete replay/closed-loop evidence;
- only then continuous non-actuating shadow non-interference testing.

No current result permits profile activation, CAN output, safety-limit changes,
shadow promotion or vehicle operation.
