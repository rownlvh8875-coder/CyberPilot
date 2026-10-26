# Prospective D3Y plant-calibration protocol

## Purpose

The historical D3Y validation is descriptive and cannot be retroactively
converted into a calibration qualification. CyberPilot therefore freezes a new
protocol before any future evaluation data are opened.

```text
protocol ID              CYBER_D3Y_PROSPECTIVE_V1
freeze time              2026-10-03T12:11:42Z
policy file SHA-256      881ea714b0fd0fb5baf27c590847e9e641d52b54bffb8ca75da7a36d7820d36d
canonical policy SHA-256 a3419a10bf24592c23ccb6e48662ba1235e89029b50e866ac894a47c82300119
```

The policy is valid only for the bound Santa Fe model, adapter, plant builder
and validation runner identities. Changing any identity requires a new protocol.

## Predeclared coverage and timing gates

- collection must start strictly after the protocol freeze time;
- collection end must precede metadata-manifest freeze;
- semantic content must remain unopened until after the manifest is frozen;
- evaluation must begin after manifest freeze;
- at least 4 validation routes, 16 sequences and 5,000 eligible pose samples;
- stability radius at most 0.98;
- independent primary position truth is mandatory;
- external reproduction is required before review-ready status;
- validation refit, candidate-output model selection and all vehicle authority are forbidden.

| Horizon | min windows | min samples | max yaw RMSE | min yaw corr | max heading endpoint RMSE | max path endpoint RMSE | max path XY RMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 s | 200 | 4,000 | 0.005 rad/s | 0.970 | 0.005 rad | 0.05 m | 0.025 m |
| 5 s | 40 | 4,000 | 0.006 rad/s | 0.960 | 0.025 rad | 0.75 m | 0.35 m |
| 10 s | 20 | 4,000 | 0.006 rad/s | 0.955 | 0.040 rad | 2.00 m | 0.90 m |

These are future operational acceptance limits. They do not re-score or qualify
the historical evidence used to define the development direction.

## Current status

A metadata-only scan examined 5,602 local rlog/qlog candidates after the freeze.
No post-freeze driving log exists:

```text
post-freeze log files  0
post-freeze bytes      0
scan SHA-256           c4ddcb49cdb3bbabf8ab00b49dd591b44d729d6c0edc118d74ba3175ac49f0a8
```

Current state:

```text
PROTOCOL_FROZEN_AWAITING_POST_FREEZE_EVIDENCE
```

Historical evidence is explicitly ineligible with
`DATA_PREDATES_PROTOCOL_FREEZE`. No candidate, qualified replay, runtime,
promotion, shadow or vehicle authority is created.

## TDD verification

```text
prospective protocol tests  9 passed / 23 subtests
Ruff                        PASS
```

The tests cover post-freeze timing, manifest-before-content ordering, platform
identity, minimum coverage, stability, independent truth, horizon thresholds,
validation leakage, forbidden authority and review-only external reproduction.

## Final verification and integrity

```text
prospective protocol tests  9 passed / 23 subtests
AutoTune + controls        501 / 501 passed
Ruff                        PASS
SCons                       100% complete
Git/privacy audit           PASS
```

- policy file SHA-256: `881ea714b0fd0fb5baf27c590847e9e641d52b54bffb8ca75da7a36d7820d36d`
- canonical policy SHA-256: `a3419a10bf24592c23ccb6e48662ba1235e89029b50e866ac894a47c82300119`
- freeze result SHA-256: `b6de679889f09a3575e404ecd8699e6100412482b9ae7bf7d804a6d2f04c6841`
- post-freeze metadata scan SHA-256: `c4ddcb49cdb3bbabf8ab00b49dd591b44d729d6c0edc118d74ba3175ac49f0a8`

Candidate generation, qualified replay, runtime acceptance, promotion and
vehicle/CAN writes remain false.
