# Cyber AutoTune retrospective development evaluation — 2026-10-03

Status: **development diagnostics passed where evaluable; independent holdout remains unavailable.**

## Scope and immutable boundaries

- Input: compact route-level sufficient statistics only; no raw log/point reopening.
- Development corpus: 85 routes, 216,356 accepted points.
- Eligibility rule: route point count >= 100, fixed before the evaluations.
- Eligible: 35 routes / 216,202 points; excluded: 50 routes / 154 points.
- Holdout/H1/H2 opened: false.
- Candidate generation, Params write, vehicle/CAN I/O, runtime acceptance and promotion: false.
- All routes were previously inspected as development data, so none of these results is an untouched holdout result.

## Diagnostic A — deterministic route-hash split

Policy SHA-256: `202efdcac402e1aad86141cc18ef7be87b1664b004e39d7bfec635445988d376`

- assignment: SHA-256 route hash, modulus 5, evaluation residue 0
- fit: 27 routes / 176,750 points
- evaluation: 8 routes / 39,452 points
- excluded: 50 routes / 154 points
- source-commit overlap: 4 commits occur in both fit and evaluation
Result: `DEVELOPMENT_STATISTICAL_DIAGNOSTIC_PASS`

| metric | observed | frozen limit |
|---|---:|---:|
| fit latAccelFactor | 4.0218395908764 | diagnostic only |
| fit offset | -0.17678726243336682 m/s² | diagnostic only |
| fit residual RMSE | 0.2471727931604575 m/s² | diagnostic only |
| evaluation RMSE | 0.26880707487851535 m/s² | <= 0.30 |
| evaluation mean residual | 0.02719701983251796 m/s² | absolute <= 0.10 |
| evaluation / fit RMSE | 1.087526954085167 | <= 1.50 plus 0.03 m/s² allowance |
| max leave-one-route factor delta | 1.4893548691430931% | <= 20% |
| max leave-one-route offset delta | 0.0049468566951703374 m/s² | <= 0.10 |
| jackknife 95% factor relative half-width | 5.155378439352535% | <= 20% |

This split is route-disjoint but not source-commit-disjoint. It is retained as a development diagnostic, not independent evaluation.

## Diagnostic B — single source-hash split

Policy SHA-256: `894372590e4cc6580c53f751044ef75ccf1b4a5d624d877e2f1cfafd7edeb65e`

- assignment: SHA-256 source commit, modulus 3, evaluation residue 0
- fit: 13 source commits / 33 routes / 205,044 points
- evaluation: 2 source commits / 2 routes / 11,158 points
- source overlap: none
Result: `BLOCKED — INSUFFICIENT_SOURCE_DISJOINT_SPLIT`

The source assignment was frozen before its result was observed. It was not changed after producing only two evaluation sources, and no fit was run under this policy.

## Diagnostic C — leave-one-source-out development evaluation

Policy SHA-256: `ec960cc45163934c5712af24e28c0d682eed128921c4b40f27264b69e109d4a2`

Every eligible source commit is held out exactly once. Each fold fits all other sources with equal source weighting and equal route weighting within each source.

- eligible source commits: 15
- folds: 15
- eligible routes: 35
- points: 216,202
- maximum single-source point share: 31.49462077131571% (limit 40%)
- all folds passed: true

Pooled equal-source reference estimate:

- latAccelFactor: `4.143064765944319`
- offset: `-0.16857079743173622 m/s²`
- residual RMSE: `0.2504412682066414 m/s²`
- mean residual: `0.0005811392649065374 m/s²`
| LOSO metric | observed | frozen limit |
|---|---:|---:|
| max fold factor delta from pooled | 1.2099887061635247% | <= 5% |
| max fold offset delta from pooled | 0.0053990778818112095 m/s² | <= 0.05 |
| max held-out source RMSE | 0.29397200544801755 m/s² | <= 0.30 |
| max held-out absolute mean residual | 0.07417210654295672 m/s² | <= 0.10 |
| max held-out / fit RMSE ratio | 1.1851354995457644 | <= 1.50 plus 0.03 m/s² allowance |
| mean held-out source RMSE | 0.25000032891667373 m/s² | diagnostic |

Result: `SOURCE_LOSO_DEVELOPMENT_DIAGNOSTIC_PASS`

All 15 source-disjoint folds pass the predeclared numerical gates. This indicates the diagnostic relationship is not dependent on one software source commit, but it still does not establish an untouched holdout, causal vehicle improvement, or deployment confidence.

## Weighting sensitivity

The earlier point-weighted cluster estimate was `4.024832798307419 / -0.17960344075536194 m/s²`.
The equal-source reference is `4.143064765944319 / -0.16857079743173622 m/s²`.

- factor difference: 2.9375622184012403%
- offset difference: 0.011032643323625718 m/s²

This difference is retained as weighting sensitivity. Neither estimate is promoted as a vehicle parameter.

## Authority and next gate

Remaining blockers:

1. `CONFIDENCE_QUALIFICATION_NOT_GRANTED`
2. `CANDIDATE_GENERATION_NOT_AUTHORIZED`
3. `QUALIFIED_REPLAY_NOT_RUN`
No result in this report authorizes use of `4.02` or `4.14` as an active comma4/vehicle value. The next scientific gate requires genuinely new, untouched driving data or another externally frozen evaluation source, followed by qualified replay and closed-loop comparison.

## Verification

- route-statistics module tests: 8 passed
- source-statistics module tests: 8 passed / 4 subtests
- source-LOSO module tests: 6 passed / 4 subtests
- actual runner tests: route 3 passed; source split 3 passed; LOSO 2 passed
- affected AutoTune + controls: **470 passed**
- Ruff: PASS
- `git diff --check`: PASS
- all three actual result files reproduced byte-identically

## Artifact identities

- route split policy: `202efdcac402e1aad86141cc18ef7be87b1664b004e39d7bfec635445988d376`
- route split result: `04a60bf8b79160d2af0b938b0933b69abfcf09e6131680bd947b6365169fae91`
- source split policy: `894372590e4cc6580c53f751044ef75ccf1b4a5d624d877e2f1cfafd7edeb65e`
- source split result: `c2969053f8757f74fc22e8bda829a6fe7cd9c3b0547fac95cae3275036459685`
- source LOSO policy: `ec960cc45163934c5712af24e28c0d682eed128921c4b40f27264b69e109d4a2`
- source LOSO result: `13d1d0fc405353478186565ab82177c3760cb09aa98b900de1c2bf97962afefc`
- sufficient statistics: `d10f031af2122948e63f5f6e06d979c604b8798385ade1cf1d38a2a130672315`
- route runner: `33ca6b65a892aa5eb4d0daca3d60057e933ff8d8407c9c60dd9379c2d6cb0a0d`
- source split runner: `a8efa7f66e6bfb4bf89eefdc0c559ef3264c3c91b2bdc4974ff4261160ccb098`
- source LOSO runner: `f4ff7e60f9a15e69daf612ab2dabfd01f8091af0c06abe9c974178cf1360b98c`
