# CORE15-R1 Case Category Totals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close CORE15's deferred per-case INPUT/RESULT/IDENTITY display gap.
**Architecture:** Add three columns to the existing bounded Markdown case table,
reading existing comparator-owned per-case totals. No comparison/API/CLI changes.
**Tech Stack:** Existing Python3.12/stdlib/venv, no installs.
**Spec:** ../specs/2026-11-05-core15-readable-archive-summary-design.md

## Global Constraints

Base da7eadaf502fdbf2574b0edb063501a00aad1d05. Input/CORE14 JSON and exit0/1/2
unchanged. Keep20details/case,160escapedASCII/cell,65536outputbytes and CORE14's
4MiB diagnostic guard. No extraction/new model/F61/Controller/Runtime/CAN/actualr,
vehicle input, source authentication or publication. Actualr/T2/scale=null,
R_BUDGET UNRESOLVED, Static Gate FAIL. Preserve local refs/evidence; no merge,
push, PR, CI or HF writes. User approved this next scoped correction.

## Review Focus

Category order is INPUT/RESULT/IDENTITY, values come from each case, not global totals.
Hidden RESULT changes remain visible in totals when20identity previews consume the summary.
Zero and mixed-category cases remain exact; original JSON/exit behavior untouched.
New9column Markdown structure stays escaped/bounded; detailed7column tables unchanged.
Limits/gates and read-only single capture/comparison are not weakened.

### Task1: presentation correction

**Files:** Modify integration_tools/core_sequence_archive_report.py,
project/test_core_sequence_archive_report.py, docs/CORE_SEQUENCE_ARCHIVE_REPORT_CORE15_KO.md,
docs/CORE_DEVELOPMENT_BACKLOG_KO.md. Create this plan only. No new Python files.
**Interfaces:** Consume existing per-case comparison['difference_counts']; retain
all existing signatures, tuple return/JSON fields and summary contract ID.

- [ ] Fresh baseline focused24tests on clean base. Previous full1303/275 gate is
  historical evidence, not rerun/claimed fresh; final full suite below is mandatory.
- [ ] Commit plan. Add2tests: valid late-invalid25identity+1RESULT ->row26/0/1/25/26/20
  despite hidden RESULT detail; mixed cases INPUT1/RESULT1/IDENTITY2 must appear in
  correct local rows and preserve full JSON/CLI bytes parity. Expected2RED.
- [ ] Add INPUT/RESULT/IDENTITY table headers/separators/cells from each case dict.
  Expected26focused GREEN; old escaping/budgets/gates/CLI tests remain passing.
- [ ] Update guide/backlog, run Ruff/Ty/Codespell; full dev.py verify to new external
  directory. Expected1305tests/275compiles/static PASS/frozen wheel unchanged. Commit.
- [ ] One fresh whole-branch reviewer; one TDD Critical/Important fix pass if required,
  no rereview; new minors deferred with exact record. Known previous gap should close.
- [ ] Independent2runs using preserved historical bytes and edited synthetic copies:
  API/pure/directCLI/import-blocked CLI identical; Pandoc GFM9column counts/values;
  original CORE14 JSON byte identity; inherited errors/no execution unchanged.
- [ ] Registered565files/560prior-protected, refs16 unchanged, gate Manifest/cloud
  consumer/doc links, Korean report/result/ZIP/checksum. Keep branch/evidence locally.
