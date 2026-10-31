# R22 Fixed Synthetic Model Consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify exactly five fixed synthetic single-step model consumptions against preregistered independent literals, without actual input/vehicle execution.

**Architecture:** SHA-pinned source-derived registry gates the complete input and
compares complete output. Explicit native mode extends only accepted R21 fixed
fixtures; all older modes and public package stay unchanged.

**Tech Stack:** CPython3.12.13, unittest/JSON/dataclasses, sealed public0.3.0,
separate pycapnp2.1.0 environment and exact native/schema/public-wheel preflight.

**Spec:** ../../MODEL_CONSUMPTION_R22.md

## Global Constraints

- Only exact five registered inputs; one p.step per successful invocation, no chains.
- Commit expected literals BEFORE first R22 execution, never bless observed outputs.
- No Controller/Runtime/CAN/F61/actual input/r/dt/deployment/main merge.
- Default R19/R20/R21 and pure workflow/public wheel/lock/old77 frozen files unchanged.
- New reference is separate DEV data, no vehicle scale/rate/timing authority.
- Static Gate FAIL, R_BUDGET UNRESOLVED; Candidate/Runtime NO_GO, F70UH/V/F71 closed.
- Existing isolated feature/inline workflow, one fresh final review, [skip ci] commits.

## Review Focus

- Correct case ID with changed values/state/limits/negative-zero must reject before step.
- Expected literals/assembly must not import or evaluate the model to bless results.
- Full quantization/clips/flags/state/projection must be checked, not just final command.
- Model call counts must distinguish per-worker execution from aggregate test work.
- No implicit model work in old modes or rejected semantic rows.

### Task 1: Preregister and gate closed consumption

**Files:** reference/r22_model_expected_v1.json, docs/MODEL_CONSUMPTION_R22.md,
integration_tools/fixed_model_reference.py, model_consumption.py,
project/test_model_consumption.py.
**Interfaces:** load_reference()->dict, expected_input(case_id)->dict,
expected_output(case_id)->dict; consume_closed_case(case_id,sample,state)->LateralOutput,
verify_output(case_id,output)->None. Error codes per spec.

- [x] Commit spec/plan/literal table first; hash and preserve receipt before any R22 step.
- [x] Write missing-feature RED tests:literal outputs for all five, step count exactly
  one, mismatched/unknown/hostile input rejected before work, no initialization/
  simulation, no input mutation, complete output mutation rejection/reference hash
  mismatch/deep-copy isolation, independent expected assembly with model disabled.
- [x] Implement strict reference/closed input gate, exactly one real step and complete
  expected-output comparison. No general model wrapper or fallback.
- [x] Targeted and full dev.py gate/static/wheel checks PASS; commit/ledger.

### Task 2: Explicit native consumption and handoff

**Files:** native_qualification/semantic_demo.py, worker.py/run.py, new
test_model_observations.py, project/test_model_mode.py, docs/results/README.
**Interfaces:** --model-consumption plus exact --package-wheel; per-worker5 steps;
R21 demonstrate(car,consume_model=False) keeps old outputs unchanged.

- [x] RED explicit-mode/missing-wheel/conflict/output assertions and five-case counts.
- [x] Implement closed accepted-row consumption and counts; rejected rows no work.
- [x] New native env/two workers, independent literal output checks, old R19/R20/R21
  SHA controls, full pure suite and explicit native static/compile checks. Fresh
  archive/new native/dev environment reproduces observations/SUMMARY exactly.
- [x] Commit; one fresh whole-branch review, one RED/GREEN fix pass for Important/
  Critical; ledger every scope ruling/deferred minor.
- [ ] Exact-head feature Draft/pure CI/downloaded manifest, original guards, external
  evidence seal and scoped handoff. Native GitHub CI remains NOT_RUN.

Self-review: independent preregistration/full-input/full-output/call-count/old-mode
regression and no-activation boundaries covered. Post-commit publication/sealing
receipts live outside the source tree to avoid a self-referential commit cycle.
