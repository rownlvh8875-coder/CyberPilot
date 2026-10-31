# R23 Fixed Native Sequence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify one preregistered four-step synthetic native/model sequence and
derive reported counts from validated actual observations.
**Architecture:** Closed producer carries verified model state across four owned
native messages. Independent SHA-pinned literal input/output table, shared layout
helpers only. Parent validates exact coverage/counts before publication.
**Tech Stack:** CPython3.12.13, unittest/JSON, unchanged public0.3.0, separate pinned
pycapnp2.1.0 Linux x86_64 environment.
**Spec:** ../../NATIVE_SEQUENCE_R23.md

## Global Constraints

- Literal table committed before any R23 model execution; never bless results.
- Exactly four fixed sequence steps; no arbitrary input/log/history API.
- No Controller/Runtime/CAN/F61/actual/r/dt/activation/deployment/main merge.
- R19/R20/R21/R22 observations, public wheel/lock/default pure CI and frozen77 unchanged.
- R_BUDGET UNRESOLVED, Static Gate FAIL; Candidate/Runtime NO_GO, F70UH/V/F71 closed.
- Existing isolated feature/inline work; one fresh final review; [skip ci] commits.

## Review Focus

- Prior requested or pre-inactive limiter output must not replace prior final state.
- Two identical but reduced-coverage workers must reject before output publication.
- Correct index with altered state/settings/negative-zero input must reject before step.
- Summary counts derive validated builtin integers, never bool coercion/constants.
- Default modes must not execute new work; native counts exclude test/stage aggregates.

### Task 1: Closed reference and coverage gate

**Files:** new sequence_reference.py/sequence_consumption.py under integration_tools;
native_qualification/coverage.py; project/test_sequence_consumption.py and
project/test_native_coverage.py. Existing public/R22 files remain untouched.
**Interfaces:** expected_input(index),expected_output(index); consume_fixed_step
(index,sample,state); validate_coverage(observations,mode)->int per spec.

- [x] Commit spec/plan/literals first. SHA receipt retained.
- [x] RED missing-feature tests for four outputs2,-2,0,2/full states/clips/trace;
  state reset/crossed settings/signed-zero mismatch before step; full output
  mutation/reference identity/copy isolation; no simulation/initialization;
  coverage missing/extra/duplicate/reorder/wrong flags/count/bool rejection.
- [x] Implement layout-only literals, exact input/output single-step gate and
  stdlib-only coverage validator. R22 five accepted/three rejects; R23 ordered4.
- [x] Targeted tests + full dev.py gate/static checks PASS; commit and ledger.

### Task 2: Native sequence integration and handoff

**Files:** native_qualification/sequence_demo.py, run.py/worker.py;
project/test_sequence_mode.py, native_qualification/test_sequence_observations.py;
README/results docs. No original/public/controller changes.
**Interfaces:** --model-sequence exact public wheel; parent consumes Task1 validator;
demo carries output.next_state into next frame's previous snapshot.

- [ ] RED mode/wheel/conflict/output-preservation/worker-reduced-coverage tests.
- [ ] Implement separate producer/mode and validated R22/R23 summary counts.
- [ ] New native env, two R23 workers, literal output tests; R19–R22 observation
  hash controls and internal count guards. Full pure suite and native static/compile.
- [ ] Fresh archive/new native/dev env repeats native observations/SUMMARY; retain
  environment receipts without cross-env equality claims. Commit/ledger.
- [ ] One fresh whole-branch read-only review; Critical/Important one RED/GREEN fix
  pass, minors ledgered. Exact-head pure CI, Draft PR update,94 downloaded hashes.
- [ ] Original guards unchanged; external evidence/reproduction ZIP seal/handoff.

Self-review: all five review-focus cases have negative tests above; source-derived
literal table includes complete states/trace/projection, not final command alone.
Post-commit publication/seal completion recorded externally to avoid commit cycles.
