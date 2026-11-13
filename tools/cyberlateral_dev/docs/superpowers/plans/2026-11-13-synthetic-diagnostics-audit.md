# Synthetic Diagnostics Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recompute SHA-pinned declared synthetic input and detect altered saved diagnostics.

**Architecture:** Reuse unchanged CORE66 capture/validation and CORE61 input capture,
preflight and calculations. Factor only CORE61's captured-bytes diagnostic formatter;
new audit API compares entire records and an opt-in CLI exposes the result.

**Tech Stack:** Existing Python3.12.13, unittest, Ruff/Ty/Codespell; no new dependencies.

**Spec:** `../specs/2026-11-13-synthetic-diagnostics-audit-design.md`

## Global Constraints

- Exact starting commit2030606ee73f452648f783b24f091f5b68d3a9fd; isolated existing worktree, feature branch.
- Two valid SHA strings before path work; saved capture and input capture once each.
- Existing wheel/model/formats unchanged; explicit synthetic execution only, N-1steps.
- REPRODUCED0/DIFFERENT1 is audit comparison, separate from saved diagnostic status.
- JSON output2097152bytes cap, fixed errors2, no retries/writes/cache; partial stdout may remain.
- R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/scale=null; all actual-use authority false.

## Review Focus

- A valid saved DIFFERENT must reproduce as audit0 while keeping the diagnostic1 meaning.
- A checksum-consistent fake final computed/saved state must be detected by real recomputation.
- A late invalid input must reject before all steps; late operational errors may have nonzero work.
- Captured files replaced afterwards must not be reopened; no claim about later path contents.
- Missing rows and header differences must remain visible without silent truncation or state repair.

---

### Task 1: Complete audit API, CLI and development guide

**Files:**
- Modify: `integration_tools/recording_input_run.py` (captured-byte formatting only).
- Create: `integration_tools/recording_diagnostics_audit.py`.
- Create: `tools/recording_diagnostics_audit.py`.
- Test: `project/test_recording_diagnostics_audit.py`.
- Create: `docs/RECORDING_DIAGNOSTICS_AUDIT_CORE68_KO.md`.
- Modify: `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`.

Paths are relative to tools/cyberlateral_dev. The spec and this plan are also scoped.

**Interfaces:**
- Consumes existing `inspect_recording_diagnostics(Path,str)->dict`,
  `recording_input_run._capture(Path)->bytes`, canonical serialization and current diagnostics.
- Produces `_diagnose_captured(raw:bytes)->dict` preserving CORE61 records and
  `audit_recording_diagnostics(Path,str,Path,str)->dict` as specified; opt-in CLI above.

- [ ] **Step 1: Establish baseline and write failing behavior tests.**
  Run old CORE61/64/66 tests once. Add literal three-transition fixtures based on
  existing independent CORE61 fixture. Assert REPRODUCED0/3new steps, saved
  DIFFERENT reproduced0, and coherent fake final value202 returns audit DIFFERENT1.
  Pin wrong-input-size/SHA zero-step rejection, late semantic error zero-step,
  missing rows/header comparison and declared-feed preservation.
- [ ] **Step 2: Observe RED.**
  Run `.venv/bin/python -B -m unittest discover -s project -p test_recording_diagnostics_audit.py -v`.
  Expected: assertion failures for missing CORE68 feature, not import errors.
- [ ] **Step 3: Implement the captured formatter and audit API.**
  Preserve old `run_recording_input` capture/SHA behavior; move the existing checked
  result serialization unchanged to `_diagnose_captured`. Validate saved/input
  identity, recalculate once and compare full canonical headers/rows. Return both
  records and exact work/authority fields. Do not add an oracle or repair data.
- [ ] **Step 4: Implement opt-in CLI and failure tests.**
  Extend the RED tests first for every required flag/duplicate/SHA/unknown option,
  exact canonical output, repeated fresh-process determinism, short/broken/partial
  stdout, output size/serialization failure, globals restoration and no file writes.
  Implement using existing CLI conventions; no execution on --help/usage failure.
- [ ] **Step 5: Verify GREEN and old behavior.**
  Run new tests plus old CORE61/64/66; expected all PASS. Run scoped Ruff, Ty,
  Codespell and compile; expected PASS before starting the expensive full gate.
- [ ] **Step 6: Document and run the whole DEV gate.**
  Guide: CORE61 input example→CORE64 saved diagnostics→CORE68 --run, both SHAs,
  separate statuses and same-algorithm limitations. Add README/backlog entry.
  Run `.venv/bin/python -B dev.py verify --output <new external directory>`.
  Expected full tests/static/compile/wheel/reference/Manifest PASS; actual counts
  from ledger, existing wheel and CORE32 pins unchanged. Preserve any failure.
- [ ] **Step 7: Commit and complete task.**
  Commit only the nine scoped files after qualified tests; rerun the task's new
  unittest command as task-done, preserving the exact BASE and result in the ledger.

Then request a fresh whole-branch review including spec, complete diff, test evidence
and rulings. Fix important findings test-first; do not silently broaden the feature.
Use normal GitHub publication under existing authorization, no force pushes or skip
checks. Preserve original stuck CI records as historical; do not claim unobserved CI PASS.
