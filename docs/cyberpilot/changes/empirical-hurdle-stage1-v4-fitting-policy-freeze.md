# Hurdle Stage1 context-conditional logistic V4 fitting policy

V4의 모델 구조는 이미 정해졌다.
직전에 조향 tick이 변하지 않은 상황과 변한 상황에 각각 다른 Logistic 판단식을 사용한다.
여기서 tick 변화는 source-grid 변화이며 물리적인 EPS 움직임이나 steering rate를 뜻하지 않는다.

이번 작업은 이 두 모델을 실제로 학습하지 않는다.
대신 어떤 데이터 변환을 쓰고, 어떤 경우 학습을 실패로 볼지,
어떤 최적화 방법과 threshold 규칙을 쓸지 미리 고정한다.
이 규칙을 먼저 정해야 실제 결과를 본 뒤 유리한 방식으로 학습법을 바꾸는 것을 막을 수 있다.

선택은 공유 V1 normalizer, STATIC의 구조적 delta 열 제거,
두 head의 독립적인 unregularized Newton 학습,
새 combined score에 대한 V1 global TRAIN BA threshold다.
학습 전에 rank와 complete/quasi-separation을 별도로 증명해야 한다.
큰 데이터용 certificate 생성기와 실제 private executor는 아직 구현하지 않았다.

## Identity and purpose

- Area: Cyber Validation / AutoTune offline fitting-policy review.
- Repository: https://github.com/rownlvh8875-coder/CyberPilot
- Branch: feature/cyber-autotune.
- Baseline: e722342fdd30fcaff80c6d9f94dd7d3465c8a447.
- Decision: HURDLE_STAGE1_CONTEXT_CONDITIONAL_LOGISTIC_V4_FITTING_POLICY_FROZEN.
- Architecture: already frozen, unchanged.
- Scope: public evidence, static inspection, mathematical rules, synthetic-only
  fitting and threshold tests. No actual private-data fitting or execution.
- No upstream integration, dependency, submodule, license or historical evidence
  changes. Existing project numerical machinery is reused by direct call.

The added math/scaffold module is
[empirical_hurdle_v4_fitting_policy.py](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_fitting_policy.py);
the public artifact producer is
[build_hurdle_v4_fitting_policy.py](../../../tools/cyberpilot/build_hurdle_v4_fitting_policy.py).
Neither provides a private runner. execute_private always rejects before I/O.

## Original references and immutable inputs

The producer pins eighteen public JSON files by file SHA256 and sealed receipt,
and five existing source files by content SHA256. Identity conflict fails as
V4_FITTING_POLICY_INPUT_CONFLICT. The architecture receipt is
01b695d8941298066b61acc341a07f2cbedcd8f1df408754d476744fc3e2a1b8.
The complete lock and 32 ordered historical model/anchor bindings are in
[fitting-policy-inputs](empirical-hurdle-stage1-v4-fitting-policy-inputs.json).

Source trace:

- [Hurdle math](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py):
  normalizer, newton, sigmoid, threshold and fit_stage1 define historical behavior.
- [S2-RI math](../../../openpilot/tools/cyber_autotune/empirical_s2_ri_fit_cv_math.py):
  features and transform define the exact feature vector and affine transform.
- [Gate/selector](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_gates.py):
  fold_gate, selection_key and select remain unchanged.
- [State contract](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_state_contract.py):
  observed_context and ProjectedContext remain unchanged.
- [V3 I/O](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v3_io.py):
  existing private model-content verification is a future implementation pattern,
  not new authority to open its source.

The public successful V1 manifest identity remains
c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6.
Public metadata reconciliation is not private normalizer/content verification.
A future separately authorized executor must verify the actual manifest members,
normalizer/model array-content hashes and all anchors before fitting.

## Architecture, inputs and causal timing

For unchanged d in {0,5,10,20} and L in {1,5,15,45}, P=2L+3:

`x=[1, L command-history terms, L past tick increments, current tick, vEgo]`.

History groups are oldest first, float64 C-order. The latest prior increment
tick[k]-tick[k-1] is raw column 2L=P-3. Derive z from that raw column before
normalization. The logits remain:

