# CORE32 Closed Reference Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox tracking.

**Goal:** Run the six fixed CORE30/31 regression audits with one explicit command.
**Architecture:** Fixed ordered orchestration, detached validated receipts, exact aggregate summary;
minimal --run descriptor CLI. No change to old auditors, model, arithmetic or references.
**Tech Stack:** Existing Python3.12.13/stdlib/component .venv; no installs.
**Spec:** [design](../specs/2026-11-10-core32-closed-reference-suite-design.md).

## Global Constraints

BASE2803a73b5375267a84700c0e0a454532e96fe92c,host-owned linked checkout/new named branch.
Old modifications only README/backlog/CORE31 guide links; preserve all other source/refs/evidence.
Actual r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL; no actual/F61/Controller/Runtime/CAN/r/dt.
No arbitrary intake, no file publication, no merge/push/PR/CI/HF writes; synthetic work nonzero.

## Review Focus

Observed DIFFERENT/REJECTED vs audit mismatch: baseline suite0 must retain4/1/1 counts and19steps.
Early mismatch vs late operational failure: process all normal verdicts but never emit partial success on failure.
Backend contract drift: bool/int, forged flags/gates/reference/case, detail counts/truncation and aliased receipts.
Cold CLI and output failures: syntax/help before project work, restore globals, partial/failed writes never success.
Coverage/authority: fixed six cases and reported counters, not runtime attestation or generic/vehicle qualification.

## Task 1 — suite API and command

Create integration_tools/core_reference_suite.py,tools/core_reference_suite.py,
project/test_core_reference_suite.py,project/test_core_reference_suite_cli.py,
docs/CORE_REFERENCE_SUITE_CORE32_KO.md and spec/plan. Modify the three allowed guide links.
Interfaces: run_reference_suite()->dict,ReferenceSuiteError.code; CLI main(argv=None)->int.

- [ ] Commit spec/plan; fresh CORE30/31 focused baseline. Expected29/36PASS.
- [ ] Write API/CLI tests before modules; run new file pattern. Expected missing-feature assertions RED.
  Test real six-case order/once, exact receipts/all counters, model19/quantizer40, observed M/D/R
  separate, all mismatches processed, malformed backend/type/flag/gate/status/count failures,
  prefix failure/no partial success, detached snapshots, BaseException, readonly refs/no temp,
  deterministic canonical JSON. Test CLI --run only/syntax/help/cold imports/global restoration,
  exact API parity/exit1, known/unknown failures, short/partial/nonpositive/dev-full/help/stderr failures.
  These cover every Review Focus line.
- [ ] Implement minimal API/CLI; run new tests. Expected allPASS; legacy audit/model unchanged.
- [ ] Add Korean command/semantics/limits guide and three links; run new+CORE30/31 regressions.
  Expected allPASS and all local links resolve.
- [ ] Fresh dev.py verify --output NEW_EXTERNAL. Expected old+new tests/static/wheelPASS,
  own325compiles, frozen wheel unchanged. Record actual new/full test counts.
- [ ] Independently reproduce API/coldCLI/directCLI, mutation and failed stdout twice using prior
  sealed receipts. Expected byte-identical corresponding outputs; normal19models/40quantizers,
  mutation19/40 with19paths across5audits, no writes/cache/temp inside guarded calls.
  Validate source671/protected661/ref35,DEV manifest/cloud consumer and prior seal custody.
- [ ] Commit/task-done verification; one fresh whole-range review, all exclusions ruled; one TDD
  fix pass+full gate for Critical/Important if needed. Seal unsigned ZIP and independently verify.
