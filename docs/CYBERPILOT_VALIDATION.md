# CyberPilot v0.1 validation and vehicle-application preparation

Current vehicle readiness: **NOT_READY**. Last assessment: 2026-10-04 KST.
This is a living preparation document, not approval for vehicle use.

Offline engineering and vehicle qualification are separate decisions. See
[branch completion](cyberpilot/CYBERPILOT_BRANCH_COMPLETION.md) for the final
software test/publication gates, and
[offline v2 change record](cyberpilot/changes/offline-synthetic-v2-and-rehearsal.md)
for the supplied-plan synthetic scope. The following historical qualification
limitations and rejected candidates are preserved; new synthetic execution does
not turn them into PASS results.

Post-completion continuation adds read-only
[candidate failure diagnostics](cyberpilot/changes/synthetic-candidate-failure-diagnostics.md)
and [native longitudinal feedback parity tests](cyberpilot/changes/cyber-long-native-feedback-parity.md).
The v2 longitudinal gain scales leave the pinned Santa Fe Ki vector at zero, so
those candidates exercised no changed longitudinal trace. The new separate
generic test closes native planner/LongControl feedback and verifies observer
parity, not full process replay or calibrated vehicle performance. Neither
extension changes the rejected candidate verdicts or vehicle readiness.

The continuation's unchanged default software test suite completed with 1,526
passed, 42 skipped and one expected failure (exit 0). The separately targeted
AutoTune/controls run passed 619 tests. The
[remaining-work audit](cyberpilot/CYBERPILOT_REMAINING_WORK_AUDIT.md) preserves
earlier incomplete executions and the verified public-fixture resolution; these
software results do not satisfy the unchecked vehicle qualifications below.

The later [planner feedback measurement checkpoint](cyberpilot/changes/planner-feedback-measurements.md)
adds descriptive time-aligned metrics without changing control or acceptance:
626 targeted and1,533 default tests passed (42 skipped,1 expected failure in the
default suite). Missing independent follow/stop-position truth remains null;
generic measurement results do not establish a vehicle gain domain or calibration.

The offline AutoTune contracts and local three-arm comparison do not yet form a
qualified replay/closed-loop/shadow pipeline. The current lateral experiment was
repeatable but failed its unchanged performance gates. Missing evidence must not
be represented as zero error, PASS, a valid calibration or an active profile.

## Scope and current evidence

Previously published offline tooling is on `feature/cyber-autotune`; the
completion report separately records the current publication checkpoint. Every new
validation run must still bind its exact source HEAD, submodules, model, configuration
and environment identities before its results can be compared or promoted.

| Area | Implemented evidence | Still missing |
| --- | --- | --- |
| Cyber Long | disabled/observer and fail-closed proposal scaffolding; historical PC/replay diagnostics | qualified full coupled replay, vehicle-calibrated closed loop, shadow qualification |
| Cyber Lateral | upstream-compatible offline bridge, deterministic synthetic scenario matrix, generic plant and native-controller closed loop, development A/A/candidate repeatability, repository-owned closed-loop structural admission | accepted optimizer candidate, authenticated plant calibration, independent center/edge truth, qualification coverage |
| AutoTune | six-class policy, structural profile guard, finite proposal preview, reviewed durable archive and restartable preview-job integration | producer-authenticated identification/confidence, reviewed search domain, evaluable real candidates, authenticated active profile/history |
| STEP9 | local three-arm receipt comparator/report; native diagnostic workers; external lateral plant receipt structural admission; synthetic source-isolated repeatability and cleanup tests | authenticated metric/plant producers, full longitudinal coupled replay, uncertainty and regression evidence |
| STEP10 | reviewed offline shadow-window scheduler and immutable promotion/fault rehearsal; no activation writer | continuous/on-device shadow, measured active-loop non-interference, authenticated evidence/persistence and executed rollback integration |

Recorded development baseline A/A and candidate-repeatability results are not new
candidate acceptance. The latest historical corrected lateral comparison had
baseline admission6/6 and candidate performance0/6. Do not substitute the older
pre-correction baseline result or promote the rejected candidate.

## Native diagnostic boundary and current verification

