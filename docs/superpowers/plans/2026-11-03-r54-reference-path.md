# R54 Reference-check Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize only unclassified public reference frontend preflight failures.

**Architecture:** Extract unchanged R38 preflight; both public frontends add narrow
classified-first wrappers. Existing R39 preflight and both post-preflight bodies stay exact.

**Tech Stack:** Existing CPython3.12.13/Linux/stdlib/unittest/locked tools. No dependency.

**Spec:** `docs/superpowers/specs/2026-11-03-r54-reference-path-design.md`

## Global Constraints

- Model/reference arithmetic, worker, public wheel/API, schemas/locks/cloud/CI unchanged.
- REFERENCE_IO/BATCH_REFERENCE_IO already exist in CLI; no invented codes/policies.
- No broad later-reader/worker catch. Existing classified errors/codes/causes retained.
- Keep R38 surrogateescape support and R39 strictUTF8 rejection intentionally distinct.
- Retain old environments/branches/evidence; future clone GIT_LFS_SKIP_SMUDGE=1.
- All actual F61/r/dt/vehicle/Controller/Runtime/CAN gates closed; synthetic work labeled.

## Review Focus

- ValueError includes classified domain errors: own exceptions first; R38 also ReportError.
- R38 extraction and R39 preflight body must be AST-exact, with unchanged guard priority.
- Path.exists suppression must still lead to bounded NUL rejection before acquisition/worker.
- Do not transplant R32's receipt UTF8 policy into R38's path-free output.
- Later reader/identity/worker/publication errors must retain old semantics, not generic IO.
- NUL child main(argv), real OS-argv permission/long names and actual UID behavior differ.
- Source identity changes are explicit, not removed wholesale to claim payload parity.

### Task 1: Bound R38/R39 public preflight errors

**Files:**
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_reference_run.py`
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_batch_reference_run.py`
- Create: `tools/cyberlateral_dev/project/test_scenario_reference_paths.py`
- Modify: `tools/cyberlateral_dev/docs/SCENARIO_REFERENCE_R38_KO.md`
- Modify: `tools/cyberlateral_dev/docs/SCENARIO_BATCH_REFERENCE_R39_KO.md`

**Interfaces:** unchanged check_saved(Path,Path)/check_batch(Path,Path). Existing CLI IO
codes gain typed public API exceptions; successful outputs/state/formula unchanged.

- [ ] Verify clean exact base; read source/docs and baseline R38 24/R39 23 ledgers.
  Expected: four actual NUL repros raw ValueError, no acquisition/output/worker.
- [ ] Add focused actual-path/metadata/cause/priority/later-error/CLI/permission and
  valid-policy controls. Run new test_scenario_reference_paths.py with -v.
  Expected RED from missing classification, unchanged controls green. Observe actual count.
- [ ] Extract only R38 preflight and wrap only the two calls, classified errors first.
  Expected GREEN new suite and existing47; no source/read/worker on invalid preflight.
- [ ] Compare same saved input at baseline/fixed with exact identity deltas only;
  verify moved preflight/R39 preflight/later-body AST and immutable source/input manifests.
  Expected no numerical/payload differences, truthful orchestration source hashes.
- [ ] Full `dev.py verify` and cloud `ci_verify.py` in external folders.
  Expected all tests/static/compile PASS, canonical public wheel unchanged; actual counts.
- [ ] Commit and fresh completion tests, then one fresh final whole-branch review.
  Expected no unresolved Critical/Important; at most one TDD fix pass, Minor ledgered.
- [ ] Normal scoped push/create/attach PR, actual exact-head CI/artifacts and two-build
  independent feature seal; normal guarded main/private HF/two fresh recoveries.
  Expected no bypass/delete/overwrite/visibility change or vehicle activation; continue.
