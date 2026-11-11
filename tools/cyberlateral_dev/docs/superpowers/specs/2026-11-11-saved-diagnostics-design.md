# CORE66 — Read-only saved recording diagnostic inspection

Author-selected next offline step under the user's standing native/sequential
execution delegation. Retain Python3.12/stdlib/unittest and the existing isolated
checkout. No dependency, installed wheel, model, codec or producer change.

## Choice and intent

Shell checksum alone does not check stored row/summary relations; rerunning CORE61
would add model work and depend on the separately held input. Choose a new saved-only
API/CLI that checks the two CORE64 files without input capture or model execution.
It is a small read-only feature, not a new report/persistence/replay subsystem.

## API and capture

`integration_tools.recording_diagnostics_saved.inspect_recording_diagnostics(
input_root: Path, expected_sha256: str) -> dict` requires an exact64lowercase-hex
external SHA for DIAGNOSTICS.json before any caller path access. Accept only a
directory containing exactly DIAGNOSTICS.json and SHA256SUMS.txt, regular files,
no symlink root/ancestors/members. Reuse CORE18 `_directory`/`_read_file` for
one read-only/no-follow/nonblocking/close-on-exec capture per file; caps1048576/512.
Check both reported and actual read size. Require root inode/device still matches
the open directory before closing it; close descriptors before parsing. No reopen,
write, extraction, temp, retry or model/reference/producer imports. Cooperative
ordinary filesystem checks, not atomic bytes or hostile-race authentication.

Hash captured DIAGNOSTICS bytes against the external SHA, then require the exact
manifest `sha + '  DIAGNOSTICS.json\n'`. Reuse CORE9 `_parse`: UTF8, canonical
JSON, duplicate-free, no float/nonfinite tokens, bounded integer tokens/depth.
Captured records and hashes do not authenticate later path contents or origin.

## Exact saved schema/relations

The accepted schema is unchanged CORE61 output, not its input schema. Exact key
sets; schema_version built-in int1; contract/scope/validation_claim/state_feed_rule
exact literals from the producer; syntactic declared input SHA and input_bytes
integer1..1048576. Header authority flags must be exactFalse and GATES exact-typed
canonical equality to unchanged GATES, including null actualr/T2/scale.

frame_count int2..128; checked_transition_count/new_synthetic_model_steps both
exact int(frame_count-1); rows list that length. Each row has exact keys
transition_index,model_index,status,declared_entry_state,computed_next_state,
declared_saved_state,differences. Ordinal equals position, model_index int1..4095
and adjacent+1. Entry/computed state keys index/previous_requested/
previous_applied/angle_counter; command fields built-in ints[-2048,2048], counter
int[0,90], entry index=model_index, computed index=model_index+1 (max4096).
Saved command/counter have the same domain. Adjacent entry applied/counter equal
the previous DECLARED saved state, not its computed state; adjacent entry requested
equals previous computed requested. These are recorded relations only.

Differences are exactly the ordered saved-command/counter versus computed values
which differ, with exact keys/typed integers. Derive row MATCH/DIFFERENT, ordered
differing_transition_indices and total status from those stored comparisons.
Never recompute arithmetic, repair declarations, infer missing fields, bind input
bytes, verify source identity or first-anchor/prehistory. An internally consistent
forgery with recomputed hashes can pass; test and document that limit.

## Inspection receipt and CLI

Return schema_version1, contract_id CORE66_SAVED_RECORDING_DIAGNOSTICS_INSPECTION_V1,
inspection_status SAVED_DIAGNOSTICS_CONSISTENT, inspection_exit_code0,
saved_status, saved_diagnostic_exit_code0/1, diagnostics_sha256/diagnostics_bytes,
recorded_model_steps, new_synthetic_model_steps0, new_reference_steps0,
numeric_validation_work NONZERO_NOT_AGGREGATED, stored_record unchanged,
arithmetic_recomputed/original_input_verified/source_identity_reauthenticated/
first_frame_transition_checked/prehistory_checked/v4_payload_allowed/
f61_input_allowed/actual_activation_allowed exactFalse, copy of unchanged GATES,
scope CHECKED_CAPTURED_SAVED_RELATIONS_NOT_NUMERICAL_OR_ORIGIN_PROOF.
The old new_synthetic_model_steps inside stored_record is historical; top-level0
is this inspection's work. No elapsed-time/rate policy is inferred.

New `tools/recording_diagnostics_inspect.py` requires exactly once --input-root
and --expected-sha256, no --run/default/stdin/format/output/context/rate override.
Reject missing/empty/duplicate/abbreviated/unknown options and malformed digest
before project imports or caller path work. Valid saved MATCH AND DIFFERENT exit0;
all inspection/usage/output failures exit2. Canonical complete stdout <=2097152bytes
before writing; positive short writes complete, nonpositive/error stops, no retry.
Partial stdout cannot be retracted; exit2 is not a valid success receipt. Fixed
codes only, no caller paths/raw exceptions. Restore sys.path/dont_write_bytecode
on all main paths and suppress cold imports. No files/cache/temp writes.

Errors: SavedDiagnosticsError with SAVED_DIAGNOSTICS_EXPECTED_SHA256, _INPUT,
_CHECKSUM, _JSON, _RECORD, _ROWS. CLI usage
SAVED_DIAGNOSTICS_INSPECT_USAGE_NO_MODEL_EXECUTION; generic failure
SAVED_DIAGNOSTICS_INSPECT_FAILED_NO_MODEL_EXECUTION. Known errors retain their code.

## Verification/boundaries

Test literal saved records independently of the new producer, real CORE64 saved
output compatibility, checksums/schema/typed booleans/state roles/counts/differences,
single bounded capture/FD closure/path replacement/readonly custody, max127rows,
strict/cold CLI and stdout failure paths, no forbidden producer/model imports,
zero new model/reference work, independent deterministic processes. Full existing
DEV+actual new method count,355 own compiles,98Manifest and unchanged wheel/CORE32
pins; fresh final review and two deterministic evidence ZIPs with separate checks.
Preserve743 baseline sources outside the8scope, main/config/primary/history/evidence.

Actualr/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,Candidate/Runtime NO_GO,
SOURCE_SCHEMA_UNQUALIFIED6000,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,F70UH/F70V/F71 NOT_ALLOWED. Actual input/capture/
Controller/Runtime/CAN/F61/actualdt/r/install/deploy0. Whole unit/gate synthetic/
model/reference/numeric work NONZERO_NOT_AGGREGATED, not the new inspector's0steps.
