# Comfort candidate history coverage

## Identity and purpose

Approved bounded validation-only continuation from feature/cyber-autotune
4655adc724090d80fa02920c1e0fc810f78e9f31. The previous fixed cap95 candidate is
REJECTED and stays rejected. This closes missing intervention-history coverage;
it does not propose a new tune or authorize runtime promotion.

## Original references and changes

Reuse this repository's comfort_cap.OfflineComfortPlanner, native planner/MPC/
LongControl, synthetic FixtureSubMaster/car_params and planner_feedback_metrics.
Root MIT license applies; no Carrot code or constants copied. Native dependencies
and submodule gitlinks are unchanged from the base. The existing cap experiment,
its inputs, report, comparison function and frozen policies remain unchanged.

New files: tests/comfort_history_fixture.py runs the test-only native loop;
tests/test_comfort_history.py checks intervention, protected arbitration,
stop/restart, disabled parity and repeatability. No production module imports
the fixture. Results have no vehicle transport, Params or device consumer.

## Predeclared scenarios and measurements

Fixed before execution: 24s at 100Hz control/plant, 20Hz native planner, initial
speed2m/s; event begins3s, demand releases18s. Baseline/default-disabled/cap95
use fresh state, the unchanged synthetic Ki0.1/stopAccel-0.5 CP, generic200ms
response and separate plant-owned delays30/150/300ms. CP planner compensation
is not a second physical queue. These numbers are fixtures, not vehicle bounds.

Three cases:

- lead_stop_restart: a stationary lead at fixed world position18m becomes visible
  at3s, then moves at4m/s from18s. Its world trajectory is identical across arms,
  not positioned relative to each arm's different ego position. Supplied lead
  appearance is not perception/cut-in detection. Stopping behind it is a declared
  scenario demand, not a claim that stock shouldStop is asserted immediately.
- model_stop_restart: experimental model acceleration2m/s2 permits earlier cap;
  at3s the supplied model acceleration is-2m/s2 with shouldStop=true until18s.
  Stock LongControl stopping behavior still uses its original stopAccel/ramp.
- force_stop_restart: unchanged forceDecel true from3s to18s; stock cruise target
  and low-speed shouldStop drive braking/stopping, then normal cruise resumes.

All cruise settings are20m/s; initial position/acceleration/plant response zero.
No driver brake force is invented. Sensor/model messages are synthetic; actual
model/radar/vehicle processes and real log qualification are outside this scope.

Count cap frames before the event and during demand. For candidate cycles whose
current stock context requests negative acceleration, any stop bit or forceDecel,
check actual final native arbitration against those same-state stock candidates:
min/clip and stop OR, with no cap. Do not compare different closed-loop states as
if their braking commands must be identical. Record mismatch counts and first
negative request/applied latency, stop latency/position, gap/TTC and the unchanged
interval metrics/restart measurements. Stop position is descriptive, not error
without a desired stopping-location truth. Missing events remain null/unresolved.
Every candidate planner update is accounted for:480updates,479fresh observations,
one explicit initial OFF-state reset. Missing/faulted/stale observations after
initial reset abort coverage rather than silently dropping a protected cycle.

## Regression risk and acceptance

Test-harness acceptance requires actual cap intervention before all three events,
protected-arbitration identity, default-disabled/native identity and exact reruns.
The model-stop case must reach standstill before release and later resume motion;
other unresolved stops, collisions or adverse metrics remain visible, never
dropped or converted into zeros. Source bindings include new helper/test contents.
Two fresh-process aggregate reports are required. All nine case/delay results
are retained, including regressions. Existing comfort comparison is descriptive
supplemental output only here; no new candidate acceptance or threshold changes.
It is nested explicitly as relative_comparison. A nonpositive signed gap in
either arm is separately labeled absolute_gap_check=FAIL, even if relative
metrics improve. Request/applied/stop latency regressions are separately listed
using the existing1e-9 numeric allowance; stop position is not ranked as error.

Required verification: RED/GREEN, AutoTune+controls, default runner, Ruff/SCons,
privacy and independent review. Rollback is to stop invoking this test-only helper.
No production/active profile change exists to roll back. New tests catch loss of
prehistory, held caps over braking, disconnected state feedback, and false launch
coverage. No holdout, private driving log or additional driving-data request.

