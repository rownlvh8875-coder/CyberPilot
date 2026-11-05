# R70 — read-only recorded trace stage summary

Base main1cd6ed64b8700641875fa6d5eebf95e125e89411. The owner delegated ordinary
offline choices and inline execution without repeated design questions. R69's
32 synthetic cases/8192 model-reference steps matched, but its aggregate verdict
does not explain which recorded stages changed a command. This is a small DEV
inspection feature, not a model or production-binding change.

## Author choice and approaches

Use one new stdlib DEV backend and stdout CLI over the existing bounded R31 reader.
The existing R32 view already counts overall limiter/inactive/suppression; preserve
those counts and add finer stored clip observations. Altering the frozen wheel/
model would broaden the API; recalculating limiter/rate formulas would become a
different oracle. Reading raw RESULTS.json alone would bypass existing consistency
checks. Do none of those. No new HTML/UI, dependency, campaign reader or schema.

Only new integration_tools/scenario_trace_summary.py, tools/scenario_trace_summary.py,
project/test_scenario_trace_summary.py and docs/RECORDED_TRACE_SUMMARY_R70_KO.md;
add a link/paragraph to component README. Commit this spec/plan first. Existing
R31/R32 reader/formatter, public src/version0.3.0/wheel, imported77, all locks,
workflows/cloud profiles/historical docs remain byte unchanged.

## Input and API

`summarize_saved_trace(input_path: Path) -> dict` reads an exact R31 six-file
directory. Guard CPython3.12.13/Linux/binary64 first (ReportError code
TRACE_SUMMARY_RUNTIME), then UTF8/NUL and root/ancestor symlink paths
(TRACE_SUMMARY_INPUT_FILE). Existing _files owns the bounded regular bytes once;
decode_report validates all six bytes/Manifest/schema/CSV/summary/state/gates before
any event counting. Reuse the same owned RESULTS bytes; never reopen data or follow
paths in receipts/producer metadata. Existing ReportError REPORT_* codes stand.
This is cooperative captured-byte consistency, not atomic OS/publisher attestation.

Output schema_version1, contract_id R70_RECORDED_TRACE_STAGE_SUMMARY_V1,
status RECORDED_TRACE_SUMMARY_COMPLETE, scenario_id, recorded_model_steps,
recorded_summary (the existing R32 summary verbatim), stage_events,
source_hashes (all six captured files), validation_claim (existing R32 claim),
source_identity_reauthenticated=false, summary_model_executions=0,
summary_reference_executions=0, time_semantics INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME,
gates unchanged and interpretation OBSERVED_STAGE_RECORD_DIFFERENCES_NOT_UNIQUE_CAUSE_OR_ARITHMETIC_APPROVAL.

Each ordered stage_events entry is {count:int,first_sample_index:int|null}:

1. driver_clip_numeric_changed: driver_clip x vs result numeric inequality.
2. driver_clip_representation_changed: x vs result stored kind/value inequality.
3. rate_clip_numeric_changed: rate_clip x vs result numeric inequality.
4. rate_clip_representation_changed: x vs result stored kind/value inequality.
5. rate_to_limited_numeric_changed: rate_clip result vs integer limited_command.
6. fault_condition_true: stored downstream fault_condition is true.
7. angle_counter_reset: prepared counter>0 and stored next counter==0.

Compare scalar numbers EXACTLY: int records remain arbitrary exact integers;
finite canonical hex floats convert to exact rational values, never round an int64
through binary64. Python/NumPy kind-only changes and -0/+0 are numeric-equal but
representation-different. No clip/rounding/limit recomputation. Never compare
normalized requests against integer command units. First index is the earliest
declared sample index, not row offset or time. A zero count has null first index.
Events overlap; do not sum into mutually exclusive causes or label fault_condition
as a vehicle fault. Coherent resealed arithmetic errors can still be summarized:
the existing reader establishes record consistency, not numerical correctness.

Return independent records without global mutable output/cache; input unchanged.
No per-row events array, percentages, r/dt/policy/config inference or follow-up IO.

## Formatting and CLI

Task2 adds `format_saved_trace(input_path: Path, output_format: str='json')->bytes`.
Validate built-in string json/markdown before input access; bad format raises
ReportError TRACE_SUMMARY_FORMAT. Build the record internally; there is no public
formatter accepting arbitrary caller-supplied summary dictionaries. JSON is existing
canonical UTF8 single-line JSON with newline. Private Markdown shows scenario,
recorded count, existing R32 counts, seven event counts/first indices, source
RESULTS SHA, unchanged gates and overlap/record-only/no-new-work caveats. It emits
no links/HTML/receipt paths; IDs are already bounded R31 ASCII identifiers.

`tools/scenario_trace_summary.py --input EXISTING_R31 [--format json|markdown]`
has no output/data/policy/rounding/normalization options. No abbreviated flags.
Argparse/help before imports/input; help0, valid summary0, validation/usage/IO2.
Validation failures have empty stdout and `REJECTED: <safe code>` stderr, no
traceback; normal valid stderr empty. Build complete bytes before stdout writing.
CLI uses a cold private temporary pycache prefix, restored in finally; no source/
input writes or repair. Ordinary stdout write failures are IO errors, not an atomic
publication promise. Direct API caller controls its interpreter/cache lifecycle.

## Verification and preservation

Use existing committed sign/resumed/layout fixtures, not new model invocations.
Literal sign: driver numeric0/representation4, rate numeric4/representation4,
rate-to-limited0, fault0, counter-reset0; old inactive-change1. Resumed index5:
driver numeric0/representation1, rate numeric1/representation1, fault first5,
active suppression1 even though final command=-2. Add coherent resealed records
for int64-vs-float precision, signed zero and counter resets; label them not new
model runs. Invalid late rows/gates/Manifest/files/paths fail before output.
4096-row layout accepted, no model/NumPy/native imports; metadata paths inert.

Fresh baseline883 tests/231compiles/static/wheel; task-focused RED/GREEN and full
component suite at each task, full gate/static/234compiles at finish, exact frozen
wheel SHA3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Actual saved R69 cases via new JSON/Markdown CLI, repeated/deterministic outputs,
input/source preservation and independent literal validation. One fresh whole-branch
review, one Critical/Important TDD fix pass if needed. Local branch only; no push/
PR/main merge/HF writes/CI dispatch or new model work during actual summary acceptance.
Full unit/gate synthetic work remains NONZERO_NOT_AGGREGATED.

Keep host-owned linked worktree, all existing evidence and this task workspace/
ledger; preservation overrides skill scratch cleanup. Packaged bookkeeping scripts
are unavailable; explicit briefs/BASE/logs/external ledger substitute without
skipping any test. R_BUDGET UNRESOLVED, Static Gate FAIL, actualr/T2/scale null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN and F70UH/V/F71/activation NOT_ALLOWED.
