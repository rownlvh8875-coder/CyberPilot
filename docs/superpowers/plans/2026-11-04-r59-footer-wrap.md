# R59 Footer Wrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the reproduced R32 mobile footer overflow without hiding text.

**Architecture:** Extend one existing scoped CSS rule. Verify actual renderer
output with installed Chromium; keep all data, locks and model code unchanged.

**Tech Stack:** Existing CPython3.12.13/uv0.12.23 DEV; installed Playwright1.62.0
and Chromium154 for an external browser regression, no new dependency.

**Spec:** `docs/superpowers/specs/2026-11-04-r59-footer-wrap-design.md`

## Global Constraints

- Baseline main26ad702efb1e3ec6fa956202f9056bcea0655074; existing linked worktree.
- Only R32 footer wrap changes; no font shrinking, overflow hiding or prose edits.
- VIEW, graphs, values, model, wheel, locks and vehicle policies unchanged.
- Real r/T2/scale null; R_BUDGET unresolved; StaticFAIL; vehicle NO_GO.
- Browser/renderer model/F61/r/dt/native execution0; full-suite synthetic work separate.
- No main merge, HF publication, snapshot modifications, policy changes or deletion.

## Review Focus

- Long footer tokens at320/360/390/425px: no document overflow, actual pan0.
- Ordinary desktop text: full footer visible without shrinking or missing content.
- Single resumed point: centered index5 and legible14px chart labels remain intact.
- Wide exact-data table: internal horizontal scrolling still works, values unchanged.
- Non-model report boundaries: CSP/local links/private receipts and source bytes preserved.

### Task 1: Scoped footer fix and real browser regression

**Files:** Modify `tools/cyberlateral_dev/integration_tools/scenario_report_html.py`.
External test/evidence lives in `/workspace/cyberpilot-r59-footer-wrap-5PI6kA`.

**Interfaces:** Existing R32 CLI takes complete saved R31 input and a new output;
produces unchanged VIEW plus HTML differing only by footer wrapping. No new API.

- [ ] Confirm clean main baseline and run the full883-test suite before editing.
- [ ] Write/run external actual-renderer browser regression before the CSS edit.
  Assert document width equals viewport and pan0; expect failure390→391/pan1.
- [ ] Extend existing `code{overflow-wrap:anywhere}` selector to `code,footer`.
- [ ] Run the same regression; expect all selected widths to fit without tolerance.
- [ ] Recheck eight reports × desktop/mobile; all16 fit, exact data/links preserved.
- [ ] Run existing full DEV verify and cloud verification with the locked env.
  Expect883 tests, static/compile/wheel and all cloud tests PASS.
- [ ] Commit the scoped change, then verify committed output and request one fresh
  whole-branch review. Re-grade findings and record each declined boundary.
- [ ] After clean verification/review, normal feature push/PR and actual CI checks.
  Preserve branch/worktree/evidence; no main/HF integration in this task.
- [ ] Seal reproducible evidence and independently validate CRC/Manifest/seal.

Plan self-review: one task, no shared interfaces; all five Review Focus cases are
owned by its actual browser regression/selection. No text-only unit test is added.
