# CORE9 Saved Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native offline work without repeated approval questions.

**Goal:** Inspect stored CORE8 bytes/record relationships without new computation.
**Architecture:** Bounded owned-file capture + pure stored-record validator,
summary/Markdown formatter and thin stdout-only CLI; no model/execution imports.
**Tech Stack:** Existing CPython3.12.13/Linux/stdlib/unittest/Ruff/Ty/Codespell.
**Spec:** docs/superpowers/specs/2026-11-05-core9-saved-inspection-design.md

## Global Constraints

- Base900fc12fd634e4b71b437c57619aa50c763f0fe7, existing linked worktree/local branch.
- Exact3files/caps/read flags/JSON grammar/canonical/schema/relations/errors from spec.
- All valid saved statuses inspect exit0; package/operational error exit2/no partial summary.
- Stored-value equality only, no model/native/quantization/dt/r or fresh source/origin proof.
- No input/source writes, reopens, recursive scan, manifest traversal or output files.
- CLI private cache only/restored; source/history/policy/vehicle gates remain false/closed.
- Old CORE1~8/runtime/src/lock/workflow/import/profile/wheel unchanged.
- Wheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- No installs/network/push/merge/PR/HF/CI/cleanup; preserve prior refs/evidence.

## Review Focus

- Manifest refresh must not hide inconsistent saved/computed/difference/count/gate records.
- Partial/late-error/boolean counts cannot become valid zero-work rejection or fresh MATCH.
- Symlinks/FIFO/extra members/large or malicious JSON must reject with bounded reads and no traversal.
- Reader/CLI must import no model/execution path and never modify or reopen captured input.
- Consistent altered data is not origin/arithmetic proof; exit0 is inspection success only.

### Task 1: Saved record inspection/API/CLI

**Files:** create integration_tools/core_sequence_record.py,core_sequence_saved.py,
tools/core_sequence_inspect.py,project/test_core_sequence_saved.py,
docs/CORE_SEQUENCE_INSPECT_CORE9_KO.md; modify component README/backlog.
**Interfaces:** InspectError.code,validate_records(object,object)->dict,
inspect_saved_sequence(Path)->dict,format_saved_sequence(Path,str='json')->bytes,
CLI --input/--format only. Existing producer used only by fixture setup, never reader.

- [ ] Immutable baseline fullgate1089/252/static/wheel PASS; commit spec/plan before code.
- [ ] Tests first: savedM/D/R exact summaries/exits0; canonical repeat/Markdown;
  capturedbytes/modesunchanged, fresh no-import/model-call guard, checksum/closure/IO/
  JSON/resource/schema/row/gate/claim rejection, coherent forged data unqualified.
  Expect missing-feature RED, not setup errors. External ledger/BASE for nonmounted scripts.
- [ ] Implement spec bounded capture/record relations/summary/thin CLI; focused GREEN,
  scoped Ruff/Ty/Codespell PASS, no old execution/source changes.
- [ ] Guide/README/backlog explain captured vs authentic, saved vs fresh outcome,
  inspection exit0/error2, new calculations0 vs setup/gate nonzero.
- [ ] Commit; stable-source fullgate1089+actual new tests/256compiles/static/wheel PASS;
  one fresh read-only whole-branch review may overlap.
- [ ] Independent API/actualCLI historical CORE8 packets twice, exact summaries,
  corruption checks/no-import profiling/input preservation; one TDD fix pass if needed.
- [ ] Final real cloud consumer/Manifest/source custody/wheel/localrefs and external
  report/result; preserve branch/evidence with no remote publication.

Self-review: one bounded-reader workflow task/no shared-task conflicts. Every focus
class has a concrete test; validation does not certify full API input or replay arithmetic.
