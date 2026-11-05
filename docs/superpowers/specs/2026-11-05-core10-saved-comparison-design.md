# CORE10 — Read-only Saved Sequence Comparison

Owner delegated ordinary offline development and opted out of repeated questions.
Author selects native implementation on the existing Linux/CPython3.12.13 host,
no installs/network. Next deliverable is locating saved differences, not model
replay or vehicle/F61 policy work. Base7ad20857f4c07fbe79d4e82e3a93833b8d0f7133.

## Approaches and scope

Hash-only comparison is smaller but cannot locate input/result/identity changes.
Replaying CORE8 computes a new result and violates the no-new-execution scope.
Choose validated captured-record comparison with deterministic JSON/Markdown
stdout. This is the author's delegated choice, not a new Owner policy approval.
Keep CORE9 capture/parser/validator behavior and all prior model/producer bytes;
only factor its existing load operation to expose owned parsed records once.

## API and integration

In integration_tools/core_sequence_saved.py add
read_saved_sequence_records(input_path:Path)->dict with keys input_record,
result_record,summary; capture/checksum/parse/validate exactly once and return those
same owned records plus the unchanged CORE9 summary. inspect_saved_sequence(Path)
delegates to that summary; existing output bytes/errors unchanged. No raw files
reopen after verification. Tuple acceptance in direct CORE9 validator is a known
deferred minor, not fixed here; file intake remains builtin JSON containers.

New integration_tools/core_sequence_compare.py:
CompareError(ValueError).code; compare_saved_sequences(left:Path,right:Path)->dict;
render_comparison(comparison:dict,output_format:str='json')->bytes for records
returned by compare_saved_sequences (not an external summary intake API).
New tools/core_sequence_compare.py: required --left/--right, optional --format
json|markdown(defaultjson), allow_abbrev=false; stdout-only/no --output/--execute.
New project/test_core_sequence_compare.py, Korean guide, spec/plan;
component README/backlog updated. Total9changedpaths/3newPythonfiles expected,
owncompiles259(base256), registered533files/baseprior524preserved excluding3edits.

## Comparison meaning

Both sides must pass unchanged CORE9 validation. Wrap InspectError into fixed
COMPARE_LEFT:<INSPECT_CODE> or COMPARE_RIGHT:<INSPECT_CODE>; unexpected API errors
propagate. Invalid format COMPARE_FORMAT before renderer touches result. CLI
ordinary errors => REJECTED: COMPARE_OPERATION_FAILED/exit2; retain SystemExit/
KeyboardInterrupt semantics. Use direct descriptor write loop inside handler
as CORE9, no pending stdout buffer/shutdown-flush retry. Private temporary cache
prefix restored; stdout failure can leave delivered partial bytes, never success.

Compare all INPUT.json and RESULTS.json parsed fields including opaque identity;
do not compare only the lossy CORE9 summary. Ignore dict insertion order (canonical
input already sorts keys). Require exact types in equality: false !=0. Dict keys
sorted lexicographically; shared keys recursive, missing keys one subtree entry.
Lists positional by index (no model-index alignment/LCS); shared indices recursive,
extra tail element one subtree entry. Type mismatch yields one TYPE_CHANGED entry;
same-type unequal scalar VALUE_CHANGED. Missing keys/indices LEFT_ONLY/RIGHT_ONLY.
Each entry: path RFC6901 pointer rooted /INPUT.json or /RESULTS.json; section
INPUT,RESULT,IDENTITY(identity subtree under RESULTS); kind,left_present,
right_present,left,right. Missing value null with explicit presence flags, so null
is distinct from absence. Escape ~ as ~0 and / as ~1, preserve Unicode in JSON.
Do not decode numeric strings/words, infer limiter/native, compute dt/r, compare
against current source, infer cause, or treat a saved result as a fresh verdict.

