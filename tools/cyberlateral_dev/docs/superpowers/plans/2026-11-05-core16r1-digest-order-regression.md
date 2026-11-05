# CORE16-R1 Digest Order Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close CORE16's deferred digest-before-output-metadata regression-test gap.
**Architecture:** Strengthen the existing bad-second-digest test with an output
preflight tripwire. Prove it detects a reordered publisher using an in-memory AST
mutation, without writing or changing any product source bytes.
**Tech Stack:** Existing Python3.12/stdlib/venv; no installs.
**Spec:** ../specs/2026-11-05-core16-archive-workflow-design.md

## Global Constraints

Base c6001267cbfc5bd567fd24125c7019ab85fcc7e6. Product source/API/CLI/output
bytes unchanged. Both full digests before caller-path inspection. No new runtime
functionality, extraction, model/reference/F61/r/dt/Controller/Runtime/CAN/vehicle
activation. Actualr/T2/scale=null; R_BUDGET UNRESOLVED, Static Gate FAIL.
Preserve source/refs/evidence. Local commits only; no merge/push/PR/CI/HF writes.
User delegated ordinary next-step choices, no routine approval pauses.

## Review Focus

1. Reordering output metadata preflight before SHA validation must fail the improved test.
2. The control/base test must pass the same deliberate reorder, demonstrating the old gap.
3. Correct code still raises role-qualified RIGHT digest error without caller I/O/output.
4. Mutation is process-local AST only; every product file remains byte/mode identical.
5. Test-only change preserves CORE16 JSON/Markdown/receipt/files and all closed gates.

### Task1: regression coverage closure

**Files:** Modify project/test_core_sequence_archive_workflow.py only; create this plan.
**Interfaces:** Existing test method and publisher signatures unchanged. Patch the
module's `_output` with an AssertionError tripwire alongside the os.open tripwire.
No production mocking or changes outside this negative-validation test.

- [ ] Focused baseline25 PASS on clean base. Commit plan and external brief/BASE ledger.
- [ ] External mutation harness swaps exactly the `_preflight`/`target=_output` AST
  statements of `publish_archive_report`, in a child process only. Run the old
  single test against mutation: expected1test PASS (demonstrates prior blind spot).
- [ ] Strengthen existing test with `_output` tripwire. Run same mutant: expected
 1test FAIL due output path inspection before digest rejection. No source mutation.
- [ ] Run unmutated focused25tests: PASS. No new test methods; test count unchanged.
- [ ] Fresh full `python -B dev.py verify --output <NEW external>`:
  expected1330tests/278compiles/Ruff/Ty/Codespell PASS, frozen wheel unchanged.
- [ ] Independent2runs on preserved CORE16 ZIP inputs: old/new output artifacts and
  receipts byte-identical; direct public API bad-digest preflight proves no path
  access. Source registry572/prior570 and old refs18 unchanged. Commit test change.
- [ ] One fresh final read-only reviewer; one Critical/Important TDD fix pass if needed,
  minors deferred, no rereview. Exhaustive rulings/costs in ledger and final response.
- [ ] Validate gate Manifest/cloud consumer/source custody; Korean result/report/ZIP/
  checksum. Preserve feature branch/worktree/evidence, no external publication.