`eta=(1-z)*dot(w_static,x)+z*dot(w_move,x)`; `p=sigmoid(eta)`.

Logged command means post-CarController normalized command, not physical EPS
applied torque. Angle source is SAS11.SAS_Angle. steeringRateDeg remains
SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL. No new rate input.

ONE-STEP uses observed tick[k]-tick[k-1]. Rollout begins with observed relative
times 0 and -1, equivalent to history[-1]-history[-2] in an oldest-first array.
After prediction, z[h] uses projected_tick[h]-projected_tick[h-1] only.
A MOVE gate can project hold and yield next z=0.

Predecessor admission requires same route/segment/causal run, source and
within-causal-run indices +1, grid +10,000,000 ns, both eligible and streak +1.
Route, segment, causal-run, eligibility or grid breaks invalidate context.
No padding/default STATIC, future measured context or predicted-gate-as-state.
Future TRAIN target labels are allowed only in separately authorized fitting;
DEV/rollout measured truth remains scoring-only, never causal covariates.

## Shared normalizer and canonical basis

Policy: reuse the byte-identical successful V1 Stage1 TRAIN normalizer for the
same candidate/fold in both heads. No new mean/std, context scaling or DEV fitting.

The pinned public V1 results show effective_columns=nominal_columns=P and
constant_columns=0 for Stage1 in all 32 jobs. Therefore no empirical constant
column was discarded by these actual source normalizers. Future metadata/content
preflight must confirm effective indices arange(P), constant flags all false
and positive nonintercept scales, in addition to receipt/content identity.

For q_j=(x_j-mu_j)/sigma_j, sigma_j>0:

`beta_j=w_j*sigma_j`;
`beta_0=w_0+sum_{j>0} w_j*mu_j`.

This invertible real affine coordinate change preserves each linear-logit
function class. It does not assert bit equality of differently ordered
binary64 expressions.

STATIC has raw delta=0 identically. Its normalized delta is the constant
c_delta=-mu_delta/sigma_delta. Absorb beta_delta*c_delta into its intercept
and remove only that delta column. MOVE retains every V1 effective column.
Intercept remains present; indices stay ascending.

| L | P | STATIC effective columns | MOVE effective columns |
|---|---:|---:|---:|
| 1 | 5 | 4 | 5 |
| 5 | 13 | 12 | 13 |
| 15 | 33 | 32 | 33 |
| 45 | 93 | 92 | 93 |

These counts are structural for the pinned full-effective source, not guarantees
of head rank. Additional context constants/dependencies fail closed; no extra
auto-drop or fitted gauge. A generic synthetic legacy-normalizer example tests
inherited constant-column handling, but does not claim unrestricted off-support
raw-feature equivalence for such a different source.

## Per-head support and exact identifiability

Each head independently requires:

- True MOVE class count >=201.
- True STATIC class count >=201.
- n_rows > effective parameter count.
- Full numerical rank and an exact nonzero row-minor certificate.

201 is the historical support floor, not a new tunable ratio or a claim of
statistical sufficiency.

Numerical rank uses float64 singular values and exactly:

`tol=sigma_max*max(n_rows,n_cols)*np.finfo(np.float64).eps`;
`rank=count(sigma>tol)`; require rank==n_cols.

SVD rank under a numerical tolerance is not an exact mathematical rank proof.
To justify the finite unique real MLE theorem, also verify a nonzero p×p
row minor over exact rational representations of the binary64 matrix entries.
Witness rows certify rank only; every original TRAIN row remains in fitting.
No pseudo-inverse, ridge, empirical column removal or old-model fallback.

The synthetic reference finds the first independent rows by exact elimination.
Large-data minor proposal/verification implementation is a future executor
requirement; it cannot change the frozen rank conditions.

## Complete/quasi separation certificate

Let A=diag(2y-1)X after the frozen head basis. Separation exists when some b
satisfies Ab>=0 everywhere and has a strictly positive margin somewhere.
Complete and quasi separation both fail the unregularized policy.

The mathematical bounded LP is:

