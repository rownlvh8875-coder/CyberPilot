# Empirical model family identifiability audit implementation plan

Goal: audit exact existing rlog causal arrays without fitting, prediction, target loss or family selection.
Architecture: additive source audit, frozen numerical policy, strict pre-array manifest admission, input-only diagnostics and redacted publication.
Tech stack: existing Python/NumPy, canonical receipt storage, no new dependency.
Spec: user EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_AUDIT_V1; prompt ends during reset step; implement stated authorized scope without assuming further authority.
Execution: writing-plans / executing-plans inline, TDD, independent final review.

## Constraints and predeclared forms
- Historical source/artifacts/stores immutable; minimum ancestor 79a752600.
- Resolve authoritative PARTIAL / PASS / COMPLETE before metadata/array access.
- Exactly original 154-rlog manifest, two retrospective routes; deny qlog by content before any arrays.
- Existing support guard with history=1. Derive contiguous admitted streaks within segment/causal run/grid, independently check guard histories on synthetic tests.
- History envelope L=1..45; lag envelope d=0..20; minimum route DEVELOPMENT availability=201. No selected L/d/family.
- S1 columns angle[k], source-native rate[k], logged normalized post-controller command[k-d], speed[k], intercept. Intercept remains one; all other constant columns center to zero and are reported.
- S2 columns chronological command history L, chronological angle history L, source-native rate[k], speed[k]. No intercept; no future target in X.
- X support uses present/history only. Next-state/target availability is counted separately using adjacent admitted rows in the same run. Delta-angle aggregates are diagnostic only and never passed into matrix diagnostics.
- Deterministic float64 population centering/std of each nonconstant input feature; no target scaling. Direct NumPy SVD compute_uv=False, rank tolerance smax*max(rows,columns)*float64 eps. Numerical rank, not proof of symbolic structural identifiability.
- Report full singular spectrum, constants/duplicates, input covariance/correlation, no arbitrary conditioning threshold. Route A, route B, pooled separately.
- Physical rate remains unproven unless exact source proves otherwise. Empirical finite-difference diagnostic cannot promote semantics.
- No S3 numeric regime search; absence of source-defined physical mechanism blocks S3.
- One BLAS thread; no RNG; two complete immutable executions / exact resume; no raw reader.

## Review focus
1. Qlog disguised as rlog: whole manifest and all segment receipts checked before np.load.
2. Cross-boundary windows: segment, run, mask, integer grid and source time checks.
3. Target leakage: rank API accepts X only; source target values cannot select layout.
4. Misleading rank: constant intercept convention and numerical tolerance explicit; no family admissibility from rank alone.
5. Publication: aggregate schema only; no arrays, individual values, paths or timestamps.

## Tasks
- [x] Policy/source: failing source/authority/layout tests, exact committed source audit; freeze policy in external store before arrays.
- [x] Numeric kernels: failing history/rank/leakage/target-only tests; input diagnostics and no fitting APIs.
- [x] Executor: failing admission/path/immutability tests; exact manifest, per-file hashes, guard and deterministic private receipts.
- [x] Execute twice; publish aggregate source/support/rank/reset/readiness and repeatability.
- [x] Independent review; focused/empirical/full/controls/lateral/Ruff/syntax/publication/SCons.
- [x] Document actual findings and complete local validation.
- Integration gate after this commit: push, exact-HEAD CI success and clean local/origin equality; report actual run in final handoff.
