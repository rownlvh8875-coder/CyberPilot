# Separated offline candidate architecture

ARCHITECTURE ONLY — NO V3 IMPLEMENTATION — NO VEHICLE AUTHORITY

## Identity and purpose

Cyber Validation / AutoTune. IMPLEMENTED: typed contracts, source audit, owner/reset validators,
SHA identities, experiment matrix, analytic observer controls and disabled-governor isolation.
PENDING: trajectory algorithm, enabled governor, composition, metric execution definitions and search.
Baseline: feature/cyber-autotune, 6c60eb8ba3382c1600d056e7b213c73517ce0e87.
No vehicle-specific controller behavior is implemented.

The previous authority audit confirmed descriptive plant authority with mixed attribution.
Scenario-dependent requested output, AR attenuation, temporal cancellation, limiting and later
transients coexist. It did not establish a pure trajectory or smoothness role for V1/V2.
CURRENT remains BASELINE_EXACT; V1 TRADEOFF_ONLY; V2 REJECTED with 37 historical violations.
Their original receipts, source, results and verdicts are unchanged. They remain MIXED historical
candidates. No old controller, plant, holdout or meter result was rerun for this increment.

## Original references

Source repository: https://github.com/rownlvh8875-coder/CyberPilot
Verified branch: feature/cyber-autotune. Exact source commit is the baseline above.
Pinned opendbc: 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.
Upstream MIT attribution and repository license remain intact; no upstream code was copied or edited.

The decision JSON records source paths, symbols, per-file SHA256, units, rate and owner for:
desired curvature → VehicleModel reconstruction → measured lateral acceleration → delayed causal
setpoint/PID error → feedforward/roll/friction → torque conversion/limit/saturation → inactive and
driver events → raw Hyundai boundary → descriptive plant input.
The raw Hyundai conversion/driver/rate/fault checks are audited only and are not executed.
The native controller update uses 100 Hz / 0.01 s. Its reference history is controller state;
the descriptive plant remains the sole physical actuator-delay owner.

Read-only references:
- openpilot/selfdrive/controls/lib/latcontrol_torque.py, LatControlTorque.update
- openpilot/common/pid.py, PIDController.update (pre-limit sum is local, historical receipt absent)
- openpilot/selfdrive/controls/lib/latcontrol.py, reset and saturation bookkeeping
- openpilot/selfdrive/controls/controlsd.py, state_control and _update_lateral_control
- openpilot/tools/cyber_autotune/curvature_yaw_native_worker.py, explicit offline feedback reconstruction
- openpilot/tools/cyber_autotune/curvature_yaw_plant.py, observe_curvature_yaw_step
- opendbc_repo/opendbc/car/hyundai/carcontroller.py, raw boundary not an integration target

Only existing public identity metadata is read. No private logs/images/coordinates are accessed.

## Changes and expected effect

Approach comparison:

| Approach | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| A: separate parallel wrappers | clear standalone roles | duplicate native logic; unclear composition | not selected |
| B: core then governor | narrow attributable command boundary; distinct identities | governor phase lag and resets need explicit evaluation | selected |
| C: integrated multi-objective | one implementation | attribution loss and hidden tradeoffs | not selected |

The following diagram specifies future boundaries; it is not executable candidate behavior.

~~~mermaid
flowchart LR
  E[Experiment: causal desired/actual curvature, speed, roll] --> T[Trajectory core: error/history owner]
  T --> O[Observed pre-limit intent and controller-limited torque]
  O --> N[Narrow command: normalized torque and core identities]
  N --> G[Governor: command/reversal/intervention owner]
  D[Experiment: inactive/driver events] --> G
  G --> F[Pre/post governor and final requested torque]
  F --> P[Existing offline adapter / plant: sole physical delay owner]
  P --> A[Applied torque / curvature / yaw / pose]
~~~

Added Python modules:
- candidate_role_contracts.py: frozen exact schemas; direct constructor and parse validation.
- candidate_architecture.py: blocked interfaces, disabled-only passthrough, identities, reset/owner,
  timebase and experiment-matrix validators.
