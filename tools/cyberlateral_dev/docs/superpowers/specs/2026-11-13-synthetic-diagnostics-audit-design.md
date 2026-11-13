# CORE68 — Audit saved diagnostics against supplied synthetic input

## Intent and decision

CORE66 checks stored relations but can accept consistently forged arithmetic. Add an
explicit synthetic recomputation against the caller's SHA-pinned complete CORE55
input and compare the entire CORE61 diagnostic record. This is the author's next
development choice under the user's standing instruction to continue without
approval questions; it is not a new user-supplied product requirement.

Approaches considered: another saved-only comparison cannot test arithmetic;
an independent new oracle duplicates already qualified arithmetic and broadens the
task; reuse current CORE61 calculations to detect changed saved records. Choose the
third. It proves reproduction by the current algorithm, not an independent oracle,
authenticated original source, whole-controller parity or actual vehicle readiness.

## API and ordering

`audit_recording_diagnostics(input_file: Path, input_sha256: str,
diagnostics_root: Path, diagnostics_sha256: str) -> dict` lives in
`integration_tools/recording_diagnostics_audit.py`.

Validate both lowercase64 SHA strings before caller-path work. Inspect the saved
two-file package once using unchanged CORE66. Reject a declared input-SHA mismatch
before opening the input. Capture the input once using existing CORE61 bounded
regular-file logic; verify its actual SHA and declared input byte size before any
model step. Call a factored private `_diagnose_captured(raw: bytes) -> dict` in
`recording_input_run.py`. Preserve existing CORE61 output/errors and full-input
preflight before its N-1 synthetic steps. Never reopen either captured artifact.

Both inputs must be complete valid synthetic formats. Corrupt saved structure,
invalid input/semantics and input identity mismatch are errors, not comparison
results. Whole-input preflight rejection executes zero model steps. Later execution
or output failure may have performed nonzero work and must retain that distinction.

## Result and command

Return canonical-data record contract `CORE68_SYNTHETIC_DIAGNOSTICS_AUDIT_V1`:
`audit_status=REPRODUCED|DIFFERENT`, `audit_exit_code=0|1`, both full
`stored_record` and `recomputed_record`, separate saved/recomputed diagnostic status,
input and diagnostic SHA/byte sizes, `differing_header_fields` (sorted, excluding
rows) and `differing_transition_indices` (ascending, including absent rows).
Compare via existing canonical serialization to preserve exact JSON types.

Report recorded model work separately from `new_synthetic_model_steps=N-1`,
`new_reference_steps=0`, `arithmetic_recomputed=True`,
`supplied_input_bytes_verified=True`, `independent_numerical_oracle=False`.
Keep all six CORE66 authority flags false, actual gates unchanged and numeric
validation work `NONZERO_NOT_AGGREGATED`. Valid saved DIFFERENT reproduced exactly
is audit REPRODUCED/exit0, with its diagnostic DIFFERENT preserved.

New developer-tree CLI `tools/recording_diagnostics_audit.py` requires exactly one
each of `--run`, `--input-file`, `--expected-input-sha256`,
`--diagnostics-root`, `--expected-diagnostics-sha256`. No abbreviations or policy
overrides. Parse and validate SHA syntax before project imports. Emit one complete
canonical JSON bounded to2097152bytes, exit0/1 by audit result, exit2 for errors.
Fixed error codes only; no caller path/exception text. Complete positive short
writes; on failure do not retry the audit or retract output prefix. Restore sys.path
and bytecode settings. No file/cache/temp writes or automatic deletion by the CLI.

## Constraints and acceptance

Python3.12.13/Linux development tree; existing dependencies only. Existing public
wheel, model arithmetic, CORE55/61/64/66 contracts and time semantics unchanged.
Declared entry feed stays declared; no computed-state repair or first-anchor replay.
Reading a supplied SHA-pinned input is byte identity, not origin authentication.
Source and inputs may change after capture; no hostile-race or atomic-snapshot claim.

Accept with test-first literal fixtures covering exact replay, true saved DIFFERENT,
consistent forgery, wrong input SHA/size, malformed/late-invalid input, full preflight,
single bounded read-only capture, no new authority, CLI execution opt-in, output
failures and old CORE61/64/66 regression. Run the full DEV gate and static checks;
review the entire branch independently before normal publication. Record actual
counts, pins and all failures. Full suite synthetic work is nonzero and unaggregated.

R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/scale=null,
Candidate/Runtime=NO_GO, F70UH/F70V/F71 and actual activation NOT_ALLOWED.
Actual input/capture/Controller/Runtime/CAN/F61/actualdt/r/install/deploy=0.
