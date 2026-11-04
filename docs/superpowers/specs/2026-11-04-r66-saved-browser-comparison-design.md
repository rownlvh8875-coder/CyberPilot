# R66 — exact saved-browser byte comparison

Base896d0ff8567610c75ca3c493f9efd2d43e738b3a. Owner delegated ordinary
offline next steps/inline implementation without repeated design questions.

## Intent and author choices

R64 verifies one saved bundle; repeated recovery checks currently compare bytes
in external scripts. Add a reusable read-only two-bundle comparator, not another
browser run or visual/numerical oracle. Existing Python/stdlib conventions stay.
The author selects exact complete saved bytes over semantic normalization or
PNG similarity: the latter would require new equivalence/tolerance policies.
Checksums and incidental saved log/metadata bytes are intentionally included.
DIFFERENT is not a newly evaluated visual regression; identical FAIL stays FAIL.

## Boundary and interfaces

Extract existing R64 validation into
`load_saved_browser(root: Path) -> tuple[dict, dict[str, bytes]]` in browser_verify.
Return the existing unchanged receipt and precisely the bytes validated in one
bounded snapshot. `verify_saved_browser(root: Path) -> dict` remains compatible,
as does its CLI --input and exit0PASS/1recordedFAIL/2invalid. No producer/classifier
change, reread-after-validation shortcut, temporary-directory copying or writes.

`compare_saved_browser(baseline: Path, candidate: Path) -> dict` in browser_compare
uses that loader once per operand and compares every38file's raw bytes, in
lexically sorted relative-path order. Both inputs must independently validate.
Same path is allowed; snapshots are sequential, not atomic across time/inputs.
Per bundle8MiB/file32MiB total; up to64MiB saved bytes for the pair. Existing
regular-file/no-follow/fixed38file-seven-dir/strict record/closed manifest rules.

Result schema1 contains:
- status: R66_SAVED_BROWSER_EXACT_BYTES_MATCH or R66_SAVED_BROWSER_BYTES_DIFFERENT;
- comparison: EXACT_SAVED_BYTES; compared_files38, changed_files, unchanged_files;
- differences: sorted {path, baseline:{sha256,byte_size}, candidate:{sha256,byte_size}};
- baseline_verification and candidate_verification: original R64 receipts;
- quality_assessment: NOT_PERFORMED; source_identity_reauthenticated:false;
- comparator_browser_model_F61_vehicle_executions:0;
- scope: SAVED_BYTES_COMPARISON_NOT_VISUAL_OR_ORIGIN_ATTESTATION.
No absolute paths/time/output files, no metrics reclassification, ignored files,
tolerance, coercion, fallback, repair, source/publisher authentication or gate lift.

CLI `python -B tools/cyberlateral_cloud/browser_compare.py --baseline EXISTING
--candidate EXISTING`: deterministic JSON stdout; exit0exactmatch/1different/
2invalid. MATCH does not mean either original screen PASS. On invalid input no
stdout, stderr `REJECTED: BASELINE_BROWSER_BUNDLE_*` or `CANDIDATE_BROWSER_BUNDLE_*`;
stop on invalid baseline before touching candidate. No abbreviation/new output.
Missing/unsupported/partial/corrupt data never becomes an ordinary difference.

## Scope and preservation

Modify only browser_verify, its tests, cloudREADME; add browser_compare, focused
tests and SAVED_BROWSER_COMPARE_R66_KO.md plus this spec/plan. No app/producer/
summary/probe/artifacts/locks/workflows/rootREADME or historical guides edits.
No browser/app/model/F61/SDK imports or invocation by comparator. Existing
prepared app/SDK only; no installs, HF writes/publication or main merge this task.
Normal feature/Draft PR + exact-head CI/evidence; preserve all environments,
branches and evidence, including the external plan workspace (no cleanup).
DEV883/wheel inherited, not new qualification. Full cloud units perform NONZERO
synthetic work; comparator/actual saved consumers perform no new model work.
R_BUDGET UNRESOLVED, Static Gate FAIL, actualr/T2/scale null, Candidate/Runtime
NO_GO, F70UH/F70V/F71 and vehicle activation NOT_ALLOWED remain unchanged.

## Acceptance

Baseline141/21/static. New real-file tests prove validated snapshot compatibility,
all38bytes comparison (including logs/manifests/JSON spelling), deterministic
ordered hash/size deltas and CLI0/1/2, original FAIL preservation, invalid-side
errors, partial/extra/symlink/FIFO/bounds/strict records, no optional imports/no
input changes. Existing R64 tests unchanged except new loader cases, all green.
Actual retained real-browser roots compared twice; self-copy MATCH, valid changed
log copy DIFFERENT, corrupt/partial copies invalid on both sides; original bytes/
file sets/modes unchanged. No new browser/installation claim. New unit count is
actual baseline141+observed methods, own Python23. One fresh final branch review,
actual hosted CI, deterministic ZIP pair and independent bounded evidence parse.
