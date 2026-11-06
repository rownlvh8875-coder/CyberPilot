# CORE24 Preflight Report CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Print unchanged CORE23 Korean Markdown with current compatibility exits and clarify prior evidence hash labels without modifying its seal.

**Architecture:** Thin standalone stdlib wrapper follows CORE22's proven no-cache parser/descriptor pattern; one CORE23 call and unchanged Markdown, paired CORE21 current verdict controls exit. Independent external addendum preserves/verifies original CORE23 artifacts.

**Tech Stack:** Configured Linux CPython3.12.13 stdlib/unittest/Ruff/Ty/Codespell, frozen wheel unchanged.

**Spec:** [design](../specs/2026-11-06-core24-preflight-report-cli-design.md)

## Global Constraints

- Exactly one nonempty --archive/--sha256, no repetition/abbreviation/extra run/export/output/format/rate flags.
- One CORE23 call, exact Markdown stdout, current compatible/rejected0/1, fixed operational2; both known error types preserved.
- Syntax/help before project/input work, bad SHA before path, no output before complete API result/status validation.
- Parser-through-output bytecode suppression, caller sys.path/flag restored; temp/cache creation/probing0.
- Short writes complete, failed stdout/stderr/help operational2, prefix cannot be retracted; BaseException restoration.
- Existing computational source/CLI/receipt/Markdown unchanged, no extraction/new model/reference/F61/actualr-dt/vehicle work.
- Numeric validation and gate fixtures separately NONZERO; actualr/T2/scale=null and denial gates unchanged.
- Old CORE23 seal immutable; addendum labels actual artifact hashes, not authority.
- Keep local branch/worktree/evidence, no merge/push/PR/CI/HF writes.

## Review Focus

- Exact Korean UTF8 bytes, current status exits and all3case rows must remain independent from historical saved labels or API generation success.
- Malformed SHA/unsafe path and syntax/help must fail before path/project work; cap/render failures must not leak partial reports or raw exceptions.
- Cold parser/API work and failure paths must suppress bytecode without temp probes and restore caller globals.
- Real failed stdout/stderr/help and partial multibyte output must retain operational2, never flush exit120 or false success.
- One report/capture/verifier/render, no producer/reference/model/F61 or added authority; addendum must name the correct artifacts and preserve the old seal.

### Task1: Korean report command and exact evidence-label addendum

**Files:** Create `tools/core_sequence_preflight_report.py`, `project/test_core_sequence_preflight_report_cli.py`, `docs/CORE_SEQUENCE_PREFLIGHT_REPORT_CLI_CORE24_KO.md`; link `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`, `docs/CORE_SEQUENCE_PREFLIGHT_REPORT_CORE23_KO.md`.

**Interfaces:** Consumes CORE23 `report_preflight_archive(Path,str)->(dict,bytes)`, PreflightReportError and CORE21 ArchivePreflightError; produces `main(argv=None)->int`/exact Markdown stdout. External addendum consumes exact old ZIP/manifest/seal/artifacts, produces labeled immutable-identity clarification JSON/KO.

- [ ] Step1: Write real archive CLI tests for all five Review Focus classes, literal exits/rows/error controls and output/global boundaries.
- [ ] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_preflight_report_cli.py' -v`; Expected new methods FAIL for absent command.
- [ ] Step3: Implement minimal wrapper with two known error classes and proven descriptor writes. Existing source untouched.
- [ ] Step4: New focused plus old138+26 regressions and Ruff/Ty/Codespell; Expected PASS. Add guide/discoverability links.
- [ ] Step5: `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`; Expected1526+actual new tests/296 compiles/static PASS, frozen wheel.
- [ ] Step6: Original CORE17 ZIP command/API/direct/blocked/cold acceptance twice and help/usage/missing; Expected exact old CORE23 Markdown, exit1,one capture/verifier/renderer,3cases/8quantizer, no new fixtures/model/ref/writes/extraction and originals preserved. Verify old CORE23 ZIP/Manifest/seal and issue named-hash addendum.
- [ ] Step7: Source616/protected608/refs27,local links/cloud consumer,commit,one fresh final review/unsigned seal; Expected clean branch/no unresolved Critical/Important/no remote publication.
