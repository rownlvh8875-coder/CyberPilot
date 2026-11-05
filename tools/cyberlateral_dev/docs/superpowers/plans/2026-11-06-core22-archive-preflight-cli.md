# CORE22 Archive Input Preflight CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose unchanged CORE21 portable archive input semantics through a no-cache read-only command.

**Architecture:** Thin stdlib wrapper using CORE20's proven bootstrap/output pattern, not importing its private command helpers. One CORE21 call, canonical JSON unchanged, exit based on current semantic verdict only. No API/model changes or new shared framework.

**Tech Stack:** Configured Linux CPython3.12.13 stdlib, unittest/Ruff/Ty/Codespell, unchanged public wheel.

**Spec:** [design](../specs/2026-11-06-core22-archive-preflight-cli-design.md)

## Global Constraints

- Exactly one nonempty --archive/--sha256; no abbreviation/repetition/run/export/output/rate flags.
- Full canonical CORE21 receipt unchanged; current compatible/rejected0/1; fixed operational2.
- Help/syntax before project import/input access; SHA format before caller path access.
- Parser-to-output bytecode suppression, original sys.path/bytecode restored; temp/cache creation/probing0.
- Short writes complete; failed/closed stderr never replaces operational2; no partial receipt before serialization succeeds.
- No extraction/new model/reference/producer/F61/actualr-dt/vehicle work. Numeric work NONZERO.
- Actualr/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL; preserve denial gates and local evidence.
- No merge/push/PR/CI/HF writes; no edits to existing algorithm/API/CLI sources.

## Review Focus

- Aggregate current compatibility, not historical saved labels, decides exit; all-valid historical REJECTED and all-invalid bundles must not be misclassified.
- Malformed SHA on an unsafe/missing path must fail before path work; syntax/help must not import product code or touch inputs.
- Cold parser/API imports and failure paths must suppress bytecode without creating/probing temp caches and restore caller globals.
- Real failed stdout/stderr/help destinations must preserve operational2; partial stdout must never be mistaken for complete successful JSON.
- One archive capture/verifier must precede all three semantic cases, with no extraction/producer/reference/model/F61 execution or policy authority.

### Task1: Read-only portable input preflight command

**Files:** Create `tools/core_sequence_archive_preflight.py`, `project/test_core_sequence_archive_preflight_cli.py`, `docs/CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CLI_CORE22_KO.md`; add links to `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`, `docs/CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CORE21_KO.md`.

**Interfaces:** Consumes unchanged `preflight_suite_archive(Path,str)->dict`, `ArchivePreflightError.code`, `canonical(dict)->bytes`; produces `main(argv=None)->int` with stdout exact API bytes and fixed error codes.

- [ ] Step1: Write real archive tests for all five Review Focus classes, literal outcomes/exits, source/global/output/error boundaries.
- [ ] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_archive_preflight_cli.py' -v`; Expected: new methods FAIL for absent command.
- [ ] Step3: Implement minimal standalone parser/bootstrap/output wrapper, same descriptor/best-effort diagnostic behavior as CORE20. No existing product edits.
- [ ] Step4: Run new tests plus prior84 focused tests; Expected PASS. Add guide/discoverability links and run Ruff/Ty/Codespell.
- [ ] Step5: Run `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`; Expected prior1472+actual new count PASS,292 own compiles/static PASS, wheel unchanged.
- [ ] Step6: Independent preserved CURRENT.zip acceptance twice, API/direct/blocked/cold commands and help/usage/missing controls; Expected canonical bytes equal prior CORE21, exit1, one capture/verifier,three cases/eight quantizer calls, no new fixtures/model/ref/writes/extraction and originals unchanged.
- [ ] Step7: Verify source606/protected598/refs25 and local links/cloud consumer, commit, one fresh final review and independent unsigned seal validation; Expected clean branch/no unresolved Critical/Important/no publication.
