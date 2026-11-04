# R64 Saved Browser Verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans; inline execution already delegated.

**Goal:** Verify current-format saved browser outputs without another browser/model run.

**Architecture:** Separate read-only stdlib consumer with bounded fixed-layout
snapshot, closed canonical manifests, typed record/hash association and exact
existing summary regeneration. No producer/classifier or app changes.

**Tech Stack:** Existing Python3.12.13/Git/cloud unittest/static tooling; pathlib,
os/stat/json and unchanged artifacts.manifest/browser_summary.render_summary.

**Spec:** docs/superpowers/specs/2026-11-04-r64-saved-browser-verifier-design.md

## Global Constraints

- Basecc453796483edfc28c92babf76280154b906d549; re-use clean host-owned linked worktree.
- API verify_saved_browser(root: Path) -> dict; CLI --input, no output or active runner.
-38regularfiles/seven dirs;8MiB perfile/32MiB total; strict typed RESULT V1/current R62 SUMMARY.
- PASS exit0, recordedFAIL exit1, invalid exit2; no new layout PASS/source attestation.
- Preserve browser_smoke/probe/summary, artifacts, workflow_checks, app/rootREADME/locks/workflows and canonical guide bytes.
- No main merge/HF writes/vehicle work; preserve old/new evidence and closed gates.

## Review Focus

- Resealed or partially written records: require all ownership/record links and completion marker, never infer runtime authenticity.
- Live filesystem races: no atomic-snapshot claim; bounded no-follow regular-file reads, no FIFO blocking or mutation.
- Historical/future summary formats: explicit current-format scope, reject mismatch without repair or migration.
- Valid recorded FAIL/global-only failure: preserve exit1 and raw status/counts, never promote to PASS or reclassify metrics.
- Passive consumer dependencies: stdlib only and no browser/app/model/SDK import, invocation, network or writes.

### Task 1: Complete read-only consumer

**Files:** Create tools/cyberlateral_cloud/browser_verify.py and
tools/cyberlateral_cloud/tests/test_browser_verify.py; create
tools/cyberlateral_cloud/docs/SAVED_BROWSER_VERIFY_R64_KO.md; add a short link to
tools/cyberlateral_cloud/README_KO.md. Do not edit pinned RECOVERY_R62_KO.md.

**Interfaces:** Consumes fixed existing RESULT schema1 and render_summary(result,
file_sha256)->bytes, artifacts.manifest(dict[str,bytes])->bytes. Produces the API/
CLI record and exit semantics fixed by spec; no downstream task/shared interface.

- [ ] Baseline full cloud gate, expected122/19/static PASS; commit spec/plan.
- [ ] Write focused failing tests before module: real prepare_reports plus synthetic
observation test record; cover valid0/FAIL1, deterministic/no-write/no-import CLI,
missing/extra/partial closure, corrupt/resealed associations, root/nested manifest,
strict JSON/typed flags/version/order, unknown codes/null, summary mismatch,
symlink/ancestors/FIFO,8MiB/32MiB bounds and path-safe errors.
Run APP -B -m unittest discover -s tools/cyberlateral_cloud/tests -p test_browser_verify.py -v.
Expected RED for missing verifier behavior, not an unrelated test setup error.
- [ ] Implement minimal verify_saved_browser and CLI exactly per spec; expected new
focused suite GREEN. Preserve inputs by bytes/file-set comparison, no mocks.
- [ ] Add accurate Korean usage/link; full cloud gate expected baseline122+actual
new methods,21owned Python compiles, Ruff/Ty/Codespell PASS. No app/source changes.
- [ ] Actual passive consumers of two saved PASS roots and sealed globalFAIL,
each twice stdout-identical; expected exits0/0/1 and byte-identical input trees.
New corrupt/partial copies expected2, no fresh browser/model/R41 execution there.
- [ ] Commit; full cloud unit repeat expectedallPASS and ledger Task1 complete.

## Finish

- One fresh whole-branch review against original base; Important/Critical fixes
only in one TDD pass, minors deferred and every declined assurance ruled.
- Normal feature push/Draft PR/attach; actual exact-head cloud CI artifact and
remaining PR CI success/SKIP statuses, no main/HF mutation.
- Deterministic two ZIPs, independent closure/identity/test/consumer verification,
final live Git/PR/HF receipt outside immutable ZIP. Retain workspace per spec.

Self-review: one task/no shared interfaces. Focus items have direct owned consumer
tests and actual saved-bundle checks; no new oracle or numerical/policy decision.
