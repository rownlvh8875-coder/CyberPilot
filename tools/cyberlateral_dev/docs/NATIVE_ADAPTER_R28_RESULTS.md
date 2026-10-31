# R28 controlled synthetic native adapter — local qualification

Status: `F70UGZ_R28_CONTROLLED_SYNTHETIC_NATIVE_ADAPTER_PASS`

Qualified executable source: `12a45e622af0e2429c54d39397ad610121bbb27f`.
R28 incremental base: `b92e09d1c73219b4ce299e1677caa2fe57ec0155`.
This results-document commit changes documentation only. The final exact-head
pure-CI run and Draft/evidence receipts are preserved in the external evidence
package; this document does not predict their outcome or equate native work
with GitHub execution. Native GitHub CI is NOT_RUN.

## Verified local results

- Clean baseline410 pure tests; final primary and committed relocated trees each
  pass421 pure tests (11 added),137 own Python compilations, Ruff/Ty/Codespell.
- Two independent isolated workers per location:15 real-native tests/worker and
  three post-context rejection assertions/worker. Four final workers total;
  R28 worker model/F61/r/dt/actual-input execution counts are all0.
- Three independent exported-data tests/location; unchanged R27 suite data checks
  60/location. Total126 data-only assertions-as-tests passed across both locations.
- Whole native folder Ruff/Ty/Codespell passes;29 Python files compile in memory.
- R27 regression passes in both locations:8 modes/16 workers/454 model calls
  per suite,908 qualification model calls across both. Pure/unit/CI model work
  is additional; this is not an aggregate whole-stage execution count.
- All generated manifests verified. Public0.3.0 wheel remains46,646 bytes,
  27 RECORD entries, SHA256
  `3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c`.
- Original10 source guards and original checkout/submodule clean observations
  match; only additive R28 component files changed, no old qualifier/model edits.

Portable primary/relocated bytes match exactly:

| Artifact | SHA256 |
| --- | --- |
| R28 observations | `c4ad7032e6e1979f501a81162284141a0db6bb4667f9c239d74dbc37aebbd364` |
| R28 summary | `1a312ca451ef513928888a8c6d5bc4c7dfee8e72697806fb1a6426a6f704350a` |
| R27 suite summary | `a80be536149889e462553b067d1629d6aa3a34fa4c8996ce6581e853d71bffdc` |
| R27 Korean report | `6316b71e487b0daf3be58ea174c401e1eb794d153dffb6662dc7e24a225c2644` |

R27 values also match the previous R27 release's portable results. Environment
receipts, absolute paths, full pure summaries/manifests are deliberately not
equated; they retain the actual observed environments.

## Independent review and limitation

One fresh whole-branch reviewer found Critical0/Important0/Minor1. Independently
ran11 pure tests and3 exported-data tests, verified native manifests and portable
comparisons, and inspected primary421-test result. The reviewer did not execute
native code or attest OS/vehicle provenance; historical work was reviewed at
architecture/dependency boundaries, not exhaustively line-by-line.

Deferred M1: add a pure `construct()` malformed-spec backend-allocation tripwire.
Current preflight-before-allocation order is correct by inspection and existing
tests reject invalid specs. This is regression hardening, not a current wrong
mapping or a blocker to the development-only Draft handoff.

## Gates remain closed

This now supplies a common internally constructed synthetic-message reader,
not a generic external reader or actual custody qualification. Declared history
remains declared; invocation order is not time. Actual r/T2/scale are null.
R_BUDGET=UNRESOLVED; STATIC_EVIDENCE_GATE=FAIL; actual input/activation,
F70UH/F70V/F71 NOT_ALLOWED. Controller/Runtime/CAN/F61/r/dt remain0.
Candidate/Runtime NO_GO; NATIVE_EXACT_REPLAY NOT_PROVEN. No main merge or install.

Next possible development scope: explicitly design a synthetic adapter-to-model
sequence regression; do not infer permission for real messages or deployment.
