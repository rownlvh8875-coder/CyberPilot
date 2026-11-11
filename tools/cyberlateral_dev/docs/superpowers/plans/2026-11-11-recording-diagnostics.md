# CORE49 Recorded Synthetic Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicitly diagnose finished synthetic recordings using unchanged CORE46 and CORE7.
**Architecture:** Compose full preflight with the existing declared-sequence checker; return its existing result without a new wrapper or mathematics.
**Tech Stack:** Existing Python3.12.13,stdlib/unittest,configured Ruff/Ty/Codespell.
**Spec:** `docs/superpowers/specs/2026-11-11-recording-diagnostics-design.md`

## Global Constraints

- Exact API: `check_recorded_synthetic_sequence(recording: object, contexts: object) -> SyntheticSequenceCheckV1`.
- No changes to existing CORE3..7/41/46/model/fixtures/wheel/CI/dependencies.
- Preserve declared state feed,raw words,integer time and all actual-use false flags.
- Full preflight before any synthetic model step; runtime errors may follow nonzero work.
- No actual Controller/Runtime/CAN/F61/input/dt/r; actual r/T2/scale=null and all gates unchanged.
- Seven allowed paths; local feature commits only. Push/PR/main/CI NOT_RUN.

## Review Focus

- Compatible pairs must not bypass the finished recording's fixed metadata rejection.
- A stale prior receipt or late invalid context must not authorize a model prefix.
- Early differences must not repair declared state or suppress later diagnostics.
- Raw signed zero/subnormal words and irregular live/replay times must survive without deriving dt or indices.
- A failed later model call must not become a successful partial result or a zero-work claim.

## Task 1: explicit recorded-sequence API

**Files:** Create `integration_tools/offline_recording_diagnostics.py`, `project/test_offline_recording_diagnostics.py`, `docs/RECORDING_DIAGNOSTICS_CORE49_KO.md`, this plan and its spec. Append `README.md` and `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`.
**Consumes:** `preflight_recording_input(recording,contexts)` and `check_synthetic_sequence(frames,contexts)`.
**Produces:** Exact API above; unchanged CORE7 result and CORE46/CORE7 exceptions.

- [ ] Add literal real-behavior tests: three transitions yield MATCH/states(6,8,2,5),(7,-8,-2,6),(8,4,2,7); minimum1step/maximum127steps; early DIFFERENT indices(0,) and declared feed10; late DIFFERENT(2,); all differences(0,1,2); no input repair; fixed metadata/foreign type/context container/late context/late index rejection with0steps; prior receipt rejection and fresh revalidation; false permissions; raw/time preservation; model failure/unknown exception propagation; no default policy args; cold import0steps.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p 'test_offline_recording_diagnostics.py' -v`. Expected assertion failures naming missing CORE49,not import/setup errors. Commit RED tests/spec/plan.
- [ ] Implement the exact function and usage guide. Explain explicit invocation,existing result/errors,N-1 synthetic steps,no repair/rollout/first-anchor/source/time/F61 authority. Append README/backlog without rewriting historical records.
- [ ] Rerun the focused tests and existing preflight/sequence tests; all PASS. Run configured owned-path static checks and fresh `.venv/bin/python -B dev.py verify --output NEW_EXTERNAL_OUTPUT`; all tests/static/342 compiles/98 Manifest,unchanged wheel/CORE32 pins PASS. Report actual test count.
- [ ] Commit verified code/docs,rerun focused task completion,and record exact head/ledger.

## Completion

- One fresh independent whole-branch review at frozen head. Regrade before fixing; one TDD fix pass for important findings,minor findings deferred.
- Source/ref custody and deterministic evidence ZIP/CRC/Manifest/rebuild verification outside checkout. Keep workspace under the preservation constraint.
- Native execution under existing user delegation; no repeated approval prompt. Missing native helper resources use explicit manual brief/ledger/review records.
