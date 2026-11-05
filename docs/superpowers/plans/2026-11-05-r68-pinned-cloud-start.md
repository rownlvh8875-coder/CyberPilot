# R68 Pinned Cloud Start Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans;
> owner delegated inline execution without repeated design/permission questions.

**Goal:** Recover the frozen R67 DEV/tools/data in one read-only cloud command.

**Architecture:** A bounded supplementary recovery helper validates Git provenance
and saved bundles. A small orchestration engine composes existing DEV restore,
HF fetch and passive comparison APIs and writes a final completion marker last.

**Tech Stack:** CPython3.12.13, stdlib, existing locked app/SDK2.4.0 and cloud tests.

**Spec:** docs/superpowers/specs/2026-11-05-r68-pinned-cloud-start-design.md

## Global Constraints

- Base f562377abefdc5796f54b4f98c0c3ded9a5a4a3e; preserve linked worktree and all evidence.
- Frozen R67_MAIN_V1 pins exactly as spec; original archive source != R68 tool revision.
- CLI profile/run, no profile/latest/env override, read-only existing private HF only.
- Only new external output, no overwrite/repair/delete/login/global install/Python download.
- Source/SAVED errors, worker metadata/types/gates, failure stage and final-marker rules as spec.
- No old helpers/app/locks/workflows/old guides edits, main merge/push/PR/CI/HF publication.
- R41 explicit synthetic work NONZERO; passive comparison no new browser/model/F61/vehicle.
- Actual r/T2/scale null, R_BUDGET UNRESOLVED, Static Gate FAIL, activation NOT_ALLOWED.

## Review Focus

- Partial DEV success or SDK/fetch failure must never produce root START_RESULT or a misleading whole-operation PASS.
- Consistently resealed source/identity/SAVED substitution must not bypass Git and original receipt binding.
- Dirty Git checkout, existing/symlinked outputs or interrupted runs must preserve user bytes and partial evidence, with no fallback or cleanup.
- A valid saved DIFFERENT or identical recorded FAIL is recovery success, not a new screen/vehicle PASS or a fabricated r policy.
- Frozen pins/private namespace/read-only workers must remain exact; help/profile and passive readers must not import optional app/browser/SDK packages.

### Task 1: Exact supplementary tooling recovery

**Files:** create tools/cyberlateral_cloud/tooling_restore.py and tests/test_tooling_restore.py.

**Interfaces:** consumes existing archive_payloads/git/reader APIs; produces
recover_tooling(repo: Path, commit: str, archive: Path, digest: str, destination: Path)->dict
with exact source identity and original saved receipts for Task2.

- [ ] Step 1: Baseline ci_verify.py expected179tests/25compiles/staticPASS; commit spec/plan.
- [ ] Step 2: Write real Git/archive/saved fixture tests for exact CRLF/modes,
  dirty checkout preservation/no SOURCE/DRIVER execution, resealed source/identity/
  member tamper, duplicate/nonfinite JSON, saved hash/type/receipt mismatch,
  existing/symlink/internal output and changed SHA. Run focused suite.
  Expected: RED assertions for missing recover_tooling module, not fixture failures.
- [ ] Step 3: Implement helper with bounded captured payloads and canonical Git
  identity, exact closed saved set, fresh writes and existing R64 reader receipt binding.
  Run focused suite. Expected: GREEN; invalid source leaves no destination;
  invalid saved evidence may be preserved but never returned as recovered.
- [ ] Step 4: Full cloud gate, then commit helper/tests. Expected:179+actualnew
  methods,27compiles,staticPASS. Record completion ledger in the same work step.

### Task 2: Frozen profile and one-command orchestration

**Files:** create tools/cyberlateral_cloud/cloud_start.py,
tests/test_cloud_start.py, docs/PINNED_CLOUD_START_R68_KO.md; modify cloud README.

**Interfaces:** consumes Task1 recover_tooling and existing cloud_restore/hf_archive/
compare_saved_browser/render_comparison_summary. Produces get_profile()->dict,
run_profile(repo:Path,sdk:Path,output:Path,profile:dict)->dict and CLI profile/run
with the exact profile/stage/marker/exit behavior in the spec.

- [ ] Step 1: Write engine tests using real local Git/archives/saved comparisons;
  double only external SDK/network/venv worker boundary. Assert successful complete
  output files, literal original FAIL and DIFFERENT, exact consumed pins, missing/
  failing SDK/DEV/fetch/gates/SAVED rejection and stage preservation, no premature
  START_RESULT; existing/symlink/internal outputs untouched. CLI profile/help
  deterministic/import-isolated, malformed options rejected. Run focused suite.
  Expected: RED for missing engine/CLI; Task1 remains GREEN.
- [ ] Step 2: Implement engine/CLI and Korean completion reading aid; no private
  profile override in CLI or archived code execution. Focused suites expectedGREEN.
- [ ] Step 3: Write new Korean guide and README current-entry link without editing
  historical guidance. Full cloud gate expected179+actualnew/29compiles/staticPASS.
- [ ] Step 4: Real default command twice in fresh external folders using existing
  SDK; actual pinned downloads, source441+35 and saved114, R41portable26 and saved
  comparisons identical, exact original statuses and no HF metadata writes. Missing
  SDK/existing output controls expectedexit2/no root success. Preserve all evidence.
- [ ] Step 5: Commit feature, fresh full gate expectedallPASS; record completion.

## Finish

One fresh whole-branch reviewer with the five focus lines and ledger rulings;
re-grade, fix Critical/Important by one RED->GREEN pass, minors deferred, no re-review.
Keep local feature/worktree/evidence; no shared writes. Double deterministic
evidence plus independent bounded custody verifier and final live source/HF receipt.
Helper script resources unavailable in this skill package: retain explicit
task briefs/BASE/logs/ledger externally; do not silently skip verification steps.

Self-review: Task1->Task2 interface matches exact signature/return data. All five
focus items map to focused real-state tests and/or real two-run consumers. No tests
of human prose, no new archive schema change or hidden numeric/policy assumption.
