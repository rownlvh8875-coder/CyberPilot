# CORE13 portable saved-suite archive

Export the exact saved CORE12 three-case suite without replay. Preserve all nine
source files byte-for-byte. Add a canonical saved-only SUITE_REPORT.json and a
root SHA256SUMS.txt covering the other ten members. Exactly eleven regular files,
sorted names, ZIP_STORED, epoch1980 timestamp, Unix0644, no extras/comments.
No caller paths, current time, output filename or current source hashes in bytes.

API: export_saved_suite(input_root: Path, output: Path) -> dict;
verify_suite_archive(archive: Path, expected_sha256: str) -> dict.
Pure build_suite_archive(source_files: dict[str, bytes]) -> bytes and
verify_suite_bytes(raw: bytes, expected_sha256: str) -> dict share the byte format.
CLI export --input-root --output; verify --archive --sha256. JSON stdout only;
exit0 means custody checks succeeded, not numerical success; exit2 is rejection.

Verify requires an external, lower-case full64hex SHA before any file access.
Never extract. Bound entire ZIP to2,000,000 bytes, final22byte EOCD to11 entries
and central directory to4096 bytes. Fixed names only, no duplicates, no directory,
link, compression, encryption, ZIP64, prefix/suffix, alternative metadata/order.
Use existing CORE9 member caps. Report cap65536; root manifest cap4096.
Verify CRC, lengths, all manifests, captured source schemas/closed gates/case IDs,
regenerated saved-only report and exact deterministic ZIP reconstruction.

Capture source once with existing CORE12 root and CORE9 capture guards. Extract
CORE9 private decode(files) without changing public loader behavior. Saved status
MATCH/DIFFERENT/REJECTED remains data. New model/reference work is zero. Checksums
are custody/self-consistency, not signatures, origin authentication or arithmetic.
Consistently forged data may pass. Source identity stays unqualified.

Output must be a NEW external file with an existing non-symlink parent, outside
checkout and outside input suite. Validate all source bytes before creation.
Exclusive no-follow publication, partial-write handling, close then one bounded
readback and byte verification before success. Failure preserves any partial file;
no cleanup, retry, atomic-snapshot/durability or concurrency-adversary guarantee.
Cooperative local filesystem assumptions remain those of CORE9/12.

Receipts contain full ZIP SHA/size/member hashes, saved-only suite summary and
unchanged gates. Actual r/T2/scale=null, Static Gate FAIL, R_BUDGET unresolved;
vehicle/F61/Controller/Runtime/CAN/calculator/r executions forbidden. No network
publication, main merge, push, CI, policy approval or automatic model execution.
