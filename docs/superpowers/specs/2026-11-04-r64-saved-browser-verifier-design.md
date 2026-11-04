# R64 — read-only verification of saved browser bundles

Baseline cc453796483edfc28c92babf76280154b906d549. Owner delegated ordinary offline
next-step choices and inline execution without repeated design questions. Author
chooses a saved-bundle consumer: current docs require RESULT and full checksums,
but readers currently need ad-hoc external verification code to enforce closure.

## Intent / approach

Add a separate stdlib-only browser_verify.py CLI/API. Do not change producer,
classifier, summary renderer, app, locks, workflows or canonical R62 recipe.
Alternatives: another human checklist leaves repeated manual verification;
adding a mode to browser_smoke couples a passive reader to active orchestration.
Author chooses the separate read-only module, using existing manifest/summary
functions without importing a model, browser library, SDK or app component.

## Supported contract

verify_saved_browser(root: Path) -> dict; CLI --input PATH, no output argument.
Supports current R62-format SUMMARY and RESULT schema_version1, not arbitrary
historical imports, pre-summary R60 bundles, ZIP extraction or schema migration.
Original inputs are never edited, resealed, rendered, executed or uploaded.

The fixed producer layout has38 regular files: RESULT, SUMMARY, root SHA;
three child logs; two fixture-inputs profiles each six files; two report profiles
each four files; twelve captures(sign/resumed,390/1440,top/charts/footer).
Only its seven required directories are permitted. Reject missing/extra files,
directories, links (including root ancestors), special files and partial FAILURE.
Read bounded regular files only:8MiB each,32MiB total; check sizes before reading,
bound reads again; Linux no-follow/nonblocking opens prevent leaf-link/FIFO waits.
No claim of an atomic snapshot or protection against an actively hostile writer.

Require canonical closed root and four nested SHA manifests using artifacts.manifest.
Strict UTF8 JSON RESULT rejects duplicate keys, nonfinite/overflow floats, invalid
JSON and excessive nesting. Require typed version1, declared source-unchanged True,
fixture_runtime_attestation False and declared model/F61/actual-r-dt/vehicle count0.
Require16 syntactically valid source-hash records (not reauthenticated source),
and captures/input/report hash maps exactly matching the owned file bytes.
Use render_summary to validate stored ten-case order/status/code structure and
compare exact current-format SUMMARY bytes. Do not invoke assess_case or infer
new observations from recorded metrics. Do not reinterpret failures as successes.

Return status R64_SAVED_BROWSER_BUNDLE_VALID, recorded_status, cases10,
recorded_case_failures, recorded_failure_records, verified_files38, RESULT SHA,
reader_browser_model_F61_vehicle_executions0, source_identity_reauthenticated False
and scope SAVED_BYTES_AND_RECORD_CONSISTENCY_NOT_NEW_BROWSER_OR_ORIGIN_ATTESTATION.
CLI exit0 for valid recorded PASS,1 for valid recorded FAIL,2 for invalid/unreadable
or unsupported bundles. Stable REJECTED codes, no traceback or supplied path/raw
exception leak; empty stdout on rejection. --help needs no browser/credentials.

## Assurance boundaries

Hashes/summary agreement are consistency, not publisher authentication, proof of
actual captures, source identity authentication, revalidation of R32 numeric data,
cross-machine/browser qualification or independent numerical correctness. A
coherently forged and resealed tree can pass. Preserve unknown valid failure
codes and null/missing observations; no new classification, normalization or repair.
The new command exists in the new Git tools revision, not pinned old1b244fe8.

## Verification / delivery

Test first with real saved fixture/report generation and a clearly synthetic
observation record; no mocked browser claim. Prove pass/fail/invalid CLI results,
no writes/imports, closure, bounds, links/FIFO, strict JSON, hash-map association,
summary mismatch and typed scope guards. Run full cloud suite/static/compile.
Consume two retained real PASS bundles and a sealed global-FAIL bundle without
rerunning browser/model; corrupted/partial new copies reject. Verify every input
byte/file set before/after, deterministic stdout and no producer/source changes.
One fresh whole-branch review, normal feature Draft PR/exact-head CI, sealed
evidence and independent bounded parse. No main merge or HF writes in this task.
Keep all prior workspaces/branches/evidence and new evidence workspace.
R_BUDGET UNRESOLVED, Static Gate FAIL, actualr/T2/scale null, Candidate/Runtime
NO_GO and F70UH/F70V/F71/vehicle activation NOT_ALLOWED remain unchanged.
