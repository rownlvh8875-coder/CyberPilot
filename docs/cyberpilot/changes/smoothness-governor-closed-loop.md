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

Policy/matrix were frozen in 115123b14 before runner implementation.
Official execution used implementation d70e1a69332c8149439fe50c2f1508e435a2d167,
after independent pre-execution review and 117 focused tests.
All 11 x 3 x 2 = 66 arm executions passed exact full trace/metric repeatability.
CURRENT matched BASELINE exactly. All native states were finite and all plant
states stayed within the source-derived finite-horizon containment envelopes.
No hard failure, config mutation, TA-B execution or composition occurred.
No measurement result or vehicle qualification follows from these results.

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

## Actual closed-loop results

Verdict: **SG_CLOSED_LOOP_STRUCTURAL_PASS / SG_CLOSED_LOOP_TRADEOFF_ONLY**.
Interaction: **FEEDBACK_COMPENSATES_GOVERNOR_LAG**, under the predeclared
high-speed tracking/available-phase rule only. Composition recommendation:
**COMPOSITION_NOT_RECOMMENDED**. No architecture-level hard rejection is justified
by this finite run; retain this as historical standalone diagnostic evidence,
with no composition or performance-candidate promotion.

Tracking p95 in 1/m; derivative p95 in normalized torque/s; occupancy is a fraction.
All pose values below are **DESCRIPTIVE_PLANT_COUNTERFACTUAL_ONLY**.

| Scenario | Tracking baseline | Tracking SG replay | Tracking SG closed loop | Requested derivative p95 baseline / closed | Output rail baseline / closed | Same-time peak pose delta m |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| straight | 0.000000000 | 0.000000000 | 0.000000000 | 0.000000 / 0.000000 | 0.00000 / 0.00000 | 0.000000000 |
| gentle_left | 0.014042884 | 0.013825618 | 0.014016282 | 117.200757 / 100.000000 | 0.49625 / 0.52875 | 0.231484418 |
| gentle_right | 0.014042884 | 0.013825618 | 0.014016282 | 117.200757 / 100.000000 | 0.49625 / 0.52875 | 0.231484418 |
| sharp_left | 0.014078378 | 0.013881691 | 0.014166763 | 117.573102 / 100.000000 | 0.49750 / 0.53000 | 0.074017875 |
| sharp_right | 0.014078378 | 0.013881691 | 0.014166763 | 117.573102 / 100.000000 | 0.49750 / 0.53000 | 0.074017875 |
| low_speed | 0.000155993 | 0.000155993 | 0.000155993 | 0.033235 / 0.033235 | 0.00000 / 0.00000 | 0.000000000 |
| medium_speed | 0.014042884 | 0.013825618 | 0.014016282 | 117.200757 / 100.000000 | 0.49625 / 0.52875 | 0.231484418 |
| high_speed | 0.022329503 | 0.023953503 | 0.021510226 | 176.350233 / 100.000000 | 0.70125 / 0.68875 | 22.729413982 |
| s_reversal | 0.014030000 | 0.013851214 | 0.014033914 | 117.169017 / 100.000000 | 0.49375 / 0.52875 | 0.218838920 |
| driver_events | 0.014002343 | 0.013746552 | 0.014014700 | 116.571145 / 100.000000 | 0.40125 / 0.41375 | 0.287080401 |
| limit_flags | 0.014040830 | 0.013820089 | 0.014013421 | 117.194867 / 100.000000 | 0.49625 / 0.52875 | 0.192702172 |

Straight/low-speed signals remain unchanged. Nine scenarios have command/plant effects.
Sharp left/right, S-reversal and driver events have higher tracking p95 than
baseline. Gentle/medium/sharp/S-reversal/driver/limit output rail occupancy rises.
These remain separate from derivative reductions; no weighted score hides them.
High-speed core-input rail occupancy rises from 0.70125 to 0.72 even though SG
output rail occupancy falls from 0.70125 to 0.68875. SG did not eliminate native
core saturation. Compared with replay output rail occupancy 0.585, feedback
raises SG output occupancy. Local no-authority-expansion invariants do not
imply cross-arm saturation improvement.

## High-speed root-cause report

First divergence markers (sample time versus post-state observation time):

