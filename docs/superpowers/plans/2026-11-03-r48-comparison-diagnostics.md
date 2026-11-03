# R48 Comparison Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** R44 cleanup diagnostics cannot replace a determined comparison result.

**Architecture:** Share the existing R47 best-effort diagnostic helper across
R44/R46, preserving the R46 runner's private import name. No comparison or output
implementation changes beyond the two R44 post-result call sites.

**Tech Stack:** Existing Python3.12.13, unittest, stdlib; unchanged dependencies.

**Spec:** `docs/superpowers/specs/2026-11-03-r48-comparison-diagnostics-design.md`

## Global Constraints

- Public wheel0.3.0, model/reference/producer/limiter, locks/dependencies,
  input/output schema and rendering remain unchanged.
- R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/vehicle scale=null.
- No F61/actual r/dt/vehicle/Controller/Runtime/CAN execution or activation.
- Feature PR only; no main merge or live HF write in this stage.

## Review Focus

- Completed DIFFERENT must retain exit1, not merely MATCH0 success.
- Completed source ERROR2 must keep its record, unlike rejected input2.
- Warning hooks and broken stderr must not replace committed API results.
- Precommit/publication and pre-result cache failures must remain failures.
- Sharing the helper must retain R47 default warnings and interrupt propagation.

## Task 1: Shared post-result diagnostic boundary

**Files:**
- Create: `tools/cyberlateral_dev/integration_tools/result_diagnostics.py`
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_campaign_compare_run.py`
- Modify: `tools/cyberlateral_dev/tools/scenario_campaign_compare.py`
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_campaign_report_run.py`
- Test: `tools/cyberlateral_dev/project/test_scenario_campaign_compare_cli.py`
- Modify: `tools/cyberlateral_dev/docs/SCENARIO_CAMPAIGN_COMPARISON_R44_KO.md`
- Modify: `tools/cyberlateral_dev/docs/SCENARIO_CAMPAIGN_REPORT_R46_KO.md`

**Interfaces:**
- Consumes: existing `run_campaign_comparison(baseline: Path, candidate: Path,
  output: Path) -> dict`, `exit_code(record: dict) -> int`, both existing CLIs,
  complete `real_campaign`/`copy_campaign` fixtures and R46's38 tests.
- Produces: private `result_diagnostics._warn_after_result(message: str) -> None`,
  imported under the same name by both runners. Existing public API/CLI unchanged.

- [ ] Add real API cleanup tests with warnings-as-errors for MATCH/DIFFERENT/ERROR;
  preserve exact source verdict/regression/exit and a closed marker/Manifest.
  Add warning-hook and stderr failure cases, both KeyboardInterrupt/SystemExit
  propagation, and precommit link failure. Default-warning controls remain.
- [ ] Add isolated CLI cache-fault tests under `-W error::RuntimeWarning` for
  MATCH0, actual saved-difference1, completed source ERROR2, rejected-input2.
  Distinguish marker presence and exact unchanged rejection. Also test cache
  creation failure before result and broken diagnostics after result.
- [ ] Run `python -B -m unittest discover -s project -p test_scenario_campaign_compare_cli.py`.
  Expected RED: diagnostic-fault cases fail for changed result/exit, not test typos.
- [ ] Move existing R47 helper unchanged into the shared module. Import it into
  both runners; replace only R44 API/CLI warning calls. Update Korean limitations.
- [ ] Rerun all `test_scenario_campaign_compare*.py` and `test_scenario_campaign_report*.py`.
  Expected: all PASS with pre-result rejection, default warnings and interrupts preserved.
- [ ] Run full `dev.py verify --output <new external gate>` and cloud `ci_verify.py
  --hf-python <existing isolated SDK> --output <new external cloud>`.
  Expected: full suite/static PASS,225 own compiles, unchanged wheel0.3.0.
- [ ] Compare baseline/fixed R44 saved-value files on the same complete campaign
  input(s) and R46 HTML/VIEW on the exact same saved R44 input in separate CLI
  processes. Expected: bytes equal, closed Manifests, workers0, input unchanged;
  private receipts and source identities may differ as documented.
- [ ] Commit the fix/tests/docs, then rerun the R44 CLI file as the completion gate
  and ledger exact BASE/HEAD/results. One fresh whole-branch reviewer; one TDD
  Important/Critical fix pass if needed, no re-review, Minors recorded only.
- [ ] Open feature PR, verify actual exact-head checks/artifacts, seal two identical
  evidence ZIPs and independently parse their closure/hashes. Keep branches/envs.
