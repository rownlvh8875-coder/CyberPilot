# R53 Saved-report Path Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound saved-report input/output path failures without hiding later defects.

**Architecture:** Narrow descriptor and R32 preflight error boundaries, classified
exceptions first; generic reader filesystem encoding differs intentionally from
the UTF8 receipt-producing frontend. No new shared abstraction or dependency.

**Tech Stack:** Existing CPython3.12.13/Linux/stdlib/unittest and locked toolchain.

**Spec:** `docs/superpowers/specs/2026-11-03-r53-report-path-design.md`

## Global Constraints

- Public wheel/API, model/reference/limiter/schema/HTML/cloud/CI/locks unchanged.
- Existing classified codes/objects/original causes and descriptor cleanup retained.
- No broad later-reader/renderer catch; no path repair or new location policy.
- Old branches/environments/evidence preserved. No approval pause between routine phases.
- R_BUDGET unresolved/StaticFAIL/actualr-T2-scale null and all vehicle gates closed.

## Review Focus

- ReportError subclasses ValueError: classified-first is mandatory at every new boundary.
- Path.exists can suppress ValueError: explicit representation check must precede reads.
- Generic reader surrogateescape support vs frontend UTF8 receipts must stay distinct.
- Input/output resolution codes, existing guard priority and untouched successful bytes.
- Actual mode000/CLI and impossible NUL OS argv must not be conflated.
- R51-M1 discharge must use an independently saved cause, not another alias.

### Task 1: Implement bounded recorded-report path handling

**Files:**
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_report_data.py`
- Modify: `tools/cyberlateral_dev/integration_tools/scenario_report_run.py`
- Create: `tools/cyberlateral_dev/project/test_scenario_report_paths.py`
- Modify: `tools/cyberlateral_dev/project/test_scenario_input_paths.py` (R51-M1 only)
- Modify: `tools/cyberlateral_dev/docs/SCENARIO_REPORT_R32_KO.md`

**Interfaces:** unchanged `read_report(Path) -> dict` and `run_report(Path,Path) -> dict`.
New frontend code REPORT_OUTPUT_PATH; existing reader/input REPORT_INPUT_FILE.

- [x] Record clean exact base/source identities and existing report30 baseline PASS.
- [x] Add focused tests for every Review Focus item plus real directory-fd cleanup,
  content code preservation and later failure propagation. Run
  `python -B -m unittest discover -s project -p test_scenario_report_paths.py -v`.
  Expected RED: raw ValueError/late encoding or unscoped output metadata failures;
  unchanged-behavior controls pass. Save raw ledger and exact observed count.
- [x] Minimal implementation: add ReportError-first/ValueError acquisition catch;
  keep old output guards first, strict UTF8/NUL checks, separate input/output
  resolution boundaries. Save independent cause for R51-M1 and document contract.
  Expected GREEN new tests + existing report30 + R51path8, no forbidden imports.
- [x] Read same sign/resumed stored fixtures with baseline/fixed report frontends.
  Expected HTML/VIEW exact, source/input immutability and closed manifests;
  receipts may differ in source hashes/locations, no numerical oracle claim.
- [x] Run `dev.py verify` and cloud `ci_verify.py` into external evidence folders.
  Expected all tests/static/compile PASS, public wheel byte-identical. Actual
  counts only; no unobserved/skipped permission test claimed PASS.
- [ ] Commit, fresh completion tests; one fresh final branch reviewer, at most one
  TDD fix pass for Important/Critical. Defer Minor with explicit receipt if needed.
- [ ] Normal push/create/attach PR; verify actual exact-head CI artifacts, bounded
  two-build evidence/independent parse. Continue guarded main/HF backup/recoveries
  under standing authorization. No force/admin bypass/delete/new public service.
