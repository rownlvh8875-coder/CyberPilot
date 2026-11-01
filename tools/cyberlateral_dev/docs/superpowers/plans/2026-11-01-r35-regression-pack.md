# R35 Synthetic Regression Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fixed synthetic regression pack over unchanged R31/R33/R34.

**Architecture:** Nine explicit JSON inputs, separate hand-derived literal
expectations, and unittest consumers. Reuse the real batch and comparison CLIs;
do not add production execution paths.

**Tech Stack:** CPython3.12.13, unittest, JSON, existing pinned DEV environment.

**Spec:** ../specs/2026-11-01-r35-regression-pack-design.md

## Global Constraints

- Baseline b6731908be519a051c6ffcf9a18845284a102c20; isolated feature branch.
- CPython3.12.13/Linux/binary64; no dependency/lock/API/model/wheel changes.
- Only new fixture/reference/test/docs files and a README link may change.
- No actual vehicle inputs, Controller, native qualification, F61, r/dt, CAN,
  deployment, push/PR/main merge/CI dispatch.
- R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/vehicle scale=null;
  SOURCE_SCHEMA_UNQUALIFIED6000; Candidate/Runtime NO_GO; F70UH/V/F71 NOT_ALLOWED.
- Literal expectations precede execution; no model-derived baseline update.
- Capture full test outputs outside the repository; leave failed outputs intact.

## Review Focus

- Replacing previous applied output with previous request must break sign/state tests.
- Inactive gating must reset applied state/counter without replacing requested history.
- Invalid late samples must reject before model loading or partial output.
- Fractional bounds and negative ties must retain nearest-even and scalar kinds.
- Repeated wrong saved values can MATCH: check literals before treating parity as acceptance.

---

### Task 1: Literal fixture pack and numerical/state tests

**Files:**
- Create: examples/r35/{positive_crossing,negative_crossing,inactive_resume,angle_counter,fractional_driver,quantization_ties,invalid_late_request,invalid_order,invalid_policy}_v1.json
- Create: reference/r35_regression_expected_v1.json
- Create: project/test_regression_pack.py

**Interfaces:**
- Consumes: scenario_input.read_scenario(Path), scenario_engine.evaluate_scenario(spec), scenario_run.run_scenario(Path, Path).
- Produces: nine fixed files, JSON reference with ordered cases, test-only row projection/assertion helpers.

- [ ] Write tests first. Missing pack must fail an explicit assertion. Pin final
  command arrays: positive[2,4,6,1,-2,0,2,-2], negative[-2,-4,-6,-1,2,0,-2,2],
  inactive[0,2,0,-2,2], angle[2,4,4,4,4], driver[2,4,-2,-4,0,0],
  quantization[0,2,0,-2,5,0]. Compare every prepared history and final state.
- [ ] Run targeted unittest discovery; expect FAIL for the missing fixture pack.
- [ ] Add independently hand-authored inputs/expected row tables. Document
  directional rate bounds, fractional2.5/3.5 ties, and89/90/91 counter derivation.
- [ ] Assert exact SCENARIO_DOMAIN/ORDER/KEYS before model loading and no output;
  assert request/product hex including signed zero, trace scalar kinds and rate bounds.
- [ ] Run targeted tests, then the full component suite; expect PASS.
- [ ] Commit only Task1 files and spec/plan after verification.

### Task 2: Real workflow regression and usage documentation

**Files:**
- Create: project/test_regression_pack_cli.py
- Create: docs/SYNTHETIC_REGRESSION_PACK_R35_KO.md
- Modify: README.md (link only)

**Interfaces:**
- Consumes: Task1 inputs/reference/test-only row projection; existing scenario_batch.py
  and scenario_compare.py CLI contracts; complete saved output bundles.
- Produces: tested documented explicit CLI order, no new command or public API.

- [ ] Run fresh real CLI mixed batches twice. Assert exit1, input9/complete6/
  rejected3/model38; check expected rows, CSV/view and three rejection codes.
- [ ] Verify every root/nested/portable manifest and compare each portable file
  directly across runs, not merely the manifest bytes. Check source/input bytes
  before/after and closed gates.
- [ ] Compare complete saved batches using a fresh R34 CLI; assert exit0/MATCH,
  sample38/difference0/new_model0 and empty forbidden-module receipt.
- [ ] Demonstrate changed raw input is INPUT_CHANGED, not same-input regression,
  by explicitly changing a synthetic input copy and running another batch.
- [ ] Publish concise Korean usage/derivation/limitations. Expected rejection is
  not a gate failure, and portable sharing subsets are not complete R34 inputs.
- [ ] Run full dev.py verify twice into new external folders and two explicit
  batch/comparison reproductions; all checks/bytes must match expected scope.
- [ ] Commit Task2; obtain one independent whole-branch review and address only
  Important/Critical findings with failing tests first. Leave main/push/CI untouched.
