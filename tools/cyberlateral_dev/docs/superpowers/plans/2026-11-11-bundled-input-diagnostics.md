# CORE58 Bundled Input Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicitly diagnose one complete canonical synthetic input without separately pairing contexts.

**Architecture:** Existing CORE55 decoder returns the unchanged CORE46 receipt.
The new explicit entry point unpacks that receipt into unchanged CORE49/CORE7.
No new validation,result schema,math,I/O or implicit execution in the codec.

**Tech Stack:** Existing Python3.12/unittest/stdlib,Ruff/Ty/Codespell;no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-11-bundled-input-diagnostics-design.md`

## Global Constraints

- check_serialized_recording_input(raw:object)->SyntheticSequenceCheckV1 in existing diagnostics module.
- Unchanged CORE55 exact bytes1..1048576,2..128records,1..127contexts and CORE46 rules/errors.
- Valid diagnostic runs N-1 steps;invalid input runs0;late execution failure may follow work.
- No context/time/state inference,repair,cache,alternate format,policy args,new result or catch/retry.
- Existing object/CORE52 APIs,codec-only behavior,model math,wheel/deps/workflows unchanged.
- Actualr/T2/scale=null,R_BUDGET unresolved,Static Gate FAIL,actual use NOT_ALLOWED.
- Local feature only;preserve main/config/primary/evidence;push/PR/main/CI NOT_RUN.

## Review Focus

- Bare CORE41 bytes,objects,receipts,or foreign raw types must not bypass complete-input decoding.
- Late metadata/wire/context/count/order/previous-request errors must reject before any model prefix.
- A declared difference must not short-circuit later checks or switch to computed-state rollout.
- Signed zero/subnormals,int64 endpoints,clock labels and explicit auxiliary floats must remain exact.
- Late model failures must preserve existing error semantics and nonzero prior-work uncertainty.

### Task 1: complete-input explicit diagnostic bridge

**Files:** Modify `integration_tools/offline_recording_diagnostics.py`,`README.md`,
`docs/CORE_DEVELOPMENT_BACKLOG_KO.md`. Create
`project/test_bundled_recording_input_diagnostics.py`,
`docs/BUNDLED_INPUT_DIAGNOSTICS_CORE58_KO.md`;this spec and plan are preregistered.

**Interfaces:** Consume CORE55 decode_recording_input(raw:object) and CORE49
check_recorded_synthetic_sequence(recording:object,contexts:object).
Produce check_serialized_recording_input(raw:object)->SyntheticSequenceCheckV1.

- [ ] Write24tests with independent literal declarations/next states and real
  step counters:full3-step MATCH;early DIFFERENT still3steps/declared feed;
  raw type;malformed/bounds;canonical/duplicates;outer permissions;inner
  permissions/gates/links;context wire;late numeric semantics;count/order;
  previous-request role;signed-zero/subnormal/time endpoints;maximum127steps;
  false authority;determinism/nonmutation;repeat changed bytes;wrong-format/
  object/receipt;unexpected decoder error;late ValueError;late RuntimeError;
  codec0 vs explicit3;no policy/override args;old APIs;cold import/no files.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p test_bundled_recording_input_diagnostics.py -v`.
  Expected:24 missing-function assertion failures,zero errors. Commit spec/plan/tests before implementation.
- [ ] Add only the minimal new bridge/import in the named module;run the same tests.
  Expected:24PASS,literal states(6,8,2,5),(7,-8,-2,6),(8,4,2,7);3model steps,
  no simulate. Difference case previous_applied(2,5,4),declared second entry10.
- [ ] Add a complete two-frame guide example and README/backlog entries;execute
  the guide's Python body. Expected:`MATCH 1 2`,one explicit model step.
- [ ] Run `.venv/bin/python -B dev.py verify --output /absolute/NEW-output`.
  Expected:2089tests/346own compiles/static/98Manifest PASS,fixed wheel/CORE32
  pins unchanged. Rerun focused24tests as task-done and commit implementation.
- [ ] Freeze source,one fresh independent whole-branch review;author-regrade all
  findings/declines,one TDD Critical/Important fix pass if needed,ledger minors.
  Seal custody/source7 and evidence with two identical ZIP builds and separate
  complete CRC/Manifest/source/rebuild checks. Preserve the local feature/evidence.
