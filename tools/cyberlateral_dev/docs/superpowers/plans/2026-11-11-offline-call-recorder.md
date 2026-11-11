# CORE41 Offline Call Recorder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bounded in-memory synthetic call transactions and exact portable recording, without real capture or calculations.

**Architecture:** Reuse frozen CORE3/4 carriers and their validations. Separate recorder lifecycle, strict codec and fixed no-input demo. Keep original files unchanged except append-only README.

**Tech Stack:** Existing CPython 3.12.13, stdlib, unittest, pinned Ruff/Ty/Codespell. No new dependency.

**Spec:** docs/superpowers/specs/2026-11-11-offline-call-recorder-design.md (copied unchanged from external DESIGN.md before Task1).

## Global Constraints

- New branch feat/core41-offline-call-recorder from ba6319418ce4fa36e336eef60259fcf748a6094a; no push or main merge.
- capacity exact built-in int 2..128; codec exact bytes <=262144.
- Fixed contract CORE41_COUNTERFACTUAL_CALL_RECORDING_V1 and COUNTERFACTUAL_RECORDING_ONLY; no origin/vehicle/F61/model authority.
- Request binary32 word bytes preserved. Exact integer ns/sequence/generation strings. No float/dt/r calculations.
- Existing source, wheel0.3.0 and fixtures unchanged; only README may gain an append.
- All malformed open-recorder operations poison it; no successful prefix, overwrite or recovery.
- No actual input/capture, Controller/Runtime/CAN/F61 invocation, policy number, dependencies, remote writes.
- User has delegated detailed choices and uninterrupted execution; no renewed design approval is represented.

## Review Focus

- Caller objects/subclasses with side-effecting attributes must reject before reads; test first request and completion.
- First and directly constructed recordings must validate, not only subsequent pairs; test malformed first/direct records.
- Failed completion must not leak a usable successful prefix; test finish and begin after each failure.
- Lossy JS-sized integer/float conversion must not enter the portable format; test literal uint64/int64 boundaries.
- Export/import must not broaden authority via added fields/flags or a relabeled scope; test modified serialized metadata and fresh isolated imports.

---

### Task 1: Synthetic call recorder, portable codec and fixed demo

**Files:**
- Create: integration_tools/offline_call_recorder.py
- Create: integration_tools/offline_recording_codec.py
- Create: tools/offline_call_recorder_demo.py
- Test: project/test_offline_call_recorder.py
- Test: project/test_offline_recording_codec.py
- Test: project/test_offline_call_recorder_demo.py
- Create: docs/OFFLINE_CALL_RECORDER_CORE41_KO.md
- Modify: README.md (append only)

**Interfaces:**
- Consumes CORE3 SyntheticRequestSnapshotV1 and CORE4 SyntheticLimiterSnapshotV1, single validators and prepare_limiter_pair.
- Produces SyntheticCallRecorderV1(capacity), begin(request), complete(frame), abort(), finish(); FinishedSyntheticRecordingV1(records); RecorderError.code.
- Produces encode_recording(recording)->bytes and decode_recording(raw)->FinishedSyntheticRecordingV1.
- Produces fixed demonstration stdout with exact signed-zero/subnormal word preservation and -9/-8 ns strings.

- [ ] Step1: Write lifecycle, codec and CLI failing tests with independent literal expected roles, exact errors and unsupported scopes.
  Run: `.venv/bin/python -B -m unittest discover -s project -p 'test_offline*' -v`.
  Expected: FAIL because new recorder/codec/demo files are absent; no unexpected test setup errors.
- [ ] Step2: Implement recorder and immutable result with CORE3/4 validation reuse, terminal poison/abort/closed states and exact resource bound.
- [ ] Step3: Implement strict canonical codec with decimal-token and hex preservation; implement no-input isolated demo. Add Korean usage and README append.
- [ ] Step4: Run targeted tests and existing CORE3/4 tests.
  Run: `.venv/bin/python -B -m unittest discover -s project -p 'test_offline*' -v`.
  Expected: all new tests PASS. Run existing test_request_snapshot/test_limiter_snapshot similarly; both PASS.
- [ ] Step5: Run full gate and read every result.
  Run: `.venv/bin/python -B dev.py verify --output EXTERNAL/final-verify`.
  Expected: inherited1924 plus actual new test count PASS; Ruff/Ty/Codespell PASS, own compiles332+6, same wheel SHA and CORE32 pins.
- [ ] Step6: Run demo twice from an external cwd using `.venv/bin/python -I -B tools/offline_call_recorder_demo.py` absolute paths; compare bytes and decode; all actual gates remain closed.
  Expected: byte-identical canonical two-call record; no model/helper/F61/r/dt execution by recorder/demo.
- [ ] Step7: Commit only feature/docs/tests on local branch; record exact commands/results, code/fixture/ref custody and fresh whole-branch review.
  Expected: clean local branch, main/origin-main unchanged; no remote writes.

## Plan self-review and execution record

One coherent task, no inter-task interface conflicts. All five Review Focus
conditions are exercised in Task1 tests. Skill helper resources were unavailable
through skills.read; preserve the same RED/GREEN/final-review evidence in the
external progress ledger instead of pretending the task scripts ran. Keep that
evidence, since deleting it is not required by the user and would lose useful logs.
