# R42 Stage Record Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the deferred malformed-internal-R39-JSON error-interface gap, then integrate PR13 only when its applicable CI/review conditions are satisfied.

**Architecture:** Keep the generator, model, R40/R39 and valid output schema unchanged. Validate the owned bounded canonical R39 stage record at the R42 ingestion boundary before any case traversal, reproducer writes or final publication. Map invalid serialized/container/required-field shapes to `ExplorationError('EXPLORATION_STAGE_RECORD')`; the existing CLI then returns REJECTED/exit2 with empty stdout. Semantic count contradictions retain the existing ERROR verdict.

**Tech Stack:** Existing CPython3.12.13/std-library and pinned DEV tools, no new dependencies.

**Spec:** User-approved continuation and the existing R42 design at `docs/superpowers/specs/2026-11-02-generated-boundary-exploration-r42-design.md`.

## Global Constraints

Work on existing isolated branch `feature/r42-generated-boundary-exploration`, base `f3a7351b6a46d8f58b3aeb89fa1193290e6ba719`. No public model/API/wheel, original reference, lock, production code, CI workflow or policy changes. Preserve existing evidence/workspaces. No vehicle/F61/actualr/dt/Controller/Runtime/CAN activation. No admin/force/required-check bypass or reference-baseline updates. Do not repair unrelated process-replay arithmetic without direction.

## Review Focus

- JSON scalar/list/null root or missing fields must fail closed without indexing exceptions.
- Invalid late cases must be checked before writing any reproducible-case subset.
- Unhashable report/status values and non-dict helper counts must never escape as TypeError/AttributeError.
- Valid reference-error records with nullable counts remain ERROR, not a schema rejection or vacuous MATCH.
- Malformed/duplicate/nonfinite/noncanonical/oversized bytes and nonregular files reject boundedly with original partial inputs preserved.

## Task1: Reproduce and fix the ingestion boundary

**Files:** Modify `tools/cyberlateral_dev/integration_tools/scenario_explore_run.py`; add `tools/cyberlateral_dev/project/test_scenario_explore_stage.py`; update Korean R42 documentation.

**Interfaces:** Existing `run_exploration(...)` and CLI stay unchanged. A private stage-reader/validator consumes only existing R39 fields; no new external loader/API or arithmetic. Reuse existing bounded no-follow byte capture and canonical JSON parsing instead of broad CLI exception masking.

- [ ] Write real saved-stage fixture tests first: use complete freshly generated R40/R39 results once, then replace only the slow completed workflow boundary with complete copies; alter stage bytes/shapes and exercise actual R42/CLI behavior. No fabricated PASS oracle or arithmetic mocks.
- [ ] Run focused tests before code; expected RED from unexpected KeyError/TypeError or incorrect generic error/acceptance, not import failures.
- [ ] Implement bounded canonical read plus required top/container/per-case/nullable field validation before traversal. Preserve valid MATCH/DIFFERENT/ERROR behavior, all gates and partial inputs; no completion record on rejection.
- [ ] Run new and existing targeted tests; expected GREEN, exact stderr/exit2/no traceback, no partial reproducer subset. Run Ruff/Ty/Codespell and commit after evidence.

## Task2: Verify, review and conditionally integrate

**Files:** External evidence workspace only plus normal feature commit/PR metadata.

- [ ] Run fresh exact committed-source full component/cloud-tool checks, unchanged wheel, normal generated repeat/baseline comparison, private archive and exact re-download; record actual test/compile/work counts.
- [ ] Fresh independent review of the hardening delta; any Important/Critical fix gets RED→GREEN and green suite. No unrelated feature expansion.
- [ ] Update PR13 normally and verify exact-head component CI/artifact/review. Inspect failed existing repository process-replay job read-only and compare pre-existing base evidence where available.
- [ ] Merge normally only if applicable required CI/review conditions are met; no bypass or hidden failure. If replay needs unrelated production/config/reference changes, keep PR open and report the exact blocker/request direction. If merged, verify exact main identity/component results and privately archive the receipt. Never mark activation gates PASS from offline CI.
