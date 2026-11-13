# Declared Diagnostics Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Check saved synthetic diagnostics against existing independent selected-source arithmetic.

**Architecture:** Parent reuses capture and complete admission, then sends declarations
to an isolated worker. Worker reuses existing NormalizedReference with declared state
per transition; parent validates its closed response and compares a full diagnostic projection.

**Tech Stack:** Python3.12.13, existing numpy2.5.3, unittest and existing static tools.

**Spec:** `../specs/2026-11-13-declared-reference-design.md`

## Global Constraints

- Base ebb3c2a00011f73b6ef1853678baaa30a67e11ea; existing linked worktree/feature branch.
- No existing model/wheel/helper/schema/dependency edits; only two documentation updates.
- Shared admission is explicit; model.step0, independent worker referenceN-1 for Nframes.
- Independent declared feed, not computed rollout; exact canonical comparison/no tolerance.
- stdin/accepted worker stdout1048576bytes, timeout60s; public output2097152bytes.
- Linux/CPython3.12.13/binary64/numpy2.5.3, no actual inputs/F61/r/dt/vehicle use.
- R_BUDGET=UNRESOLVED,Static Gate=FAIL,actual r/T2/scale=null; actual authority false.

## Review Focus

- Shared admission must not be presented as an independent validator or whole-controller oracle.
- Declared DIFFERENT must retain declared state feed and may still yield reference audit0.
- Worker/result/source failures must not fall back to public model or a successful empty comparison.
- Missing/extra rows, boolean integer impostors and fake helper/runtime fields must reject or differ correctly.
- Replaced captured paths, stdout failures and timeout results must preserve identity/work distinctions.

---

### Task 1: Complete declared reference audit

**Files** (relative to tools/cyberlateral_dev):
- Create `integration_tools/recording_diagnostics_reference.py` (capture/admission/wire/validation/comparison).
- Create `project/recording_diagnostics_reference.py` (primitive wire→existing independent reference).
- Create `tools/recording_diagnostics_reference_worker.py` (private guarded worker).
- Create `tools/recording_diagnostics_reference.py` (public opt-in CLI).
- Test `project/test_recording_diagnostics_reference.py`.
- Create `docs/RECORDING_DIAGNOSTICS_REFERENCE_CORE69_KO.md`.
- Modify `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md`.
- This plan and its spec are also scoped; ten paths total.

**Interfaces:** Consumes unchanged CORE66 inspector/CORE61 capture/CORE55 decoder,
R38 source identity, NormalizedReference and canonical parser. Produces
`check_recording_reference(Path,str,Path,str)->dict`,
`reference_declared_states(object)->dict` and the two CLIs with the exact spec wire.

- [ ] **Step 1: Establish baseline and write failing behavior tests.**
  Run old saved/audit/R38 tests once. Use independent existing three-row fixture:
  next states(6,8,2,5),(7,-8,-2,6),(8,4,2,7). Expect reference audit0,
  model.step0/reference3 and exact helper counts1/2/0/3/3/0/6. True saved DIFFERENT
  uses entry applied10/5 and reference outputs5/4. Forge final computed202 and
  require audit1; simulate a shared public-model fault and require reference detection.
- [ ] **Step 2: Observe RED.**
  Run `.venv/bin/python -B -m unittest discover -s project -p test_recording_diagnostics_reference.py -v`.
  Expected missing-feature assertions,not import/fixture errors.
- [ ] **Step 3: Implement guarded independent worker.**
  Validate complete canonical primitive wire before helper initialization; use direct
  declared states, independent bit quantizer and pinned selected helper. Add real
  worker tests for no public-model imports, boundaries and closed typed output.
- [ ] **Step 4: Implement parent and CLI.**
  Both pins before paths, one capture each, full preflight before launch; source
  identity before/after, strict worker validation, full projection comparison.
  Test malformed/later input, source/worker/result errors, row-count directions,
  opt-in flags/help, repeated-process determinism, output prefixes and restored globals.
- [ ] **Step 5: Verify and document.**
  New tests and old recording/R38 regression must pass. Scoped Ruff/Ty/Codespell/
  compile PASS before full gate. Explain selected-state scope, shared admission,
  work counts and diagnostic-status/audit-status split in Korean guide/README/backlog.
- [ ] **Step 6: Freeze and run whole gate.**
  Freeze ten paths and preserve all other registered bytes/modes/refs/config/limited
  primary metadata. Run `.venv/bin/python -B dev.py verify --output <new outside path>`.
  Expected all actual tests/static/363compiles/wheel/reference/98Manifest PASS;
  test count is2243 plus actual new tests. Preserve all failures and actual counts.
- [ ] **Step 7: Commit and task-done.**
  Commit only tested scoped bytes; rerun the new unittest command and record BASE,
  exact commit and result in ledger. Request one fresh complete-branch review with
  this Review Focus verbatim and all rulings. Important fixes require RED→GREEN and
  a new green full gate; no speculative second reviewer.

Then normal feature backup, bounded explicit tracking fetch if needed, main
fast-forward/normal push under existing authorization, exact main/push DEV/Cloud
CI identities and one artifact download per successful role. Never alter workflow
security, force-push, skip checks or relabel old queued runs as new successes.
