# Isolated native longitudinal diagnostic

## Identity and purpose

- Area: Cyber Validation, STEP9. Implemented/reviewed; final full-PC run pending.
- Execute stock LongControl on explicit synthetic/exogenous state and plan samples.
- Requested acceleration only, not planner/event replay, CarController, CAN or a plant.
- HKG protocol label HYUNDAI_SANTA_FE_2022 is not qualification of the user's2021 vehicle.
- feature/cyber-autotune HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b plus uncommitted new files.

## Original references

- https://github.com/rownlvh8875-coder/CyberPilot feature/cyber-autotune at above HEAD;
  original upstream c8fb906815530460ed156f14e09e1f312bb0f851. LongControl unchanged between these.
- openpilot/selfdrive/controls/controlsd.py: enabled/event/CP conjunction, inactive reset,
  CI PID limits and LoC.update; controls/lib/longcontrol.py; common/pid.py, constants.py.
- opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 car/interfaces.py and hyundai/interface.py.
- Existing MIT openpilot/opendbc source remains in place; no Carrot/Mazda code imported/copied.
- Reuse native controller, not a rewritten control law. No model runs; inputs exogenous.
- Python3.12.13/Ubuntu24.04 pinned environment, existing cereal/opendbc/NumPy dependencies.

## Changes and expected effect

- New native_long_protocol.py: exact request fields, source/CP digest, timestamps and resource bounds.
- New native_long_worker.py: fresh source-bound native imports, fixed CP and wire normalization,
  stock activation/LoC and native limit lookup, finite checks, diagnostic trace.
- New native_long_runner.py: fixed isolated worker, owned timeout cleanup, strict response binding.
- New corresponding three tests; no runtime consumer/integration or lateral controller changes.
- Review fix adds source_imports.py and its test; both native workers now run with a fresh
  private empty bytecode prefix and writes disabled. Existing caches are not read/deleted.
  This intentionally changes earlier native_worker.py, not any lateral controller.
- Frozen EXPECTED_ACCEL_LIMITS=(-3.5,2.0)m/s² observes current CI PID limits; not panda safety
  or a tuning parameter. Source limit drift fails, never enlarges limits automatically.
- Fresh controller/window,10ms source timestep; no inserted delay or carry-over state.
- State names come from native enum constants. Before-update state mirrors controlsd epoch.
- Malformed/overflow/stale/timeout fails without samples; no active fallback is needed because
  there is no active connection. Parent gets generic codes, not native stderr/private content.
- Safety, driver override producer, CarController and longitudinal control code unchanged.
- Separate protocol chosen over changing reviewed lateral code; selected-source map maintenance
  required on future upstream revisions, not complete dependency/build attestation.

## Regression risk and acceptance

- Risks: wrong source/import identity, wire precision, stale state epochs, bounded arithmetic,
  CP flag override, confusing requested vs applied output or exogenous vs coupled replay.
- Accept exact repeatability on same synthetic inputs; native Float32 direct-reference equality;
  literal off/stop/start/clip expected outputs; all negative tests must reject. No relaxation.
- No holdout or private raw logs. Synthetic CP is not a device configuration or measured tune.
- Rollback: remove use of this offline tool; existing native/control behavior was never changed.
- One final independent review required. No promotion authority, all flags remain false.

## Validation method and actual results

| Check/stage | Method | Actual result/limits |
| --- | --- | --- |
| Focused unit/native | pytest three test_native_long_* files, Ubuntu24.04 |14 passed,89 subtests,5.76s,exit0; synthetic only |
| Package/controls/Ruff | full tools/cyber_autotune plus controls tests |214 package/694subtests19.64s;346affected12.02s,exit0; Ruff/diff PASS |
| Cache/source guard | real same-size/same-second stale cache + both child entrypoints |3 tests2subtests PASS; original symptom1!=2 reproduced before fix |
| Baseline diagnostic | same CP/frames on c8fb and1ee1, fresh-process repeats |6 longitudinal and6 lateral runs repeat identically; candidate=current, not route replay |
| Qualified replay | complete planner/event/controller source-bound process replay | NOT_RUN; missing qualified producers/data |
| Closed loop | calibrated applied-input plant and independent tracking truth | NOT_RUN; requested accel is not plant input qualification |
| Shadow | continuous non-actuating qualified runtime | NOT_RUN; no device connection |

## Handoff

- Verified focused synthetic behavior only; this cannot establish real braking or driver takeover safety.
- Initial test fixture mistakenly pinned nonexistent common/conversions.py; corrected to actual
  controlsd common.constants.CV. Native enum int serialization fixed before first passing run.
- Independent review0Critical1Important0Minor; Important cache issue fixed RED->GREEN.
- Default PC before this change1236passed42skipped1xfailed1148.67sexit0. Updated run pending;
  no full-suite success is inferred from its predecessor. Existing tests/thresholds unchanged.
- No commit/PR/push/merge. No qualified optimization, performance improvement or vehicle readiness.
- Real-vehicle application NOT_AUTHORIZED; STEP8–10 overall PARTIAL/NOT_READY.
