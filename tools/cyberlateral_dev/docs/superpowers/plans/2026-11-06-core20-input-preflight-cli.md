# CORE20 Preflight CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CORE19 usable as a strict standalone saved-input validation command.

**Architecture:** Parse before project imports under bytecode suppression, temporarily select component sources, invoke CORE19 once and emit its unchanged canonical receipt. Separate exit0/1 semantics from fixed exit2 failures. No cache infrastructure or existing API changes.

**Tech Stack:** Existing CPython3.12.13 Linux stdlib, unittest, Ruff/Ty/Codespell, unchanged wheel.

**Spec:** [design](../specs/2026-11-06-core20-input-preflight-cli-design.md)

## Global Constraints

- Exactly one nonempty --input-root, no abbreviated/duplicate/run/output/policy options.
- Keep CORE19 receipt bytes/semantics and all existing algorithms/CLI/wheel unchanged.
- Bytecode suppression before parsing through stdout; restore sys.path and bytecode flag; leave pycache_prefix/temp settings untouched.
- No temp/cache discovery/allocation. Caller stdout is not an atomic file publisher.
- Numeric validation NONZERO; command model/reference/F61/actualr-dt/Controller/Runtime/CAN0.
- Actual r/T2/scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual activation forbidden.
- Retain branch/evidence, no merge/push/PR/CI/HF writes.

## Review Focus

- Current compatible versus historical DIFFERENT/REJECTED: exact CORE19 JSON, correct0/1 exit, not saved status.
- Invalid/duplicate/abbreviated/policy options and help: no project import or caller input access.
- Cold first main with bytecode enabled and prefix/temp settings under input: no input/cache writes or temp probes; globals restored.
- Import/API/serialization/stdout failures: fixed exit2, no early receipt; short writes progress, zero/negative writes fail closed.
- Invocation from unrelated cwd, read-only/space-containing input paths,3captures, no model/reference/producer/F61 execution.

### Task1: Standalone preflight CLI

**Files:** Create `tools/core_sequence_input_preflight.py`, `project/test_core_sequence_input_preflight_cli.py`, `docs/CORE_SEQUENCE_INPUT_PREFLIGHT_CLI_CORE20_KO.md`; modify guide links in `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`, `docs/CORE_SEQUENCE_INPUT_PREFLIGHT_CORE19_KO.md`.

**Interfaces:**
- Consumes unchanged CORE19 `preflight_saved_sequence(Path)->dict`, `InputPreflightError.code`, canonical serializer.
- Produces `main(argv=None)->int` with spec exit0/1/2, fixed usage/failure diagnostics and no new receipt fields.

- [ ] Step1: Add real CLI parity and failure/cold-bootstrap tests covering every Review Focus item; literal expected statuses, independent CORE19 API comparison only for unchanged wrapper bytes.
- [ ] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_input_preflight_cli.py' -v`; Expected: new methods FAIL because CLI file is absent.
- [ ] Step3: Implement minimal parser/main, full-main bytecode suppression/restoration, source-path restoration, fixed diagnostics and write-progress loop.
- [ ] Step4: Run same focused command; Expected: all new methods PASS. Add Korean usage/exit/limitations guide and discoverability links.
- [ ] Step5: Run `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`; Expected: prior1419 + actual new methods PASS;288 compiles; Ruff/Ty/Codespell PASS; frozen wheel unchanged.
- [ ] Step6: Two independent acceptance rounds on preserved CORE17 case packages: API/direct CLI/import-blocked CLI receipt equality,0/0/1 exits,3captures, cold prefix/temp overlap success and bad-input failure, no mkdir/bytecode/model work. Expected: byte-identical summaries, input bytes/layout/modes unchanged, no fixtures generated.
- [ ] Step7: Verify source596/protected588/refs23, local commit, one final fresh whole-branch review; independent unsigned ZIP verification. Expected: clean branch, no unresolved Critical/Important, no remote writes.
