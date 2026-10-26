# Stage1 V4 architecture redesign review

V2는 움직임을 거의 막아서 STATIC exact-hit 손실을 줄였고, V3는 MOVE
coverage를 복구했지만 STATIC exact-hit와 장기 예측이 다시 나빠졌다.
세 실험은 모두 같은 Stage1 점수에 하나의 threshold를 적용했다.
이번에는 threshold 숫자를 다시 조정하지 않고 결정 구조 자체를 검토했다.
새 모델을 학습하거나 V4 성능을 측정하지 않았다.

**결론: 기존 global single-threshold 계열은 현재 프로젝트의 연구 우선순위에서
종료한다. V4 architecture 선택은 `V4_ARCHITECTURE_REDESIGN_INCONCLUSIVE`다.**
관측된 직전 source-grid 변화 상태에 따라 두 threshold를 쓰는 구조는 가장 작은
명확한 구조변경 후보다. 그러나 정확한 대규모 fitting 방법과 두 파라미터의
선택 계약이 아직 해결되지 않았다. 이를 해결된 것으로 가정해 설계를 동결하지 않았다.
따라서 V4 design contract와 fitting policy는 생성하지 않았다.

## Context, scope and evidence lock

- Baseline: `b7e91e57c3d19be827c8757d9803e4744ddcf4a9`, branch `feature/cyber-autotune`.
- Startup: fetch, ancestor, local/origin equality, clean worktree/index and exact-HEAD CI success verified.
- [Architecture inputs](empirical-hurdle-stage1-v4-architecture-inputs.json) binds 161 historical public JSON files by file SHA and sealed receipt SHA.
- All existing V1/V2/V3 numerical evidence, policies, models and tests remain unchanged.
- No new V4 fitting, threshold evaluation, DEVELOPMENT scoring, rollout, candidate ranking or selection occurred.
- Storage remains verified E external SSD. No migration, source reconstruction or source cleanup occurred.

The public receipts reconcile all historical `NO_ADMISSIBLE` verdicts. V2's
extreme MOVE suppression is a **32/32 historical-job** fact. V3 has **31 evaluated
jobs and one TRAIN no-feasible job**. Its 31 comparable jobs improve missed-MOVE
versus V2 and worsen exact-hit, each 31/31. Fold A and B both pass 0/16 complete gates.
The closed-gate failure count includes the unevaluated job; this is never described
as 32 numerically evaluated failures.

| Frozen clause failures | V1 /32 | V2 /32 | V3 closed /32 (evaluated /31) |
|---|---:|---:|---:|
| One-step exact-hit | 32 | 18 | 32 (31) |
| One-step within-one-tick | 8 | 10 | 8 (7) |
| OVERALL 200 RMSE / MAE / p95 | 21 / 22 / 18 | 5 / 5 / 1 | 21 / 22 / 19 (20 / 21 / 18) |
| PATH_MOVED 200 RMSE / MAE / p95 | 21 / 22 / 17 | 5 / 5 / 0 | 21 / 22 / 18 (20 / 21 / 17) |

## Single-threshold family closure

`SINGLE_GLOBAL_THRESHOLD_OVER_FIXED_STAGE1_SCORE` means the same candidate/fold
Stage1 scalar probability, one TRAIN-selected scalar cutoff and strict `score > cutoff`.
V1 maximizes balanced accuracy; V2 uses task-aware exact-hit with MOVE and overall-RMSE
protection; V3 adds the immutable V1 TRAIN TP floor to V2. Models, normalizers,
features, structural candidates, folds, projection, final gate and selection are shared.

[Family review](empirical-hurdle-stage1-fixed-threshold-family-review.json) records
`GLOBAL_SINGLE_THRESHOLD_FAMILY_RETROSPECTIVELY_EXHAUSTED`: empirical project policy
closure for this dataset, fixed score, Hurdle composition and frozen gate. Three
substantially different policies all failed admission and V2/V3 exposed opposite
STATIC/coverage consequences. This supports ending further objective tweaking as
the current research priority. It proves neither that every possible cutoff fails
nor that all future Stage1 models or threshold policies are impossible.

## Equivalence and equality semantics

For strictly increasing `f`, `f(p) > c` is an upper cut of the original ordering.
When an inverse exists at `c`, the cut is `p > f_inverse(c)`. Positive-slope Platt
and positive-temperature transformations with one global cutoff add no contextual
boundary. Reversing the ordering with a decreasing transformation is a different case.

