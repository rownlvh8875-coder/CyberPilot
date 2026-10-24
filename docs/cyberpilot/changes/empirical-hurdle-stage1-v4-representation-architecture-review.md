# Bounded Stage1 V4 representation architecture review

지금까지는 같은 Stage1 점수를 어디에서 자를지 바꿨다.
하지만 같은 상태 안에서는 threshold를 아무리 바꿔도
샘플의 순서 자체는 바뀌지 않는다.

이번 검토는 기존 입력정보를 그대로 사용하면서도
MOVE와 STATIC의 순위를 새롭게 만들 수 있는
가장 작은 모델 구조를 찾는다. 실제 모델은 아직 학습하지 않는다.

검토한 family와 명시된 선택 규칙 안에서는 기존 입력 전체를 두 context별
logistic head에 연결하는 구조를 선택했다. 이것이 가능한 모든 모델 중
유일한 최소 모델이라는 뜻은 아니다. 실제 성능 향상도 입증하지 않았다.

## Identity and purpose

- Area: Cyber Validation / offline AutoTune research.
- Repository: https://github.com/rownlvh8875-coder/CyberPilot
- Branch: feature/cyber-autotune; locked baseline:
  da23b158fa2ff6eecf1ca8d33ae5e2190fcba078.
- Status: architecture design frozen; fitting policy NOT_FROZEN.
- No private arrays, fitted weights, threshold search, CV, DEVELOPMENT scoring,
  actual rollout, HOLDOUT, pooled refit, controller or vehicle operations.
- Additive math witnesses, tests, producer, fourteen sealed JSON records and
  this change record. No historical evidence or executor changed.
- Upstream layout, submodule gitlinks, licenses and existing dependencies remain
  unchanged. Existing project code is reused by static reference; no external
  model/code adaptation or new package is introduced.

## Evidence and why thresholds reached a project limit

V1/V2/V3 retain the same scalar Stage1 scores. V1 emphasizes balanced accuracy;
V2 projected task exact-hit; V3 adds the immutable V1 TRAIN TP floor.
All historical selections remain NO_ADMISSIBLE and failed closed.
V2 suppressed more than 95% of MOVE in all 32 jobs; restoring coverage in V3
worsened exact-hit in all 31 comparable jobs. This supports an empirical project
priority closure of the global fixed-score threshold family, not a proof that
every possible threshold or objective must fail.

The previous two-context policy review remains INCONCLUSIVE and its track is
not retroactively closed here. Its public six-condition signal supports this
separately authorized representation review. Exact joint two-threshold fitting
remains Cartesian in the worst case. Representation review does not solve that
optimizer or silently adopt separable threshold fitting.

Public evidence is locked by both file SHA256 and sealed receipt, and six
feature/solver/state source files by SHA256. The producer
[build_hurdle_v4_representation_review.py](../../../tools/cyberpilot/build_hurdle_v4_representation_review.py)
rejects drift as STAGE1_REPRESENTATION_REVIEW_INPUT_CONFLICT.
Input identities are in
[representation-review-inputs](empirical-hurdle-stage1-v4-representation-review-inputs.json).

## Original references and exact causal feature trace

These symbols are inspected, not executed on private input:

1. [Hurdle math](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py),
   parameters/anchors/features delegate to S2-RI; normalizer, transform alias,
   newton and fit_stage1 define the existing numerical fit.
2. [S2-RI math](../../../openpilot/tools/cyber_autotune/empirical_s2_ri_fit_cv_math.py),
   features constructs the exact raw vector; anchors sets history/horizon
   eligibility; transform applies TRAIN normalization.
3. [Hurdle data](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_data.py),
   load_route maps tick/command/speed and continuity; design targets k+1.
4. [Causal reader](../../../openpilot/tools/cyber_autotune/empirical_causal_dataset_reader.py),
   numeric reads carOutput.actuatorsOutput.torque.
