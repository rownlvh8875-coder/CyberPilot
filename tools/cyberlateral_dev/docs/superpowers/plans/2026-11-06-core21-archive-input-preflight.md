# CORE21 Archive Input Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revalidate all three saved synthetic inputs directly from one verified portable ZIP capture.

**Architecture:** Reuse unchanged CORE13 `_verified_suite` and its owned records; factor CORE19's post-capture body into a private helper without changing its AST. Aggregate all case receipts, preserve current versus historical outcomes and fixed integrity errors. No CLI/extraction/replay.

**Tech Stack:** Existing CPython3.12.13 Linux stdlib, unittest/Ruff/Ty/Codespell, unchanged public wheel.

**Spec:** [design](../specs/2026-11-06-core21-archive-input-preflight-design.md)

## Global Constraints

- CORE13 verification, CORE19 public API/receipt and CORE20 CLI semantics unchanged.
- Full expected SHA format before path access; one bounded read and one `_verified_suite` call.
- Semantic validation only after whole archive verification; every case processed in fixed order.
- No filesystem writes/extraction/model/reference/F61/actualr-dt/Controller/Runtime/CAN work.
- Numeric validation NONZERO; actual r/T2/scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL.
- Retain branch/worktree/evidence, no merge/push/PR/CI/HF writes.

## Review Focus

- Integrity success is not input compatibility: historical labels remain data; all-valid and all-invalid coherent bundles must classify correctly.
- Malformed SHA or corrupt final member must fail before path/semantic work respectively, never emit a partial aggregate.
- Path captures once; bytes variant performs no file I/O; all existing ZIP resource/type/path restrictions remain enforced.
- Factored CORE19 preserves receipts, numeric errors/prefixes, signed zero and exception propagation; no altered CLI behavior.
- Every case is checked after an early rejection, unknown/helper failures cannot masquerade as success, and no model/reference/producer/F61 execution occurs.

### Task1: Portable archive semantic preflight

**Files:** Create `integration_tools/core_sequence_archive_preflight.py`, `project/test_core_sequence_archive_preflight.py`, `docs/CORE_SEQUENCE_ARCHIVE_PREFLIGHT_CORE21_KO.md`; modify `integration_tools/core_sequence_input_preflight.py` by helper extraction only; add links to `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`, `docs/CORE_SEQUENCE_INPUT_PREFLIGHT_CORE19_KO.md`.

**Interfaces:**
- Consumes `_verified_suite(bytes,str)->(receipt,owned_records)`, `_expected(str)`, `_read_archive(Path)`, CORE19 post-capture body.
- Produces `_preflight_captured(dict)->dict` private, unchanged public CORE19; new bytes/Path preflight APIs and ArchivePreflightError.code exactly as specified.

- [ ] Step1: Write real canonical archive tests for all five Review Focus classes, fixed literal outcomes/counts, folder parity and error controls.
- [ ] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_sequence_archive_preflight.py' -v`; Expected: all new methods FAIL because module absent.
- [ ] Step3: Factor existing CORE19 post-capture body with identical AST, implement small verified-record aggregator and one-read Path wrapper.
- [ ] Step4: Run new focused tests plus existing `test_core_sequence_input_preflight*.py`; Expected: new methods and prior58 tests PASS. Add guide/discoverability links.
- [ ] Step5: Run `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`; Expected: prior1446 + actual new count PASS;290 compiles/static checks PASS, wheel unchanged.
- [ ] Step6: Independent preserved CURRENT.zip bytes/Path runs twice; compare embedded case receipts against prior CORE19 and archive receipt against CORE13, guard read/verification counts/imports/execution/writes. Expected: one path capture, one verifier invocation,3semantic cases,0fixture/model work, identical outputs and input bytes/modes.
- [ ] Step7: Verify source601/protected592/refs24 plus exact CORE19 computational AST preservation, local commit, one fresh final reviewer, independent unsigned ZIP verification. Expected: clean branch/no unresolved Critical/Important/no publication.
