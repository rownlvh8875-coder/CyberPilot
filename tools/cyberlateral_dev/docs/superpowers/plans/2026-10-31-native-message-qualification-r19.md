# R19 Native Message Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproducible actual pycapnp synthetic observations without a native adapter.

**Architecture:** A stdlib parent verifies pinned inputs and launches isolated
workers in a separate binary-only native environment. Workers inspect only
internally constructed messages and produce observations plus process receipts.

**Tech Stack:** CPython3.12.13, pycapnp2.1.0 pinned manylinux x86_64 wheel, unittest.

**Spec:** ../../NATIVE_MESSAGE_QUALIFICATION_R19.md

## Global Constraints

- Component lock/default CI/public API0.3.0/sealed wheel unchanged.
- Native import/schema load only in explicit isolated worker, no original modules.
- Controller/Runtime/CAN/F61/actual vehicle input/r/dt calculation=0.
- Q05 and unrestricted lifetime/native activation remain NOT_QUALIFIED.
- Static Gate FAIL, R_BUDGET UNRESOLVED; no main merge or vehicle activation.
- Inline execution with one fresh final reviewer; commits include [skip ci].

## Review Focus

- A mutated wheel or installed extension must reject before native import.
- Default zero/False must never be mistaken for explicit field provenance.
- NaN/inf/overflow must produce canonical JSON, not crash or silently clamp.
- Receipt equality must not claim portable OS/ABI identity or actual call custody.
- Existing output/symlink paths and native execution through the pure gate reject.

### Task 1: Opt-in observation tool and fail-closed tests

**Files:** Create native_qualification/run.py, worker.py, requirements.txt;
project/test_native_qualification.py; native_qualification/test_observations.py.

**Interfaces:** run.qualify(python:Path,wheel:Path,output:Path)->dict;
worker.verify_inputs(wheel:Path,schema:Path)->dict;
worker.observe(wheel:Path,schema:Path)->dict returns observations and receipt.
Neither module imports native dependencies at import time.

- [x] Add pure tests for missing implementation, bad source/wheel rejection,
  installed-file mutation, existing/dangling output rejection and inert import.
  Add opt-in native tests for independently specified exact0.3/signed-zero
  readback, wrong-schema generic classes, defaults, canonical special values,
  matched reader/builder schema and deliberately incomplete Q statuses.
- [x] Run pure tests, observe missing-feature assertions fail.
- [x] Implement smallest pinned preflight/worker/report orchestration. Separate
  process receipt from deterministic observations; reject mismatched repetitions.
- [x] Run pure tests and actual opt-in characterization tests. Record observed
  behavior, not guessed acceptance/lifetime guarantees.
- [x] Run full dev.py verify, plus explicit Ruff/Ty/Codespell/own compile on new
  native directory, without adding native execution to existing pure gate.
- [x] Commit implementation and tests with [skip ci].

### Task 2: Reproduction, review and feature publication

**Files:** README opt-in instructions; docs/NATIVE_MESSAGE_QUALIFICATION_R19_RESULTS.md.
External audit directory holds receipts/logs/TDD/ledger and review package.

**Interfaces:** Task1 JSON reports, SHA256SUMS and fixed source identities.

- [ ] Run qualifier twice, check observation bytes identical and all receipts.
- [ ] Fresh git archive/new native environment run; compare observation bytes,
  retaining distinct environment receipts. Recheck original source/Git guards.
- [ ] Write exact observations/limits/reproduction results and rerun full gate.
- [ ] Commit, request one fresh whole-branch review; one RED/GREEN fix pass for
  Important/Critical, ledger all scope rulings and deferred minors.
- [ ] Publish existing feature branch/Draft PR only; dispatch existing pure CI,
  verify exact HEAD and retained artifact. Native CI remains NOT_RUN.
- [ ] Final handoff states Q coverage, test counts, hashes and remaining block.

Self-review: source/receipt/default/precision/lifetime/custody/fail-closed and
reproduction requirements are covered; Q05/Q06 are reported as limits, not built.