5. [Causal source proof](../../../openpilot/tools/cyber_autotune/empirical_causal_dataset_execution.py),
   source_proof traces SAS11.SAS_Angle and source-native rate code.
6. [Established state contract](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_state_contract.py),
   observed_context and ProjectedContext encode observed initialization,
   projected recursive updates and invalidation across boundaries.

For a decision at tick k targeting k+1:

`x = [1, command[k-d-L+1..k-d], tick[k-L+1..k]-tick[k-L..k-1], tick[k], vEgo[k]]`.

Both histories run oldest to newest. P=2L+3 includes intercept; the last
increment is zero-based column 2L=P-3. Features are float64, C-order.
The source anchor R=max(d+L,L+1) provides the predecessor even for L=1.
No rows, histories or eligibility rules change.

Command means logged post-CarController normalized command, not proven physical
EPS applied torque or an actuation acknowledgment. The angle source is
SAS11.SAS_Angle. Delta means source-grid tick change, not physical EPS movement.
steeringRateDeg remains SOURCE_NATIVE_RATE_CODE_ONLY /
RATE_SOURCE_CONTRACT_PARTIAL. No rate dependency is added.

Existing Stage1 uses sigmoid(beta dot transformed x).
TRAIN mean/std with ddof=0 drops empirical constant columns except intercept.
Effective indices retain ascending order. Actual effective P may be smaller
than nominal P and is not measured in this review.

## Exact structural parameter counts

Each row applies separately to all d=0,5,10,20 structures, giving sixteen
candidates. The JSON parameter table lists every candidate ID individually.

| L | Current nominal P | Dual nominal 2P | Dual generic identifiable upper | New generic directions vs global P | Full degree-2 total | New quadratic products |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 10 | 9 | 4 | 15 | 10 |
| 5 | 13 | 26 | 25 | 12 | 91 | 78 |
| 15 | 33 | 66 | 65 | 32 | 561 | 528 |
| 45 | 93 | 186 | 185 | 92 | 4371 | 4278 |

The static head always has delta_prev=0. Its last-increment column is therefore
zero. In [x,zx], delta_prev=z*delta_prev duplicates a column.
A shared normalized last increment q=(delta-mu)/s is constant in STATIC:
q-zq+(mu/s)(1-z)=0. Normalization does not remove this structural dependence.

Thus 2P is the stored nominal coefficient count, not a guaranteed identifiable
fit dimension. Actual rank is r_static+r_move, unknown until separately
authorized fitting preflight. No particular column drop, gauge or normalization
has been selected here.

Full quadratic uses q=P-1 nonintercept inputs, q(q+1)/2 unique square/cross
products and total M=P(P+1)/2. Intercept products are excluded as duplicate linear
terms. Dense design uses 8NM bytes; Hessian 8M² bytes; Newton update costs
O(NM²+M³). At L=45, M=4371 and Hessian alone uses 152845128 bytes approximately
146 MiB; the exact byte count is recorded in the parameter artifact.

Dual inference selects one head: one P-element dot product and sigmoid,
O(P). Nominal coefficient payload is 80/208/528/1488 bytes respectively,
excluding normalizer/metadata. Independent context designs can total 8NP bytes
without allocating a zero-padded N×2P matrix; Newton work is O(NP²+P³).
These are static estimates, not vehicle benchmarks.

## Equivalence and candidate families

| Option | Representation result | Review result |
|---|---|---|
| A state intercept on old logit | Within-state ordering unchanged; two-threshold reparameterization | Negative control excluded |
| B state affine old score | Positive slope preserves order; zero collapses; negative reverses without evidence of usefulness | Positive variant excluded; negative-slope justification unresolved |
| C full binary context × existing x logistic | Can change within-state ordering with all existing features | Selected minimum among reviewed families |
| D full degree-2 logistic | Can change ordering; all pairs/squares introduce general curvature | Eligible conceptual comparator, more assumptions and parameters |
| E selected interactions | All state×x equals C; a smaller subset requires unsupported term choice | Not independently specified eligible minimum |
| F small MLP | Can change ordering/nonlinear interactions | Width, activation and fitting choices unresolved |
| G state-conditioned MLP | F plus context concatenation/dual-head choice | Additional unresolved freedoms |
| H tree/boosted tree | Can reorder but needs depth/leaf/split/tree-count contracts | Non-minimal unspecified family; no dependency added |

