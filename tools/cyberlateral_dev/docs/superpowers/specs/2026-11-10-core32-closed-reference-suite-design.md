# CORE32 — one explicit closed reference regression command

Builder-selected next increment under standing offline delegation. Existing six audited cases
are useful but require separate API calls; add one bounded regression entry point, not more
arithmetic. Alternatives: generic case selection/external replay (unneeded intake), another
saved-byte report (does not run regression), or fixed six-case orchestration (selected).

## Contract

`run_reference_suite() -> dict` in integration_tools/core_reference_suite.py runs, exactly once
and in this order: CORE30/sign-cycle,declared-difference,late-invalid; CORE31/inactive-resume,
fault-reset,rounding-ties. Reuse unchanged audit_rollout_case/audit_boundary_case. No args,
new arithmetic/vectors, policy values, arbitrary input or output-folder writes.

Retain a detached deep copy of each complete owned audit receipt. Validate its fixed exact
field set/types, schema/contract/case/scope, audit status/code/count/detail consistency,
observed status/code (CORE31 cannot REJECT), source reference ID/SHA, input-identity shape,
reference model0, nonzero-preflight marker, denial flags false and exact-type unchanged GATES.
This is a versioned contract boundary on trusted internal receipts, not an arbitrary-object
validator/sandbox/source authenticator. In-process hostile mutation/concurrent globals are excluded.

MATCH audit must report expected model counts3/3/0/3/4/6 and baseline observed statusM/D/R/M/M/M.
DIFFERENT audit may contain a changed observed M/D status and nonnegative reported step count;
do not silently claim those counters are independently measured. Keep underlying full receipts
and their256-path cap/truncation semantics. No new flattened detail list or lost difference counts.
Audit mismatch is normal regression information: continue all six and aggregate it. Unexpected
exception/malformed receipt stops immediately with fixed case-qualified
REFERENCE_SUITE_CASE_FAILED/RECEIPT_INVALID:<group>:<case>:WORK_MAY_BE_NONZERO;
return no partial success. BaseException propagates; no retry/fallback. Reference verification
occurs per unchanged backend, not as an atomic all-case preflight; later failure can follow work.

Suite contract CORE32_CLOSED_REFERENCE_SUITE_V1: execution_requested=true, all_cases_processed,
case_count6, ordered reports {group,case_id,report}, audit_counts MATCH/DIFFERENT,
observed_rollout_counts MATCH/DIFFERENT/REJECTED, sum of difference_count and reported detail
count, any truncation, reported_synthetic_model_steps, expected_reference_model_steps0,
reported_work_is_runtime_attestation=false, numeric_preflight_work NONZERO_NOT_AGGREGATED,
denial flags false, unchanged gates and closed scope. Status CLOSED_REFERENCE_SUITE_MATCH/exit0
iff all audits match, otherwise CLOSED_REFERENCE_SUITE_DIFFERENT/exit1.
Normal observed counts4/1/1 and reported model19 are not overall test/stage execution totals.

CLI tools/core_reference_suite.py accepts exactly one --run only. No selection/input/output/
policy/format flags, abbreviations, duplicates or positional args. Parse/help before project
imports/reference/numeric work. --help0, syntax2/REFERENCE_SUITE_USAGE_NO_MODEL_EXECUTION.
Valid run emits canonical JSON; return suite0/1 after validating owned status before stdout.
Known errors retain fixed code; other/output errors2/REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO.
Guard bytecode from parser through output and restore sys.path/flag in finally including
BaseException. Complete descriptor short writes; failed help/stderr/stdout cannot be successful.
Partial stdout is not retractable; consumers must check exit/full JSON. Caller shell redirection
and initial imports are outside custody; use -I -B. API reads refs but writes no files/temp.

## Scope/proof

Seven new files: API,CLI,two test files,Korean guide,spec,plan. Only old README/backlog/CORE31
guide links change. Existing CORE30/31/model/vectors/helpers/old CLIs/wheel remain byte-identical.
TDD real cases/mutations, contract fault injection, prefix/error/output boundaries, cold no-cache/
temp/write guard, exact preserved receipts/counts/determinism. Fresh complete DEV gate, independent
two-run acceptance using prior sealed expected receipts, source/ref custody and one fresh review
precede unsigned evidence seal. No browser UI changed; no visual PASS claimed.
Actual r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,SOURCE_SCHEMA_UNQUALIFIED6000,
Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/V/F71 NOT_ALLOWED. Original F61/actual inputs/Controller/
Runtime/CAN/actual r/dt0. Synthetic work explicitly nonzero. No merge/push/PR/CI/HF writes.
