# CyberPilot Legacy V2 Shadow validation

## Identity and purpose

- Area: Validation / CI. Status: implemented; exact-HEAD GitHub validation pending at commit time.
- Purpose: complete the original Legacy checks in a separate public offline job.
- Scope: new workflow and independent Shadow contract only; no vehicle application.
- Baseline: feature/cyber-autotune at dfbc1915f981f67f570e6a3e750eb5e28375595b.

## Original references

- Repository: https://github.com/rownlvh8875-coder/CyberPilot (MIT license).
- Original workflow: .github/workflows/cyberpilot.yaml, unchanged Frozen bytes.
- Reused tools: tools/test_runner.py, full_ci_test_manifest.py, verify_full_ci_coverage.py.
- Native source, wrapper, compiler, flags, binary and receipt use existing qualified pins.
- Submodule six gitlinks, LFS252 pointers and Frozen231 remain unchanged.

## Changes and expected effect

- Add cyberpilot-legacy-v2.yaml with distinct LEGACY_V2_SHADOW_FULL_VALIDATION job.
- Add independent cyberpilot-legacy-v2-shadow-contract-v1.json; old V1 contracts are preserved.
- Execute original setup, publication, SCons, Ruff and postchecks.
- Prepare fresh GCC13.3.0 Native artifact and explicit receipt before regression.
- Run the unchanged full-suite runner through its existing two-worker evidence helper.
- Require exact5960 current IDs, original5927 subset and59 atomic fixture groups.
- Require all18 prerequisite stages and sealed source/Native/regression proof in one job.
- No new artifact upload, privileged token, enforcement or Legacy disable operation.
- Default offline opt-in and all controller/scientific/native runtime source remain unchanged.
- Timeout45minutes is bounded headroom: current V2 PR producer1767s/push1149s,
  D2 local workers1123.87s/1128.05s. Local time is not a GitHub bound.
- Legacy regression global BLAS settings remain unspecified; original attribution
  OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1 are retained.

## Regression risk and acceptance

- Reject missing/duplicate/nonpass IDs, fixture splits, wrong head or changed Native/source proof.
- All original stages must execute successfully; final always-step cannot rescue failures.
- Same-job evidence includes exact checkout SHA/run/attempt/event, not a cross-job artifact claim.
- Shadow SUCCESS never means old Legacy SUCCESS, all CI green, merge approval or road readiness.
- Historical receipt verification, original Frozen workflow and V2 gate remain independent.
- Rollback: normal revert of this additive commit after impact review; retain all old/new evidence.

## Validation method and actual results

| Check | Method | Actual result and limit |
| --- | --- | --- |
| Workflow | YAML, Bash, embedded Python, actionlint | PASS; actionlint and external4+7 verifier tests, codespell2.4.3 |
| Coverage | exact IDs / fixture owners / result seals | 5960 PASS /1129.80s; exact IDs,59 fixture groups, zero split |
| Native | fresh build and original receipt verification | PASS; GCC13.3.0, qualified binary and receipt hashes |
| Postchecks | attribution95, lateral16, syntax/whitespace, JSON, publication, source, clean | PASS in corrected isolated postcheck arm; findings0 |
| Whole Shadow | actual GitHub push/PR job | Pending exact-HEAD run |
| Existing regressions | Unit, V2, numerical, Native | Pending exact-HEAD run |
| Official process replay | Separate observed upstream job | No reference update; no local rerun |
| Local limits | prepared read-only venv; GitHub checkout/setup not emulated, WSL fetch DNS unavailable | Actual final entrypoint rejects incomplete local stages; no whole-local-CI success claim |
| Vehicle / private evaluation | Outside authority | NOT_AUTHORIZED |

The full regression ran before removing trailing spaces from six blank YAML lines.
All stage metadata, normalized shell commands and embedded Python AST stayed equal;
corrected bytes, fresh Native preparation and postchecks were revalidated separately.
Hosted exact-HEAD execution remains the acceptance criterion.

## Handoff

- Required precommit review: source integrity, coverage, Native trust and failure propagation.
- No promotion to a Required Check; PR remains Draft/Open/Unmerged.
- D2 PERFORMANCE_NOT_EVALUATED; HOLDOUT CLOSED; vehicle authority NONE.
- selected_candidate and selected_policy remain null.
