# CORE47 — reviewed receipt-copy and import-guide fixes

The user requested the recommended follow-up: fix CORE46 M1/M2, publish the
verified feature branch, and check scoped offline CI. Main integration, PR creation,
workflow/rule changes and actual-use authority are not part of this request.

## Small bounded design

Add explicit `__copy__` / `__deepcopy__(memo)` on the existing frozen
SyntheticRecordingInputPreflightV1. Both validate current declarations and
reconstruct through the existing validated constructor. Shallow copying creates
a new receipt sharing recording/contexts; deep copying creates copied declarations,
honors the caller's shared memo and graph aliases, and records the copied receipt
under id(original). Validate before invoking nested copying and revalidate the
copied declarations, including memo-provided substitutions. Preserve all false
permission flags, exact values, errors, model-index rules and the early __new__
subclass guard. Numeric validation remains nonzero; no model/reference/F61 work.

Alternatives: relaxing __new__ would weaken the early guard; a general pickle
reconstruction hook would widen persistence scope. Explicit standard copy hooks
are the author's narrow choice under the user's delegated implementation preference.
No receipt codec, pickle/transport support, CLI or new input acceptance is added.

The guide will show a real component-root `PYTHONPATH=src .venv/bin/python -B`
import check before its typed API snippet, and explain shallow/deep copying and
remaining cooperative/non-persistence boundaries. Prose is not tested by grepping;
execute the shown import command in a fresh process.

## Verification and delivery

TDD covers shallow/deep identity, input revalidation, pre-copy rejection of foreign
hooks, memo aliases and substituted invalid declarations, exact signed-zero/raw
bytes/time preservation, and zero public model steps/propagated unexpected errors.
Run the full configured DEV gate, unchanged wheel/CORE32 pins and full Manifest;
obtain an independent review of the five-path fix range against594879a0d.

Publish only feat/core46-recording-input-preflight through one ordinary non-force
push, after fresh remote/workflow preflight. No PR: inherited PR workflows would
open a different full-build scope. If no automatic feature-push workflow matches,
dispatch only existing DEV and Cloud workflows at the exact frozen feature head,
once each; verify terminal success and downloaded artifacts. Do not repeat a push
or dispatch just because its response is delayed. Keep main at695e76ae8.

All prior evidence/workspaces and unchanged files/refs remain preserved.
Actual r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,actual activation and
F70UH/V/F71 prohibited. This fixes usability, not source/vehicle qualification.
