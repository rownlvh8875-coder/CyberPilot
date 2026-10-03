# Offline positive-acceleration cap experiment

## Identity, scope and references

Approved single hypothesis, based on feature/cyber-autotune at
bf36c1ff819219e62b94be8dc0aba934ad40cbd5. Offline implementation verified;
the fixed candidate is REJECTED, not eligible for runtime promotion.
This is NOT production Phase B activation or a vehicle tune. Follow the approved
CYBER_LONG_DESIGN.md sections5–7: a planner candidate before min/stop OR/clip and
state feedback, never an actuator post-filter. No Carrot source/constants copied;
independent research implementation under repository license. Upstream native
planner, LongControl, MPC, cereal, opendbc and panda remain unchanged.

The stock get_max_accel speed table is from the pinned upstream-derived planner.
The single cap fraction0.95 (dimensionless) is an explicitly approved synthetic
hypothesis, not an empirical HKG bound or driver setting. Existing synthetic CP
has fingerprint SYNTHETIC_PARITY_ONLY and Ki0.1; this is NOT the vehicle's zero Ki.
Do not infer effective vehicle tuning from this synthetic controller fixture.

## Implementation boundary and failure behavior

comfort_cap.py: stateless positive proposal plus synthetic-only subclass of the
pinned native planner. Reuse its existing pre-arbitration observation hook only
in the offline subclass. Production CyberLongMode remains disabled/observe-only.
Default experiment disabled. No real CP, IO, Params, socket, device or CAN sink.
The pinned planner SHA rejects an unreviewed seam. Fingerprint is a misuse guard,
not authenticated vehicle provenance or a hostile-code sandbox.

Invalid/reset/override/force-decel/stop/near-standstill data returns no candidate.
Observer temporal watermarks reject repeated/reversed timestamps. No candidate
state is retained across rejection. A smaller positive cap is appended with stock
cruise source semantics; original stop bits and clip/feedback are consumed by the
native update. No physical delay is added to the controller. The generic plant
owns its only delay queue. Less acceleration is not a safety proof.

comfort_experiment.py: fixed synthetic12second scenarios, planner20Hz and
control/plant100Hz; generic response time0.2s and delays0.03/0.15/0.30s. These are
declared stress inputs, not measured vehicle calibration. Three fresh arms:
current stock baseline, default-disabled subclass, cap95. Existing native fixture
CP/SubMaster and interval-aligned metric reader reused; old fixtures unchanged.

## Predeclared evaluation (before candidate performance execution)

Cases: open_road, lead_brake, cut_in_loss, stop_start, driver_cancel, force_decel,
coast, curve_left, curve_right, model_stop. All cases and all3delays required.
Two repetitions per arm and two complete fresh-process reports must agree.
Baseline and disabled must agree exactly, including trace and MPC feedback.
No route, holdout, camera or personal log is used.

Compare existing planner_feedback_metrics without changing their definitions:
planner tracking, requested/applied error, command/actual jerk, minimum gap/TTC,
nonpositive gaps, unresolved stop/restart/cut-in, restart/cut-in delay and inactive
request. Additionally measure speed-target RMS against the scenario's exogenous
cruise/stop target, never a candidate-generated reference. Missing values stay
null. The stop-position/follow-error metrics remain unavailable.

Preserve old v1/v2 policies. This separately identified experiment borrows their
numeric allowance1e-9, zero relative regression allowance, and minimum1% primary
improvement. Any worsening of any compared metric or changed metric availability
rejects the case. At least one command/actual jerk RMS must improve by1% on an
effectful case. No-effect cases are labeled NO_EFFECT, not improvement. Any case
regression blocks overall acceptance; an all-no-effect matrix cannot pass.
No gain search, dropped failing case, modified reference or post-result threshold
adjustment. These gates are deliberately strict research gates, not qualification.

## Risks and verification

Expected trade-off: reducing positive acceleration may lower jerk while worsening
speed response. Short windows, generic plant and synthetic sensor/model inputs
cannot certify stopping, gap, cut-in or vehicle safety. MPC next-tick coupling is
exercised; instantaneous braking arbitration preservation alone is insufficient.
Driver cancel/reengage inputs are supplied, not inferred human intervention.

Required: RED/GREEN unit/native tests, default-disabled exact parity, malformed
input/repeated timestamp/stop OR checks, declared full matrix repeatability,
affected and default suites, Ruff/SCons, privacy and independent review.
The following sections record execution of these checks. Old1533/626passes
remain historical and do not verify these new files.
Rollback: stop using offline module; no runtime profile changes to reverse.
All vehicle authority remainsfalse; REAL_VEHICLE_UNVERIFIED / NOT_READY.

