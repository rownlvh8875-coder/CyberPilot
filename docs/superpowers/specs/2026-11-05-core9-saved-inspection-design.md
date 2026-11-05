# CORE9 — Read-only Saved Sequence Inspection

## Intent and author-selected approach

Read a saved CORE8 three-file package, check captured-byte integrity and consumed
record relationships, and summarize without importing/running the model or the
CORE5~8 execution path. Owner delegated native offline development and opted out
of repeated routine questions. Choose bounded owned-byte inspection with JSON/
Markdown stdout. Bare checksum display would miss internally inconsistent rows;
replaying the model would answer a different question and is prohibited here.

Inspection success is separate from saved outcome: intact MATCH, DIFFERENT and
REJECTED packages all yield CLI exit0 with saved_status explicitly retained.
Invalid package/arguments/operational errors yield exit2 and no summary. A stored
MATCH is never labeled a fresh model result, source proof or vehicle approval.

## Files and APIs

New integration_tools/core_sequence_record.py: InspectError(ValueError).code and
validate_records(input_record:object,result_record:object)->dict, stdlib-only
record consistency plus inert CASE_IDS and unchanged GATES/canonical imports.
New integration_tools/core_sequence_saved.py: inspect_saved_sequence(Path)->dict,
format_saved_sequence(Path,output_format:str='json')->bytes. New
tools/core_sequence_inspect.py: --input required folder, --format json|markdown
(defaultjson), allow_abbrev=false, stdout only, no --output or execution option.
New project/test_core_sequence_saved.py and Korean usage guide. Existing producer,
CORE1~8, model/wheel/loader/locks/workflows/source profiles unchanged.

## Capture and parsing boundary

Linux existing CPython3.12.13 environment; no installs/network. Require Path and
UTF8/noNUL, reject symlink root/parents, missing/not-directory path. Open directory
with O_DIRECTORY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC; require exactly INPUT.json,
RESULTS.json,SHA256SUMS.txt and no other file/subdirectory. Open only those fixed
names once relative to directoryfd with O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC;
fstat regular-file before reading, caps INPUT65536/RESULTS524288/Manifest512bytes,
bounded readcap+1. No write/create flags, following links, recursive scan, model
source lookup, untrusted manifest member traversal or reopening captured files.
Recheck directory name set; this is cooperative captured bytes, not atomic whole
filesystem attestation or hostile-race/bind-mount sandbox.

Manifest must equal exactly the sorted two SHA256 lines for captured INPUT and
RESULTS with newline; do not resolve names supplied by the Manifest. Parse JSON
only after checksum success: strict UTF8, duplicate keys rejected, depth<=64,
integer token length<=32, float tokens/NaN/Infinity rejected (CORE8 stores numeric
float data as hex strings). Canonical sorted compact ensure_ascii=false/newline
bytes required. Invalid Unicode/surrogates/recursion/JSON errors get fixed codes.

InspectError codes: INSPECT_INPUT_FILE(path/open/nonregular), INSPECT_FILES(name
set), INSPECT_SIZE(cap), INSPECT_CHECKSUM(Manifest), INSPECT_JSON(syntax/resource
grammar), INSPECT_CANONICAL(valid noncanonical JSON), INSPECT_RECORD(top/input
shapes/gates/metadata), INSPECT_ROWS(row/state/difference/aggregate relations),
INSPECT_FORMAT(unsupported format, before reading input). No raw values or paths
in diagnostic message. Unexpected API exceptions propagate; CLI handles ordinary
Exception with fixed INSPECT_OPERATION_FAILED/exit2, not SystemExit/KeyboardInterrupt.
CLI may use an empty private cache prefix/restores it like existing tools; no
persistent output/cache/input writes. Caller shell redirection is outside the API.

## Record consistency (not input qualification or arithmetic replay)

Input top exact keys schema_version,contract_id,scope,case_id,frames,contexts.
Result exact keys from CORE8: schema_version,contract_id,scope,case_id,status,
rejection_code,sequence_completed,frame_count,declared_transition_count,
completed_transition_count,model_steps,differing_transition_indices,rows,identity,
gates,validation_claim,anchor_transition_checked,prehistory_checked,source_authenticated.
Exact built-in types; schema1, known CORE8 contract/scope/CASE_IDS, matching case
ids, frames4/contexts3, counts4/3. No case->outcome arithmetic inference.

