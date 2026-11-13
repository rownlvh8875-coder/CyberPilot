# Reference Audit Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish one CORE69 audit, a Korean summary and checksum without rerun/overwrite.

**Architecture:** Digest/output preflight,one unchanged checker call,private trusted
formatter,complete serialization then unchanged CORE16 exclusive publication.

**Tech Stack:** Existing CPython3.12.13/Linux/numpy2.5.3,unittest and static tools.

**Spec:** `../specs/2026-11-13-reference-workflow-design.md`

## Global Constraints

- Base8fdd1633cf415b9a78e9954c7da387fb3eed9d5f;existing linked feature worktree.
- Existing model/wheel/helper/dependencies/prior APIs/schemas unchanged.
- Two lowercase64 pins before caller paths;output preflight before checker.
- One CORE69 call,model0/referenceN-1;one CORE16 publish,no retry/repair.
- JSON2097152bytes,Markdown65536bytes,receipt16384bytes;20audit row details.
- R_BUDGETUNRESOLVED,Static GateFAIL,actual r/T2/scale null;actual use prohibited.

## Review Focus

- A true saved/reference diagnostic DIFFERENT with audit MATCH must not be presented as all-success.
- Existing or illegal output paths must reject before reference work and preserve existing bytes.
- Late serialization/publication/stdout errors must never retry arithmetic or return a success receipt.
- Missing/extra rows and more than20differences must remain visible with exact omitted counts and complete JSON.
- Retained JSON/summary/checksum integrity must not become source/build/vehicle authority or independent admission.

---

### Task 1: Complete one-run audit publication

**Files** (relative to tools/cyberlateral_dev):
- Create `integration_tools/recording_reference_workflow.py` (API/private summary).
- Create `tools/recording_reference_workflow.py` (explicit opt-in CLI).
- Test `project/test_recording_reference_workflow.py`.
- Create `docs/RECORDING_REFERENCE_WORKFLOW_CORE70_KO.md`.
- Modify `README.md`,`docs/CORE_DEVELOPMENT_BACKLOG_KO.md`.
- This plan/spec:8scoped paths total.

**Interfaces:** Consumes unchanged CORE69 checker,CORE16 `_output`/`_publish`,
canonical JSON and CORE66 flags. Produces exact API/receipt/three files/CLI
defined in spec. Private formatter accepts fresh checker record only.

- [ ] **Step1: Baseline and tests.** Run old CORE64+69 tests. Write behavioral
  tests with real3transition fixture. Assert complete canonical JSON/states,
  new model0/reference3,helper1/2/0/3/3/0/6,three exact digests,one checker/publish.
  Include real saved DIFFERENT/auditMATCH and forged202/audit1. Test both absent
  sides,>20rows omitted count,all diagnostic/header indices and work distinctions.
  Test pins/output/preflight before work,captures/originals,serialization limits,
  nested output rejection before checker with source package layout preserved,
  partial publisher/readback faults,CLI parsing/help/output/repeatability.
- [ ] **Step2: RED.** Run `.venv/bin/python -B -m unittest discover -s project -p test_recording_reference_workflow.py -v`.
  Expected missing-feature assertions,not import/fixture errors.
- [ ] **Step3: Implement API/summary.** Validate pins,preflight output,call checker
  once,serialize unchanged JSON/bounded Korean summary/receipt,then publish once.
  Table shows both entry/next/saved state and differing field names;max20audit
  row details with explicit omissions;all data in JSON. Errors preserve work.
- [ ] **Step4: CLI and GREEN.** Six exact flags,usage before imports,full stdout
  handling/restoration;all new tests PASS,old recording+reference regression PASS.
  Document use,diagnostic/audit split,no-overwrite/partial failures and all gates.
- [ ] **Step5: Static/freeze/full gate.** Scoped Ruff/Ty/Codespell/3compiles PASS;
  freeze8files/protect745registered files/config/refs/limited primary metadata.
  Run `.venv/bin/python -B dev.py verify --output <new external directory>`.
  Expected actual2277+new tests,366compiles,98Manifest,unchanged wheel/CORE32 pins.
- [ ] **Step6: Commit/task-done/review.** Only frozen tested scope committed;
  rerun new tests and ledger exact BASE/range/counts. One fresh full-branch reviewer
  gets plan/spec/focus verbatim/rulings/raw evidence. Important fixes RED→GREEN
  plus new full gate;no second reviewer. Retain raw reports and rule all set-asides.

Then normal feature backup,bounded tracking fetch,main fast-forward/fresh focused
smoke/normal push;exact new main/push DEV+Cloud CI and each successful artifact
download once with full Manifest/ledger/source/pins checks. No force/reset/
workflow edits/CI skip/manual rerun/cancel/PR or actual vehicle use.
