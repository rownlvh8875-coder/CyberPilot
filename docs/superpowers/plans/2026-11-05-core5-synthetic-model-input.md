# CORE5 Synthetic Model Input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Owner delegated native offline execution without repeated approval questions.

**Goal:** Build one current synthetic model input from explicit CORE4 declarations.
**Architecture:** One typed module composes unchanged CORE4 and frozen0.3.0 types;
explicit missing context, checked previous quantization, no transition execution.
**Tech Stack:** Existing Python3.12.13/stdlb/unittest/Ruff/Ty/Codespell; no installs.
**Spec:** docs/superpowers/specs/2026-11-05-core5-synthetic-model-input-design.md

## Global Constraints

- Base6e32c35d653d27a4559d38baf721a252f439a722, existing linked worktree, local stacked branch.
- Exact fields/bounds/error order/mapping/fixed flags from spec; no defaults/coercion.
- Both frames require request_active==inactive_gate_active, override=false; no old API relaxation.
- modelindex1..4095 is explicit, not capture sequence; previous_integer_request checked, not inferred.
- Exact binary32->binary64 embedding; use existing quantizer for previous-request check only.
- New API does not call step/simulate/limiter/oracle, does not prove declared outputs.
- Old runtime/CORE1~4/src/imported77/lock/workflow/profiles/public wheel unchanged.
- Frozen wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
- Preserve all unresolved/null/FAIL/NO_GO/NOT_ALLOWED gates; no actual-source/F61/r work.
- No push/merge/PR/HF/CI dispatch/cleanup. External evidence and prior refs retained.

## Review Focus

- Foreign classes/getters/bool-as-int/nonfinite/dyadic edge cases must reject before coercion.
- A previous limited output must not fill previous_integer_request; tie rounding and signed raw words must map correctly.
- Single model active cannot conceal different read roles/override; reject incompatible inputs, not CORE4's carrier.
- Resumed state/modelindex must not be inferred from sequence or current saved values, nor clamped to scale.
- Valid model input must not become next-state parity, actual consumption, source authentication or V4/F61/vehicle permission.

### Task 1: Current synthetic model input boundary

**Files:** create component integration_tools/synthetic_model_input.py,
project/test_synthetic_model_input.py, docs/SYNTHETIC_MODEL_INPUT_CORE5_KO.md;
modify component README and docs/CORE_DEVELOPMENT_BACKLOG_KO.md.
**Interfaces:** consumes unchanged prepare_limiter_pair(object,object), exact
CORE4 frames; produces SyntheticModelContextV1(scope,model_index,
previous_integer_request,current_driver,current_angle_deg),
PreparedSyntheticModelInputV1(previous,current,context), and
prepare_model_input(object,object,object) with derived public LateralState/Input.

- [ ] Export immutable baseline and run dev.py verify:985tests/242compiles/static/wheel PASS.
- [ ] Commit spec/plan before module code; keep external ledger/BASE because cloud skill scripts are not mounted.
- [ ] Write real literal tests first: previous-0.25/current+0.5,scale16, suppliedprevious-4,
  modelindex5, driver1.5,angle85.0 -> state(5,-4,-2,4), sample(5,0.5,1.5,85.0,true,limits,SYNTHETIC_ONLY).
  Domain/type tests, no field fallback, previous ties/raw preservation, active/override checks,
  inherited CORE4 errors, direct construction/replace, independent current saved values,
  model usability on a synthetic invocation and preparation-only import/call isolation.
  Run focused unittest; expected RED from missing-feature assertions, not setup errors.
- [ ] Implement spec carriers, guards and mapping; focused unittest GREEN, scoped static checks PASS.
- [ ] Guide/README/backlog: exact field-role mapping, unsupported contexts, absence of output parity/actual authority,
  preserved raw/time/state metadata and no policy fallback.
- [ ] Stable source full dev.py verify expected985+actual new methods/244compiles/static/frozenwheel PASS.
  Commit implementation after scoped checks; one fresh read-only whole-branch review may overlap the full gate.
- [ ] Independently hand-check mapping/boundaries/rejections in two fresh processes, exact results/bytes;
  no original source/helper/F61 work. Independent review outcomes adjudicated once.
- [ ] Verify final source custody/Manifest/frozenwheel/preserved refs/real cloud gate consumer;
  external final report and result, keep branch/evidence locally, no remote publication.

Self-review: one task, no shared task interface conflicts; all five Review Focus
classes have tests. Scope remains current input preparation, not transition validation.