Frame exact fields per CORE8 projection. Request exact fields include context,
sequence,sample_time_ns,requested_binary32_be_hex,request_active,request_override,
reset_since_previous. Context is a dict with expected CORE3 keys/declared labels,
builtin IDs/ints; equal contexts, adjacent capture sequence and strictly ordered
int64 times checked. Raw request is eight lower-case hex characters, not decoded
to native. Settings exact7int fields, synthetic bounds/scales equality/stability;
limited states[-2048,2048],counters[0,90],known stage/origin,exactbool gate/flags,
inactive saved0. Previous saved/current entry links checked. These checks do not
authenticate origin, qualify actual input or recompute limiter/native/dt/r.

Aux contexts exact CORE8 fields scope,model_index,previous_integer_request,
current_driver_hex,current_angle_deg_hex; declared scope, index1..4095 consecutive,
previous request boundedint, bounded hex-float string syntax only (no decoding or
quantizer). Intentionally invalid stored0.1 driver remains viewable in REJECTED.
Identity only requires dict/model_version='0.3.0'/CLI SHA64; it is stored metadata,
not checked against current source or used as provenance. Other identity content
is opaque bounded JSON. Gates canonical exact equality to unchanged closed GATES;
all three authority flags exact false, validation_claim exact CORE7 string.

For completed status MATCH/DIFFERENT: sequence_completed exacttrue,model_steps/
completed_count3,rows3,rejectionNone. Each row exact transition_index,status,
model_index,entry_state,computed_next_state,declared_saved_state,differences.
State exact4int fields: index,previous_requested,previous_applied,angle_counter;
bounds as CORE8, entryindex=modelindex=contextindex, nextindex=entry+1. Entry
previous_requested equals stored auxiliary value, applied/counter match current
frame entry; saved dict equals current frame saved values. Reconstruct differences
only by comparing those stored saved ints to stored computed ints, fixed field
order; require exact list/row status, aggregate indices and status. Adjacent stored
next.previous_requested equals next entry.previous_requested; do not feed computed
applied/counter into the next declared entry (DIFFERENT remains diagnostic).

For REJECTED: exactfalse completion, modelsteps/completed_count0,rows=[],indices[],
ASCII bounded known-preflight code SEQUENCE_INPUT:<0..2>:MODEL_* or MODEL_ORDER:
<1..2> or TYPE/CONTAINER/COUNT. Never accept SEQUENCE_TRANSITION:* as zero-work
rejection. No rows/partial prefix turned into success. No recomputation that this
specific saved rejection or computed command is true. Coordinated changes to
data and its checksums may be self-consistent without being authentic/correct.

## Summary and formatting

schema_version1,contract_id CORE9_SAVED_SEQUENCE_INSPECTION_V1,
inspection_status=SAVED_RECORDS_CONSISTENT,case_id,saved_status,
saved_rejection_code,recorded_model_steps,recorded_transition_count,
differing_transition_indices,rows (transition_index/status/modelindex, declared/
computed command/counter and original validated differences),captured_sha256 for
all3files,gates,inspection_model_executions=0,inspection_reference_executions=0,
source_identity_reauthenticated=false,anchor_transition_checked=false,
prehistory_checked=false,integrity_scope=CAPTURED_BYTES_CHECKSUMS_AND_RECORD_RELATIONS_NOT_ARITHMETIC_OR_ORIGIN_PROOF.
No input/workspace path/timestamp in summary. Markdown clearly labels stored
outcome, new model/reference0, differences and limits. No fresh MATCH claim.

## Tests and preserved gates

TDD real saved fixtures from unchanged CORE8 producer for setup (separate nonzero
synthetic work), then inspection read-only/zero-model in fresh forbidden-import
processes; API/JSON/Markdown/all3saved outcomes exit0, mutation/source bytes/mode
preserved, corruption/extra/missing/symlink/FIFO/oversize/traversal/duplicate/NaN/
deep/noncanonical/record bool/count/difference/gate/claim/late-error rejection,
coordinated internally consistent forged data explicitly not arithmetic-authenticated.
No model imports/checker/quantization/dt/r/native conversion in inspector. One
fresh whole-branch review, independent real historical CORE8 packages twice,
source/Manifest/ref/cloudconsumer verification, baseline1089tests/252compiles,
final1089+actual new tests/256compiles/static/frozenwheel.

Base900fc12fd634e4b71b437c57619aa50c763f0fe7. Frozen wheel
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.
Host linked worktree/local stacked branch, no push/merge/PR/CI/HF/network/cleanup.
Preserve old refs/evidence. Actual r/T2/vehicle_scale=null; R_BUDGET=UNRESOLVED;
STATIC_EVIDENCE_GATE=FAIL; SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY=NOT_PROVEN;
F70UH/F70V/F71/actualactivation=NOT_ALLOWED; actual inputs/F61/Controller/Runtime/
CAN/actualr calculation0. Entire unit/gate/setup synthetic work remains nonzero.
