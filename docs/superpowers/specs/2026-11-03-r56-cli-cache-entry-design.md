# R56 — Bound producer CLI cache-constructor I/O failures

## Evidence and selected scope

Actual main90c60ae7c57f2f287c97d1af2589aa72675a5f51, tree
3eb7df037fe0c410fd9abd9428281369336c9d1b. A fresh-child actual-mode000 probe
for R33/R40/R42/R43 showed four raw PermissionErrors before integration/model
imports, input reads or output. Only temporary base selection was patched; real
TemporaryDirectory/mkdtemp performed the denied filesystem operation. Source
bytes/sys.path/sys.pycache_prefix remained unchanged. R55 backups/recovery use
their separate pinned reviewed source while this single host worktree advances.

The owner delegated ordinary offline choices without repeated approvals. Select
the narrow constructor boundary, not a broad CLI lifecycle rewrite. Alternatives
are a new generic framework or an outer catch around the whole with-body: neither
is needed to fix this exact defect, and the latter could hide later output or
worker errors. Post-result cleanup behavior remains explicitly outside R56.

## Design

In each producer CLI, preserve argparse first. Construct its existing
TemporaryDirectory with the identical prefix inside a small try. Catch only
OSError from construction, emit the existing IO code with stderr
`REJECTED: <code>\n` and return2. Use the successfully constructed manager in the
existing with statement, keeping its entire body, imports, argument mapping,
sys.path insertion, pycache-prefix restoration, stdout and return logic intact.

Codes: R33 BATCH_IO (introduced in R55), R40 WORKFLOW_IO, R42 EXPLORATION_IO,
R43 CAMPAIGN_IO. No new diagnostic code or fallback directory. Do not expose raw
private filesystem text. Preserve OSError subclasses at this consumed CLI result
boundary without inventing a new exception API/cause contract.

Do not catch constructor ValueError/TypeError/RuntimeError/BaseException, manager
entry/exit failures, subsequent imports, parsing, workers, identity, publication
or primary stdout failures with this new handler. Actual TemporaryDirectory
constructor creates the directory; its ordinary __enter__ returns the name.
Existing cleanup/sink behavior is not expanded or represented as repaired.

## Verification

TDD new focused regression: factory OS failures including actual mode000 in fresh
children, exact rejection exit2/empty stdout/no traceback, original parser priority,
constructor prefix, no new input/import/worker/output activity, unchanged pycache
prefix/sys.path. Control non-OS programmer errors/interrupts and manager entry/exit
or later-body OSError propagation outside the new catch. Real Unicode successful
CLI outputs and checksum closures compare baseline/fixed at the same sandbox
paths, permitting only four exact CLI source SHA and validated dependent hash
changes. Existing with-bodies AST-exact, all other production code/math unchanged.

Reuse the already executed same-tree873 baseline rather than repeat it as a new
baseline. Run current targeted and full locked DEV/cloud gates, fresh committed
task completion, one independent final whole-branch review, actual exact-head CI
and normal guarded integration/private HF/two recoveries. Never advance shared
main before R55 main delivery seals. Preserve all earlier evidence/branches/envs.

Public0.3.0 wheel, schemas/dependencies/locks/cloud/CI/model/reference unchanged.
R_BUDGET unresolved, StaticFAIL, real r/T2/scale null, no actual F61/r/dt/vehicle/
Controller/Runtime/CAN/activation, Candidate/Runtime NO_GO, F70UH/V/F71 forbidden.
Synthetic unit/gate work NONZERO, not aggregate-counted or vehicle qualification.