- candidate_architecture_policy.py: separate future metric catalogs, family descriptions and verdicts.
- candidate_architecture_probe.py: analytic geometry and signal-observer fixtures only.
- candidate_architecture_evidence.py: additive receipts, immutable atomic publication and exact validation.
- candidate_architecture_publication.py: exact published receipt allowlist.

Trajectory input whitelist: desired/actual curvature (1/m), speed (m/s), roll (rad), time/dt (s),
active/steeringPressed/safetyLimited/curvatureLimited booleans. Actual feedback is explicit simulated
measurement, not hidden plant state or future truth. The contract does not accept lane location,
modelV2, planner/candidate outputs, or arbitrary scale/bias behavior. It makes no lane-centering claim.

Trajectory output separates controller-limited raw requested normalized torque from optional
pre-limit intent, tracking error, FF, feedback, friction and saturation intent. Optional values are
null with UNAVAILABLE unless explicitly observed in a future offline prototype. Upstream PID
components use acceleration units; any future normalized-equivalent components must record the
conversion. Historical pre-limit intent remains null.

Governor input is deliberately narrower than trajectory output: only normalized command and core
source/config IDs, plus time/dt/active/pressed/release/reengagement. It cannot receive tracking error,
desired curvature, component observations, lane or path. Disabled governor is exact stateless
passthrough, including inactive/pressed inputs; this is a diagnostic isolation control, not a
vehicle-safe controller. Enabled construction raises NOT_AUTHORIZED. TA.update and compose also raise.
No fallback candidate behavior, rate shaping, low-pass filter, search or V3 exists.

Three architecture families are described, with none selected:
TA-A causal delay-aware feedforward; TA-B bounded tracking-error feedback; TA-C speed-conditioned blend.
Mechanism/failure/observability/transfer risks are recorded. Parameter names/count/ranges remain pending.

## State, reset, delay and identity

TA owns error/integrator/causal-demand history. SG owns last command/reversal/intervention state.
Experiment owns inactive/pressed event sources and 100 Hz timing. PLANT alone owns physical delay.
No state or queue is shared. Governor time constant and maximum memory remain null; this blocks
enabled execution. Command shaping is not physical actuator delay.

All listed reset events have an explicit owner/action. TA and SG use fresh instances for standalone
structural tests at experiment start, inactive, pressed, release, reengagement, config change and
scenario boundary. PLANT retains physical dynamics and delay queue across intervention events.
Experiment/scenario start resets plant; config changes require a new experiment, not in-run mutation.
A future state-retention algorithm requires a versioned policy before execution.

Each role has a separate frozen identity with source/config/state/reset/input/output/experiment-policy,
native software, CarParams/profile, plant, environment and timebase SHA fields.
Native software and CarParams/profile are pinned historical first-index baseline REFERENCE context,
not executed by the new probe. Current pure-Python probe environment is separately recorded.
Sources include contracts, metric policy, fixture code and evidence builder. Experiment-policy identity
binds fixtures, metric catalogs, search schemas and matrix. SG output binds the full SG identity.
A different role/config/policy changes identity. No executable candidate identity is claimed.

## Evaluation separation and frozen policy

Separate future experiments: EXPERIMENT_TA, EXPERIMENT_SG; composed experiment not authorized.
Three-arm infrastructure is preserved: baseline / current exact alias / future role-specific candidate.
Only ARCHITECTURE_PROBE is executable now. DEVELOPMENT_SCREEN / FROZEN_EVALUATION /
STRESS_DIAGNOSTIC require future authority and fully declared execution policies.
Historical DEVELOPMENT/EVALUATION/STRESS roles remain unchanged; historical 70 cases are not search inputs.

Metric catalogs freeze name, unit, direction, aggregation intent, mask/availability, phase/coverage
handling and no-worse semantics. Exact spectral bands, lag estimator, event windows, numeric tolerances,
scenario selections and hard thresholds are pending before execution.
THRESHOLD_UNJUSTIFIED means evaluation cannot claim pass/fail. No minimum cm effect or weighted score
is introduced. TA must independently satisfy SG hard constraints; SG must independently satisfy
tracking/pose constraints. Improvement cannot offset the other objective's hard failure.
Error/coverage are separate; missing support is null, never zero-filled.

