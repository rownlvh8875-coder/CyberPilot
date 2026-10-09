# SG-A standalone closed-loop feedback audit

## Identity and purpose

Cyber Validation / AutoTune; additive offline audit on feature/cyber-autotune.
Starting source: cd5561b6c8ee568917fc6a5d2c53a6396d4544fe.
The previous SG experiment freezes native baseline commands before plant replay.
Its SG plant pre-state is a metric query, **not feedback to a native core**.
This increment alone authorizes unchanged native baseline plus SG-A in an
own-feedback descriptive closed loop. No TA-B, composition, config/radius
change, search, frozen evaluation, candidate acceptance or vehicle authority.

## Original references

- Repository: https://github.com/rownlvh8875-coder/CyberPilot
  branch feature/cyber-autotune, exact starting source above.
- Existing sources retained byte-for-byte:
  trajectory_authority_core.py::NativeBaseline,
  smoothness_governor_v0.py::Governor, smoothness_v0_screen.py::step,
  trajectory_v0_screen.py::PLANT/scenarios, smoothness_v0_metrics.py.
  NativeBaseline invokes unchanged LatControlTorque, native PID and
  opendbc VehicleModel, with the existing source Hyundai descriptive profile.
  The TA Core class is never instantiated.
- Existing SG config, intervention/reset policy, metric policy, scenario
  rows and historical replay receipt are pinned by
  smoothness-closed-loop-policy-v1.json. Source-only freeze precedes runner
  implementation; implementation/environment/submodule/native-support
  identities are in the execution binding.
- Upstream source attribution/licenses and submodule gitlinks are unchanged.
  No adapted external algorithm or new dependency.

## Changes and expected effect

New modules: smoothness_closed_loop_policy.py freezes timing/matrix;
smoothness_closed_loop.py owns isolated runtimes and validates native/SG/plant
trace reproduction; smoothness_feedback_metrics.py adds block containment,
replay interaction and divergence attribution; smoothness_closed_loop_publication.py
binds additive aggregate evidence/readiness. Tests accompany each.

Order at sample k, 100 Hz / 0.01 s:

1. Read only frozen exogenous scenario input k.
2. Read the same arm's plant state k, before update.
3. Reconstruct curvature through unchanged NativeBaseline/VehicleModel and
   update that arm's fresh native controller.
4. Baseline/current use disabled exact passthrough.
5. SG arm uses unchanged SG-A radius-one projection on its own core command.
6. Deliver final command to that arm's plant.
7. Advance its sole physical delay queue, curvature/yaw/heading/pose to k+1.
8. The next native update reads that arm's new state.

Each arm/repeat/scenario has separate controller/PID/history, CP builder,
VehicleModel, governor/timeline, plant/queue and pose. A runtime-bound feedback
token rejects cross-arm, future, stale and equal-valued foreign states.
Complete native pre/post snapshots and requested command are verified by a
fresh exact NativeBaseline; complete SG trace and plant evolution are checked.
Verification native recomputations are structural checks, separate from the
66 declared arm executions.

Core reset and SG event behavior remain unchanged. Intervention does not
silently clear the physical plant queue. Inactive requires exact zero core/SG
command; pressed/release/reengagement freshly rebase SG. Scenario/config changes
require new instances. SG last-command state is command shaping, not a
physical delay. Native 0.15 s demand alignment remains unchanged, with no new
physical queue.

No production hook, Params/CAN/device write, CarController integration, lane,
model, planner, human-reference or detector input.

## Regression risk and acceptance

This is a mechanism audit, not acceptance. The source-only policy fixes
11 existing 800-sample scenarios, three arms, two repeats; all exogenous input
identities and existing metric masks/windows are unchanged. Baseline/current
must match exactly, and all full state/command/plant/metric repeats must match.
Nonfinite, command/ownership/source/time/reset/bound violations are hard errors.
No arbitrary numerical performance threshold or weighted score.

The local SG sign/magnitude/TV invariants concern its **own pre/post stream**.
They do not imply fewer reversals/saturation or lower tracking error relative
to a baseline whose closed-loop core sees different feedback.

## Finite-horizon diagnostic

Source triangle recurrences bound curvature/yaw for bounded plant inputs;
heading and pose have finite cumulative envelopes. Each bound is rounded
outward toward positive infinity. This is input-bounded plant containment,
**not closed-loop convergence, an asymptotic stability proof, or real vehicle
stability**. A bounded saturated limit cycle can pass containment.

Frozen quarter intervals are [0,200), [200,400), [400,600), [600,800).
RMS/peak, tracking, reversals, saturation and native state endpoints are
reported. Unequal exogenous phases cannot support a growth attribution.
The final three 100-sample blocks are inspected only if their exogenous
demand/intervention/limits are exactly constant. Strict increasing RMS and peak
are descriptive flags; no result-dependent tail selection or extended horizon.

## Replay versus feedback

Historical metrics are read from immutable receipts, not re-evaluated. Local
synthetic replay traces are checked against their frozen SHA and used only for
paired stage/pose deltas. Replay pre-curvature was never native feedback.
New closed-loop metrics reuse the exact existing implementation.

Tables keep baseline closed loop, SG replay, SG closed loop, and both deltas
separate. Phase-lag estimator results retain ambiguity/support; phase estimates
are not fabricated sample-local timestamps. Command sample time and pre/post
state observation time are distinct. Distance queries require observed monotone
forward x and never extrapolate. Nonmonotone x is distinguished from insufficient
distance support in the additive diagnostic.

## Validation method and actual results

Pre-execution: policy/matrix frozen, structural tests and independent review
required before official execution. Actual run/result identities and final
validation counts are recorded after execution; no measurement result
or vehicle qualification is implied by tool readiness.

| Check / stage | Method | Evidence / limitation |
| --- | --- | --- |
| Unit / regression / build | Focused, AutoTune, controls, replay, Ruff, syntax, publication, SCons | Final verification receipt |
| Replay vs baseline | Read exact old replay receipt/trace SHA only | No historical re-execution or metric recalculation |
| Simulation / closed loop | 11 x 3 x 2, own feedback and exact repeats | Descriptive plant only |
| Shadow | Not run | No authority for runtime/device use |

## Handoff

Reference/calibration track remains unchanged:
CALIBRATION_UNCERTAINTY_PENDING,
INDEPENDENT_CALIBRATION_VALIDATION_PENDING,
PIXEL_GEOMETRY_REGISTRATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE,
INDEPENDENT_REFERENCE_UNAVAILABLE.

TA-B remains structural pass / tradeoff only. SG replay remains structural pass /
tradeoff only. CURRENT remains baseline exact alias, V1 tradeoff only, V2 rejected
with 37 historical violations. No retroactive role reinterpretation.

Composition, search, frozen evaluation and acceptance remain unauthorized.
Only a composition recommendation may be recorded. Independent meter result and
total physical bound remain null; sealed reference NOT_GENERATED;
vehicle NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

Rollback is to omit the additive audit; no production behavior was changed.
Next engineering action depends on the separately recorded closed-loop
interaction; it cannot authorize composition or vehicle use.