On 2026-10-03 the fixed-source strict-cold torqued diagnostic advanced from
NOT_RUN to bounded A/A PASS on the already-approved source-A development segments
6, 13 and 19. Each segment ran twice in a fresh private namespace; every ordered
output digest matched exactly and `first_output_difference=null`. The runs retained
the frozen receive/sample invariants, confirmed child cleanup/terminal coverage,
and recorded zero `estimate_params`, random `get_points`, or `update_params`
calls. All runtime/promotion/candidate authority flags stayed false.

This does **not** clear the qualified replay gate. All three intervals still report
`ever_calculable=false` and `ever_valid=false`; they cannot support an accepted
parameter estimate or candidate. Historical warm-state equivalence, full coupled
replay, calibrated plant evidence, confidence/independent truth, and continuous
non-actuating shadow remain unverified. Detailed evidence is in
`CYBER_AUTOTUNE_RECORDED_COLD_AA_20261003.md` and the frozen result artifact
SHA-256 is `f3eb6a376fcc1cb9522c1bbda9574c45e11228ee31ed0350d85810b428edeb07`.

A later development-only grouped coverage diagnostic preserved 19 explicit route/clock
boundary groups (15 nonempty) rather than flattening them into one synthetic sequence.
The pooled structural counts are 31,595 points with bucket counts
`[104,608,2709,11591,10588,4443,1194,358]`; count minima are therefore covered. A
read-only exact-schema point-identity pass reproduced every final bounded native bucket
and found zero duplicate source-sample IDs within or across groups, zero duplicate signal
times and zero non-increasing times. This removes only the raw-point-identity blocker.
Statistical independence across route clusters remains unverified; no pooled fit,
confidence, candidate generation or promotion ran. The v4 aggregation report keeps
`CROSS_GROUP_STATISTICAL_INDEPENDENCE_UNVERIFIED`, `NATIVE_EPOCH_VALIDITY_NOT_ESTABLISHED`,
`FIT_NOT_AUTHORIZED` and `CANDIDATE_GENERATION_NOT_AUTHORIZED`. Overall readiness remains
NOT_READY. Detailed report: `CYBER_AUTOTUNE_GROUPED_TORQUE_AGGREGATION_20261003.md`.

The subsequent full clean-development expansion froze 85 routes and 2,213 segments,
with 37 nonempty routes, 216,356 accepted points and 16 source commits represented
in the numerical fit. Its structural leave-one-route-out count gate passed. Before
reading any TLS outcome, a route/source-cluster policy fixed 25%/40% dominance limits,
5% factor sensitivity limits, 0.05 m/s² offset limits, and matching route-jackknife
limits. The Gram-matrix TLS result is numerically stable under those gates: pooled
`lat_accel_factor=4.024832798307419`, offset `-0.17960344075536194 m/s²`; maximum
route/source factor deltas are 1.3325%/1.7194%, route/source offset deltas are
0.010512/0.010653 m/s², factor jackknife relative SE is 2.2353%, and offset jackknife
SE is 0.014358 m/s². This is still an authority-free diagnostic: confidence and
parameter identification remain unqualified, and candidate generation, replay
acceptance, profile activation and vehicle use remain blocked. Overall readiness
remains NOT_READY. Detailed report: `CYBER_AUTOTUNE_CLUSTER_TLS_STABILITY_20261003.md`.

A repository-owned plant-calibration evidence contract now verifies the private
aggregate evidence chain without importing route identities, paths, samples or model
coefficients. The result is `DESCRIPTIVE_CALIBRATION_EVIDENCE`: development/validation
roles are disjoint, the model was frozen before validation, no validation refit or
candidate-output selection occurred, and smoke trace/pose are deterministic. It is not
qualified because historical acceptance limits were not precommitted, position truth is
not independent, external reproduction is absent, and the exact current platform has not
been prospectively revalidated. Detailed report:
`docs/cyberpilot/changes/cyber-validation-plant-calibration-evidence.md`.

