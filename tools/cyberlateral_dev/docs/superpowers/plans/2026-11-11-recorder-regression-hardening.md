# CORE42 Recorder Regression Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close CORE41 review M1/M2 with regression tests, without changing recorder behavior.

**Architecture:** Extend the current unittest file and reuse its literal fixtures. Run three isolated faulty copies as negative controls; the real library stays byte-identical. Finish with the whole DEV gate and independent review.

**Tech Stack:** Existing CPython3.12.13, stdlib unittest/dataclasses, pinned DEV checks; no dependencies.

**Spec:** ../specs/2026-11-11-offline-call-recorder-design.md; CORE41 independent review M1 requires side-effecting request/frame subclass tests before attribute reads; M2 requires both finish/begin after completion failures and failures after an exportable two-record prefix.

## Global Constraints

- Base2cdbbb5a764bb67d2439a86e3fa58a1f9e150cca; continue local feat/core41-offline-call-recorder.
- Only project/test_offline_call_recorder.py, this plan and an append to docs/OFFLINE_CALL_RECORDER_CORE41_KO.md may change.
- No library/codec/demo/model/wheel/API/fixture/production/config changes; no push/main merge/remote CI.
- Only explicit synthetic carriers; no actual data, capture, Controller/Runtime/CAN/F61 or actual dt/r calculations.
- Existing caller scopes, capacity2..128, codec limit262144, all permission false fields and unresolved actual gates remain unchanged.
- Negative controls live outside the repository, use copied validation-only modules and are never original-source recovery or production fixes.
- Existing correct behavior passes; RED means each new test detects its specified faulty copy, not that the real recorder had a defect.

## Review Focus

- Subclass construction must not itself trigger the attribute probe; the input read is what the test detects.
- Request and frame checks must reject subclasses before any attribute access with the exact public error code.
- Every completion error must keep both finish and begin blocked, including existing zero/one-record cases.
- A failed third completion after two valid records must not export or resume a valid prefix across type/request/settings/state/counter errors.
- Negative controls must load their own copied module, and their edits must not reach the original checkout or original F61 code.

---

### Task1: Close the two recorder regression gaps

**Files:** Modify project/test_offline_call_recorder.py; append docs/OFFLINE_CALL_RECORDER_CORE41_KO.md.

**Interfaces:** Consume existing RecorderTests.reject/complete_two/frames and SyntheticCallRecorderV1 API unchanged. Produce test_request_subclasses_reject_before_side_effecting_reads, test_frame_subclasses_reject_before_side_effecting_reads and test_failed_third_completion_blocks_export_and_reentry; a test-only reject_failed helper checks original fixed code followed by finish/begin RECORDER_FAILED.

- [ ] Step1: Verify the clean current tree and focused baseline; preserve source/ref identities.
  Run: `.venv/bin/python -B -m unittest discover -s project -p 'test_offline*' -v`.
  Expected:36 tests PASS and clean HEAD/base; prior sealed evidence verifies.
- [ ] Step2: Prepare isolated request-prevalidation, frame-prevalidation and conditional-third-completion-poison mutants, each one semantic change. Run copied pre-change RecorderTests against each.
  Expected:19 old tests PASS for each mutant; records remain declarations and no model runs.
- [ ] Step3: Write the three named new tests and reject_failed; update existing completion-error cases to check both terminal operations. Use separate subclasses whose __getattribute__ raises AssertionError, literal third call sequence9/time-7/entry4/saved6/counter5->6 and explicit error cases.
- [ ] Step4: Run each new relevant test on its isolated mutant.
  Expected:one relevant new test FAILS/0 errors for each of the three mutants; then run unmodified recorder.
  Run: `.venv/bin/python -B -m unittest discover -s project -p 'test_offline*' -v`.
  Expected:39 tests PASS (34 CORE41/42 plus5 existing offline tests), library unchanged.
- [ ] Step5: Run the whole gate and exact fixed demo twice.
  Run: `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`.
  Expected:1958 tests,338 compiles,static checks PASS; unchanged wheel/CORE32 pins/demo bytes and closed actual-use gates.
- [ ] Step6: Commit the three allowed paths locally; verify all other source/ref identities; independent whole-delta review checks M1/M2 closure and the negative controls. Keep branch and external evidence, no remote writes.

## Self-review and execution

One coherent tests-only task; no shared inter-task interfaces. The original design
already specifies this behavior, so there is no new functional design or API.
Detailed execution is delegated by the user. A persistent external ledger records
commands/results because this cloud provider did not expose the skill helper
scripts. No failing original behavior or production RED-to-GREEN fix is claimed.