For real arithmetic, sigmoid(eta+b_z)>tau iff
eta>logit(tau)-b_z for 0<tau<1. Global/per-state nondecreasing calibration preserves
or coarsens within-state order. Binary64 sigmoid saturation can create ties;
these equivalence claims do not assert byte equality of arbitrary implementations.

C's deterministic witness uses command c=−1,+1 in both contexts, logits c in
STATIC and −c in MOVE. Command contrast is +2 versus −2. One global affine
feature model has the same command contrast in both states and cannot represent
this function. C is therefore more than just refitting the old global linear
coefficients or using two cutoffs on its fixed score.

Quadratic c² and illustrative two-unit ReLU(c)+ReLU(−c) supply additional
ordering witnesses. Their synthetic coefficients are mathematical examples,
never trained weights. The B eligibility control is explicitly the positive-slope subfamily. A negative
slope fully reverses the old scalar ordering; that mathematical variant is
reviewed, but arbitrary reversal is not supported as useful new representation
evidence. Its possibility is not declared impossible.

A one-unit ReLU score is itself nonlinear; its threshold
classifiers are halfspaces or constants. It is not falsely excluded as a
linear score class. Neural options instead lose eligibility/minimality through
unsupported architectural/training choices.

For hidden width H and nonintercept input count P−1, MLP coefficients total
H(P+1)+1; concatenating z gives H(P+2)+1; independent dual MLP heads give
2[H(P+1)+1]. No H/activation is chosen. Initialization, optimizer, regularization,
convergence, artifact format and export parity all need separate contracts.

## Selected architecture and minimality

**HURDLE_STAGE1_CONTEXT_CONDITIONAL_LOGISTIC_V4**

`eta=(1-z)*dot(w_static,x)+z*dot(w_move,x); p_move=sigmoid(eta)`.

Equivalently w_base=w_static, w_delta=w_move−w_static and
eta=dot(w_base,x)+z*dot(w_delta,x). This is a function-class identity, not a
claim of byte-identical numerical fitting under reparameterization.

Selection applies the user's lexicographic rule to fully specified eligible
families. C adds one empirically supported context interaction to all x without
choosing terms, width, depth or new sensor semantics. D assumes unrestricted
pairwise curvature without specific evidence; even if their assumption priority
were tied, C has fewer generic coefficients for every current P.
The rule does not use expected performance, opaque weighted scores or candidate
ID tie-breaking. A tied minimum returns INCONCLUSIVE.

C adds one externally derived binary context bit and no recurrent hidden state.
It introduces future context-specific coefficients, while Stage2 stays unchanged.
It is not a fixed old score plus two thresholds. Architecture is frozen;
normalization, identifiable basis, regularization, solver/stopping, support,
threshold objective/domain/equality/tie order remain FITTING_POLICY_UNRESOLVED.

## Causality, boundaries and failure behavior

Compute raw z before normalization:

- TRAIN/one-step: z[k]=1[tick[k]−tick[k−1] != 0], using observed admitted history.
- Rollout start: z[0]=1[observed_tick[0]−observed_tick[−1] != 0].
- Recursive h>=1: z[h]=1[projected_tick[h]−projected_tick[h−1] != 0].

