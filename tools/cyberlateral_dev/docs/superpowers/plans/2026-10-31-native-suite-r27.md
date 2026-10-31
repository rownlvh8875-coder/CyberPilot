# Fixed Native Suite R27 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One explicit fixed R19–R26 command with strict artifact validation and bounded reporting.
**Architecture:** Immutable eight-profile registry; pure stage validator; separate
parent orchestrator/reporter calling unchanged qualifiers. Staged no-overwrite
publication, summary last. No default/native-domain/API change.
**Tech Stack:** CPython3.12.13/stdlib/unittest, same separate pinned pycapnp2.1.0/public0.3.0 environment.
**Spec:** ../../NATIVE_SUITE_R27.md

## Global Constraints

- Fixed orderedR19–R26 only; commit retained identity registry/fixtures before new suite execution.
- Existing qualifier/worker/reference/model/API/lock/public46646-byte27-entry wheel/default pure CI unchanged.
- Frozen77 and original10 source/status guards unchanged. No actual/F61/Controller/Runtime/CAN/r/dt/deployment/main merge.
- All vehicle/r/static gates remain closed; native GitHub CI NOT_RUN.
- Delegated existing isolated feature/inline; one fresh final review, [skip ci]
  commits/manual exact-head pure workflow; preserve evidence/worktree.

## Review Focus

- Identical but incomplete/forged child outputs must not pass registry, manifest, source or numeric checks.
- Missing/mixed modes or stages and false zero/boolean counts must not publish suite PASS.
- Existing outputs, late collisions and publication failures must never overwrite or leave a successful summary.
- Receipt/environment differences must not contaminate portable summary equality or imply authentication.
- Full suite PASS must not open default native CI, generic readers, F61, policy or vehicle gates.

### Task 1: Fixed registry and pure stage validator

**Files:** reference/r27_suite_profiles_v1.json,r27_stage_records_v1.json;
native_qualification/suite_profiles.py,suite_validation.py;
project/suite_fixture.py,test_suite_validation.py.
**Interfaces:** load_profiles()->tuple[Profile,...],get_profile(stage_id)->Profile;
validate_stage(directory:Path,stage_id:str)->dict with spec's nine row fields.

- [ ] Extract only exact retained JSON records and identities from verified R26
  archive, using apply_patch; commit registry/fixtures/spec/plan before execution.
- [ ] Write12 validator tests:all8 full records+literal counts/hashes; registry
  tamper/freshness; unknown stage; bad/duplicate/path manifest; missing/extra or
  symlink files; noncanonical JSON; mutated observation; summary status/reference/
  counts/gates/source/extra-field forgery; delegated numerical rejection;
  oversized/nonfile data; data-only import/no native/model calls.
  Run unittest discover -s project -p test_suite_validation.py -v.
  Expected:RED missing validator. Implement minimal registry/validator; GREEN12.
- [ ] Full dev.py verify --output out/r27-stage-validation; explicit native static
  checks and20 own native in-memory compilations. Expected:398 tests/133 pure
  compilations/frozen77/public wheel unchanged PASS. Commit and ledger before Task2.

### Task 2: Complete explicit suite runner and report

**Files:** native_qualification/suite.py,suite_report.py,test_suite_observations.py;
project/test_suite_runner.py; README/spec/results/plan.
**Interfaces:** consume Task1's fixed profiles and validated rows;
run_suite(python,wheel,package_wheel,output,*,enabled=False)->dict;
build_summary(rows)->dict,render_report(summary)->str; CLI --fixed-native-suite.

- [ ] Write12 runner/report tests:mandatory opt-in/bool/output/wheel/parent
  preflight;8 exact mode calls and report454/16; stage failure abort/no final;
  returned-summary/artifact contradiction; bad child metadata; missing/duplicate/
  reordered report rows and false counts; deterministic pure results/no native
  import; CLI help/invalid flags; report capability boundaries; late output
  collision; link failure/summary-last/no overwrite;43-entry manifest verification.
  Run unittest discover -s project -p test_suite_runner.py -v.
  Expected:RED missing suite. Implement minimal runner/reporter; GREEN12.
- [ ] Full dev.py verify --output out/r27-primary, native Ruff/Ty/Codespell/23
  compilations. Expected:410 tests/134 pure compilations/frozen77/sealed wheel PASS.
- [ ] Fresh native env executes suite (8 stages/16 workers/454 model calls),
  independent7 suite observation checks and all53 existing individual output
  assertions; verify root43 and8 inner4-entry manifests. Expected:all PASS.
- [ ] Commit; archived source+workflow/new dev/native env full gate and suite.
  Expected:SUITE_SUMMARY/report and all8 observations/summaries byte-identical;
  receipts/manifests preserved without equality/OS-authentication claim.
- [ ] One fresh whole-branch review; one blocker RED/GREEN fix pass only. Regrade
  all findings and rule on every declined area, ledger all decisions/minors.
- [ ] Docs-only final commit; exact-head pure CI/Draft update preserving latest
  body; download94 hashes; original guards; Korean report and deterministic
  two-build ZIP/CRC/fresh root+three pure94+suite manifests PASS.

Self-review: Task1 validated row fields feed Task2 unchanged; Task2's report
coverage/typed-count checks defend the second consumer boundary. All five Review
Focus cases have named owner tests. No shared-interface conflict found.
