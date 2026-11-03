# R47 — R46 post-result diagnostics

## Intent

R46 commits a complete report by exclusively linking `index.html` last. A later
temporary-directory cleanup error is diagnostic, not publication failure.
Currently `RuntimeWarning` promoted to an exception reverses that API/CLI result.
Protect the already determined result without hiding errors before that boundary.

## Author-selected approach

The user delegated routine next-step choices and opted out of repeated approval
questions. Keep the existing Python implementation and warning codes. Use one
private `_warn_after_result(message: str) -> None` helper in the R46 runner, also
imported by its CLI. First issue the existing RuntimeWarning. If any ordinary
`Exception` escapes warning delivery, try a `WARNING: <code>` stderr line. If
that diagnostic sink also raises `Exception`, preserve the determined result.
Do not intercept `BaseException` (interrupt, exit, process termination).

Alternatives: dropping warnings loses useful diagnostics; changing global warning
filters changes callers' policies; direct stderr-only delivery breaks existing
warning observers. This bounded best-effort helper preserves default observers
and handles user-provided warning hooks without a new framework/dependency.

## Contract and limits

- API: after index commit, cleanup diagnostics cannot replace REPORT_COMPLETE.
- CLI: after result determination, cache cleanup diagnostics cannot change exit0
  or rejection exit2; before a result, I/O failures still reject with exit2.
- Existing default RuntimeWarning codes remain observable. Broken warning hooks
  or stderr may lose diagnostics; no guaranteed diagnostic delivery is claimed.
- Real files, input validation, exclusive publication and closed Manifest remain
  in use. No renderer output format/schema, HTML or VIEW changes.
- R44's separate post-result warnings are out of scope, not claimed fixed.
- Public wheel0.3.0, dependencies/locks, model/reference/calculator untouched.
- R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/scale=null.
- No F61/actual r/dt/vehicle/Controller/Runtime/CAN execution or activation.
- Feature-stage PR only; no main merge or Hugging Face writes in this stage.

## Verification

Use complete real saved comparison fixtures; inject only cleanup or diagnostic
faults. Prove default warning delivery, warning-as-error API and isolated CLI,
broken warning hook/stderr, interrupts not swallowed, precommit publication error,
pre-result cache error, and preserved rejection. Check real closed output Manifest.
Run the full dev gate and cloud gate, independent whole-branch review and exact
PR-head CI. Compare baseline/fixed HTML and VIEW bytes for the same saved input.
Preserve evidence outside the repository; package it deterministically twice.
