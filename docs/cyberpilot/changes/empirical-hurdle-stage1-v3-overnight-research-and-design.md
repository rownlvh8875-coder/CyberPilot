# Stage1 V3 overnight research and design

V2는 모든 job의 exact-hit를 개선했지만 실제 MOVE 대부분을 놓쳤고,
두 fold를 모두 통과한 구조는 없었다. 이번 작업은 저장된 증거의 temporal
특성을 분석하고, 모델을 바꾸기 전에 decision policy의 최소 변경을 검토한다.
실제 V3 threshold 선택·prediction·rollout·성능 평가는 이번 작업의 범위 밖이다.

## Identity and purpose

Cyber Validation, research/design only. Repository
https://github.com/rownlvh8875-coder/CyberPilot, branch `feature/cyber-autotune`,
baseline `91b3210d3e7d45a9dc7d6253eeec2f4e36d4a57e`.
No vehicle applicability or execution authority is granted.

## Predeclared implementation plan

1. Verify public V1/V2 receipt chains and historical states. Bind existing public
   evidence by file bytes and canonical receipt. Preserve every historical file.
2. Test and implement a stored-evidence-only temporal audit. Route statistics use
   the structurally predefined D00/L01 one-step anchor populations, one per route,
   without pooling candidates. Previous delta is the stored causal context.
   Run lengths describe eligible observed fragments, not complete raw route runs.
   Split on route, segment, causal run, index discontinuity; label boundary runs
   as censored. History-two statistics require an adjacent stored predecessor.
   Candidate-specific score diagnostics retain each candidate/fold population.
   Empty classes are undefined, never assigned chance AUC. Trigger support uses
   at least 201 positives and 201 negatives in every one of the 32 DEV jobs.
3. Run two independent aggregate-only audits with no prediction, fitting,
   threshold search, source rebuild, or rollout; verify source bytes and resume.
4. Compare A/B/C/D/E using the user's ordered structural selection criteria.
   Independent architecture review precedes final design freeze. Any guarantee
   from TRAIN constraints is explicitly limited to TRAIN; route transfer remains
   an empirical risk. Persistence is already represented in prior-delta features.
5. Add declarative design, fitting and execution contracts plus a synthetic-only
   scaffold. No private V3 runner is enabled by these contracts.
6. Perform independent implementation review, full regression, lateral replay,
   Ruff, syntax/JSON/publication/authority checks and SCons. Publish actual counts
   and limits, commit additive changes, push, verify exact-HEAD CI success.

## Original references

Local immutable Hurdle family/fitting contracts, V1/V2 execution and attribution
modules under `openpilot/tools/cyber_autotune`, and their public receipts are the
only algorithm/evidence references. No external model or control code is adopted.
Existing repository license and attribution remain unchanged. Call path:
stored receipts/arrays → descriptive audit → public design contracts → synthetic
scaffold/tests. No controller or actuator caller is introduced.

## Regression risk and acceptance

Baseline full regression: 4,627; lateral replay: 16. Risks: crossing discontinuous
anchors, treating censored runs as complete, leaking private values, confusing
TRAIN guarantees with DEV performance, or enabling private execution prematurely.
Acceptance requires exact source lineage, two independent reviews, unchanged
historical gate/selection, and no actual V3 private numerical performance run.

## Validation method and actual results

Startup verified local/origin equality, clean tree and baseline exact-HEAD CI
success (run 38410839619). Focused tests: 53 PASS with 82 subtests. Combined
empirical regression: 1,821 PASS with 707 subtests. Lateral replay: 16 PASS.
Ruff, compileall, JSON, publication/privacy/authority checks and SCons passed.
The full AutoTune/controls regression passed all 4,680 tests in 1,639.71 seconds.
This includes the historical Hurdle V1/V2 and S2-RI regressions. The final
validation receipt binds source and contract identities and these check results.
Simulation, shadow, HOLDOUT and vehicle execution: NOT_RUN / NOT_AUTHORIZED.

## Handoff

Option A selected after independent architecture review. V3 PERFORMANCE = NOT_RUN.
HOLDOUT CLOSED, opening/discovery 0; vehicle authority NONE.

## Evidence synthesis and temporal audit

All 104 existing public Hurdle JSON artifacts matched their baseline file bytes
and canonical receipts. The new research-input binding freezes that exact set.
V1 and V2 NO_ADMISSIBLE / MODEL_SELECTION_FAILED_CLOSED remain historical facts.
V2 improved projected exact-hit in 32/32 jobs but still failed that clause in
18/32; true-MOVE protection passed 32/32. Development ranking was above chance
in 32/32 and below TRAIN ranking in 32/32. Missed MOVE exceeded 95% in 32/32.
This is weak retained ranking with transfer degradation; it is neither a
validated good classifier nor evidence of entirely random scores.

