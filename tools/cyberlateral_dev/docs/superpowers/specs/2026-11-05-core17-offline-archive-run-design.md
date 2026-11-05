# CORE17 Closed Offline Archive Run Design

Intent: connect the existing fixed synthetic suite runner, portable export and
saved archive report in one explicit run command. The user delegated normal
offline next steps; this orchestration is the builder's choice, not a new vehicle
or whole-product requirement. It adds no input domain or calculation algorithm.

## Approach

Manual CORE12/13/16 commands work but require the caller to manage intermediate
files and failure state. A new runner/comparator would duplicate authority.
Chosen: reuse the existing algorithms unchanged and capture the original baseline
once, verify before any execution, and retain an exact baseline copy for comparison.
This avoids reopening a changing caller baseline after execution begins.

## Interface and ordering

New `run_archived_suite(baseline: Path, baseline_sha256: str, output_root: Path)
-> dict` in integration_tools/core_sequence_archive_run.py. CLI
tools/core_sequence_archive_run.py requires literal `run`, --baseline-archive,
--baseline-sha256, --output-root. No check/default-run/format/arbitrary-input mode.

1. Validate full lowercase64hex SHA before any caller-path inspection.
2. Guard NEW output: existing parent, outside checkout, no existing target or
   symlink components/invalid Path/NUL/UTF8. Capture original baseline once with
   CORE13 bounded no-follow reader; verify full SHA/CRC/schema/Manifest/canonical ZIP.
3. Publish/readback exact baseline bytes to NEW root/BASELINE.zip exclusively,
   using CORE16's private publisher. Baseline-copy failure performs no model work.
4. CORE12 run_closed_suite(root/suite), fixed sign-cycle/declared-difference/
   late-invalid. Successful run has6new synthetic model steps (3/3/0), saved M/D/R
   1/1/1. These are development diagnostics, not a blanket numerical PASS.
5. CORE13 export_saved_suite(root/suite, root/CURRENT.zip), unchanged9source files.
6. CORE16 publish_archive_report(BASELINE.zip, suppliedSHA, CURRENT.zip, exportSHA,
   root/comparison). Baseline LEFT/current RIGHT. No original source reopen.
7. Check root has exactly2regular files(BASELINE.zip/CURRENT.zip) and2directories
   (suite/comparison), without symlinks. Child closure/readback belongs to the reused
   stages. Return canonical JSON receipt only after all stages succeed.

Receipt contract CORE17_CLOSED_OFFLINE_ARCHIVE_RUN_V1; status
OFFLINE_SYNTHETIC_ARCHIVE_RUN_COMPLETED; execution_requested=true;
baseline_verification, suite_run, current_export, comparison_publication unchanged
stage receipts; new_synthetic_model_steps from suite; comparison_exit_code from
CORE16; source_identity_reauthenticated=false; closed gates and scope. No absolute
paths/timestamps/random IDs. Same fixed code/baseline gives byte-identical files
and receipt in different output directories. Receipt is stdout only, not a stored
root file. No new whole-folder Manifest or authenticity/sealing claim.

## Errors and work

Fixed ArchiveRunError.code with stage and no raw caller text. SHA/output/baseline
preflight error: NO_MODEL_EXECUTION, output absent. BASELINE_COPY failure:
NO_MODEL_EXECUTION/OUTPUT_MAY_EXIST. RUN/EXPORT/COMPARE/final-layout failure:
WORK_MAY_BE_NONZERO/OUTPUT_MAY_EXIST; never claim0after work may have started.
Preserve all partial files, no cleanup/retry/resume/overwrite. Unexpected post-copy
exceptions get the same conservative work/output uncertainty. No partial success.
CLI cache creation/argument failure:0model. Cleanup/stdout failure may occur after
full execution, so generic diagnostics acknowledge possible work and output.
Cleanup/serialization/exit calculation before stdout; short writes handled, an
already-written stdout prefix cannot be retracted. Exit0identical ZIPs,
1valid difference (workflow still complete),2error; saved M/D/R never set this exit.

## Constraints and exclusions

CPython3.12.13/existing stdlib/venv only; no installs. Preserve existing APIs/code,
CORE13 input2MB/CORE14 diagnostic4MiB/CORE15 Markdown65536byte limits. The caller's
baseline snapshot, generated suite, ZIP and comparison are captured stage records,
not an atomic simultaneous filesystem snapshot; later mutation is not prevented.
Cooperative POSIX filesystem scope, no hostile alias/race, atime, fsync/power-loss
durability, repeated CLI embedding, universal renderer or source authenticity claim.
No extraction/arbitrary synthetic reader/actual vehicle input/F61 import or
executable compile/calculation/Controller/Runtime/CAN/actualr/dt/policy approval.
Actualr/T2/scale=null, R_BUDGET UNRESOLVED, Static Gate FAIL; F70UH/V/F71/vehicle
activation prohibited. New fixed synthetic work6on success is explicit; whole
unit/gate fixture work is NONZERO_NOT_AGGREGATED. Local commits only; preserve prior
refs/source/evidence, no merge/push/PR/CI/HF writes.