`max 1^T A b, subject Ab>=0 and ||b||_1<=1`.

A supplied exact feasible b with positive objective proves separation; it need
not be an optimizer. Zero margins alone do not prove quasi rather than complete
separation. The quasi synthetic fixture also has duplicate inputs with opposite
labels, which prohibit an all-strict separator.

NO_SEPARATION is accepted only with an exact rational certificate:

`lambda_i>=1 for every row; A^T lambda=0`.

This is a scaled strictly-positive Stiemke alternative. For q=lambda-1>=0,
the LP dual is feasible with mu=0 because
`|A^T(q+1)|<=mu`. The primal b=0 is feasible with objective 0, so exact
primal/dual bounds certify optimum 0. Normalizing separator b is a certificate
convention, not a cap on learned logistic coefficients.

Each finite binary64 matrix value is interpreted as its exact integer ratio.
No decimal rounding or epsilon is used. Tiny nonzero residuals are rejected.
Certificates bind exact matrix/label content, shape, row order, basis and source
identities. Raw row witnesses and rational dual vectors belong in future
private artifacts; public records expose only receipt/status/aggregate fields.

The [Saunders–Schneider theorem-of-alternatives paper](https://people.math.wisc.edu/hans/saunders.pdf)
provides primary background; the LP dual calculation above is stated explicitly.
Missing, malformed or unverifiable proof gives
SEPARATION_CERTIFICATE_INCONCLUSIVE and the job fails closed.
Gradient size, coefficient size, Hessian condition and iteration counts are
not separation proofs.

No SciPy or other dependency was added. This increment implements supplied
synthetic proof verification, not a scalable LP/certificate generator.
**Fitting policy FROZEN does not mean private executor READY.**

## Why finite unique MLE, and what is not guaranteed

Under finite inputs and exact full column rank, absence of a nonzero signed
nonnegative direction implies every unit direction has some negative signed
margin. By compactness of the unit sphere, the maximum negative margin has a
positive uniform lower bound. Logistic NLL therefore grows without bound as
coefficient norm grows: the loss is coercive. Its finite-coefficient Hessian
X^T W X/n is positive definite because W has positive entries and X is full
column rank. A finite unique minimizer follows.

This is a real-arithmetic theorem under the frozen preconditions. See
[Boyd–Vandenberghe logistic log-likelihood concavity](https://web.stanford.edu/class/ee364a/lectures/stat.pdf),
slide 7.5, for the underlying convex objective.
It does not guarantee that the finite-precision Newton process succeeds within
100 updates, or that a small gradient is a coefficient-error certificate.

## Loss, regularization and independent fitting

No L1/L2/elastic-net/Firth, lambda, clipping, pseudocount, class weights,
oversampling or resampling. Each head uses ordinary unweighted mean NLL:

`mean(logaddexp(0,X*beta)-y*(X*beta))`.

Uncoupled unregularized SUM likelihood is L0_sum+L1_sum. When head argmin sets
exist, its minimizer is the product of the head minimizers. Changing each
head loss to a positive local-mean scaling preserves those mathematical
minimizers. The synthetic tests check the block algebra.

Fit STATIC first and MOVE second independently. Each uses its own original-order
row subset, the same immutable V1 normalizer and its frozen basis.
This does not claim optimizer byte equivalence to a zero-padded joint fit:
reduction order, local/global mean scaling, Armijo path and parameterization
can differ. Reusing the old unregularized method avoids choosing a new lambda;
separation is rejected instead of rescued with regularization.

## Exact historical Newton machinery

The reference directly reuses empirical_hurdle_fit_cv_math.newton:

- Zero float64 coefficient initialization.
- Gradient X.T@(p-y)/n_head.
- Hessian X.T@((p*(1-p))[:,None]*X)/n_head.
- Direction numpy.linalg.solve(H,g); update beta-alpha*direction.
- Per-head local mean maxabs gradient <=1e-8.
- At most 100 accepted updates.
- Armijo c=1e-4; alpha=0.5**j for j=0..20.

Gradient is tested first; if not converged and updates>=100, fail.
No global n_head/N gradient weighting. The prior witness local gradient 2e-8
versus globally scaled 2e-9 must not falsely pass the local stopping test.
Singular Hessian, nonfinite values, nonpositive Newton slope, no accepted
Armijo trial and nonconvergence all fail closed. No fallback.
The exact separation certificate is a prefit gate, independent of convergence.

## Combined score and global TRAIN threshold

Reconstruct one probability vector in original TRAIN order, selecting STATIC
or MOVE head by each row's raw z. Both heads must have passed before threshold
finalization. No per-head threshold is introduced.

Reuse the exact V1 threshold function on this new combined score:

- Sorted unique union of {0.0,1.0} and all finite TRAIN probabilities.
- MOVE iff p>threshold; equal is STATIC; no epsilon/rounding.
- Python-int BA_NUM=TP*N_negative+TN*N_positive.
- Lexicographic maximum: BA_NUM, TN, threshold.
- Stable score sorting and exact equal-score groups.

This is a historically predeclared classification policy without a new target
or Stage2-dependent task objective. BA applies to threshold selection only,
not class-weighted training. DEV labels never enter fitting.
A saturated probability 0 cannot be made MOVE by this finite domain; no
negative/nextafter cutoff or hidden default 0.5 is introduced.

This rule can still choose very conservative decisions on poor or tied scores.
No collapse prevention or real improvement is promised.
The closed family concerned the old fixed score; a global threshold on the
new context-conditional representation is a different experiment.
No V2/V3 objective or TP floor is silently inherited.

## Stage2, folds, acceptance and unchanged selector

Stage2 coefficients and its original MOVE-only TRAIN normalizer must be reused
byte-identically for the same candidate/fold. Its subset anchor is bound
separately from the Stage1 parent TRAIN anchor. No Stage2 fitting/search.

All sixteen structures and two historical route folds/anchors remain exact.
All 32 jobs must be recorded, including failed jobs. One head failure closes
that job; candidate admission requires both folds and the unchanged 32-clause
Hurdle gate. Projection, p95, one-step populations, horizons25/50/100/200,
OVERALL/PATH_MOVED metrics and all comparison operators stay unchanged.

The exact pinned selector code and receipt still use 2P as their historical
complexity ordering proxy. It must not be reported as the actual V4 parameter
total: V4 nominal Stage1+Stage2 is 3P, generic identifiable upper 3P-1.
For this exact fixed structure set, 2P and 3P are both strictly increasing in L
and independent of d. With all preceding metric keys and following L/d/ID keys
unchanged, all 256 ordered candidate-pair comparisons are identical.
Thus the original selector can be reused exactly, with true V4 counts reported
separately. This is not a claim for arbitrary future model families.
No current gate or model selection was executed.

## Artifact identity, environment, repeatability and resume

Future private head artifacts bind candidate/fold/context, architecture/policy
receipts, TRAIN/source/anchor identity, V1 normalizer receipt/content hashes,
basis positions/feature names, class counts, singular diagnostics, exact rank
minor, separation proof, float64 coefficients, convergence and content hashes.
Public artifacts expose permitted counts/statuses/opaque hashes only.

Future actual execution requires Python3.12.13, NumPy2.5.3, float64 C-order,
OpenBLAS/OMP threads1, RNG NONE and pinned BLAS build identity
704bde2afe24c22d171cc7d2508517db81b7db455743b2cb0e5de9dda88da7a2.
Do not publish private np.show_config metadata.

Two independent E output roots must recompute fits and thresholds without RUN1
cache reuse. Compare source/model/normalizer identities, bases, rank/separation
receipts, coefficients, convergence, combined probabilities, thresholds, future
DEV/rollout/gate/selection aggregates, logical manifests and payload hashes
byte-exactly. Because certificate witnesses need not be unique, a deterministic
generator algorithm/version/transitive source identity must be frozen before
execution. Reduced rational numerator/positive-denominator decimal strings use
canonical sorted JSON. Proof bytes, matrix row order and generator identity must
also repeat exactly. Physical root paths must not alter logical result identities.
Mismatch gives V4_EXACT_REPEATABILITY_FAILURE.

Verify-only resume must validate saved finalized artifacts without opening
source numerics or recomputing fits, thresholds or rollouts. Future resume
tests must trap source/model loaders, fitter/normalizer/predictor/threshold,
DEV/rollout/scorer/selector. No actual resume executor was implemented here.

Future private model/proof/result payloads are E_EXTERNAL_SSD only.
Verified explicit roots, fresh real E capacity, volume/mount identity,
non-overlap, authorization and deterministic compression are required.
No broad scan or guessed path. The existing E storage pattern receipt is
historical provenance, not a V4 execution authorization.
No private executor is automatically built or run.

Coefficients are small; HUGGING_FACE_NOT_REQUIRED_FOR_MODEL_SIZE.
No HF setup/login/repo/upload/download or actual model artifact generation.

## Changes, regression risk and acceptance

Added one pure synthetic math/scaffold module, tests, a public producer,
fourteen sealed policy artifacts and this document. Historical files and
controller/vehicle interfaces are untouched.

Risks: misidentifying numerical rank as an exact proof, accepting approximate
dual residuals, normalizer drift, using a centered value for z, treating
convergence as non-separation, silently changing the selector complexity
meaning, or mistaking policy readiness for execution authority.
Focused negative tests and independent reviews address these risks.
Rollback removes this additive increment; no active runtime consumer changes.

## Validation method and actual results

Ubuntu24.04 WSL VHD on E; Python3.12.13/NumPy2.5.3; single BLAS/OMP thread.
All new scripts, synthetic data, logs and temporary results are on E-backed WSL.
Legacy D-path tests run in an isolated empty tmpfs mount namespace, preserving
global mounts and historical guards.

| Check | Method | Result |
|---|---|---|
| New fitting policy | pytest test_empirical_hurdle_v4_fitting_policy.py | 51 PASS |
| Prior V3/V4/representation | explicit focused pytest files | 264 PASS |
| Combined empirical | pytest test_empirical*.py | 2083 PASS |
| Full AutoTune/controls | tools/test_runner.py -j4 | 4942 PASS |
| Lateral replay | two explicit cyber lateral process-replay modules | 16 PASS |
| Static/build | Ruff, compileall, JSON718, publication/privacy, diff whitespace, SCons | PASS |
| Independent reviews | numerical/statistical; causal/authority/reproducibility | APPROVED |
| Synthetic fitting/thresholds | deterministic fixtures and two-run result identity | PASS, synthetic only |
| Actual private fitting/performance | not authorized | NOT_RUN |

Actual empirical operation counters are zero. Authorized synthetic fitting and
threshold calls are reported separately; zero actual calls does not mean the
synthetic tests skipped fitting. Validation receipts bind observed commands, exit codes, opaque E-log hashes,
reviewed source hashes and counts/environment. The full run source binding was
identical before/after, and all 4942 tests passed on the first full attempt.

The final GitHub workflow binds the resulting commit separately.

## Handoff and authority

HURDLE_STAGE1_V4_FITTING_POLICY_REVIEW_COMPLETE.
HURDLE_STAGE1_CONTEXT_CONDITIONAL_LOGISTIC_V4_FITTING_POLICY_FROZEN.

Actual V4 fitting/CV/DEV/rollout/selection/performance remain NOT_RUN;
actual coefficients NOT_GENERATED. Private numeric/raw/qlog/HOLDOUT opens0.
Historical S2-RI/V1/V2/V3 NO_ADMISSIBLE and failed-closed records, old fixed-score
project closure, earlier two-context policy INCONCLUSIVE, causal state contract,
architecture freeze and Stage2 long-horizon residual risk remain preserved.

Next recommended increment is separately authorized private executor/certificate
implementation and synthetic validation, not actual fitting.
HOLDOUT CLOSED, opening/discovery0, pooled refit NOT_AUTHORIZED.
Vehicle authority NONE; NOT_READY, REAL_VEHICLE_UNVERIFIED,
VEHICLE_ACTIVATION_BLOCKED. No automatic next step.
