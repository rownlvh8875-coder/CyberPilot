# CORE31 Boundary Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox tracking.

**Goal:** Audit inactive/fault/rounding state chains with preregistered independent literals.
**Architecture:** Separate typed closed factory, pinned model-free reference assembly and explicit
audit. Reuse unchanged CORE27 executor and CORE30 observation/exact comparison helpers.
**Tech Stack:** Existing Python3.12.13/stdlib/component .venv; no installs.
**Spec:** [design](../specs/2026-11-10-core31-boundary-rollout-design.md).

## Global Constraints

BASE0781f2e5e374c6e64d17325a2d516f3288aa7bab; existing host-owned linked worktree, new named branch.
CORE30/model/arithmetic/producer/CLI/wheel unchanged; old modifications only three guide links.
Actual r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL; original F61/vehicle/r/dt0.
No arbitrary inputs or runtime activation; preserve prior evidence/refs; no publication/deletion.

## Review Focus

Inactive final0 vs nonzero limited value: resumed step must consume computed post-gate state.
Fault89/90/91/reset: steer request false must not be conflated with active final-command gating.
Negative half-ties and signed-zero: preserve request/product sign but canonicalize integer/output zero.
Reference independence and drift guards: factory hashes are structural, expected outputs are hand literals.
Error/work honesty and coverage: full selected output comparison is not generic validation or call attestation.

## Task 1 — one closed boundary audit increment

Create integration_tools/core_boundary_cases.py,boundary_reference.py,core_boundary_audit.py;
project/test_core_boundary_audit.py;reference/core31_boundary_expected_v1.json;
docs/CORE_BOUNDARY_ROLLOUT_CORE31_KO.md and spec/plan.
Modify README.md,docs/CORE_DEVELOPMENT_BACKLOG_KO.md,docs/CORE_ROLLOUT_REFERENCE_CORE30_KO.md.
Interfaces: build_boundary_case()->(frames,contexts),input_record()->dict;
load_reference()/expected_boundary()->dict; audit_boundary_case()->receipt,BoundaryAuditError.code.

- [ ] Commit spec/plan, write BoundaryCaseTests first. Run with PYTHONPATH=project .venv/bin/python
  -B -m unittest test_core_boundary_audit.BoundaryCaseTests. Expected: missing factory RED.
- [ ] Implement typed factory only; repeat class command. Expected: PASS, model/quantizer0.
  Commit factory/test. Do not call CORE27 on new fixtures yet.
- [ ] Hand-enter expected vectors per spec; derive only structural input SHA/size using factory
  serializer with model/quantizer calls forbidden. Freeze vector in a separate commit before audit.
- [ ] Write BoundaryAuditTests before reference/audit modules. Same class command for audit:
  Expected: missing API RED. Pin model3/4/6,quantizer6/8/12; all outputs/states/flags/zero representations;
  cold model-free reference, before-execution case/hash/catalog guards; inactive/fault/signed-zero/
  clip/state/type mutations, prefix failure/malformed result/BaseException, no writes and determinism.
  Include exact path reporting, truncation and false vehicle/source flags. Cover every Review Focus.
- [ ] Implement minimal modules, run full new file. Expected: all new tests PASS.
- [ ] Add guide+links; run new and CORE30/27 regressions and fresh dev.py verify --output NEW_EXTERNAL.
  Expected: all tests/static/wheel PASS, own321compiles, frozen wheel unchanged, links resolve.
- [ ] Independent profiled acceptance twice with normal3cases+three targeted mutations.
  Expected: per run26model/52quantizer, expected assembly0; receipts/artifacts byte-identical.
  Verify source664/protected653/ref34, DEV manifest/cloud consumer and old seal custody.
- [ ] Commit final product/task-done verification; one fresh whole-range review, rule all exclusions;
  one RED/GREEN fix pass+complete gate for Critical/Important if necessary. Seal and independently verify ZIP.
