# Cloud-only DEV Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** One explicit command restores pinned private HF DEV evidence against exact Git objects and verifies a new synthetic environment.

**Architecture:** Add read-only fetch to the isolated SDK worker. A stdlib orchestrator validates source identity before creating the app venv, then reuses existing R41 workflow checks. No product arithmetic, CI or lockfile changes.

**Tech Stack:** Python3.12.13, uv0.12.23, dedicated HF SDK2.4.0, existing stdlib/unittest/archive checks.

**Spec:** docs/superpowers/specs/2026-11-02-cloud-restore-design.md

## Global Constraints

- New external output; no pre-existing path/ancestor symlink or source-root mutation.
- Own private Dataset, exact40hex source/revision and64hex archive; no remote writes.
- Git SOURCE manifest/member equality before executing restored code; never execute DRIVER.
- Unchanged lockfile; app and HF environments separate; no new Python download.
- All physical/F61/r/dt gates stay closed. Git push/merge/CI/environment publish excluded.

## Review Focus

- Corrupt sidecar/ZIP or wrong revision must fail before restored source execution.
- Consistently resealed but changed/extra/missing SOURCE must fail Git identity checks.
- Broken/symlink ancestors and existing output must not be followed or overwritten.
- Missing SDK/tool/Python/network prerequisites preserve failure evidence without a success receipt.
- Successful synthetic arithmetic never becomes vehicle/runtime/r policy qualification.

## Task 1: Read-only pinned private fetch

Files: modify tools/cyberlateral_cloud/hf_archive.py; create tests/test_restore_fetch.py.
Produces `fetch(digest, repo, source_commit, revision, output, hub) -> dict`, using
existing preflight/SdkHub. Writes only NEW local archive/checksum, never calls hub.commit.

- [x] Write tests for pinned success; invalid IDs; wrong owner/public repo; corrupted ZIP/sidecar; source-label mismatch; existing output; upstream error redaction; changed privacy.
- [x] Run `python -B -m unittest discover -s tools/cyberlateral_cloud/tests -p test_restore_fetch.py -v`: RED missing fetch (11failures).
- [x] Implement fetch and CLI subcommand with bounded verified downloads.
- [x] Run focused tests GREEN (11) and complete cloud suite (54); commit task1.

## Task 2: Restore source and orchestrate isolated synthetic verification

Files: create tools/cyberlateral_cloud/cloud_restore.py and tests/test_cloud_restore.py.
Consumes Task1 CLI fetch receipt; produces `recover_source(repo,commit,archive,digest,destination) -> dict`
and `verify_restored_workflows(component,workflows,archive,digest) -> dict`, plus CLI.

- [x] Tests RED for exact Git bytes despite dirty local source; altered/missing/extra source/manifest/mode/hash; existing/symlink paths; rejected CLI inputs with no success receipts; wrong saved portable data (14failures).
- [x] Implement minimal source proof/recovery, no DRIVER execution.
- [x] Add orchestration: SDK worker→Git verification→new uv env→runtime origin/dependencies→existing R41 three-run acceptance→HF exact portable comparison→source recheck→receipts.
- [x] Focused14 GREEN, complete cloud68 GREEN; Ruff/Ty/Codespell/compile10 PASS.
- [x] Unchanged full DEV gate PASS:700 tests/static/202compiles.
- [x] Real pinned-private command twice PASS (project and SDK launcher), negative existing-path/wrong-hash rejected. Commit task2.

## Task 3: Usage and handoff

Files: update tools/cyberlateral_cloud/README_KO.md; this plan/spec.

- [x] Document exact pinned private command, prerequisites, output scope, failure handling and gates.
- [x] Fresh whole-branch immutable-tree review: Critical0/Important0, one safe preflight failure-recording/documentation minor deferred; final complete cloud suite rerun.
- [x] Preserve evidence and local feature commits; report verified cloud68/DEV700, two real private restores, one deferred minor, and no push/merge/vehicle changes.

## Execution

Native inline execution, chosen under the user's prior delegation/no-questions instruction.
Existing linked worktree is reused (not nested). Plan helper scripts are cloud resources,
not executable local paths; the equivalent task briefs, BASEs, commands/results and
decisions are tracked in the external progress ledger and this checklist. No fake helper
execution or cleanup of other plan workspaces. Evidence remains preserved for review.
