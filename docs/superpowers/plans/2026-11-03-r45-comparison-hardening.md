# R45 Comparison Boundary Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize ordinary R44 API preflight errors and cover R43 verdict precedence in both orders.

**Architecture:** Catch expected path/OS exceptions only at the R44 preflight boundary.
Keep specific CompareError mapping first. Parameterize the existing real R43 worker
test without changing its producer. No new abstractions or dependencies.

**Tech Stack:** CPython3.12.13/Linux, unittest, existing pinned uv0.12.23 DEV environment.

**Spec:** `docs/superpowers/specs/2026-11-03-r45-comparison-hardening-design.md`

## Global Constraints

- Public0.3.0 API/wheel, model/reference source, shared R34 preflight, R43 producer,
  locks/dependencies, cloud tools and CI configuration remain unchanged.
- R_BUDGET UNRESOLVED; Static Gate FAIL; actual r/T2/vehicle scale null;
  Candidate/Runtime NO_GO; F70UH/F70V/F71/vehicle activation NOT_ALLOWED.
- No F61/actual r/dt/vehicle work. Synthetic fixture/unit/gate/CI work NONZERO.
- Open reviewed PR+actual CI only; no main merge/HF refresh or cleanup.

## Review Focus

- Expected OS/path errors reject before data/source reads or output publication.
- Specific existing output/encoding/runtime rejection codes are not replaced by IO.
- Programmer TypeError is not silently reclassified as an invalid-path rejection.
- Both mixed ERROR/DIFFERENT orders preserve runs/findings/counts and ERROR/exit2.
- Real CLI denied paths stay bounded/no traceback and successful saved comparisons stay exact.

---

### Task1: R44 preflight normalization

**Files:** modify `tools/cyberlateral_dev/integration_tools/scenario_campaign_compare_run.py`,
`project/test_scenario_campaign_compare_run.py`, `project/test_scenario_campaign_compare_cli.py`
under that component, and `docs/SCENARIO_CAMPAIGN_COMPARISON_R44_KO.md`.
**Interfaces:** consumes existing `_preflight(Path,Path,Path)` and `CompareError`;
produces the unchanged public `run_campaign_comparison` signature and CampaignCompareError.

- [x] Add direct tests expecting literal `CAMPAIGN_COMPARE_IO` for PermissionError,
  OSError and embedded-NUL paths, with no output/source reads; observe current failures.
- [x] Add the minimal expected-exception handler after existing specific mapping.
- [x] Verify those regressions GREEN, exact specific codes retained and TypeError propagated.
- [x] Run a real isolated CLI permission-denial control and document the API boundary.
- [x] Run all `test_scenario_campaign_compare_*.py`; commit Task1.

### Task2: R43 mixed-verdict order coverage

**Files:** modify `tools/cyberlateral_dev/project/test_scenario_campaign.py` only.
**Interfaces:** consumes unchanged `run_campaign(list[int],int,int,Path)->dict`.

- [x] Parameterize existing real reference ERROR/Difference test with seed orders
  `[42,43]` and `[43,42]`; literal expected runs/findings follow each order, totals32/16/1.
- [x] Run the test, expected GREEN for existing correct producer; do not invent a defect.
- [x] Demonstrate reverse-order failure under an isolated first-child-wins function mutant.
- [x] Run all campaign tests; commit Task2.

### Verification and delivery

- [ ] Full `dev.py verify` PASS; cloud `ci_verify.py` PASS; unchanged wheel/source guards.
- [ ] Actual saved R44 comparisons/control checks and independent Manifests PASS.
- [ ] One fresh whole-branch review; Important fixes only, each RED→GREEN, no re-review.
- [ ] New feature PR with exact-head actual CI/artifact verification; seal evidence.
