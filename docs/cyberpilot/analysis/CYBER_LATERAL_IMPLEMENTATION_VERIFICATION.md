# Cyber Lateral Step 7 Implementation Verification

## Decision

The first Cyber Lateral implementation is locally software-verified for its DISABLED and OBSERVE_ONLY scope. The repository-wide runner has one baseline-reproduced WSL loggerd audio failure, documented below; no Cyber Lateral or controls test failed. This implementation is not qualified for active lateral control, replay promotion, calibrated closed loop, device shadow or road use.

## Fixed identity

- CyberPilot base: `19062e9b0bfc98a132e0fd8a2e2e540fe8fdeeeb`
- Local branch: `work/cyber-lateral-step7`
- Environment: Ubuntu 24.04 WSL2, Python 3.12.13, dependency versions fixed by `uv.lock`
- Gitlinks:
  - msgq `0e266c1dbcf7328beee3e57b4a8688555387c877`
  - opendbc `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`
  - panda `92eb565169fd553f4dfaf508c1a3f8dbc14fbfbf`
  - rednose `8671c17c3a4cdc4be5df07a068039e2da5b94eaa`
  - teleoprtc `1aa8fc433bef1519a95c0700c96258c3be6dfb34`
  - tinygrad `9d0446a4ba8a532c8b674fb6ad795af015cd9dcf`

The first apparent 5-test baseline used an editable environment pointing at the original checkout and was discarded. The baseline reported here was rerun from the dedicated Step 7 worktree and its own `.venv`.

## Authority and failure order

`controlsd` still constructs one upstream torque, PID, angle or curvature controller. One narrow seam invokes `self.LaC.update` exactly once and returns the same tuple object. Actuator assignment, finite checks, `clip_curvature`, controller reset order, driver override and panda/opendbc safety remain upstream-owned.

- DISABLED: returns the native tuple without calling the diagnostic context factory.
- OBSERVE_ONLY: native control and both actuator-bearing publications complete first. Diagnostics then read already-subscribed `modelV2`, `carState`, `vehicleParameters` and `lateralDelay`, and only when `modelV2` was updated in that cycle.
- Native exception: propagates unchanged; no retry.
- Diagnostic/context exception: clears current observation and returns the exact native result.
- Duplicate/reversed model timestamp, reversed async source timestamp, inactive control, steering override, incomplete/mismatched binding or non-finite input: invalidates the current observation.
- Runtime firmware and model identity are not authoritative in `controlsd`; both remain absent, so runtime provenance is incomplete and cannot support tuning admission.

## Reimplemented observer logic

### Sunnypilot concept

Fixed source: `a5f44653d7f43ad57fef2f546f3916ec4cbf3c56`, `latcontrol_torque_jerk_aware.py`, Custom MIT License.

CyberPilot independently implements linear interpolation of the current upstream `modelV2.acceleration.t/y` horizon, segment lateral jerk, sign consistency and minimum absolute jerk. Mixed-sign, short, non-finite or out-of-horizon data is invalid. The result has no friction, torque, gain or actuator output.

### Carrot concept

Fixed source: `c57d0ff11f766b7fd70e9a9eaec1247b623ffbea`, `selfdrive/controls/lib/lateral_planner.py`; no root license file was found in the fixed tree.

CyberPilot independently computes model-path bias relative to the current ego-lane center, lane-width statistics, confidence and an edge-clearance proxy. Runtime extraction uses the explicit fixed lane/edge station axis from `modelV2` and linearly interpolates the model path only over the station overlap. It never extrapolates and requires at least three overlapping stations. Lane change, lost/crossed lanes, invalid probability/std or geometry mismatch is invalid. No Carrot threshold, offset command, MPC or actuator behavior is copied.

## Offline metrics and AutoTune boundary

- Metric inputs are immutable, finite, unit-tagged and use one uniform pre-aligned time axis.
- Curvature phase residual uses only the caller-declared nonnegative delay; no result-fitted delay search exists. Separate straight, entry, apex and exit aggregates make the caller-frozen phase labels observable in evidence.
- Lane-center and inside/outside metrics require a separate source identity and are invalid when the model desired path is reused as its own reference.
- Steering jerk is the third derivative of steering angle in `deg/s^3`.
- Saturation duty and driver-intervention rising-edge count are separate metrics.
- Metadata records owner/class/stage/controller binding, source, unit, default, bounds, rate limit, confidence, valid domain, safety and tuning flags.
- All proposals are rejected. Unknown, forbidden, malformed, insufficient-confidence, unbound, controller-mismatched, evidence-missing, unreviewed-bound and out-of-bound cases have distinct reasons. No Params, CAN, controller or application callback exists in the admission module.

## Verification evidence

| Status | Check | Result |
| --- | --- | --- |
| PASSED | Dedicated pre-edit upstream lateral baseline | 5 passed, exit 0 |
| PASSED | Current targeted Cyber Lateral regression | 45 passed, exit 0 |
| PASSED | Current affected controls test directory | 108 passed, exit 0 |
| FAILED (baseline-reproduced) | Current repository default runner | 998 passed, 44 skipped, 1 xfailed, 1 failed; `TestLoggerd.test_record_audio_0` expected an audio stream that WSL did not record |
| FAILED (baseline-reproduced) | Isolated loggerd audio test | current patch: 1 failed; exact base `19062e9`: the same 1 failed with the same assertion, so this is not introduced by Step 7 |
| PASSED | Ruff on all changed Python files | exit 0 |
| PASSED | `scons -u` with the dedicated virtual environment activated | exit 0; an earlier invocation without the venv on `PATH` failed to find build tools and is not treated as build evidence |
| PASSED | Synthetic native oracle parity | exact steer, lateral output, serialized log and controller state for torque/PID/angle/curvature in both modes |
| PASSED | Synthetic offline baseline A/A | exact zero path/cross-track/curvature/lane/jerk/oscillation/delay residual deltas |
| NOT RUN | Qualified lateral replay | suitable frozen qualified input/reference not selected in this task |
| NOT RUN | Calibrated lateral closed loop | matched lateral vehicle plant and frozen domain/thresholds not supplied |
| NOT RUN | Non-actuating device shadow | device connection and separately approved shadow procedure deferred |
| NOT RUN | Live CAN, flashing, deployment, road test | prohibited by scope |

The synthetic checks prove plumbing and non-interference only. They do not estimate real vehicle path error, actuator delay, stability margin or driver-intervention performance.

The loggerd failure was not skipped, weakened or modified. It is outside the changed paths and reproduces at the exact fixed base, but the repository-wide runner is still reported as failed rather than passed.

## Prohibited-path audit

No product diff is present under cereal schema/services, modeld, plannerd, locationd estimators, opendbc or panda. No new Params key, service, process, dependency, model weight, NNLC data, safety limit or device operation was introduced.

## Remaining promotion gates

1. Freeze a qualified lateral replay manifest with controller/CP/firmware/model/config/input identity, independent path/lane reference, units, masks and declared delay before viewing candidate results.
2. Run repeatable baseline A/A and baseline-versus-observer replay. OBSERVE_ONLY must remain exact at native output/controller state.
3. Calibrate a lateral plant at the actual controller-input stage, including timestep, delay, speed, curvature, bank, friction and uncertainty domain without double-counting model/controller/plant delay.
4. Freeze metric thresholds and worst-segment rules before candidate closed-loop results.
5. Only after replay and calibrated closed-loop gates pass, perform separately approved non-actuating device shadow. Active output requires a new design, tests and approval.

Step 5 remains independently incomplete. Its remaining longitudinal qualified replay, calibrated closed loop and non-actuating shadow gates are unchanged.
