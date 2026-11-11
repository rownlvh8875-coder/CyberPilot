# CORE52 Serialized Recording Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicitly diagnose canonical synthetic recording bytes through existing boundaries.

**Architecture:** CORE41 decode, then unchanged CORE49/46/7 validation and diagnostics.
No new parser, math, result schema or file operations.

**Tech Stack:** Existing Python 3.12, unittest, Ruff/Ty/Codespell; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-11-serialized-recording-diagnostics-design.md`

## Global Constraints

- Exact bytes, 1..262144 bytes; canonical CORE41 recording, 2..128 frames.
- Exact explicit CORE5 contexts tuple; validate all before N-1 synthetic steps.
- Preserve CORE7 result, declared feed, differences, errors and false permissions.
- No inference, fallback, file reader, new serialization or public wheel change.
- Actual r/T2/vehicle scale=null; Static Gate FAIL; actual use NOT_ALLOWED.
- Local feature only; push/PR/main integration/CI NOT_RUN; preserve evidence.

## Review Focus

- Invalid bytes must reject before touching hostile contexts or running a prefix.
- Metadata/permission tampering must not become execution authority.
- Repeated calls must revalidate contexts, not cache acceptance.
- Raw signed zero/subnormals and int64 time endpoints must survive decoding.
- Later model failure must not be swallowed or described as zero-work success.

### Task 1: canonical bytes diagnostic boundary

**Files:**
- Modify: `integration_tools/offline_recording_diagnostics.py`
- Create: `project/test_serialized_recording_diagnostics.py`
- Create: `docs/SERIALIZED_RECORDING_DIAGNOSTICS_CORE52_KO.md`
- Modify: `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`

**Interfaces:**
- Consumes: `decode_recording(raw: object) -> FinishedSyntheticRecordingV1` and
  `check_recorded_synthetic_sequence(recording: object, contexts: object) -> SyntheticSequenceCheckV1`.
- Produces: `check_serialized_synthetic_recording(raw: object, contexts: object) -> SyntheticSequenceCheckV1`.

- [ ] Write focused tests with literal states `(6,8,2,5)`, `(7,-8,-2,6)`,
  `(8,4,2,7)`, three real steps, early differences and full declared-state feed.
  Exercise every Review Focus, canonical rejection, late invalid context/index,
  exact error precedence, unchanged errors, no mutation and no automatic execution.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p 'test_serialized_recording_diagnostics.py' -v`.
  Expected: assertion failures for missing callable, zero errors. Commit preregistration.
- [ ] Implement the decode-then-diagnose composition; same command must PASS.
- [ ] Write a complete runnable two-frame synthetic example and boundary guide;
  run it under `PYTHONPATH=src .venv/bin/python -B`, expect `MATCH 1 2`.
- [ ] Run `.venv/bin/python -B dev.py verify --output /absolute/NEW-output`.
  Expected: all tests/static checks/own compiles PASS, frozen wheel and CORE32 pins
  unchanged, full Manifest verified. Re-run focused tests and commit completed task.
- [ ] Freeze the head and request one independent final review; disposition any
  findings under executing-plans; preserve custody and seal evidence twice.
