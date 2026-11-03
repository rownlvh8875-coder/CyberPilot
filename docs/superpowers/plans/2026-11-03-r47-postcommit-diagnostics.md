# R47 Post-result Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve R46's determined API/CLI result when cleanup warning delivery fails.

**Architecture:** One private best-effort warning helper in the R46 runner, reused
by the R46 CLI. Catch ordinary exceptions only inside diagnostic delivery, never
around publication or result determination. Keep existing warning codes.

**Tech Stack:** Existing Python3.12+, unittest, standard library; no new dependency.

**Spec:** `docs/superpowers/specs/2026-11-03-r47-postcommit-diagnostics-design.md`

## Global Constraints

- R44's separate post-result warnings are out of scope, not claimed fixed.
- Public wheel0.3.0, dependencies/locks, model/reference/calculator untouched.
- R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/scale=null.
- No F61/actual r/dt/vehicle/Controller/Runtime/CAN execution or activation.
- Feature-stage PR only; no main merge or Hugging Face writes in this stage.

## Review Focus

- Warning promoted to error after committed index: API returns real completion.
- CLI cache cleanup after rejection: exit2 and original rejection remain intact.
- A failing custom warning hook plus closed stderr: no ordinary exception replaces result.
- Cleanup or I/O error before result: still rejects; no false completion marker.
- Interrupt/exit from a diagnostic hook: not swallowed by an overbroad catch.

## Task 1: Harden R46 diagnostics and prove publication invariance

**Files:**
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_campaign_report_run.py`
- Modify: `tools/cyberlateral_dev/tools/scenario_campaign_compare_report.py`
- Test: `tools/cyberlateral_dev/project/test_scenario_campaign_report_cli.py`
- Modify: `tools/cyberlateral_dev/docs/SCENARIO_CAMPAIGN_REPORT_R46_KO.md`

**Interfaces:**
- Consumes: existing `run_report(input_path: Path, output_path: Path) -> dict`,
  `main(argv=None)`, complete saved fixture `real_comparison(kind='match')`.
- Produces: private `_warn_after_result(message: str) -> None`, same public results,
  same four output files; no new output schema or CLI flag.

- [ ] Write failing API tests: warnings-as-errors, custom warning hook failure,
  closed/broken stderr, BaseException propagation. Inject cleanup only after real
  temp cleanup; assert REPORT_COMPLETE and all four files/closed Manifest for
  successful ordinary-exception cases. Existing default-warning test stays.
- [ ] Write isolated CLI fault tests using a test-only Python `-c` wrapper:
  `-W error::RuntimeWarning`, cleanup fault only for `cyberlateral-r46-cache-`.
  Valid input exits0/REPORT_COMPLETE/closed Manifest. Missing input exits2,
  original CAMPAIGN_REPORT rejection/no index. Add pre-result cache-enter failure
  and precommit hard-link failure controls, both reject/no index.
- [ ] Run `python -B -m unittest discover -s project -p 'test_scenario_campaign_report_cli.py'`.
  Expected RED: new warning-filter/hook cases expose post-result exceptions;
  controls preserve existing behavior. Save full output, no implementation yet.
- [ ] Implement `_warn_after_result(message: str) -> None` in the runner, retaining
  RuntimeWarning delivery first and bounded stderr fallback; use it only in the
  two existing post-result cleanup branches. Update Korean diagnostic limitations.
- [ ] Rerun the CLI test file and all `test_scenario_campaign_report*.py`.
  Expected: all PASS, no unhandled warnings/errors.
- [ ] Run `python -B dev.py verify --output <new external gate>` and cloud
  `ci_verify.py --hf-python <existing SDK Python> --output <new external cloud>`.
  Expected: all tests, Ruff/Ty/Codespell,224 own compiles and unchanged public wheel PASS.
- [ ] Compare same saved input baseline/fixed HTML and VIEW byte-for-byte in two
  separate CLI processes; verify closed Manifests and renderer workers0. Receipts
  may differ in source/path identity. Expected: HTML/VIEW identical.
- [ ] Commit the fix and tests together after checks, complete ledger with command
  output, then dispatch one fresh whole-branch reviewer. Resolve Important/Critical
  in one RED→GREEN fix pass/full suite; ledger Minors without a second review.
- [ ] Open the feature PR, verify actual exact-head checks/artifacts, and seal two
  byte-identical evidence ZIPs. Keep existing branches/envs/evidence; do not merge.
