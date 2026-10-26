# Curvature/yaw parameterized native offline candidate

## Identity and purpose
Cyber Lateral / AutoTune, opt-in worker controller, synthetic software verification.
Start: feature/cyber-autotune at 57489486afd5a5197256570fae1bf12bfcfbb296;
fetch/pull verified HEAD=origin, clean before edits. Target vehicle identity remains
the existing Santa Fe synthetic fixture, not a Hyundai calibration or active tune.

Goal: meaningful native controller behavior difference with identical CP and plant,
not an output scale or bias. Actual performance qualification remains BLOCKED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

## Arm/code audit
UPSTREAM_BASELINE: native LatControlTorque at upstream baseline
c8fb906815530460ed156f14e09e1f312bb0f851; current core content matches SHA-256
9489bfd923246906ef543a1c305bf7a7fe534ee9754c94d8195ae98bb3a1f2cd.
Pinned opendbc in both baseline and execution:
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. Current execution source HEAD and all
selected native files are bound separately; synthetic CP is generated and SHA-bound.
CYBER_CURRENT runtime disabled/observe-only delegates one native update and returns
its exact result. It is a BASELINE alias, not a third unique controller.
CYBER_CANDIDATE: v2 explicit SPEED_SCHEDULE selector in curvature_yaw_native_worker.

native_worker._execute_request and curvature_yaw_native_worker.execute_request
construct fresh CP, LatControlTorque and VehicleModel per run. PID state, native
reference history, jerk filter and saturation timer persist within the sequence.
latAccelFactor/friction affect acceleration-to-torque conversion, feedforward and
PID acceleration-space limits; latAccelOffset, gains, lookahead and limits remain
native. Candidate injection occurs before each native update, with whole schedule
admission before controller construction and exact wire readback afterward.

Existing A1 prepare_schedule and speed_aware_tune are reusable pure validators.
Existing bounded_combined coordinates are retained unchanged as the declared
hypothesis: speeds 0/10/20/30 m/s, factor 4+[0,1/128,1/64,0], friction
.125+[0,1/2048,1/1024,0]. Existing range/transition guards are unchanged.
Historical generic-plant bounded A1 candidates were rejected. This increment
tests that existing hypothesis in another descriptive plant; it neither repairs
those failures nor creates an accepted candidate. No search or best selection.

Synthetic candidate grids are existing offline experiments; none activates a
runtime profile. A3 preprocesses recorded requested/applied commands and cannot
be silently substituted for this feedback-bound candidate. A3 rejection remains.
An identity schedule or zero demand can produce identical output even when named
candidate; later screening explicitly reports observable no-op rather than inventing
a difference.

Sunny jerk-persistence ideas exist as a pure jerk observer; Carrot lane/path
quality ideas exist as model-derived path diagnostics. Step7 Phase A records
Sunny a5f44653d7f43ad57fef2f546f3916ec4cbf3c56 (Custom MIT) and Carrot
c57d0ff11f766b7fd70e9a9eaec1247b623ffbea (license unresolved).
No foreign controller/gain/NNLC/MPC code is copied here.

## Architecture and changes
Chosen C: frozen parameterized offline native controller. A generic output
post-filter would require new anti-windup/transient semantics; a derivative would
duplicate upstream state/control code. Existing whole-schedule admission is the
smallest causal native-core seam and requires no controller fork.

- curvature_yaw_candidate.py validates selector/table and prepares immutable
  float32 factor/offset/friction tuples via existing A1 guards; no I/O or delay queue.
- curvature_yaw_native_protocol.py adds strict opt-in v2 selector plus exact support
  file set. v1 schema and identity formula preserved.
- curvature_yaw_native_worker.py source-verifies selected adapter dependencies,
  precomputes schedule, applies native update_torque_parameters once per frame,
  verifies readback and binds selector/config/effective-row SHA in result.
- curvature_yaw_native_runner.py revalidates all v2 config/readback bindings before
  public transcript replay. Controller identity includes config and adapter source.
- Seven new synthetic tests: strict versioning/config/source drift, v1/native-v2
  exact output/state parity, non-zero difference/repeatability/admission, late
  invalid schedule/source rejection, inactive/pressed and response tampering.

Physical actuator delay remains PLANT only. Native .15 s reference history is
prediction alignment, not a second physical command queue. Frozen config never
mutates; effective speed-conditioned parameters are deterministic derived state.
Fresh workers reset controller/plant; inactive and pressed behavior is inherited
from native update (pressed freezes integrator, does not force zero active torque).
No runtime controller, safety, Params/CAN/device/CarController/network writer,
profile activation, private input or comparator edit.

## Risk, acceptance and rollback
Bounds are existing synthetic A1 coordinates, not real vehicle validity. Schedule
cannot handle every real CP or out-of-domain speed; it must fail closed. Same CP
for all arms is mandatory in the later synthetic contract. No perception reference
is available, so neither lane-center improvement nor lane-less bias repair can be
claimed. No threshold/metric/policy is tuned to candidate results.
Rollback: revert only the opt-in v2 offline seam and its module/tests; v1/live
behavior remains the baseline. Promotion/real vehicle authority: none.
Source: CyberPilot existing MIT implementation at starting HEAD; no new dependency.

## Verification
Ubuntu 24.04 WSL, .venv Python 3.12.13. Test-first RED: 7 missing CANDIDATE_FILES
errors before implementation. Initial GREEN blocked worker on stale SUPPORT_FILES
loop reference; Ruff identified it, then full v1/v2 tests passed after the fix.
Focused 31/31 PASS in 7.10 s; new module 7/7 PASS in 4.225 s.
Full AutoTune stable source run: 880/880 PASS in 226.15 s.
Earlier concurrent run: 879 PASS / 1 FAIL in 225.23 s, existing A1 source-bound
repeat worker generic failure. Isolated reproduction PASS in 17.43 s; stable full
rerun PASS. Source files/build outputs were changed concurrently with the earlier
run, a plausible binding-drift cause; worker error alone does not prove that cause.
No old test, bound, metric or threshold changed to obtain the rerun result.
Ruff, py_compile, authority grep (no writers), git diff --check PASS.
publication_check: 363 changed files / 0 findings.
SCons: 100% PASS with PATH=$PWD/.venv/bin:$PATH and .venv/bin/scons -j2
(existing PWD warning only). Production/runtime/comparator/evidence-audit diff empty.
Actual performance qualification / independent reference / device shadow: BLOCKED / NOT_RUN.
Later separate equivalent-arm experiment will freeze inputs and metrics, without
changing strict three-distinct-arm production comparison or prior audit snapshots.
