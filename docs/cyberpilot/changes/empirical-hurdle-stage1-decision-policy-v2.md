# Hurdle Stage1 decision policy V2 — design only

기존 Hurdle은 실제 MOVE 구간의 RMSE·MAE·p95 보호 조건을 32개 job 모두
통과했지만, 전체 exact-hit에서는 모두 탈락했다. STATIC 구간에서 잃은
exact-hit가 MOVE 구간에서 얻은 exact-hit보다 32개 job 모두 컸다.

이번에는 모델을 더 복잡하게 만들기 전에, MOVE 확률을 어디에서 끊을지
결정하는 threshold의 목적만 바꿨다. V1은 분류 Balanced Accuracy를
최대화했다. V2는 실제 projected tick의 exact-hit 개수를 최대화하되,
MOVE 오차를 악화시키거나 전체 RMSE를 개선하지 못하는 threshold를 먼저
제외하도록 설계했다. 실제 threshold를 계산하거나 모델을 실행한 결과는
아직 없다. 기존 NO_ADMISSIBLE 판정은 유지된다.

## Identity and purpose

- Cyber Validation: HURDLE_STAGE1_DECISION_POLICY_V2_DESIGN.
- Family HURDLE_RI_V1; change_scope THRESHOLD_OBJECTIVE_ONLY.
- Branch feature/cyber-autotune; baseline
  13e1ac7c8b892d3bd61b5e2eab9deba8f4dc08d6.
- Scope: public-only declarative design and synthetic contract tests.
- Status: design frozen; independent review and local validation complete.
- No vehicle applicability or controller integration. No private result store,
  threshold, coefficient, prediction array, full path, raw/qlog or HOLDOUT access.

## Original references and evidence binding

