# V3 external SSD storage amendment

기존 V3의 모델·threshold·TP 제약·평가 규칙은 바꾸지 않는다. 검증된 E 외장
SSD를 실행 저장소로 지정하고, 이전 무결성과 새 authorization을 확인한 뒤에만
실제 retrospective 실행을 허용한다. 이 문서의 계획 항목은 실행 결과와 구분한다.

## Identity and purpose

Cyber Validation, baseline `3acd6543eff2b88b8128f6fb71a2b60f08ac5617`, branch
`feature/cyber-autotune`. User-supplied execution specification is authoritative.
Change scope: storage authority only; historical evidence and contracts immutable.

## Original references

Same CyberPilot repository/license; existing V3 I/O, store, orchestration,
V1/V2 numerical implementation and exact public policy receipts. Existing linked
feature worktree is reused. No dependencies, submodule or numerical changes.

## Implementation plan

Goal: validate migrated inputs, authorize only the verified E volume, then perform
the separately authorized 32-job two-run retrospective experiment.
Architecture: additive storage amendment and migration verification; explicit
authorization binding; context-bound storage checks reused by existing writers.
Tech stack: frozen Python/NumPy environment and existing deterministic gzip format.

- [x] Phase 1: verify completed migration logs/receipts and manifest-listed input
  bytes only. Supplement the migration with explicitly planned direct-E copies of
  the causal/derived pinned members currently inside the E-backed WSL image.
  Record exact private mappings and a redacted public receipt; no arrays decoded.
  All manifest-declared members: 23,273 files, 2,677,113,133 bytes, exact SHA verified.
  Existing successful V1/source identities remain unchanged.
- [x] Phase 2: add `empirical_hurdle_v3_external_storage.py` with exact E mount,
  physical volume, root, overlap and authorization bindings. Keep base D behavior
  for historical callers; amendment-authorized runs must reject D and other roots.
  Extend I/O/preflight, store, resume and cleanup-eligibility storage routing only.
  Write failing tests first, including remount/volume drift and pre-numeric traps.
- [x] Phase 3 validation; Phase 4 commit/CI pending: run synthetic storage and all V3 parity/firewall/repeatability/
  resume tests, historical/combined/full regression, replay, lint/syntax/JSON/
  privacy/diff/SCons. Independent storage review; fix findings. Publish additive
  amendment evidence; commit/push and verify clean exact-HEAD CI success.
- [ ] Phase 5: outside the executor generate the user-approved one-shot trusted
  authorization bound to that committed HEAD, code, E volume/roots, migration,
  source/model/anchor/reference identities, frozen runtime and exact capacity.
- [ ] Phase 6/7: clean independent repeat-1 and repeat-2, all 32 jobs each, no
  performance early stopping. Byte-exact comparison, trapped resume both runs,
  manifest-bound before/after source hashes. Retain repeat-2, no cleanup deletion.
- [ ] Phase 8/9: allowlisted V1/V2/V3 aggregates, separate folds and clause
  transitions, documentation, two independent reviews, required regression,
  commit/push and final clean exact-HEAD CI success.

Review focus: remounted/reassigned E drive after authorization; symlink/nested
mount aliases; WSL-image sources accidentally admitted as direct E roots; source
overlap and partial migration; authorization routing retained during resume.
Every case belongs to the external-storage tests or manifest verifier tests.

## Changes and expected effect

Only storage admission is extended. Model bytes, normalizers, features, 16
structures, folds/anchors, TP references, five feasibility clauses, objective,
strict probability comparison, p95, projection, recursive rollout, 32-clause
acceptance and selection remain unchanged. No numerical benefit is assumed.

## Regression risk and acceptance

Baseline: full 4,731; V3 focused 104; combined empirical 1,872; replay 16.
No source rebuild, fitting, fallback, HOLDOUT, pooled refit or vehicle authority.
Fail closed on migration/hash/mount/authorization/environment/capacity conflicts.
Public evidence permits opaque root hashes and E_EXTERNAL_SSD only, never paths.

## Validation method and actual results

Startup: fetch, clean local/origin equality, baseline ancestor verified. Exact
baseline CI run 38478340876 completed/success. Migration completion and healthy
SSD identity verified. Exact executor capacity bound: 17,638,766,452 bytes;
observed free space exceeds this. Direct-E supplemental transport is verified
separately before authorization; its public receipt contains only opaque roots.

Focused V3: **121 passed** (187 subtests). Combined empirical: **1,889 passed**
(812 subtests). Full AutoTune and controls: **4,748 passed**. Lateral replay:
**16 passed**. Ruff, compileall, publication checks, diff checks and SCons passed.
The bounded/exhaustive numerical parity and synthetic independent 32-job runs,
byte comparison and trapped resume are included in the focused suite.

Migration changed two historical synthetic exclusion paths into D-to-E aliases.
Unisolated tests correctly rejected those aliases. The successful regression ran
inside a private user/mount namespace with an empty temporary D mount. It changed
no global mount, data or historical guard. Actual execution uses the normal E
mount namespace. Earlier failed/aborted attempts remain in private validation logs.

Independent read-only storage review identified a physical-volume reassignment
gap after preflight. A live Windows volume GUID check now precedes each numerical
permit and each write, alongside the kernel mount identity. Regression tests
reject post-admission and per-write GUID drift. The reviewer verified the fix;
no blocking or important finding remains. A separate pre-execution numeric review
  found no important or blocking issue. No numerical implementation changed.

## Handoff

Actual V3 execution remains NOT_RUN until the committed amendment's CI and new
out-of-process authorization pass. HOLDOUT CLOSED, opening/discovery zero;
pooled refit forbidden; vehicle authority NONE.