Count every deterministic difference, but retain only the first256 entries.
Output difference_count,total section difference_counts,reported_difference_count,
differences_truncated explicit bool; compare status DIFFERENT whenever count>0,
even if detail truncates. Each side bounded by existing CORE9 file/depth caps;
whole traversal is bounded by those captured inputs, no recursive disk scan.
No field/path filter or silent ignored metadata. All valid case pairs permitted;
case mismatch is a recorded difference, not an assertion of comparability in physics.

## Result contract

schema_version1;contract_id CORE10_SAVED_SEQUENCE_COMPARISON_V1;
comparison_status SAVED_PACKAGES_IDENTICAL or SAVED_PACKAGES_DIFFERENT;
same_case_id bool;left/right metadata containing case_id,saved_status,
saved_rejection_code,recorded_model_steps,recorded_transition_count,captured_sha256;
differences/counts/truncation above;gates unchanged GATES;
comparison_model_executions0,comparison_reference_executions0;
source_identity_reauthenticatedfalse;arithmetic_recomputedfalse;
integrity_scope CAPTURED_RECORD_COMPARISON_NOT_ARITHMETIC_OR_ORIGIN_PROOF.
No caller paths/timestamps in portable results; preserved stored record data may
itself contain opaque paths/strings, not asserted authenticated or current.
JSON canonical unchanged helper. Markdown shows both saved outcomes/counts and
separate typed JSON-encoded code-span cells for paths/values; ensure_ascii=true,
JSON Unicode escapes for backtick/pipe/HTML delimiters preserve decoded values
while preventing active HTML/Markdown/control/bidi injection from opaque identity
keys/values. Review corrected the earlier insufficient HTML/entity-only strategy.
Local GFM consumer conversion is not a browser/visual claim; text stdout only.

CLI exit0 identical,exit1 different,exit2 invalid/operational. Saved DIFFERENT or
REJECTED self-comparison exits0 if records identical; no saved-status promotion.
No claim baseline is correct, difference improves performance, or sources match.
Captured consistency cannot authenticate coordinated forgeries. Cooperative
filesystem scope inherited: no atomic snapshot/hostile-race/atime/hardlink-origin
proof, directory enumeration not separately capped, Linux only. Same input path
is captured independently per side, no caching/equality shortcut.

## Verification and preserved boundaries

TDD old behavior/loader byte equality; identical/mirrored/same-path; three saved
statuses; full metadata/input differences absent from summary; exact bool/type,
missing/null,escaped pointers,deterministic positional ordering;>256 cap with full
counts; independently changed coherent packages are not arithmetic authenticated;
all case pairs; both-side corrupt/invalid/gate/row/symlink/FIFO/oversize rejection;
format-before-access; real CLI0/1/2/help/options/stdout device failure; fresh blocked
model/execution imports; exactly8read-only opens(directory+3 each)/no reopens;
oldinput bytes/modes/name preservation, canonical repeated output and Markdown safety.
Fixture creation uses unchanged CORE8 producer only for setup(nonzero); acceptance
uses historical packets with no new fixtures/model execution, two fresh repeats.
Baseline1116tests/256compile/static/frozenwheel then full1116+actualnew/259 PASS.
One fresh reviewer; one RED->GREEN Important/Critical fix pass, no rereview.
Source/Manifest/cloud consumer/local ref checks; local keep-as-is, no routine menu.

Frozen wheel3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
No push/merge/PR/CI/HF writes/deletion. Preserve host worktree/old refs/evidence.
Actual input/F61/Controller/Runtime/CAN/actualr calculation0. Whole unit/gate/setup
synthetic work NONZERO_NOT_AGGREGATED. R_BUDGET UNRESOLVED;Static Gate FAIL;
actualr/T2/vehicle_scale null;SOURCE_SCHEMA_UNQUALIFIED6000;Candidate/RuntimeNO_GO;
D2 PERFORMANCE_NOT_EVALUATED;F19 LEGACY_UNRESOLVED;NATIVE_EXACT_REPLAY NOT_PROVEN;
F70UH/F70V/F71/actualactivation NOT_ALLOWED.
