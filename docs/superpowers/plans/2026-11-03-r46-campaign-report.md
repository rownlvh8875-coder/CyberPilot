# R46 Saved Campaign Comparison Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a data-only Korean HTML view of complete R44 saved comparison results.

**Architecture:** Bounded owned reader validates known R44/R34 records and Manifests.
An escaped static renderer consumes its view; isolated CLI publishes only after input/
source rechecks. Old formats and producers stay unchanged. No new dependencies.

**Tech Stack:** CPython3.12.13/Linux, unittest, existing uv0.12.23; installed Chromium
for external bounded visual acceptance, not a project/runtime dependency.

**Spec:** `docs/superpowers/specs/2026-11-03-r46-campaign-report-design.md`

## Global Constraints

- Known R44 V1 only: max4runs/12files,32MiB total,16MiB per file,256retained details.
- No old producer/comparator/model/oracle/generator/public0.3.0/wheel/lock/dependency/cloud/CI changes.
- Renderer model/reference/F61/actual r/dt/vehicle work0; fixture/unit/gate/CI NONZERO.
- R_BUDGET UNRESOLVED; Static Gate FAIL; actualr/T2/scale null; Candidate/Runtime NO_GO;
  F70UH/F70V/F71/activation NOT_ALLOWED. Open PR/evidence only; preserve old workspace.

## Review Focus

- Source ERROR/DIFFERENT with regressionMATCH must remain visibly failed, not promoted.
- Rehashed contradictory parent/child totals, alerts, identity flags and truncation reject.
- Missing values differ from present null, and hostile text is inert escaped visible text.
- Private receipt paths are never followed/copied into the view or emitted as links.
- Late input/source/publication/cleanup failures never contradict the HTML commit point.

---

### Task1: Owned reader and strict recorded schema

**Files (under tools/cyberlateral_dev):** create
`integration_tools/scenario_campaign_report_schema.py`,
`integration_tools/scenario_campaign_report_data.py`,
`project/scenario_campaign_report_fixture.py`,
`project/test_scenario_campaign_report_data.py`.
**Interfaces:** `CampaignReportError(code: str)` in schema;
`validate_comparison(record: dict, children: dict) -> None`;
`read_comparison(path: Path) -> dict` returns `view` and `hashes`.

- [ ] Build cached complete real R44 test outputs (match/difference/error/source-
  difference/added/truncated) with existing synthetic fixture utilities, no partial mocks.
- [ ] Write reader tests: literal values/statuses, source hash ownership, coherent
  record corruptions, cap/type/context/alert/identity contradictions, closed hashes,
  canonical JSON, missing/extra/link/FIFO/size guards and ignored private paths.
- [ ] Run reader tests RED for missing feature; implement strict schema then reader.
- [ ] Run reader tests GREEN and static checks; commit Task1.

### Task2: Static HTML, guarded publication and isolated CLI

**Files (same component):** create
`integration_tools/scenario_campaign_report_html.py`,
`integration_tools/scenario_campaign_report_run.py`,
`tools/scenario_campaign_compare_report.py`,
`project/test_scenario_campaign_report_html.py`,
`project/test_scenario_campaign_report_cli.py`;
modify README.md; create docs/SCENARIO_CAMPAIGN_REPORT_R46_KO.md.
**Interfaces:** consumes Task1 snapshot; produces internal `_render_html(view)->bytes`,
`run_report(input_path: Path, output_path: Path)->dict` and required input/output CLI.

- [ ] Write RED tests for exact visible typed values/presence, failed source vs equal
  regression, safe hostile text/no external links/scripts/private paths, fixed JSON links.
- [ ] Write RED actual CLI/API tests for complete four-file output/Manifest, renderer
  zero-work/forbidden imports, CLI source ERROR exit0/report status preserved, invalid
  input exit2/no output, required flags, existing/location/path guards, late mutations,
  pending-write failures, and postcommit cleanup warning semantics.
- [ ] Implement escaped responsive HTML and exclusive-link index commit point, no new
  worker/model calls; document command, statuses, limits, private vs portable scope.
- [ ] Run all R46 tests GREEN/static; actual saved128sample repeated reports and
  six control views, byte/Manifest/input/source checks, PC/mobile browser captures.
- [ ] Full dev.py verify + cloud ci_verify PASS and unchanged-source/wheel guards.
- [ ] Commit Task2, one fresh whole-branch review; Important fixes only RED→GREEN.
- [ ] Create feature PR, observe actual exact-head CI/artifacts; seal evidence twice.
