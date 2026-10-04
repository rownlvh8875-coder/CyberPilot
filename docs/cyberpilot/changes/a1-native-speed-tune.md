# A1 synthetic native speed-tune integration

## Identity and purpose

Cyber Lateral / AutoTune validation; implemented and reviewed, offline-only. Enable a separate
offline A1 experiment applying speed-table factor/friction to native control,
not requested-command post-scaling. Branch feature/cyber-autotune; baseline
b555b8a59be05f6b664db830e3dd5ee674c93b56. Synthetic inputs only; no vehicle tune.

## Original references

CyberPilot current native worker, speed_aware_tune evaluator and upstream
LatControlTorque/update_torque_parameters (MIT), at the baseline above; pinned
opendbc 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. Original openpilot baseline
c8fb906815530460ed156f14e09e1f312bb0f851. No external fork code copied.
ajouatom/openpilot hoya/c3-atune 0e9c589c1b83027146f909a9cdc306c2c665ceaf
informs only rejection/reporting design: no preset fallback, direct Params write,
external AI, current/recorded epoch conflation, or partial multi-parameter apply.
Caller path: frozen fixture -> admission -> native update -> requested torque
receipt; never vehicle controller/EPS. No model execution or new dependency.

## Changes and expected effect

Add A1 schedule, fixture/experiment, worker and tests under tools/cyber_autotune;
extend only the existing offline native worker's private loop. Preserve public v1
schemas and command-only optimizer guard. Alternative post-scaling rejected.
Small synthetic factor/friction changes must actually affect unsaturated output.
Factor unit (m/s^2)/normalized command; friction normalized command. Synthetic
baseline 4/.125; knot speeds 0/10/20/30 m/s. Maximum deltas 1/16,1/128 and per-frame
changes 1/64,1/1024; absolute domains [3.5,4.5], [0,.25]. Software-test coordinates,
not HKG calibration or safety bounds. Response identity only; delay unchanged.
Each arm owns fresh CP/controller/VM; history persists inside the arm. Whole
schedule admitted first; invalid inputs abort, never fabricate fallback rows.
No controlsd, online estimator, model, planner, PID, opendbc/panda or limits edit.
Maintenance cost: small private offline worker extension and separate response.

## Regression risk and acceptance

Risks: float storage mismatch, history reset, no-op tuning, stale source/receipt,
v1 output changes, synthetic PASS misrepresented as qualification. Require exact
disabled/identity baseline output and ordered-state parity, actual parameter
readback and native output differences for factor/friction/combined fixtures,
fresh-process determinism, fail-closed malformed/late-invalid inputs.
Only synthetic fixtures; no holdout/private data. Rollback: leave CLI unused or
revert this isolated patch, no active profile exists. Independent review required.

## Validation method and actual results

| Stage | Method | Actual status |
| --- | --- | --- |
| Preflight | Native worker + runner regression | 21 passed, exit 0, before changes |
| Targeted | A1 + native worker/runner + source imports/resources | 38 passed, exit 0 |
| AutoTune+controls | Supported runner, Ubuntu 24.04/Python 3.12 venv | 654 passed, exit 0 |
| Default runner | Unchanged tests, verified public fixture mirror, activated venv | 1561 passed /42 skipped /1 xfailed, exit 0, 366.60s |
| Ruff / build | Ruff affected tool/control areas; SCons -u -j4 | PASS, exit 0 each |
| Native requested-torque | Two fresh source-bound five-fixture runs | Byte-identical aggregates; disabled/identity exact, all three nonconstant variants non-noop |
| Independent review / privacy | Whole patch read-only review; selected publication files | No Critical/Important; one deferred Minor; privacy PASS |
| Qualified replay | Recorded/native admission | BLOCKED, not provided by this increment |
| Calibrated closed loop | Independent plant/truth | NOT_RUN |
| Non-actuating shadow | Device isolation and evidence | NOT_RUN |

## Handoff

No performance improvement or qualification claim. Verification gates and independent
review passed for this increment. REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED;
overall vehicle status NOT_READY. This feature never authorizes vehicle use.

## Offline invocation and receipt semantics

