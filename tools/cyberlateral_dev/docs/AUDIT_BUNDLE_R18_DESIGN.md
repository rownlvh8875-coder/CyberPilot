# R18 — portable fixed synthetic audit evidence bundle

## Intent and delegated choice

Export the verified R16/R17 data as one deterministic ZIP that the owner can
save on a notebook and validate later using this repository's trusted stdlib
tools. No new model/extractor/F61/r/dt work. Routine next-step choices, inline
work and existing feature/Draft publication were delegated by the user; this
choice is the implementer's, not vehicle or source-authentication approval.

Alternatives: a loose copy leaves custody/file-list checks to the recipient;
an executable standalone verifier duplicates trusted code/authority into the
bundle. Select data-only ZIP plus repository-side verifier. It is portable
DATA, not standalone trusted authority, a signed certificate or an installer.

## Inputs and snapshot

Only exact fixed directories lifecycle_one/lifecycle_two (RESULTS.json and
SHA256SUMS.txt each), audit_one/audit_two (AUDIT.json, audit.csv, SUMMARY_KO.md,
EXECUTION.json and SHA256SUMS.txt each). Refactor R17 acceptance into
read_audit_pair(...)->(validated_record, validated_report_bytes, summary),
retaining audit_pair_summary's old return and all R17 output bytes.
Capture the SAME validated snapshot, never reread user paths after validation.
R16 canonical payload/manifest bytes can be reconstructed from this validated
record: existing canonical and checksum validation establishes exact identity.
Both pair copies are already required byte-identical. No raw logs/general
data intake, executable source, wheel, secrets or absolute source paths in ZIP.

Export sources are the trusted fixed full-verification directory, not a
general hostile-filesystem service; prior reader scope is unchanged. ZIP
verification treats archive bytes as untrusted and applies bounded checks.

## Deterministic archive

Exactly17 file members: the14 input files under their four fixed directories,
BUNDLE.json, README_KO.md and SHA256SUMS.txt. The archive manifest covers16
other members. Metadata includes contract F70UGZ_R18_FIXED_AUDIT_BUNDLE_V1,
source lifecycle/audit SHA, seven scenarios/112rows/37columns, fourteen data
hashes, unchanged gates and separate source9010/report0/bundle0 work counts.
README explains repository-based offline validation and all scope limitations.

ZIP_STORED (no compression), sorted names, regular mode0100644/create_system3,
fixed1980-01-01 00:00:00 header time, no extras/comments. This time is format
metadata, NEVER sample/creation/vehicle time. Larger stored bytes are accepted
to avoid zlib/environment variation. Whole ZIP must equal canonical rebuild.
Do not include volatile logs, Git state, temp paths or current time.

## Bounded verification

Limit archive input8MiB, total declared/unpacked data8MiB and each member4MiB.
Bound file reads to8MiB+1 and reject over-limit data before parsing/decompression.
Inspect names/count before materializing any member: exact17 unique expected
names only, no directory/traversal/absolute/drive/backslash/extra/duplicate paths.
Require ZIP_STORED and regular-file metadata, check sizes and CRC, and compare
the complete canonical archive bytes (reject header drift/trailing junk).
Never extractall. Materialize only the14 hardcoded validated-name data files
into a private TemporaryDirectory, then apply existing complete R16/R17
source/golden/canonical/report/environment checks. Reconstruct expected
metadata/README/Manifest from those validated bytes and compare them exactly.
Rewritten checksums do not authorize changed rows, gates or claims.

This verifies consistency against repository authorities, NOT malicious
replacement of those trusted authorities or cryptographic origin provenance.
No archive member is executed or imported. Temp materialization is validation
only, not an installation or public extraction service.

## CLI and output publication

audit_bundle.py export --evidence FIXED_ROOT --output NEW_DIR
audit_bundle.py verify --bundle BUNDLE_ZIP

Export output4 files: F70UGZ_R18_AUDIT_BUNDLE.zip (completion marker),
F70UGZ_R18_AUDIT_BUNDLE.zip.sha256, RESULTS.json and EXECUTION.json.
Output exists/file/dir/dangling link rejects before input reading. Validate,
build and self-verify complete ZIP bytes before output mkdir; write staged ZIP
and all receipts first, publish ZIP last. Failure leaves no completed archive.
Verify prints canonical result+actual isolation/module facts only; no permanent
output, input mutation, extraction/capture/deployment mode. Private validation
temps are removed normally; concurrent writers/crash durability are not promised.

In full verification use the same new installed venv: two -I/-B export
processes and two -I/-B read-only verify processes, no model/native/NumPy loaded.
Both exports' four files are exact-equal and both independent CLI verification
results match the archive content/result. Actual report/bundle work counts0
stay separate from source9010 and aggregate unit/reference test activity.

## Boundaries and completion

Unchanged package/API/wheel0.3.0, R14/R15/R16 producer/results, R17 output,
source/reference/goldens/dependencies/workflow. No actual input/native/schema/
Controller/Runtime/CAN/F61/r/dt/capture/vehicle install/deploy/main merge. Prior
two extracted helper bodies remain authorized only in inherited synthetic DEV
reference checks. Actual r/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL,
Candidate/Runtime NO_GO, F70UH/V/F71 NOT_ALLOWED; native Q01-Q06 remain closed.
No new numerical/physical/performance/replay/visual-quality certification.

TDD, full synthetic component/static/wheel gate, archive/new venv reproduction,
one independent whole-branch review, then existing feature/Draft update and
exact-HEAD dedicated offline CI/artifact/ZIP checks. Every commit [skip ci],
no legacy runtime CI. Retain external evidence and downloadable bundle SHA.
