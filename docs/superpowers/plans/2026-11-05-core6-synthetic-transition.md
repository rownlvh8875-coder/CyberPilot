# CORE6 Synthetic Transition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native offline implementation without repeated approval questions.

**Goal:** Check current declared saved state/counter against one existing synthetic step.
**Architecture:** One typed module composes unchanged CORE5 and public0.3.0 model;
exact differences, no declaration rewriting or implicit prehistory claims.
**Tech Stack:** Existing Python3.12.13/stdlib/unittest/Ruff/Ty/Codespell, no installs.
**Spec:** docs/superpowers/specs/2026-11-05-core6-synthetic-transition-design.md

## Global Constraints

- Base118ac73b1ba12d1ef8415d031137417de4fc9224; host linked worktree/local stacked branch.
- Exact interfaces/guards/order/errors/fields/fixed flags/bounds from spec.
- CORE5 preflight before exactly one public synthetic model step; no shortcut prepared inputs.
- Current post-gate saved command/counter only; no full-output or previous/prehistory parity.
- Preserve declarations and compute differences exactly in state/counter order, never overwrite.
- Failed model work may be nonzero; never emit successful partial result or zero-work claim.
- No actual inputs/F61/Controller/Runtime/CAN/actual dt/r/policy; keep all existing gates/nulls.
- Old CORE1~5/runtime/public src/lock/workflow/imports/profiles and frozen wheel unchanged.
- Wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- No push/merge/PR/HF/CI dispatch/cleanup. Preserve existing refs/worktree/evidence.

## Review Focus

- MATCH must mean both checked fields match, never a partial success or repaired declaration.
- Post-gate final command, not pre-gate limiter value/current entry/previous request, must be compared.
- Invalid CORE5/type/override/active/context inputs must fail before model work; model failure never becomes DIFFERENT/MATCH.
- Direct construction/replace and foreign/boolean-valued model results must not forge successful derived fields.
- Synthetic MATCH must not grant previous-transition/prehistory/source/physical/V4/F61/vehicle authority.

### Task 1: Exact current-transition checker

**Files:** create component integration_tools/synthetic_transition_check.py,
project/test_synthetic_transition_check.py, docs/SYNTHETIC_TRANSITION_CORE6_KO.md;
modify component README and docs/CORE_DEVELOPMENT_BACKLOG_KO.md.
**Interfaces:** consume unchanged prepare_model_input(object,object,object) and
public model.step; produce SyntheticTransitionDifferenceV1(field,declared,computed),
SyntheticTransitionCheckV1(previous,current,context),
check_synthetic_transition(object,object,object) with prepared/state/differences/status.

- [ ] Immutable export baseline dev.py verify, expected1015tests/244compiles/static/wheel PASS.
- [ ] Commit spec/plan before code; external ledger/BASE substitutes for non-mounted skill scripts.
- [ ] Write tests first: literal next(6,8,2,5), saved(2,5)MATCH; saved(4,5)one difference;
  saved(4,6)two differences in order; inactive post-gate0, threshold/fault89/90, sign/driver/
  tie/resumed cases with hand-checked literals; state declarations preserved.
  Cover preflight errors/no model call, exactly-one-step including direct/replace, fixed flags,
  malformed returned state and model failures, inherited CORE5 restrictions/import isolation.
  Run focused tests; expected missing-feature assertion RED, not setup errors.
- [ ] Implement exact guards/calculation/mapping/classification; focused tests GREEN and scoped static PASS.
- [ ] Guide/README/backlog explain current-only comparison, work accounting/error boundary and no authority escalation.
- [ ] Commit implementation; run clean stable-source full dev.py verify expected1015+actual new tests/
  246own compiles/static/frozenwheel PASS. One fresh read-only whole-branch review may overlap full gate.
- [ ] Run independent rational/literal acceptance twice, expected exact state/classification/differences/
  no declaration mutation; one TDD fix pass for any Critical/Important reviewer findings, minors ledgered.
- [ ] Final real cloud gate-consumer/source custody/Manifest/wheel/refs, external report/result;
  retain local branch and evidence with no remote publication.

Self-review: one task/no shared task conflicts. Five focus classes all have concrete
tests; no model redesign or unavailable previous driver/angle/prehistory inferred.