## Executed candidate comparison

Implementation is present in the three new offline source/test files; production
control files and frozen policies are unchanged. TDD: five missing-cap failures,
then five passes; two missing-experiment failures, then seven passes; missing
full-matrix failure, then eight passes. The first RED log's outer shell returned0
despite the recorded five assertion failures; that shell status is not a test PASS.
Subsequent RED runs returned1 and GREEN runs returned0. A capnp serialization
warning in the first GREEN test was removed using its supported write-flag reset,
not by suppressing warnings or altering product behavior.

Independent review found one Important provenance gap: the shared binding omitted
the planner's cruise.py dependency. An actual boundary byte-read mutation test
failed before adding its explicit hash and passed afterwards. No checkout file
was mutated by that test. The reviewer verified the fix independently.

Final-source two fresh-process reports are byte-identical, SHA-256
`e1e7e053627b0861f8141218418d7481086b2aa97aa32de4dcefdf3a498787b6`.
Each executed180native runs:10cases x3delays x3arms x2repetitions. Baseline/default
disabled match exactly; repeatability and before/after source bindings passed.
Pre-fix reports remain preserved locally, not relabeled as final-source evidence.

Candidate outcome: **REJECTED**. Of30case/delay comparisons,15rejected,
12had NO_EFFECT and3passed the scoped synthetic criteria. The three passing
comparisons are force-deceleration scenarios after earlier capped acceleration;
they do not establish an overall improvement. Open-road/cut-in/cancel/curve cases
show speed-response regressions despite some jerk reduction. No ratio was retuned.

Important coverage limits: lead_brake, stop_start, coast and model_stop never
activate the cap at any declared delay. Their identity cannot demonstrate stopping
or restart behavior after a cap intervention. model_stop also leaves one unresolved
stop at every delay for baseline and candidate; this is not a successful stop test.
Future experiments need separately declared cap-history-to-braking/stop scenarios
before a positive improvement claim. Existing rejected results stay frozen.

The first combined AutoTune/controls run passed634tests in151.89s before the
provenance-only fix; do not reuse that count as final-source verification.
No private data used.

## Final-source software verification

Ubuntu24.04/WSL, Python3.12.13, unchanged pinned submodules and native assets:

| Check | Result |
| --- | --- |
| Supported runner, AutoTune + controls, `-j 1` | PASS:635passed,150.99s,exit0 |
| Supported default runner, `-j 2 -v` | PASS:1,542passed,42skipped,1xfailed,288.13s,exit0 |
| `scons -u -j2` | PASS:100%,exit0 |
| Ruff on all three new Python files | PASS |
| Publication scanner and whitespace | PASS:zero findings/errors |
| Two fresh-process fixed synthetic matrices | PASS:byte-identical; candidate REJECTED |
| Independent code/evidence review | No remaining Critical/Important findings |
| Qualified recorded replay / vehicle-calibrated closed loop / live shadow | NOT_RUN for this candidate; promotion BLOCKED |

The default suite uses the already verified public upstream fixture via the
existing DATA_ENDPOINT option, not a replaced test or private driving log.
The external supervisor records actual exit0, no timeout, unchanged source and
fixture and no verification errors. Receipt SHA-256:
`9caf5ea43af825d6e746df5006b6caeceb2ebef64dc814a6bfe475e26ce24ee5`.
Existing42skips and1expected failure are retained, not new exclusions.

Tested executable content SHA-256:

- comfort_cap.py: `6bbc4cf693976f54479cc380a7218db367e12870f1c2954f118e1c72636295e9`
- comfort_experiment.py: `1822814c480ebaf453b4f38ee3e1cf18c7d9843ae39653ef0f64e20e935b26b9`
- test_comfort_cap.py: `6a17ddcf08644f49c6eecb6b6806b01cd178bbb0c4bf1b680379071f252f1b92`

These completion notes and the remaining-work audit are documentation-only
updates after the full run; they are separately reviewed, not retroactively part
of its bound overlay. Executable content remains identical to the receipt.
Raw reports, commands and logs remain local, outside the publication tree.

Decision: retain this disabled-by-default research experiment and its rejection
as reproducible evidence. Do not activate it, retune the ratio after seeing the
results or count it as completed active Cyber Long Phase B. A new behavior
hypothesis needs a separately declared design and coverage plan. All original
vehicle qualification gaps remain; REAL_VEHICLE_UNVERIFIED,
VEHICLE_ACTIVATION_BLOCKED and NOT_READY are unchanged.
