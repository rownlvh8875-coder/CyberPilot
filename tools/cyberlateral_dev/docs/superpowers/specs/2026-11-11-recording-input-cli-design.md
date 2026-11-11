# CORE61 — Explicit saved complete-synthetic-input diagnostic CLI

## Intent and choice

Make the integrated CORE58 complete-input diagnostic usable from a command without
manually writing a Python caller. The user's standing choice delegates offline
implementation decisions and opts out of repeated design approvals. The CLI and
its precise shape below are the author's choice, not a new user policy approval.

Approaches considered: another pure projection API leaves file capture/manual
execution to each caller; a complete save/report workflow adds publication and
result-reader contracts; one explicit read-only CLI connects the existing API to
a bounded file and stdout. Choose the last, retaining the existing Python3.12,
stdlib, unittest and scoped static checks; no dependency or installed wheel change.

## Input, execution and filesystem contract

`integration_tools.recording_input_run.run_recording_input(input_file: Path,
expected_sha256: str) -> dict` validates an exact64 lowercase-hex external digest
before path access. It accepts one regular nonsymlink file, no symlink ancestors,
captured once with read-only/no-follow/nonblocking/close-on-exec flags. Empty and
over1048576bytes reject. Bound both fstat size and actual read to cap+1, close the
descriptor on every path, hash the captured bytes, and reject mismatch before
calling unchanged CORE58 `check_serialized_recording_input(raw)` exactly once.
No format guessing, normalization, retry, reopen after checking, write or temp/cache
allocation. Path checks are cooperative, not protection against a hostile racing
filesystem. SHA authenticates neither origin nor the contents of the later path.

`tools/recording_input_diagnostics.py` requires exactly one each of `--run`,
`--input-file` and `--expected-sha256`. Abbreviations, duplicates, missing/empty
values, invalid digest syntax and unknown flags reject before project imports or
input access. Help executes no model. No defaults, stdin, policy/context overrides,
actual/log source readers, output paths or alternate formats.

## Output

One canonical JSON stdout record using existing scenario_output.canonical:
schema_version1, contract_id CORE61_COUNTERFACTUAL_RECORDING_DIAGNOSTICS_V1,
scope DECLARED_SYNTHETIC_INPUT_DIAGNOSTICS_ONLY, input_sha256, input_bytes,
status MATCH/DIFFERENT, frame_count, checked_transition_count,
new_synthetic_model_steps, differing_transition_indices, rows, validation_claim,
state_feed_rule, first_frame_transition_checked, prehistory_checked,
source_identity_reauthenticated, v4_payload_allowed, f61_input_allowed,
actual_activation_allowed, and a copy of existing GATES.

Each row contains transition_index, model_index, status, declared_entry_state,
computed_next_state, declared_saved_state(saved_limited_state/saved_angle_counter),
and all differences(field/declared/computed). State records retain all four int
fields: index, previous_requested, previous_applied, angle_counter. Rows are a
diagnostic projection, not a lossless input/result codec, source certificate,
first-anchor/prehistory proof, computed-state rollout or an independent math oracle.
Input words/floats/int64 timestamps remain in the captured canonical source;
the command does not turn them into elapsed seconds, dt or rate policy values.

Valid N frames execute N-1 synthetic model steps and retain every adjacent
diagnostic even after DIFFERENT; each step uses declared entry state. Entire
wire/semantic preflight rejects before any model prefix, as existing CORE58 does.
No model arithmetic, codec schema, API, validation or exception semantics change.

## CLI outcomes and process boundaries

MATCH exit0; DIFFERENT exit1. Input/usage/operation/execution/output failures exit2
with no success record. Expected pre-execution path/size/SHA/codec/preflight errors
produce their fixed code; other failures use
RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO. Never print raw exceptions,
paths or caller data. Late model/serialization/stream failure may follow work.
Build the complete <=1048576byte output before writing it; use complete positive
short writes, stop on nonpositive/error without retry or model re-execution.
A partially written stdout prefix cannot be retracted; exit2 is not a valid receipt.
Diagnostic-stream failure must not turn failure into success.

Suppress cold parser/project bytecode from main entry and restore sys.path and
sys.dont_write_bytecode on success/help/usage/error. Do not alter cache-prefix,
temporary-directory settings or environment. CLI process-scope manipulation is
cooperative/single-threaded; no hostile dependency/process sandbox is promised.

## Verification and non-goals

44 failing tests before implementation, then44PASS with real model counters,
literal3states(6,8,2,5)/(7,-8,-2,6)/(8,4,2,7), all rows after a difference,
bounded single capture, preflight0steps, late failure uncertainty, cold/stream/
process boundaries and actual subprocess CLI. Prior2089tests plus44 =>2133,
349 own compiles, static/98Manifest and fixed wheel/CORE32 pins unchanged.
One fresh branch reviewer; author disposition; reproducible evidence. Local commits
only; no publication/main integration/CI in this task. No format or numerical policy
changes, F61 execution, actual data, Controller/Runtime/CAN/install/deploy.

Actualr/T2/scale=null; R_BUDGET UNRESOLVED; Static Gate FAIL;
SOURCE_SCHEMA_UNQUALIFIED6000; Candidate/Runtime NO_GO; D2 PERFORMANCE_NOT_EVALUATED;
F19 LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY NOT_PROVEN; F70UH/F70V/F71 NOT_ALLOWED.
Full DEV synthetic/model/reference/numeric work is nonzero, not aggregated.
