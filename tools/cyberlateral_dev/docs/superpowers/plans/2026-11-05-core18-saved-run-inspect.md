# CORE18 Saved Run Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify all14saved CORE17 files without executing a model.
**Architecture:** Fixed tree capture, existing pure archive report regeneration,
canonical suite rebuild, exact stored report comparison; new API/CLI only.
**Tech Stack:** CPython3.12.13/existing stdlib/venv.
**Spec:** ../specs/2026-11-05-core18-saved-run-inspect-design.md

## Global Constraints

Base136bd6ec50490b0888d38bd515b80c2b537b248b. Existing algorithms/API unchanged.
Both digests before caller paths,14file single capture, bounded no-follow readers.
Keep existing2MB/4MiB/65536byte bounds. No new model/reference/F61/r/dt/vehicle work,
extraction/replay/arbitrary report JSON intake/repair/writes to input tree.
Actualr/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL; activation/F70UH/V/F71
prohibited. Local commits only; preserve refs/evidence, no merge/push/PR/CI/HF writes.

## Review Focus

1. Both digests precede path metadata/open, with role-specific rejection and no partial receipt.
2. Root/suite/case/comparison missing/extra/symlink/FIFO/size corruption must reject without blocking.
3. Checksummed-but-divergent suite copies and self-checksummed altered reports must reject.
4. Large valid comparison JSON must not inherit Markdown cap; excessive diagnostics retain CORE14 rejection.
5. Valid stored DIFFERENT/M/D/R and historical steps stay data; inspection/model/reference execution0.

### Task1: cross-artifact saved-only inspector

**Files:** Create integration_tools/core_sequence_run_inspect.py,
tools/core_sequence_run_inspect.py, project/test_core_sequence_run_inspect.py,
docs/CORE_SEQUENCE_RUN_INSPECT_CORE18_KO.md, this plan/spec.
Modify README.md and docs/CORE_DEVELOPMENT_BACKLOG_KO.md only.
**Interfaces:** Consume CORE14 _preflight, CORE15 report_suite_archive_bytes,
CORE13 build_suite_archive/_read_archive, CORE9 _capture/CAPS, CORE12 _root/_path,
scenario canonical/GATES. Produce RunInspectError.code and
inspect_archived_run(Path,str,str)->dict, CLI inspection0/error2.

- [ ] Baseline focused23PASS, commit spec/plan; external brief/BASE/ledger.
- [ ] Tests first for14capture/no writes/bytes modes/model0; same/diff and recorded6;
  both malformed digests before path; invalid SHA/CRC and missing/extra layouts;
  symlinks/FIFO/oversize; mismatched but valid/checksummed suite/report; large JSON,
  no arbitrary JSON render, deterministic receipts, original snapshots after mutation;
  import-blocked CLI, exit0onstoredDiff, argument/cache/stdout errors. Expected RED.
- [ ] Implement minimal new inspector/CLI, focused GREEN, existing code untouched.
  Human guide/backlog/README links, Ruff/Ty/Codespell PASS.
- [ ] Full `python -B dev.py verify --output <NEW external>` -> all tests,
 284own compiles/static PASS, frozen wheel unchanged. Commit implementation.
- [ ] Independent2runs on existing CORE17 fresh/historical/historical_marker folders,
  API/directCLI/import-blockedCLI receipt parity, exactly14regular reads and unchanged
  bytes/modes; tampered copies reject, pure model/reference/F61/r/dt0. No new fixtures.
- [ ] One final fresh read-only reviewer, at most one TDD Critical/Important fix pass
  and full gate, no rereview; minors deferred, exhaustive rulings/costs.
- [ ] Source584/prior576,refs20,gate Manifest/cloud consumer/docs/reproduction,
  Korean report/result/seal/ZIP/checksum; preserve branch/worktree/external evidence.
