# CORE21 portable suite input semantic preflight

Builder-selected offline increment under the user's delegated execution: accept a
complete existing CORE13 portable suite and revalidate all three captured case inputs
without extraction, reopening case files, model/reference execution or a new CLI.

## Approaches and boundary

Per-case path intake remains useful for unpacked CORE8 packages, but requires caller
format handling for portable bundles. Chosen: reuse the complete existing bounded
CORE13 verifier and its owned decoded records directly. Extract CORE19's current
post-capture body into private `_preflight_captured(captured: dict) -> dict`; its public
Path API still performs the identical CORE9 capture/error wrapping and delegates.
No numeric rule, existing receipt/schema/CLI/limiter/wheel behavior changes.

## Interface

New `integration_tools.core_sequence_archive_preflight`:

- `preflight_suite_archive_bytes(raw: bytes, expected_sha256: str) -> dict`
- `preflight_suite_archive(input_archive: Path, expected_sha256: str) -> dict`
- `ArchivePreflightError.code`: `ARCHIVE_PREFLIGHT:` plus the original PortableError code.

Path API validates the complete lowercase64hex built-in string SHA before any caller
path metadata/open, reads the bounded archive exactly once through `_read_archive`,
then delegates to the bytes API. Bytes API performs `_verified_suite` exactly once:
exact bytes/type/SHA,2MB cap,11 fixed stored members, CRC/member caps/Manifest/closed
CORE9 records/saved suite report/canonical ZIP. No extraction or filesystem writes.
Existing unsafe/missing/symlink/nonregular/FIFO/oversized paths remain rejected.

Only after the entire archive is valid, call the same private CORE19 post-capture
routine once per case in CASE_IDS order. Process all cases even after a semantic
rejection. Corruption/capture failures raise fixed ArchivePreflightError with no
aggregate receipt. Unexpected helper exceptions/statuses propagate, never become a
normal rejection or partial aggregate. Numeric work may be nonzero before a later
unexpected failure; no claim of zero validation work in that situation.

## Result

schema_version1, contract_id `CORE21_PORTABLE_SUITE_INPUT_PREFLIGHT_V1`;
`archive` is the unchanged CORE13 verification receipt. `case_reports` is the ordered
list of byte-identical CORE19 case receipts, not prepared/model/calculator args.
`case_ids` is list(CASE_IDS), `case_count`3, `all_cases_processed`true.
`compatible_case_count`/`rejected_case_count` count current input verdicts.
`preflight_status` is INPUTS_COMPATIBLE iff all three are compatible, otherwise
INPUTS_REJECTED. `validated_transition_count` totals each case's successful prefix,
`declared_transition_count`9, `recorded_model_steps` sums historical case data.
Current compatibility is independent of historical MATCH/DIFFERENT/REJECTED.

`new_synthetic_model_steps`/`new_reference_steps`0;
`numeric_validation_work` NONZERO_NOT_AGGREGATED;
`source_identity_reauthenticated`/`arithmetic_recomputed`/`prehistory_checked`/
`v4_payload_allowed`/`f61_input_allowed`/`actual_activation_allowed`false;
`gates` copies the unchanged GATES. No state/precision/time/r-policy inference.

## Verification and limits

TDD: default bundle2compatible/1rejected, all-compatible/all-rejected coherent
archives, exact folder/bytes/path receipt parity, SHA preflight ordering, one capture
and one archive verification, full validation before semantics, no extraction or
model/reference/producer/F61 work, prefix counts, exception propagation, ownership,
corruption/size/path controls and unchanged CORE19/20 regression tests.
Independent acceptance twice uses preserved CORE17 CURRENT.zip and case files,
not new model fixtures. Preserve original case/CORE13 receipts and the AST of CORE19
post-capture computational body. Whole DEV gate plus290 own compiles/static checks,
frozen wheel unchanged, one fresh whole-branch review and unsigned seal verification.

Configured CPython3.12.13 Linux/cooperative API, not a hostile Python sandbox,
atomic snapshot, atime-preserving reader, source/execution/arithmetic authenticator,
V4/F61 bridge or vehicle evaluation. Import infrastructure remains caller-managed;
documented invocation uses -I -B. Semantic numeric validation is nonzero; independent
fixture/model/reference/F61/actualr-dt/Controller/Runtime/CAN work0. Whole unit/gate
fixture work separately NONZERO_NOT_AGGREGATED. Actual r/T2/vehicle_scale=null,
R_BUDGET=UNRESOLVED, Static Gate=FAIL, Candidate/Runtime=NO_GO,
F70UH/F70V/F71/vehicle activation=NOT_ALLOWED. No merge/push/PR/CI/HF writes.
