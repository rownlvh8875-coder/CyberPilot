# Immutable Replay Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; one independent final whole-change review. Steps use checkbox syntax.

**Goal:** Remove moving replay references and reject incompatible or modified inputs before decode/replay.

**Architecture:** A stdlib-only lock reader verifies declared source identity and exact compressed artifact hashes. The existing test runner consumes verified bytes and retains its numerical comparison logic unchanged.

**Tech Stack:** Python 3.12 stdlib unittest, Git metadata, JSON lock; existing isolated DEV verification tools.

**Spec:** `docs/superpowers/specs/2026-11-02-replay-reference-bundle-design.md`

## Global Constraints

- Producer c8fb906815530460ed156f14e09e1f312bb0f851; artifact revision eab2cc2b1f6de3773617937868442520c7ef554c, only after index/blob verification.
- Production parameters, tolerances and workflow checks unchanged; no golden generation or fallback.
- No native replay/Controller/Runtime/log decode/F61/r/dt/candidate evaluation; synthetic fixture tests only.
- Local branch only, no push/merge/CI dispatch.

## Review Focus

- Corrupt cache, missing artifact or transfer failure must stop before any replay.
- Modified schema/submodule/source and shallow checkouts must not bypass compatibility checks.
- Invalid/duplicate JSON, unsafe names and branch-like revisions must reject clearly.
- Workers must use verified bytes, not reopened mutable paths.
- Full and selected process inventories must preserve existing comparison coverage.

### Task 1: Exact bundle and stdlib validation

**Files:** Create `openpilot/selfdrive/test/process_replay/reference_bundle.py`, `reference_bundle.json`, `test_reference_bundle.py`.

**Interfaces:** `ReferenceBundle.load(path)`, `validate_checkout(root)`, `reference_name(segment, process)`, `reference_url(name)`, `verify_bytes(name, raw)`, `prepare_references(pairs, cache, fetch)` returning name-to-bytes dictionary. `ReferenceBundleError` provides stable diagnostic codes.

- [ ] Fetch historical index/tree and compressed blobs outside the repository; verify declared producer, Git blob/size and calculate SHA256. Generate the tracked lock with apply_patch.
- [ ] Write failing unittest cases for strict lock validation, immutable URLs, corrupt/missing bytes, wrong source/opendbc/schema, legacy override, cache precedence and all-selected preflight.
- [ ] Run `python -B openpilot/selfdrive/test/process_replay/test_reference_bundle.py -v`; observe missing feature failures, then implement minimal validator.
- [ ] Run the same command; all cases pass. No project/native modules loaded.
- [ ] Commit scoped helper/lock/tests/design/plan after verification.

### Task 2: Runner integration and verification

**Files:** Modify `test_processes.py`, `README.md`; extend `test_reference_bundle.py`.

**Interfaces:** stdlib preflight before heavy imports; selected-reference preparation before input logs; workers receive verified bytes.

- [ ] Add regression tests executing the runner in an isolated fixture checkout with protected-source mismatch and `--update-refs`: exit2 without native imports or data/network work. Exercise worker byte consumption with controlled stdlib dependency doubles only.
- [ ] Observe RED, then remove floating baseline selection/URL and integrate source/byte preflight; reject baseline updates and disagreeing legacy pins.
- [ ] Run the complete new unittest suite; run the existing isolated DEV gate (700 tests expected before this root-only change), scoped Ruff/Ty/Codespell and in-memory compile.
- [ ] Independently review the full diff and fix Important/Critical findings with RED→GREEN regressions.
- [ ] Commit integration/docs after fresh verification. Report local commit, actual counts and root replay NOT_RUN; do not claim CI green or push/merge.
