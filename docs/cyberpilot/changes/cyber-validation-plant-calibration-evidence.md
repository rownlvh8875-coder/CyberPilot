# D3Y plant calibration evidence admission

## Purpose and boundary

CyberPilot now owns an authority-free contract for aggregate plant-calibration
evidence in `openpilot/tools/cyber_autotune/plant_calibration.py`. The contract
does not open logs, fit a model, choose a threshold, run the plant, write a
profile, access CAN or grant vehicle/runtime authority.

A local evidence-chain runner verified private historical artifacts and emitted
only a sanitized aggregate receipt. Private route identities, local paths, raw
samples and model coefficients remain outside the repository.

## Verified evidence chain

- precommit, development, frozen-model, independent-validation, deterministic
  smoke and assurance-contract files are content-addressed;
- every cross-reference between precommit, development, frozen and validation
  artifacts matches the actual file SHA-256;
- the frozen model canonical digest was recomputed from the model object;
- development and validation route sets are disjoint;
- model structure was fixed before validation;
- no validation refit or candidate-output model selection occurred;
- the dual-axis smoke trace and pose repeat deterministically;
- all authority fields remain false.

## Aggregate evidence

| Item | Result |
|---|---:|
| development routes | 8 |
| validation routes | 4 |
| validation sequences | 17 |
| eligible pose samples | 6,359 |
| model stability radius | 0.9571762129 |
| validation refit | false |
| candidate-output selection | false |
| deterministic smoke trace / pose | true / true |

| Horizon | windows | samples | yaw-rate RMSE | yaw-rate correlation | path endpoint RMSE | path XY RMSE |
|---:|---:|---:|---:|---:|---:|---:|
| 1 s | 296 | 6,133 | 0.003796 rad/s | 0.980247 | 0.028656 m | 0.013406 m |
| 5 s | 52 | 5,226 | 0.005427 rad/s | 0.965010 | 0.884794 m | 0.386823 m |
| 10 s | 22 | 4,415 | 0.005126 rad/s | 0.960230 | 2.984862 m | 1.311992 m |

These are descriptive historical validation metrics, not newly selected
acceptance thresholds and not real-vehicle safety evidence.

## Assessment

The aggregate receipt is internally consistent and returns:

```text
DESCRIPTIVE_CALIBRATION_EVIDENCE
```

Remaining blockers are:

1. `ACCEPTANCE_THRESHOLD_NOT_PRECOMMITTED`
2. `DESCRIPTIVE_VALIDATION_ONLY`
3. `PRIMARY_POSITION_TRUTH_NOT_INDEPENDENT`
4. `EXTERNAL_REPRODUCTION_NOT_ESTABLISHED`
5. `CURRENT_PLATFORM_REVALIDATION_REQUIRED`
6. `QUALIFICATION_AUTHORITY_NOT_GRANTED`

The historical local-path pose reference is orientation-derived and is not an
independent absolute position or lane-center truth source. The existing
validation therefore cannot be retroactively relabeled as a calibration pass.
A future qualification requires a prospectively frozen protocol or independently
reproduced evidence with predeclared acceptance limits.

## Verification and integrity

```text
plant evidence contract tests   8 passed / 23 subtests
Ruff                            PASS
local evidence-chain run        byte-identical on repeat
```

Sanitized result SHA-256:

```text
db035e6d6c2f763953c6f1d8ac66111d30b5b9bf7402d885bb319d539f961f23
```

Canonical evidence SHA-256:

```text
523f0a77eea1a8ea9c75a30b21d14c3e6550d4754a10b2ae561ebc1b9ff4a6ac
```

The sanitized machine-readable result is
`cyber-validation-plant-calibration-evidence-result.json`. It contains no route
identity, log path, raw sample or model coefficient.

`plant_calibration_qualified`, `runtime_accepted`, `promotable`,
`performance_acceptance`, `recommendation_authorized` and `real_vehicle_write`
all remain false.

## Prospective successor protocol

The historical evidence remains descriptive. A separate protocol was frozen on
2026-10-03 before future content access:

- policy: `../policies/plant-calibration-prospective-v1.json`
- freeze result: `../policies/plant-calibration-prospective-v1-result.json`
- canonical policy SHA-256: `a3419a10bf24592c23ccb6e48662ba1235e89029b50e866ac894a47c82300119`

No local post-freeze driving log currently exists. Historical artifacts cannot be
submitted to this protocol and receive `DATA_PREDATES_PROTOCOL_FREEZE`.
