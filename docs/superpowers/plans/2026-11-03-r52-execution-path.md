# R52 Execution Path Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject unsupported R31 input/output execution paths before input/model work.

**Architecture:** Two narrow preflight boundaries in run_scenario; existing output
guards keep precedence, then UTF8/NUL output and input receipt qualification.
The generic input reader/validation-only mode remain unchanged.

**Tech Stack:** Existing CPython3.12.13/Linux/unittest/stdlib; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-03-r52-execution-path-design.md`

## Global Constraints

- Public0.3.0 wheel/API, model/reference/limiter/generator and locks unchanged.
- Generic reader/R37/parser/payload schema/cloud tools/CI/shared helpers unchanged.
- One documented new DEV code SCENARIO_OUTPUT_PATH; existing classified codes keep precedence.
- No actual F61/r/dt/vehicle/Controller/Runtime/CAN; preserve old environments/evidence.
- R_BUDGET unresolved, StaticFAIL, actualr/T2/vehicle scale null; no vehicle activation.
- Scoped reviewed PR → real CI → normal guarded merge/private HF under standing authorization.

## Review Focus

- Path.exists can swallow ValueError: invalid output must still reject before reads.
- Output exists/parent and classified object/code/original cause must keep precedence.
- Generic R37 surrogateescape acceptance differs from R31 UTF8 receipt requirements.
- TypeError/interrupts and later reader/loader defects must not be reclassified.
- NUL OS argv is impossible; actual fresh CLI main and real permission paths must stay distinct.

---

### Task 1: Qualify R31 execution paths

**Files:**
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_run.py`
- Create: `tools/cyberlateral_dev/project/test_scenario_execution_paths.py`
- Modify: `tools/cyberlateral_dev/docs/SYNTHETIC_SCENARIO_CLI_R31_KO.md`
- Modify: `tools/cyberlateral_dev/docs/SCENARIO_VALIDATION_R37_KO.md`

**Interfaces:**
- Consumes: `run_scenario(input_path: Path, output_path: Path) -> dict`, ScenarioError.code.
- Produces: unchanged signature and successful payloads; preflight SCENARIO_OUTPUT_PATH
  or SCENARIO_INPUT_FILE for unsupported execution path representations.

- [ ] Confirm clean existing linked worktree/new branch and R31 CLI baseline.
  Expected: existing10 PASS, actual read/load barriers reproduce ordering defects.
- [ ] Write ten focused methods named for the behaviors in Spec/Review Focus.
  Run `python -B -m unittest discover -s project -p test_scenario_execution_paths.py -v`.
  Expected RED: missing fail-fast/classification; unchanged scope controls green.
- [ ] Add only the two ScenarioError-first preflight boundaries. Preserve existing
  guards first, UTF8 encode/NUL checks without changing the Path, then reader/model.
  Expected: new tests green; existing R31/R37/reader/R51 tests green; no output on rejection.
- [ ] Compare same synthetic sign/resumed fixtures at baseline/fixed. Expected:
  numeric core and INPUT/TRACE/SUMMARY/validation exact, explicit identity delta,
  closed manifests and unchanged inputs/source. No independent numerical overclaim.
- [ ] Run fresh `dev.py verify` and cloud `ci_verify.py` outside source. Expected:
  all tests/static/compile PASS; wheel unchanged; actual observed counts reported.
- [ ] Commit, rerun new10 completion tests and record BASE/HEAD. One fresh final
  branch review, one TDD Important/Critical fix pass if needed; Minor deferred.
  Expected: clean exact head with no unresolved Important/Critical.
- [ ] Normal scoped push/create/attach PR; inspect actual exact-head CI/artifacts;
  seal evidence twice, independently verify; continue guarded main/HF integration.
  Expected: no bypass/force/delete, old HF objects preserved, vehicle gates closed.
