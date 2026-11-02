# R38 — independent selected-source check of saved synthetic scenarios

User requested implementation of the prior R38 recommendation and delegated routine
technical choices. These interfaces are the author's choices, not a vehicle or
whole-product requirement approval. Work in the existing isolated feature worktree;
no commit/push/merge/CI or vehicle activation in this implementation request.

## Choice and boundaries

Chosen: a separate DEV checker of a complete, bounded R31 saved directory.
Alternative automatic checking inside R31 changes existing execution semantics;
alternative another repeated model run is not independent. The chosen tool reuses
R32's complete checksum/schema/cross-record validation before any reference work.
Portable subsets, arbitrary raw messages and actual vehicle inputs are not accepted.
Raw R31 JSON can already be run with the existing producer; R38 checks its result.

CLI: `tools/scenario_reference_check.py --input COMPLETE_R31_DIR --output NEW_DIR`.
API: `integration_tools.scenario_reference_run.check_saved(input_path:Path,
output_path:Path)->dict`. exit0 MATCH; exit1 DIFFERENT; exit2 invalid request,
input/source/runtime/reference/publication failure. No fallback or tolerance.
Output parent exists; output cannot exist/be a dangling symlink or be inside input
or the component. Refuse bad output before input reads/reference launches.

## Independent computation

After complete input validation and exact imported-source/runtime checks, launch
the current pinned Python with `-I -B`, private empty cwd/cache and a fixed worker
path. Parent owns INPUT bytes; never pass source paths from the saved receipt.
Worker parses/validates the entire typed INPUT again before importing the reference.
Use existing `NormalizedReference`, `SourceReference`, bit quantization oracle,
`project_reference`, and SHA-pinned Kernel helper pair unchanged. New reference
sequence function lives in project/ and is not in public0.3.0/wheel.

Expected state starts from the explicit initial declaration and carries ONLY its
own preceding reference result, never a model output. Compare every prepared row,
complete model_output (quantization/clip/fault/projection/next_state) and final state
using typed canonical exact comparison including float hex/signed zero. Cap detail
records at256 while counting all differences. Do not infer authentic pre-resume
history. State/source shape equivalence is scoped to these pinned helpers/wiring,
not whole-controller or mathematical all-input proof.

Worker never imports public cyberlateral_dev, model backend, Controller or native
modules. NumPy2.5.3 is required by the existing selected helpers, not a new dependency.
Helper definitions are the existing two exact inherited functions only; no whole
Controller/schema compile/import/execute. Record reference steps, exact Kernel
counts and forbidden-module observation. Checker model executions=0; reference
arithmetic/helper work is NONZERO. Unit/gate producer/model work is additional.

## Publication, identity and errors

Canonical `REFERENCE_CHECK.json` plus `SHA256SUMS.txt` only, deterministic/path-free.
Record input file SHA ledger, reference source hashes, interpreter version/NumPy,
reference expected-result SHA, steps/counts, first/all-bounded differences and gates.
No old producer identity equality or origin authentication claim: saved producer
identity and currently observed reference identity are different concerns.
Check current reference source identity before/after subprocess; fail if changed.
Trusted cooperative source/runtime boundary, not hostile-process/OS attestation.
Unexpected worker failures are hard errors, never MATCH; do not expose stderr/input
contents in public error messages. Preserve partial output after write failure.

## Acceptance

Tests precede implementation. Cover saved sign/resumed inputs and all six R35 valid
fixtures, exact counts and independent state. Consistent saved arithmetic mutations
(clip bounds, output/history, fault and projection) must report DIFFERENT, not be
accepted merely because checksums/cross-record duplication agree. Invalid last
sample/source/output must reject before reference work. Include missing/checksum/
symlink/FIFO/oversize input, moved-input byte identity, worker/source failure and
fresh-process public-model/native import barriers. Preserve raw producer outputs.
Full existing component gate, Ruff/Ty/Codespell/own compile/wheel checks must pass.

Actual r/T2/vehicle scale remain null; R_BUDGET UNRESOLVED, Static Gate FAIL,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/V/F71 NOT_ALLOWED.
F61, actual r/dt, vehicle inputs/installation, Runtime/Controller/CAN remain0.
