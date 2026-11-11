# CORE64 — Saved complete-synthetic-input diagnostic publication

Author-selected next offline deliverable under the user's sequential-execution
delegation. No new policy approval is inferred. Existing Python3.12/stdlib/dev-tree
commands remain; no dependency, wheel, codec, model or CORE61 API change.

## Choice and scope

Shell redirection leaves overwrite/partial-result handling to callers. Extending
CORE61's strict stdout command breaks its no-file contract. Choose a separate
API and explicit save CLI, reusing the tested CORE16 exclusive publisher. The
saved diagnostic plus checksum is the deliverable, not another result-reader or
report system. No input copy: caller retains the original SHA-pinned source.

## API and files

`integration_tools.recording_input_workflow.publish_recording_input(input_file:
Path, expected_sha256: str, output_root: Path) -> dict` checks exact64lowercase SHA
syntax before any caller path work. Reuse CORE16 `_output` to reject existing,
symlink, missing-parent or checkout output before model execution. Then call
unchanged CORE61 `run_recording_input` exactly once; no recapture/retry/replay.

Serialize the complete result with unchanged `scenario_output.canonical` to
`DIAGNOSTICS.json`, 1..1048576bytes. `SHA256SUMS.txt` contains exactly its lowercase
SHA, two spaces, filename and newline. Construct all files and the receipt before
mkdir. Unknown status, serialization or size failure creates no output folder,
but may follow model work. `_publish` creates one new external folder (requested
0700), exclusive files (requested0600), handles short writes, verifies exact layout
and bounded readback. Reuse its error codes. Do not delete or retry partial output.
No fsync/durability, atomic multi-file transaction or hostile-race promise.

Receipt: schema_version1, contract_id CORE64_RECORDING_INPUT_WORKFLOW_V1,
status RECORDING_DIAGNOSTICS_PUBLISHED, diagnostic_status MATCH/DIFFERENT,
diagnostic_exit_code0/1, input_sha256/input_bytes/frame_count/
checked_transition_count/new_synthetic_model_steps/differing_transition_indices,
files{name:{sha256,byte_size}} for both files, original false authority flags,
validation_claim/state_feed_rule, gates, scope
DECLARED_SYNTHETIC_DIAGNOSTIC_PUBLICATION_NOT_ORIGIN_OR_VEHICLE_PROOF.
No path/date/random field: identical inputs at distinct destinations yield equal
files and receipts. Receipt is a publication summary, not the F61 constructor.

## CLI

New `tools/recording_input_workflow.py` requires exactly once each `--run`,
`--input-file`, `--expected-sha256`, `--output-root`. Reject abbreviation,
duplicate/missing/empty values, malformed SHA and unknown flags before project
imports or caller filesystem access; help executes no model. No defaults/stdin/
context/rate/dt overrides. MATCH0, DIFFERENT1 after successful publication;
all failures2. Emit complete canonical receipt on stdout, fixed codes only on
stderr; use complete short-write handling. Generic failure code
RECORDING_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_WORK_MAY_BE_NONZERO; usage
RECORDING_WORKFLOW_USAGE_NO_MODEL_EXECUTION. Never retry model or publication.
Partial stdout cannot be retracted; exit2 is not success even if files exist.
Restore sys.path/dont_write_bytecode on all main paths; no cache/temp writes.

## Verification and boundaries

Test real API/CLI with independently literal three-row MATCH and early DIFFERENT
fixtures, N-1 actual public model steps, input unchanged and single capture;
bad digest, malformed/late semantic input and existing/invalid destination0steps;
serialization/size/publication/readback/stream failures with honest work/partial
custody; exact two files/manifest/private modes/no overwrite, deterministic fresh
processes, parser/help/cold import suppression and process-global restoration.
Unchanged full DEV plus new tests, statics/compile/98Manifest/wheel/CORE32 pins;
fresh final review and author disposition, two deterministic evidence builds.
Keep old CLI/model/math/source config and primary checkout unchanged.

All actual input/capture/Controller/Runtime/CAN/F61/actual dt/r/install/deploy0;
actualr/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL, actual activation and
F70UH/F70V/F71 NOT_ALLOWED. Full synthetic/model/reference/numeric work NONZERO
NOT_AGGREGATED. A saved MATCH is not source/anchor/prehistory/vehicle authority.
