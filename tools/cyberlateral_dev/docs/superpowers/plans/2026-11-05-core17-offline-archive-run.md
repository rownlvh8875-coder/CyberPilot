# CORE17 Offline Archive Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One explicit run command produces a fixed synthetic suite, ZIP and baseline summary.
**Architecture:** Validate/capture baseline once, publish its exact copy, reuse
CORE12 run/CORE13 export/CORE16 comparison without changing their APIs or source.
**Tech Stack:** CPython3.12.13, existing stdlib/venv only.
**Spec:** ../specs/2026-11-05-core17-offline-archive-run-design.md

## Global Constraints

Base625d5b44d9b047a49158c1a85cf47711777e3cb8. Existing APIs/code unchanged.
Explicit fixed3case run only;6new synthetic model steps on success, comparison0.
No arbitrary intake/extraction/vehicle/F61/Controller/Runtime/CAN/actualr/dt.
Actualr/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL; F70UH/V/F71 prohibited.
NEW external output/no overwrite/partial preservation. Existing2MB/4MiB/65536byte
caps retained. Local commits only; no merge/push/PR/CI/HF writes, keep prior evidence.

## Review Focus

1. Bad SHA/output/baseline must fail before any model execution or output creation.
2. Baseline copy short/failed write must prevent model work and retain partial output.
3. Original baseline read once before execution; later original mutation cannot alter captured comparison.
4. Later-stage failure never reports zero work or success and never removes earlier output.
5. Literal run/exit0vs1/cache/stdout behavior preserves truthful synthetic work and gates.

### Task1: closed end-to-end orchestration

**Files:** Create integration_tools/core_sequence_archive_run.py,
tools/core_sequence_archive_run.py, project/test_core_sequence_archive_run.py,
docs/CORE_SEQUENCE_ARCHIVE_RUN_CORE17_KO.md, this plan/linked spec.
Modify README.md and docs/CORE_DEVELOPMENT_BACKLOG_KO.md only.
**Interfaces:** Consume CORE13 _expected/_read_archive/verify_suite_bytes/export_saved_suite,
CORE16 _output/_publish/publish_archive_report and CORE12 run_closed_suite.
Produce ArchiveRunError.code, run_archived_suite(Path,str,Path)->dict, comparison_exit_code.

- [ ] Focused baseline25PASS, commit plan/spec; external brief/BASE/ledger.
- [ ] New tests first: same/different baseline full14-file layout, exact old API
  composition,6observed model steps, M/D/R1/1/1 distinct from exit; deterministic2runs;
  SHA before metadata, invalid hash/ZIP/size/source FIFO/output guards ->0steps;
  copy no-progress/short writes; single original capture and mutation after capture;
  actual partial second-case failure, export/report/final-layout failure preservation;
  CLI required run/arguments/stdout/cleanup/work uncertainty/closed gates. Expected RED.
- [ ] Implement only new orchestrator/CLI and fixed layout check. Focused GREEN;
  old CORE12/13/16 tests remain passing, no algorithm changes. Add Korean docs/links.
- [ ] Full `python -B dev.py verify --output <NEW external>` -> all tests,
 281own compiles/Ruff/Ty/Codespell PASS, frozen wheel unchanged. Commit implementation.
- [ ] Independent2runs on preserved identical/changed ZIP baselines; API/directCLI
  outputs/receipts byte-identical, explicit6steps/run, old stage composition parity,
  original baseline custody, no F61/vehicle/r/dt work. Registered578/prior570, refs19.
- [ ] One fresh whole-branch read-only reviewer; at most one TDD Critical/Important
  fix pass/full gate, no rereview. Minors deferred, exhaustive rulings/costs.
- [ ] Verify source/refs/gate Manifest/cloud consumer/reproducibility/docs; Korean
  result/report/seal/ZIP/checksum. Retain local branch/worktree/evidence.