A prospective current-platform protocol is now frozen at
`2026-10-03T12:11:42Z` before future content access. It binds the exact model,
adapter, plant builder and validation runner, requires independent primary position
truth, predeclared 1/5/10-second limits, minimum route/sequence/sample coverage,
and metadata-manifest freeze before semantic evaluation. Historical evidence is
ineligible with `DATA_PREDATES_PROTOCOL_FREEZE`. A metadata-only scan of 5,602
local rlog/qlog candidates found zero post-freeze logs, so the current status is
`PROTOCOL_FROZEN_AWAITING_POST_FREEZE_EVIDENCE`. Policy:
`docs/cyberpilot/policies/plant-calibration-prospective-v1.json`; report:
`docs/cyberpilot/changes/cyber-validation-plant-calibration-prospective-protocol.md`.

The lateral closed-loop contract now binds that evidence SHA/status to every external
receipt in addition to controller/adapter/plant/domain/input/reset/metric/environment/
timebase identities. Against public HEAD
`dfa0ff8ff465962ecb0e0db2a0f2536ac0a746c1`, the frozen six-window development run
passed strict A/A 6/6 and A/B repeatability 6/6. All 12 arm receipts (1,000 samples each)
passed structural admission and retained `PLANT_CALIBRATION_DESCRIPTIVE_ONLY`,
`INDEPENDENT_REFERENCE_UNVERIFIED` and `PERFORMANCE_GATE_NOT_EVALUATED`. The aggregate
result repeated byte-identically with SHA-256
`06332c1492de07f92b26aae9a833af081063160a454b38cef02eed8f928703c7`. Every prior
A0/A3 trace hash and metric was unchanged, so no integration drift was observed. A3
still passed 0/6 performance gates, remains rejected, and cannot proceed to shadow.
Detailed report: `docs/cyberpilot/changes/cyber-validation-lateral-closed-loop-admission.md`.
Sanitized receipt: `docs/cyberpilot/changes/cyber-validation-lateral-closed-loop-admission-result.json`.

A deterministic synthetic lateral matrix now freezes 14 offline scenarios before any
controller or plant execution. Twelve nominal cases cover straight, left/right gentle
and tight curves, S-curve, ramp, lane change, driver override/release/reengagement,
low/medium/high speed, entry/apex/exit and saturation. Two rejected-input cases cover
sensor dropout and a single timebase gap; delay-high and friction-low/high stress axes
are also explicit. Catalog SHA-256 is
`c92cb9e71a9e9c0273f56a6ca3966b7d92fda5c67aa47742aa852a0b3a14928c`.
The matrix is deterministic and structurally complete, but no controller, plant or
vehicle path was executed and `SYNTHETIC_ONLY_NO_PHYSICAL_QUALIFICATION` remains.
Detailed report: `docs/cyberpilot/changes/cyber-validation-synthetic-lateral-matrix.md`;
sanitized result: `docs/cyberpilot/changes/cyber-validation-synthetic-lateral-matrix-result.json`.

A repository-owned generic lateral plant now provides a deterministic, transparent
software-stress response surface with one plant-owned 30 ms physical delay queue,
normalized-command friction deadzone, first-order lag, saturation and left/right
symmetry. Zero input remains exactly zero, reset reproduces the same trace, and
friction-low/high responses preserve the expected ordering. It is explicitly classified
`GENERIC_SYNTHETIC_NOT_VEHICLE_CALIBRATION`: no controller was executed and no actual
vehicle friction, tire response, steering ratio or time constant is claimed. Result
SHA-256 is `2410c5e4d373c9d4eb0af5d0dc5afe0929e0894065c793560315f9e7261b7751`.
Detailed report: `docs/cyberpilot/changes/cyber-validation-synthetic-lateral-plant.md`;
sanitized result: `docs/cyberpilot/changes/cyber-validation-synthetic-lateral-plant-result.json`.

The actual `LatControlTorque` implementation was then connected to that generic plant
with fresh state for all 14 frozen scenarios. Twelve nominal runs completed and both
fault inputs were rejected before controller execution. The aggregate result repeated
byte-identically with SHA-256
`5b287382df84d7d95f253479dcce3be93447fd9477de132426ca9a9953d123f5`.
Straight cases remained exactly zero and left/right curves were symmetric, but tight
curves and the ramp showed about 79–80% torque saturation with very large generic-plant
tracking errors; driver override also exposed a large synthetic steering-jerk transient.
This is therefore a deterministic baseline and defect-finding result, not a performance
pass. `GENERIC_SYNTHETIC_PLANT_NOT_VEHICLE_CALIBRATED` and
`PERFORMANCE_GATE_NOT_EVALUATED` remain. Detailed report:
`docs/cyberpilot/changes/cyber-validation-synthetic-lateral-closed-loop.md`;
sanitized result:
`docs/cyberpilot/changes/cyber-validation-synthetic-lateral-closed-loop-result.json`.

