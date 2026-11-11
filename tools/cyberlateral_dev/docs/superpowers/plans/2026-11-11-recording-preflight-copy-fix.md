# CORE47 Copy Fix and Scoped Feature Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve CORE46 M1/M2 and publish the exact verified feature without changing main.
**Architecture:** Explicit standard copy hooks delegate to the existing validated constructor; preserve shared memo semantics. Delivery is separately gated by fresh verification and existing scoped workflows.
**Tech Stack:** Existing Python3.12.13/stdlib/unittest and configured Ruff/Ty/Codespell/gh.
**Spec:** `docs/superpowers/specs/2026-11-11-recording-preflight-copy-fix-design.md`

## Global Constraints

- Preserve __new__ guard/CORE46 validation semantics and false permissions.
- No model/reference/F61/Controller/Runtime/CAN/actual input/dt/r execution by the copy API.
- Preserve model/public wheel/fixtures/CI/dependencies; actual r/T2/scale remain null.
- Five fix paths only; preserve prior evidence and host-owned worktrees.
- Feature publication and exactly two scoped dispatches allowed after preflight; main/PR/force/rules bypass prohibited.

## Review Focus

- Invalid declarations must fail before their nested deepcopy hooks execute.
- Memo-supplied invalid copied declarations must be revalidated before a clone is returned.
- Repeated receipts and shared recording/context references must remain aliased in one deepcopy graph.
- Copies must reconstruct counts and false permissions, not copy forged derived flags.
- Copy operations must preserve raw words/signed zero and never execute model steps.

## Task 1: reviewed copy and documentation fixes

**Files:** Modify `integration_tools/offline_recording_preflight.py`, `project/test_offline_recording_preflight.py`, `docs/RECORDING_INPUT_PREFLIGHT_CORE46_KO.md`; create this plan and its spec.
**Consumes:** Existing CORE46 receipt and validated constructor.
**Produces:** `__copy__(self)` and `__deepcopy__(self, memo: dict[int, object])` returning exact validated receipts, plus the executable development import recipe.

- [x] Add copy-specific real-behavior tests and run them against the unchanged implementation; expect failures naming missing reconstruction support, not import/setup errors.
- [x] Commit tests/spec/plan preregistration, then implement only copy hooks and the guide.
- [x] Run focused tests, fresh documented import command, configured owned-path static checks and full dev.py verify with a NEW external output. Expected all tests/compiles/Manifest/wheel/pins PASS; report actual counts.
- [x] Commit verified fixes and record task completion; obtain independent delta review before publication. Fix any important issue with TDD and a green suite.

## Post-task delivery

- [ ] Fresh live main/feature/workflow/permissions check; normal feature push once, no PR.
- [ ] Dispatch only existing DEV/Cloud workflows on the exact head if no automatic feature CI; verify actual run metadata, terminal results and whole artifacts.
- [ ] Check source/ref custody, build two deterministic evidence archives and independently rebuild/verify CRC/Manifest.

Native execution continues under the user's delegation without repeated approval prompts. Existing missing skill helpers use the documented external ledger fallback; finalization state is recorded there rather than changing this frozen plan after review.
