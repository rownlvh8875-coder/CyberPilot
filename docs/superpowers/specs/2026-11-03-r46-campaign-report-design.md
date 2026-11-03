# R46 — Read-only saved campaign comparison report

## Intent and choice

After R45 main/HF integration, make saved multi-seed comparison results usable in
a browser without new model/reference calculations. Owner delegated routine offline
choices and opted out of repeated design questions. This scope/approach is the
author's choice, not a new vehicle/r-policy approval. Base3787068425da30f340ef6dca73e1214e6a6e0cd4.

Approaches considered:
- **Selected:** separate R46 reader/HTML/CLI for complete R44 V1 output. Preserve
  all old producer/comparator formats and hashes; explicit validation/view boundary.
- Add HTML to R44 production: changes its closed file set and existing outputs.
- Render Markdown alone: loses typed values, source failures and cross-record checks.

## Input and consistency

`read_comparison(path: Path) -> dict` owns a bounded complete R44 comparison snapshot,
not its baseline/candidate inputs. Root4files: CAMPAIGN_COMPARE.json, SUMMARY_KO.md,
RECEIPT.json, SHA256SUMS.txt; paired runs add fixed comparisons/seed-NNN/COMPARE.json
and same-directory SHA256SUMS.txt. Max4runs/12files,32MiB total,16MiB per file; reuse
bounded no-follow capture/closed Manifest checks. Reject symlinks including ancestors,
FIFO/devices, extras/missing files, corruption, late changes and unsupported contracts.
Read into owned bytes with no-follow regular-file descriptors; check all read hashes
against capture and repeat capture after ownership. Never follow private receipt paths.

Canonical typed JSON only: reject duplicate/nonfinite/noncanonical/overdeep values.
Validate exact known R44/R34 schema fields, strict bool/int types, gates and fixed
claim/time/exactness/zero-new-work fields. Parameter bounds remain R43 V1:1..4unique
uint32 seeds,1..16cases,16..256steps. Validate explicit positional run/case IDs and
fixed child paths; source side presence, classifications, status aggregation and alerts;
root sample count from children; root differences from parameter changes+run counts;
child counts from cases;256detail cap/first difference/truncation and retained contexts;
before/after presence separately from null; source/child identity flags consistently.
For untruncated details verify full retained grouping/counts; truncated evidence must
not claim all unseen details were checked. Preserve order, typed values and all retained
details. Render private receipt only as file hash, not path/content. Recorded producer
identity is metadata, never authenticated against current installed/source code.

This is structural/saved-record consistency, not regeneration of the original R44
comparison from unavailable campaigns, numerical truth, or origin authentication.
Markdown/private narrative equivalence is not checked; bytes/hash closure is checked.
Known V1 only, not a generic R34 renderer or arbitrary future-schema loader.

## View, UI and command

`VIEW.json`: schema_version1,contract_id R46_RECORDED_CAMPAIGN_COMPARISON_VIEW_V1,
comparison (full parent), children (paired child records by run_id),source_file_hashes,
renderer_model_executions0,renderer_reference_executions0 and explicit recorded-only claim.
`_render_html(view: dict) -> bytes` is internal; validated reader view only.
`run_report(input_path: Path, output_path: Path) -> dict` and separate
`tools/scenario_campaign_compare_report.py --input COMPLETE_R44 --output NEW_EXTERNAL`.
No alternate/abbreviated/input/r/dt/vehicle options. CPython3.12.13/Linux binary64.

Static Korean index: prominent overall vs recorded-regression status, source verdicts,
counts/identity/truncation, ordered seed table, retained differences with exact typed
before/after+presence+case/index, source-error/difference findings and SHA evidence.
Both ERROR/regressionMATCH and DIFFERENT/regressionMATCH stay clearly non-success.
No numerical charts, interpolation, rounding or new oracle. Index is invocation order,
not seconds/100Hz. All strings escaped; CSP default-src none, inline CSS only; no JS,
external assets, active embeds, private-path links or baseline auto-update. Only fixed
local VIEW.json/checksum links and generated internal anchors. Mobile390px/desktop1440px:
readable14px minimum body/table/code text, wrapping cards/values, scoped table scroll,
no document-wide horizontal overflow, status text not color-only.

Output: index.html,VIEW.json,private RECEIPT.json,closed SHA256SUMS.txt. Report generation
success exit0 even for recorded ERROR/DIFFERENT, print REPORT_COMPLETE and recorded
verdicts explicitly; it is not a source MATCH promotion. Invalid/incomplete input exit2,
bounded CAMPAIGN_REPORT_* message/no traceback/output. Existing output never overwritten;
reject component/input-internal output and symlink ancestors before reading inputs.
Normalize expected OS/path errors, retain specific codes, do not hide programmer TypeError.
Snapshot renderer source/input hashes before/after and immediately before final HTML
exclusive link. Fully write pending HTML first; index.html is commit point; cleanup
after commit warns without contradicting completion. Precommit failures preserve partial
files but no valid index. No whole-directory atomicity/fsync/crash/hostile-writer guarantee.

## Constraints and delivery

No old producer/comparator/model/oracle/generator/public0.3.0/wheel/lock/dependency/cloud/CI
changes. Renderer model/reference/F61/actual r/dt/vehicle work0; fixture/unit/gate/CI
synthetic work NONZERO/unaggregated. R_BUDGET UNRESOLVED, Static Gate FAIL, actualr/T2/
scale null, Candidate/Runtime NO_GO, F70UH/F70V/F71/activation NOT_ALLOWED.
Actual saved two-seed128sample reports twice, difference/error/source-difference/added/
truncated controls, hashes/Manifests/input preservation and browser desktop/mobile
captures required. Independent final code review, full gate/cloud and actual PR CI.
This stage ends at open reviewed PR/evidence; no main merge/HF refresh or cleanup.
