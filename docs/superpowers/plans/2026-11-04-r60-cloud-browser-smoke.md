# R60 Cloud Browser Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the bounded R59 real-browser regression reusable without old evidence folders.

**Architecture:** An opt-in stdlib orchestrator renders preserved fixture records
in an existing app interpreter. A lazy-loaded host browser probe serves only
owned report bytes and records explicit layout verdicts and screenshots.

**Tech Stack:** Existing CPython3.12.13 app and host Python/Playwright/Chromium;
no new dependency installation, lock changes or default browser CI.

**Spec:** `docs/superpowers/specs/2026-11-04-r60-cloud-browser-smoke-design.md`

## Global Constraints

- Main baseline1f5ebb2b91f5d2d475e630d364f91ffaf9118c26, existing isolated worktree.
- Existing app/model/wheel/source fixtures and CI unchanged; cloud modules only.
- Missing dependencies fail closed; no downloads, policy changes or public upload.
- No vehicle/F61/r/dt/Controller/Runtime/CAN work; actualr/T2/scale null.
- StaticFAIL, Rate Budget unresolved, Candidate/Runtime NO_GO, vehicle prohibited.
- External new outputs only; source/input/report bytes unchanged, failures retained.

## Review Focus

- Missing browser/library/app or wrong component must not produce a PASS.
- Old footer CSS must cause an actual layout failure, not merely a source check.
- Local HTTP must never expose receipts/source/paths or allow external requests.
- Existing/symlink/in-component output and mutated source must fail safely.
- Chart/table/link regressions must be classified even when page width fits.

### Task 1: Opt-in runner, evidence and regression tests

**Files:** Create `tools/cyberlateral_cloud/browser_smoke.py`, `browser_probe.py`,
`tests/test_browser_smoke.py`, `tests/test_browser_probe.py`,
`docs/BROWSER_SMOKE_R60_KO.md`; update cloud `README_KO.md` only for discoverability.

**Interfaces:** `browser_smoke.main(argv=None) -> int` owns CLI/new output/rendering
and closed evidence. `browser_probe.assess_case(profile, width, metrics) -> list[str]`
classifies independent observed metrics; `preview(payloads)` is a context manager
over an immutable allowlist; `run_browser(reports, captures, executable) -> dict`
uses an explicitly installed Playwright and real Chromium. Browser import is lazy.

- [ ] Run baseline DEV883 and cloud91 gates; confirm clean linked-worktree branch.
- [ ] Write failing behavior tests for real CLI/help/prerequisites/output guards,
  source mutation checks, full layout classifications and HTTP allowlist.
- [ ] Run new tests and observe missing-feature failures, then implement the
  minimal runner/probe. No browser mocks masquerading as actual layout tests.
- [ ] Run new tests and cloud suite; verify default execution needs no Playwright.
- [ ] Run actual new command twice with preserved fixtures at all ten cases.
  Expect exit0, tenPASS,12captures, fourlinks, no forbidden imports/executions;
  compare four HTML/VIEW files exactly and inspect actual mobile screenshots.
- [ ] Run copied old-CSS renderer negative control; expect exit1 and mobile
  overflow failures. Run missing-browser CLI control; expect2/no output.
- [ ] Run full final DEV gate and cloud gate with Ruff/Ty/Codespell/compile;
  unchanged wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
- [ ] Commit feature and request one fresh whole-branch review. Resolve Important/
  Critical in one RED/GREEN pass, record declined boundaries and deferred minors.
- [ ] Normal new feature push/Draft PR, attach, verify actual scoped CI and artifacts.
  Do not merge main or publish HF in this feature task.
- [ ] Seal reproducible external evidence; independently verify Manifest/CRC/seal.

Plan self-review: one task, no shared task interfaces; each Review Focus failure
is owned by pure boundary tests or the mandatory actual-browser controls.
