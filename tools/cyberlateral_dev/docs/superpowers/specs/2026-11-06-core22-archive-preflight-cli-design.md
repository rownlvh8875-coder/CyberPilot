# CORE22 Portable archive input preflight command

Builder-selected offline increment under the user's delegated execution and explicit
opt-out of repeated approval questions: expose unchanged CORE21 receipts through a
single read-only command. It requires no extraction, handwritten Python or new policy.

## Approaches and selection

Existing -I -B API invocation works but requires Python glue. Chosen: a thin stdlib
CLI using the proven CORE20 parser/output/bootstrap pattern, without changing it or
coupling one command to another command's private helpers. A combined export/run
command would add side effects and is out of scope. This is the builder's choice,
not a new user statement of complete product requirements.

## Interface

New `tools/core_sequence_archive_preflight.py::main(argv=None)->int`.
Exactly one nonempty `--archive` and one nonempty `--sha256`, either order or
argparse equals form. No abbreviated, positional, repeated, run/export/output/rate
options. Ordinary argparse --help exits0 without project imports or input access.
Syntax errors exit2, fixed diagnostic `REJECTED: ARCHIVE_PREFLIGHT_USAGE_NO_MODEL_EXECUTION`.

After parsing, temporarily select component ROOT and ROOT/src, call unchanged
`preflight_suite_archive(Path,str)` exactly once. SHA format/type/ZIP/path/size/
integrity/semantics remain CORE21 authority; invalid SHA must still precede caller
path access. Canonical JSON stdout must be byte-identical to the API receipt.
Current aggregate INPUTS_COMPATIBLE gives0; INPUTS_REJECTED gives1, regardless of
historical labels. Unexpected status fails closed with no serialized receipt.

Known ArchivePreflightError gives2 and `REJECTED: <error.code>` on stderr. Other
ordinary errors give2 and `REJECTED: ARCHIVE_PREFLIGHT_FAILED_NO_MODEL_EXECUTION`.
No raw caller paths/messages. Serialize fully before writing. Descriptor writes
complete short writes and reject zero/negative progress; failures give2. Already
written stdout prefixes cannot be retracted. Diagnostics are best effort and must
not replace operational2 with Python's buffered-flush exit120. Failed help output
also gives2; failed in-memory diagnostics must not escape as ordinary exceptions.
BaseException propagates after restoring globals.

Suppress bytecode from parser construction through project imports/output, restore
sys.path and dont_write_bytecode in finally. No temp/cache allocation or probing,
pycache_prefix/temp/environment settings unchanged. No product imports for help or
syntax errors. Module import infrastructure is caller-managed; documented command
uses configured CPython3.12.13 with -I -B. No new dependency or shared CLI framework.

## Verification and boundaries

TDD with real canonical archives: default2compatible/1rejected=>exit1, all-compatible
including historical REJECTED=>0, all-invalid=>1; exact CORE21 receipt and ordered
case counts. Errors/no partial JSON, bad SHA before path, syntax before imports,
one read-only capture/verifier, readonly/space paths, symlink/nonregular/size/CRC/
Manifest/schema failures, cold bytecode/cache/global restoration, blocked producer/
reference/model/F61 execution, short/failed output and real /dev/full/closed stderr.
Existing84 focused tests unchanged. Fresh full DEV gate,292 own compiles/static
checks, frozen wheel unchanged. Independent two-run original CORE17 CURRENT.zip
API/direct/blocked/cold command parity against prior CORE21 receipt, no new fixtures,
one capture/verifier/three semantic cases/eight quantizer validations and input custody.

No CORE13/19/20/21 API/algorithm/CLI changes. Numeric validation and whole gate
fixture work separately NONZERO_NOT_AGGREGATED; command/independent model/ref0.
Not source/execution/arithmetic/prehistory/atomic/atime/hostile-hooks authenticity,
portability beyond configured Linux CPython3.12.13, F61 bridge or vehicle evaluation.
Actualr/T2/vehicle_scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
Candidate/Runtime=NO_GO,F70UH/F70V/F71/actual activation NOT_ALLOWED.
Retain local branch/worktree/evidence, no merge/push/PR/CI/HF writes.
