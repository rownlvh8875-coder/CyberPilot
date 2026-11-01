# R37 Validation-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Track steps with checkbox (`- [ ]`) syntax.

**Goal:** Inspect declared-synthetic V1 input without importing or running the model.

**Architecture:** Small inert validator consumes unchanged R31 reader. Existing
source DEV CLI selects validation or execution; installed wheel stays unchanged.

**Tech Stack:** Existing stdlib/CPython3.12.13 DEV and unittest gate.

**Spec:** ../specs/2026-11-01-r37-validation-design.md

## Global Constraints

- Baseline6fed18cb92bcd3f95a2e46fe2cefc593d4328e8e; isolated feature branch.
- Unchanged R31 schema/errors, public0.3.0 API/source/wheel, dependency/lock,
  workflow/native/historical R30/R31/fixtures. Local commits/review only.
- Validation:one canonical stdout JSON line, exit0/2, no result files;
  temporary cold-cache allowed. CLI misuse:argparse stderr/exit2.
- --validate-only forbids --output before read; normal mode requires --output.
- Validation:model/engine/runner imports and calls0 including rejections.
- No F61/r/dt/Controller/native/vehicle Runtime/CAN/actual data/candidate work.
- Actualr/T2/scale null; R_BUDGET UNRESOLVED; Static Gate FAIL;
  SOURCE_SCHEMA_UNQUALIFIED6000; Candidate/Runtime NO_GO; F70UH/V/F71 NOT_ALLOWED.

## Review Focus

- Model-free input PASS must not claim source/runtime readiness; test absent model.
- Ambiguous/missing mode flags reject before reads/writes; test reader barrier.
- Late invalid/nonregular/unknown-policy inputs use unchanged codes with no model.
- SHA/count/index bind real snapshot bytes; rejected identity stays null.
- Existing R31/R33 numerics/wheel unchanged; DEV producer identity changes explicit.

### Task 1: Validation mode with behavioral tests

**Files:**Create integration_tools/scenario_validate.py and
project/test_scenario_validate.py; modify tools/scenario.py;
create docs/SCENARIO_VALIDATION_R37_KO.md and this spec/plan.

**Interfaces:**Consumes read_scenario(Path)->ScenarioSpec/ScenarioError,
scenario_output canonical(value)->bytes/GATES. Produces
validate_scenario(input_path:Path)->dict with exact spec fields; CLI
--validate-only stdout JSON exit0/2 without --output.

- [ ] Baseline unittest discover. Expected:570 PASS, no product edits before green.
- [ ] Write test_cli_valid_and_resumed_json_without_output:accepted0, actual SHA,
  sample_count2/index0..1 or count1/index5..5, model_executions0.
- [ ] Write test_invalid_inputs_report_original_codes_and_null_identity for JSON,
  non-finite, late integer request, index gap, state and extra rate policy;
  test_file_rejections for missing/symlink/FIFO/directory/oversize.
- [ ] Write test_mode_errors_before_input_read; test_fresh_cli_import_barrier;
  test_minimal_export_needs_no_model_payload; test_validator_import_is_inert;
  test_repeated_moved_inputs_are_canonical_and_private_path_free.
- [ ] Run new module. Expected:FAIL for missing option/module, not fixture mistakes.
- [ ] Implement validate_scenario and exclusive CLI mode using exact result fields,
  copied gates/null rejected metadata. Import scenario_run only in execution branch.
- [ ] Run new and existing scenario tests. Expected:PASS, validation model work0.
- [ ] Fresh full dev.py verify to external NEW output. Expected:suite/static/
  compiles/wheel PASS, dynamic counts from SUMMARY, old wheel SHA unchanged.
- [ ] Document result/exit/claim boundaries and commit feature/tests/R37 docs.

### Task 2: Current discovery and whole-branch verification

**Files:**Modify README.md, docs/OFFLINE_QUICKSTART_CURRENT_KO.md and
docs/OFFLINE_CAPABILITY_INVENTORY_CURRENT.json.

**Interfaces:**Consumes Task1 committed feature SHA/validator symbol/CLI;
produces CURRENT source map pinned to actual committed source and current usage.

- [ ] Link R37 mode and acceptance-vs-ready distinction; disclose changed DEV
  producer metadata and preserve old R30 bytes. Refresh inventory source hashes.
- [ ] Run help/valid/rejected validation and normal sign→report/two basic batches→
  comparison. Expected:[2,-2,0,2], each batch2/0/5, MATCH/sample5/diff0/newmodels0.
- [ ] Validate source SHA/AST pointers/doc links/output manifests; preserve
  examples/public source/old R30 bytes. Human prose earns no wording unit tests.
- [ ] Fresh final full gate. Expected:suite/static/compile/wheel PASS.
- [ ] Commit docs and request one independent whole-branch review. Material fixes
  only:RED→GREEN/full suite. Retain local branch/worktree and external evidence.

Native inline execution selected under owner's no-question delegation. No
independent implementer agents needed; one fresh final reviewer is sufficient.
