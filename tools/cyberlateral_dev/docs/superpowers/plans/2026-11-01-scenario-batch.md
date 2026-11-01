# R33 Scenario Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, task by task. Steps use checkbox syntax.

**Goal:** Independently run explicitly named synthetic scenarios and publish one result index.

**Architecture:** Bounded preflight owns bytes; sequential isolated existing CLI workers produce data and reports. Static aggregate output marks completion last.

**Tech Stack:** Python3.12.13 stdlib, existing uv/test/static tool pins.

**Spec:** `docs/superpowers/specs/2026-11-01-scenario-batch-design.md`

## Global Constraints

- 1..32 explicit inputs; at most8192 valid samples; existing R31 schema unchanged.
- New exclusive output, cooperative filesystem scope, no overwrite/rollback.
- Public0.3.0/API/wheel/arithmetic and vehicle gates unchanged.
- Fresh producer/report workers; renderer never imports/runs model.
- No real vehicle/F61/native execution, no actual r/dt/T2/scale.
- No dependencies, main merge, unrelated source edits or browser-policy bypass.

## Review Focus

- Duplicate scenario IDs and hostile filenames must never control output paths.
- Input changes after preflight must not change worker-consumed bytes.
- All-invalid and mixed input lists must report every file without false PASS.
- Late worker/write failure must not publish a completion marker or overwrite.
- Portable equality must exclude environment-bearing receipts/manifests/logs.

## Task 1: Owned input preflight

**Files:** create `integration_tools/scenario_batch_input.py`, `project/test_scenario_batch_input.py`.

**Interfaces:** `prepare_batch(inputs: list[Path], output: Path) -> list[BatchInput]`;
frozen record with source_path, label, raw bytes|None, digest|None, spec|None,
rejection_code|None. `BatchError` has stable code.

- [ ] Write tests for output-first rejection, count/duplicate/total-step limits,
  bounded regular reads, all input schema checks, owned byte snapshots, same IDs.
- [ ] Run discover `test_scenario_batch_input.py`; see missing-feature failure.
- [ ] Implement preflight without model imports, no output writes.
- [ ] Run same discovery; all pass. Commit tested task with `[skip ci]`.

## Task 2: Orchestration, static index and CLI

**Files:** create `integration_tools/scenario_batch_run.py`,
`scenario_batch_html.py`, `tools/scenario_batch.py`, `project/test_scenario_batch_cli.py`.

**Interfaces:** consumes Task1 records; `run_batch(inputs: list[Path], output: Path) -> dict`;
`render_index(record: dict) -> bytes`. CLI maps completed/rejected/request failure to0/1/2.

- [ ] Write failing tests: exact sign/resumed outputs, independent driver/inactive
  sequences, mixed/all-invalid, duplicate IDs, hostile filename links, snapshots,
  manifests/repeated portable equality, worker fault, marker-last write fault.
- [ ] Run discovery `test_scenario_batch_cli.py`; see missing CLI/function failure.
- [ ] Implement fresh sequential worker reuse, static index, exclusive completion.
- [ ] Run both batch files plus scenario/report regression tests; all pass.
- [ ] Run full `dev.py verify --output NEW`; tests/static/compile/wheel pass;
  commit tested task with `[skip ci]`.

## Task 3: Guide, fresh export, review and delivery

**Files:** add `docs/SCENARIO_BATCH_R33_KO.md`, update component README;
external audit workspace stores verification/review evidence.

**Interfaces:** document exact CLI, exit/status/partial/snapshot/count scope from
Task2. No historical R30 or old sealed evidence rewrites.

- [ ] Document command, generated tree, mixed-error behavior and fixed boundaries.
- [ ] Run Ruff/Ty/Codespell/diff checks and commit documentation.
- [ ] Export committed component with scoped workflow/root README into fresh
  external folder; locked sync, full gate, two exact example batches; compare
  portable manifests and verify all recursive checksums.
- [ ] Request one fresh whole-branch review against baseline8a6d156b4 and spec;
  disposition every finding; Important/Critical fixes in one TDD/full-green pass.
- [ ] Normal push new feature branch; new Draft PR, attach it; scoped CI dispatch
  at exact HEAD; read resulting summary and checksum artifact. No main merge.
- [ ] Final concise handoff: executable change, verified counts, Draft PR,
  remaining actual visual check, fixed vehicle gates and any rulings/minors.