On a **fixed finite score support**, any nondecreasing mapping (including isotonic
flats or frozen global ECDF ranks) rejects a prefix of distinct scores. If the
rejected prefix is nonempty, its largest score is a strict original-score cutoff.
Tied original scores cannot split. Flats can remove available cuts; they do not
create state-dependent ones. A transformed value exactly at the cutoff is STATIC.
No epsilon, probability rounding or tie splitting is permitted.

Two qualifications prevent an overbroad proof: an all-MOVE rule including score
zero needs a negative original cutoff, absent from the historical `[0,1]` candidate
domain. Also a weak monotone discontinuity on a continuum can yield `p >= a`;
it need not equal `p > a` over that entire continuum. Finite-support equivalence
does not establish identical extrapolation on future score values. These details
do not make global calibration a new context-aware architecture.

With two causal states, within-state increasing calibration and one common cutoff
produce two original-score cutoffs, exactly Option A's decision family on its
representable domain. Fixed original logit plus a binary-state intercept and a
positive slope has the same property. Extra calibration parameters can therefore
be redundant decision degrees of freedom.

## Onset, continuation and short fragments

The existing audited `HRI_D00_L01` population is used once per route, without
pooling candidate populations. Route identifiers below are opaque receipt prefixes;
`962f…` is Fold A DEVELOPMENT and `7ae1…` is Fold B DEVELOPMENT.

| Stored route population | 962f… | 7ae1… |
|---|---:|---:|
| True MOVE count | 43,488 | 48,231 |
| MOVE onset count / share | 23,776 / 54.6726% | 26,782 / 55.5286% |
| MOVE continuation count / share | 19,712 / 45.3274% | 21,449 / 44.4714% |
| P(MOVE given previous STATIC) | 9.2452% | 9.2804% |
| P(MOVE given previous MOVE) | 45.4204% | 44.3592% |
| MOVE fragments | 24,660 | 27,616 |
| Length-one fragments / share | 15,851 / 64.2782% | 17,638 / 63.8688% |
| Boundary-censored length-one fragments | 1,986 | 2,441 |
| Uncensored length-one fragments | 13,865 | 15,197 |

The singleton counts were absent from the existing public summaries. A minimal
read-only supplement opened only 12 unique stored V1 truth/continuity arrays
referenced by V2/V3, per independent audit run. The authoritative two runs used
24 decodes; an earlier two-run diagnostic also used 24, so this task made 48
numeric-array decodes in total. The earlier aggregate receipt is preserved.
Manifest, receipt, compressed, decoded-NPY, array-content, dtype, shape and C-order
identities were checked. Fifteen unique opened source members, including metadata,
were unchanged before/after. Two aggregate runs matched byte-exactly and their
separate sealed receipts are published in the
[singleton audit](empirical-hurdle-stage1-v4-singleton-audit.json). No score/model
arrays, raw logs, qlogs, causal/derived stores or HOLDOUT were opened. Only small
aggregate receipts were persisted to E; no original arrays were duplicated.

These are **eligible observed fragments**, with continuity breaks and boundary
censoring, not complete raw-route runs. A length-one fragment at a boundary may
be part of a longer unobserved run. The previous public median=1, p95=4 evidence
has the same limitation. Persistence is real in these observed populations;
hysteresis performance is unmeasured. The majority onset share means continuation
benefit alone cannot be assumed to solve Stage1 failure.

## State-conditional ranking and route transfer

Existing onset AUC compares onset positives against **all STATIC** negatives;
continuation AUC likewise uses all STATIC negatives. Neither is the state-specific
operating population. The relevant conditional comparisons instead use only
`previous_static` or `previous_move` rows. All TRAIN/DEV ranges and score aggregates
are bound in [support](empirical-hurdle-stage1-v4-onset-continuation-support.json)
and [route transfer](empirical-hurdle-stage1-v4-route-transfer-analysis.json).

| DEVELOPMENT conditional AUC | Fold A | Fold B |
|---|---:|---:|
| Previous STATIC: STATIC vs onset | 0.536115–0.541400 | 0.538935–0.550868 |
| Previous MOVE: STATIC vs continuation | 0.568068–0.594901 | 0.537838–0.559279 |

Overall DEV AUC is above chance in 32/32 and below TRAIN in 32/32; the predeclared
rank-collapse trigger was not met. Ranking remains weak, rather than validated
good or random. Conditional state representation is supported as a question,
not as a proven gain. The base model already contains prior signed increments;
zero/nonzero state is a non-affine representation of existing information, not
a new measurement or proof of incremental information conditional on the score.

