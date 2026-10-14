# Hurdle Stage1 V4 executor implementation and exact certificate review

V4의 모델 구조와 학습 규칙은 이미 정해졌다.

이번 작업은 실제 주행 데이터를 학습하는 단계가 아니다.
실제 학습 전에 각 Logistic head가 정상적으로 식별 가능한지,
데이터가 완벽히 갈라져 계수가 무한대로 가는 상황인지,
그 판정을 정확하게 증명하는 도구를 만들었다.

그리고 나중에 실제 데이터를 열었을 때 정해진 순서 외의 동작을 하지 못하도록
실행기와 권한 장치를 만들었다. 이번 검증은 synthetic 배열만 사용한다.
실제 private 배열, 계수, threshold, DEV, rollout, selection은 모두 NOT_RUN이다.

## Identity and purpose

- Area: Cyber Validation / offline AutoTune.
- Repository: https://github.com/rownlvh8875-coder/CyberPilot
- Branch: feature/cyber-autotune.
- Baseline: c508cddf833ed7b98b12765f19c68f316f1710fc.
- Architecture: HURDLE_STAGE1_CONTEXT_CONDITIONAL_LOGISTIC_V4, unchanged.
- Fitting policy: FROZEN, unchanged.
- Scope: additive certificate, future private executor, authority/storage/resume
  implementation and synthetic-only validation.
- Actual retrospective authorization: absent. No grant is generated.
- Vehicle applicability: none; no controller integration or actuator consumer.

## Original references and source trace

Original project source is the repository/branch/baseline above; existing licenses
and upstream layout are preserved. No external source code, dependency, model,
submodule or LFS payload is imported.

- [Frozen V4 fitting policy](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_fitting_policy.py):
  basis/normalizer definitions and frozen numerical constants.
- [Historical Hurdle math](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_math.py):
  newton, threshold, sigmoid, projection, metrics, diagnostics.
- [Historical data](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_data.py):
  design, binding, pair, subset_sha.
- [Historical gate/selector](../../../openpilot/tools/cyber_autotune/empirical_hurdle_fit_cv_gates.py):
  fold_gate, select, selection_key. All 32 clauses and both-fold admission remain.
- [V3 external storage proof](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v3_external_storage.py):
  prove_authorized_external_volume and check_live_volume.
- [New certificate](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_certificate.py):
  rank_generate/rank_verify, separation_generate/separation_verify.
- [New authorization](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_authorization.py):
  contracts, preflight, valid, capacity.
- [New I/O](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_io.py):
  metadata admission, normalizer/Stage2 reuse, finalized TRAIN dependency check,
  permit-bound route read, before/after immutability.
- [New store](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_store.py):
  mandatory admitted output, atomic immutable JSON/NPY, saved-only verification.
- [New executor](../../../openpilot/tools/cyber_autotune/empirical_hurdle_v4_execution.py):
  train → finalized receipt → development → projected-context rollout → gate/select.

Public policy file SHAs and receipts are pinned independently. Historical numerical
source SHAs are pinned too; all new runtime source SHAs bind future external
authorization. Neither a matching hash nor this implementation report grants
permission to execute actual fitting.

## Exact rank

Both frozen rank conditions are mandatory:

1. Float64 singular values, with
   tol=sigma_max*max(N,P)*finfo(float64).eps and rank=count(sigma>tol)=P.
2. A P×P row minor with exact nonzero determinant.

The deterministic generator retains the first exactly independent original rows.
Every finite binary64 value is its exact dyadic rational via as_integer_ratio.
A positive dyadic row scale produces integers; fraction-free Bareiss with exact
division and pivot sign tracking computes the determinant. Scaling is restored
and the normalized numerator/denominator recorded privately.

The verifier independently checks the SVD criterion, unique/in-range row offsets,
matrix/basis/normalizer binding, exact determinant and certificate hash.
Minor witness rows certify the full population; they do not filter fitting rows.
SVD failure, unavailable minor, arithmetic/certificate failure or resource bound
never falls back to empirical column dropping or pseudo-inverse fitting.

Memory is O(NP+P²), including the original float design and small exact basis.
There is no N×threshold matrix or N×P Python Fraction matrix.

## Separation theorem and compact proof

For signed rows A_i=(2y_i-1)X_i, separation means a direction b with A_i b>=0
for all rows and a strict positive margin somewhere. Complete and quasi separation
both fail the frozen unregularized policy.

The exact alternative is lambda_i>0 for all i with Aᵀlambda=0.
Scale lambda so lambda>=1, set q=lambda-1, and obtain
-SUM(A_i)=SUM(q_i A_i), q>=0. Conic Caratheodory reduces the correction to
at most rank(A)<=P rows. With rational input and target, independent selected
generators yield rational weights. Clearing denominators produces:

