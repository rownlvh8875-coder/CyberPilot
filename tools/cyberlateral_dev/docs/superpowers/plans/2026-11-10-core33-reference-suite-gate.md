# CORE33 Reference Suite Development Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox tracking.

**Goal:** Require two exact CORE32 CLI receipts in dev.py verify.
**Architecture:** Pure byte-pin summary plus existing subprocess runner, early failure,
four retained artifacts and a nested DEV summary. No new numerical algorithm.
**Tech Stack:** Existing CPython3.12.13/stdlib/locked .venv; no installs.
**Spec:** [design](../specs/2026-11-10-core33-reference-suite-gate-design.md).

## Global Constraints

BASEeee243da8c21d6f50effc17ff13d5077c5bc9325;new branch in existing linked worktree.
Exact normal receipt10463bytes/SHA6dba6db52bbaf8a5e602a4c2266a2e29908629f894683c67bcdb11adaf32dead.
Protected old source except verify.py/README/backlog/CORE32guide; prior refs/evidence preserved.
Actual r/T2/scale=null,R_BUDGET UNRESOLVED,StaticGateFAIL,no actual/F61/Controller/Runtime/CAN/r/dt.
Synthetic work nonzero; no baseline regeneration,merge/push/PR/CI/HF writes.

## Review Focus

Pinned normal bytes versus merely equal outputs: identical corruption or reformatted JSON must fail, not bless a new baseline.
First/second subprocess or receipt failure: stop without retry, preserve existing logs/first stdout and never publish final success.
Invocation semantics: exactly two explicit -I -B --run commands with development-tree scope and reported38 distinct from total work.
Publication/collision boundary: preflight all four names, exclusive writes, correct hashes and final Manifest inclusion without overwrite claims.
Compatibility/authority: nested summary and current cloud consumer work without changing old formulas/references/gates or granting vehicle authority.

## Task 1 — explicit closed CLI regression in DEV

Create integration_tools/reference_suite_gate.py,project/test_reference_suite_gate.py,
docs/CORE_REFERENCE_GATE_CORE33_KO.md and spec/plan.
Modify integration_tools/verify.py plus three guide links.
Consumes CORE32 --run canonical stdout and _run command/log boundary; produces
reference_suite_pair_summary(first,second)->dict and verify_reference_suite(...)->dict.

- [ ] Commit spec/plan and read task brief; fresh CORE32(40)/dev command(6) baselines.
- [ ] Write focused tests before implementation: pin normal child output with independent
  fixed SHA/size; reject different/identical-corrupt/empty/type/reformat/count/gate bytes;
  validator model/quantizer0; real CLI pair/canonical receipts; command args/cwd/order;
  collision no-work/no-overwrite; first/second/invalid receipt failure preservation;
  BaseException; dev CLI error2/no success artifacts. Run new pattern,expected missing-feature RED.
- [ ] Implement pure summary and verify.py integration minimally; run focused tests,expected PASS.
- [ ] Add guide/links and run focused+CORE32+dev regressions,expected all PASS.
- [ ] Fresh dev.py verify --output NEW_EXTERNAL,expected1890+actual new tests,327own
  compiles/static/frozenwheelPASS,98Manifest entries,nested summary exact and receipts pinned.
- [ ] Independent two-run helper/parent profile and saved fullgate receipts,expected exact
  bytes/summary and each pair38 reported models; parent validator0,additional unit/gate work
  nonzero/unaggregated. Exercise real child exit1/2/fake valid-exit0 corruption in isolated
  copied scripts without modifying owned source. Source676/protected667/ref36 preserved.
- [ ] Commit/task-done verification; fresh whole-range review with exclusions ruled.
  One RED/GREEN fix pass+whole gate if needed; unsigned ZIP and independent seal check.
