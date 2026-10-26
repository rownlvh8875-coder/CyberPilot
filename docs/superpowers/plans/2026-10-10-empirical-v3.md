# Empirical V3 route CV implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task. The user authorizes native execution and independent review without intermediate questions.

**Goal:** Develop actuator structures on exactly the two admitted V2 TRAIN routes, without changing V2 or opening a holdout.

**Architecture:** Add separate policy/cache/CV/publication modules. Reuse immutable V2 alignment and model functions; enforce new route-equal selection and two-fold directional admission. Store arrays, coefficients and predictions privately.

**Tech Stack:** Python 3.12, NumPy single-thread BLAS, sealed JSON and atomic immutable NumPy arrays.

**Spec:** User's EMPIRICAL_PLANT_V3_RETROSPECTIVE_ROUTE_CV request.

## Global constraints

- RETROSPECTIVE_MODEL_DEVELOPMENT; no independent validation or ready claim.
- Read exact full route IDs from pinned V2 split; exclude V2 DEVELOPMENT from scoring.
- 201 common rows; unchanged ARX1/FIR25 delays 0/5/10/20; unchanged metrics and timebase.
- Policy frozen privately before fitting. No V2 writes, holdout, Stage C, candidate/controller execution.
- Public aggregates only; raw arrays and coefficients private.

## Review focus

- Stale cache/code/source binding must reject rather than resume silently.
- A large route must not dominate the primary ranking.
- Missing horizons must not masquerade as finite validation.
- A selected structure failing either fold must not enter the holdout package.
- Pooled refit must never claim development evidence.

### Task 1: Policy and immutable cache binding

Files: empirical_v3_policy.py, empirical_v3_cache.py, test_empirical_v3.py.
- [x] Write tests for exact two-route allowlist, fold inversion, excluded route, unchanged support/grid.
- [x] Verify failures, implement policy/folds and readonly cache validation.
- [x] Verify source hashes, metadata/opening/cache receipts and V2 closure. Preserve a private before/after V2 digest.

### Task 2: CV model execution and admission

Files: empirical_v3_models.py, empirical_v3_generation.py, test_empirical_v3.py.
- [x] Test worst-route ranking, equal-route mean/ties, same-support naive gate, conditional refit.
- [x] Implement separate fold fits, private design/prediction arrays, existing one-step/endpoint metrics.
- [x] Freeze conservative cross-fold yaw admission; block weak gyro even with kinematic support.
- [x] Independent pre-execution review, freeze policy and run twice. Exact output conflicts reject.

### Task 3: Publication and completion

Files: empirical_v3_publication.py, test_empirical_v3_publication.py, change record and aggregate JSON.
- [x] Test publication whitelist, historical preservation, closed holdout, forbidden authority.
- [x] Publish aggregate fold results and readiness; include coefficients only as private model SHA.
- [x] Complete focused/full/controls/replay/Ruff/syntax/privacy/publication/SCons/diff checks.
- [ ] Independent final review; commit, push, verify exact HEAD Actions success and clean equal local/origin.
