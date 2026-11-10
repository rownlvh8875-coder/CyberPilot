# CORE38 Offline Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the deferred diagnostic issue,triage actual-use prerequisites and
deliver the verified offline branch to GitHub without opening runtime scope.

**Architecture:** Message-only test-helper fix with real-record RED/GREEN tests;
bounded historical evidence review;unchanged existing DEV/scoped CI execution.

**Tech Stack:** Python3.12/unittest/dataclasses,existing DEV tooling,Git/GitHub CLI.

**Spec:** [design](../specs/2026-11-11-offline-release-readiness-design.md)

## Global Constraints

- No target/API/formula/fixture/cut/wheel/F61 or actual-use gate changes.
- Keep original assertion ordering/fail-fast behavior;add diagnostic context only.
- Actual r/T2/scale=null,R_BUDGET UNRESOLVED,StaticGateFAIL;no numeric fallback.
- No actual data/raw decoding/Controller/Runtime/CAN/F61/actual-r-dt execution.
- Only normal new-branch push and explicit existing offline CI dispatch allowed.
- No PR/main merge,force push,workflow edits,skip-ci or unrelated PR1 mutation.
- Preserve host-owned worktree,old refs and all historical evidence.

## Review Focus

- Diagnostics must identify sample/field and prefix endpoint without swallowing failure.
- Assertion wording changes must not change numeric expectations or loop continuation.
- Definition approval and backup observations must not become actual numeric authority.
- Remote publication must not silently trigger broad runtime CI or bypass checks.
- Actual binding/rate/static gaps must block evaluation/deployment,not offline development.

## Task 1: diagnostics and actual-use readiness

**Files:**new `project/test_fault_lifecycle_diagnostics.py`,new
`docs/REMAINING_WORK_READINESS_KO.md`,this plan/spec;modify
`project/test_fault_lifecycle.py` messages only and README/backlog navigation.
External workspace owns evidence,ledger/briefs/logs and publication receipts.

**Interfaces:**consumes CORE37 helper and real public simulate output;produces
2diagnostic methods,unchanged CORE37 behavior and a prerequisite readiness table.

- [ ] Baseline original CORE37/CORE36/state16PASS;capture prior identities/refs.
- [ ] Write2diagnostic tests;run against old helper ->2assertion FAIL/errors0.
- [ ] Add sample_index/field/prefix_end messages only;run ->2PASS plus original2PASS.
- [ ] Read/hash bounded existing approval/readiness/intake/search evidence;record
  missing actual pair/period/scale/static authority without new scans/calculations.
- [ ] Run original CORE37 twice with measured counts and event hashes equal to
  old baseline;keep new diagnostic200steps per run separate from4200original.
- [ ] Full `.venv/bin/python -B dev.py verify --output <work>/final-verify`
  ->1924PASS/staticPASS/332compiles,unchanged wheel/pins/98DEV Manifest.
- [ ] Verify source696/prior689/ref42 and links;local commit;task-done4PASS.

## Task 2: safe GitHub delivery preparation

**Files:**external publication preflight,workflow trigger inventory and branch
diff metadata;no new repository edits.

**Interfaces:**consumes Task1 verified HEAD,gate results and explicit unresolved
actual-use prerequisites;produces reviewed delivery package and exact safe refs.

- [ ] Compare live main and local diff;all changes stay within offline component
  and plan docs;existing workflows unchanged and custom branch matches no push
  trigger. Verify existing two offline dispatch workflows and upstream PR risk.
- [ ] Task-done rerun focused4PASS and source/ref/diff preflight;then one fresh
  whole-branch reviewer checks new changes and integration boundary. Important
  findings get one RED/GREEN+full-suite fix pass;minors deferred.
- [ ] Finish after review:normal push new branch only,verify remote HEAD;dispatch
  only CyberLateral Offline Development and Cloud Tooling by exact ref. Wait for
  terminal results with updates;record run URLs/head/conclusions without overclaim.
- [ ] Seal report/evidence;state PR/main integration blocked by broad upstream CI
  scope and actual-use stages blocked by missing authority. Request only the
  missing authority/CI-scope decision at handoff,not permission to repeat tests.

Self-review:Task1 produces verified bytes/readiness and Task2 consumes those exact
bytes/gates;no interface conflict. All Review Focus cases have tests or source/
workflow/evidence checks. Standing delegation opts out of another approval menu.
