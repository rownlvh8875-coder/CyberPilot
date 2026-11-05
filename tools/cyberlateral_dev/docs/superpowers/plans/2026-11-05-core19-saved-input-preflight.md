# CORE19 Saved Input Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revalidate closed saved synthetic inputs through CORE3~5 without executing the model.

**Architecture:** One new read-only DEV API consumes CORE9 captured records, reconstructs owned declarations and applies existing CORE5 rules. Keep saved outcomes separate from current input compatibility; expose no prepared/calculator args.

**Tech Stack:** Existing CPython3.12.13 Linux stdlib, unittest, Ruff/Ty/Codespell; unchanged public wheel.

**Spec:** [design](../specs/2026-11-05-core19-saved-input-preflight-design.md)

## Global Constraints

- Existing CORE3~18 algorithms, readers and CLI behavior unchanged; no dependency changes.
- New API only, no CLI/vehicle reader/replay/F61/nominal-time fallback.
- Exact3 captured files; stored status is not current semantic outcome.
- Numeric decoding/quantization NONZERO; new model/reference/actualr-dt/F61 execution0.
- Actual r/T2/vehicle_scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL.
- Retain external evidence/local branch; no merge/push/PR/CI/HF writes.

## Review Focus

- Coherent checksummed MATCH with invalid dyadic/request/active/override input must reject semantically without replay.
- Valid input labeled REJECTED and valid DIFFERENT data must not be mistaken for incompatible inputs.
- Float overflow/underflow/noncanonical encodings must not round into accepted zero; signed zero stays exact.
- Single bounded capture, no mutation and no model/reference/producer/F61 execution, including failure paths.
- Late invalid input and unexpected helper failures must not return partial prepared inputs or fake compatible success.

### Task 1: Saved synthetic semantic preflight

**Files:** Create `integration_tools/core_sequence_input_preflight.py`, `project/test_core_sequence_input_preflight.py`, `docs/CORE_SEQUENCE_INPUT_PREFLIGHT_CORE19_KO.md`; modify `README.md` and `docs/CORE_DEVELOPMENT_BACKLOG_KO.md` links only.

**Interfaces:**
- Consumes unchanged `read_saved_sequence_records(Path) -> dict` and `prepare_model_input(previous,current,context)`.
- Produces `preflight_saved_sequence(Path) -> dict` and `InputPreflightError.code` exactly as specified; no output dataclasses escape.

- [ ] Step1: Write real-package tests for the five Review Focus items plus checksum/path rejection, snapshot/capture counts, flags, deterministic JSON, bounds and time ordering. Expected values are literals, not computed by the new API.
- [ ] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_input_preflight.py' -v`; Expected: all new methods FAIL because the module is absent.
- [ ] Step3: Implement the one module, CORE9 capture→owned decoding→CORE5 preflight. Exact float re-encoding check; fixed indexed diagnostics; no caller values in errors.
- [ ] Step4: Run same focused command; Expected: all new methods PASS. Add Korean guide and discoverability/backlog links.
- [ ] Step5: Run `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`; Expected: all prior1388 + actual new test count PASS;286 compiles; Ruff/Ty/Codespell PASS; wheel unchanged.
- [ ] Step6: Two independent subprocess acceptance rounds on preserved three-case CORE17 records with import/execution/read/write guards. Expected:3reads/case, compatible/compatible/rejected-driver, no fixture/model/reference work, identical summaries, old input bytes/modes unchanged; coherent negative copies classified correctly.
- [ ] Step7: Verify source591/protected584/refs22, commit locally, one fresh final whole-branch review and one TDD correction pass if required; independently verify unsigned evidence ZIP. Expected: clean branch, no unresolved Critical/Important, no publication.
