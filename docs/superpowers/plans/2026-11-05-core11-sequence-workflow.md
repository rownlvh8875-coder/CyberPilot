# CORE11 Closed Sequence Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native offline execution without repeated approval questions.

**Goal:** One explicit check/run command integrates closed execution,saved inspection,
and optional saved baseline comparison without reopens or hidden new computation.
**Architecture:** Lazy CORE8 producer;CORE9 owned capture;CORE10 private pure comparison
extraction;thin JSON stdout CLI and testable in-process APIs.
**Tech Stack:** Existing CPython3.12.13/Linux/stdlib/unittest/Ruff/Ty/Codespell.
**Spec:** docs/superpowers/specs/2026-11-05-core11-sequence-workflow-design.md

## Global Constraints

- Baseacd03844f6d227dcf79a191dc2da91b94a38e58f,existinghostlinkedworktree/localbranch.
- check imports/runs no producer/model;run named3cases only,lazy afterbaselinevalidation.
- Capture current/baseline once;runbaseline captured beforework;reuse parsed ownedrecords.
- CORE8outputguards/publication,CORE9capture/parser/validation,CORE10logic unchanged.
- Workflow exit0valid/1baseline differs/2error;read saved_status separately,no numericPASS.
- No baseline means nocomparison,no fallback;postwork failure maybenonzero,no cleanup.
- JSON stdout only;exact3runpackagefiles,no implicit receipt writteninsideinput/output.
- No installs/network/vehicle/F61/r/dt/Controller/runtime/CAN/push/merge/PR/CI/HF/deletion.
- Frozenwheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.

## Review Focus

- check-only must never import producer/model or create outputs,even with malformed inputs.
- Baseline changes after capture must not trigger rereads or contaminate report/compare.
- New synthetic work/recorded historical work/saved M-D-R/workflow exits must stay distinct.
- Failed run after any calculation/publication must not claim zero work or delete/reuse partial output.
- Pure comparison extraction must preserve existing CORE10 full metadata/type/truncation/errors/bytes.

### Task 1: Integrated closed workflow

**Files:** create integration_tools/core_sequence_workflow.py,tools/core_sequence_workflow.py,
project/test_core_sequence_workflow.py,docs/CORE_SEQUENCE_WORKFLOW_CORE11_KO.md;
modify integration_tools/core_sequence_compare.py,README/backlog;spec/plan committed first.
**Interfaces:** check_saved_sequence(Path,Path|None=None)->dict;
run_closed_sequence(object,Path,Path|None=None)->dict;WorkflowError.code;exit_code(dict)->int;
CORE10 private _compare_captured(ownedlhs,ownedrhs)->dict(existingAPI delegates).

- [ ] Immutable baseline fullgate1147/259/static/wheel PASS.
- [ ] Tests first:checkM/D/R0work,baseline/no baseline,8read-onlyopens,noreopens;
  runactual3/3/0,closed3files,case/baseline/outputguards;capturedbaseline survives
  subsequentdiskchange;producer/results mismatch,postworkcorruption/exception,
  partialpreservation;freshblockedcheck,realCLI0/1/2/help/options/stdout;determinism
  andCORE10compat. Run `.venv/bin/python -I -B -m unittest discover -s project -p test_core_sequence_workflow.py -v`.
  Expected:missingfeature RED,not import/fixture errors.
- [ ] Extract pure comparison body unchanged;implement coordinator/thinCLI per spec.
  Samecommand expected allPASS;scopedRuff/Ty/Codespell/diffcheckPASS.
- [ ] Guide/README/backlog explain modes,workcounts,baselineidentity,falsequalification,
  nooverwrite/partialfolder andworkflowexitnotnumericalstatus;commit stable source.
- [ ] Full `dev.py verify --output <newexternaldir>` expected1147+new/262/static/wheelPASS;
  one fresh wholebranch review;one TDDfixpass if needed,no rereview.
- [ ] Independent actualAPI/CLI checks andrun3cases twice;profile stepcounts6perrunset,
  inputpreserved,exactpackageclosure/manifests,noreopens,baselinechecks,portableparity.
- [ ] Source539/prior530preserved;Manifest/cloudconsumer/localrefs/links,external
  report/result/recheck/ledger;keep localbranch/evidence without remote writes.

Self-review:onecohesiveworkflow,privatecomparison seam consumed bycoordinator,
no multi-taskinterface conflicts. Each ReviewFocus has a concrete test above.
