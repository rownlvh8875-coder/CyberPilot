# CORE16 Saved Archive Workflow Design

Intent: one offline command takes two CORE13 ZIPs and full external SHA256 values,
then saves unchanged canonical CORE14 JSON, CORE15 Korean Markdown and their
checksum in a NEW external directory. It does not execute the synthetic producer.
User delegated ordinary design choices and asked to continue without approval pauses.

## Approaches and builder choices

Shell composition duplicates source captures and has unclear partial failure semantics.
A new comparison/report implementation risks divergence. Chosen by the builder:
reuse `report_suite_archives` once and add a small exclusive directory publisher.
Existing CORE13/14/15 APIs and CLIs remain unchanged. No dependencies or installs.

## Contract

`publish_archive_report(left: Path, left_sha256: str, right: Path,
right_sha256: str, output_root: Path) -> dict` returns a receipt only after readback.
Both SHA strings pass CORE14 preflight before caller path access. Preflight a NEW
output with an existing parent; reject invalid Path/NUL/UTF8, symlinks in its path,
existing targets and paths inside this checkout. Read each source role once;
validate both ZIPs, compare once, render once before creating output. A valid input
cannot be within a nonexistent output directory; a shared external parent is allowed.

Fixed file set: `COMPARISON.json`, `SUMMARY_KO.md`, `SHA256SUMS.txt`. JSON is exactly
`canonical(comparison)` without wrapper/changes; Markdown exactly CORE15 output.
Checksum lists the first two in sorted filename order, full lowercase SHA, two spaces,
LF, no self-entry. Files and receipt exclude absolute paths, clock values and random IDs.
Receipt contract `CORE16_ARCHIVE_WORKFLOW_V1`, publication status
`ARCHIVE_REPORT_PUBLISHED`, comparison status/exit code, per-file SHA/byte lengths,
closed gates, explicit no new model/reference, source authenticity/arithmetic false.

Create directory0700 exclusively. Hold a no-follow directory fd; create files0600
with exclusive/no-follow/nonblocking flags and handle short writes. Check exact
directory membership, regular-file sizes and exact bounded bytes readback of all3;
check root fd/path identity before returning. No source reopening or ZIP extraction.
Failures before mkdir leave no output. Publication errors state partial directory
possible; readback errors state directory may exist. Preserve leftovers; never clean,
retry or overwrite. Success is observational, not atomic snapshot/fsync/durable or
hostile-filesystem guarantee. Python3.12/POSIX cooperative local filesystem scope.

CLI `tools/core_sequence_archive_workflow.py` takes the four CORE15 flags plus
required `--output-root`. JSON receipt stdout only after publication and private
cache cleanup; exit0 identical archives,1 valid difference,2 error. Arg abbreviations,
unknown options, omitted SHA/output rejected. Generic errors after attempting the
operation say output may exist; no fake success/cleanup. Partial stdout cannot be
retracted. Saved MATCH/DIFFERENT/REJECTED never set this comparison exit code.

## Limits and exclusions

Inherit input2MB, CORE14 retained diagnostic4MiB and CORE15 Markdown65536bytes
limits unchanged. Output readback is bounded by generated file lengths, not the
Markdown cap (comparison JSON can exceed64KiB). No arbitrary report JSON reader,
input manufacture, live input, extraction, replay, F61 import/compile/calculation,
Controller/Runtime/CAN, policy approval, r/dt calculation, actual vehicle activation.
Actualr/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL; F70UH/V/F71 prohibited.
Whole unit/gate fixture activity is nonzero and not an all-model-zero claim.
Preserve prior refs/registered source and evidence. Local commits only, no merge,
push, PR, CI or HF writes. No browser/all-renderer visual PASS claim.
