# Standalone trajectory authority V0

## Identity and purpose
Cyber AutoTune / Validation. TA-only offline prototype; development validation pending.
Baseline feature/cyber-autotune c2d3923d9a13e3e9942352d8a8114cd3203188e2.
The user's new authorization permits family selection, one canonical standalone implementation,
architecture probes and development screening. It excludes search, frozen evaluation, SG,
composition, acceptance, production integration and vehicle deployment.

The family/config/scenario/metric policy was committed at 2bec29c54 BEFORE algorithm implementation.
No historical70 case/index data, private images/annotations, detector output or candidate results
were used for family selection, configuration or synthetic scenario construction.

## Original references
Source: [CyberPilot baseline](https://github.com/rownlvh8875-coder/CyberPilot/tree/c2d3923d9a13e3e9942352d8a8114cd3203188e2),
existing repository licenses/attribution retained. opendbc source commit
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. Source SHA bindings are in
trajectory-family-selection-policy-v1.json and supplementary execution binding.
No new dependencies or adapted external algorithms.

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
| Focused | unittest new policy/core/screen tests | frozen policy + source hashes | 91 PASS before official screen; final counts below |
| Unit/regression/build | full AutoTune/controls, replay, Ruff/syntax, SCons | branch source | pending |
| Replay | existing two Cyber lateral unittest modules | unchanged production | pending |
| Simulation/closed loop | fixed three-arm descriptive plant, two repeats | execution binding + per-trace SHA | pending |
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
Effect, repeatability, final test results and limitations will be added after official execution.
No UI, device, CAN, Params mutation, CarController, planner/model input or deployment path added.
Source interface imports construct a source-only synthetic CarParams profile; no live profile activation.

Historical states remain CURRENT=BASELINE_EXACT, V1=TRADEOFF_ONLY, V2=REJECTED (37 violations);
V1/V2 remain MIXED_HISTORICAL. SG implementation pending; composition/search/frozen evaluation
not authorized. The reference/calibration track remains separate and unchanged:
CALIBRATION_UNCERTAINTY_PENDING, INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING, METRIC_CALIBRATION_UNAVAILABLE,
INDEPENDENT_REFERENCE_UNAVAILABLE. Sealed reference NOT_GENERATED; vehicle NOT_READY,
REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.
