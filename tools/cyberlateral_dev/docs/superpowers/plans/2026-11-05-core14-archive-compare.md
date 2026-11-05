# CORE14 Archive Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare two validated saved-suite ZIPs, no extraction or model work.
**Architecture:** Extend private CORE13 verification to expose captured records;
reuse CORE10 comparison for fixed three cases, with role-qualified errors and CLI.
**Tech Stack:** Existing Python3.12, standard library, existing venv; no installs.
**Spec:** ../specs/2026-11-05-core14-archive-compare-design.md

## Global Constraints

No extraction, source reopening, model/F61/Controller/Runtime/CAN/actual r work.
Both full lower-case64hex SHA values validated before filesystem/parsing work.
CORE13 ZIP/public receipts unchanged; opaque identity not reauthenticated.
Actual r/T2/vehicle_scale=null; R_BUDGET UNRESOLVED; Static Gate FAIL.
Keep prior sources/refs/evidence. No merge/push/PR/CI/HF writes. Inline execution
and one fresh whole-branch reviewer; at most one Important/Critical TDD fix pass.

## Review Focus

Both-role SHA preflight and malformed-right behavior: no early partial receipt.
CORE13 private extraction: exactly-once captures/parses and unchanged public bytes.
Nested/type/identity differences: all counts, bounded detail and no status promotion.
ZIP64/malformed archive boundaries: same preparse guards as CORE13, no extraction.
CLI cache/serialization/stdout failures: truthful fixed errors, no premature output.

### Task1: saved-only archive comparison

**Files:** Create integration_tools/core_sequence_archive_compare.py,
tools/core_sequence_archive_compare.py, project/test_core_sequence_archive_compare.py,
docs/CORE_SEQUENCE_ARCHIVE_COMPARE_CORE14_KO.md. Modify private verification helpers
in integration_tools/core_sequence_bundle.py, README.md, docs/CORE_DEVELOPMENT_BACKLOG_KO.md.
**Interfaces:** Consumes CORE13 _read_archive, _expected, private verified receipt/
records pair and CORE10 _compare_captured; produces the exact file/byte API and
CLI contract in spec. CORE13 public wrapper returns the same receipt only.

- [ ] Archive baseline90db5d91f3fcce683813771871b67468b6a8ddff then run
  `.venv/bin/python -B <archive>/dev.py verify --output <work>/base-verify`.
  Expected1248tests/269compiles/static PASS/frozen wheel unchanged.
- [ ] Commit spec/plan. Write behavioral tests for pure/file/CLI boundaries.
  Expected missing CORE14 assertion RED. Pin identical/MDR history/no new work;
  literal one identity difference (INPUT0/RESULT0/IDENTITY1); multiple case counts;
  exact types/null/missing/JSON-pointer escaping; detail truncation/all-counts;
  reversal; both SHA preflight; left/right malformed/checksum/source/gate/report
  rejection; symlink/FIFO/cap/ZIP64; capture/parse exactly once; input immutability;
  unchanged CORE13 output; CLI0/1/2/options/cleanup/stdout; no execution imports.
- [ ] Implement smallest private CORE13 extraction and new file/byte API/CLI.
  Expected new focused tests GREEN; CORE10/CORE13 compatibility tests GREEN.
- [ ] Add guide/README/backlog. Run Ruff/Ty/Codespell and complete dev.py verify.
  Expected1248+actualnew tests/272compiles/static PASS/same frozen wheel. Commit.
- [ ] Fresh whole-branch review using Review Focus verbatim; grade findings by
  user effects, record all declined judgments; one TDD Important/Critical fix pass
  and full suite if required; no rereview, minors deferred.
- [ ] Two independent acceptance runs against historical CORE13 ZIP and synthetic
  edited copies (never change originals), API/CLI/import-blocked CLI; expected
  identical/difference/error0/1/2, precise difference1, malformed no output,
  no new execution, reports byte-identical across paths/repeats.
- [ ] Source custody558registered/549prior-protected; doc links, gate Manifests,
  actual cloud gate consumer and old refs verification; final Korean report and
  result/checksum records. Keep local branch, no external publication.
