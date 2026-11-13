# CORE71 — Manifest-pinned saved reference package integrity

Author choice under standing autonomous cloud instructions: safely reopen CORE70
three-file output without new model/reference work. Use the existing Python
development tree;no dependencies or preceding API/source/schema changes.

Approaches: re-execution already exists;full audit semantic inspection needs a
separate typed CORE69 stored-result contract;manifest-pinned integrity and narrow
envelope checks solve retained-byte verification now. Choose the third. Explicitly
do not claim full row validation,JSON/Markdown semantic agreement,arithmetic,
original-input/source authentication or vehicle authority.

## API and capture

New `integration_tools/reference_package_integrity.py` API:
`inspect_reference_package(input_root: Path, expected_manifest_sha256: str) -> dict`.
Exact lowercase64 manifest SHA is checked before caller paths. Reuse unchanged
CORE18 `_directory`/`_read_file` and CORE12 `_path`. Exact flat regular-file layout:
REFERENCE_AUDIT.json1..2097152bytes,SUMMARY_KO.md1..65536bytes,SHA256SUMS.txt1..512bytes.
One read-only bounded capture each,no symlinks/directories/FIFO or extra/missing
members. Compare opened/root inode after capture and check layout before/after;
close all descriptors before validation. This is not an atomic hostile-host
snapshot or a promise about later path content.

Compare external SHA against actual captured Manifest bytes. Require exactly two
canonical sorted lines:lowercase64 hash,two spaces,REFERENCE_AUDIT.json/newline,
then SUMMARY_KO.md/newline. Hash both captured payloads. Pinning the manifest binds
both JSON and summary;pinning only JSON would permit summary/manifest replacement.
Caller obtains expected manifest SHA from a trusted CORE70 receipt or trusted
delivery channel. A self-computed or attacker-supplied pin is not origin authority.

Strict canonical JSON parse via existing `_parse`:UTF8,duplicate/float/NaN/depth/
oversized-int/noncanonical rejection;root dict. Narrow required envelope only:
schema_version exact int1;contract_id CORE69_DECLARED_DIAGNOSTICS_REFERENCE_AUDIT_V1;
scope BOUNDED_DECLARED_NEXT_STATE_SELECTED_SOURCE_PARITY_NOT_FULL_CONTROLLER_ORIGIN_OR_VEHICLE_PROOF;
all six CORE66 authority flags exact False;gates canonical-equal to existing GATES.
Other body fields and additional keys are not semantically checked. Do not expose
stored audit status,work counters,identity or body as trusted inspection fields.
Summary is bounded strict UTF8 text only;do not render or interpolate its content.
Do not regenerate it through CORE70 because that imports execution machinery and
would assert a semantic relationship this feature intentionally does not check.

## Result and CLI

Result contract CORE71_REFERENCE_PACKAGE_INTEGRITY_INSPECTION_V1,schema_version1,
inspection_status REFERENCE_PACKAGE_INTEGRITY_VERIFIED,inspection_exit_code0,
manifest_sha256,captured_file_count3,files map of sha256/byte_size for all3files.
envelope_validation=CORE69_IDENTIFICATION_AND_CLOSED_AUTHORITY_FLAGS_ONLY.
audit_semantics_validated=False,summary_consistency_checked=False,
recorded_work_counts_validated=False,original_input_verified=False,
arithmetic_recomputed=False,new_synthetic_model_steps0,new_reference_steps0,
six authority flagsFalse,gates copied from existing GATES.
scope CAPTURED_THREE_FILE_INTEGRITY_ENVELOPE_NOT_AUDIT_SEMANTIC_NUMERICAL_OR_ORIGIN_PROOF.
No stored input,metadata strings,claimed history or source identity is elevated.

New `tools/reference_package_inspect.py`:exactly one --input-root and
--expected-manifest-sha256. No --run,policy/context overrides,abbreviations or
duplicates. Usage/SHA validation before project imports;help0 does no work.
Canonical stdout receipt<=16384bytes,positive short writes complete. Exit0 only
for integrity/envelope success regardless historical audit MATCH/DIFFERENT;
errors2 with fixed codes,no prefix success/retry. Restore sys.path/bytecode.
No result/cache/temp writes or subprocess/model/helper/checker execution/import
needed. Cold entry must work with -S (no NumPy/site-packages).

`ReferencePackageIntegrityError.code`: REFERENCE_PACKAGE_EXPECTED_MANIFEST_SHA256,
REFERENCE_PACKAGE_INPUT,REFERENCE_PACKAGE_CHECKSUM,REFERENCE_PACKAGE_JSON,
REFERENCE_PACKAGE_ENVELOPE,REFERENCE_PACKAGE_SUMMARY_UTF8. CLI usage code
REFERENCE_PACKAGE_INSPECT_USAGE_NO_EXECUTION,generic failure
REFERENCE_PACKAGE_INSPECT_FAILED_NO_EXECUTION. Never echo caller content/errors.

## Verification and unchanged boundaries

Witness missing-feature RED then real CORE70-produced package GREEN. Test actual
MATCH and audit DIFFERENT packages return integrity exit0,all3digests/sizes and
explicit unvalidated fields. Tamper either payload/manifest,malformed sorted
manifest,missing/extra/symlink/FIFO/directory/empty/oversized files,bad canonical
JSON/UTF8/envelope/gates/flags reject. Prove unknown or misleading audit body is
not semantically validated and never copied into inspection claims. Cold -S run
with algorithm imports blocked;all3captures once and fds closed;replacement after
capture uses captured bytes;inputs/no writes;CLI help/parsing/short/broken/stdout
prefix/restored globals and deterministic repeatability. No arithmetic fallback.

Freeze8scoped paths/protect751registered files,refs/config/limited primary;full
DEV2302+actual new tests,369compiles,98Manifest and unchanged wheel/CORE32 pins.
One fresh whole-branch review,then normal feature backup/main fast-forward/push
under prior authority;exact main/push DEV and Cloud CI/artifacts verified.
Retain external evidence. No workflow/dependency/security or actual-use changes.

R_BUDGETUNRESOLVED,STATIC_EVIDENCE_GATEFAIL,actual r/T2/scale null,
SOURCE_SCHEMA_UNQUALIFIED6000,Candidate/RuntimeNO_GO,F70UH/F70V/F71/actual
activationNOT_ALLOWED. CORE71 is an offline development label,not F-71 approval.
Actual Controller/Runtime/CAN/F61/vehicle input/capture/actual r/dt/install/deploy0.
Fixture generation and whole unit/gate synthetic work are nonzero/unaggregated;
the inspector itself performs model0/reference0,not zero integrity computation.
