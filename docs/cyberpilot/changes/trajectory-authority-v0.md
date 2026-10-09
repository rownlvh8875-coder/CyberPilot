# Standalone trajectory authority V0

## Identity and purpose
Cyber AutoTune / Validation. TA-only offline prototype; development screen complete; local regression/build/review PASS.
Baseline feature/cyber-autotune c2d3923d9a13e3e9942352d8a8114cd3203188e2.
The user's new authorization permits family selection, one canonical standalone implementation,
architecture probes and development screening. It excludes search, frozen evaluation, SG,
composition, acceptance, production integration and vehicle deployment.

The family/config/scenario/metric policy was committed at 2bec29c54 BEFORE algorithm implementation.
No historical70 case/index data, private images/annotations, detector output or candidate results
were used for family selection, configuration or synthetic scenario construction.

## Original references
Source: [CyberPilot baseline](https://github.com/rownlvh8875-coder/CyberPilot/tree/c2d3923d9a13e3e9942352d8a8114cd3203188e2),
MIT licenses and comma.ai copyright/attribution retained. opendbc source commit
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. Source SHA bindings are in
trajectory-family-selection-policy-v1.json and supplementary execution binding.
No new dependencies or adapted external algorithms. The source HYUNDAI_SANTA_FE_2022 CarParams profile is an offline fixture, not validated actual-vehicle geometry.

Traced source:
- openpilot/selfdrive/controls/lib/latcontrol_torque.py: delayed acceleration error,
  current feedforward, desired-only jerk/friction, native limits and negative torque return.
- openpilot/common/pid.py: D defaults zero; current native call has no error_rate;
  native antiwindup sees p+i+d+f before clipping.
- opendbc_repo/opendbc/car/interfaces.py: source linear acceleration/torque conversion.
- openpilot/tools/cyber_autotune/curvature_yaw_plant.py: unchanged descriptive plant,
  sole physical actuator queue.

## Changes and expected effect
Selected TA-B: **one-step clipped-error innovation**. TA-A presently duplicates existing
FF/reference alignment/desired jerk. TA-C needs an unsupported extra speed blend while native P
is already speed scheduled. Selection is source/design based; no empirical winner was selected.

For native delayed acceleration error e[k], inherited PID bounds L,U:
~~~text
q[k] = clip(e[k], L, U)
c[k] = 0 on fresh/reset sample
c[k] = clip(q[k] - q[k-1], L, U) otherwise
native PID feedforward argument = original native ff + c[k]
~~~
This is the minimal one-step discrete predictor contribution dt * backward_difference.
Horizon=one sample, dt=0.01s; neither .02s plant delay nor .15s reference alignment derives its gain.
The one-step design is not an identified optimum. Native P/I, desired buffer, jerk, friction,
conversion and total output limits remain unchanged. The correction enters BEFORE native
antiwindup and clipping. No postlimit torque addition, scale, bias or waveform exists.

The stored clipped error and correction inherit acceleration output authority as a containment
design. These are **not physical tracking-error bounds**. Innovation may amplify measurement
noise, partly overlap desired jerk, alter saturation and worsen smoothness/tracking.

New modules:
trajectory_v0_policy/freeze: pre-algorithm source/config/metric/scenario/matrix pins.
trajectory_authority_core: exact authoritative input/output schemas and instance-local PID extension.
trajectory_v0_metrics: separate descriptive trajectory/smoothness metrics and support.
trajectory_v0_screen: fixed three-arm development execution, exact repeats, immutable receipts.

State: one previous clipped acceleration error, TA-owned, alongside unchanged native state.
EXPERIMENT_START/INACTIVE/STEERING_PRESSED/RELEASE/REENGAGEMENT/SCENARIO_BOUNDARY reset fresh native
and innovation state. CONFIG_CHANGE requires a new instance/experiment. Pressed samples disable
innovation; native pressed torque is not forced zero. Inactive output is zero. Plant physical
state/queue persists across intervention transitions.

Observability: explicit native p/i/d/f and prelimit operands, correction, clip status, requested
torque, state and resets. Friction and pure FF decomposition remain null; combined native FF
including friction is separately labeled. Historical hidden prelimit signals are not reconstructed.
Command path is exact SG-disabled passthrough; physical delay belongs only to PLANT.

## Regression risk and acceptance
Potential regressions: noise amplification, clipping, low-speed high P, changing speed/error
projection, reset transients, phase changes and smoothness degradation. There is no new numerical
performance threshold: THRESHOLD_UNJUSTIFIED. Structural gates cannot be compensated by improvement.

Canonical V0 and disabled exact baseline are the only performance arms. TEST_ONLY controls are
separate. Eleven new frozen synthetic 8s/100Hz scenarios include left/right, speed, entry/apex/exit,
S reversal, driver events and limiting flags. Each arm is repeated twice. CURRENT aliases BASELINE
with identical outputs and identity. No parameter mutation, optimization or result-driven changes.
Rollback: remove these additive modules/receipts; production and historical evidence are untouched.
Independent reviewer: source/design and implementation review required; no promotion authority.

## Validation method and actual results
| Stage | Method | Identity | Result/limits |
| --- | --- | --- | --- |
| Focused | unittest new policy/core/screen tests | frozen policy + source hashes | 107 new focused/publication PASS; existing architecture81 PASS |
| Unit/regression/build | full AutoTune/controls, replay, Ruff/syntax, SCons | branch source | AutoTune2148 + controls142 =2290 PASS in888.72s; Ruff/syntax/SCons/publication/privacy PASS |
| Replay | existing two Cyber lateral unittest modules | unchanged production | lateral replay16 PASS |
| Simulation/closed loop | fixed three-arm descriptive plant, two repeats | execution binding + per-trace SHA | 66 runs, EXACT repeatability PASS; structural PASS, tradeoff-only |
| Shadow | no candidate command authority | no runtime integration | NOT RUN, not authorized |
| Browser | no UI added | command-line prototype only | NOT APPLICABLE |

Event reporting preserves the frozen derivative mask: active/nonpressed adjacent samples within
a contiguous reset segment. Event peaks use all finite window rows, separately disclosed.
Pressed-window derivative support can be zero. The first boundary jump is outside that derivative
estimator; before/at-event commands are disclosed as observations. These metrics do not claim to
fully quantify intervention comfort. Saturation tracking metrics separate observed unsaturated
conditioning from missing saturation observations.

5–30m distance queries use observed pose_x and interpolation only. Full observed distance is
secondary descriptive context. No meter-envelope acceptance comparison or extrapolation.

## Handoff
Official execution at 3ab2ab102 completed 11 scenarios × 3 arms × 2 repeats = 66 executions.
Every full state/prelimit/command/plant trace and metric receipt repeated EXACTLY. Baseline/current
outputs, state and identity are exact aliases. Straight is exact zero; the other10 scenarios have
requested/applied/curvature/heading/pose differences. No settings or policies changed after results.

Structural status: TA_STANDALONE_STRUCTURAL_PASS.
Standalone interpretation: TA_STANDALONE_TRADEOFF_ONLY. No acceptance/winner or tracking-improvement
claim. Medium/high-speed synthetic responses oscillate and saturate substantially in BOTH arms.
Numerically lower tracking p95 does not establish stable control. Saturation occupancy worsens:
gentle/medium .49625→.635, sharp .4975→.635, high .70125→.8325. High-speed requested derivative
p95 increases176.350233→200 normalized/s; sharp117.573102→121.290819. A requested delta of2 is the
difference between two individually bounded ±1 commands, not permitted authority expansion.

The high-speed full-run peak same-time pose difference is22.587686m in this descriptive plant.
It is not a real-vehicle displacement or lane-centering gain, and is not compared with any meter
diagnostic envelope. Low-speed peak pose difference is0.000003286m. These disparate effects and
the strong cancellation ratios prohibit a single generalized performance conclusion.

| Scenario | Tracking p95 baseline / TA (1/m) | Requested derivative p95 baseline / TA (normalized/s) | Saturation occupancy baseline / TA |
| --- | --- | --- | --- |

| straight | 0 / 0 | 0 / 0 | 0 / 0 |
| gentle_left | 0.014042884 / 0.011976181 | 117.20076 / 116.15777 | 0.49625 / 0.635 |
| gentle_right | 0.014042884 / 0.011976181 | 117.20076 / 116.15777 | 0.49625 / 0.635 |
| sharp_left | 0.014078378 / 0.01201802 | 117.5731 / 121.29082 | 0.4975 / 0.635 |
| sharp_right | 0.014078378 / 0.01201802 | 117.5731 / 121.29082 | 0.4975 / 0.635 |
| low_speed | 0.0001559933 / 0.00015579631 | 0.033235306 / 0.032811282 | 0 / 0 |
| medium_speed | 0.014042884 / 0.011976181 | 117.20076 / 116.15777 | 0.49625 / 0.635 |
| high_speed | 0.022329503 / 0.021234167 | 176.35023 / 200 | 0.70125 / 0.8325 |
| s_reversal | 0.01403 / 0.012090589 | 117.16902 / 114.95405 | 0.49375 / 0.635 |
| driver_events | 0.014002343 / 0.011973465 | 116.68685 / 116.14216 | 0.43667 / 0.56 |
| limit_flags | 0.01404083 / 0.011974809 | 117.19487 / 116.17116 | 0.49625 / 0.635 |

No UI, device, CAN, Params mutation, CarController, planner/model input or deployment path added.
Source interface imports construct a source-only synthetic CarParams profile; no live profile activation.

Historical states remain CURRENT=BASELINE_EXACT, V1=TRADEOFF_ONLY, V2=REJECTED (37 violations);
V1/V2 remain MIXED_HISTORICAL. SG implementation pending; composition/search/frozen evaluation
not authorized. The reference/calibration track remains separate and unchanged:
CALIBRATION_UNCERTAINTY_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE,
INDEPENDENT_REFERENCE_UNAVAILABLE. Sealed reference NOT_GENERATED; vehicle NOT_READY,
REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.

Independent source/design, preflight and final aggregate review completed. Review repairs added
regressions for runtime timestep/filter/model drift, metric time gaps, saturation conditioning,
event support and support-file binding. Original policies and canonical parameters did not change.

Local checks: AutoTune2148 (previous2041; +107), controls142, existing architecture81,
new focused/publication107, lateral replay16, privacy/publication tests28, Ruff, syntax,
publication_check863files/0findings, git diff check and SCons PASS.
No browser UI was added, so browser validation is not applicable.
Future native PID/interface changes require a new version and source binding; no silent adaptation.

Public evidence is aggregate NEW synthetic output. Per-sample synthetic traces remain in the
local execution folder; no private holdout images/coordinates/logs were accessed or published.
A repeat of the immutable published run uses the exact execution commit/source/environment;
a changed commit/binding must create a new experiment version, never overwrite receipts.
