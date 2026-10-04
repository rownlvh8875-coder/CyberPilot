# A1 generic native closed-loop comparison

## Identity and purpose

Cyber Lateral / AutoTune offline validation; implemented, reviewed and verified.
Baseline e7b6607fcfc4283d8b4c9387a3d61f51192bf2d1, feature/cyber-autotune.
Compare already implemented A1 schedules using existing generic plants, never a
vehicle tune or active profile. Synthetic-only, no private data or holdout.

## Original references

CyberPilot native A1 and synthetic-native-v2 at baseline; upstream MIT native
LatControlTorque with pinned opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.
No fork code/constants copied. Catalog -> admitted schedule -> native controller
-> plant -> next measured feedback -> unchanged v2 metrics. No perception/model,
planner, EPS/CarController or new dependencies. Reuse measurement/plant code.

## Changes and expected effect

Separate a1_closed_loop experiment/worker/tests. Frozen v1/v2 untouched. Small
feedback glue reproduces original trace semantics; exact parity tests prevent
measurement drift. Reuse synthetic factor4/friction.125 and existing fixed A1
tables and bounds, no new parameter tuning. Each arm starts fresh once; updates
retain PID/history. Plant alone owns physical delay; native .15s history reference
compensation unchanged. Invalid first transition blocks before construction;
no synthetic warm-up or automatic clipping/fallback. Native normalized limit1
and every upstream safety/controller file unchanged. Maintenance: isolated glue.

## Regression risk and acceptance

All26 lateral cases/29delay pairs, all5 A1 variants. Fault cases must reject.
Disabled/identity trace parity and fresh-process deterministic reruns required.
Frozen metric policy4ff9dcfaa369cbdcee53f56a8db9c160efb3005a50f463e4125a1f41b74e8d35:
no ranked regression beyond1e-9; at least1% primary improvement; missing valid
coverage blocks favorable outcome. Negative lane margin/unresolved recovery
reject additionally. All authorities false even on synthetic favorable results.
Rollback: stop invoking offline worker or revert isolated change; no live state.
Independent review and all existing test/build/privacy gates before publication.

## Validation method and actual results

Final targeted parity/admission/feedback/worker/regression tests:45passed, exit0,
20.56s. Two independent full-catalog workers produced byte-identical reports.
Ruff and SCons pass. AutoTune+controls661passed, exit0,74.27s. Default runner
1568passed/42existing skips/1expected failure, exit0,282.99s. Activated existing
venv and verified public CI fixture mirror, no test/selection/reference edits.
Supervisor confirmed no timeout, source and public fixture unchanged.
Independent review: no Critical/Minor, one Important policy revalidation gap
fixed with isolated RED->GREEN test; final full regression suite green.
Publication-content privacy check:7selected files, PASS. Protected code/policies/
metrics/catalog/submodules unchanged. Earlier checkpoints remain historical.
Qualified replay/calibrated plant and non-actuating device shadow remain
BLOCKED/NOT_RUN, not provided here.

| Variant | Completed synthetic cases/delays | Startup blocked | Invalid input rejected | Candidate verdict |
| --- | ---: | ---: | ---: | --- |
| disabled | 26 | 0 | 3 | baseline control |
| identity | 26 | 0 | 3 | exact baseline parity |
| factor | 3 | 23 | 3 | REJECTED |
| friction | 3 | 23 | 3 | REJECTED |
| combined | 3 | 23 | 3 | REJECTED |

The three executable candidate conditions are low-speed alley, speed sweep and
saturation. No skipped/blocking scenario is counted as a pass. Most catalog
cases start at18m/s; the existing nonidentity schedules exceed their first-frame
change bounds. No warm-up, ramp or initial-parameter replacement was added.

Speed-sweep example (synthetic, not a vehicle target):

| Variant | Center RMS m | Minimum edge margin m | Steering jerk RMS deg/s^3 |
| --- | ---: | ---: | ---: |
| baseline/identity | 0.705249180 | -0.898614445 | 98883.594450 |
| factor | 0.709169811 | -0.909632082 | 98688.773939 |
| friction | 0.701488269 | -0.888521781 | 98919.364888 |
| combined | 0.705382359 | -0.899461241 | 98724.876155 |

Crossing-pair frequency is0.166944908Hz and saturation ratio0 for each arm in
this case. This is not a spectral oscillation measurement. Friction slightly
reduces center error but increases jerk; factor/combined worsen center error.
None achieves the required1% primary improvement without ranked regression.
All have negative lane margin here, including baseline. Saturation scenario
also has negative margin. No arm is a safe/qualified candidate. The large generic
jerk values are produced by the unchanged full-rate metric with supplied input
transients; they must not be interpreted as measured real EPS behavior.

## Handoff

Candidate improvement rejected. REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED,
NOT_READY. Startup admission and coverage limitations must be retained even if
some admitted synthetic cases improve. No vehicle application authorized.

## Fixed offline invocation

In the prepared Linux environment, use the existing bounded process helper, not
an onroad/control thread. No CLI arguments or stdin inputs are supported:

```python
from pathlib import Path
import sys
from openpilot.tools.cyber_autotune import a1_closed_loop
from openpilot.tools.cyber_autotune.native_runner import _run_process

worker = Path(a1_closed_loop.__file__).with_name('a1_closed_loop_worker.py')
outcome = _run_process([sys.executable, '-I', str(worker)], b'', 60.)
assert outcome.status == 'EXITED' and outcome.returncode == 0
```

The aggregate is archival synthetic evidence, not a trusted external admission
or runtime profile API. Require two byte-identical successful executions with
unchanged sources for repeatability. A single report explicitly says repeats
were not checked. Worker uses fresh source-only import cache, existing CPU60s /
address-space2GiB limits and output bound4MiB; parent owns wall timeout/group
cleanup. Input/argument rejection is sanitized. It does not load logs, Params,
recorded source, private simulator or devices. Source hashes are not signatures.

## Final evidence and limitations

Two post-review fresh-process report SHA256:
`721c54b06bff9aa46be425d5e82194e4946132759fcaa8fd2b73d1aec57cd7c4`.
Full-suite receipt SHA256:
`2f68e10e1a55496c9533259d63daaa16ce1c8a4aed2a5726e23b90e299d58b76`.
Reports bind precommit source HEAD plus working-source/binary dependency hashes;
documentation-only closeout does not alter tested executable bytes.

Review fix: policy JSON is outside code directory hash scope, so the worker now
revalidates frozen_policy at both boundaries, not just the catalog/constant.
The isolated regression mutates a temporary copy after actual matrix execution:
before fix worker returned0, after fix sanitized rejection/return1. Frozen files
were never edited. An initial in-process test rejected the test namespace before
reaching the intended assertion and was replaced, not claimed as a reproduction.
Other initial test errors were repeated Cap'n Proto serialization (fixed with
documented write-flag reset for exact byte check) and a diagnostic use of the
nonexistent supervisor stderr field (corrected to its stdout field). No production
controller or metric was altered to make a test pass. Failure records retained.

This increment is ENGINEERING_COMPLETE_OFFLINE_ONLY. The original full driving
objectives remain incomplete; REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
There is no vehicle-ready candidate and no device installation/deployment.