5–30 m is primary early context. Full observed distance is LONGER_HORIZON_DESCRIPTIVE_CONTEXT;
no extrapolation or extension of the existing meter envelope is authorized.
Structural detectability states describe output/curvature/heading/pose differences, cancellation,
limiting or distance unavailable, without candidate acceptance.

Trajectory and SG search schemas require family, parameter names/units/ranges/discretization,
reset/development/evaluation scenarios, constraints/tie-break/maxcount. Status NOT_FROZEN and
execution_allowed=false; missing values are null.

Composition requires separate structural PASS, repeatability, complete distinct identities,
no shared mutable state/duplicate delay/role violation, and new explicit implementation authorization.
Current composition remains NOT_AUTHORIZED.

## Probe interpretation

The analytic fixture uses signed curvature arcs at fixed 10 m length to test geometry sign/amplitude
observability. The oscillatory normalized command fixture tests derivative/reversal detection.
Constant input, identical reset and disabled passthrough are negative controls.
These do not exercise an enabled TA/SG algorithm, plant gain, production controller or candidate.
Stronger-shaping monotonicity, phase lag and tracking tradeoff remain implementation pending.
Fixtures were fixed before execution and are not a search grid.

## Regression risk and acceptance

Risks: role leakage, ambiguous reset, identity omissions, hidden physical delay, false distinct current
arm, fabricated saturation/pre-limit signals and premature execution. Exact schemas and immutable
receipts fail closed. Independent review added regression coverage for full SG identity, fixture/metric
policy binding and continuous plant retention. No performance/vehicle acceptance threshold exists.
Rollback is additive-file removal; historical configuration remains the last unchanged reference.
Future algorithms/composition/search need separate user authority and review.

## Validation method and actual results

Commands use the prepared Ubuntu 24.04 WSL Python 3.12 environment.

| Check / stage | Method and identity | Actual result and limits |
| --- | --- | --- |
| Unit / regression | unittest new architecture modules; tools/test_runner.py AutoTune + controls | PASS: 2,183/2,183 in 885.67 s (AutoTune 2,041 + controls 142); 81 new focused tests PASS |
| Lint/syntax/publication | Ruff scoped Cyber sources; compileall; check_publication --base origin/main; privacy/authority tests; diff --check | PASS: 842 files / 0 findings; 28 publication tests; offline import authority audit; 216 JSON artifacts parsed |
| Build | PATH=.venv/bin:$PATH; .venv/bin/scons -j2 | PASS, exit 0 |
| Replay | unittest Cyber lateral card/native experiment modules | PASS: 16 tests; isolated regression only, no vehicle authority |
| Simulation / closed loop | synthetic architecture observer fixtures | geometry/sign/amplitude and derivative/reversal controls; no historical plant/candidate rerun |
| Browser | no UI added; local-only architecture diagram is documentation | not applicable |
| Shadow | no runtime integration or live device access | NOT RUN / NOT AUTHORIZED |

Independent review: PASS, no remaining Important/Critical findings. 81 new focused tests PASS.
Controls regression independently PASS: 142 tests. Full AutoTune+controls PASS: 2,183/2,183 in 885.67 s.
AutoTune increased from 1,960 to 2,041; controls remains 142. No tests were skipped or weakened.

## Handoff

ARCHITECTURE_DEFINED, CONTRACTS_FROZEN and EXPERIMENT_MATRIX_FROZEN.
TRAJECTORY_IMPLEMENTATION_PENDING, SMOOTHNESS_IMPLEMENTATION_PENDING,
COMPOSITION_NOT_AUTHORIZED, SEARCH_NOT_AUTHORIZED.
Historical V1/V2 and CURRENT verdicts remain unchanged.

Architecture DAG is separate from reference calibration DAG. The unchanged full blocker graph is
bound from the prior readiness receipt; calibration uncertainty, independent calibration validation,
pixel registration, metric calibration and independent reference remain blocked.
Sealed reference NOT_GENERATED. NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No real-vehicle application is authorized. Next check is a separately scoped causal standalone
algorithm design and fully specified metric execution policy; no algorithm is selected here.
