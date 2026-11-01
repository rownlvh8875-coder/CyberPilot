# R34 Scenario Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exact read-only comparison of two saved R33 synthetic batches.

**Architecture:** Bounded owned-byte reader reuses the existing R32 decoder.
A pure typed diff separates input, result, rejection and identity changes.
A separate CLI publishes a portable comparison and private runtime receipt.

**Tech Stack:** Existing CPython3.12.13 stdlib and pinned DEV checks only.

**Spec:** `docs/superpowers/specs/2026-11-01-scenario-regression-design.md`

## Global Constraints

- Public0.3.0 source/API/wheel/imported bytes unchanged; no new dependencies.
- Complete R33 input only;32 cases/8192 samples/512 members/128MiB per bundle.
- No model/Controller/Runtime/F61/CAN or r/dt execution by the comparator.
- Exact typed comparison, no tolerance/fallback/baseline update.
- NEW output outside component/inputs, JSON last, no overwrite.
- Frozen closed gates and null actual r/T2/scale.

## Review Focus

- Correctly rehashed but semantically contradictory records must reject.
- File replacement/symlink/FIFO must not escape owned bounded reading.
- Duplicate scenario IDs and case insertion must not silently misalign results.
- Equal values with changed producer identity must remain visibly distinct.
- Output path/encoding/write failure must not create a false completed comparison.

---

### Task 1: Owned saved-batch reader

**Files:**
- Modify `integration_tools/scenario_report_data.py`: expose bytes-only decoder.
- Create `integration_tools/scenario_compare_input.py`.
- Create `project/scenario_compare_fixture.py`, `project/test_scenario_compare_input.py`.

**Interfaces:**
- Consumes existing R31/R32 canonical records and consistency rules.
- Produces `decode_report(owned: dict[str, bytes]) -> dict`, and
  `read_batch(path: Path) -> dict` with record, per-case records and owned identities.
- Error class `CompareError(code: str)` used by later tasks.

- [x] Write preserved-fixture reader tests: valid complete/rejected/mixed input,
  nested hashes, raw binding, canonical/count/gate consistency, missing/extra/
  corrupt/unsafe members, per-file/aggregate limits, old identity metadata only.
- [x] Run targeted unittest discovery; expect failure for missing reader/decoder.
- [x] Implement safe reader and minimal decoder extraction, without model imports.
- [x] Run reader tests and full component suite; expect all PASS.
- [x] Commit reader, fixtures/tests and design/plan.

### Task 2: Exact semantic diff

**Files:**
- Create `integration_tools/scenario_compare_data.py`.
- Create `project/test_scenario_compare_data.py`.

**Interfaces:**
- Consumes `read_batch` dictionaries.
- Produces `compare_batches(baseline: dict, candidate: dict) -> dict`.

- [x] Write tests with literal changed field/first sample/count expectations:
  exact match, request/input changes, final command/state/clip trace changes,
  type/signed-zero differences, changed rejection/status, missing raw input,
  added/removed cases, duplicate IDs, metadata change flags and256-detail truncation.
- [x] Run targeted tests; expect failure for missing comparison implementation.
- [x] Implement typed traversal, ordered case alignment and portable result record.
- [x] Run targeted and full suite; expect all PASS.
- [x] Commit pure diff and tests.

### Task 3: CLI, publication and developer guide

**Files:**
- Create `integration_tools/scenario_compare_run.py`, `tools/scenario_compare.py`.
- Create `project/test_scenario_compare_cli.py`, `docs/SCENARIO_REGRESSION_R34_KO.md`.
- Update component README with bounded usage link.

**Interfaces:**
- Consumes `read_batch`, `CompareError`, `compare_batches`.
- Produces `run_comparison(baseline: Path, candidate: Path, output: Path) -> dict`.
- CLI exit0 MATCH /1 DIFFERENT /2 rejected; isolated private pycache.

- [x] Write real CLI tests for0/1/2, deterministic portable output/full manifests,
  no forbidden imports/model execution, output collision/ancestry/encoding,
  partial write failure and no marker, private receipt separation, help/options.
- [x] Run targeted tests; expect failure for missing CLI.
- [x] Implement output preflight, receipt/source identity, exclusive publication.
- [x] Add Korean usage, exactness/limits/unchanged gates and no auto-baseline update.
- [x] Run full dev.py verify, including Ruff/Ty/Codespell/compile/wheel reproducibility.
- [x] Run two independent comparisons of saved complete batches; portable bytes match.
- [x] Commit feature and documentation after successful verification.

## Completion

One fresh-context whole-branch review after all tasks. Resolve important findings
with RED→GREEN tests and a full green gate. Preserve local commits; do not merge,
push, publish or change CI/branch policy automatically.

## Approved follow-up: review test coverage and GitHub PR

The user approved the proposed follow-up: close the semantic-rejection test
weakness, rerun full verification, push the named feature branch, create a PR
against main and verify its CI. This specifically authorizes the feature push/PR;
it does not authorize main merge, workflow/policy bypass or vehicle activation.

### Task 4: Protect later semantic checks independently

**Files:** `project/scenario_compare_fixture.py`,
`project/test_scenario_compare_input.py`, `docs/SCENARIO_REGRESSION_R34_RESULTS.md`.

**Interfaces:** Existing `edit_batch` keeps its deliberate root-only refresh.
Add `rehash_portable(root)` for test fixtures, using the existing generated member
inventory, not possibly corrupted paths in BATCH.json. No production file changes.

- [x] Reproduce the review: bypass only the aggregate record check or only the
  raw-to-typed check in temporary in-memory functions; the old tests still pass.
- [x] Fully rehash root/portable records for count/gate contradictions and assert
  COMPARE_RECORD. Preserve distinct schema/path/raw-digest rejection codes.
- [x] Align every claimed raw digest in a deliberately inconsistent R31 fixture,
  then ensure decode_report succeeds but batch raw-to-typed validation rejects.
- [x] Observe strengthened tests fail under the two specific mutations, restore
  the real guards and observe targeted tests pass. Mutations never reach Git.
- [x] Run full dev.py verify including all tests/static/compile/wheel checks.
- [ ] Commit coverage/docs, perform a normal non-force feature push, create a PR
  and inspect exact-head scoped CI. Preserve all previous worktrees and gates.
- [ ] Do not merge main or activate vehicle/runtime code.

CI routing follows the prior R33 PR: a `[skip ci]` commit avoids automatic generic
openpilot build/replay jobs, then the existing scoped offline workflow is explicitly
dispatched on the exact named feature head. No required checks or repository rules
are changed or bypassed; any outstanding policy/check remains visible in the PR.