The existing public selected-gate TRAIN evidence also shows extreme suppression:
V2 TRAIN recall ranges from 0.0000270 to 0.008584 in FOLD_A and 0.003955 to
0.025332 in FOLD_B. Thus this is already a TRAIN objective consequence, not
only an unseen-route effect. The immutable V1 TRAIN recall reference ranges
from 0.370084 to 0.543385 in FOLD_A and 0.163608 to 0.236421 in FOLD_B.
These historical aggregates motivate a source-derived TRAIN TP floor; they
are not V3 numerical results or a guarantee of DEVELOPMENT recall.

Route statistics below use D00/L01 DEVELOPMENT populations, one per route.
These are eligible stored fragments, not all raw-route samples. Other structural
candidates retain their own exact anchor sets for score diagnostics.

| Count or conditional probability | FOLD_A development route | FOLD_B development route |
| --- | ---: | ---: |
| Anchors | 300,569 | 336,941 |
| STATIC → STATIC | 233,394 | 261,806 |
| STATIC → MOVE | 23,776 | 26,782 |
| MOVE → STATIC | 23,687 | 26,904 |
| MOVE → MOVE | 19,712 | 21,449 |
| P(MOVE given previous STATIC) | 0.0924524634 | 0.0928035816 |
| P(MOVE given previous MOVE) | 0.4542040139 | 0.4435919178 |
| P(MOVE given last two STATIC), adjacent support only | 0.0725311877 | 0.0733867601 |
| P(MOVE given any of last two MOVE), adjacent support only | 0.3950229411 | 0.3903135889 |
| MOVE fragment median / p95 / max steps | 1 / 4 / 66 | 1 / 4 / 47 |
| STATIC fragment median / p95 / max steps | 3 / 30.8 / 493 | 2 / 30 / 393 |
| Eligible contiguous fragments | 12,067 | 18,498 |

Both routes satisfy the predeclared persistence inequality, with every
conditioning support above 201. Boundary-censored run counts are published
separately: MOVE 3,095 / 3,339 and STATIC 12,898 / 18,495.
History-two rows require a stored adjacent predecessor; gaps are never padded.
Persistence is already partly represented by existing prior-delta features.
It is not newly discovered independent input information or evidence about
projected recursive state stability.

| Threshold-free AUC range over 16 structures | FOLD_A | FOLD_B |
| --- | --- | --- |
| TRAIN onset vs STATIC | 0.559645–0.564843 | 0.531865–0.535895 |
| DEV onset vs STATIC | 0.533730–0.538227 | 0.535569–0.547192 |
| TRAIN continuation vs STATIC | 0.620648–0.637436 | 0.597815–0.611353 |
| DEV continuation vs STATIC | 0.594794–0.622294 | 0.558381–0.585306 |

All 32 DEV onset and continuation comparisons have both class supports at least
201 and exact AUC above 0.5. Class-conditional means/AUC within prior STATIC and
prior MOVE populations are also published. AUC uses integer pair numerators,
ties receive half credit, and no threshold is selected by this audit.

Two independent stored-evidence audits produced identical job receipts and
logical manifests. Source loading and numerical audit functions were trapped
during verify-only resume. 512 manifest-bound members were read and rehashed
unchanged. This is an opened-member/manifest integrity claim, not a claim that
unopened raw, qlog, HOLDOUT or entire disks were compared. Output is small
aggregate JSON on D (587,818 bytes); no source arrays were duplicated. The final
reviewed audit manifest is
`7a9055a90ea44ee83b40ee0c6e217d2a121479ef8ce3e152a65455a13492892e`,
with repeatability receipt
`e7b32f08e9d66f0d147cdc8a420878958375ef1931393d5f3128b55e99cee52d`.
An initial serialization failure, an interrupted attempt and a completed
pre-review run remain separate superseded outputs, not authoritative inputs.

## Design alternatives and decision

| Option | Decision and structural reason |
| --- | --- |
| A: recall-constrained fixed threshold | Selected: exact V1 TRAIN TP lower bound directly protects actual MOVE coverage. |
| B: prevalence-constrained fixed threshold | Predicted MOVE count can be satisfied entirely by false positives; no true-MOVE recall bound. |
| C: causal two-state hysteresis | Persistence makes it review-eligible, but closed entry can remain all-STATIC. Adds a second threshold, state/reset and recursive feedback. |
| D: causal rank-adaptive gate | Requires new window, initialization, update and tie semantics without a uniquely justified choice. |
| E: new Stage1 classifier | Predeclared rank-collapse trigger is not met and a smaller decision-only option exists. |

A and B both can use one fitted threshold and zero new tunable scalar constants.
A wins at the true-MOVE suppression criterion, not by claiming fewer scalar
parameters than B. No option was tried on actual V3 private performance data.

Selected identity: HURDLE_STAGE1_DECISION_POLICY_V3, family
V1_TRAIN_TP_CONSTRAINED_FIXED_THRESHOLD, change scope DECISION_POLICY_ONLY.

The new exact feasibility clause is TP_V3_TRAIN >= TP_V1_TRAIN. The reference is
the immutable V1 confusion receipt for the same candidate/fold, models, TRAIN
anchor SHA and class counts. It does not use the historical numerical threshold
or any DEVELOPMENT result. V1 TRAIN recall ranges are 0.370084–0.543385 (A) and
0.163608–0.236421 (B). All references satisfy integer guard 20*TP>P, the
complement of the already declared missed-MOVE>95% state. This is a provenance
check, not an invented recall percentage to optimize.

