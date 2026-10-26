# Simulator selective reuse audit

## Identity and purpose

Cyber Validation; source-level audit and nonexecuting contract/scaffolding increment.
Audit anchor: CyberPilot 46e41ad2f2e11cd4aee926b47d037c46d226108c.
Implementation base: feature/cyber-autotune at 3a3bec6f07fc7c217e4c8a024217e755be065261.
The newer future-data increment is preserved and included in overlap analysis.
Purpose: select validation/replay/visualization ideas without importing simulator
plants, candidate results, thresholds or authority.

## Original references

- [Public simulator exact commit](https://github.com/rownlvh8875-coder/Carrot-comma-SIM/tree/50af6679956ed4ef0f13214f832b8f65e212e370), verified main.
- [Private simulator exact commit](https://github.com/rownlvh8875-coder/carrotsimPrivately-/tree/4c2d094f188b072172de6e8d848dfb4a31b23bd9), verified carrot-sim-v0.
- [Exact source identities](simulator-source-identity-v1.json): repository visibility,
  commit/tree/Git blob/SHA-256, reviewed function/class source slices and normalized AST hashes.
- [Component matrix](simulator-reuse-matrix-v1.json), [overlap](simulator-overlap-analysis-v1.json),
  [audit verdict](simulator-reuse-audit-v1.json).
- Public NOTICE.md explicitly says no redistribution license has been selected.
  Private exact tree has no license file; no grant is inferred. No simulator code
  is copied, vendored, imported or executed. The new contracts and validators
  are independently implemented using existing CyberPilot receipt utilities.
- No submodule, production controller, model asset or build dependency changes.

33 source files were retrieved with authenticated, exact-commit GitHub GETs and
verified against their Git tree blob identities. No private data, log, image,
video, evidence directory, config backup or run-result file was opened. README
and moving branch labels cannot substitute for exact source.

Two requested public modules are absent at that commit:
simulation_fidelity_tiers.py and behavior_metrics.py. Their private counterparts
are separate audited components; neither is silently attributed to the public tree.

## Source findings and adoption decisions

35 classified entries: 19 ADAPT_REQUIRED, 8 DUPLICATE_STRONGER_CYBERPILOT,
8 REJECT_UNSAFE_OR_STALE, 0 REUSE_AS_IS. The matrix includes useful substructures
and rejected subfeatures for each module; an ADAPT verdict does not admit its runtime.

| Area | Useful source mechanism | CyberPilot decision |
| --- | --- | --- |
| H1/config | Epoch, loop/config sequence, canonical config SHA, consumed snapshot identity, service masks | Adapt to lateral contract; longitudinal modelV2/radar/trigger schema is incompatible |
| Campaign comparison | Exact paired grid and manifest/controller/plant/config identities | Duplicate; CyberPilot per-arm provenance/repeatability is stronger |
| Route partition | Deterministic route assignment | Duplicate; hash buckets omit logger lineage, prior analysis, source/profile and role-before-open checks |
| Sealed holdout | Campaign/finalist-set drift rejection and exposure count | Adapt CLOSED exposure plan; append-on-every-open and non-atomic writer are rejected |
| Scenario catalog | Objective/steps/coverage metadata | Adapt schema idea only; weighted novelty/budget selection excluded |
| Safety policy | Explicit failure reasons | Reject imported TTC/jerk/error thresholds and different saturation semantics |
| Axis interface | Separate state/reset ownership, invalidation after partial failure | Adapt design only; no coefficients, dynamics, teacher forcing or runtime composition |
| Visual frames | Receipt SHA, null availability, paging, exact paired grid | Adapt mapping design; no private paths, lane/planner reference or angle/command conflation |
| Visual server/UI | Loopback and self-contained playback | Adapt design; optimizer endpoints, decorative digital-twin claim and index-only pairing excluded |
| Private eligibility | H1/config linkage and completeness checks | Duplicate; longActive/modelV2 dependence and READY_HOLDOUT inference are weaker |
| Private config matcher | Explicit history vs inferred timestamp distinction | Adapt concept only; filename/mtime cannot establish active configuration |
| Private candidate/role modules | Historical workflow-specific logic | Reject model/camera anchors, nearest-time data, fixed candidate preferences |
| Private replay executor | Queue synchronization and stale job rejection | Adapt design only; no mutable job deletion, subprocess/Params execution or automation |
| Private replay series | Longitudinal nearest-time series | Reject future-nearest alignment and missing flags filled with zero |
| Private behavior/fidelity | Descriptive metric and claim ceiling separation | Adapt tier contract; no longitudinal metric or plant claim import |

Private visual catalog/parser additionally pins a historical event count, unlike
the public positive-count check. That stale dataset assumption is not imported.
Generic campaign parameter attribution credits each read changed parameter when
any monitored trace differs; it does not establish per-parameter causal effect.

Call paths were inspected without execution: H1 JSONL parser -> per-record
hash/semantic verifier -> evidence-set qualification; campaign manifest/grid ->
comparison -> safety evaluator; visual catalog -> SHA-bound rows -> normalization
-> exact-grid pairing/paging -> loopback GET/HEAD/UI; private route scanner ->
accumulator -> H1/config/active completeness -> eligibility; replay executor v2 ->
mutable queue -> inherited runtime worker. These traces explain the adaptation
boundaries rather than treating module names as behavioral proof.

## Changes and expected effect

Added three independent Python modules: contract builders, pure synthetic boundary
checks, and exact publication validation; two focused test modules; eight sealed
JSON artifacts. No existing CyberPilot file is changed.

Lateral H1 contract preserves process/config/input identity, distinct torque
stages, raw CAN representation, steering angle/rate, nullable limit/driver fields,
events, source clocks and per-service masks. The synthetic checker rejects
snapshot/config/epoch/sequence/timing drift, including decreasing decisions and
capture before the preceding decision within a sequential epoch. Desired curvature remains controller
intent; actual curvature needs explicit source/frame provenance. Raw post-controller
command is not EPS acknowledgement. No cereal IDs, production observer or overlay
is implemented. Actual source-specific producer verification remains required.

Holdout exposure plan binds campaign, sorted exact model set, model-set digest,
purpose, admission and metric policy. Resume requires identical CLOSED content;
drift or an already opened/count-positive record is rejected. It creates no file,
increments no exposure and provides no opener. Future private one-time atomic
journal persistence remains a separately authorized implementation.

Fidelity tiers are non-authoritative ceilings:
T0_REPLAY, T1_DESCRIPTIVE_COUNTERFACTUAL, T2_EMPIRICAL_PLANT_CLOSED_LOOP,
T3_SENSOR_WORLD_CLOSED_LOOP. Existing descriptive TA/SG evidence cannot exceed T1;
SG own-feedback ordering remains distinct from frozen-command replay. One-step
empirical/CV evidence is not a simulation tier. T2/T3 are unavailable: measured
provenance, admissible empirical model, untouched holdout, domain and feedback
proof are required. No tier implies calibration, safety or vehicle qualification.

Visual adapter scaffolding validates exactly baseline/current/candidate metadata,
relative integer origin/dt/count identity, source receipt digests, missing fields
and loopback scope. It produces a sealed plan, not frames or a server. Current
public receipts contain trace hashes/aggregates, not the full trace rows needed
for a frame conversion, so actual conversion is blocked. Future SG source mapping
is specified from the inspected trace producer: pre is core/pre-governor output,
requested is post-governor output, and curvature/heading/pose are post-step.
Pre-limit torque and measured steering angle stay null where the trace lacks
them. No private trace is opened to fill those gaps. Carrot ego.pose/metrics/events
shape is a future rendering target, with explicit lateral units, evidence tier,
blockers and immutable verdict. No optimizer API or external assets.

Alternatives considered: wholesale simulator import (rejected for schema,
license and authority conflicts); reusing only conceptual structures through
small independent contracts (selected); rewriting existing CyberPilot replay and
admission infrastructure (unnecessary duplicate).
No new tunable constants or acceptance thresholds. State is caller-owned synthetic
input; checks do not mutate it. No actuator delay state, runtime/controller reset,
model fitting, selector, candidate execution or vehicle authority is added.

## Regression risk and acceptance

Risks: stale commit/document substitution; confusing raw/normalized/measured
steering units; hiding unknown limiter provenance; repeated holdout exposure;
mispaired visual grids; lower-tier evidence promoted to physical truth.
Acceptance: pinned source identity, exact historical bytes, deterministic sealed
contract output and rejection of unsafe/drifting inputs. Existing calibration and
reference dependency graph remains authoritative. No new metric threshold,
scenario, private holdout, candidate result or plant is evaluated.

Rollback: remove this additive commit; no production migration or runtime consumer.
Independent review approved the final source facts and contract boundaries.
Two findings were reproduced before repair: a commit-query SHA mistaken for the
actual tree object SHA, and missing cross-loop decision/capture clock ordering.
Three added regressions pass; exact tree identities and sealed contracts were
revalidated after the fixes.

## Validation method and actual results

Validation runs in the existing Ubuntu 24.04 environment with the pinned native
dependencies. Detailed execution receipts/logs remain local; only aggregate
verification outcomes are published here after completion.

| Check / stage | Method | Actual result and limits |
| --- | --- | --- |
| Focused contracts/publication | unittest test_simulator_reuse and test_simulator_reuse_publication | 69 PASS, including three independent-review regressions |
| AutoTune / controls / lateral replay | Existing native test runner and two explicit lateral replay modules | AutoTune 3,264 PASS (1,046.57 s); controls 142 PASS; lateral replay 16 PASS |
| Ruff / syntax / publication / privacy / authority / diff | Existing branch checks | Ruff lint PASS across AutoTune/publication; new files format PASS; syntax/publication/privacy/authority/diff PASS |
| Native build | scons -u -j 4 | PASS |
| Source identities | Exact repository/tree/blob + SHA-256 inspection | 33 source blobs verified; exact commit/tree identities verified; 2 requested public paths absent |
| Simulation / shadow / vehicle | Not applicable to contract-only increment | NOT_RUN / NOT_AUTHORIZED |

## Handoff

SIMULATOR_REUSE_AUDIT_COMPLETE means the source comparison is complete, not runtime
integration or model readiness. Source adaptation/actual visual conversion and H1
producer implementation require their own authorization and source-specific tests.

Preserved: SOURCE_GRID_OBSERVATION_REJECTED,
CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED,
NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, CLOSED_MISSING_ADMISSIBLE_MODEL,
HOLDOUT_OPENING_CLOSED, FUTURE_UNTOUCHED_HOLDOUT_REQUIRED,
STAGE_B_SIGNAL_ADMISSION_BLOCKED, historical V3 tradeoff/attribution/causal recovery,
TA_STANDALONE_TRADEOFF_ONLY, SG_CLOSED_LOOP_TRADEOFF_ONLY,
CURRENT=BASELINE_EXACT, V1=TRADEOFF_ONLY, V2=REJECTED (37 violations).
Composition remains NOT_RECOMMENDED and NOT_AUTHORIZED; search and frozen candidate
evaluation remain NOT_AUTHORIZED. CALIBRATION_UNCERTAINTY_PENDING,
INDEPENDENT_CALIBRATION_VALIDATION_PENDING, PIXEL_GEOMETRY_REGISTRATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE, INDEPENDENT_REFERENCE_UNAVAILABLE; sealed reference
NOT_GENERATED; vehicle NOT_READY, REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.
