# CORE55 Recording Input Codec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve complete explicit synthetic recording inputs as bounded canonical bytes.

**Architecture:** Embed unchanged CORE41 canonical UTF8 as text,encode auxiliary
floats as canonical hex,and delegate all semantic compatibility to CORE46.
Return its existing receipt;never call a diagnostic/model during codec operations.

**Tech Stack:** Existing Python3.12/unittest/stdlib JSON,Ruff/Ty/Codespell;no dependencies.

**Spec:** `docs/superpowers/specs/2026-11-11-recording-input-codec-design.md`

## Global Constraints

- Exact bytes,1..1048576bytes;unchanged CORE41 recording2..128frames.
- Explicit context list1..127 on wire,exact tuple for encoder;CORE46 count/order/rules.
- Canonical finite float.hex strings at most32characters;signed zero preserved.
- Fixed outer metadata/false permissions;no inference,fallback,model/reference or I/O.
- Structural error RECORDING_INPUT_SERIALIZATION;semantic CORE46 codes unchanged.
- No existing source contracts/model/F61/rate/wheel/workflow changes.
- Actual r/T2/scale=null;R_BUDGET unresolved;Static Gate FAIL;actual use NOT_ALLOWED.
- Local feature only;retain prior evidence/primary/refs/config;push/PR/main/CI NOT_RUN.

## Review Focus

- Wrong raw types or noncanonical JSON must reject before semantic processing.
- Tampered metadata,inner authority or extra fields cannot grant permission.
- Late invalid contexts/count/index and previous-request mismatch must reject wholly.
- Signed zero/subnormal request words,int64 endpoints and auxiliary floats stay exact.
- Codec-only calls and cold import must execute no model/simulate/reference work.

### Task 1: canonical recording-input codec

**Files:** Create `integration_tools/offline_recording_input_codec.py`,
`project/test_offline_recording_input_codec.py`,
`docs/RECORDING_INPUT_CODEC_CORE55_KO.md`;modify `README.md` and
`docs/CORE_DEVELOPMENT_BACKLOG_KO.md`.

**Interfaces:** Consume existing CORE41 encode/decode and CORE46 preflight;
produce encode_recording_input(recording:object,contexts:object)->bytes and
decode_recording_input(raw:object)->SyntheticRecordingInputPreflightV1.

- [ ] Write literal independent wire/context expectations and real-step counters.
  Test all Review Focus cases,canonical/shape/bound errors,CORE46 codes,count/order,
  exact metadata false flags,max128records,repeat validation and explicit diagnostics.
- [ ] Run `.venv/bin/python -B -m unittest discover -s project -p 'test_offline_recording_input_codec.py' -v`.
  Expected:missing-module assertion FAIL,zero errors. Commit preregistration.
- [ ] Implement only this codec and unchanged dependency calls;rerun same command.
  Expected:all new tests PASS,codec step/simulate0;explicit diagnostics3steps and
  literal states `(6,8,2,5)`, `(7,-8,-2,6)`, `(8,4,2,7)` unchanged.
- [ ] Add a complete two-frame guide example;run its Python body with PYTHONPATH=src.
  Expected:`INPUTS_COMPATIBLE 2 1`,no diagnostic step;document optional explicit run.
- [ ] Run `.venv/bin/python -B dev.py verify --output /absolute/NEW-output`.
  Expected:whole tests/static checks/own compiles PASS,98Manifest and fixed pins
  unchanged. Re-run focused task tests and commit the completed task.
- [ ] Freeze source,one fresh independent final review;handle Critical/Important
  through one TDD fix pass if needed. Seal source/custody/evidence with two ZIP builds
  and separate complete CRC/Manifest/source/rebuild checks. Completion is ledgered.
