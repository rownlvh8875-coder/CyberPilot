# Native longitudinal feedback-loop parity

## Identity and purpose

Cyber Long / Validation, test-only continuation from
`cfa169896ad2efd913ec2f99e968ece1fed8c475`, `feature/cyber-autotune`.
Add actual planner-to-controller-to-generic-plant feedback to existing native
parity coverage. This reduces a software test gap; it is not full coupled-process
replay, vehicle-calibrated closed loop, Phase B implementation or qualification.

## Original references

Reuse `test_cyber_long_integration.py` fixture and Git-object baseline loader.
The reference planner and LongControl execute source from upstream
`c8fb906815530460ed156f14e09e1f312bb0f851`, root MIT license. The current source
uses the same pinned MPC dependencies and opendbc
`4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`. No external fork logic is copied.
Git-loaded baseline top-level modules import the shared current pinned
dependencies. This is not a separately reconstructed entire upstream stack.

Call path: declared synthetic lead/model-action/driver inputs → native MPC and
LongitudinalPlanner at 20 Hz → LongControl at 100 Hz → generic 1-D response at
100 Hz → next vEgo/aEgo, standstill, relative lead gap and controller-state inputs.
Native upstream, repeat upstream, current disabled and observer arms each have
fresh independent planner/controller/plant state. The existing helper constructs
in-memory cereal messages, not a SubMaster socket or daemon.

## Changes and expected effect

Only `openpilot/selfdrive/controls/tests/test_cyber_long_feedback.py` is added.
No product/controller/plant framework, safety, Params or schema code changes.
Three six-second fixtures cover lead following with a declared cut-in and loss,
supplied model stop/restart with a moving lead, and driver cancellation/reengagement.
The stop fixture starts at 0.5 m/s, asserts actual zero speed before the restart
boundary, and asserts resumed motion above 0.1 m/s by its end.

The existing `SYNTHETIC_PARITY_ONLY` CP has Ki=0.1. It is deliberately not the
Santa Fe vehicle tune, whose zero Ki makes the separate v2 scaling grid ineffective.
No new gain candidate is tested here. Existing fixture bounds remain native
ACCEL_MIN/ACCEL_MAX. Generic plant delay is 30 ms (three control ticks) and its
first-order response time is 200 ms. Existing CP planner compensation is 200 ms;
it does not enqueue actuator commands or add another physical delay. These are
test fixtures, not matched/calibrated vehicle dynamics.

Outputs at each interval include planner target/stop/source/acceleration arrays,
MPC acceleration solution, requested controller acceleration, controller state
and integrator, and interval-end plant speed/acceleration/position. They must be
exactly equal across all four independent arms; no tolerance expansion. Solver
wall-clock time is not a control value and is not asserted, as in the pre-existing
parity test. No upstream replay ignore list is changed.

## Regression risk and acceptance

- Closed-loop parity must not accidentally share candidate and reference states.
- A disconnected speed/acceleration-feedback negative control must change actual
  planner targets, not merely recorded plant output.
- Inactive controller requested acceleration must equal zero over all 100 cancel
  ticks. This does not claim zero physical acceleration while plant lag decays.
  Cancellation is a supplied active/brake fixture, not an executed selfdrived
  engagement/driver-monitoring decision or a vehicle brake event.
- Startup reads previous LongControl OFF state and resets the first planner
  cycle. Reengagement likewise reads OFF for one cycle. Expected valid observer
  counts are 119/120 normally and 98/120 with twenty cancelled planner cycles
  plus startup and reengagement resets. Disabled observes none.
- This is not a collision, stopping-distance, comfort or performance acceptance
  gate. Scenario success means software parity/feedback, not safe driving.

Alternative considered: reuse upstream maneuver Plant directly. That fixture
opens messaging sockets and feeds planner acceleration directly to the plant,
omitting LongControl; it does not exercise the intended isolated full feedback
boundary. Its code and existing acceptance remain untouched.

## Validation method and actual results

Test-first: two missing-helper errors before implementation, exit 1. First native
execution passed the feedback/cancel test and failed overly broad expected
observation counts. Tracing native `long_control_off` reset behavior explained
the startup/reengagement cycles; explicit expected counts were corrected without
changing production behavior or established acceptance. A review then caught that
the initial 2 m/s fixture never reached standstill. An explicit stopping assertion
failed (minimum speed before restart 0.732500 m/s); lowering only the new fixture's
initial speed to 0.5 m/s made it exercise actual stopping. Observation collection
now reads policy state in every mode, avoiding a tautological disabled counter.
Final targeted rerun: three tests passed, exit 0, 1.19 s. Independent review found
no remaining actionable findings after these corrections. This is source review,
not a separate physical qualification or independent test-lab result.

## Handoff

No new log data, holdout, private simulator, sockets, device communication, CAN,
vehicle-controller apply, profile update or deployment. Native MPC executes, but
modeld/radard inference, planner publication/socket scheduling and actual vehicle
response do not. Do not promote this in-process software test to qualified replay
or calibrated closed loop. Rollback is omission of the test. Next work remains
an independently designed bounded planner-coupled evaluation with explicit
performance metrics and input identity; not enabling active comfort/cut-in.