Before any new candidate execution, a relative no-regression/improvement policy was
committed and pushed with SHA-256
`ae4ad7f1cad3e4e5f138df2d4ef8feae17e881a951a5b37caa481fd124ba2a62`.
It binds all 14 scenarios, catalog/CarParams identity, sample counts, fault outcomes,
left/right symmetry and the baseline internal report. The baseline self-check returns
`SYNTHETIC_NONREGRESSION_PASS`, with no regressions, preserved symmetry/fault identity
and `improvement_pass=false`; it repeated byte-identically with SHA-256
`3d07f9be8afa562333db535755c8f97d86fb476d204b9592f3cc5f0ae3c7f559`.
No candidate was executed and candidate/shadow/runtime/promotion authority remains false.
Detailed report: `docs/cyberpilot/changes/cyber-validation-synthetic-lateral-gate.md`;
self-check result:
`docs/cyberpilot/changes/cyber-validation-synthetic-lateral-gate-selfcheck-result.json`.

The new LongControl worker consumes exogenous plan/state/event samples, fixed serialized
CP, native Float32 messages, stock engagement/reset and source-derived PID limits.
It reports requested acceleration before CarController/CAN, not applied plant input.
The frozen PID envelope is not panda safety or a tunable limit. No controller changed.
Baseline/current/current-as-candidate each repeat twice on synthetic inputs only.

Independent review found that disabled bytecode writes still permit stale cache reads.
Both native workers now use a fresh private empty cache prefix with writes disabled.
The same-size/same-second stale-cache regression failed before the fix and passes after;
existing source caches are preserved. This is not complete build attestation or hostile
code containment. Cached-source-era results remain historical, not upgraded silently.

Current laptop package checks:246 AutoTune tests781subtests PASS. The previous
controls+AutoTune375 result predates the test-only follow-up; fresh default PC below
includes the new tests and upstream controls. No production change in this follow-up.
The bounded shadow terminal-fault accounting repair now counts an unread buffered
result exactly once under the existing lock. Both axes and five fault/close/poll modes
have regression coverage; independent review found no issues. No controller changed.
Reviewed longitudinal offline shadow windows now reuse the bounded scheduler; three
11-frame synthetic windows repeat native requested-accel/state traces with no authority.
The STATIC wheelbase metadata now resolves to the actual opendbc VehicleModel;
its unit, classification, physical value and denied proposal permission are unchanged.
The new reviewed frozen-point torque TLS module reproduces native numerical estimates
without constructing the live estimator. Confidence stays unknown; all candidate/update
authority remains false. Synthetic repeatability is not real parameter identification.
Longitudinal three-arm orchestration/reports now reuse the reviewed native worker and
bind the same frame/control ownership across arms; all diagnostics require six complete
repeatable runs. The initial affected352/1failure exposed descendant kernel-exit timing.
Shared lifecycle now confirms owned-group termination without weakening original tests;
new delayed-exit regression RED->GREEN and independent review passed. Confirmation polling
is bounded, not a hard-real-time guarantee for communicate/kernel stalls.
Six synthetic runs per axis repeat after the cache fix; no candidate improvement claimed.
The earlier preview-inclusive default PC run passed1236/42skipped/1xfailed,1148.67s,exit0.
It predates longitudinal/cache fixes. The later1328-collected default run timed out124
at2400s, with1218passed/41skipped/1xfailed/1error partial records; it predates matrix/
cleanup/identification changes. The recorded TestLocationdScenarios.setUpClass error
did not recur in the targeted base check:1passed603.82s, actual body2.61s. The old
error's cause remains unproven because interruption suppressed its final details.
Run13540 collected1348 tests before the longitudinal shadow extension and finished
1273passed43skipped1xfailed in2273.80s, exit0. This is PRE_EXTENSION evidence: all9 old
shadow tests had ended before shared hooks were edited. It does not verify the later
hooks/new longitudinal shadow tests. Post-extension run79116 finished1281passed,
43skipped,1xfailed in1993.65s,exit0;1356collected. Its71 source/document overlay
hashes and Git/submodule/index/observer/Python identity matched before/after.
That run predates the later one-line terminal-drop accounting repair. Post-repair
run40549 collected1357 and finished1282passed43skipped1xfailed in1183.59s,exit0,
using the same2400s budget and unchanged tests. Before/after73overlay hashes and
Git/submodule/index/observer/Python identity matched. Final Ruff/diffcheck PASS.
These counts are software regression, not qualified replay/plant/device evidence.
Subsequent test-only follow-up46212 collected1360:1285passed43skipped1xfailed,
2354.94s,exit0; before/after73overlayfiles and recorded identity fields match.
It closes range-only all-or-nothing preview and mixed-group comparison coverage
gaps. Isolated mutants are rejected; independent review found no issues. Existing
controller/source and all empirical gates remain unchanged.
Real qualified stages remain NOT_RUN.

