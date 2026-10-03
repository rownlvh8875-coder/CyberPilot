# Native longitudinal three-arm comparison

## Identity and purpose

- Cyber Validation STEP9, implemented/reviewed; current full-PC pending.
- Compare baseline/current/candidate requested acceleration with two repetitions each.
- Exogenous native inputs only, not process replay, measured vehicle response or active tuning.
- feature/cyber-autotune at1ee1eb07f6cc48526f4d61265abe317fe67cc23b plus uncommitted new files.
- Protocol vehicle label HYUNDAI_SANTA_FE_2022; does not establish actual vehicle applicability.

## Original references

- CyberPilot official repository https://github.com/rownlvh8875-coder/CyberPilot, branch/HEAD above.
- Reuses local native_long_protocol/runner and comparison.ARMS/SCENARIO_TAGS. Native stock
  LongControl source and opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 referenced in
  cyber-validation-native-longitudinal.md; no third-party control logic copied or changed.
- Flow: immutable per-arm payloads -> preflight -> six fixed native runs -> validate each
  response -> ordered repeatability -> aggregate diagnostics plus revalidation report.
- No model/plant; existing Python3.12.13/Ubuntu24.04 environment, no added dependency.

## Changes and expected effect

- Added native_long_experiment.py, tests/test_native_long_experiment.py; no upstream edits.
- Same frames/fingerprint/control owner across three arms; per-arm CP/source identity explicit.
- Repeated rows and digests must match. Any incomplete arm suppresses all comparisons.
- Requested acceleration differences in m/s²; requested rate RMS in m/s³, not vehicle jerk.
- Native PID endpoint occupancy, not actuator/panda saturation; stopping-state fraction,
  not stopping distance or lead/cut-in effectiveness. No new tuning constants or thresholds.
- Each repetition fresh state via native worker; no added delay/warmup or hidden filter.
- Failure status missing, never fabricated zero; bounded owned lifecycle reused, interrupts
  propagate. False runtime_accepted/promotable always, highest result REVALIDATION_REQUIRED.
- Alternatives: shared-axis refactor deferred to avoid modifying reviewed interfaces;
  scratch-only orchestration inadequate for reusable response validation/reporting.
- Maintenance: small duplicate orchestration with explicit units; no control merge risk.

## Regression risk and acceptance

- Wrong input ownership, stale CP/source responses, reordered traces, partial favorable
  summaries, or diagnostic/physical metric confusion must fail explicit tests.
- Accept exact same-input repeats; hand-derived diagnostic equality; no physical acceptance
  threshold or candidate ranking invented. Synthetic CP/frame inputs, no holdout/private logs.
- Rollback is not invoking this offline module; active stock behavior never changed.
- One independent code review; no result grants promotion, deployment or vehicle authority.

## Validation method and actual results

| Check/stage | Actual result |
| --- | --- |
| Focused TDD | missing-module RED->7 tests21subtests PASS3.70s,exit0 |
| Ruff | new module/tests PASS |
| Package/controls/full PC |225package725subtests29.75s;357affected14.83s exit0 after separate cleanup fix; prior1328 run12605 pre-module pending |
| Source-isolated baseline comparison |6new API executions,11samples each, repeated/equal; synthetic current-as-candidate only |
| Independent matrix review |0Critical0Important0Minor;7tests21subtests3.78s plus fault/identity probes |
| Qualified replay / calibrated closed loop / continuous shadow | NOT_RUN; no adequate measured producers/plant/authority |

## Handoff

- Verified initial protocol/statistics/failure behavior, not physical improvement.
- Initial affected352PASS1FAIL retained; separate cleanup correction RED->GREEN and final
  affected357PASS. Current full-PC pending. Real identification/confidence and
  primary metrics/plant/coupled processes remain incomplete; do not convert them to zero.
- No commit/PR/push/merge. No device connection, active profile update or vehicle permission.
