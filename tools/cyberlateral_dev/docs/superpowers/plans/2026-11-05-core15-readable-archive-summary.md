# CORE15 Readable Archive Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Korean Markdown projection of verified CORE14 ZIP comparison, no replay.
**Architecture:** Two API wrappers call unchanged CORE14 once; private bounded safe
Markdown projection; separate CLI with existing cleanup/error/output discipline.
**Tech Stack:** Existing Python3.12/standard library/venv, no installs.
**Spec:** ../specs/2026-11-05-core15-readable-archive-summary-design.md

## Global Constraints

Existing CORE13/14 Python, JSON and CLI unchanged. Both external SHA checks and
all ZIP/diagnostic budgets remain enforced. No extraction, source reopening, model/
F61/Controller/Runtime/CAN/r work. Actual r/T2/scale=null, Static Gate FAIL,
R_BUDGET UNRESOLVED. No publish, merge, push, PR, CI, HF writes or evidence deletion.

## Review Focus

Hostile metadata escaping: Markdown source must not inject code spans/HTML/tables.
Bounded preview: long paths/subtrees must not amplify output or hide omission.
Projection fidelity: full/retained/shown counts, missing/null, types, history vs work.
Single comparison and inherited SHA/ZIP/budget rejection before any summary output.
CLI render/exit/cache/stdout failures: fixed errors, no premature success or fallback.

### Task1: bounded Korean Markdown projection

**Files:** Create integration_tools/core_sequence_archive_report.py,
tools/core_sequence_archive_report.py, project/test_core_sequence_archive_report.py,
docs/CORE_SEQUENCE_ARCHIVE_REPORT_CORE15_KO.md; modify README.md and
docs/CORE_DEVELOPMENT_BACKLOG_KO.md only. New spec/plan included. No older Python edits.
**Interfaces:** Consumes compare_suite_archives/compare_suite_archive_bytes/exit_code
from CORE14; produces report_suite_archives/report_suite_archive_bytes ->tuple[dict,bytes].
Private renderer consumes comparator-owned dict, not external records.

- [ ] Archive base1d5ba3642130a0aedfd296808786394e6d1cd2fe and run archived dev.py
  verify to external base-verify. Expected1279tests/272compiles/static PASS/frozen wheel.
- [ ] Commit spec/plan. Behavioral tests first: missing feature RED. Cover identical/
  changed/invalid0/1/2; returned dict equals CORE14; exact SHA/case/history/gates;
  full vs retained256 vs shown20; missing/null/false/0; escaped controls/HTML/pipe/
  backtick/bidi;160character preview boundary/marker; long subtrees/output<=65536;
  repeated/path independent bytes; one comparison/two captures; inherited digest/
  ZIP/4MiB rejection; input immutability; CLI options/cache/exit/render/stdout faults;
  fresh-process import/extraction blockers. Expected new focused tests GREEN.
- [ ] Implement new APIs/private safe projection and CLI only. Add guide/README/
  backlog. CORE14compat31 and CORE13compat36 PASS; Ruff/Ty/Codespell PASS.
- [ ] Full dev.py verify. Expected1279+actualnew tests/275owncompiles/static PASS/
  frozen wheel unchanged. Commit implementation and task completion ledger.
- [ ] One fresh whole-branch review with focus verbatim; all declined judgments
  ruled with reasons/costs. One Important/Critical TDD fix pass/full gate if needed;
  no rereview, minors deferred. Markdown source checks do not claim browser PASS.
- [ ] Independent2runs against historical ZIP + edited/malformed copies using
  API/pure/directCLI/import-blocked CLI. Markdown and returned comparison repeat
  byte-identically, exact comparison compatibility, count/escaping checks and no
  execution. Never mutate old evidence; no browser/network/environment setup.
- [ ] Source custody564registered/556old-protected; previous refs15 preserved;
  DEV Manifest/cloud consumer/doc links; Korean report/result/evidence ZIP/SHA.
  Keep branch/evidence, no publication.
