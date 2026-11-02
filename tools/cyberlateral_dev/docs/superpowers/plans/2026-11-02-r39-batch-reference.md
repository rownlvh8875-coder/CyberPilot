# R39 Batch Reference Implementation Plan

> **For agentic workers:** use superpowers:executing-plans inline. No implementer delegation; one fresh final reviewer.

**Goal:** one command independently checks every complete saved batch case and clearly accounts for rejected inputs.
**Architecture:** bounded R34-owned input snapshot, existing complete-batch validation, existing R38 workers, deterministic aggregation/publication.
**Tech Stack:** Python3.12.13, stdlib frontend, locked NumPy2.5.3 independent workers, unittest/Ruff/Ty/Codespell.
**Spec:** `../specs/2026-11-02-r39-batch-reference-design.md`

## Global Constraints

Base dc3cf32dc7d566c5f24420985f99a092e5b71dae. No imported/public/wheel arithmetic changes.
New model executions0. Reference/helper work NONZERO. No added dependencies.
Actual r/T2/scale null; R_BUDGET UNRESOLVED, Static Gate FAIL; no F61/vehicle/CAN/native activation.
User delegated routine decisions and opted out of repeated approval. No remote publication in this task.

## Review Focus

- Owned snapshot must be the only worker input even if original files change after validation.
- Rejected-only or unavailable raw inputs must not turn into vacuous MATCH.
- Late corrupt cases must reject before any independent computation.
- Worker failure and partial publication must not masquerade as numerical DIFFERENT or successful zero work.
- Cold CLI cannot import public model/whole Controller, follow receipts or reveal private paths.

## File map

- Create `integration_tools/scenario_batch_reference_run.py`: guards, ownership, per-case orchestration, result aggregation/exclusive writes.
- Create `integration_tools/scenario_batch_reference_summary.py`: Korean path-free summary of classified aggregate.
- Create `tools/scenario_batch_reference_check.py`: isolated CLI and exact exit mapping.
- Create `project/test_scenario_batch_reference.py`: real fixtures/reference checks, classification and safety regressions.
- Create `project/test_scenario_batch_reference_cli.py`: real CLI, deterministic artifacts and cold import barrier.
- Create `docs/SCENARIO_BATCH_REFERENCE_R39_KO.md`; link from README/current quickstart.

### Task1: complete saved batch reference checker

**Consumes:** R34 `_owned_files(path)`/`read_batch(path)`, R38 `check_saved(input_path, output_path)` and `_identity(root)`, existing fixture builders.
**Produces:** `check_batch(input_path: Path, output_path: Path) -> dict`, `BatchReferenceError.code`, `exit_code(record: dict) -> int`, `summary(record: dict) -> bytes`; CLI and documented artifact format.

- [x] Run unchanged baseline unittest discover: expected603/OK.
- [x] Write tests asserting missing runner/CLI, complete/mixed/rejected classification, DIFFERENT1, guards and worker errors; run them RED on absent implementation.
- [x] Implement runner/summary/CLI using existing parser/validators/reference, with no public model imports.
- [x] Run focused tests GREEN; add focused RED→GREEN tests for owned snapshot, source/runtime checks, incomplete input and error precedence as needed.
- [x] Run actual CLI on R35 mixed batch twice: expected MATCH_WITH_INPUT_REJECTIONS,6matched/3confirmed/38reference steps/new model0, output bytes identical for same input.
- [x] Run coherent wrong saved-value copy: expected DIFFERENT/exit1, exact first field; corrupted late batch rejects2 before references.
- [x] Add Korean CLI/accounting/scope documentation and README/current guide links. No wheel option changes.
- [x] Run full `dev.py verify --output <new audit gate>`: all tests/static checks/own compiles/wheel pass; report observed counts.
- [ ] Fresh independent final review of whole change. Fix Critical/Important via tests first, whole suite green; ledger deferred minors.
- [ ] Preserve tested local branch; hand off exact changes/results/commands. Do not push/merge without further task scope.

No speculative UI or policy work. One feature task because reader/runner/summary/CLI form a single independently useful deliverable.
