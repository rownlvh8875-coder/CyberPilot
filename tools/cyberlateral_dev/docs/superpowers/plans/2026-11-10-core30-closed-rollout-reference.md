# CORE30 Closed Rollout Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Independently audit all full outputs and chain roles of three closed CORE27 fixtures.
**Architecture:** Pinned hand-derived vectors -> model-free assembly; separate explicit executor
guards frozen input bytes, invokes CORE27 once and exact-type compares complete selected records.
**Tech Stack:** Existing Python3.12.13/stdlib/component .venv; no dependency changes.
**Spec:** [design](../specs/2026-11-10-core30-closed-rollout-reference-design.md).

## Global Constraints

Keep existing model/producer/helper/CLI/wheel unchanged; only three prior guide links may change.
Actual r/T2/scale=null, R_BUDGET UNRESOLVED,Static Gate FAIL; no F61/vehicle/r/dt execution.
No new CLI, arbitrary input reader, generic oracle or deployment. Preserve all prior evidence/refs.
BASE85ce6d0300a2e6c6eb600f0a61f95083ae7d7402; native inline under standing delegation.

## Review Focus

Reference independence: no target/oracle imports/calls while assembling expected full outputs.
Catalog drift and late-invalid: reject before model; never turn unexpected execution errors into match.
Subtle corruption: bool/int equality, signed zero, projection/trace-only differences and wrong state feed.
Owned reference capture/identity and error honesty: no false zero-work or source/vehicle authority.
Determinism and coverage: complete selected record vs explicitly excluded prepared/input internals.

## Task 1 — closed audit API

Files create: reference/core30_rollout_expected_v1.json, integration_tools/rollout_reference.py,
integration_tools/core_rollout_audit.py, project/test_core_rollout_audit.py,
docs/CORE_ROLLOUT_REFERENCE_CORE30_KO.md and this spec/plan.
Modify only README.md,docs/CORE_DEVELOPMENT_BACKLOG_KO.md,docs/SYNTHETIC_SEQUENCE_ROLLOUT_CORE27_KO.md.
Interfaces: expected_rollout(case_id)->dict and load_reference()->dict in rollout_reference;
audit_rollout_case(case_id:object)->dict and RolloutAuditError.code in core_rollout_audit.

- [ ] Commit hand-derived vector/spec/plan before target execution; record reference SHA.
- [ ] Write behavioral tests before API modules exist, verify missing-feature assertion RED.
  Pin model calls3/3/0, all audit matches0 vs observed statusesM/D/R; literal full-output checks;
  independent reference import/execution profile0; input/reference/case guards before execution;
  mutations of projection/clip/fault/state/difference/metadata, exact-type/signed-zero/path ordering,
  malformed result/unexpected error => no partial success. These cover every Review Focus line.
- [ ] Implement minimal two modules and run `.venv/bin/python -B -m unittest discover -s project -p 'test_core_rollout_audit.py'`.
  Expected: all new tests PASS; exceptions remain fixed with nonzero-work honesty.
- [ ] Add Korean derivation/use/scope guide and three links. Expected: local links resolve.
- [ ] Run old CORE27/29 focused regressions and fresh `dev.py verify --output NEW_EXTERNAL`.
  Expected: all old+new tests/static checks/317 own compiles/frozen wheel PASS.
- [ ] Independently reproduce twice including deliberate output-only mutations. Expected: deterministic
  receipts, model3/3/0 per three-case run (nonzero), expected assembly0; source656/protected646/ref33
  custody, DEV manifest and cloud gate consumer PASS. Record actual counts and work boundaries.
- [ ] Commit product and task-done verification, dispatch one fresh whole-range reviewer, rule all
  exclusions; one TDD fix pass for Critical/Important if needed; seal unsigned ZIP and independently verify.
