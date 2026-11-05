# CORE16 Saved Archive Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save one verified ZIP comparison, its readable summary and checksum together.
**Architecture:** CORE15 single comparison feeds an exclusive fd-relative publisher;
new CLI prints a path-independent receipt after readback and cache cleanup.
**Tech Stack:** Existing Python3.12/stdlib/venv; no installs.
**Spec:** ../specs/2026-11-05-core16-archive-workflow-design.md

## Global Constraints

Base2a45f6b35935d491146973161eb329a66d37a509. Existing APIs/CLIs unchanged;
CORE14 4MiB/CORE15 65536byte caps unchanged. Fixed3file output/no overwrite/readback.
No new comparison-model/reference/F61/Controller/Runtime/CAN/r/dt/vehicle work.
Actualr/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL. Local commits only;
no merge/push/PR/CI/HF writes. Preserve prior files/refs/evidence.

## Review Focus

1. Full digests before caller path access; malformed second digest must not capture first ZIP.
2. Existing targets/symlink parents/checkouts/invalid paths must never receive output.
3. Valid comparison JSON may exceed64KiB; no accidental Markdown-sized readback cap.
4. Short/no-progress writes and readback/layout failure never report publication success.
5. Cache cleanup/stdout failure after publication must not claim no output exists.

### Task1: integrated saved-only workflow

**Files:** Create integration_tools/core_sequence_archive_workflow.py,
tools/core_sequence_archive_workflow.py, project/test_core_sequence_archive_workflow.py,
docs/CORE_SEQUENCE_ARCHIVE_WORKFLOW_CORE16_KO.md, this plan and linked spec.
Modify README.md and docs/CORE_DEVELOPMENT_BACKLOG_KO.md only.
**Interfaces:** Consume CORE14 `_preflight` and `exit_code`, CORE15
`report_suite_archives(Path,str,Path,str)->tuple[dict,bytes]`, suite `_path`/ROOT and
scenario `canonical`/GATES. Produce `ArchiveWorkflowError.code` and
`publish_archive_report(Path,str,Path,str,Path)->dict` with the spec's receipt.

- [ ] Commit plan/spec; focused baseline26tests. External brief/BASE/progress ledger.
- [ ] Write test module first. Pin same/different saved M/D/R versus exit, exact
  original CORE14 JSON/CORE15 MD and independently hashed sorted2entry checksum,
  deterministic two output directories, single source capture, no source mutation.
  Pin review focus1-5, source hash/ZIP rejection before mkdir, exclusive race,
  partial preservation, short writes, readback mismatch/extra file/fifo/root switch,
  three-file CLI stdout/exit/errors/no producer imports. Expected missing-feature RED.
- [ ] Implement only the new API/CLI; focused tests GREEN. Existing26tests unchanged.
- [ ] Add Korean usage and backlog/README link. Ruff/Ty/Codespell PASS.
- [ ] Run complete `python -B dev.py verify --output <NEW external>`; all tests,
  own compile/static/wheel/gate checks PASS. Commit implementation after verification.
- [ ] Independent2runs on preserved ZIP bytes with identical, ordinary and hidden
  changes via API/directCLI/import-blocked CLI; stdlib JSON/checksum/readback equality,
  exact older JSON/MD parity, deterministic receipts/files, zero new executions.
- [ ] One fresh whole-branch reviewer; at most one TDD Critical/Important fix pass
  and full gate; no rereview, minors deferred. Exhaustive rulings with costs.
- [ ] Verify source registry/prior refs/frozen wheel/cloud gate consumer/Manifest,
  two runs byte identity, docs links; Korean result/report/seal/ZIP/checksum.
  Keep local feature branch and external evidence; no remote write.
