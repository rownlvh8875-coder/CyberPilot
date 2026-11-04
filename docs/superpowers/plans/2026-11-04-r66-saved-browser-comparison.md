# R66 Saved Browser Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans; owner delegated inline execution.

**Goal:** Compare two fully validated saved browser bundles without re-execution.

**Architecture:** Share the R64 single validated byte snapshot via a new loader;
keep its old receipt API/CLI intact. A stdlib comparator emits exact relative-file
hash/size differences and preserves original recorded states, never visual truth.

**Tech Stack:** Existing CPython3.12.13, stdlib, cloud unittest/static tools.

**Spec:** docs/superpowers/specs/2026-11-04-r66-saved-browser-comparison-design.md

## Global Constraints

- Base896d0ff8567610c75ca3c493f9efd2d43e738b3a, reuse clean host-linked workspace.
- Old R64 API/CLI/receipts stay compatible. New loader returns only validated
38regularfile/seven-dir bytes,8MiB/file32MiB/bundle; pair64MiB; no atomic claim.
- Comparator CLI --baseline/--candidate, exit0match/1different/2invalid, typed
schema1/result fields and safe side-prefixed errors exactly as spec.
- No ignores/normalization/repair/fallback/new screen/metrics/source authenticity.
- No app/producer/summary/probe/artifacts/locks/workflows/rootREADME/old guides edits.
- No main merge/HF writes/vehicle work; preserve source/environments/evidence.

## Review Focus

- Two snapshots diverge during writes: compare the exact validated bytes, not a later reread; no atomic or concurrent-writer guarantee.
- Identical recorded FAIL: exact match must preserve both FAIL receipts, never imply screen quality PASS.
- Incidental log/manifest/JSON bytes differ: report all owned bytes without hidden normalization or semantic-equivalence claims.
- One operand is partial/unsupported/symlinked/oversized: reject with side-specific safe error, not a normal DIFF or partial stdout.
- Passive dependency boundary: no browser/app/model/SDK import, network, input writes or temporary outputs.

### Task 1: Validated loader and complete comparator

**Files:** modify tools/cyberlateral_cloud/browser_verify.py and tests/test_browser_verify.py;
create browser_compare.py, tests/test_browser_compare.py and
docs/SAVED_BROWSER_COMPARE_R66_KO.md; add cloudREADME link. Relative to cloud tools
unless full path stated. Spec/plan are committed first.

**Interfaces:** consumes existing fixed layout/manifests/strict result/summary;
produces load_saved_browser(Path)->tuple[dict,dict[str,bytes]] and
compare_saved_browser(Path,Path)->dict with schema1 fields fixed by spec.
One cohesive deliverable, no downstream task/shared interface.

- [ ] Baseline full cloud gate141/21/static expectedPASS; commit spec/plan.
- [ ] New loader tests first: exact validated detached byte snapshot/receipt,
corrupt input never returned. New comparator tests first: self/copy match,
literal sorted size/hash deltas, changed logs despite same RESULT, JSON spelling,
same FAIL not qualityPASS, PASS/FAIL delta,0/1/2/determinism/no mutation/no path,
both-side corrupt/partial/extra/symlink/FIFO/size/record errors and import isolation.
Run APP -B -m unittest discover -s tools/cyberlateral_cloud/tests -p 'test_browser*verify.py' -v
then new compare suite. Expected new tests RED for missing loader/comparator,
not fixture failure. Existing R64 tests remain green.
- [ ] Extract existing validation into loader, keep old verifier wrapper; add
minimal comparator/CLI. Expected focused new+existing suites GREEN, exact R64
receipts/exit semantics retained. No second unvalidated read or product imports.
- [ ] Write Korean scope/usage and README link, no historical guide changes.
Run full cloud gate; expected141+actualnew methods/23owncompile/staticPASS.
- [ ] Execute actual saved consumers twice each: retained pair/self-copy/changed
log copy/corrupt and partial on either side, expected DIFF-or-MATCH by raw bytes,
0/1/2 exact independent raw-file oracle, stdout deterministic, source untouched.
- [ ] Commit feature; full cloud unit repeat expectedallPASS and ledger completion.

## Finish

One fresh whole-branch reviewer with focus list above and all Ruling lines.
Re-grade findings; Important/Critical one TDD fix pass, minors deferred, no re-review.
Normal feature push/Draft PR/attach; exact-head CI artifact/source hashes and all
PR checks success/SKIP. Main/HF unchanged. Two deterministic ZIPs, independent
bounded stdlib identity/closure/consumer checks; final live receipts outside ZIP.
Preserve workspaces/evidence. No new install/browser/model work in saved consumers.

Self-review: cohesive one task/no shared interfaces; each focus maps to a real-file
test and/or actual saved consumer, no tests of prose/source text.
