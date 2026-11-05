# CORE18-R1 Cache Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep inspection CLI cache writes outside saved input regardless of user temp settings.

**Architecture:** Validate CLI SHA/path prerequisites under suppressed bootstrap bytecode. Allocate the private cache with explicit `/tmp` parent, reject overlap/unusable parent without fallback, restore Python flags on every path. Leave the inspection API unchanged.

**Tech Stack:** Existing CPython3.12.13 stdlib, unittest, Ruff, Ty, Codespell.

**Spec:** [design](../specs/2026-11-05-core18r1-cache-isolation-design.md)

## Global Constraints

- Configured CPython3.12.13 Linux; no dependencies or frozen-wheel changes.
- Explicit `CACHE_PARENT = Path('/tmp')`; no implicit temp discovery/fallback.
- Preserve API/receipt/comparison semantics, prior source outside three allowed edits, all old refs.
- No F61/model/reference/vehicle execution by inspection or independent acceptance.
- Actual r/T2/vehicle_scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL.
- External evidence retained; no merge/push/PR/CI/HF writes.

## Review Focus

- Cached tempfile.tempdir and all three temp environment variables overlap input: success without any input mkdir.
- Implicit gettempdir probe: never invoked, including with bytecode enabled initially.
- Equal/descendant/missing/non-directory cache parent: fail closed before allocation/data reads.
- Malformed second SHA or absent input: no cache allocation; SHA checks precede caller metadata.
- Bootstrap/cleanup/stdout errors: restore both Python globals, never publish a receipt before cleanup.

### Task 1: CLI cache boundary

**Files:**
- Modify: `tools/core_sequence_run_inspect.py`
- Test: `project/test_core_sequence_run_inspect.py`
- Modify: `docs/CORE_SEQUENCE_RUN_INSPECT_CORE18_KO.md`

**Interfaces:**
- Consumes: unchanged `inspect_archived_run(Path, str, str) -> dict`, `RunInspectError.code`, SHA `_preflight`, suite `_path`.
- Produces: same `main(argv=None) -> int`, exit0 canonical receipt or exit2 fixed rejection.

- [ ] Step 1: Add seven real-CLI regression methods covering every Review Focus item; preserve all27 existing methods. TemporaryDirectory/gettempdir tripwires prohibit side effects, not substitute successful inspection.
- [ ] Step 2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_run_inspect.py' -v`; Expected: new methods FAIL against old CLI for the documented cache/bootstrap/order defects.
- [ ] Step 3: Implement suppressed bootstrap, SHA/path preflight and explicit cache allocation, restoring flags in finally; preserve short-write stdout behavior.
- [ ] Step 4: Run same focused command; Expected: all34 tests PASS. Update Korean guide for temp policy and fixed failure diagnostics.
- [ ] Step 5: Run `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`; Expected: full DEV tests,284 own compiles, Ruff/Ty/Codespell PASS, frozen wheel unchanged.
- [ ] Step 6: Repeat preserved CORE17 acceptance twice without fixture generation, plus independent temp-overlap/import suppression/read-count subprocess probe. Expected: old receipt bytes identical,14 reads/success,0 forbidden work, input bytes/modes/layout unchanged.
- [ ] Step 7: Commit CLI/tests/guide. Expected: clean `fix/core18-cache-isolation`, two local commits from24986de81 including plan commit, no external publication.
- [ ] Step 8: Fresh whole-branch review, disposition every finding and declined judgment, independent sealed ZIP verification. Expected: no unresolved Critical/Important; preserve ledger, source custody and evidence.