## Validation and handoff

Implementation, six focused tests and final broad software gates pass below.
Qualified recorded replay, vehicle-calibrated simulation and on-device shadow
are NOT_RUN for this extension. REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED / NOT_READY remain unchanged.

## Executed synthetic result (not candidate acceptance)

**Absolute lead-gap check: FAIL.** Baseline and candidate cross the supplied lead
position at all three delays. Candidate minimum signed gaps are approximately
-0.119/-0.484/-1.033m at30/150/300ms; baseline gaps are
-0.406/-0.763/-1.323m. There is no collision-contact physics, so these are generic
plant overlap/collision indicators, not a reconstructed crash or a road prediction.
Candidate stopping latency is0.01s worse in each lead case. Two scoped relative
comparisons improve enough to say SYNTHETIC_ONLY_PASS, but the separate absolute
gap check stays FAIL. These are not two safe or promotable scenarios.

All nine case/delay combinations now have42cap frames before the event and zero
cap frames during demand. Each candidate run accounts for480planner frames,
479fresh observations and one initial reset; no protected arbitration mismatches.
All three arms reach standstill before release and restart in these new fixtures.
This establishes intervention-history coverage, not adequate gap or control
performance. Stopping behind the suddenly revealed lead is still a failed safety
outcome. Seven of nine unchanged relative comparisons reject; the other two do
not supersede the original candidate rejection.

Two complete fresh-process reports,54native runs each, are byte-identical:
`758f0659f6ebd63f0ed2c3651e095ea5d2e3238e4a6828f8be96da351e295ae3`.
The earlier reports before adding explicit absolute-gap labels are preserved,
not reused as final-source evidence. All27native arm results remain exactly
equal across that reporting-only change: no trajectory, scenario or metric was
retuned. Both original cap95 matrix and candidate implementation remain unchanged.

TDD: four missing-fixture assertions failed, then passed; missing bound matrix
failed, then five tests passed. Independent review reproduced a missing-observer
blind spot. Actual SubMaster invalidation failed the new negative test before
the guard and passed after it; the reviewer's single-cycle lost-observation plus
wrong-target mutation is now rejected. A missing absolute-gap label also failed
before adding the separate report check. Final focused six tests pass in26.277s.
No remaining Critical/Important review findings. Broad regression/build evidence
before the final report-only change is historical, not final verification.

## Final software verification

Ubuntu24.04/WSL, Python3.12.13; native code, assets and pinned submodules unchanged.

| Check | Final result |
| --- | --- |
| AutoTune + controls supported runner, `-j 1` | PASS:641passed,177.35s,exit0 |
| Default supported runner, `-j 2 -v` | PASS:1,548passed,42skipped,1xfailed,312.86s,exit0 |
| `scons -u -j2` | PASS:100%,exit0 |
| Ruff on both new Python files / whitespace / publication audit | PASS,zero findings |
| Two separate-process matrices | PASS for repeatability and coverage only; absolute gap FAIL |
| Independent code and evidence review | No remaining Critical/Important findings |

The unchanged default runner used the previously verified public upstream fixture
through existing DATA_ENDPOINT, not a private driving log or changed reference.
Supervisor receipt records actual exit0, no timeout, unchanged source and input,
and no verification errors. Its SHA-256 is
`c61f1e58180de9b9e77c6f0e45c2fe09ff57f56a518e0146cc645466b435ffe9`.

Final executable SHA-256:

- comfort_history_fixture.py: `4fb1b5ca3314232f096137e2b37f4a7f8720d61b71524d50f926c62a41b5ea68`
- test_comfort_history.py: `f9de4e41e85d2b667bb4688c1db95670f6da5aaeb9d27bfde41e50fb401af3e9`

This completion section and the remaining-work audit are documentation-only
updates after the full run, separately reviewed; they are not retroactively
bound to the receipt. Executable hashes still match the tested overlay.
Raw reports/runner evidence remain local, outside the publication tree.

Decision: approved coverage extension complete; original cap95 candidate still
REJECTED. The collision/gap and relative regressions prohibit promotion. No
ratio, scenario timing, gap, acceptance criterion or frozen result was changed
to obtain a favorable outcome. Original full vehicle objectives remain partial;
no road-use, active comfort, calibrated-plant or device-shadow claim is made.
