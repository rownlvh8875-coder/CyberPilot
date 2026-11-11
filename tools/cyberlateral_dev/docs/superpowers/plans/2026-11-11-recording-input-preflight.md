# CORE46 Recording Input Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate completed synthetic recordings with explicit CORE5 contexts without executing a model.

**Architecture:** Revalidate the exact CORE41 result, then reuse CORE5 input preparation
for every adjacent frame. Return a non-executable frozen compatibility receipt;
never repair declarations, infer metadata or grant model/vehicle permissions.

**Tech Stack:** Existing Python3.12.13, stdlib dataclasses/unittest, existing DEV environment.

**Spec:** `docs/superpowers/specs/2026-11-11-recording-input-preflight-design.md`

## Global Constraints

- Preserve CORE3~7/CORE41/model/wheel/fixtures/CI/dependencies bytes.
- Exact recording; exact context tuple of records-1; recording2..128.
- Every context is explicit; model indices consecutive after full CORE5 validation.
- No model step/reference/F61/Controller/Runtime/CAN/I/O or dt/r/seconds calculation.
- Numeric validation NONZERO_NOT_AGGREGATED, all execution/actual-use flags false.
- Actual r/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL.
- One isolated feature branch, main and host-owned worktrees preserved; no push/PR/CI this implementation stage.

## Review Focus

- Hostile recording/context/container subclasses: reject before reads/iteration.
- Last invalid context and earlier model-order gap: validate whole input first, no success prefix.
- Forged fixed flags or changed linked frame: revalidate recording, not only class name.
- Signed-zero/subnormal/int64 endpoint metadata: preserve exact declarations, never calculate dt.
- Unknown validation exception: propagate rather than convert to compatibility or expose wrapped input.

## Task 1: Typed recording input preflight and honest documentation

**Files:**
- Create: `integration_tools/offline_recording_preflight.py`
- Test: `project/test_offline_recording_preflight.py`
- Create: `docs/RECORDING_INPUT_PREFLIGHT_CORE46_KO.md`
- Modify: `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`

**Interfaces:**
- Consumes CORE41 `_validate_finished(recording)` and CORE5 `prepare_model_input(previous,current,context)`.
- Produces `RecordingPreflightError`, `SyntheticRecordingInputPreflightV1(recording,contexts)` and `preflight_recording_input(recording: object, contexts: object)` per spec.

- [x] Step1: Add real four-frame fixtures and failing tests. Literal requests be800000/3f000000/bf000000/3e800000; previous integer requests -4/8/-8, model indices5/6/7 and capture sequences7/8/9/10.
- [x] Step2: Run `.venv/bin/python -B -m unittest discover -s project -p 'test_offline_recording_preflight.py' -v`; expect assertion failures for missing CORE46 module, not import errors. Preserve RED ledger and commit spec/plan/tests only.
- [x] Step3: Implement the small module with exact error order in the spec; no new decoder or arithmetic algorithm. Derive counts only after all checks succeed.
- [x] Step4: Run focused tests; literal success counts4/3, max128/127, wrong previous request→INPUT:0:MODEL_PREVIOUS_REQUEST_MISMATCH, final bad driver→INPUT:2:MODEL_DRIVER, model-order gap→MODEL_ORDER:1.
- [x] Step5: Document compatibility vs saved-output parity, false permissions and nonzero numeric validation; update README/backlog without rewriting historical evidence.
- [x] Step6: Run baseline-related tests and full `.venv/bin/python -B dev.py verify --output /absolute/NEW-output`, Ruff/Ty/Codespell/compile, whole Manifest, unchanged wheel and CORE32 pins. Confirm fresh source counts rather than reusing old1958/338 literals.
- [x] Step7: Commit the verified implementation/documentation and record task completion with its focused test command.

## Post-task finalization

These finalization boxes describe the implementation commit's checkpoint; the external ledger records subsequent review/seal completion without a post-review documentation-only commit.

- [ ] Obtain the native workflow's independent whole-branch review on the frozen commit. Resolve important findings in one TDD fix pass with a green whole suite.
- [ ] Verify seven-path scope, unchanged main/other refs/704 out-of-scope baseline files/primary metadata; seal external evidence deterministically. Keep branch/worktree; report next publication stage without doing it.

## Execution selection and self-review

Native execution is the author's choice under the user's explicit delegation and
request to continue without repeated approvals. One tightly coupled module does
not need multiple implementers. Spec/interface/error/permission requirements map
to Task1; each Review Focus has focused tests. No additional product requirement
or individually approved design is claimed. Independent final review is still required.