Here 0 and −1 denote relative times at the anchor, not array indices.
An oldest-to-newest observed history array uses history[-1]−history[-2].
A MOVE gate followed by half-even projected hold gives next z=0.
Gate state is not movement context. No future measured truth can update context. Future authorized TRAIN fitting
may use target y=1[tick[k+1]−tick[k]!=0] as a supervised label only; DEV and
rollout future measured truth remain scoring-only, never causal covariates.
No sign/magnitude states, rate signal or new sensor is added.
Route/segment/causal-run/eligibility/grid breaks invalidate state. The predecessor
and current row must share route/segment/run; source and within-causal-run indices
increase by one, grid time by exactly 10,000,000 ns, both rows are eligible,
and the validated eligible streak increments by one. Missing/nonfinite input fails closed. No padding,
STATIC default, other-head/old-model/threshold fallback is permitted.
The inherited state test relies on explicit boundary invalidation; this review
does not add an integrated runtime continuity detector or executor.

## Training algebra, identifiability and determinism

The logistic negative log-likelihood is convex in its linear coefficients; see
[Boyd–Vandenberghe, Statistical estimation, logistic regression](https://web.stanford.edu/class/ee364a/lectures/stat.pdf), slide 7.5.
The block separation argument below is direct algebra, not an external
performance claim.

For unregularized SUM logistic likelihood and uncoupled head domains, rows
belong to exactly one block. Off-diagonal Hessian blocks are zero in exact
arithmetic. If both argmin sets exist, the joint argmin is the product of
independent head argmins. A global MEAN loss is n0/N L0_mean+n1/N L1_mean;
positive weights preserve mathematical minimizers under those conditions.

This does not guarantee finite or unique estimates. Each head needs an
identifiable basis, sufficient classes/rank and absence of complete/quasi
separation. Synthetic full-rank two-class data with 201 rows per class still
have loss log(1+exp(−a)), whose infimum 0 occurs only as a→infinity.
A finite toy a=32 can already satisfy the old gradient tolerance. No optimizer
was run to produce this witness.

Existing Newton fitting uses zero float64 initialization, unregularized mean
loss, 100 updates, maxabs gradient <=1e−8, Armijo 1e−4 with 2^-j, j=0..20,
and numpy.linalg.solve. Existing class support is 201; none of these constants
are silently adopted as V4 per-head policy.

Global-mean gradient weighting can change stopping: local gradient 2e−8 with
context fraction .1 becomes 2e−9 jointly. Independent versus shared Armijo
steps, parameterization, floating reduction order and penalties can also differ.
Algebraic equivalence therefore does not mean byte-identical optimizer output.
Coupled regularization breaks independence; local mean penalties require
compatible scaling even when penalties are separable.

Shared V1 normalization avoids normalizer refit but leaves a static-head
collinearity. Separate context TRAIN normalization can drop constants and
rescale locally but creates a new normalization policy/model identity.
Raw inputs avoid normalization but retain scaling/conditioning risks.
No choice is made. Deterministic logistic fitting is structurally possible;
the future exact numerical and failure contract is still required.

## Route transfer, onset and remaining uncertainty

Public onset fractions are 55.53% and 54.67%; continuation 44.47% and 45.33%.
Length-one fractions are 63.87% and 64.28% of eligible observed MOVE fragments,
including the public boundary-censoring scope, not complete raw-route run statistics.
Previous-STATIC DEV AUC ranges are Fold A .5361–.5414 and Fold B .5389–.5509;
previous-MOVE .5681–.5949 and .5378–.5593. These describe weak above-chance
signals without an invented quality cutoff or statistical significance claim.

C can modify ranking within the majority onset context and continuation context.
It does not inherently provide route-calibration invariance. Fold A scores
shifted upward and V3 recall was about 57–66%; Fold B shifted downward with
about 7–12% recall. Mean shifts and rank degradation coexist; calibration alone
is not established as their cause. No improvement is predicted for C.

A new representation still needs a decision policy and unchanged downstream
admission. This architecture review cannot resolve Stage2 residual risk.

## Model artifact lifecycle and next increment

Compact logistic coefficients do not require Hugging Face for model size:
**HUGGING_FACE_NOT_REQUIRED_FOR_MODEL_SIZE**. Future private model/normalizer
payloads belong in an authorized E_EXTERNAL_SSD manifest; GitHub publishes only
design, permitted aggregate evidence and receipts. No model artifact was
generated. HF setup/login/repo/upload/download and ONNX export are NOT_RUN.

Next recommended increment: freeze the context-conditional logistic fitting
policy only. Resolve normalization, effective basis/gauge, per-head support,
rank/separation failure, solver/convergence/regularization, threshold policy,
frozen folds/anchors/final gate/selection, E storage authorization, repeatability
and verify-only resume. Actual fit/execution requires separate authority.

## Regression risk and acceptance

Primary risks are accidentally presenting nominal 2P as identifiable rank,
assuming context fit byte equivalence, choosing an unapproved normalizer or
threshold, overstating route robustness, and importing actual execution authority.
Synthetic tests and sealed contracts check these boundaries.
Historical evidence is immutable; rollback is removal of this additive increment.
No controller integration or runtime model consumer exists in this increment.

## Validation method and actual results

Prepared Ubuntu 24.04 WSL, Python 3.12.13 / NumPy 2.5.3, single BLAS/OMP thread;
private-shaped test data are absent. E-backed WSL holds code/build/test outputs.
Legacy D alias tests use an isolated mount namespace with temporary empty D;
global mounts and historical storage guards stay unchanged.

| Check | Command/method | Result |
|---|---|---|
| New algebra/contracts | pytest test_empirical_hurdle_v4_representation_review.py | 31 PASS |
| Prior V3/V4 reviews/executors | pytest prior V3/V4 focused files | 233 PASS |
| Combined empirical | pytest test_empirical*.py | 2032 PASS |
| Full AutoTune + controls | tools/test_runner.py, -j4 | 4891 PASS |
| Lateral replay | two explicit cyber lateral process replay modules | 16 PASS |
| Static/build | Ruff, compileall, 704 policy/change JSON, publication/privacy, diff whitespace, SCons | PASS |
| Independent review | research; numerical/causal/authority | APPROVED after corrections |
| Actual V4 performance / simulation / shadow | Unauthorized | NOT_RUN |

The initial full attempt returned 4890 PASS / 1 WORKER_FAILED in an existing
synthetic worker test while review edits were still changing files in its hashed
source scope. The child suppresses internal exceptions, so the exact internal
reason was not exposed. The same test passed alone without edits, then the full
suite passed 4891/4891 with source_binding identical before/after
(d433c8b064aa418d6a2b665e548420a65908ae8ced5dab6a398ad6d843be8083).
No existing worker, timeout, resource limit, test or gate was changed.

The sealed validation artifact binds counts and environment; GitHub's final
commit-specific workflow supplies CI verification separately. No replay references,
gates, safety limits or tests are weakened.

## Handoff and authority

BOUNDED_STAGE1_REPRESENTATION_ARCHITECTURE_REVIEW_COMPLETE.
STAGE1_V4_REPRESENTATION_ARCHITECTURE_SELECTED.
HURDLE_STAGE1_V4_REPRESENTATION_DESIGN_FROZEN.

Actual V4 fitting/CV/DEVELOPMENT/rollout/performance/selection remain NOT_RUN.
Private numeric opens, model fitting, threshold search, raw/qlog/HOLDOUT opens
are zero. Historical S2-RI/V1/V2/V3 NO_ADMISSIBLE and failed-closed records,
prior policy review INCONCLUSIVE, Stage2 long-horizon risk and global blockers
remain intact. HOLDOUT CLOSED, opening/discovery 0; pooled refit NOT_AUTHORIZED;
vehicle authority NONE, NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED. Architecture freeze authorizes no automatic next step.