D*SUM(A_i)+SUM_active(q_i A_i)=0, D>0 integer, q_i>0 integer.

The certificate sorts distinct active row offsets, removes zeros and divides
the common positive gcd. This gives lambda_i=D+q_i>0. Presence uses an integer
direction divided by its positive gcd; its sign must not be flipped arbitrarily.

The absence verifier computes exact column sums and sparse correction.
The presence verifier computes exact margins for every signed row. Identical
rows may be compressed with exact multiplicities. A nullspace vector with no
strict margin is rejected. Near-zero binary64 is never rounded to zero.
The proof hash covers canonical proof fields only, excluding runtime telemetry.

For the sparse support reduction, if a positive cone representation uses dependent
generators, choose a nonzero rational dependence and move its coefficients until
one nonnegative coefficient first reaches zero. The target is unchanged; repeating
leaves independent generators, at most rank(A). This explains the support bound
without assuming that the implemented generator always finds that representation.
[Boyd–Vandenberghe, section5.8](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf#page=276)
provides primary background on strong alternatives and mixed strict/non-strict
linear systems. The exact positive-lambda algebra here fixes our orientation.

This is a direct algebraic proof; correctness does not depend on a floating LP
termination flag or the name of an optimization theorem.

## Generator and operational limits

The generator is a deterministic cone active-set column proposal. It proposes
active rows using float residual costs with smallest-original-index tie handling.
It reconstructs the active rational Gram system exactly, then submits either a
zero-residual sparse correction or a nonzero residual direction to the independent
exact verifier. No floating verdict is authoritative.

This is an incomplete generator, not a claimed complete Lawson-Hanson solver.
Dependent active systems, failed exactification, invalid signs, cycling or
unverifiable candidates produce INCONCLUSIVE. Default 4P² proposal iterations is
an operational cap, not a scientific threshold or an architecture rejection.
Exhaustion returns SEPARATION_CERTIFICATE_INCONCLUSIVE_RESOURCE_BOUND.
No guess, regularization or best-so-far certificate is promoted.

Logical row-pass telemetry counts high-level exact-sum, verification and float
proposal scans, not individual NumPy kernel memory traversals.
Worst-case rational bit growth and difficult cones remain costs; constructed
stress timings are descriptive, not a universal runtime guarantee.

## Frozen fitting and causal execution

Both heads pass support, numerical/exact rank and exact NO_SEPARATION before
either head fits. The STATIC head removes only the structural latest prior-delta
column; MOVE retains the full effective basis. Both share byte-identical V1
Stage1 TRAIN normalizer content. No new mean/std is computed.

The executor directly calls the immutable historical Newton function with zero
float64 initialization, local unweighted mean loss/gradient, tolerance1e-8,
100 accepted updates, Armijo1e-4 and alpha=.5**j for j=0..20.
No L1/L2, class weights, resampling, clipping, Firth or old-head fallback exists.

The combined score preserves original TRAIN row order and uses one global V1 BA
threshold: strict p>t; exact Python-int BA_NUM; ties TN then threshold.
Stage2 and its MOVE-only TRAIN normalizer remain byte-identical V1 artifacts.
The frozen selector's historical complexity proxy is reused exactly; the earlier
fitting-policy ordering proof remains authoritative.

TRAIN models, proofs, convergence, score and threshold are written and hashed,
then a finalized receipt is durably committed. DEV loading verifies that receipt
and its saved dependency graph. Failed heads remain recorded as failed jobs;
all 32 candidate/fold jobs are accounted. Gate failures do not stop other jobs.

z comes from raw previous source-grid tick increment before normalization.
The first rollout context uses observed anchor history; later contexts use
projected tick increments only. MOVE gate with half-even projected hold yields
STATIC next context. Route/segment/eligibility continuity is inherited from the
unchanged historical anchor machinery. No future measured truth enters inputs.

Logged command means post-CarController normalized command, not physical applied
EPS torque. Delta means source-grid tick change, not physical EPS movement.
steeringRateDeg remains SOURCE_NATIVE_RATE_CODE_ONLY / RATE_SOURCE_CONTRACT_PARTIAL.
There is no new rate dependency.

## External authority and E storage

V4 has its own schema/permit registry; V3 authority is not reused as a V4 fit grant.
The executor has no authorization command and cannot mint its own trusted SHA.
A future external one-shot authorization must bind exact HEAD/branch/repository,
all policy/component receipts, executor/generator/verifier source SHAs, immutable
V1 manifest/normalizer/Stage2/route/anchor identities, replica set, pinned environment,
source manifests, explicit roots, migration/amendment receipts and live E volume.

Precheck order is public policies, HEAD, source SHAs, external trusted receipt,
E identity, non-overlap, capacity, environment, metadata/model/anchor identities,
then numeric permission. No arrays open during precheck.

The inherited E proof checks the exact E letter, 9p mount root, kernel mount/device
identity, Windows live volume identity, no alias/nested mount and disjoint roots.
C/D/F/WSL roots are rejected; no D alias or output fallback is present.
No source discovery or broad E scan occurs.

Capacity includes RUN1+RUN2, rollout payloads, coefficients/score arrays, gzip/NPY
overhead, atomic peak, proof integer budget, metadata maximum and reserve.
The authorized bit/metadata/output maxima are enforced before writes. They are
operational storage bounds, not new model parameters. Insufficient capacity or
proof/metadata cap exhaustion fails closed without omitting required evidence.

Input members and authoritative metadata are opaque-byte hashed before/after.
Models/normalizers are read-only; writes target the separately admitted output only.
Output inventories during finalization/resume cover own result directories, never
input roots. No deletion function or automatic scratch cleanup is implemented.

## Repeatability, resume and privacy

Two independent output roots share immutable inputs only. Canonical proof choice,
coefficients, convergence, combined score, threshold, DEV, rollout, gates, selection,
all file hashes and manifests must agree exactly. Elapsed/RSS telemetry is separate.

Verify-only resume requires externally trusted auth/manifest identities for an
actual store and rechecks the live E volume. It verifies schemas, receipt seals,
dependency links, file hashes and decoded NPY shape/dtype/content, while source/model
loaders, certificate generators, Newton, threshold, predictor, DEV, rollout and selector
are trapped. Corruption fails; it never silently regenerates.

Public output contains code/receipt hashes, schema, synthetic aggregates and statuses.
Private roots, row offsets, proof vectors, coefficients, normalization values, actual
scores/thresholds/ticks/paths/gates/commands/timestamps/GPS remain private.
Hugging Face is not needed for compact logistic artifacts and was not used.

## Regression risks, acceptance and actual validation

Acceptance is exact proof or fail-closed INCONCLUSIVE, unchanged numerical policy,
synthetic E2E/firewall/storage/repeatability/resume pass, full regression/build/privacy
pass and independent numerical/authority approval. No performance target is added.
New files are additive and can be reverted without changing historical evidence.

The synthetic orchestrator test injects labelled external probes and source readers;
it exercises actual job/training/DEV/rollout/store/accounting code without opening
private inputs. Separate tests exercise rejection and admission ordering.
Synthetic gate-pass/admission fixtures test the exact frozen gate independently;
they are not claims that fitted real models pass it.

Observed commands/counts/log hashes and review statuses are in
[executor-validation](empirical-hurdle-stage1-v4-executor-validation.json).
Stress fixture code and limitations are bound in
[certificate-stress](empirical-hurdle-stage1-v4-certificate-stress.json).
Observed local validation:

| Check | Result |
|---|---:|
| New certificate/executor focused | 54 PASS |
| Historical V3/V4 including fitting policy | 315 PASS |
| Combined empirical | 2,137 PASS |
| Full AutoTune + controls | 4,996 PASS |
| Lateral replay | 16 PASS |
| Policy/change JSON | 731 PASS |
| Ruff / compileall / publication / diff-check / SCons | PASS |
| Independent numerical and authority reviews | 2 APPROVED |

Full-regression source SHAs match before/after exactly. The initial SCons
validation driver omitted the existing venv bin directory from PATH, so cythonize
and capnpc were not found. Restoring the established venv PATH and correct PWD
made the same build command pass; no dependency or product source changed.
Both attempts and their log hashes are retained in the validation record.

Legacy historical D-shaped synthetic fixtures ran in an isolated mount namespace
with a temporary in-memory filesystem. No D-to-E alias or retired D payload tree
was created. All new scripts, logs and synthetic files are E-backed.

Current implementation readiness is in
[executor-readiness](empirical-hurdle-stage1-v4-executor-readiness.json).
Replay here means only the required synthetic lateral regression. Simulation,
shadow, vehicle application and actual private V4 fitting were NOT_RUN.

## Handoff and absolute stop

Readiness, if all checks pass, is only
V4_PRIVATE_EXECUTOR_READY_FOR_SEPARATE_RETROSPECTIVE_FITTING_AUTHORIZATION.
It is not an actual execution grant or a performance result.

Next: separately review/freeze actual execution inputs, operational certificate
budgets, verified E roots/capacity, final exact-HEAD environment and external
one-shot authorization. Do not mint it or open private TRAIN in this increment.
HOLDOUT stays CLOSED, untouched future holdout REQUIRED, pooled refit NOT_AUTHORIZED,
vehicle NONE / NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
