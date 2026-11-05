# CORE18 Saved Run Inspection Design

Intent: read-only cross-artifact consistency check of the exact14-file CORE17
layout. User delegated ordinary offline next work; this inspection is a builder
choice, not authority to execute vehicles, calculators or arbitrary new inputs.

## Approach

Checking only individual checksums does not link suite copies to CURRENT.zip or
the report to both archives. Replaying the model would change scope and work.
Chosen: capture fixed saved artifacts, reuse existing pure archive verification/
comparison/rendering and canonical builder, then compare exact bytes. No existing
APIs/algorithms/files modified except human README/backlog links.

## Interface and algorithm

`inspect_archived_run(input_root: Path, baseline_sha256: str, current_sha256: str)
-> dict` in integration_tools/core_sequence_run_inspect.py. CLI of same basename
takes --input-root, --baseline-sha256, --current-sha256; no run/output/format flags.
Both full lowercase64hex digests checked before any caller-path inspection.

Require root exactly BASELINE.zip/CURRENT.zip regular files and suite/comparison
directories; suite exactly the3fixed case directories, each exactly INPUT.json,
RESULTS.json,SHA256SUMS.txt; comparison exactly COMPARISON.json,SUMMARY_KO.md,
SHA256SUMS.txt. No extra/missing files, invalid paths/symlinks/nonregular files.
Use existing guarded no-follow/nonblocking readers; directory layouts before/after
capture. Success captures each of14files once, no source reopening or extraction.

Capture archives (2MB each), run CORE15 report_suite_archive_bytes once. This
validates both SHA/ZIP/CRC/canonical/schema/Manifest and regenerates unchanged
CORE14 dict plus CORE15 Markdown. Capture9case files with CORE9 caps65536/524288/512
and CORE12 suite layout guard; build_suite_archive from those owned bytes must
equal captured CURRENT.zip exactly. This verifies source-copy relations without
reopening files or treating hashes alone as a byte-equality oracle.

Expected comparison files: canonical(comparison), generated Markdown, existing
sorted2entry checksum. Capture each actual comparison file with cap equal to its
generated expected length, using regular-file/no-follow bounded reads; compare
exact bytes. This accepts correctly generated JSON larger than64KiB without an
invented cap, and rejects overlong corrupt reports before unbounded allocation.
Do not parse arbitrary report JSON or load external objects into the renderer.
Keep CORE14 4MiB diagnostic and CORE15 65536byte limits unchanged.

Receipt contract CORE18_SAVED_ARCHIVE_RUN_INSPECTION_V1, status
SAVED_ARCHIVE_RUN_CONSISTENT, execution_requested=false, captured_file_count14,
captured_file_sha256 for all14, baseline/current validated receipts,
comparison_status/comparison_exit_code/difference_count/difference_counts,
recorded_current_model_steps from CURRENT receipt (not proof of execution),
new_synthetic_model_steps0, inspection_model_executions0,
inspection_reference_executions0, source_identity_reauthenticated=false,
arithmetic_recomputed=false, unchanged gates and scope. No absolute paths/random
IDs. Inspection CLI exit0 means consistency, including valid saved differences;
comparison exit0/1 is data, never inspection failure. Exit2 rejects, no receipt.

## Errors and boundaries

Fixed RunInspectError.code, inherited comparison/portable/case/suite rejection
details wrapped without raw caller values. No partial success, no fallback,
normalization/repair/overwrite/deletion. API performs no writes; CLI private cache
is separate infrastructure, cleaned before stdout, prefix restored. Short writes
handled; generic cache/stdout failure is rejection2, prefix may already be sent.

This is capture-based consistency, not proof that CORE17/model actually executed,
current source authentication, arithmetic truth, atomic snapshot, atime preservation,
hostile alias/race protection, fsync/durability, repeated CLI embedding or universal
renderer behavior. Consistently forged/rebuilt records can pass if caller supplies
their updated external archive digests. Never qualify actual vehicle context.
No new model/reference/F61/Controller/Runtime/CAN/actualr/dt/extraction/replay.
CPython3.12.13/configured Linux/POSIX environment, existing stdlib/venv, no installs.
Actualr/T2/scale=null; R_BUDGET UNRESOLVED; Static Gate FAIL; F70UH/V/F71/activation
prohibited. Unit fixture generation is separately NONZERO_NOT_AGGREGATED.
Local commits only, prior refs/source/evidence preserved; no merge/push/PR/CI/HF writes.
