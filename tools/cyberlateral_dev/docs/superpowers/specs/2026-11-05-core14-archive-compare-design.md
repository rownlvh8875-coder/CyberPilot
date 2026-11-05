# CORE14 saved-suite archive comparison

Compare two CORE13 ZIPs in this cloud without extraction, model replay, publication
or policy decisions. User has delegated ordinary implementation choices and
approved progressing from CORE13 to saved-only ZIP comparison.

## Approach and builder choices

Choose validated in-memory comparison, extending the private CORE13 verification
boundary to return its owned decoded records alongside the unchanged public
receipt. Reuse CORE10 exact-type INPUT/RESULT/IDENTITY comparison per fixed case.
Extraction to temporary folders adds writes/path surface and is rejected. Comparing
only ZIP/member hashes loses field differences and is rejected. No new dependencies.

## Interfaces and output

`compare_suite_archives(left: Path, left_sha256: str, right: Path,
right_sha256: str) -> dict` and pure `compare_suite_archive_bytes(left: bytes,
left_sha256: str, right: bytes, right_sha256: str) -> dict`.
Both SHA strings must be valid full lower-case64hex BEFORE any file access or
ZIP parsing. Each file role is captured exactly once via existing bounded no-follow
CORE13 reader; each byte role is verified and ZIP-parsed once. Two roles referencing
the same path are still separately captured, not an atomic snapshot. No reopen or
extraction, no source-directory input, no external manifests or implicit SHA.

After complete validation of both roles compare fixed case order sign-cycle,
declared-difference, late-invalid. Preserve every stored status and historical
step count. Return CORE14_ARCHIVE_COMPARISON_V1 with full CORE13 left/right
receipts, full CORE10 per-case comparisons, actual `archive_bytes_identical`,
`comparison_status` SAVED_SUITE_ARCHIVES_IDENTICAL or SAVED_SUITE_ARCHIVES_DIFFERENT,
`difference_count`, INPUT/RESULT/IDENTITY totals, comparison counts, case IDs,
reported count and truncation. All differences count; details are capped at256 per
case (768 overall), retaining each case's relative JSON pointers. Metadata identity
is opaque data and is never ignored or reauthenticated. Equality is not a new
numerical MATCH, regression qualification, signer identity or provenance proof.

Resource-profile amendment from final review: before materializing CORE10 detail
lists, stream the first256 differences per case and sum canonical JSON byte lengths
(one newline per diagnostic included). Aggregate limit4,194,304bytes across all
cases, inclusive. Return detail_byte_limit and reported_difference_bytes for
accepted reports. Exceeding this limit rejects with ARCHIVE_COMPARE_DETAIL_BYTE_LIMIT
and no report, even if both ZIPs individually verify. No shortening paths, silent
omission or forged complete counts. This is a software diagnostic-memory limit,
not F61 r/vehicle policy. Accepted records/details and full difference counts stay exact.

`new_synthetic_model_steps`, comparison model/reference executions are0;
`source_identity_reauthenticated` and `arithmetic_recomputed` arefalse. All existing
GATES unchanged. No partial success if a role is malformed; no record fallback.
`ArchiveCompareError` wraps portable diagnostics with ARCHIVE_COMPARE_LEFT: or
ARCHIVE_COMPARE_RIGHT: and fixed codes, not raw paths or exception text.

CLI `tools/core_sequence_archive_compare.py --left-archive --left-sha256
--right-archive --right-sha256` emits canonical JSON stdout. No abbreviation,
extract/run/r/format/upload/output flags. Exit0 identical ZIP bytes,1 validated
difference,2 rejection. Cache cleanup, exit classification and serialization all
precede success/difference output; ordinary errors have fixed diagnostics. Partial
stdout cannot be retracted; no output-file publication API.

## Compatibility and protection

CORE13 public receipt/ZIP format and byte identity remain unchanged. Existing
bounded EOCD/actual11entry/ZIP64/CRC/member/canonical validation remains authority.
Only private helper extraction in core_sequence_bundle.py plus new module/CLI/tests
and docs. Existing producers/model/calculator/loaders/locks/workflows unchanged.

Scope is configured Python3.12 POSIX/cooperative filesystem. No atomic snapshot,
fsync, hostile-parent/alias race, native Windows, future Python byte stability or
repeated CLI embedding guarantee. Consistent forgeries may pass custody checks.
Actual r/T2/vehicle_scale=null; R_BUDGET UNRESOLVED; Static Gate FAIL;
actual input/F61/Controller/Runtime/CAN/r calculation0; F70UH/F70V/F71 and actual
activation NOT_ALLOWED. Whole unit/gate fixture work is NONZERO_NOT_AGGREGATED.
Keep local branch/evidence; no main merge, push, PR, CI or HF writes.
