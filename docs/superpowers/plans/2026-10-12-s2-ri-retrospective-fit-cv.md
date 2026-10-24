# S2-RI retrospective fit/CV execution plan

Scope: additive implementation of the already frozen S2_RI_V1 finite policy.
Baseline d954267e692d9a9faf74b56a7e22bd5489b98988; startup fetch, equality,
clean index/tree and exact-HEAD CI 38203411742 succeeded.

1. Resolve the canonical one-step binary64 error conflict before real metrics.
   Frozen policy subtracts observed delta from predicted delta, aliasing both
   continuous error channels. The execution request STEP 20 instead subtracts
   actual next tick from predicted next tick. These are not bitwise equivalent.
   User confirmed preservation of the frozen delta-error primitive before any actual metric. No historical contract is changed.
2. Implement and test exact public contract admission, chronological features,
   history/rollout anchor boundaries, TRAIN-only normalization, rank precondition,
   float64 OLS, finite failures and direct signed16 tick projection.
3. Implement read-only admission with exact historical and derived manifests,
   qlog deny check before arrays, then seal explicit external-store authorization.
4. Implement immutable per-job normalizer/model/results/receipt and manifest-last
   storage; verify-only exact resume; explicit accounting for every failure.
5. Implement frozen one-step and projected recursive rollout metrics, identical
   comparator populations, both-fold gate and deterministic candidate selection.
6. Review implementation and adversarial synthetic tests before first real metric.
7. Execute all 32 jobs twice independently with single-thread BLAS. Compare all
   bytes/digests/metrics/manifests and verify resume with compute paths trapped.
   After first real metrics, semantic fixes invalidate the run and require an
   additive invalidation record and a complete clean rerun.
8. Publish closed-schema aggregate evidence only, document outcomes, independent
   review, focused/empirical/full controls/replay/Ruff/syntax/JSON/privacy/SCons
   verification, commit/push and exact-HEAD CI success.

Historical files and private inputs remain immutable. No raw logs, qlog support,
HOLDOUT, pooled refit, TA/SG, production, device or vehicle authority.
