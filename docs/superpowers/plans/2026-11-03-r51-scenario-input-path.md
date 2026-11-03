# R51 Scenario Input Path Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize invalid input path failures at file acquisition for R31/R37.

**Architecture:** Only os.open receives a new classified-error-first ValueError
boundary. Existing reader, runner and validator consume the unchanged API.

**Tech Stack:** Existing CPython3.12.13/Linux/unittest/stdlib; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-03-r51-scenario-input-path-design.md`

## Global Constraints

- Public0.3.0 wheel/API, models/reference/generator/limiter, locks unchanged.
- Parser, output preflight, schemas, downstream and cloud tools/CI unchanged.
- R_BUDGET unresolved, StaticFAIL, actualr/T2/vehicle scale null, no activation.
- No F61/actualr/dt/vehicle/Controller/Runtime/CAN; preserve old work/evidence.
- Feature PR only; no main merge/HF write in this stage.

## Review Focus

- ScenarioError is ValueError: preserve classified object/code/cause identity.
- Unencodable surrogates reject, valid Unicode/surrogateescape filenames remain usable.
- No broad catch: TypeError/interrupts and parser errors must still propagate.
- NUL OS argv is impossible: test actual CLI main in a fresh isolated process.
- Validation rejection must preserve canonical JSON/null identity/no model import.

---

### Task 1: Classify input-open path errors

**Files:**
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_input.py`
- Create: `tools/cyberlateral_dev/project/test_scenario_input_paths.py`
- Modify: `tools/cyberlateral_dev/docs/SYNTHETIC_SCENARIO_CLI_R31_KO.md`
- Modify: `tools/cyberlateral_dev/docs/SCENARIO_VALIDATION_R37_KO.md`

**Interfaces:**
- Consumes: `read_scenario(Path) -> ScenarioSpec`, `ScenarioError.code`.
- Produces: unchanged R31/R37 API, existing SCENARIO_INPUT_FILE for invalid open.

- [ ] Confirm clean isolated branch from exact main; run existing reader tests.
  Expected: green baseline, raw NUL/encoding errors reproduced without model work.
- [ ] Add eight test methods covering all Review Focus items and actual permission.
  Run `python -B -m unittest discover -s project -p test_scenario_input_paths.py -v`.
  Expected RED: missing classification/CLI contract; unchanged scope controls green.
- [ ] Add the os.open-only catch and Korean boundary notes. Run reader, runner CLI
  and validator tests. Expected: all green; file/JSON guards and causes preserved.
- [ ] Run identical declared-synthetic fixtures through baseline/fixed R31/R37.
  Expected: exact numeric/validation bytes, honest source identity delta, closed
  Manifests, no input changes. Error probes new model/reference0.
- [ ] Run fresh full `dev.py verify` and cloud `ci_verify.py` outside repository.
  Expected: all tests/static PASS, public wheel unchanged; report actual counts.
- [ ] Commit; run the targeted completion suite and record BASE/HEAD/test receipt.
  One fresh whole-branch review; one TDD Important/Critical fix pass if necessary,
  Minors deferred. Expected: clean reviewed branch, no unresolved Important/Critical.
- [ ] Push scoped branch/open/attach PR; verify actual exact-head checks/artifacts.
  Seal deterministic evidence twice; independently verify checksum/closure.
  Expected: open feature PR, main/HF unchanged, vehicle gates still closed.
