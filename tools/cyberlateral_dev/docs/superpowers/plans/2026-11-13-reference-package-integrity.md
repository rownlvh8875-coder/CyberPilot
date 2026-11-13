# Saved Reference Package Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Check a retained CORE70 package using one external manifest SHA,no rerun.

**Architecture:** Existing read-only bounded capture,strict manifest/payload hashes,
canonical JSON+narrow closed-authority envelope and UTF8 summary;fixed receipt.

**Tech Stack:** Existing Python3.12.13/Linux,unittest/static tools,no new dependencies.

**Spec:** `../specs/2026-11-13-reference-package-integrity-design.md`

## Global Constraints

- Baseabf791e5bc82ac4cd4615ced53f1e0ed7246de02;existing linked feature worktree.
- Existing APIs/arithmetic/model/helper/wheel/schemas/dependencies unchanged.
- External manifest SHA before paths;three single captures,exact flat regular files.
- JSON2097152bytes,summary65536bytes,Manifest512bytes;receipt16384bytes.
- Narrow envelope only;no audit row/summary semantics,original input or source auth.
- Inspector model0/reference0,subprocess0,writes0;separate nonzero fixture/gate work.
- R_BUDGETUNRESOLVED,Static GateFAIL,actual r/T2/scale null;actual use prohibited.

## Review Focus

- A coherently rehashed but misleading audit body must never become a semantic or arithmetic success claim.
- Both summary and JSON must be bound by the external manifest pin;changed manifest cannot bypass it.
- Special files,path replacement,late read errors and descriptor closure must preserve bounded captured-byte semantics.
- Cold help/inspection must avoid algorithm imports/execution,writes and implicit --run behavior.
- Stored MATCH/DIFFERENT,source identities and work counters must not override inspector authority fields or zero new work.

---

### Task 1: Complete saved package integrity API and CLI

**Files** relative to tools/cyberlateral_dev:
- Create `integration_tools/reference_package_integrity.py` (capture/verify/receipt).
- Create `tools/reference_package_inspect.py` (read-only CLI).
- Test `project/test_reference_package_integrity.py`.
- Create `docs/REFERENCE_PACKAGE_INTEGRITY_CORE71_KO.md`.
- Modify `README.md`,`docs/CORE_DEVELOPMENT_BACKLOG_KO.md`.
- This plan/spec:8scoped paths total.

**Interfaces:** Consumes unchanged `_directory`, `_read_file`, `_path`, `_parse`,
canonical/GATES/FLAGS. Produces exact API/receipt/CLI and errors in spec. No
CORE69/70 execution imports or report semantic validator is consumed.

- [ ] **Step1: Baseline/tests.** Existing CORE70+CORE66 tests PASS. Write tests
  using actual CORE70 outputs including DIFFERENT;assert external manifest pin,
  all3digests/sizes,fixed scope/false authority/unvalidated semantics,new work0.
  Corrupt each member/Manifest;test canonical JSON/envelope/UTF8,bounds/layout,
  all3single captures/fds/unchanged inputs and captured-path replacement.
  Prove forged body not trusted,cold -S blocked algorithm imports,CLI help/unique
  flags/no --run,short/zero/broken writes,prefix failure/globals/determinism.
- [ ] **Step2: RED.** Run `.venv/bin/python -B -m unittest discover -s project -p test_reference_package_integrity.py -v`.
  Expected missing-feature assertion failures,not import/fixture errors.
- [ ] **Step3: Implement API.** Capture exact flat3files once with unchanged helpers;
  verify external manifest SHA and both payloads,strict canonical JSON/envelope,
  summary UTF8;return fixed inspection-only receipt,no content passthrough.
- [ ] **Step4: CLI/GREEN/docs.** Two unique flags,usage before imports,canonical
  bounded stdout and fixed errors/global restoration. New and relevant old tests
  PASS;document manifest pin acquisition,scope and unchanged actual-use gates.
- [ ] **Step5: Static/freeze/full gate.** Scoped Ruff/Ty/Codespell/3compiles PASS;
  freeze8/protect751files/config/refs/limited primary. Run full `dev.py verify`
  into new external root. Expected actual2302+new tests,369compiles,98Manifest,
  existing wheel/reference pins. Preserve explicit flags/exit/logs.
- [ ] **Step6: Commit/task-done/review.** Only frozen tested paths committed;
  rerun new tests/ledger range. One fresh full-branch reviewer gets exact focus,
  spec/plan/rulings/raw receipts. Important fixes RED→GREEN and green whole gate;
  re-grade findings and rule set-asides,no second reviewer. Retain evidence.

Then standing-authorized normal backup/tracking fetch/main FF/fresh focused smoke/
normal push;exact main/push DEV+Cloud runs and one download per successful role
with full artifact verification. No force/reset/PR/workflow edits/CI skip/manual
rerun/cancel/dispatch,HF upload or actual vehicle work.
