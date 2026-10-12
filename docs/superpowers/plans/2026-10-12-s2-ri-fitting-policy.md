# S2-RI fitting policy implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline; independent final review uses a fresh reviewer.

**Goal:** Freeze exactly 16 retrospective S2_RI_V1 candidates and all future fit/CV/selection semantics without executing them.
**Architecture:** New static contract builder, exact public-evidence binding and closed policy validator/publication CLI. No numeric loader, model evaluator, selector or rollout executor.
**Tech Stack:** Existing Python standard library and empirical canonical JSON/seal helpers. No new dependencies.
**Spec:** User S2_RI_FITTING_POLICY_V1 steps 1–59 and explicit approval of additive direct-tick projection.

## Global constraints
All existing tracked evidence and private data immutable. Public input only. No fitting, prediction, residuals, actual metrics, normalizer fitting, CV scoring, selection, rollout, qlog, raw logs, HOLDOUT, controllers or device authority. Direct integer-tick ROUND_HALF_TO_EVEN is a newly versioned contract: historical degree-roundtrip semantics remain unchanged. Exactly d={0,5,10,20}, Lu=Ldelta=L={1,5,15,45}. Primary all-active scope; non-rail diagnostic only.

## Review focus
- Historical receipt SHA and exact file bytes must both be pinned; resealed drift must fail.
- Old structural X order is newest-first; fitting uses oldest-first as an explicit permutation, no historical rewrite.
- A half-tie can differ after binary64 degree roundtrip; direct-tick projection must not claim bitwise equivalence.
- All candidate/fold/horizon populations and numeric failure behavior must be fixed before performance.
- Policy validation must reject modified/resealed contracts and injected private/model fields without invoking execution APIs.

## Task 1: Evidence binding and contracts
Create empirical_s2_ri_fitting_contracts.py and empirical_s2_ri_fitting_policy.py.
Interfaces: load_inputs()->exact public artifacts; build()->filename/artifact mapping; validate(bundle)->bundle.
- [x] Write failing candidate/indexing/normalization/rollout/gate/selection contract tests.
- [x] Observe RED, implement declarative contracts and exact historical pins, verify GREEN.
- [x] Fixed features: intercept; commands u[k-d-L+1..k-d]; delta[k-L..k-1]; tick[k]; speed[k]. P=2L+3.
- [x] Fit contract: float64 OLS NumPy 2.5.3 lstsq rcond=None; effective nonconstant columns, TRAIN population std only.
- [x] Metrics: endpoint k+H over eligible anchors, H=25/50/100/200; same support comparator; exact operators, no epsilon.
- [x] Gate/selection are data contracts only, with no functions accepting performance values.

## Task 2: Validator, publication and firewall tests
Interfaces: publish(output)->immutable public files; CLI --output.
- [x] Closed full-bundle comparison against pinned canonical definitions; exact types and receipts; unknown/missing artifacts rejected.
- [x] Atomic no-overwrite publication; exact resume; symlink/traversal rejection.
- [x] Hard-trap model, solver, private-loader, raw-reader imports/calls while generation completes.
- [x] Test corrupted input bytes, resealed drift, candidate expansions, future/forbidden features, normalizer leakage, cross-boundary rollout, relaxed gate, reordered tie-break, runtime authority.
- [x] Publish required 10 artifacts plus explicit feature/grid/metric contracts and public validation receipt.

## Task 3: Review and completion
- [x] Independent read-only review; fix findings with RED/GREEN tests before full regression.
- [x] Focused, combined empirical, full AutoTune+controls, lateral replay, Ruff, syntax, JSON, publication/privacy, diff and SCons.
- [x] Feature record documents exact semantics, historical preservation, test evidence, no numeric access and separate future authorization.
- [ ] One logical commit, push, fetch, clean/equality and latest exact-HEAD CI completed/success.

## Decisions
User explicitly approved the direct-tick additive correction. Retain both historical grid-policy receipt and the new policy identity; do not relabel historical emission. Canonical future metrics use tick-coordinate errors (optional degree display only), not Float32 display rounding. Rollout primary metrics are endpoint errors at k+H across anchors; no averaged-short-horizon substitution. Source-range/nonfinite failures invalidate candidate/fold with no anchor dropping. No data access is needed to freeze these semantics.

## Execution ledger
Initial contract tests RED (implementation absent) then GREEN. Closed policy mutation,
binding, authority and synthetic publication tests pass: 56 tests / 48 subtests.
Independent reviewer found one P2: .atomic destinations not preflighted. Four
reproduction/postcondition tests RED then GREEN after all final/atomic paths and
exact bytes were checked before writes and all final bytes after persistence.
Historical common persistence helper is unchanged. No remaining review findings.
Combined empirical plus future-empirical: 1289 passed / 264 subtests after fixes.
Ruff, compileall, 16 lateral tests, SCons and publication (19 changed files,
1344 branch files; zero findings) pass. Full regression passed: 4063 in 1571.68 s (3921 AutoTune + 142 controls).

Commit/push and exact-HEAD CI verification follow this precommit validation record; no fitting follows.