Frozen STEP5 predecessor remains BLOCKED: recorded segment29 repeatability passed,
but strict recorded-behavior A/A after approved warmup failed (maximum requested-accel
error0.07648241519927979 m/s² against unchanged1e-6). Generated delivery traces
cannot replace independent historical capture. Preserve this gate before coupled
qualification; generic planner simulation or unit PASS cannot discharge it.

## Validation stages

1. **Source/input admission.** Verify exact source, submodules, dirty overlay,
   CP/fingerprint/firmware/model, schema, unit producer, active parameter epoch,
   input digests, reviewed development split/coverage and role authority.
   Previously seen development data stays development. Holdout/validation remain
   sealed unless their separate authority/gate is satisfied.
2. **Offline identification and proposal.** Check identifiability, input stage,
   units/sign, causal time alignment, excitation/conditioning, sample independence
   and reviewed uncertainty. Bind range/delta/rate/update interval and confidence
   policy. `SAFETY_LOCKED`, user preference and static identity cannot be optimized.
3. **Native replay.** Freeze upstream/current/candidate arm identities and initial
   state. Repeat each independently. Compare ordered output traces and all metric
   records, not only summary means. Preserve references; do not auto-update them.
4. **Calibrated closed loop.** Reuse reviewed plant/domain/timestep and exactly one
   physical actuator-delay owner. Run predeclared scenarios and identical masks.
   Out-of-domain output is a failure, not a reason to select a friendlier window.
5. **Non-actuating shadow.** Only after replay and simulation requirements pass,
   compute candidate separately; candidate results cannot reach actuator transport.
   Same input epoch/time, comparison stage and profile identity are mandatory.
6. **Limited activation.** Separate explicit vehicle-operation approval, reviewed
   deployment/configuration and rollback mechanism, qualified platform latency,
   vehicle-specific safety review and operator checklist are required. No current
   tool grants this stage.
7. **Active profile.** Requires the preceding staged evidence and explicit reviewed
   policy. A local report PASS or a content digest is never an activation token.

Replay precedes simulation in the current development workflow. A final replay of
the same candidate after simulation may detect integration drift; both gates must
be complete before shadow. Do not infer permission to skip either from stage names.

## Metrics and decision rules

Lateral priorities: independent lane-center error, curve/path/cross-track error,
left/right and entry/apex/exit error, edge margin, steering tracking, jerk,
oscillation amplitude, saturation and driver intervention. PSD peak frequency alone
is diagnostic, not a monotonic loss. Integrated model-path displacement is not
independent lane-center truth.

Longitudinal records: target/actual acceleration, lead distance/relative speed,
jerk, stop/start timing, braking events and intervention. Counterfactual stopping
distance, launch delay and lead response need a calibrated closed-loop environment;
recorded exogenous lead/driver behavior cannot establish real candidate improvement.

Compare upstream baseline, Cyber current and the candidate on identical declared
groups. Hard-constraint violations reject the candidate. No important regression
may be compensated by comfort improvements. Missing/mismatched data, unknown units,
timeout or unsupported domains require revalidation. Establish primary-improvement
and uncertainty criteria before observing candidate results. No test/reference or
threshold relaxation is allowed to manufacture acceptance.

