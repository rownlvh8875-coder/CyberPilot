# CyberPilot v0.1 validation and vehicle-application preparation

Current readiness: **NOT_READY**. Last assessment: 2026-10-03 KST.
This is a living preparation document, not approval for vehicle use.

The offline AutoTune contracts and local three-arm comparison do not yet form a
qualified replay/closed-loop/shadow pipeline. The current lateral experiment was
repeatable but failed its unchanged performance gates. Missing evidence must not
be represented as zero error, PASS, a valid calibration or an active profile.

## Scope and current evidence

The offline tooling is committed and published on `feature/cyber-autotune`; the
current evidence no longer depends on a dirty working-tree overlay. Every new
validation run must still bind its exact source HEAD, submodules, model, configuration
and environment identities before its results can be compared or promoted.

| Area | Implemented evidence | Still missing |
| --- | --- | --- |
| Cyber Long | disabled/observer and fail-closed proposal scaffolding; historical PC/replay diagnostics | qualified full coupled replay, vehicle-calibrated closed loop, shadow qualification |
| Cyber Lateral | upstream-compatible offline bridge, development A/A/candidate repeatability, repository-owned closed-loop structural admission | accepted optimizer candidate, authenticated plant calibration, independent center/edge truth, qualification coverage |
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

Current classification is **NOT_READY**: real tune qualification and native
metric/plant/longitudinal integration are missing, primary truth/coverage remain
incomplete, and no accepted optimizer or measured shadow integration exists.

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

- [Retrospective route/source evaluation](CYBER_AUTOTUNE_RETROSPECTIVE_EVALUATION_20261003.md)
- [AutoTune policy/profile result](CYBER_AUTOTUNE_STEP8_POLICY_PROFILE_RESULT_20261002.md)
- [Grid/audit result](CYBER_AUTOTUNE_STEP8_GRID_AUDIT_RESULT_20261002.md)
- [STEP9 comparison result](CYBER_STEP9_COMPARISON_CORE_RESULT_20261002.md)
- [Corrected lateral gate record](CYBER_LATERAL_STEP7_D3Y_CORRECTED_GATE_REPORT_20261001.md)
- Repository safety requirements: docs/SAFETY.md (unchanged in the repository).

Update this document when implementation/evidence changes. Do not mark unchecked
items complete from synthetic tests or reused historical results alone.
