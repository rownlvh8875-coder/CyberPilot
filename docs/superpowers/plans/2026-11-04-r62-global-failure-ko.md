# R62 Global Failure Korean Explanation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve R61-M1 without altering recorded failure facts or PASS output.

**Architecture:** Existing pure Markdown renderer appends descriptions from the
existing translation map below preserved whole-run JSON. No other code path changes.

**Tech Stack:** Existing Python3.12.13/cloud tests/static tools, explicit host browser.

**Spec:** `docs/superpowers/specs/2026-11-04-r62-global-failure-ko-design.md`

## Global Constraints

- Baseline e5b76678cff4d45a4915da0f9b26982711167b1d; existing linked worktree.
- No app/probe/classifier/API/lock/dependency/workflow/vehicle/policy changes.
- Preserve raw escaped JSON, statuses/exit0/1/2, checksum and last marker.
- PASS summary/case table/HTML/VIEW remain exact; no new observation or reader.
- Preserve all old evidence; Draft-only delivery, no main/HF write this task.

## Review Focus

- Global FAIL while every case PASS remains visibly FAIL with its original record.
- Multiple/unknown codes retain raw identifiers and use safe Korean labels.
- Empty accepted code lists never manufacture a reason or success explanation.
- Metadata escaping and fixed local links remain unchanged.
- Summary publication still precedes the closed checksum and final RESULT marker.

### Task 1: M1 fix, regression and scoped proof

**Files:** modify `tools/cyberlateral_cloud/browser_summary.py`, its
`tests/test_browser_summary.py`, and `docs/BROWSER_SMOKE_R60_KO.md`.

**Interfaces:** unchanged `render_summary(result: dict, file_sha256: dict[str,str]) -> bytes`.

- [ ] Baseline full cloud gate121/19compile PASS; reproduce raw-only global record.
- [ ] Extend existing global-failure test to require literal Korean explanation in
  the whole-run section. Add one method testing multiple/unknown and empty records;
  assert raw records/case PASS persist. Browser-family command expected2FAIL/0ERROR.
- [ ] Minimal global rendering change; same browser-family31 tests expectedPASS.
- [ ] Usage doc note; full cloud gate122/19compile expectedPASS, Ruff/Ty/Codespell.
- [ ] Real browser twice10PASS; summaries and four HTML/VIEW exact with each other
  and canonical R61 main evidence; closed37entries/18owned links each.
- [ ] External test-only BrowserContext-close wrapper makes exactly one extra page
  navigate to an unlisted loopback path, retains original close and catches only
  expected route-abort error. Actual command expectedexit1/global code count1,
  all10casePASS/raw record/Korean explanation/closed manifest. No production patch.
- [ ] Confirm Git diff app/probe/workflows empty; inherited DEV883 proof explicitly
  not a fresh rerun. Full cloud unit command again expected122PASS; commit fix.
- [ ] Single fresh whole-branch review; Critical/Important one RED/GREEN fix pass,
  Minor ledgered. Normal feature push/Draft PR/attach/exact-head scoped CI artifact.
- [ ] Two deterministic ZIPs byte-identical; independent bounded stdlib verification.

Self-review: one task/no shared interfaces; all five Review Focus behaviors have
the new/existing tests or actual publication/browser controls above. No new UI.
