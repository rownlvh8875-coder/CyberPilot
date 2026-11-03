# R45 — Comparison boundary hardening

## Intent and authority

Close two deferred offline maintenance items after R44 main integration. The owner
delegated routine development choices and opted out of repeated design questions;
these are the author's scoped choices, not a new vehicle or rate-policy approval.
Base: `a0bcbd34c017b26868404cc9a7f5905a0005fa25`.

## Approaches

1. **Selected: R44 boundary-only normalization and test-only R43 coverage.** Small,
   preserves shared R34 behavior and all existing specific rejection codes.
2. Refactor shared preflight for every tool: broader compatibility risk, unnecessary.
3. Handle errors only in CLI: leaves the reported programmatic API inconsistency.

## Contract

`run_campaign_comparison(baseline: Path, candidate: Path, output: Path) -> dict`
keeps its signature. During preflight only, ordinary `OSError` (including permission
denial) and invalid-path `ValueError` become `CampaignCompareError` with code
`CAMPAIGN_COMPARE_IO`. The original exception stays chained. Existing `CompareError`
codes keep their current prefix mapping; do not blanket-catch programmer `TypeError`
or replace specific encoding/output/runtime errors. Reject before reading campaign
bytes, observing comparator identities, or creating outputs. No sensitive path/error
text is printed by CLI. CLI rejection remains exit2 with no output for preflight errors.

Tests must cover OS/path errors in the baseline, candidate, and output positions,
preserve specific rejections, and confirm unexpected programmer errors are not hidden.
An external real mode-000 path probe complements deterministic unit fault injection.
The Linux runtime is already pinned; no cross-platform compatibility expansion.

R43 source verdict aggregation already gives ERROR priority independent of order.
Parameterize its existing real-worker test over `[42,43]` and `[43,42]`, with seed42
ERROR and seed43 DIFFERENT. Assert ordered runs/findings, ERROR/exit2, successful
reported model/reference counts32/16, one injected difference, and closed Manifests.
This is test-only coverage, not a newly discovered producer defect. A first-child-
wins in-memory mutant should fail the reversed-order assertion.

## Non-goals and constraints

- No new calculator, worker, generator, output/schema version, tolerance or fallback.
- Preserve public0.3.0 API/wheel, model/reference source, shared R34 preflight,
  R43 producer, locks/dependencies, cloud tools and CI configuration.
- Preserve all existing snapshots, environments, branches and historical evidence.
- R_BUDGET UNRESOLVED; Static Gate FAIL; actual r/T2/vehicle scale null;
  Candidate/Runtime NO_GO; F70UH/F70V/F71/vehicle activation NOT_ALLOWED.
- Fixture/unit/gate/CI synthetic work is NONZERO and not aggregated. Comparator
  read-only acceptance performs no new model/reference work; no F61/actual r/dt.

## Delivery

One scoped branch, independent final review, full DEV gate and cloud checks, actual
exact-head PR CI plus artifact checks. This stage ends with an open reviewed PR,
not a main merge or HF refresh; those use the later integration workflow.
