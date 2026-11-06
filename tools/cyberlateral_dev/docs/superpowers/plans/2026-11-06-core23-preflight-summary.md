# CORE23 Preflight Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pair unchanged CORE21 JSON with bounded Korean Markdown that separates current input compatibility from historical results.

**Architecture:** One existing bytes/Path preflight call then private owned-receipt renderer; reuse unchanged CORE15 safe typed cell preview. No public arbitrary dict input, new CLI/extraction/replay or numerical algorithm changes.

**Tech Stack:** Configured Linux CPython3.12.13 stdlib/unittest/Ruff/Ty/Codespell, unchanged public wheel.

**Spec:** [design](../specs/2026-11-06-core23-preflight-summary-design.md)

## Global Constraints

- Exactly one corresponding CORE21 call; complete preflight before rendering, errors propagate, original receipt unchanged.
- Title/contract and display fields as spec; all three case rows, current/historical/prefix/new work clearly distinct.
- Reuse CORE15 typed escaped160-character cell previews; clipped count;65536UTF8byte output cap, no clamp of original JSON.
- No new CLI or edits to existing algorithm/API/CLI sources; no extraction/writes/new model/reference/F61/actualr-dt/vehicle work.
- Numeric validation and whole gate fixture work separately NONZERO; actualr/T2/scale=null and denial gates unchanged.
- Retain local branch/worktree/evidence; no merge/push/PR/CI/HF writes.

## Review Focus

- Historical REJECTED with now-compatible input and early/all input rejection must preserve distinct current/saved rows and correct full counts.
- Null versus false/zero and validation prefixes versus executed transitions must remain unambiguous in every displayed row and gate.
- Display data containing Markdown/HTML/control/bidi tokens or long text must stay bounded and escaped without changing original JSON.
- Malformed SHA/corrupt final archive member or unexpected semantic failure must never yield a summary or trigger extra capture/validation.
- Rendering must not add producer/reference/model/F61 execution, source/arithmetic/vehicle authority, or a misleading all-process-zero/visual-quality claim.

### Task1: Owned preflight Markdown report

**Files:** Create `integration_tools/core_sequence_preflight_report.py`, `project/test_core_sequence_preflight_report.py`, `docs/CORE_SEQUENCE_PREFLIGHT_REPORT_CORE23_KO.md`; link `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`, `docs/CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CORE21_KO.md`.

**Interfaces:** Consumes `preflight_suite_archive_bytes(bytes,str)->dict`, `preflight_suite_archive(Path,str)->dict`, CORE15 `_preview(value)->(str,bool)`; produces the two `report_preflight_archive*` APIs and `PreflightReportError.code` as spec. Private `_markdown` accepts owned result only.

- [ ] Step1: Write real archive behavior tests for all five Review Focus classes, exact row/count literals, gate/null/safe rendering, errors/capture and execution guards.
- [ ] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_preflight_report.py' -v`; Expected all new methods FAIL because module absent.
- [ ] Step3: Implement bounded deterministic renderer and two thin public wrappers. No existing computational sources modified.
- [ ] Step4: New focused + prior preflight/report regressions, Ruff/Ty/Codespell; Expected PASS. Add guide/discoverability links.
- [ ] Step5: Run `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`; Expected1504+actual new tests/294 own compiles/static PASS, frozen wheel unchanged.
- [ ] Step6: Independent preserved CURRENT.zip bytes/Path reports twice, JSON equal prior CORE21; Expected identical reports, capture0/1,verifier1/cases3/quantizer8, no new fixtures/model/ref/writes/extraction, originals unchanged.
- [ ] Step7: Source611/protected603/refs26, local links/cloud consumer, local commit, one fresh final review and independent unsigned seal; Expected clean branch/no unresolved Critical/Important/no publication.