Required regression coverage includes straight/gentle/tight/left/right curves,
low/medium/high speed, curve entry/apex/exit, lane change, driver override, steering
release/re-engagement and saturation. Route tags also distinguish ramp, urban,
highway, stop-and-go and cut-in. Frame count is not independent sample count.

## Shadow isolation contract (offline subset implemented; runtime unqualified)

The offline native worker is a reusable execution component, not this full shadow
contract. Its supervisor blocks the caller; do not place it in the active control
thread. The new asynchronous window scheduler bounds pending/result queues, counts
gaps, rejects stale output and isolates immutable active observations. Native state
resets per window; this is not continuous shadow. Validation/locking are not real-time,
so the scheduler API also remains prohibited on an active-control thread. Separate
lateral and longitudinal window comparisons now exist, using private built-in axis
hooks and immutable active traces. Longitudinal comparison binds the same control owner,
reports requested m/s² differences and removes all metrics on expiry. These are not
brake/actuator commands or physical safety saturation. Synchronized continuous two-axis
shadow and device latency remain unimplemented/unqualified. Runtime authority stays false.

- Existing active controller remains the only actuator authority. Do not insert
  candidate output into `carControl`, `sendcan`, vehicle-controller inputs or Params.
- Candidate has an independent state and bounded input queue. Copy immutable
  snapshots; never share the active controller's PID/filter/learner state.
- Observe command differences at the same stage and units: requested torque is not
  applied CAN torque; planner acceleration is not actuator acceleration. Bind any
  conversion and delay once. Do not subtract unlike signals.
- Slow candidate, full queue, exception or missing output must not block the active
  loop. Drop/mark the candidate sample and record the gap. Timeout is not zero error.
- Candidate process termination/cleanup must target only the owned process handle,
  not other controllers or global processes. No device transport handles are passed.
- Measure latency, sequence gaps, saturation and boundary proximity; replay-laptop
  timings cannot qualify the device platform. A software unit test cannot prove
  on-device fault isolation by itself.

## Promotion, profile versioning and rollback

Profiles must bind fingerprint, source/parameter revision, configuration, evidence,
metric/adapter, training/evaluation groups, confidence method/results, baseline,
previous profile and rollback target. Digest verification proves content identity,
not reviewer authenticity. Compatibility changes invalidate prior validation.

The current `ProposalBinding` only represents an initial review proposal with
previous==baseline==rollback. The reviewed Linux offline archive now persists and
reopens validated proposals and STARTED→one terminal audit chains using immutable
no-overwrite publication and file/directory fsync. STARTED-only remains incomplete;
terminal execution is not qualification. Corrupt/conflicting records are rejected
and preserved, not repaired. This is not an active `CyberTuneProfile` store, an
atomic runtime updater or authenticated history. Signed/trusted checkpoints and
physical storage/platform qualification remain absent.

The reviewed preview-job workflow now binds exact template/grid/evaluator identities,
durably records STARTED before any proposals and terminal only after the entire grid.
Restart inspection checks every proposal, not just a terminal marker; missing/corrupt
completed artifacts block without repair. Partial publication permits explicit retry.
Storage failure is never acknowledged as durable completion. Its highest status is
STRUCTURAL_PREVIEW and no evaluator or actual candidate generation is authorized.

The immutable promotion rehearsal checks bound, ordered simulation-screen/replay/
final-calibrated-simulation/shadow receipts. Even a complete asserted PASS history
ends awaiting separate vehicle approval with runtime authority false. Fault advice
distinguishes quarantine, requested rollback and required operator intervention;
prior failed gates remain visible. No requested rollback is reported as executed.

| Failure | Required response before activation | Additional requirement for any future active updater |
| --- | --- | --- |
| Regression threshold exceeded | reject candidate, retain reference | bounded safe return to verified prior profile |
| Unexpected saturation/domain violation | stop candidate evaluation, record exact gate | reviewed fallback/driver notification, never increase limits |
| Profile corruption/source mismatch | reject loading or promotion | verified compatibility and atomic persistence before switching |
| Controller exception/timeout | isolate/disable candidate, active path unchanged | independently reviewed runtime fault handling |
| Confidence loss/insufficient samples | stop candidate promotion | validated conservative fallback; no blind last-estimate update |
| Invalid vehicle state/override | no candidate application | stock cancel/override precedence must remain immediate |
| Rollback target missing/corrupt | no activation, no guessed replacement | fail closed using previously established safe behavior |
| Audit disk full/missing checkpoint | mark run incomplete, no promotion | preserve known active state, prohibit untraceable updates |

