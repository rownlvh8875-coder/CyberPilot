# R35 Reset Coverage and Main Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Track each task with checkbox (`- [ ]`) steps.

**Goal:** Close the reviewed low-angle reset coverage gap and integrate the fixed
synthetic pack through exact-head CI into main, then prepare a pinned WSL handoff.

**Architecture:** Keep the existing public0.3.0 model/CLI untouched. Swap only the
last two angle fixture samples, update independently derived counter literals,
and make the existing test require the nonzero→0 transition. Use normal GitHub
PR/merge operations and the existing scoped offline workflow.

**Tech Stack:** Existing CPython3.12.13/Linux/binary64, unittest, pinned DEV tools,
Git/gh, standard ZIP/checksums. No new dependency.

**Spec:** ../specs/2026-11-01-r35-regression-pack-design.md; amendment: the user
approved the subsequent four-step proposal (reset-case fix, verification,
PR/CI/main integration, WSL development update). That authorizes normal remote
integration for this stage, superseding the initial stage's no-push restriction.
It does not authorize vehicle activation or direct access to an unconnected laptop.

## Global Constraints

- Base main b6731908be519a051c6ffcf9a18845284a102c20; initial feature head d870b10309215bd3e47572ddebeb08d468c90bd7.
- Original checkout/STEP7 and older branches/environments are preserved.
- No src/integration_tools/tools/API/lock/wheel or workflow changes.
- Normal non-force push to the new feature branch only; no branch deletion,
  admin merge, protection/rule/settings changes, broad CI dispatch, or credentials edits.
- Draft PR plus `[skip ci]` feature commits and explicit offline workflow dispatch
  avoid generic openpilot PR builds. Read actual trigger configuration first.
- Merge only the exact reviewed head after PASS CI/artifact verification, no
  outstanding change requests, unchanged expected base, and clean normal merge.
- R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/scale=null,
  Candidate/Runtime NO_GO, SOURCE_SCHEMA_UNQUALIFIED6000, F70UH/V/F71 NOT_ALLOWED.
- No actual vehicle inputs, F61/calculator/r/dt/Controller/vehicle Runtime/CAN.
- WSL outcome is NOT_RUN here: provide a checksum-pinned kit and local prompt.

## Review Focus

- A below85 row with counter0 is not evidence of clearing a nonzero counter.
- Counter/flag expectations change, but all38 command outputs and case counts stay fixed.
- CI must bind to the final head, not a previous feature/merge artifact.
- Merge must not bypass protection, delete branches, or race silently with base changes.
- Portable sharing subsets cannot replace complete saved batches for R34.

### Task 1: Close reset coverage

Files: project/test_regression_pack.py; examples/r35/angle_counter_v1.json;
reference/r35_regression_expected_v1.json; docs/SYNTHETIC_REGRESSION_PACK_R35_KO.md.
Consumes: unchanged scenario parser/engine and literal reference.
Produces: same6 valid/3 rejected fixtures and38 samples, with last angle row counter1→0.

- [ ] Make existing test require final before/after counter and condition [1,0,false].
- [ ] Run targeted test; expect assertion RED [0,1,true] vs [1,0,false].
- [ ] Swap final angle samples to85 then-84.5. Counter/flag sequence becomes
  (89,true),(90,false),(0,false),(1,true),(0,true); final counter0. Commands unchanged.
- [ ] Update hand-derived reference/derivation, run all14 pack tests GREEN.
- [ ] In-memory mutation retaining a nonzero counter below85 must fail the test;
  restore and verify GREEN. Run full dev gate and explicit two pack reproductions.
- [ ] Commit with `[skip ci]`; independent final review before publication.

### Task 2: Exact-head PR and CI

Consumes: Task1 exact commit, clean worktree, fresh gate/review evidence.
Produces: one draft PR and one successful scoped workflow artifact for that head.

- [ ] Recheck remote main, feature absence/head, settings/rules, workflow bytes.
- [ ] Non-force push feature/cyberlateral-regression-pack; create draft PR; attach URL.
- [ ] Dispatch only .github/workflows/cyberlateral-dev.yaml on exact feature ref.
- [ ] Wait via bounded observations, verify run head/event, success, artifact CRC,
  all manifests,570 tests/174compiles/static checks and unchanged sealed wheel/gates.

### Task 3: Normal main integration

Consumes: Task2 PASS, exact head/base, no change requests, normal clean merge.
Produces: actual main merge SHA/tree/parents and successful main offline CI.

- [ ] Verify prospective merge source bytes, head/base, normal merge availability;
  mark PR ready and merge with expected head SHA (no admin/force/delete).
- [ ] Confirm actual merge parents/tree, PR closed/merged, feature preserved.
- [ ] Verify automatic scoped main push CI and its complete artifact.

### Task 4: Pinned development handoff

Consumes: verified merged main SHA, exact Git source bytes, complete fixed batches.
Produces: new main WSL kit, usage/local prompt, source/expected/output manifests.

- [ ] Export registered source only to a fresh external folder, new venv/cache.
- [ ] Rehearse full gate and R35 batch/compare twice, verify every manifest/byte.
- [ ] Build deterministic ZIP twice, verify CRC/manifest/source custody and SHA.
- [ ] Preserve older environments; state cloud rehearsal PASS, notebook NOT_RUN.