| Stage | Sample index | Command/sample time s | State observation time s |
| --- | ---: | ---: | ---: |
| applied_torque | 114 | 1.14 | not a state observation |
| core_requested_torque | 116 | 1.16 | not a state observation |
| output_saturation | 112 | 1.12 | not a state observation |
| plant_curvature_post | 114 | 1.14 | 1.15 |
| plant_curvature_pre | 115 | 1.15 | 1.15 |
| pose_y_post | 114 | 1.14 | 1.15 |
| post_governor_torque | 112 | 1.12 | not a state observation |
| shaping_first | 112 | 1.12 | not a state observation |
| tracking_residual_pre | 115 | 1.15 | 1.15 |

Shaping first differs at k=112. The existing two-step plant queue produces
applied/curvature divergence at k=114; state_(115) is observed at 1.15 s.
The core receives divergent own feedback at k=115 and its requested torque
first differs at k=116. There is no extra SG physical delay queue or future
feedback. Phase-lag divergence is a phase aggregate, not a sample-local event.

High-speed requested derivative p95 remains 100, versus baseline 176.350233.
Requested RMS is 58.780175, versus baseline 72.312877 and replay 58.818700.
Nonzero reversals are 140, versus baseline/replay 153.
Tracking p95 is 0.0215102264, versus baseline 0.0223295032 and replay 0.0239535032.
Exactly one equal-support identified phase-lag comparison is available; its
absolute lag delta is 0 s. Four phase segments are flat/ambiguous/unavailable.
This supports the frozen interaction label but does not establish complete
lag recovery, stability, or general performance improvement.

Same-time peak pose delta from baseline: replay 61.276370161 m versus closed
loop 22.729413982 m. Closed loop versus replay is 38.546956180 m.
Full common observed-x aligned peak delta: closed versus baseline
22.745268632 m; closed versus replay 38.511463813 m. These use separate
monotone observed supports (1480 / 1463 union queries), with no extrapolation.
The 5–30 m high-speed early queries are all exact zero delta, before the
first shaping at 1.12 s. The large later pose divergence is therefore not
removed entirely by feedback and is not solely a feedback-open artifact.
Neither old nor new pose is real vehicle displacement or lane-centering gain.

## Finite-horizon support and remaining oscillation

All 800 samples per arm are finite/bounded under the source containment oracle.
All four quarter blocks disclose 200 samples each. Their changing demand is
not a damping comparison. Ten scenarios have three exactly equal-demand
100-sample tail blocks, with no strict peak-and-RMS growth flag. Driver events
have only 200 final active constant-demand samples after reengagement, so the
frozen 300-sample equal-demand tail requirement is unavailable (0/300).
No response-dependent shorter-tail substitution was made.
Bounded oscillations and rail saturation remain; no convergence/limit-cycle
elimination or real stability is claimed. Full native endpoint states and
per-block RMS/peak/reversal/rail statistics are in the results artifact.

## Receipts and verification

- binding receipt SHA256: 046aaec7019f3aa8125326f95b0df7ad8bdbef1813f3d2037db37fccccb8dc0e
- results receipt SHA256: e2369657aa47cb447bdfbaa1dd72bb7eddc712b0747f34d64a94503e54ca5818
- interaction receipt SHA256: 667c6b36f590c6bc4b9a19c6899024461498a812bc147c3622c3e5e359958f11
- readiness receipt SHA256: 0326dad0852f57d04615f66975fcb879ba248464d05709b3915e7b3cb8f3657b

Official execution: source-only interpreter (-B with a fresh persistent
pycache prefix), smoothness_closed_loop module; local synthetic trace store
separate from Git. Replay history was read by exact SHA, never re-executed
or passed to its metric evaluator.
Focused suite after lossless publication packaging: 124 PASS.
Full AutoTune: 2369 PASS; controls: 142 PASS; combined full suite:
2511 PASS in 904.24 s. Separate controls: 142 PASS; lateral replay: 16 PASS;
privacy: 16 PASS (20 subtests). Ruff, syntax, SCons and branch whitespace PASS.
Publication scanner: 914 files, 0 findings before this verification receipt;
final publication check is also required before push.
Independent pre-execution, aggregate/narrative and lossless packaging review:
PASS, no unresolved findings. Log hashes are recorded in
smoothness-closed-loop-local-verification-v1.json.

The publication root is a separately pinned transport manifest with eleven
per-scenario aggregate shards, each below the unchanged publication scanner
size limit. Reconstruction preserves the full original result receipt exactly;
no metric, native endpoint state or block statistic is dropped or recomputed.
The original complete result and all execution traces remain immutable locally.
No UI added or changed; browser test is not applicable. No new private input
was opened; no private images/coordinates or paths are published.
GitHub Actions is verified separately after push; local checks do not imply CI success.
