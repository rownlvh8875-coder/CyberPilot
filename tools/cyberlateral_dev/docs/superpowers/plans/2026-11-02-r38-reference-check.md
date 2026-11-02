# R38 Reference Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently check complete saved declared-synthetic R31 results without new public-model execution.

**Architecture:** Reuse R32's preflight; a fresh worker carries independent reference state and returns expected rows. Parent compares all typed fields and publishes a deterministic bounded report. Public0.3.0 and existing R31/R34 remain unchanged.

**Tech Stack:** CPython3.12.13, existing NumPy2.5.3 DEV group, stdlib unittest/subprocess/AST; no new dependency.

**Spec:** `../specs/2026-11-02-r38-reference-check-design.md`.

## Global Constraints

- Complete saved R31 input only; no arbitrary messages, actual vehicle input or policy fields.
- Exact canonical comparison; no tolerance/defaults/coercion/clamp or baseline auto-update.
- Reference uses only its own preceding state. Public model executions0, reference/helper counts explicit.
- Isolated worker -I/-B/private cwd/cache; current source identity before/after.
- No public src/reference fixtures/lock/workflow changes; Commit/Push/CI NOT_RUN in this request.
- Keep all real-world gates/unknown values unchanged.

## Review Focus

- Consistently falsified saved output: checksums/duplicate fields agree but independent arithmetic must detect it.
- Reference state accidentally derived from model: faults in later state must remain detectable.
- Late malformed sample or source mismatch: no prefix helper work/partial success.
- Source/source receipt paths supplied by input: metadata only, never followed or imported.
- Reference unavailable or output collision: no MATCH/fallback/overwrite.

### Task 1: Independent sequence and checker

**Files:** create `project/scenario_reference.py`, `tools/scenario_reference_worker.py`, `integration_tools/scenario_reference_run.py`, `project/test_scenario_reference.py`.

**Interfaces:** `reference_values(spec:ScenarioSpec)->dict` yields complete rows/final_state/helper counts; `check_saved(input_path:Path,output_path:Path)->dict` consumes complete saved R31 bytes and emits canonical report.

- [ ] Write failing tests for fixed sign/resumed, R35 cases, consistent arithmetic mutations, late malformed input, identity/failure/output guards and deterministic report.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p test_scenario_reference.py -v`; expected missing-feature assertions.
- [ ] Implement independent sequence after full validation, fixed isolated worker, complete preflight/source checks, typed comparisons and bounded exclusive publication.
- [ ] Run that test command; expected all PASS. Inspect counts0 model / N reference / N limiter+fault, and field differences.
- [ ] Record tested diff in external ledger; do not commit or change unrelated files.

### Task 2: CLI and discoverability

**Files:** create `tools/scenario_reference_check.py`, `project/test_scenario_reference_cli.py`, `docs/SCENARIO_REFERENCE_R38_KO.md`; update component README/current guide only.

**Interfaces:** consumes Task1 `check_saved`; CLI exit0 MATCH/1 DIFFERENT/2 error, two required Path args; no native/public imports in fresh checker process.

- [ ] Write/run failing real CLI tests for exact exit/output, public-model import barrier, invalid args and no overwrite.
- [ ] Implement narrow wrapper/private cache, document saved-input requirement and reference NONZERO vs model0, no broader approval.
- [ ] Run both new test files; expected all PASS. Run actual producer→checker twice plus consistent mutation and all R35 cases; inspect complete reports/Manifests.
- [ ] Run `dev.py verify` with existing private uv/Python/locked offline environment and fresh external output. Expected whole suite/static checks/own compile and unchanged wheel identity PASS; report observed counts.
- [ ] Fresh whole-change review, TDD-fix Important/Critical findings in one pass, rerun whole gate. Preserve workspace/artifacts; no external publication in this request.

## Pre-flight self-review

Task2 consumes exactly Task1 check_saved and ReferenceCheckError. Saved input errors retain REPORT_* codes; reference/runtime/source/output failures use REFERENCE_* codes. Review Focus is covered by Task1 mutation/late-error/identity guards and Task2 fresh-process/CLI guards. No public arithmetic is reimplemented or edited.
