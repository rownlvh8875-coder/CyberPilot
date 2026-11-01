# R32.1 Report Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** deterministic rejection of looping source paths and scoped visual evidence.
**Architecture:** narrow existing input-resolution error translation, unchanged
reader/renderer; external bounded browser probe over saved synthetic HTML.
**Tech Stack:** existing CPython3.12.13 stdlib/unittest/pinned DEV tools; installed Chromium/Node diagnostics only.
**Spec:** `docs/superpowers/specs/2026-11-01-r321-report-finish-design.md`

## Global Constraints

- Catch only input resolve OSError/RuntimeError, REPORT_INPUT_FILE with cause.
- Keep invalid output guards before input work, existing location/runtime/file contracts.
- CLI exit2/exact rejection, no traceback/output for loops; no broad exception swallow.
- Only runtime scenario_report_run.py and test_scenario_report_cli.py edits; old public/native/source protected.
- No new deps/workflow/model/F61/Runtime/CAN/vehicle/r/dt/activation; renderer model calls0, inherited unit/CI work additional.
- Browser own profile/loopback only,25s total/4s request bound; no laptop assumption or screenshot overclaim.

## Review Focus

- Ancestor source loops as well as final self-links reject without publication.
- Existing output and missing parent keep precedence over invalid input resolution.
- OSError/RuntimeError input failure is not confused with later internal failures.
- Valid report bytes and all closed gates remain unchanged despite error-path change.
- Browser DOM/screenshot observations must not become full accessibility/vehicle qualification.

### Task 1: reproduce and narrowly fix M1

**Files:** modify `integration_tools/scenario_report_run.py`, `project/test_scenario_report_cli.py`.
**Interfaces:** existing run_report(Path,Path)->dict and CLI --input/--output unchanged.

- [ ] Write two regressions: isolated self/ancestor-loop CLI→exit2/exact stderr/no output;
  direct API→REPORT_INPUT_FILE/RuntimeError cause and output guard precedence.
- [ ] Run `uv run --locked python -B -m unittest discover -s project -p test_scenario_report_cli.py -v`;
  Expected RED: current traceback/exit1 and uncaught RuntimeError.
- [ ] Narrowly translate input-resolution errors; same CLI and data suites PASS,
  targeted Ruff/Ty/Codespell PASS; commit `[skip ci]`.

### Task 2: scoped browser check, complete verification and delivery

**Files:** add `docs/SCENARIO_REPORT_R321_RESULTS.md`, update R32 guide with follow-up link.
**Interfaces:** unchanged saved R31 six-file inputs and R32 portable2 output.

- [ ] Bounded blank-page/CDP report diagnostic; inspect screenshots if available,
  otherwise record blocker/local read-only check. Do not alter product for environment failure.
- [ ] Full `uv run --locked python -B dev.py verify --output NEW` local/fresh PASS;
  repeat saved profiles, exact prior HTML/VIEW bytes, import tripwire/source/original guards PASS.
- [ ] Fresh whole-branch reviewer, all exclusions dispositioned, one Important/Critical
  TDD fix pass if needed; record any deferred minors. Commit docs, normal feature
  push, exact-head dedicated pure CI/artifact and existing Draft PR2 update.
- [ ] Deterministic twice ZIP/CRC/fresh extraction/checksums; external final receipt.
