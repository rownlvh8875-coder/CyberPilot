# R17 — read-only fixed synthetic handoff audit tables

## Intent and delegated choices

Make the verified R16 source→prepared→owned state→output chain inspectable in
CSV, canonical JSON and a Korean summary without rerunning extraction/model.
User delegated ordinary next-step choices, inline work and existing Draft
feature publication. This choice is the author's, not a new vehicle approval.

Approaches: more lifecycle-only tests give no new inspection surface; a native
reader needs a separate still-closed qualification. Select a small stdlib-only
report over exactly the frozen-authority R16 artifact pair. It accepts no raw
logs, arbitrary record schema, model arguments, timestamps, r or vehicle input.
No HTML/browser/server/UI is added; CSV/JSON/Markdown are local data documents.

## Source and snapshot boundary

CLI: handoff_audit.py --first R16_DIR --second R16_DIR --output NEW_DIR.
Refactor the existing reader into read_lifecycle_pair(first,second)->(record,
summary). It reads each pair once, validates all existing canonical/hash/golden/
coverage/claim/gate checks, and returns that SAME validated in-memory snapshot.
Existing lifecycle_pair_summary remains a wrapper returning summary; old R16
output bytes stay unchanged. Never validate paths and then reread their payload
for reporting. Source identity in reports is the validated RESULTS SHA, not a
path, presumed original timestamp or atomic filesystem custody claim.

Existing output file/dir/dangling link rejects before input reading. Invalid
input rejects before creating output. Render complete bytes before directory
creation. Write non-marker files and checksum first, publish AUDIT.json last;
failure leaves no designated successful report. No concurrent writer, hostile
filesystem race or crash-durability promise is made.

## Projection

Exactly seven scenarios and112 rows, scenario/catalog order then sample order.
Each row has37 named scalar columns, in this order:

scenario_id, offset, invocation_index, sequence_id, seed_origin,
source_request, source_request_hex, lat_active, driver, driver_hex,
angle_deg, angle_deg_hex, STEER_MAX, STEER_DELTA_UP, STEER_DELTA_DOWN,
STEER_DRIVER_ALLOWANCE, STEER_DRIVER_FACTOR, STEER_DRIVER_MULTIPLIER,
previous_requested, previous_applied, angle_counter, quantized_integer,
driver_clip_result, rate_clip_result, limited_command, final_command,
normalized_expression, normalized_expression_hex, steer_request,
next_index, next_previous_requested, next_previous_applied, next_angle_counter,
source_result_sha256, custody_claim, precision_claim, time_semantics.

Copy numbers from the validated baseline frame/prepared/result, including
separate quantization/driver/rate/limited/final stages. Binary64 hex is a
representation only, not recomputation of any command. Preserve -0.0 in JSON/
CSV, print null explicitly (not blank), and keep bools as true/false. CSV uses
stdlib quoting and LF; its column order is fixed. Spreadsheet display may
coerce numbers: JSON and hex columns, not spreadsheet display, retain precision.
history-scale keeps REGISTERED_SYNTHETIC_SEED_NOT_OBSERVED_PREHISTORY; index1
must never become claimed observed prehistory. Time is invocation order only.

## Artifact contract and validation

Five files only: AUDIT.json (completion marker), audit.csv, SUMMARY_KO.md,
EXECUTION.json, SHA256SUMS.txt (covers the four other files). AUDIT contains
contract F70UGZ_R17_FIXED_HANDOFF_AUDIT_V1/status F70UGZ_R17_FIXED_HANDOFF_AUDIT_PASS,
scope, validated input_lifecycle_sha256, columns, rows, scenario summaries,
source_execution_counts9010 and separate report_execution_counts all0, gates.
Korean summary shows7 scenario rows/samples/cuts/seed/result hashes and makes
synthetic scope/zero report work/unresolved vehicle gates explicit.
EXECUTION records actual isolation and loaded forbidden modules, including the
model package. Installed report processes must be -I/-B with no model/native/
NumPy modules loaded. No source module selectors or executable original compile.

The verifier runs two report processes in the same new installed venv used for
that full verification, after its two R16 processes. Separate full local and
relocated verifications create separate venvs. Pair acceptance compares all
five files and exact source-derived rendered payloads/environment/checksums,
not labels/counts alone. Acceptance reuses projection to detect artifact drift;
it is NOT an independent mapping oracle. Tests independently check every field
of all112 rows against raw validated source dictionaries plus literal cases.

## Unchanged boundaries and completion

Package/API/wheel0.3.0, R14/R15/R16 producers, source/goldens/dependencies and
workflows are unchanged; the R16 reader refactor does not run models. Existing
authorized synthetic gates still run in full verification, including prior two
extracted helper bodies; zero report work does not relabel total test activity.
No actual input/native Q01-Q06/schema/Controller/Runtime/CAN/F61/r/dt/capture/
vehicle activation/install/deploy/main merge. Actual r/T2/scale=null;
R_BUDGET UNRESOLVED, Static Gate FAIL, Candidate/Runtime NO_GO, F70UH/V/F71
NOT_ALLOWED. No new independent arithmetic, malicious-authority authentication,
physical safety, persistent checkpoint or general replay claim.

TDD, full component/static/wheel gate, new archive/venv reproduction, one fresh
whole-branch review, then existing feature/Draft update and exact-HEAD dedicated
offline CI/artifact verification. All commits [skip ci], no legacy runtime CI.
Retain external audit evidence. Correct the prior deferred R16 environment
wording as documentation only; no new behavior/qualification is implied.