V3 TRAIN reference recall ranges are 37.0084–54.3385% in Fold A and
16.3608–23.6421% in Fold B. Actual finalized V3 TRAIN recall matches these ranges.
DEV recall is 57.1627–65.5974% (15 scored jobs) and 7.3977–12.0832% (16), respectively.
Per-job DEV minus reference recall is +11.2589 to +23.7106 percentage points in A
and −12.3039 to −8.9631 points in B. The unmatched job stays null, not zero.

The mean score shifts upward in A (+0.02941 to +0.03545 overall) and downward
in B (−0.01903 to −0.01485), while AUC declines in both. STATIC and MOVE class
means and calibration biases are reported independently. Different TRAIN reference
recalls and opposite score shifts coexist with the DEV recall asymmetry; these
are descriptive facts, not an identified causal explanation or evidence that
calibration alone will resolve the failures.

## Architecture options and decision

| Option | New boundary and state | Effective new decision parameters | Decision |
|---|---|---|---|
| A: previous observed-state two thresholds | One causal source-grid state bit; different cut per state | Two cutoffs; +1 relative to a global cutoff | Smallest clear structural candidate, fitting readiness unresolved |
| B: score/state calibration | Global monotone form remains one cut; monotone per-state form is A | Two effective cutoffs in binary-state monotone form; raw model parameters may be redundant | No distinct smaller family established |
| C: explicit temporal logistic | Binary state is nonlinear representation of existing increments; refitting can change rankings | Depends on frozen weight/interaction choice | Fixed-score state-intercept form is A; broader model not justified as minimum |
| D: bounded nonlinear classifier | Can change within-state ranking | Unspecified until a justified family/terms are chosen | No supported minimum nonlinear architecture to freeze |
| E: online unlabeled adaptive gate | Causal score-distribution state | Unresolved window/target/reset/update choices | Unlabeled score shift does not identify conditional label calibration |
| F: predicted-state hysteresis | Previous predicted gate bit, distinct from observed/projected movement | Two cutoffs, plus state update/reset semantics | Observed persistence does not validate gate feedback; onset and sticky errors remain |

Option A can decide differently at equal score in different observed states and
therefore escapes the closed global family. No evidence requires its MOVE-context
cutoff to be lower; imposing that ordering would be a further design choice.
Option F is not A: a predicted MOVE gate can project a held tick, and a previous
gate error can feed back through future decisions. Observed truth persistence
does not establish persistence of the predicted gate.

The supplied twelve-part lexicographic rule is machine-readable. Non-equivalence,
causality, TRAIN-only fitting, direct failure relevance, empirical input support
and feasible bounded exact fitting are eligibility requirements, not weighted
scores that complexity can compensate for. Unknown requirements fail eligibility.
Only a unique eligible lexicographic minimum may be selected; unresolved ties
return INCONCLUSIVE without an arbitrary ID tie-break. Currently no option
satisfies all requirements. This is an architecture-review outcome, not a ranking
or selection of empirical candidate structures.

## Why exact fitting is unresolved

For A, the two context supports generate a Cartesian domain of size
`T_STATIC * T_MOVE`, potentially billions of pairs. Integer exact-hit, projected
STATIC false movement, within-one-tick and TP counts separate across contexts.
This does **not** establish separability of the frozen continuous metrics:

1. Original-row-order NumPy float64 reductions are not equal to adding two
   context totals. The existing bounded engine uses `OrderedSum` to preserve
   the reduction structure. Even positive SSE terms can differ under regrouping.
2. Pooled p95 is the exact NumPy-linear interpolation of adjacent pooled order
   statistics. Per-context p95 values/support do not determine pooled p95. A
   single exceedance-count condition is generally insufficient for interpolation.
3. Feasibility need not be monotonic in either cutoff, so binary-searching an
   assumed feasible interval or using uncertified pruning is invalid.
4. A total tie order for two thresholds and the exact TRAIN objective/constraints
   must be preregistered. V3's scalar `MAX_THRESHOLD` has no unique automatic
   extension to a pair. Neither threshold order nor inherited TP floor is assumed.

A certifying rectangle branch-and-bound algorithm is a **future research
possibility**: exact integer objective bounds, conservative bounds preserving
original-order floating semantics, exact pooled order-statistic bounds and
canonical leaf checks. A selected pair could be returned only after all competitors
are safely excluded or dominated. Checking just the winning pair cannot prove
optimality if pruning was approximate. A resource cap must return INCONCLUSIVE,
never a best-so-far pair or NO_FEASIBLE. Worst-case search can remain Cartesian;
there is no demonstrated practically bounded exact fitter yet. This is a gap,
not a proof that an efficient algorithm is impossible.

