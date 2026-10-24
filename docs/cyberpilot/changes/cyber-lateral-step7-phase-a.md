# Cyber Lateral Step 7 Phase A

## Identity and purpose

- Feature / area: Cyber Lateral
- Status: observer-only implementation complete; local software verification passed; vehicle promotion not qualified
- Purpose: connect an optional diagnostic coordinator around the existing native lateral controller while preserving exact controller output and state.
- Scope: DISABLED and OBSERVE_ONLY only. No active path, friction, NNLC, parameter application or actuator authority.
- Baseline: CyberPilot `19062e9b0bfc98a132e0fd8a2e2e540fe8fdeeeb`.

## Original references and license handling

- Openpilot: `c8fb906815530460ed156f14e09e1f312bb0f851`, MIT license,
  [`controlsd.py`](https://github.com/commaai/openpilot/blob/c8fb906815530460ed156f14e09e1f312bb0f851/openpilot/selfdrive/controls/controlsd.py)
  and its native `latcontrol_*.py` implementations. The native controller remains the executable authority.
- Sunnypilot: `a5f44653d7f43ad57fef2f546f3916ec4cbf3c56`, Custom MIT License,
  [`latcontrol_torque_jerk_aware.py`](https://github.com/sunnypilot/sunnypilot/blob/a5f44653d7f43ad57fef2f546f3916ec4cbf3c56/openpilot/sunnypilot/selfdrive/controls/lib/latcontrol_torque_jerk_aware.py).
  Only the research question “does future lateral jerk retain one sign across the preview?” was independently reimplemented as a pure observer. No gain, torque, friction, PID, NNLC or controller state code was copied.
- Carrotpilot: `c57d0ff11f766b7fd70e9a9eaec1247b623ffbea`, no root LICENSE/COPYING found in the fixed tree,
  [`lateral_planner.py`](https://github.com/geniuth2/openpilot_carrot/blob/c57d0ff11f766b7fd70e9a9eaec1247b623ffbea/selfdrive/controls/lib/lateral_planner.py).
  Only lane/path quality and bias diagnosis was independently reimplemented. No Carrot threshold, offset command, steering-ratio override, MPC or actuator logic was copied.
- Opendbc: `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.
- Full source paths, symbols and hashes: `outputs/CYBER_LATERAL_SOURCES_20261001.json` in the local handoff workspace.

## Implemented changes and expected effect

- Runtime integration: exactly one native lateral update per control tick; the returned native tuple remains the sole actuator source.
- DISABLED is the default and does not evaluate the optional context factory or read new model fields.
- OBSERVE_ONLY creates immutable current-frame observations with monotonic identity, validity, controller type and source provenance only on a newly updated model frame. Observation runs after both native control publications, so it cannot delay the current actuator-bearing message.
- Current `modelV2.acceleration.t/y` feeds a pure future-jerk observer. The model path is boundedly interpolated onto the fixed ego-lane/road-edge station axis over their overlap; extrapolation, fewer than three common stations and shape mismatch are invalid.
- Offline metrics validate units, common uniform time, independent lane reference and declared delay. They never search candidate output for a better delay, and emit separate straight/entry/apex/exit delay-residual aggregates from caller-frozen labels.
- Read-only metadata centralizes vehicle, controller, user-preference and safety classes. Every AutoTune proposal returns `accepted=False`; forbidden limits and gates have explicit entries.
- Failure behavior: native exceptions propagate; optional diagnostic failures clear diagnostics and retain the native result.
- Safety: no panda/opendbc, actuator limit, driver override, engagement, DM, brake/cancel or fault-handling changes.

## Regression risk and acceptance

- Primary risk: a wrapper invokes a stateful controller twice or changes update/reset order.
- Required acceptance: exact native output and internal state parity for torque/PID/angle/curvature across disabled, observe-only, inactive, override, limited and reversal sequences.
- Rollback: remove the optional coordinator construction and single call seam; native controller files remain unchanged.
- Promotion: unit and synthetic parity do not qualify replay, closed loop, shadow or road use.

## Validation method and actual results

| Check / stage | Method | Actual result and limits |
| --- | --- | --- |
| Existing lateral baseline | `test_latcontrol.py` and `test_latcontrol_torque_buffer.py` | PASSED before edits in the dedicated worktree environment: 5 passed, exit 0, Python 3.12.13 |
| Targeted current patch | six Cyber Lateral test files | PASSED: 45 passed, exit 0 |
| Affected controls directory | `python tools/test_runner.py openpilot/selfdrive/controls/tests` | PASSED: 108 passed, exit 0 |
| Repository default runner | `python tools/test_runner.py` | FAILED: 998 passed, 44 skipped, 1 xfailed, 1 failed; only `TestLoggerd.test_record_audio_0` failed |
| Baseline comparison for repository failure | isolated loggerd audio test on exact base `19062e9` | FAILED with the same assertion, confirming a pre-existing WSL/loggerd environment failure rather than a Step 7 regression; test unchanged and not skipped |
| Ruff | all changed Python product and test files | PASSED, exit 0 |
| Build | activated dedicated venv, then `scons -u`, with exact gitlinks initialized from preserved local clones | PASSED, exit 0; an earlier non-activated invocation failed because build tools were absent from `PATH` |
| Synthetic baseline A/A | native torque/PID/angle/curvature parity and offline metric zero-delta fixtures | PASSED; synthetic plumbing evidence only |
| Replay vs baseline | qualified lateral input required | not run |
| Simulation / closed loop | calibrated lateral plant required | not run |
| Shadow | isolated non-actuating device run required | not run |

## Handoff

- Verified effect: exact native tuple/log/internal-state parity in DISABLED and OBSERVE_ONLY for torque, PID, angle and curvature fixtures; diagnostic failures cannot replace native output.
- Provenance: runtime firmware/model identity is deliberately absent in `controlsd`, so `provenance_complete=False` until an authoritative source supplies both.
- Step 5: remains independently incomplete; its qualified replay, calibrated closed loop and non-actuating shadow gates are not promoted by this Step 7 work.
- Vehicle application: not authorized.
- Commit / push / merge: not run by user instruction.
