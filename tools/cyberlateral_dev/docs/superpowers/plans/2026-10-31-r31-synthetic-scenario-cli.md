# R31 Synthetic Scenario CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** developer-defined synthetic JSON scenarios→unchanged model→exact records/CSV.

**Architecture:** separate DEV parser/types, model engine, renderer/publisher and
thin source-selecting CLI. No frozen package/public CLI/native runner changes.

**Tech Stack:** CPython3.12.13 stdlib, existing public0.3.0 source, unittest, pinned DEV tools.

**Spec:** `docs/superpowers/specs/2026-10-31-r31-synthetic-scenario-cli-design.md`

## Global Constraints

- Exact V1 root/nested keys, explicit synthetic limits/state,1..4096 adjacent samples.
- Binary64 float fields require JSON floating tokens, finite/domain/dyadic rules exactly per spec.
- Input1MiB, float token128/int32 characters; bounded regular-file read, strict JSON.
- Entire input preflight before model work; no fallback/coercion/clamp/r/time fields.
- Unchanged public0.3.0/source/wheel/API, fixed CLI, existing native runners/workflow/dependencies.
- Separate portable4 files and actual receipt; no successful RESULTS before all other writes.
- No actual vehicle/F61/Controller/Runtime/CAN/r/dt/main merge or activation; gates remain closed.

## Review Focus

- Invalid final samples must not cause prefix model execution or partial output.
- JSON numeric types/duplicate keys/nonfinite/oversize/deep inputs must reject explicitly.
- FIFO/symlink/device/dangling/existing output inputs must not block or overwrite.
- Signed-zero/binary64 precision and previous request/applied state must survive mapping correctly.
- Synthetic labels/source hashes must not be promoted to actual origin, installed-wheel or safety authority.

### Task 1: strict file/schema preflight

**Files:** create `integration_tools/scenario_input.py`, `project/test_scenario_input.py`.

**Interfaces:** produces frozen ScenarioSpec/LimitsSpec/StateSpec/SampleSpec,
`ScenarioError(code)`, `parse_scenario(raw:bytes)`, `validate_spec(spec)`,
`read_scenario(path:Path)`; no public model import or execution.

- [x] Write parser/typed/domain/order/resource/duplicate/unknown/scope/precision/file tests; run RED missing module.
- [x] Implement bounded strict JSON and frozen exact-type preflight, source-derived rules without model calculations.
- [x] Run targeted tests/static PASS; commit `[skip ci]`.

### Task 2: model engine, output and CLI

**Files:** create `integration_tools/scenario_engine.py`, `scenario_output.py`,
`scenario_run.py`, `tools/scenario.py`, `project/test_scenario_engine.py`,
`project/test_scenario_cli.py`.

**Interfaces:** consumes Task1 spec; `evaluate_scenario(spec)->dict` over unchanged
p.simulate; `render_outputs(spec,result,identity,receipt)->dict[str,bytes]`;
`run_scenario(input_path,output_path)->dict`, CLI --input/--output only.

- [x] Write engine literal sign-cycle/resumed/precision/preflight no-work tests and CLI guard/inert/source/IO/determinism tests; run RED missing implementation.
- [x] Implement cold exact-source loader after complete preflight, model mapping, full trace rendering and exclusive final publication.
- [x] Run targeted tests/static PASS; actual CLI subprocess examples pass; commit `[skip ci]`.

### Task 3: examples, docs and full handoff

**Files:** create `examples/synthetic_sign_cycle_v1.json`, `synthetic_resumed_v1.json`,
`docs/SYNTHETIC_SCENARIO_CLI_R31_KO.md`, `docs/SYNTHETIC_SCENARIO_CLI_R31_RESULTS.md`;
update README navigation and R30-M1 report-opening prose.

**Interfaces:** Task2 CLI only, no new public package flags or hardware paths.

- [ ] Add literal synthetic examples and usage/format/rejection/claim limits; corrected report path.
- [ ] Full component tests/static/wheel/original guards PASS; committed relocated fresh env repeats custom examples twice, portable files exact, receipts retained.
- [ ] Unchanged optional native R27/R28/R29 regressions match historical pins; native static/compile/data checks PASS.
- [ ] Fresh whole-branch reviewer; Important/Critical one RED→GREEN fix pass if needed; all exclusions dispositioned.
- [ ] Commit results, normal feature push, exact-head dedicated pure CI/artifact PASS, preserve/update Draft PR2.
- [ ] Deterministic evidence seal twice, fresh extraction/CRC/all checksum manifests PASS; final closed production gates.
