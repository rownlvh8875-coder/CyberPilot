# CORE25 Exclusive input preflight report publication

Builder-selected offline increment under delegated execution and opt-out of repeated
approvals: save the existing CORE21 JSON and CORE23 Korean Markdown as a deterministic,
checked three-file package. This is local report publication, not network/deployment.

## Approaches and choice

Shell redirection keeps commands simple but separates artifacts and can overwrite.
Chosen: one narrow API and CLI using unchanged CORE16 `_output`/`_publish` safety
machinery, unchanged CORE23 report and CORE21 preflight. Reimplementing filesystem
publication or adding a new ZIP/HTML format is unnecessary and excluded.

## API and order

New `integration_tools.core_sequence_preflight_workflow.publish_preflight_report(
input_archive: Path, expected_sha256: str, output_root: Path)->dict`.

1. Validate complete lowercase64hex expected SHA through CORE13 `_expected` before
   any caller input/output path work. Wrap PortableError as unchanged CORE21
   ArchivePreflightError with `ARCHIVE_PREFLIGHT:` prefix.
2. CORE16 `_output` validates a NEW path outside the current checkout, under an
   existing parent, rejecting symlinks/bad text/non-Path/existing file or directory.
   Existing output rejection precedes input capture. Keep original ArchiveWorkflowError codes.
3. Call CORE23 `report_preflight_archive(Path,str)` exactly once. Validate current
   status mapping to0/1 before publication. Propagate integrity/helper/render errors.
4. Build `PREFLIGHT.json` as unchanged CORE21 canonical JSON, `SUMMARY_KO.md` exact
   CORE23 bytes, then `SHA256SUMS.txt` sorted over those two, self excluded.
   Finish all serialization before mkdir; no extra input reading/extraction/model work.
5. Reuse CORE16 `_publish` once: new0700 directory, exclusive/nofollow0600 writes,
   short-write completion, exact file set/regular-file/size/bytes bounded readback,
   output fd/path identity. No custom rewrite of existing publisher.
6. Return path/time-independent canonical publication receipt only after success.

New receipt schema_version1,contract_id `CORE25_PREFLIGHT_WORKFLOW_V1`,status
`PREFLIGHT_REPORT_PUBLISHED`; `preflight_status`,`preflight_exit_code`; archive_sha256/
archive_byte_size; case_count/compatible_case_count/rejected_case_count,
validated_transition_count/declared_transition_count/recorded_model_steps; files map
for all3names with sha256/byte_size; new_synthetic_model_steps/new_reference_steps0,
numeric_validation_work NONZERO_NOT_AGGREGATED; six authority flags false, unchanged
GATES,scope `VERIFIED_INPUT_PREFLIGHT_REPORT_PUBLICATION_NOT_ARITHMETIC_OR_ORIGIN_PROOF`.
Publication success is not semantic compatibility: current rejection is still saved
normally with preflight_exit_code1. Historical labels do not decide this code.

## CLI

New `tools/core_sequence_preflight_workflow.py::main(argv=None)->int` requires exactly
one nonempty --archive/--sha256/--output-root. No abbreviations,duplicates,positional,
run/export/format/rate options. Help/syntax before project/input/output work;
fixed usage `PREFLIGHT_WORKFLOW_USAGE_NO_MODEL_EXECUTION`/exit2. Uses CORE24 no-cache
parser/bootstrap/descriptor pattern locally, not a new shared command framework.

One publish call, canonical publication receipt stdout; current compatible/rejected0/1.
Known ArchivePreflightError/PreflightReportError/ArchiveWorkflowError preserve codes/2.
Other ordinary failures use `PREFLIGHT_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION`/2.
Bytecode suppressed parser-through-output,sys.path/flag restored,temp/cache/probing0.
Short/nonpositive/failed stdout/help/stderr behavior like CORE24; diagnostic failure
cannot replace operational2. BaseException restored then propagated.

## Failure and authority boundaries

Preflight/output/serialization errors before publication leave output absent. During
publication failures may leave empty/partial/complete directories; preserve them,
never auto-delete,retry or overwrite. Readback/root-identity failure never returns
success. stdout failure after publication can leave a complete valid package and a
partial stdout prefix; exit2 is not proof output absent. Exact inherited publisher
error codes expose these possibilities. No atomic/fsync/crash durability claim.

No existing computational/API/CLI/publisher edits, no new ZIP/reader/dict renderer,
producer/reference/model/F61/actualr-dt/vehicle work or policy value. Numeric validation
and whole unit/gate fixture work separately NONZERO; feature/independent model/ref0.
Configured cooperative Linux CPython3.12.13; no hostile hooks/concurrent globals/
path-race/atime/other-platform/visual/source/arithmetic/prehistory/vehicle guarantees.
Actualr/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,Candidate/Runtime=NO_GO,
F70UH/F70V/F71/actual activation NOT_ALLOWED. Keep branch/worktree/evidence;
no merge/push/PR/CI/HF writes.

## Verification

TDD API+CLI: exact old artifacts/manifest/publication receipt,current versus historical
cases,determinism,requested permissions,one report/capture/verifier/renderer,source
custody; digest/output ordering,no-overwrite/path guards,preflight/render/serialization
failures before mkdir; short/zero/later writes,creation race,readback corruption/extra
file/FIFO/root replacement,partial preservation; CLI grammar/cold/cache/globals,
known/unexpected/import/status/output failures,post-publication stdout failure,
real /dev/full/closed streams,blocked producer/ref/F61/model execution and unchanged gates.
Fresh full1560+actual new tests,300own compiles/static,wheel unchanged. Independent
original CORE17 ZIP API/direct/blocked/cold publication twice to distinct destinations,
old CORE21 JSON/CORE23 MD parity,manifest/readback/file identities/permissions,
same receipts across paths,source unchanged; no new fixtures there. Source623/
protected613/refs28,one fresh final review and separate unsigned evidence seal.