Automatic rollback is not implemented. No current code changes the active vehicle
profile, so the stock active controller remains unchanged on all new-tool failures.
Future runtime rollback must be designed as a state/ownership transition, not merely
overwriting a parameter during engagement.

## Retrospective development evaluation

A deterministic route-hash split was frozen before evaluation. It produced 27 fit
routes and 8 development-evaluation routes and passed its numerical gates, but four
source commits occur in both sides. It is route-disjoint, not source-disjoint, and is
not independent holdout evidence. The fit estimate was 4.0218395908764 with offset
-0.17678726243336682 m/s²; evaluation RMSE was 0.26880707487851535 m/s².

A separately frozen source-hash split preserved source disjointness but produced only
13 fit sources and 2 evaluation sources, below its predeclared minimum. It was blocked
before fitting with INSUFFICIENT_SOURCE_DISJOINT_SPLIT and was not altered after the
result.

Leave-one-source-out evaluation then held out each of 15 eligible source commits once.
All 15 folds passed their predeclared development gates. The equal-source reference
estimate was 4.143064765944319 with offset -0.16857079743173622 m/s². Maximum held-out
source RMSE was 0.29397200544801755 m/s², maximum absolute mean residual was
0.07417210654295672 m/s², maximum evaluation/fit RMSE ratio was 1.1851354995457644,
maximum factor deviation was 1.2099887061635247%, and maximum offset deviation was
0.0053990778818112095 m/s².

These are retrospective development diagnostics: all routes were previously inspected.
Confidence remains unqualified, candidate generation and qualified replay remain blocked,
and neither 4.02 nor 4.14 is approved as an active vehicle parameter. Detailed evidence:
CYBER_AUTOTUNE_RETROSPECTIVE_EVALUATION_20261003.md. Overall classification remains
NOT_READY.

A separate route-label-disjoint retrospective evaluation then froze all 17 local routes
absent from the complete development intake before opening any content. Pilot technical
screening retained 11 routes; full-route source identity checks excluded two later-drift
routes, and a zero-point route was excluded by the predeclared 100-point minimum. The
final evaluation used 8 nonempty routes from 8 distinct source commits, 76,001 accepted
points and bucket counts `[242,1570,7671,23524,26908,12282,2959,845]`, with zero
cross-route or within-epoch sample/time duplicates. All three already-frozen models pass
the absolute route-balanced gates: point-weighted development RMSE/mean residual
0.2454603669/0.0318597971 m/s², route-balanced development
0.2449451873/0.0291343635 m/s², and source-balanced development
0.2512116301/0.0172427283 m/s². Model selection remained disabled and `selected_model`
remained null. Because these logs existed before the evaluation design, this is stronger
retrospective route-disjoint evidence, not a prospective independent holdout. Confidence,
candidate generation, replay qualification and vehicle use remain blocked. Detailed
report: `CYBER_AUTOTUNE_UNTOUCHED_EVALUATION_20261003.md`. Overall classification remains
NOT_READY.

## D-drive evidence-preserving cleanup

After the retrospective set was content-bound, 5,052 low-utility files were deleted:
4,713 unreferenced qlogs whose same segment retained a non-zero full rlog, 33 exact
duplicate/zero-payload copies, and 306 zero-byte lock files. Logical deletion size was
3.334 GiB and filesystem free space increased by 3.343 GiB. All 3,665 prior-development
files remained at their expected sizes; all 1,687 retrospective-evaluation files were
rehashed and matched their frozen SHA-256 identities; 63 explicitly referenced qlogs,
839 qlog-only files, all non-zero cameras and all unique rlogs were preserved.

