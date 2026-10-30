# Repository Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL superpowers:executing-plans inline TDD and one fresh final reviewer. User delegated choices and approved scoped commit/push/PR; no routine approvals.

**Goal:** Versioned standalone CyberLateral0.3.0 integration with one-command offline CI.
**Architecture:** Exact sealed package import into tools/cyberlateral_dev, isolated dev env/check runner, scoped GitHub workflow and safe draft-PR publication.
**Tech Stack:** CPython3.12.13/uv0.12.23/stdlib package; pinned DEV dependencies only.
**Spec:** tools/cyberlateral_dev/docs/INTEGRATION_DESIGN.md

## Global Constraints

- Only new component, new workflow and root README; no root dependencies/runtime/submodule/main merge changes.
- Exact R7 src/project bytes, package0.3.0, runtime dependencies[], expected wheel SHA per DESIGN.
- Old evidence unchanged; no original Controller/Runtime/CAN/F61/schema execution/compile or actual data/r/dt/candidate evaluation.
- Only2 helper bodies in DEV reference,0 in package. Actual r/T2/scale null, Static Gate FAIL, Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED.
- Prevent legacy PR build/replay via tested push first, tree-identical skip-ci guard and DRAFT PR; no CI-policy/credential changes.

## Review Focus

- Root dependencies/native vehicle sources never become implicit dependencies of standalone project/CI.
- Existing file/dir/dangling output must reject before work, and imported source mismatch must reject before reference execution.
- Installed wheel and moved checkout must work without /workspace paths/source/NumPy runtime dependencies.
- Full verification must not recursively invoke itself or silently omit old tests/fixture identities/gates.
- Dedicated CI proof must distinguish tested commit/tree from guarded PR head; no old vehicle CI or false head-green claim.

## Task1 — sealed import/environment

Files: tools/cyberlateral_dev/{src,project,licenses,reference,build_backend.py,pyproject.toml,tools/build_wheel.py,IMPORTED_ARTIFACT.json,.gitignore,uv.lock,README.md}.

- [ ] Verify R7 ZIP and copy selected exact bytes; run127-method baseline.
- [ ] RED project/test_repository_integration.py for isolated dev config/provenance integrity/runtime/build identity.
- [ ] Add pinned dev config/lockfile/import manifest, project README and root link; install isolated local env only.
- [ ] Whole suite PASS; wheel remains exact R7; commit scoped import.

## Task2 — verification command and CI

Files: dev.py,integration_tools/verify.py,project/test_dev_command.py,project/test_ci_contract.py,.github/workflows/cyberlateral-dev.yaml.

- [ ] RED output-guard/import-tamper/real-wheel helper tests, semantic safe workflow configuration tests; full CLI missing command RED.
- [ ] Implement verify helpers/orchestrator and pinned scoped CI; actual end-to-end verify outside unit suite (no recursion).
- [ ] Whole suite/static/lock/repro/local isolated report PASS; commit checked runner/workflow.

## Task3 — independent review and safe publication

- [ ] Fresh final read-only review against initial base/spec/ledger; Important fixes RED->GREEN with whole suite; minors ledger.
- [ ] Final full verify on clean committed tree; normal branch push (no PR yet); monitor dedicated CI only.
- [ ] Record tested SHA/tree, add tree-identical skip-ci guard, push and create DRAFT PR; attach artifact.
- [ ] Try dedicated manual dispatch guarded head; report exact CI status/URLs and main/runtime preservation. Keep worktree.
