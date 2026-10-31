# Synthetic Message Handoff Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify split/resume and round-robin state continuity through the fixed synthetic message boundary.

**Architecture:** Reuse R15's exact owned advance in a separate closed DEV runner. Independently validate lifecycle traces against the embedded, frozen-authority R15 trace; integrate two installed runs into the existing verifier.

**Tech Stack:** CPython 3.12.13, stdlib, unchanged cyberlateral_dev 0.3.0, existing pinned DEV tools.

**Spec:** MESSAGE_HANDOFF_LIFECYCLE_R16_DESIGN.md

## Global Constraints

- Seven fixed fixtures/112 samples,105 interior cuts,9010 model steps/extractions per lifecycle process,0 prefix validation steps.
- R15 installed RESULTS unchanged; R14/src/reference/goldens/dependencies/workflows unchanged.
- No arbitrary input/native/schema/Controller/Runtime/CAN/F61/actual vehicle/r/dt/activation/merge.
- Actual r/T2/scale=null; R_BUDGET UNRESOLVED, Static Gate FAIL, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.
- NEW output only, canonical JSON, result published last, [skip ci], existing Draft/feature publication only.

## Review Focus

- Empty/end cuts or duplicated/reordered certificates must not masquerade as105 valid splits: tamper test pins exact cut coverage.
- A resumed prior-request-only alteration must not pass because the integer output happens to match: full frame/prepared comparison test.
- Foreign stream state during interleaving must not be hidden behind final-state/hash-only comparison: event-by-event tamper and isolation fault tests.
- Input catalog changed between baseline and lifecycle work must fail before any additional model step: second-call catalog drift test.
- Signed zero, history-scale index1 seed and counter-heavy fault-cycle must retain their existing semantics: full golden, cut and event comparisons.

## Task 1: Closed lifecycle producer, acceptance gate and installed integration

**Files:** Create integration_tools/handoff_lifecycle.py, lifecycle_validation.py, project/test_handoff_lifecycle.py. Modify message_handoff.py (extract one shared advance), handoff_validation.py (extract record-only validation), verify.py, README.md. Keep design/plan with component docs.

**Interfaces:** Consume R15 run_handoff_chain()->dict, _encode(sample,state,sequence), frozen catalog and source/result hashes. Produce _advance_owned(sample,state,sequence)->(frame,prepared,output); validate_handoff_record(record:dict)->None; run_lifecycle()->dict; _chunk(samples,state,sequence)->dict; lifecycle_pair_summary(first:Path,second:Path)->dict; verify_installed_lifecycle(root:Path,python:Path,output:Path,cwd:Path)->dict. CLI --output NEW only.

- [ ] Write RED tests: test_all_splits_and_interleaved_full_trace (7/112/105/9010/0, all exact result hashes, hand-checked ramp[2,4,6], inactive[2,0,0,2],history95/19.0); test_second_catalog_drift_before_lifecycle_work (only baseline112 calls); test_resumed_state_fault_rejected (real prefix with altered prior-request, mismatch even if command unchanged); test_interleaved_fault_rejected (real events with wrong owned state); test_complete_trace_tampering (all exact cut/event coverage, states/hashes/baseline/gates/env/seed/signed-zero, both checksum-rewritten pairs); test_existing_outputs_and_failed_publication; test_isolated_installed_pair; test_repeat_has_no_hidden_state.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p test_handoff_lifecycle.py -v`. Expected:8 missing-planned-feature assertion failures before code, not import errors.
- [ ] Implement the interfaces using one new model step per extracted sample, complete baseline/cut/event checks, no fallback or prefix simulation. Keep R15 payload unchanged.
- [ ] Repeat targeted tests. Expected:8 PASS. Run full `uv run --locked python -B dev.py verify --output out/r16-run-1`. Expected:all existing224+8=232 PASS, Ruff/Ty/Codespell/owncompile/imported77/unchanged wheel/old pairs/new lifecycle pair PASS.
- [ ] Commit only planned component files with [skip ci]. Run full verifier in fresh minimal git archive including unchanged workflow and a fresh DEV venv. Expected:232 PASS and deterministic payload/wheel equality; not whole Manifest identity.
- [ ] Request one fresh whole-branch review with spec/plan/ledger/evidence. Resolve important findings in one RED/GREEN fix pass; ledger rulings/minors. Expected:no unresolved Critical/Important.
- [ ] Push existing feature branch, dispatch only cyberlateral-dev.yaml, verify exact HEAD232 PASS and all artifact checksum entries, update existing Draft PR. Recheck original10 source hashes and clean unchanged roots. Expected:Draft/open/unmerged, no actual activation. Retain external audit/receipt, report actual counts/limitations.