The untouched fixed-model runner was rerun after cleanup. Its output remained byte-identical
with SHA-256 `2510eadb5959f062e783f0c76713fd8ceee967fbd477546759dff959a75fddad`.
No evidence gate, model value, authority flag or readiness classification changed. Detailed
report: `docs/cyberpilot/changes/cyberpilot-d-drive-data-curation.md`.

## Logging and privacy

Every run needs source/config/input/metric/adapter/plant/reset/mask identities,
command and exit status, repetitions, processing outcome, gate reasons and missing
coverage. Failures/timeouts must survive in the audit record. Report PASS, FAIL,
REVALIDATION_REQUIRED, BLOCKED and NOT RUN with their exact scope.

Do not publish personal logs, CAN/GPS/video, private simulator code/settings/results,
credentials or raw route labels. Public tools should emit aggregate metrics and
validated content IDs. Keep approved local reports separate from public commits.
Hash chains without trusted checkpoints do not detect full-history rewriting.

## Readiness definitions

- **READY_FOR_REPLAY:** complete input/source/adapter readiness and reproducible
  isolated native runner for the declared validation scope. Not road-use approval.
- **READY_FOR_SHADOW:** required replay and calibrated simulation acceptance,
  confidence/coverage and shadow isolation prerequisites all verified on the exact
  candidate/platform. Still not actuator authority.
- **NOT_READY:** any mandatory prerequisite absent, blocked, failed or unverified.

Current vehicle classification is **NOT_READY**: real tune qualification and
vehicle-calibrated, qualified metric/plant/longitudinal integration are missing.
Independent physical truth/coverage remain incomplete, and no accepted optimizer
or qualified on-device shadow integration exists. The generic synthetic and
offline immutable-window integrations are described in the completion report.

## Real-vehicle checklist — do not execute yet

- [ ] Exact vehicle/firmware/model/software/configuration identities verified.
- [ ] Existing longitudinal ownership and driver preferences preserved.
- [ ] Independent dataset roles, masks and validation authority reviewed.
- [ ] Source-bound native A/A/repeatability and all regression gates passed.
- [ ] Calibrated plant input stage/domain/timestep/delay verified; no duplicate delay.
- [ ] Independent center/edge truth and longitudinal scenario metrics sufficient.
- [ ] Confidence and maximum-delta/update-rate policy verified from actual data.
- [ ] Shadow non-interference, latency/backpressure/exception tests qualified.
- [ ] Versioned profile persistence/rollback and audit failure tests qualified.
- [ ] Panda/opendbc safety, actuator clipping and driver override unchanged.
- [ ] Separate explicit approval for the exact device/vehicle operation received.

## Development references

- [Offline engineering release checklist](cyberpilot/CYBERPILOT_RELEASE_CHECKLIST.md)
- [Manual vehicle-evaluation preparation, Korean](cyberpilot/MANUAL_VEHICLE_EVALUATION_KO.md)
- [Remaining-work audit](cyberpilot/CYBERPILOT_REMAINING_WORK_AUDIT.md)

- Historical local report identifiers (not bundled in this public tree):
  `CYBER_AUTOTUNE_RETROSPECTIVE_EVALUATION_20261003.md`,
  `CYBER_AUTOTUNE_STEP8_POLICY_PROFILE_RESULT_20261002.md`,
  `CYBER_AUTOTUNE_STEP8_GRID_AUDIT_RESULT_20261002.md`,
  `CYBER_STEP9_COMPARISON_CORE_RESULT_20261002.md`,
  `CYBER_LATERAL_STEP7_D3Y_CORRECTED_GATE_REPORT_20261001.md`.
- Repository safety requirements: docs/SAFETY.md (unchanged in the repository).

Update this document when implementation/evidence changes. Do not mark unchecked
items complete from synthetic tests or reused historical results alone.

## A1 synthetic native integration evidence

The [A1 speed-tune experiment](cyberpilot/changes/a1-native-speed-tune.md) passed
native parameter application, exact disabled/identity parity and repeated-process
checks using repository-owned synthetic inputs. Requested torque differences are
not applied steering performance. Center deviation, lane edge margin and physical
steering jerk remain unavailable at this boundary. Fixture-only parameter bounds
are not vehicle calibration. No new vehicle checklist item above is checked off;
qualified replay, calibrated closed loop and device shadow remain unverified.