In the prepared Linux virtual environment, use the bounded supervisor:

```python
from openpilot.tools.cyber_autotune.a1_experiment import build_request, run_experiment

result = run_experiment(build_request('combined'), timeout_s=20.)
print(result['status'])
```

Allowed fixtures: disabled, identity, factor, friction, combined. All generate
owned synthetic inputs. There is intentionally no real-log or arbitrary table API.
The envelope binds native and adapter files; successful receipts bind generated
CP, full-rate frames, table, environment, effective schedule and ordered native
state hashes. Schedule rows are [effective speed, requested factor, requested
friction, native factor, native friction]. No current machine Params are read.
Both arms start fresh once, not once per frame. State schema native-torque-state-v1
includes torque parameters, PID p/i/d/f/control/speed/limits, saturation timer,
acceleration history and jerk-filter state. Static gains, offset, deadzone and
normalized torque limit are invariant; native acceleration-space limits track
factor. Input lateral delay is fixed and unchanged. Driver override is an observed
input, not an inferred dissatisfaction label. No partial candidate survives errors.
PASS means software/native connection and synthetic parity/non-noop checks only.
Unavailable center deviation, edge margin and physical steering jerk remain
unavailable. No report field grants runtime/profile/CAN/promotion authority.

## Verification identities and preserved failures

The full-suite supervisor recorded actual returncode0, no timeout, unchanged
source/overlay/submodules and identical verified public input before/after.
Receipt SHA256: `4631823085e6a7ee10192f87a83fe96fdd34432658a6d39367990043b43c3b05`.
Two native aggregate runs share SHA256
`3c7775734d3bfa8a58d0a8fc68da87f85f7105186e78fed706c2af21733e9bf5`.
Each fixture has601frames: disabled/identity0 changed output frames; factor,
friction and combined each570 changed frames. Maximum absolute requested-command
differences are respectively0.00007394953775801197,0.00024045905458422445,
0.00019241608529768292. These numbers establish application, not improvement.
Independent review additionally compared the original Git-object native worker
against the changed v1 path: entire601-frame result dictionaries exactly equal.

Initial bare full run lacked the already verified public fixture mirror setting;
cancelled/incomplete evidence is retained, not PASS. The first mirrored run had
1560pass/42skip/1xfail/1fail: loggerd audio inspection could not find ffprobe because
only venv Python, not its toolchain PATH, was selected. Exact isolated loggerd
tests reproduced10pass/1fail; activating the existing venv yielded11pass. The next
full run had1560pass/42skip/1xfail/1error from a public AGNOS server HEAD disconnect.
Its unchanged isolated test passed on retry, then the final whole suite passed as
listed above. No installation, source/test edit, threshold change, exclusion or
reference update was used to resolve either environment/network failure.

Deferred Minor: generic WORKER_FAILED currently omits the child returncode; it
does not distinguish rejection from individual terminating signals. Failure
receipts remain fail-closed, but detailed cause diagnosis is not claimed. Source
hashes bind selected contents, not trusted producer authentication or exhaustive
binary supply-chain provenance. Native dependency packages are versioned.

Final executable/test SHA256 identities (documentation-only closeout follows):

| File under openpilot/tools/cyber_autotune | SHA256 |
| --- | --- |
| a1_experiment.py | 2c5988dfd80151fbee2cf7c4493a7b5dceca5525df36da3b0555b19c3341f639 |
| a1_schedule.py | c9c6a2d8ffbcb95ffd004a3a6e98130b5a28cf51fa4810b8cfdbf11836dc57ff |
| a1_worker.py | 57e5ca499f30f4fa8583ac1febc50413f888a563003c886b52cff89e5531b0ef |
| native_worker.py | 4dfde93aa5c08206a1dbc387acf6459d77a8b14f91fc73b66e718336cc6a279f |
| tests/test_a1_experiment.py | bf6cb528eb81a759179ccdb3d7ba97dd8212523efd6536bc04935b1431abdf93 |
| tests/test_a1_schedule.py | e4d1f8771928b180cd10bbf11b907716f94209f0c50154f9ccb46d870912758e |
