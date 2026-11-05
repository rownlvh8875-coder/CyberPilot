# CORE3 Counterfactual Request Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native execution and routine choices without repeated questions.

**Goal:** Preserve explicit raw request/flags/context and reject invalid adjacent pairs.
**Architecture:** One stdlib module, immutable input carriers and a validated
result constructor/factory; no external source reads or downstream execution.
**Tech Stack:** Existing CPython3.12.13, unittest/Ruff/Ty/Codespell; no installs.
**Spec:** docs/superpowers/specs/2026-11-05-core3-request-snapshot-design.md

## Global Constraints

- Basee0d5225bee52e198afe4aab6c81ffcb244ecbff8; stacked local feature branch.
- Exact classes/fields/types/constants/errors/order as spec; no defaults/coercion.
- Raw finite[-1,1] MSB-first binary32 only, preserve signed zero; no native float/dt/r.
- Same11-field context, adjacent uint64 sequence, ordered int64 times, explicit current reset false.
- Input constructors are carriers; result constructor must not bypass pair validation.
- No model/F61/adapter/native source imports/calls, source getters, CLI/reader/history registry.
- Old runtime/V4/CORE2 matrix/public src/imported77/locks/workflows/profiles unchanged.
- Frozen wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- Actual gates unchanged; no push/PR/main merge/HF/CI dispatch; retain all evidence.

## Review Focus

- Actual-looking scope/profile labels or raw objects must not become qualified input or trigger source property reads.
- Explicit reset/override/active flags must remain required, with reset-before-previous distinguished from reset-inside-pair.
- Clock/controller/config/capture/generation differences and sequence gaps/wrap must not pass as a continuous pair.
- Signed zero/subnormals/int64/uint64 endpoints must be preserved exactly, without coercion or nominal-dt substitution.
- Direct result construction or mutable aliases must not bypass validation or grant V4/F61/vehicle permission.

### Task 1: Pure request pair boundary

**Files:** create integration_tools/request_snapshot.py,
project/test_request_snapshot.py, docs/REQUEST_SNAPSHOT_CORE3_KO.md under
tools/cyberlateral_dev; modify component README and docs/CORE_DEVELOPMENT_BACKLOG_KO.md.
**Interfaces:** consumes only explicit new counterfactual carriers; produces
prepare_request_pair(object,object)->PreparedSyntheticRequestPairV1 with same immutable
snapshots and false authority flags. No other task consumes a new interface here.

- [ ] Fresh immutable Git-export baseline `python -B dev.py verify --output NEW_BASE`.
  Expected:927tests/238compiles/static/frozen wheel PASS, no edited source leakage.
- [ ] Commit spec/plan before module code; external ledger/BASE stand in for unavailable cloud bookkeeping scripts.
- [ ] Write failing actual-boundary tests before module. Literal pair raw previous
  `be800000`,current`3f000000`,seq0/1,time1000000000/1010000000, explicit flags/context.
  Assert exact raw values, input identity, no dt/native/kwargs and false permissions.
  Cover all five focus classes, missing fields, wrong/subclass types, positive/negative
  range and nonfinite words, immutable bytes, int64/uint64 bounds, all context fields,
  prior-reset true vs current true, direct result constructor, stable errors/no fallback,
  import isolation and deterministic repeated results. Expected: missing-feature RED.
- [ ] Implement exact carriers/errors/factory/result validation, no speculative options.
  Focused unittest expected GREEN; Ruff/Ty/Codespell expected PASS.
- [ ] Add Korean guide/README/backlog covering declaration-only source, request-only
  scope, no settings/limited-state authority and no automatic V4 bridge.
- [ ] Run full DEV `dev.py verify` on stable final source to NEW_FINAL.
  Expected:927+actual new methods PASS/240compiles/static/frozen wheel unchanged.
  Whole-root unit/gate work is nonzero; standalone seam model/native/dt/r work remains0.
- [ ] Commit implementation locally after focused validation. One fresh whole-branch
  review may overlap final gate on identical bytes; both must finish before completion.
  Re-grade findings, one Critical/Important RED→GREEN/full-suite fix pass, no re-review.
- [ ] Exercise hand-authored request/context/word/pair acceptance table in two fresh
  processes using independent bit-domain/tuple checks, not new oracle in runtime.
  Expected: literal codes/raw preservation, identical canonical records, source unchanged.
- [ ] Final Git/source/Manifest/wheel checks and external scoped result report.
  Keep branch/worktree; no remote publishing inferred.

Self-review: one deliverable with no shared task interfaces. All five Review Focus
classes are in named tests and final acceptance; permission flags are constructor-
fixed and every public validated-result constructor executes the guards.
