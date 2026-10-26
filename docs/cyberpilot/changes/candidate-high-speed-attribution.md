# Candidate v1 high-speed attribution

## Identity and purpose
Cyber Validation / AutoTune. IMPLEMENTED descriptive decomposition at starting
2e999233700426970eb2486a4c71ce985fcb2e23; fetch verified origin equality/clean.
SYNTHETIC SCREENING, not empirical vehicle diagnosis. Actual qualification BLOCKED:
INDEPENDENT_REFERENCE_UNAVAILABLE.
REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

## Original references and exact data flow
CyberPilot MIT existing candidate/worker/protocol/screening at starting HEAD;
native core c8fb906815530460ed156f14e09e1f312bb0f851 unchanged, opendbc
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.
Immutable v1 knots 0/10/20/30: factor 4+[0,1/128,1/64,0],
friction .125+[0,1/2048,1/1024,0]. At 5 m/s: 4.00390625/.125244140625;
at 15: 4.01171875/.125732421875; at 25: 4.0078125/.12548828125.
Whole schedule is interpolated/admitted/float32-quantized before constructing
native controller, then update_torque_parameters/readback before every update.
Config and schedule tuples are immutable; torque params and PID/reference/filter
are native dynamic state. Friction/feedforward, acceleration-to-torque conversion
and acceleration-space limits change. KP/KI, offset, reference history,
lookahead .19 s, jerk filter 1.2 Hz and native requested-command limits do not.
Every fresh worker resets controller/plant. Inactive keeps native history/state
but requested torque is zero; steeringPressed freezes integrator, not active output.
PLANT alone owns two physical command-delay frames. Native one-second desired
accel history (.15 s reference index) is not a physical command FIFO.

Existing thirteen source-bound reports reused, not new candidate results.
Catalog ec7b9557f91fc97fbd5012702d2367d9325310a000baa55884234a2219e5a027.
Attribution module validates receipt/physical replay before reading semantics.
Model-derived desired steering angle uses exact software CP SHA and native VM
negative-curvature convention; it is neither measured angle nor lane truth.

## Implementation and observable results
curvature_yaw_attribution.py and six tests add speed buckets [3,10), [10,20),
[20,27], desired magnitude/sign and original phase cells, requested/applied torque
and derivatives, saturation, zero/reversal rates, post-step tracking residual,
pre-step residual against native delayed acceleration reference, pose excursion,
steering residual, pressed/release and inactive/active flags.
Derivatives/events are computed over full time sequence before grouping, avoiding
false transitions across disconnected bins. Aligned reference is t-15 samples
after native buffer append; varying-speed desired acceleration is normalized by
current speed squared. Pose is diagnostic only, not minimized as a lane score.
Bounded integer lag [-20,20] compares a fixed central window; flat or too-short
signals report insufficient evidence. Lag is never a physical delay fit.

Low constant cases: baseline/v1 lag10, zero crossings1. High gentle/sharp:
both zero crossings79, saturation about .54/.55; correlation lag -14/-3
respectively, which is ambiguous in saturated oscillatory traces.
Reengage-high lag15→16; speed sweep hits +20 boundary. S-high zero crossings79.
All quantities and per-phase/cell splits are retained in
candidate-v1-attribution-results.json (sanitized synthetic summary).

## Cause candidates: evidence, contradiction, confidence, unresolved
| Hypothesis | Supporting evidence | Contradiction / unresolved evidence | Confidence |
| --- | --- | --- | --- |
| A excess gain | high delayed loop oscillates | native KP/KI unchanged; larger factor reduces proportional torque gain, raw PID terms not exported | LOW |
| B insufficient gain | factor at25 rises .1953125%, reducing torque/accel conversion | saturation and alternating torque dominate; no unique small-signal identification | LOW |
| C excess friction | compensation at25 rises .390625%; interacts with error/jerk signs near reversals | both controllers oscillate; factor and friction changed together | PLAUSIBLE / LOW |
| D insufficient friction | saturation/tracking not uniquely explained by compensation | v1 increases friction; no measured steering friction truth | LOW |
| E excessive history/lookahead | input/history alignment creates nonzero phase residual | buffer/filter/lookahead identical across arms; history cannot explain config difference alone | LOW |
| F insufficient history/lookahead | reengagement lag shift | same fixed history, nonlinear clipped outputs; no planner future-path timing truth | LOW |
| G transition discontinuity | speed sweep changes schedule/slopes | constant25 cases also regress; interpolation continuous, existing per-frame limits intact | LOW |
| H prediction/physical mismatch | native index16 vs plant delay2; lag diagnostic varies | reference history is predictive alignment, not physical delay; fixture future-target semantics/calibration unverified | PLAUSIBLE / LOW |
| I saturation interaction | high occupancy >.54, low0; v1 sharp-high RMSE/derivative worsen with same occupancy | occupancy alone does not identify factor/friction cause | HIGH descriptive / LOW causal |
| J reversal instability | high79 crossings/4s vs low1; sharp-high command derivative worsens | not independently identified physical steering oscillation | HIGH descriptive |
| K plant artifact | fixed/speed-growing curvature command gain produces acceleration gain scaling with v^2 | no calibrated transfer function or empirical truth | MEDIUM structural, physical conclusion BLOCKED |
| L not identifiable | combined coefficient change, nonlinear saturation, no exported PI/FF decomposition or independent physical truth | bounded ablations/search can isolate software effects only | HIGH |

Simplified local proportional feedback coefficient: KP(v)*v^2*(.004+.0002*v+
.002/v)/4, about .388 at5 and 1.703 at25, versus plant AR .92 and two delayed
steps. This is a diagnostic linearization ignoring friction/integrator/saturation,
not a stability proof or fitted vehicle model. v1 marginally lowers this term.

## Risk, acceptance and rollback
No new controller/plant/metric/comparator policy. Lag optimization cannot identify
real delay; absolute pose magnitude is not a lane error. Current thirteen cases
were already observed: later evaluation-role split is not an untouched holdout.
No foreign code/dependency. Revert standalone attribution/tests/summary to roll
back. Independent reviewer/promotion authority: later read-only review; none for
vehicle activation. New immutable search policy freezes nine factor/friction
high-delta attenuation cells before any new candidate output; not a tuning claim.

## Validation and handoff
TDD RED missing module; GREEN focused27 PASS (six new attribution tests).
An exact floating reference assertion exposed multiply/divide rounding at ~1e-20;
test now checks numerical reference indexing without changing any metric/threshold.
Full AutoTune 907/907 PASS; SCons 100% PASS; Ruff/syntax/diff PASS; publication_check 378 files / 0 findings. Authority grep finds no writer/network call in attribution; synthetic summary only, no raw private data.
Replay: existing public structural reports validated. Synthetic only.
Shadow/device/real performance: NOT_RUN / BLOCKED.
Next: frozen search, separate development/evaluation roles and bounded stress,
then viewer and loopback browser validation. Production/A3/private data unchanged.

Follow-up in candidate-v2-frozen-search.md: SPEC2 aligns speed-sweep delayed target
to native CarState float32 speed. Historical SPEC1 summary remains a bound
historical descriptive receipt, not the revised scoring source. Constant-speed
quantities/cause limits above are unchanged. Revised search results are separate.