A separately fitted objective in each context could avoid joint search. Choosing
that objective would be an additional policy decision; it is not equivalent to
optimizing the pooled integrated task metrics. The review neither mandates V3's
fitting objective for V4 nor silently replaces it with a convenient separable
one. This unresolved choice is part of the INCONCLUSIVE outcome.

## Causality and future requirements

For any future A-like design, define the target transition index explicitly:
the decision for `delta[k]` may use `delta[k-1]`, the already observed source-grid
tick increment, never the current/future target delta. At one-step anchors use
the same continuity-qualified stored history. No route, segment, causal-run,
eligibility break or missing predecessor may silently initialize to STATIC.

Recursive rollout is a separate concern: initialize from observed history, then
update context from **projected tick increments**. Using subsequent measured
deltas would leak future truth. This changes the state distribution and requires
its own frozen contract and later empirical validation. No rollout was generated
here. No hysteresis, debounce, new window or new rate signal has been selected.

`delta_tick` is a source-grid change, not physical EPS movement. Logged command
is post-CarController normalized command, not physical applied torque.
`steeringRateDeg` remains `SOURCE_NATIVE_RATE_CODE_ONLY` with
`RATE_SOURCE_CONTRACT_PARTIAL`; it cannot supply signed physical rate semantics.

The [future requirements](empirical-hurdle-stage1-v4-future-fitting-requirements.json)
request a separate **synthetic-only exact fitting feasibility and causal-state
contract review**. If it establishes eligibility, return to architecture selection
before freezing a fitting policy. Any new B/C/D fitted model requires a separate
artifact lifecycle and registry review; explain Hugging Face usage to the beginner
user at that authorized stage. No HF setup, repository, download, upload or weights
were created here. Current Stage1, Stage2 and normalizers remain unchanged; no
new state or fitted/free parameters are committed to an executable V4 architecture.

## Work plan and verification

The writing-plans workflow is applied to this review deliverable only:
lock public inputs → supplement the single missing fragment statistic → analyze
equivalence and six options → record eligible/inconclusive outcome → synthetic
contract tests → two independent reviews → historical/full validation → commit,
push and exact-HEAD CI. It contains no future policy implementation or experiment.

New code is limited to read-only evidence/fragment checks and an aggregate-only
publication builder. Synthetic witnesses cover monotone strict/weak maps, ties,
endpoint/decreasing exceptions, different decisions at equal scores in different
states, non-affine binary-state representation, continuity, p95 nonseparability,
float reduction order, unique selection and inconclusive paths. Historical
comparison/identity/denominator and privacy/authority regressions are included.

Validation results and independent review findings are sealed in
[validation](empirical-hurdle-stage1-v4-validation.json). Full AutoTune/controls:
**4,787 PASS**; combined empirical: **1,928 PASS** (+812 subtests); V4 focused:
**29 PASS**; existing V3 focused: **131 PASS** (+187 subtests); lateral replay:
**16 PASS**. Ruff, compileall, 667 JSON files, publication/privacy/authority,
diff whitespace and SCons passed. Two independent read-only reviews completed.
The publication review found missing repeatability validation and unrestricted
aggregate fields; strict schema/two-run receipt validation and adversarial tests
fixed both. Full regression was rerun after those fixes. No historical test or
safety gate was relaxed.

Local synthetic regression masks `/mnt/d` only inside a private user/mount
namespace: migrated Windows junctions otherwise alias the synthetic historical
D fixtures to E. Global mounts and aliases are unchanged, safety alias rejection
is unchanged, and the real-source audit runs in the normal verified E namespace.

## Authority and interpretation

All S2-RI/V1/V2/V3 NO_ADMISSIBLE and MODEL_SELECTION_FAILED_CLOSED records remain
immutable. `STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS` is preserved. Nothing here
establishes a better V4, future admissibility, independent validation or vehicle
readiness. V4 fitting, CV, parameter search, DEV, rollout, performance and selection
are all NOT_RUN. No automatic fitting-policy implementation or model experiment
follows this review.

HOLDOUT remains CLOSED, opening/discovery count 0; future untouched HOLDOUT remains
required. No model is admitted for future HOLDOUT; pooled refit, search and
composition remain unauthorized. Vehicle remains NOT_READY, REAL_VEHICLE_UNVERIFIED,
VEHICLE_ACTIVATION_BLOCKED, with authority NONE.
