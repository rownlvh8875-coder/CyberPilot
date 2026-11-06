# CORE24 Korean preflight report command

Builder-selected small offline increment under delegated execution and opt-out of
repeated approvals: print unchanged CORE23 Korean Markdown through one command,
using current CORE21 compatibility for its exit, not historical saved labels.

## Approaches and choice

The existing -I -B Python snippet works but its success exit means generation, not
semantic compatibility. Chosen: a standalone thin stdlib command following CORE22's
tested parser/bootstrap/descriptor-write pattern without changing or importing its
private helpers. Extending CORE22 with format switches would alter an existing
interface; a multi-file publisher/HTML UI is independent scope and not included.

## Contract

New `tools/core_sequence_preflight_report.py::main(argv=None)->int`.
Exactly one nonempty --archive and --sha256; order/equals form allowed. No duplicates,
abbreviations,positional,run/export/output/format/rate options. --help exits0 before
project imports or input access. Syntax errors exit2 with fixed stderr line
`REJECTED: PREFLIGHT_REPORT_USAGE_NO_MODEL_EXECUTION`.

After parsing, temporary ROOT/ROOT/src source selection and exactly one unchanged
CORE23 `report_preflight_archive(Path,str)` call. Its paired CORE21 status controls
exit: INPUTS_COMPATIBLE0,INPUTS_REJECTED1. stdout is exact original Markdown bytes,
not reconstructed from text, re-encoded, appended JSON or a new report contract.
Unknown status/ordinary operational failure gives2 before output when possible.

Known ArchivePreflightError and PreflightReportError give2 and `REJECTED: <code>`;
other ordinary errors give2 and `REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION`.
No raw path/exception text echo. CORE21 bad SHA remains before path access; CORE23
cap/render/integrity/helper errors produce no report. Short descriptor writes
complete; nonpositive progress/failure gives2, and an already written prefix cannot
be retracted or presumed valid UTF8/full Markdown. Failed/closed stderr cannot
replace operational2 with buffered-flush exit120. Failed help output also gives2.
BaseException propagates after original sys.path/dont_write_bytecode restoration.

Suppress bytecode from parser construction through output; no temporary cache or
temp-directory probing/allocation. pycache_prefix/temp environment untouched.
Initial module imports remain caller-managed; configured documented command -I -B.
No new dependencies, shared CLI framework or existing computational edits.

## Evidence-label clarification

Preserve all original CORE23 sealed bytes and ZIP identity. In the new external
evidence workspace issue a separately named addendum identifying acceptance JSON,
Markdown and evidence ZIP hashes by exact artifact names. Verify actual standalone
bytes and ZIP members/canonical seal/manifest before calling prior M1 clarified by
addendum. Do not retroactively edit the old ledger/review/ZIP or call its wording
changed. This is handoff clarification, not new source/arithmetic/owner authority.

## Verification and limits

TDD: real canonical archive Markdown/API parity; default exit1 with2compatible/
1rejected,all-valid historical REJECTED0,all-rejected1,early rejection all3rows;
SHA/syntax/help ordering,one report/capture/verifier/renderer,unchanged UTF8 bytes;
integrity/report cap/render/unexpected/import/status errors2 without raw text;
short/nonpositive/partial/stdout/stderr/help failures including real /dev/full;
cold parser/import/bytecode/temp/global restoration,blocked producer/reference/F61/
model execution,readonly/space/path/size controls and unchanged gates.
Existing138 preflight+26 CORE15 regressions, fresh1526+actual new tests/296 own
compiles/static, frozen wheel. Independent preserved CORE17 ZIP twice through
API/direct/blocked/cold command plus help/usage/missing: original CORE23 Markdown
and CORE21 receipt preserved; capture1/verifier1/cases3/quantizer8/renderer1;
no new fixtures/model/ref/extraction/writes, source bytes/modes/layout unchanged.

No browser visual PASS, wheel distribution, artifact output API or hostile Python/
concurrent globals/path-race/atomic/atime/non-Linux3.12.13 guarantee. Numeric
validation and whole unit/gate fixture work separately NONZERO; command/independent
new model/ref0. Actualr/T2/scale=null,R_BUDGET=UNRESOLVED,Static Gate=FAIL,
Candidate/Runtime=NO_GO,F70UH/F70V/F71/actual activation NOT_ALLOWED.
Retain branch/worktree/evidence; no merge/push/PR/CI/HF writes.
