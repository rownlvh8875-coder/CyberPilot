# R32.2 Mobile Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Fix mobile axis readability without changing recorded calculations.

**Architecture:** HTML axis labels surround the existing SVG geometry. No browser
dependencies, scripts or additional consumer API.

**Tech Stack:** Python3.12.13 stdlib, static HTML/CSS/SVG, existing unittest gate.

**Spec:** `docs/superpowers/specs/2026-11-01-r322-mobile-chart-design.md`

## Global Constraints

R_BUDGET UNRESOLVED; Static Gate FAIL; actual r/T2/vehicle scale null.
No F61/Controller/Runtime/CAN/actual vehicle/r/dt/candidate evaluation.
Reader model executions0; inherited full unit/CI model work is additional NONZERO.
No native rebuild, original-source edit, public wheel change or main merge.

## Review Focus

- Long signed/decimal Y labels must not cross the plot or leave the card.
- Terminal index4095 must not clip at the right edge.
- Single-point resumed charts must retain visible points and one centered index.
- Narrow chart legends must wrap complete label entries, not truncate them.
- Browser-independent checks must not be reported as actual visual PASS.

## Task 1: Readable chart labels and delivery

**Files:** Modify `integration_tools/scenario_report_html.py`; create
`project/test_scenario_report_chart.py`; create results and local recheck docs.

**Interfaces:** Consume `_render_html(view)` after existing reader validation;
produce escaped bytes with exactly the same series geometry and VIEW.json.

- [ ] Add real HTML regressions: all tick/caption text outside SVG, literal axis
  values for sign/resumed/flat4096, one centered resumed index, geometry unchanged,
  long signed Y labels and complete separate legend entries. Mutations caught:
  text restored inside shrinking SVG, lost terminal label, state/series mix-up.
- [ ] Run new unittest discovery before renderer edits. Expected: assertion FAIL
  because old SVG text/labels still present, not import/setup ERROR.
- [ ] Implement grid-based HTML axes,14px axis/legend text and padded plot-only
  SVG without changing any polyline point, circle coordinate or stored record.
- [ ] Run report tests. Expected: all PASS, no skipped new regressions.
- [ ] Run full `uv run --locked python -B dev.py verify --output NEW` and read logs.
  Expected: full suite/static tools/immutable wheel PASS, exact count observed.
- [ ] Compare actual saved sign/resumed input hashes and VIEW bytes to R321, render
  twice locally and in committed fresh archive. Expected: unchanged VIEW/source,
  deterministic changed HTML, actual receipts retained and all checksums PASS.
- [ ] Document bounded status and local recheck prompt; commit code/tests/docs.
- [ ] One fresh whole-branch review. Grade findings and disposition all exclusions.
  Important fixes require one RED/GREEN pass; no repeated reviewer dispatch.
- [ ] Push feature branch, manually run only scoped CI, keep PR2 Draft/unmerged.
  Verify exact-head CI artifact and deterministic evidence ZIP/sidecar.

Self-review: one cohesive display change, no task interface conflicts. Each focus
has a rendered-output regression or an explicit local browser check. User standing
delegation selects inline execution; no additional approval pause.
