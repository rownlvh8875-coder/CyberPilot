# R54 — Reference-check frontend preflight diagnostics

## Goal

Continue offline work from main `df978418fa62b62e1483bc0b44782b1e26c36182`.
Actual R38/R39 input/output NUL paths each leak raw ValueError before acquisition
or reference work. Existing single24/batch23 tests PASS on this exact source tree.
Bound these errors at the public frontend without changing reference arithmetic.
Owner has delegated ordinary design/execution and opted out of approval questions.

## Design choice

Use a narrow preflight-only boundary. A blanket CLI ValueError handler would hide
later defects; a new shared path utility would unnecessarily couple different
frontend policies. Neither is needed.

R38: extract its existing output guards, resolution/location checks and runtime
check unchanged into private `_preflight(input_path, output_path) -> None`.
`check_saved` calls it under classified-first handlers for ReferenceCheckError
and ReportError, then ordinary OSError/ValueError → ReferenceCheckError with the
existing CLI code `REFERENCE_IO`, preserving the original cause.

R39: keep its existing `_preflight` unchanged. Wrap only that call in check_batch,
preserving BatchReferenceError first, then OSError/ValueError → BatchReferenceError
with existing CLI code `BATCH_REFERENCE_IO` and original cause.

Do not wrap acquisition, parsing, identity, worker, result comparison, snapshots
or publication. Their existing propagation/aggregation behavior remains. TypeError,
KeyboardInterrupt/SystemExit and ordinary RuntimeError outside the existing
resolve handlers must not be hidden by the new boundary.

## Existing policy differences are intentional

Keep output existence/broken symlink/missing parent/component/input-location,
loop-resolution, encoding and runtime priorities exactly. Do not repair Paths,
add clamping/fallbacks, or invent new error codes.

R38 output contains no caller-path receipt; its valid Linux surrogateescape
input/output names remain supported. R39 already explicitly requires strict UTF8
for source/output/component paths: keep BATCH_REFERENCE_PATH_ENCODING. Do not
copy R32 receipt-specific requirements to R38 or weaken R39's existing contract.
NUL cannot be passed through OS argv: exercise actual CLI.main in a fresh child,
and separately real permission/overlong OS-argv failures under unprivileged UID.

## Unchanged boundaries

Public wheel/API, F61, model/reference arithmetic, state/limiter wiring, generator,
payload/expected literals, parsing/owned reads, dependencies/locks/cloud/CI unchanged.
Orchestration source hashes must change truthfully; compare all other saved-input
reference output fields exactly, with no tolerance or golden update.

R_BUDGET unresolved, StaticFAIL, actualr/T2/scale null, Candidate/Runtime NO_GO,
F70UH/V/F71/actual activation prohibited. No actual F61/r/dt/vehicle/Controller/
Runtime/CAN. Synthetic reference checks are permitted and counted separately.
No new concurrency, source authenticity, atomic publication or physical safety proof.

## Verification and delivery

TDD actual invalid paths, injected metadata errors, saved classified object/cause,
old code priority, pre-read/worker barriers, later fault propagation, real mode000
API/OS CLI, fresh-child NUL CLI and valid Unicode/surrogateescape distinctions.
Baseline/fixed exact saved-input parity except documented source-hash identity
deltas; inputs/source/closed manifests retained. Full locked DEV/cloud gates,
one fresh final branch reviewer, actual PR CI, normal exact-head merge and private
append-only HF backup/two recoveries without another approval pause.
