# CORE4 Limiter State and Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native offline execution without repeated approval questions.

**Goal:** Preserve request/state/settings roles and validate declared adjacent state links.
**Architecture:** One stdlib module composing unchanged CORE3's public pair validator;
immutable carriers and a self-validating result, no arithmetic/model/downstream bridge.
**Tech Stack:** Existing CPython3.12.13, unittest/Ruff/Ty/Codespell; no installs.
**Spec:** docs/superpowers/specs/2026-11-05-core4-limiter-state-settings-design.md

## Global Constraints

- Base5b33af5bb85d3eb08c43d7016d580e9833a4fb4d; local stacked branch/host worktree retained.
- Exact classes/fields/constants/error order and synthetic bounds from the spec.
- Request/raw unit differs from integer limited state; request_scale/limiter_scale are separate.
- Preserve request-active and later gate-active separately; false gate requires saved0.
- Same seven settings and previous-saved/current-entry state/counter links; no state clamp or seed inference.
- CORE3 validation reused and fixed errors wrapped without raw input; direct result constructor revalidates.
- No model/helper/quantization/native/dt/r/F61 work or production/source authentication.
- Old runtime/CORE3/V4/CORE2 matrix/public src/imported77/locks/workflows/profiles unchanged.
- Frozen wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- No push/PR/main merge/HF/CI; all unresolved/null/FAIL/NO_GO/NOT_ALLOWED gates unchanged.

## Review Focus

- Previous requested bytes must not fill integer limited-state/counter fields or be reverse-normalized.
- Independent consumed-scale/settings declarations must not silently default, alias or change within a supposedly continuous pair.
- Request-stage active must not substitute for the later gate read, nor permit a nonzero saved state when that gate is false.
- Invalid/resumed state, raw types, reset/loss/time/context transitions and direct result construction must not bypass guards.
- Linked declarations must not be labeled arithmetic parity, actual consumption, model readiness or V4/F61/vehicle approval.

### Task 1: Typed limiter snapshot boundary

**Files:** create tools/cyberlateral_dev/integration_tools/limiter_snapshot.py,
project/test_limiter_snapshot.py, docs/LIMITER_SNAPSHOT_CORE4_KO.md under that component;
modify its README and docs/CORE_DEVELOPMENT_BACKLOG_KO.md.
**Interfaces:** consumes unchanged CORE3 prepare_request_pair(object,object) and
SyntheticRequestSnapshotV1; produces prepare_limiter_pair(object,object) with closed
settings/state declarations and derived CORE3 request pair. No model-input API.

- [ ] Immutable Git-export baseline full dev.py verify. Expected956tests/240compiles/static/wheel PASS.
- [ ] Commit spec/plan before module. Keep external ledger/BASE because cloud skill scripts are not mounted.
- [ ] Write tests first: raw requests be800000/3f000000 vs state entry7/saved-2 and
  next entry-2/saved4, scales16/16, deltas2/5, calibration7/1/3, counter3->4->5.
  Assert preserved roles/false permissions and actual constructor guards.
  Cover required fields, exact types/subclasses/hostile getters, R31 synthetic bounds,
  independent scales, all setting changes, limited/counter link errors, no initial
  zero inference/no scale clamp, false gate saved0 and distinct request/gate active,
  CORE3 context/sequence/reset/time/raw errors, deterministic detached output and import isolation.
  Run focused unittest; expected missing-feature assertion RED, not setup errors.
- [ ] Implement only the specified carriers/errors/composition/checks.
  Focused tests expected GREEN; scoped Ruff/Ty/Codespell PASS.
- [ ] Guide/README/backlog explain R31 subset vs full model4096/vehicle limits,
  aggregate declarations vs repeated consumed reads, absence of model/V4/F61 conversion.
- [ ] Full stable-source dev.py verify expected956+actual new methods/242compiles/static/wheel PASS.
  Commit implementation after focused checks; one fresh whole-branch review may overlap
  full gate on identical bytes. Wait for both; one TDD Critical/Important fix pass if needed.
- [ ] Independent literal/settings-range/state-link/gate acceptance twice, no original
  helper/model execution. Expected exact errors/preserved records/deterministic output,
  and explicitly accepted linked-but-arithmetically-unproven declarations remain labeled so.
- [ ] Final source/Manifest/wheel and real existing cloud gate-consumer check; external
  result report, preserve branch/evidence, no remote publication or cleanup.

Self-review: one task; no shared task interfaces. Five focus classes all have
specific real tests, model-input flags are fixed false and no old API is redesigned.
