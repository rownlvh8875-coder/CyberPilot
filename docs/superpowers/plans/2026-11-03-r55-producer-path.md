# R55 Producer Path Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound remaining producer path errors and retain R54 overlong regressions.

**Architecture:** Extract existing batch preflight; narrow classified-first
acquisition/metadata boundaries; keep workflow/generation/worker bodies intact.
Independent permanent existing-behavior coverage task, no new numerical policy.

**Tech Stack:** Existing CPython3.12.13/Linux/unittest/stdlib and locked tools.

**Spec:** `docs/superpowers/specs/2026-11-03-r55-producer-path-design.md`

## Global Constraints

- Parser, generator, model/reference arithmetic, worker, schema/wheel/locks/cloud/CI unchanged.
- Existing classified errors, source-open per-file rejection and guard priority preserved.
- No blanket later ValueError catch, path repair, normalization, scale/r/time fallback.
- R54 authority stays in its exact reviewed snapshot; only existing host worktree is edited.
- Old branches/envs/evidence retained. R_BUDGET unresolved/StaticFAIL/actualr-T2-scale null.
- No actual F61/r/dt/vehicle/Controller/Runtime/CAN; all activation gates closed.

## Review Focus

- ScenarioError/BatchError/WorkflowError/ExplorationError/CampaignError subclass ValueError.
- Batch UTF8 guard comes before output exists; preserve this existing ordering.
- Batch preflight extraction must not put capture/parse under a generic catch.
- Workflow unavailable input and Exploration→Campaign mapping must retain their semantics.
- Generation/parameter validation order precedes output preflight and must not silently move.
- Later parser/identity/worker/publication errors must not become new path failures.
- R54-M1 needs actual permanent OS-argv coverage; non-strict long inputs use owned readers.
- Identity hash/manifest changes do not justify removing arbitrary fields from parity checks.

### Task 1: Bound producer capture and preflight errors

**Files:**
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_batch_input.py`
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_workflow_input.py`
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_explore_run.py`
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_campaign_run.py`
- Create: `tools/cyberlateral_dev/project/test_scenario_producer_paths.py`
- Modify: R33/R40/R42/R43 KO docs under `tools/cyberlateral_dev/docs/`

**Interfaces:** unchanged prepare_batch/prepare_workflow/run_exploration/run_campaign;
new DEV BATCH_IO for unclassified batch preflight, existing other IO/location/input-file
codes retain scoped typed errors/causes. Workflow inherits explicit batch-stage BATCH_IO.

- [x] Read clean actual main and reused854 baseline93 relevant methods, no duplicate baseline run.
  Expected: same source tree as reviewed R54; actual raw NUL errors reproducible without workers.
- [x] Promote/complete external test draft with real CLI, cause/priority/type/later-fault controls.
  Run focused new suite; Expected RED from missing classification, existing controls green.
- [x] Minimal descriptor/preflight/resolve changes per spec, docs accurate to their order.
  Expected GREEN new suite and existing relevant suites, no forbidden worker/publication.
- [x] Verify extracted preflight/later-body AST and same-input successful outputs with
  only exact source-identity deltas; Expected inputs/source/closed manifests retained.
- [x] Commit Task1 and run its fresh completion test; Expected exact committed HEAD / green ledger.

### Task 2: Retain R54-M1 overlong regression permanently

**Files:**
- Modify: `tools/cyberlateral_dev/project/test_scenario_reference_paths.py`

**Interfaces:** existing R38/R39 public APIs/CLIs and error codes; no production change.

- [x] Add permanent actual overlong input/output API/OS argv cases for both frontends.
  Expected baseline GREEN; input reader/code distinction preserved, worker/output0.
- [x] Run that same test against exact pre-R54 source in an isolated process if available.
  Expected retrospective RED on untyped API output failures, not a fabricated new behavior.
- [ ] Run current reference suites, commit Task2 and fresh completion.
  Expected GREEN and permanent test/source/ledger identity; only then mark R54-M1 addressed.
- [ ] Full DEV/cloud verification and one fresh whole-branch final review.
  Expected static/compile/all tests PASS, wheel canonical; at most one TDD Important/Critical fix pass.
- [ ] Ordinary push/create/attach PR, actual CI/artifact validation, two-build seal;
  guarded normal main/private-HF/two recoveries without approval pauses.
  Expected no bypass/force/delete/visibility change or new vehicle/r-policy authority.
