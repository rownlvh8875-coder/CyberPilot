# R29 fixed synthetic adapter→model sequence results

Status: `F70UGZ_R29_FIXED_SYNTHETIC_ADAPTER_MODEL_SEQUENCE_PASS`.

Qualified executable source: `8dad979247d919f229949f976993f00397e4ff8d`.
Reviewed HEAD: `c3740297d786b89669bf9c3a1c5b123748fd24b4` (usage doc only after source).
Incremental base: `e34b128c8ca45ed3e0d85ab2f9b8694b171a8f34`.
This results commit adds documentation only. Final exact-head pure CI and Draft
publication/sealing receipts belong to the external evidence package; their
success is not predicted by this local-results document. Native GitHub CI NOT_RUN.

## Implementation and checks

The unchanged R28 adapter builds/owns/reads native synthetic CC/CS bytes; the new
closed gate checks exact record metadata/stamp and complete registered input,
then the unchanged model consumers verify complete outputs. Actual verified
next_state carries into the next synthetic invocation. Profiles are independent
and explicitly initialized; no actual call history or elapsed time is inferred.

- M1 closed:3 construct() allocation-tripwire regression tests. Deliberately moving
  validation after allocation caused3 RED failures; restoring exact R28 source
  restored3 GREEN. No retained change to R28 executable source.
- New19 pure tests PASS; primary and committed relocated full pure gates each
  pass440 tests (baseline421),141 own compilations, Ruff/Ty/Codespell.
- Whole native folder Ruff/Ty/Codespell and33 in-memory compilations PASS.
- Each location:2 R29 workers, each4+99=103 model steps; observed invocation counter
  equals row count, every complete input/output matches exact pinned literals.
- Each location:5 independent R29 data checks,3 R28 data checks,60 R27 data checks.
  Total136 data-only tests across both locations PASS; all generated manifests PASS.
- Unchanged R28 and full R27 native regressions PASS at both locations.
- Formal qualification model counts: R29=412,R28=0,R27=908,total1320. Exploratory
  R29 run206 additional. Pure/unit/CI model work is further additional; no aggregate
  whole-stage zero or whole-stage1320 claim is made.
- All pre-existing tracked Python/reference JSON guards and original10 source
  guards match. Public0.3.0/model/build/lock remain unchanged. The46,646-byte public
  wheel SHA remains `3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c`.

Primary/relocated portable bytes match exactly:

| Artifact | SHA256 |
| --- | --- |
| R29 observations | `20530fe93d6bf08bf6408d72a67adbe2a547280970007fa1ce4878770d16f5ca` |
| R29 summary | `2aa8c514181319213a66ea45015c8cef4445ea587c7d3442098721b4bb5d23aa` |
| R28 observations | `c4ad7032e6e1979f501a81162284141a0db6bb4667f9c239d74dbc37aebbd364` |
| R28 summary | `1a312ca451ef513928888a8c6d5bc4c7dfee8e72697806fb1a6426a6f704350a` |
| R27 suite summary | `a80be536149889e462553b067d1629d6aa3a34fa4c8996ce6581e853d71bffdc` |
| R27 report | `6316b71e487b0daf3be58ea174c401e1eb794d153dffb6662dc7e24a225c2644` |

R28/R27 values also match their historical pins. Actual environment receipts,
absolute paths and complete pure summaries/manifests are not equated or normalized.

## Review and limits

One fresh final whole-branch reviewer:Critical0/Important0/Minor0, no deferred minors.
Independently ran19 pure tests, both complete R29 export validators, five literal
data tests/location and manifests. Inspected both440-test executor runs and native
completion logs. Reviewer did not execute native code; historical architecture
was examined at integration boundaries, not every historical line recertified.

Native input reading does not promote output to CAN wire: model projections still
say SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE. Invocation-only sequence evidence is
not time/custody/vehicle authority. Cooperative single-threaded process only.

F61/Controller/Runtime/CAN/actual input/r/dt/calculator-input execution0; actual
r/T2/vehicle scale null. R_BUDGET UNRESOLVED, Static Gate FAIL, actual custody
NOT_QUALIFIED, generic external reader NOT_IMPLEMENTED, actual activation/F70UH/
F70V/F71 NOT_ALLOWED. Candidate/Runtime NO_GO; NATIVE_EXACT_REPLAY NOT_PROVEN.
No main merge, installation, deployment, physical safety or performance approval.