Retained feasibility:

1. True-MOVE RMSE <= HOLD_LAST.
2. True-MOVE MAE <= HOLD_LAST.
3. True-MOVE p95 <= HOLD_LAST.
4. ALL RMSE < HOLD_LAST.

Among thresholds satisfying these four clauses and the new TP floor, retain the
V2 lexicographic order: maximize projected exact-hit integer count; minimize
STATIC projected false-move count; maximize within-one-tick integer count;
maximize numerical threshold. Balanced Accuracy remains report-only.
Candidates remain sorted unique TRAIN probabilities union {0,1}; MOVE iff
p_move > threshold. No epsilon, midpoint, default, fallback, or row dropping.
Empty feasibility fails closed. Missing/invalid reference fails closed.

**The construction guarantee is TRAIN-only, return-or-fail.** No fixed TRAIN
threshold guarantees DEVELOPMENT recall under arbitrary score shifts. This
design limits the decision objective's sacrifice of TRAIN true positives; it
does not calibrate cross-route scores. All-MOVE is not separately forbidden and
there is no claim that existing constraints always exclude it. The unchanged
DEVELOPMENT gate remains the acceptance authority.

## Fitting and execution policy

Stage1 logistic model, Stage2 MOVE-only OLS, both normalizers, features, 16
structures, route folds, projection, rollout, 32 clauses per fold and candidate
selection remain unchanged. No model is refitted. Stage2 long-horizon residual
risk remains; sparse gate-perfect evidence does not authorize redesign.

Future authorized execution must reuse exact successful V1 model bytes. TRAIN
p_move is prediction-only replay and must match saved V1 bytes when present.
Stage2 must infer on ALL TRAIN anchors, including STATIC truth rows, using its
existing MOVE-only normalizer. Truth labels define feasibility masks, never
inference branches. The V3 parameter receipt must finalize before DEVELOPMENT.
Rollout uses projected integer state and projected deltas; future observed
states are scoring-only. Commands/vEgo are the unchanged logged exogenous inputs.

Storage remains D-only, source references replace duplicate V1 model/truth/
HOLD_LAST payloads. V3-specific arrays use C-order NPY and deterministic gzip
level 1, mtime zero, empty filename, with compressed/decoded/content hashes.
Run 2 independently repeats computation. Scratch deletion requires complete
exact comparison and durable verification receipts; this scaffold never deletes
files. Resume must read only its own persisted output and reproduce identity
without computation.

## Scaffold and remaining work

The implemented evaluator is a synthetic, exhaustive canonical reference. It
does not load private data. Private execution always raises, even when passed an
authorization-shaped object. The scaffold contains exact metrics, the additional
TP constraint, immutable gate binding, identity checks, deterministic compression,
an aggregate manifest writer and verify-only resume primitives.

A bounded large-population sweep and the authorized private orchestrator remain
future implementation work. Their optimization must match the frozen canonical
semantics, including ordered binary64 reductions and exact linear p95. This is
an implementation prerequisite, not an unfrozen architectural parameter.
There is one fitted private threshold per candidate/fold (32 total), one
source-derived TP reference per fold, and no new tunable hyperparameter/window/
hysteresis gap/debounce. Actual V3 parameter values are NOT_COMPUTED.

Before any future private execution: obtain separate user authorization, bind
then-current HEAD and all policies, verify successful source/model/normalizer/
anchor identities, D output and free-space peak, executor SHA and exact runtime.
Then implement/review the bounded orchestrator and test exact sweep equivalence
before opening numeric inputs. No additional experiment is started by this task.

## Review and validation ledger

Architecture REVIEW 1 approved A with the TRAIN-only guarantee, explicit
transfer risk and no all-MOVE guarantee. It also required stronger resume
schema/count validation; that was added and tested before the authoritative
two-run audit. Independent implementation REVIEW 2 found incomplete resume
validation, an overly broad nested publication projection, missing input tick
bounds and missing exact temporal-publication binding. All four were corrected
with reproducing tests. The complete temporal audit was then independently
rerun twice; review of the final five temporal artifacts and 21 contracts passed.
Existing historical files have not been edited.

Final local verification: 53 focused tests and 82 subtests; 1,821 combined
empirical tests and 707 subtests; 4,680 full AutoTune/controls tests; 16 lateral
replay tests. All passed. SCons, Ruff, compileall, JSON, exact contract/publication
binding and staged whitespace checks passed. Publication audit reported zero
findings. Exact-HEAD remote CI is verified after the final push and reported in
the handoff rather than embedding a self-referential commit identity here.

Next recommendation: separately authorize implementation and review of the
bounded private executor against these frozen policies, then verify source,
environment and D-side capacity before any V3 numerical experiment. No model,
threshold or gate redesign is automatically started.

No V3 private threshold selection, DEVELOPMENT scoring, rollout or model
selection was performed. HOLDOUT CLOSED, opening/discovery 0. Vehicle remains
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED, authority NONE.
