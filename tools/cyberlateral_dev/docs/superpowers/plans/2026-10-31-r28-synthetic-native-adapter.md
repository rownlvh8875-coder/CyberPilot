# R28 Synthetic Native Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** read internally built synthetic native messages into exact model-input records.

**Architecture:** Add an identity-bound adapter and isolated qualified context;
reuse the unchanged R20/R21 validation and R19 identity checks. A separate R28
worker/runner proves real native reads; R27 remains an unchanged regression.

**Tech Stack:** CPython3.12.13, public0.3.0, pycapnp2.1.0 exact pinned wheel, unittest.

**Spec:** `docs/superpowers/specs/2026-10-31-r28-synthetic-native-adapter-design.md`

## Global Constraints

- Builtin finite floats exactly representable as Float32; preserve signed zero.
- Request [-1,1]; driver [-1024,1024] and angle [-180,180], dyadic denominator<=256.
- Existing R20 stamp/settings/previous-snapshot and R21 conversion rules unchanged.
- No external bytes/native objects accepted by the public construction API.
- Public0.3.0/model/wheel/lock, R19–R27 executable modules and original10 unchanged.
- No Controller/Runtime/CAN/F61/actual inputs/r/dt/main merge or activation.
- R_BUDGET=UNRESOLVED, Static Gate=FAIL; feature commits/push/Draft PR only.

## Review Focus

- A copied/foreign handle must not admit caller-controlled bytes to native parse.
- Closed contexts must invalidate retained handles, with no borrowed readers escaping.
- Negative zero/subnormal/0.3 precision must not silently round or lose sign.
- Bad settings or previous stamp/state must reject before any message allocation.
- Declared synthetic history and process receipts must not become actual custody claims.

### Task 1: exact spec preflight and owned adapter

**Files:** create `integration_tools/native_adapter.py`, `project/test_native_adapter.py`.

**Interfaces:** consumes existing R20 records and R21 prepare function; produces
`SyntheticSpec`, `AdapterError(code)`, `validate_spec(spec)`, private
`_SyntheticAdapter(car)` with construct/inspect/prepare/close. Output frozen
`PreparedNativeInput(prepared, read_claim)`; handle type private.

- [ ] Write pure tests for scalar rejection, exact precision/sign, bad stamps/settings/prior, invalid/foreign handle and close.
- [ ] Run `uv run --locked python -B -m unittest project.test_native_adapter -v`; observe missing adapter fail.
- [ ] Implement preflight, owned construction, weak identity registry and within-context native read; no model execution.
- [ ] Run same tests: PASS. Commit `[skip ci]`.

### Task 2: qualified real-native adapter and independent checks

**Files:** create `native_qualification/adapter_runtime.py`, `adapter_checks.py`,
`adapter_worker.py`, `adapter_run.py`, `adapter_oracle.py`,
`project/test_native_adapter_run.py`.

**Interfaces:** consumes Task1 API; produces `qualified_adapter(wheel,schema,package_wheel)`
context, `observe(...) -> {observations,receipt}`, and fixed R28 two-worker runner.
Oracle consumes frozen envelope plus explicit spec scalar values, never adapter imports.

- [ ] Write real-native unittest checks first: literal values, signed zero/subnormal/promoted0.3, invalid specs, settings/prior, foreign/copied handles, context close; oracle agreement exact.
- [ ] Write runner failure tests (existing output, artifact mismatch); run RED for missing runtime/runner.
- [ ] Implement qualified loader and worker; execute with pinned native env using `-I -B`, empty cwd, private import cache.
- [ ] Implement runner: canonical two-worker comparison, source pins, separate receipts, manifest; run pure tests/native checks PASS. Commit `[skip ci]`.

### Task 3: reproducibility, regression, documentation and Draft handoff

**Files:** create `docs/NATIVE_ADAPTER_R28.md`, `docs/NATIVE_ADAPTER_R28_RESULTS.md`;
update plan checkboxes only. External evidence workspace holds complete artifacts.

**Interfaces:** consumes Task2 fixed runner; no changes to old suite/worker or public API.

- [ ] Run full pure gate, native Ruff/Ty/Codespell/in-memory compile; PASS.
- [ ] Run R28 and unchanged R27 suite in primary and committed relocated source with new envs.
- [ ] Verify R28 observations and R27 portable summary/report equality; retain environment-specific receipts.
- [ ] Verify original10 guards, unchanged public wheel; document true scoped model counts.
- [ ] One fresh whole-branch reviewer; adjudicate exclusions, fix Important/Critical RED→GREEN once if necessary.
- [ ] Commit docs, normal feature push; exact-head dedicated pure CI PASS; preserve/update Draft PR2.
- [ ] Seal deterministic evidence ZIP twice, fresh extraction/CRC/all manifests; final report gates closed.
