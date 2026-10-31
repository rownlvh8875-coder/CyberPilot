# R20 Owned Synthetic Message Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve owned message bytes and explicit same-frame ledgers/settings/prior declarations without a reader/model adapter.

**Architecture:** Frozen stdlib envelopes pass a pure structural validator. An
opt-in closed native demonstration reuses R19 preflight and schema context; the
default R19 and pure verification behavior remain unchanged.

**Tech Stack:** CPython3.12.13, unittest/dataclasses, separate pinned pycapnp2.1.0.

**Spec:** ../../OWNED_MESSAGE_BOUNDARY_R20.md

## Global Constraints

- Public0.3.0 wheel/lock/goldens/default pure CI unchanged.
- Native only through explicit isolated verified worker; no external message input.
- Controller/Runtime/CAN/F61/actual input/model work/r/dt by new code=0.
- Structural declarations are not authentic native validity/atomicity/history.
- Static Gate FAIL, R_BUDGET UNRESOLVED; actual activation/F70UH/F70V/F71 forbidden.
- Existing isolated feature tree/inline workflow; one fresh final reviewer.
- Every commit includes [skip ci]; no main merge or deployment.

## Review Focus

- Consistent forged labels must never be presented as native validity/custody.
- Mutable/subclassed inputs must reject without executing user properties.
- Defaults/duplicate/missing ledgers must not silently become explicit writes.
- Cross-frame or source/model prior-state mismatches must reject, not initialize.
- Existing R19 observations/default CI must not silently activate native behavior.

### Task 1: Pure owned envelope boundary

**Files:** Create integration_tools/owned_message_boundary.py and project/test_owned_message_boundary.py.
**Interfaces:** Frozen required records and prepare_owned_frame(OwnedFrame)->PreparedOwnedFrame exactly as spec.

- [x] Write tests for immutable preservation; default/unknown/missing constructors;
  hostile objects/subclasses; source/stamp/schema; bytes size/hash/mutable rejection;
  field-ledger completeness/digest binding; settings domains; zero/resumed prior
  state consistency and stage; report-only custody semantics.
- [x] Run targeted tests; expected missing-module assertions RED.
- [x] Implement ordered fail-closed validator, no native import/model calls.
- [x] Run targeted and full dev.py verify; expected GREEN with sealed wheel intact.
- [x] Commit with [skip ci]; ledger exact count/result.

### Task 2: Closed native demonstration and verification

**Files:** Create native_qualification/owned_demo.py and test_owned_observations.py;
modify worker.py/run.py only for explicit --owned-boundary; add pure mode guard tests.
**Interfaces:** owned_demo.demonstrate(car)->dict; worker.observe(...,owned_boundary=False);
run.qualify(...,owned_boundary=False). Default observations still original R19 SHA.

- [x] Write missing-demo/mode RED tests and literal output assertions for four
  fixed cases,0.3 Float32 readback, signed zero/default proof, frozen-after-mutation,
  expected rejection codes and blocked actual-reader/model gates.
- [x] Implement fixed local builder producer + declaration ledger, no arbitrary
  input parser. Only --owned-boundary enables it in the verified R19 schema context.
- [x] Run two workers, independently check output, original R19 SHA, Ruff/Ty/
  Codespell/own compile and full component gate. Fresh archive/new native env
  reproduces observation bytes; include unchanged workflow in relocated source.
- [x] Commit and request one fresh whole-branch final review; one RED/GREEN fix
  pass for Important/Critical, ledger all rulings/deferred minors.
- [ ] Record results/docs; publish existing feature/Draft PR, run exact-head pure
  CI and verify downloaded manifest. Native GitHub CI remains NOT_RUN.
- [ ] Seal external evidence/report; final handoff states structural-only limits.

Self-review: complete spec coverage; Task1 consumes opaque bytes only, Task2
supplies native bytes from closed fixtures, so neither is an external native reader.
Final post-commit publication/sealing progress lives in external task receipt.
