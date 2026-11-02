# R40 Synthetic Workflow Implementation Plan

> **For agentic workers:** use superpowers:executing-plans inline; one fresh whole-branch reviewer.

**Goal:** one DEV command for owned synthetic validation, batch/report, independent reference and optional regression.
**Architecture:** reuse R33/R37/R39/R34 functions, one bounded original snapshot, separate publication/classification.
**Tech Stack:** existing CPython3.12.13/Linux/binary64/NumPy2.5.3 lock, stdlib frontend; no dependencies added.
**Spec:** SCENARIO_WORKFLOW_R40_DESIGN.md

## Global Constraints

Public0.3.0/wheel/lock/R31–R39 numerical behavior unchanged. No real input/F61/r/dt/Controller/Runtime/CAN.
actualr/T2/scale=null, R_BUDGET UNRESOLVED, StaticGateFAIL, F70UH/V/F71 NOT_ALLOWED.
Baseline main7a4bdec6a1d9b2859d32ef96f4c9fe82f5623646; feature-only local work, no push/merge/new CI.
No overwrite/resume/delete/autoupdate. All user input cases independent. Whole suite plus full verify required.
Preserve audit evidence externally; no cleanup of past evidence or workspaces.

## Review Focus

- Original input or baseline changes after capture: later stages use owned snapshot, not original paths.
- All rejected inputs and missing raw bytes: no vacuous VERIFIED or fabricated fallback input.
- Malformed baseline/output collision: reject before model or publication, preserve existing bytes.
- Reference ERROR vs numerical/regression DIFFERENT: separate exits/counts and unknown failed work.
- Private receipts: no full-output byte identity overclaim; root portable summary remains deterministic.

### Task 1: core owned workflow and result contract

Files: create integration_tools/scenario_workflow_input.py, scenario_workflow_run.py,
scenario_workflow_summary.py; project/test_scenario_workflow.py.
Consumes existing prepare_batch/validate_scenario/run_batch/check_batch/run_comparison/read_batch.
Produces `run_workflow(inputs: list[Path], output: Path, baseline: Path | None = None) -> dict`,
`WorkflowError.code`, `exit_code(record: dict) -> int` and full new output.

- [x] Write real tests with literal statuses/counts: sign+resumed VERIFIED/model5/reference5,
  mixed sign+bad VERIFIED_WITH_INPUT_REJECTIONS/exit1/model4/ref4, bad-only NO_COMPLETED_CASES/exit1.
- [x] Watch missing core module assertions fail, not import errors.
- [x] Test raw-unavailable, duplicate/symlink/FIFO/oversize, output guards, full/corrupt/portable
  baseline, owned original mutation, source mutation, stage failure preservation.
- [x] Implement owned preflight plus run_workflow using existing functions, no numerical copy.
- [x] Test literal priority mapping, optional regression MATCH/difference and same-input root
  portable repeats with different full receipts; verify every full root/nested checksum and gates.
- [x] Run targeted tests then full unittest discovery, observe GREEN. Record task completion/local commit.

### Task 2: CLI, documentation and full acceptance

Files: tools/scenario_workflow.py, project/test_scenario_workflow_cli.py,
docs/SCENARIO_WORKFLOW_R40_KO.md, README.md, docs/OFFLINE_QUICKSTART_CURRENT_KO.md.
Consumes Task1 run_workflow/WorkflowError/exit_code.
Produces standalone --input repeat/--output/optional --baseline CLI, canonical stdout and docs.

- [x] Write real CLI tests before CLI: valid exit0, mixed/all rejected exit1,
  missing input/corrupt baseline/output/unknown --rate exit2 and no traceback.
- [x] Watch missing CLI assertions fail, then implement existing cold-cache frontend pattern.
- [x] Test frontend model/native import barrier with fresh actual worker execution, baseline path
  plus source/input preservation, no automatic baseline overwrite.
- [x] Document exact states/exits/relative links/private receipt scope/model-reference counts and gates.
- [x] Targeted tests GREEN then full `dev.py verify --output <new audit output>`; require full suite,
  Ruff/Ty/Codespell/memory compile and unchanged wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
- [x] Execute real sign/resumed, R35mixed and baseline workflow in two independent new output roots;
  compare root portable files and validate all full manifests, preserving any failed output.
- [ ] Fresh whole-branch review; rule on every declined scope, fix significant findings RED→GREEN
  plus full suite, record deferred minors. Local commit and finish branch without remote mutation.
