# Cyber Long Phase C — non-actuating offline admission

## Identity and purpose

- Area: Cyber AutoTune / Cyber Long. Status: implemented offline rejection contract; no tuning authority or native qualification.
- Purpose: centrally describe parameter ownership/units and reject unsafe or unqualified offline proposals.
- Scope: every proposal rejected in this first version; no apply engine, persistence, online learning, CP/Params writes.
- Vehicle applicability: no qualified target vehicle or approved bounds. Unknown provenance is incomplete.
- feature/cyber-long, baseline c8fb906815530460ed156f14e09e1f312bb0f851; local uncommitted file hashes in verification record.

## Original references

- commaai/openpilot master c8fb906815530460ed156f14e09e1f312bb0f851, root MIT LICENSE.
- longitudinal_planner.py reads CP.longitudinalActuatorDelay; longcontrol.py uses acceleration-error PID with CP longitudinalTuning.kiV/kiBP.
- CI/opendbc global limits and separate per-vehicle CAN/safety limits remain authoritative, not tunable through this API.
- opendbc 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76; panda 92eb565169fd553f4dfaf508c1a3f8dbc14fbfbf, unchanged/uninitialized.
- No model/firmware artifact available. No Carrot code copied or gain/delay adopted.
- Step 4 concepts: separate physical characteristics, current-controller gains, preferences and safety; null bounds deny use.

## Changes and expected effect

- types.py adds frozen metadata/proposal/assessment. params.py owns immutable registry and pure admission checks.
- assess_tuning_proposal has no actuator/CP/Params callback and returns accepted=False for all proposals.
- Registry source strings include pinned upstream symbol identity. Defaults for vehicle-specific/variable stock values are None,
  not a fictitious universal calibration; min/max/rate/confidence are None because unreviewed, not unbounded.
- Physical delay (s), acceleration integral gain (1/s) are research-only; preferences and safety entries are forbidden/read-only.
- Confidence uses dimensionless [0,1] as input format, not an acceptance threshold. No learning/tuning safety constants introduced.
- Fail closed on unknown parameter, wrong unit, invalid number, missing/mismatched vehicle/firmware/model/epoch/evidence,
  unreviewed bounds or disabled tuning. User/safety policy never writable.
- State ownership/reset/rollback: no mutable admission state or applied config; existing validated upstream config is untouched.
- Safety boundary: panda/opendbc/driver monitoring/takeover/engagement unchanged; no effect on current planner/LoC outputs.
- Upstream conflict: independent module low risk; unit/source semantics must be reviewed when CP/LoC contracts change.

## Regression risk and acceptance

- Risk: callers misinterpret a diagnostic assessment as permission. accepted is never True and API has no application path.
- Acceptance: all malformed, unsafe, preference, unknown and apparently valid synthetic proposals rejected, no input mutation.
- Fixtures: synthetic identities and values only, not empirical bounds or qualified tuning artifacts.
- Rollback: remove offline API; no changed CP/Params to roll back. Future apply design requires separate review/approval.
- Reviewer: fresh whole-change review; human promotion and vehicle authority separate, not provided here.

## Validation method and actual results

Planned: TDD portable real-function tests, immutable registry tests, configured lint/syntax and prohibited-file audit.
Actual: 12 admission methods and all 30 portable methods pass (WSL Ubuntu26.04, CPython3.12.14); Ruff exit 0.
Follow-up: same unchanged candidate in Ubuntu24.04.5/Python3.12.14 passes all 30 portable methods,
native planner/LongControl parity 5, affected controls 63, maneuver methods4 and full scons build.
This resolves the supported integration environment for those checks; it does not add tuning authority,
reviewed parameter bounds, evidence qualification or accepted proposals. Broader checks remain separately recorded.
Further authorized command-scoped public CA follow-up: unchanged source, full default PC runner exit0
(954 passed / 42 skipped / 1 xfailed, collected1029), affected controls rerun63 passed.
No private key export, permanent trust-store change or TLS bypass. These checks do not qualify tuning.
See [implementation verification](../analysis/CYBER_LONG_IMPLEMENTATION_VERIFICATION.md) for commands, hashes and blocked native stages.
Replay → closed-loop simulation → shadow remain prerequisites before any later actuating implementation.

## Handoff

- Verified effect: tested synthetic rejection only, not auto-optimization. All five registry entries remain read-only and non-tunable.
- Missing: vehicle/model/firmware evidence and reviewed bounds/rate/confidence. Supported native integration environment is now prepared and tested, not a remaining environment blocker.
- Publication follow-up: the user subsequently authorized commit/push to feature/cyber-long. No PR, develop/main promotion or road/device operation is included. Fresh controls regression passes63 (29.17s) and affected-file Ruff passes before publication; see verification section10. Next: fixed replay inputs/metrics and offline evidence design; no apply authority added.
