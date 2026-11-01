# R29 Adapter Model Sequence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** prove fixed synthetic R28 adapter→public model state-carry sequences.

**Architecture:** preserve R28 reader and existing public model/closed consumers;
add fixed-profile preparation gate, sequence orchestration and isolated runner.
Reuse pinned R23/R26 literal references, never generate expected outputs.

**Tech Stack:** CPython3.12.13, public0.3.0, exact pycapnp2.1.0 wheel, unittest.

**Spec:** `docs/superpowers/specs/2026-10-31-r29-adapter-model-sequence-design.md`

## Global Constraints

- Profiles exactly SIGN_CHANGE_4 and NEGATIVE_CYCLE_99,103 calls/complete worker.
- R23/R26 SHA and recipes exactly as spec; synthetic limits16/2/5/7/1/3.
- Explicit initial State(0,None,0,0); only verified output.next_state carries forward.
- Exact R28/R21 types, Float32/sign and invocation-only semantics unchanged.
- Preserve R19–R28 executable sources/public0.3.0/wheel/lock/original10 bytes.
- No F61/Controller/Runtime/CAN/actual input/r/dt/main merge/install/activation.
- R_BUDGET=UNRESOLVED, Static Gate=FAIL; feature/Draft handoff only.

## Review Focus

- A malformed construct spec must reject before any native backend access.
- Previous request and applied output must not alias, especially after inactive gating.
- Wrong profile/index/stamp/preparation must reject before a model step.
- Full output mismatches must fail closed, without advancing or retrying the sequence.
- Counted model execution and synthetic history must not be relabelled as actual custody or elapsed time.

### Task 1: M1 construct pre-allocation regression

**Files:** create `project/test_adapter_preflight_order.py`; retain R28 source unchanged.

**Interfaces:** existing SyntheticSpec/_SyntheticAdapter.construct; no new runtime API.

- [ ] Write3 tests for invalid envelope/domain/precision with backend access tripwire.
- [ ] Run discovery: existing implementation GREEN; temporarily move validation after allocation using apply_patch, run RED, restore exact bytes, GREEN.
- [ ] `git diff` confirms no R28 source delta; commit tests `[skip ci]`.

### Task 2: closed prepared-input gate and fixed sequence

**Files:** create `integration_tools/adapter_sequence.py`, `project/test_adapter_sequence.py`.

**Interfaces:** consumes R28 PreparedNativeInput, R23/R26 existing consumers/references;
produces `SequenceError(code)`, `consume_prepared(profile_id,index,prepared)`,
`run_registered_sequence(adapter,profile_id) -> dict` and `profile_count(profile_id)`.

- [ ] Write pure tests: missing module RED; valid first step literal State(1,5,2,0), invalid profile/index/metadata/stamp/prior/counter reject before p.step; corrupt output rejects.
- [ ] Implement exact closed gate and recipe-based native orchestration with independent conversion oracle, complete input/output checks and carried state.
- [ ] Run pure discovery PASS; commit `[skip ci]`.

### Task 3: isolated fixed native worker and export verification

**Files:** create `native_qualification/adapter_sequence_worker.py`,
`adapter_sequence_run.py`, `test_adapter_sequence_observations.py`,
`project/test_adapter_sequence_run.py`.

**Interfaces:** consumes Task2 run_registered_sequence and unchanged R28 qualified_adapter;
produces fixed two-worker `qualify(python,wheel,package_wheel,output,enabled=False)`
and OBSERVATIONS/SUMMARY/separate receipts/four-entry manifest.

- [ ] Write runner/data tests first; missing runner RED, data checks require103 ordered rows split4/99 and exact state transitions/boundary literals/gates/counts.
- [ ] Implement worker, fixed-only CLI and canonical export; source/hash guards and exact coverage validation, no dependency installation.
- [ ] Run pure discovery PASS; real native worker two-process observations equal; data checks PASS. Commit `[skip ci]`.

### Task 4: regression, review and handoff

**Files:** create `docs/ADAPTER_SEQUENCE_R29.md`, `docs/ADAPTER_SEQUENCE_R29_RESULTS.md`;
external workspace preserves actual artifacts/ledger.

**Interfaces:** Task3 fixed runner only; old R27/R28 commands unchanged.

- [ ] Full pure gate and all native Ruff/Ty/Codespell/in-memory compile PASS.
- [ ] Repeat new R29, unchanged R28 and complete R27 in primary and committed relocated tree/new environments.
- [ ] Portable outputs match; every manifest, literal data check, old source hash and original10 guard PASS; receipts stay distinct.
- [ ] Fresh whole-branch final reviewer; adjudicate every exclusion; Important/Critical fix once RED→GREEN if needed.
- [ ] Document results, normal feature push, exact-head dedicated pure CI PASS, preserve/update Draft PR2.
- [ ] Seal ZIP twice byte-identical; CRC/fresh extraction/root+nested manifests PASS; final report closed gates.