Source: [CyberPilot](https://github.com/rownlvh8875-coder/CyberPilot), exact branch
and baseline above. Existing repository licensing and attribution remain;
no external implementation, dependency, submodule or LFS object was introduced.

The builder pins 23 public inputs by exact file SHA256 and canonical receipt
SHA256. These include V1 design/fitting contracts, fit/CV readiness and selection,
and the attribution readiness, trigger and mechanism summary. The public
references to private manifests are identifiers only, never opened:

- Fit/CV manifest:
  c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6.
- Attribution manifest:
  07345517d3bca95e90962e0566a58e2b756a8aa6f5c658b8b312f02d4961f77d.
- Exact-hit state: HURDLE_EXACT_HIT_STATIC_LOSS_ALL_JOBS.
- Review trigger: STAGE1_GATE_REDESIGN_REVIEW_SUPPORTED.
- Historical verdicts: HURDLE_NO_ADMISSIBLE_CANDIDATE,
  MODEL_SELECTION_FAILED_CLOSED,
  FROZEN_HURDLE_RI_V1_FAILED_RETROSPECTIVE_GATE.

The evidence records exact-hit failures, true-MOVE protection passes,
STATIC_HIT_LOSS > MOVE_HIT_GAIN, and projected false movement in all 32 jobs.
Fold A false-MOVE rate is approximately 0.456–0.557 and missed-MOVE
0.344–0.428; Fold B is approximately 0.0187–0.0306 and 0.879–0.926.
These are distinct transfer directions, not independent validation or a basis
for candidate-specific numerical threshold choices.

## Changes and expected effect

One new public-only Python builder,
empirical_hurdle_decision_policy_v2.py, verifies the fixed input allowlist,
constructs ten sealed contracts, validates the complete bundle and publishes
without overwriting differing files. The matching test module interprets only
synthetic fixtures. The production builder contains no threshold selector,
model predictor, fitter or rollout executor; numerical equations are strings.

Call path: public JSON bytes → byte/receipt/state checks → declarative contracts
→ canonical bundle validation → immutable public JSON. No runtime callers were
added. Every previous tracked file remains unchanged. Rollback means removing
the additive V2 design; no model or control state needs resetting.

Expected future effect is a task-aware threshold decision; improved empirical
performance is a hypothesis, not an outcome of this design increment.

### Unchanged models and structures

Stage1 remains DETERMINISTIC_FLOAT64_UNREGULARIZED_LOGISTIC_NEWTON. Stage2
remains DETERMINISTIC_FLOAT64_MOVE_ONLY_OLS with true-MOVE TRAIN rows only.
The separate TRAIN normalizers, convergence rules, solver tolerances, features,
projection, causal anchors and rate independence are unchanged. No weights,
regularization, calibration, probability transform or new feature is introduced.

Exactly 16 tied structures remain: HRI_D00_L01/L05/L15/L45,
HRI_D05_L01/L05/L15/L45, HRI_D10_L01/L05/L15/L45 and
HRI_D20_L01/L05/L15/L45. Stage1 and Stage2 share d/L. Both original route folds,
the HOLD_LAST comparator, projected-integer-tick recursive steering state and
logged-command/vEgo exogenous rollout at 25/50/100/200 steps remain pinned.
No measured future steering or true MOVE label controls inference.

The unchanged-components artifact binds the exact final acceptance and selection
receipts, copies the 32 clauses in their original order and preserves all
candidate/fold identities. Historical V1 threshold policy and values are not
rewritten.

### TRAIN integrated decision semantics

For each future candidate/fold, candidates remain the sorted union of {0.0,1.0}
and every unique finite TRAIN p_move. MOVE iff p_move > threshold; equality
means STATIC. There is no default 0.5, fixed grid, midpoint or epsilon search.

A predicted STATIC branch holds the current tick exactly and has continuous
delta zero. A predicted MOVE branch uses the fixed Stage2 delta for that
candidate/fold, then rounds binary64(current_tick)+binary64(delta) directly
half-to-even to an integer tick. Predicted MOVE can still project to the same
tick. No minimum movement or soft probability blending is permitted.

Stage2 coefficients cannot change while evaluating thresholds. True labels
serve masks, constraints and diagnostics only. The comparator uses the exact
same ordered TRAIN anchors, delta zero and projected current tick. Canonical
continuous error remains predicted delta minus float64 actual delta, with the
V1 contiguous float64 reduction order and linear-interpolated p95.

### Four feasibility constraints

Every selectable threshold must satisfy all four, using integrated output:

| TRAIN population | Metric | Required comparison to HOLD_LAST |
| --- | --- | --- |
| true MOVE | RMSE | <= |
| true MOVE | MAE | <= |
| true MOVE | p95 | <= |
| ALL | RMSE | < |

Comparisons use finite computed values, without epsilon or a significance
threshold. Overall MAE, p95, within-one-tick and classification metrics add no
threshold feasibility conditions.

MOVE non-worse conditions alone permit an all-STATIC solution. Strict overall
RMSE improvement excludes exact all-STATIC behavior. This conjunction does not
impose a minimum predicted-MOVE fraction or guarantee that nearly-all-STATIC
decisions cannot be feasible; no such additional cutoff is introduced.

An empty feasible set yields
STAGE1_DECISION_POLICY_V2_NO_FEASIBLE_THRESHOLD for that candidate/fold.
There is no V1, Balanced Accuracy, 0.5, nearest-threshold or relaxed-gate fallback.

### Objective and tie-breaks

Within the feasible set, use exactly this lexicographic order:

1. Maximize ALL_PROJECTED_EXACT_HIT_COUNT: projected next tick equals target.
2. Minimize STATIC_PROJECTED_FALSE_MOVE_COUNT: true STATIC and projected tick
   differs from current tick. A gate FP that still projects a hold is excluded.
3. Maximize ALL_WITHIN_ONE_TICK_COUNT: absolute projected-minus-target tick <=1.
4. Maximize the numerical threshold.

Counts are integer-exact on a fixed population; widening integer ticks before
subtraction prevents signed16 overflow. No classification accuracy, unprojected
delta exactness, rounded probability, Balanced Accuracy or extra tie-break is
allowed. Balanced Accuracy and TP/TN/FP/FN, precision, recall, specificity,
false-MOVE and missed-MOVE remain report-only.

### Leakage and publication boundary

Threshold choice is candidate/fold TRAIN-only. DEVELOPMENT, HOLDOUT, pooled A+B,
rollout DEVELOPMENT, future untouched routes, V1 per-candidate attribution
results and V1 DEVELOPMENT metrics cannot enter numerical selection. Attribution
supports this policy's rationale only. Poor DEVELOPMENT results cannot trigger
a second-best or neighboring threshold rescue.

A future actual threshold remains private. Public outputs may contain policy
and selected-threshold receipts, candidate/feasible threshold counts, and TRAIN
aggregate task/confusion metrics. This design has no actual threshold value.

### Final acceptance and selection remain unchanged

Each fold still requires ALL one-step RMSE < HOLD_LAST, MAE/p95 <= HOLD_LAST,
exact-hit/within-one-tick >= HOLD_LAST; integrated true-MOVE RMSE/MAE/p95
non-worse; and both overall and PATH_MOVED RMSE/MAE/p95 non-worse at all four
horizons. Both folds must pass, without pooling or epsilon: 32 clauses per fold.
V1 support and numerical preconditions also remain mandatory, including
fail-closed handling of undefined diagnostics; clause scores alone cannot admit
a candidate.

Only admissible candidates can enter the unchanged ascending selection order:
worst PATH_MOVED rollout RMSE ratio, worst overall rollout RMSE ratio, worst
integrated one-step p95 ratio, total nominal parameter count, L, d, candidate ID.
Neither admission nor candidate selection is executed here.

### Stage2 long-horizon caveat

STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS. Gate-perfect PATH_MOVED SSE improves
in 32/32 jobs at 25 steps. At 50 steps, 28 improve and 4 regress. At 100 steps,
24 improve, 5 regress and 3 have equal SSE. At 200 steps, only 2 jobs have any
gate-perfect PATH_MOVED support, each with one path; both improve and 30 are
empty. At 50 and 100 steps all gate-perfect populations are below 201 anchors.
These are SMALL_SUPPORT_DESCRIPTIVE_ONLY associations, not proof that Stage2 is
validated or that a threshold change resolves long-horizon drift. Stage2
redesign/implementation is not authorized.

## Regression risk and acceptance

Primary risks are objective/projection confusion, TRAIN/DEVELOPMENT leakage,
reversed tie-breaks, hidden acceptance changes, or premature execution authority.
The complete generated bundle is compared canonically, so resealing a modified
contract does not bypass validation. Input drift fails with
HURDLE_STAGE1_DECISION_POLICY_V2_DESIGN_CONFLICT.

Tests cover each feasibility boundary, objective priority, all ties, empty set,
half-even parity, gate-MOVE/projected-hold distinction, leakage and mutation
rejection, immutable publication and an execution/file-access firewall.
Synthetic tests establish contract semantics, not model performance.
Independent review is required before completion. No HOLDOUT inputs are needed.

## Validation method and actual results

Environment: Ubuntu 24.04, Python 3.12.13, NumPy 2.5.3, with
OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. Logs and test temporary files remain
on the D-backed development volume. No private result directories were accessed.

| Check | Command / method | Actual result |
| --- | --- | --- |
| Focused design/synthetic/mutation/firewall | python -m pytest -q openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_decision_policy_v2.py | 33 passed, 18 subtests; independent reviewer rerun 33 passed |
| Combined empirical, including Hurdle and S2-RI history | python -m pytest -q openpilot/tools/cyber_autotune/tests/test_empirical_*.py | 1,661 passed, 582 subtests |
| Full AutoTune and controls | python tools/test_runner.py openpilot/tools/cyber_autotune/tests openpilot/selfdrive/controls/tests -j 1 | Stable-source rerun: 4,520 passed in 1,586.54 s; initial rejection recorded below |
| Lateral replay | python -m unittest -q openpilot.selfdrive.test.process_replay.test_cyber_lateral_card_replay openpilot.selfdrive.test.process_replay.test_cyber_lateral_native_experiment | 16 passed |
| Ruff | ruff check tools/cyberpilot openpilot/tools/cyber_autotune openpilot/selfdrive/controls/lib/cyber_lateral openpilot/selfdrive/controls/lib/cyber_long openpilot/selfdrive/controls/tests/test_cyber_*.py openpilot/selfdrive/test/process_replay/*cyber_lateral*.py | PASS after dictionary-format fixes |
| Syntax | python -m compileall -q openpilot/tools/cyber_autotune tools/cyberpilot | PASS |
| Native build | scons -u -j2 | PASS |
| JSON and receipt chain | strict JSON parse; builder.validate on published bundle | 560 JSONs valid; 10 new artifacts and 23 pinned inputs verified |
| Publication/privacy/authority | python tools/cyberpilot/check_publication.py --base 13e1ac7c8b892d3bd61b5e2eab9deba8f4dc08d6 --json; same check --base origin/main | Both empty finding lists |
| Whitespace/historical preservation | git diff --check; git diff --cached --check; baseline tracked-path diff | PASS; 13 additions, zero historical modifications |
| Independent review | Separate read-only reviewer of source, tests, ten artifacts and this record | No outstanding findings; strengthened file/alias firewall, overflow and objective-distinction tests |
| Exact-HEAD GitHub Actions | Baseline run 38359202558 | Baseline SUCCESS; final commit run is checked by exact HEAD after push |

The first full run recorded one existing bounded A1 worker rejection
(test_worker_repeats_and_rejects_external_input, second subprocess returned
INVALID_OR_FAILED_BOUNDED_A1), with 4,519 other passes. This was not a timeout:
the test took 27.74 seconds against a 90-second subprocess budget. Formatting
edits overlapped that run; the worker binds all AutoTune Python sources and
rejects changes during execution. Its generic public rejection does not expose
the underlying exception, so source-change overlap is the identified plausible
cause, not a recovered exception trace. Both isolated unittest and identical
test-runner reproductions subsequently passed (28.31/28.29 seconds).
The final full run used stable source and no concurrent edits/builds and passed
all 4,520 tests. The earlier worker rejection did not recur.
No historical code, worker limits or assertions were changed.

Design policy receipt:
463ac0c2f34b59b67c1a1d7365c5662d717a49de328cabfd9101f185bff2bf19.
Validation receipt:
c4ae8f8a377578093582a4a60b12e08f1c8bccb95e81e458f3cefc542572e181.
Builder source SHA256:
27a248dd5d97d2f781cb5d147fe4a996ef2b8acc8099dc12a9f010e1eb3b8c6b.

Browser is NOT_APPLICABLE. Actual model fitting, private arrays, new prediction/
rollout, simulation, shadow and vehicle execution are NOT_AUTHORIZED here.
These offline regressions do not establish vehicle readiness or V2 performance.

## Handoff

Final readiness is HURDLE_STAGE1_DECISION_POLICY_V2_DESIGN_FROZEN with the
candidate-set, four feasibility constraints, exact-hit objective and all three
tie-break states frozen. Stage1/Stage2/features/16 structures/folds/rollout/final
acceptance/selection remain unchanged. All actual V2 fitting, threshold
selection, prediction, rollout, CV scoring and candidate selection are NOT_RUN;
actual threshold is NOT_COMPUTED and private access is zero.

The next increment is HURDLE_STAGE1_DECISION_POLICY_V2_EXECUTION_POLICY,
REQUIRES_SEPARATE_AUTHORIZATION. It must decide reuse of byte-identical V1 models
versus clean 32-job refitting, immutable lineage for Stage2 TRAIN predictions,
repeatability/store/resume and V1/V2 comparison before execution. This design
makes none of those choices and does not inspect availability of private data.

Historical NO_ADMISSIBLE/FAILED_CLOSED, retrospective-development limitations,
all rate/source/calibration/reference blockers, HOLDOUT CLOSED/opening_count=0,
NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT, FINAL_POOLED_REFIT_NOT_AUTHORIZED,
SEARCH_NOT_AUTHORIZED and COMPOSITION_NOT_AUTHORIZED remain. Vehicle authority
is NONE: NOT_READY, REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED.
