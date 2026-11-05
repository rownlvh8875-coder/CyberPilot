# CORE7 Declared Synthetic Sequence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native offline execution without repeated approval questions.

**Goal:** Check every adjacent declared synthetic transition with explicit context.
**Architecture:** One typed bounded sequence module over unchanged CORE5/6;
whole-input preflight, per-declaration diagnostics, no repair/computed rollout.
**Tech Stack:** Existing Python3.12.13/stdlib/unittest/Ruff/Ty/Codespell, no installs.
**Spec:** docs/superpowers/specs/2026-11-05-core7-declared-sequence-design.md

## Global Constraints

- Base1651203989eb44186c6a14aec0a6d531807a81ac; host worktree/local stacked branch.
- Required exact tuple inputs; frames2..4096, contexts=frames-1, all spec fields/errors/order.
- All CORE5 preflight then consecutive explicit model indices, before any public step.
- Zero model steps on preflight error is not zero quantization/validation work.
- Preserve all CORE6 results/differences, use declared entry each time; no partial or repaired MATCH.
- First-frame transition/prehistory/full-output/source/physical/V4/F61/vehicle authority not granted.
- No old CORE1~6/runtime/src/locks/workflows/imports/profiles/wheel changes.
- Frozen wheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- Preserve all existing unresolved/null/FAIL/NO_GO/NOT_ALLOWED gates; no actual r/F61/runtime work.
- No push/merge/PR/HF/CI/network/cleanup; preserve prior refs and evidence.

## Review Focus

- Late invalid inputs/model-index gaps must reject before any public step, not after processing a prefix.
- Earlier differences must not overwrite a declaration, feed computed state forward, or skip later diagnostics.
- Empty/single/oversize/wrong-container/misaligned contexts cannot yield vacuous MATCH or bypass exact types.
- Direct/replace/foreign values and late model failures cannot forge a completed sequence or zero-work claim.
- Sequence MATCH excludes anchor transition/prehistory/full output/source/vehicle policy authority.

### Task 1: Bounded declared sequence checker

**Files:** create component integration_tools/synthetic_sequence_check.py,
project/test_synthetic_sequence_check.py, docs/SYNTHETIC_SEQUENCE_CORE7_KO.md;
modify component README and docs/CORE_DEVELOPMENT_BACKLOG_KO.md.
**Interfaces:** consumes unchanged prepare_model_input/check_synthetic_transition;
produces SyntheticSequenceCheckV1(frames,contexts),
check_synthetic_sequence(object,object), SequenceCheckError.code and derived results/counts.

- [ ] Immutable baseline dev.py verify1041tests/246compiles/static/wheel PASS.
- [ ] Commit spec/plan before code; external ledger/BASE for non-mounted skill scripts.
- [ ] Write tests first: four literal frames/three states from spec; minimal pair,
  no-repair computed2,5,4/statusD,M,M; late/all mismatches, whole-preflight/model-order
  guards and zero-step profiling, exacttuple/type/count/domain restrictions,
  maximum4096frames and last index4095, direct/replace/flags/failure/isolation.
  Focused unittest expected missing-feature assertion RED, no setup errors.
- [ ] Implement exact spec with unchanged CORE5/6 public entry points;
  focused GREEN/scoped Ruff/Ty/Codespell PASS.
- [ ] Guide/README/backlog explain transition ordinal, preflight work vs steps,
  declared-entry diagnostics vs computed rollout and unchanged authority gates.
- [ ] Commit; clean stable-source full gate1041+actual new tests/248compiles/
  static/frozenwheel PASS. One fresh read-only whole-branch review may overlap.
- [ ] Independent rational/literal multi-call acceptance twice; exact all rows/
  aggregate/classification/step counts, no mutation or source-policy claims.
  One TDD pass for Critical/Important findings; minor findings ledgered.
- [ ] Actual final cloud consumer/Manifest/source custody/wheel/refs; external
  report/result, keep branch/worktree/evidence with no remote publication.

Self-review: one task/no shared-task conflicts; five focus classes have concrete
tests. Whole preflight intentionally repeats CORE5 when CORE6 later calculates.
