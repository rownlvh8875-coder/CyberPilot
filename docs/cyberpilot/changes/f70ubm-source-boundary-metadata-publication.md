# F70UBM source boundary metadata publication

## Identity and purpose
- Area: Cyber Validation. Publication of a frozen metadata-only standalone module.
- Baseline: 08eaf10250b6a005fd9bc74f74d2ec7f67c61e79.
- Branch: feature/f70ubm-source-boundary-metadata.
- Vehicle applicability: recorded metadata equality only; no physical vehicle approval.

## Original references
- Original external delivery ZIP SHA256: e7519edaa6678745f6cff503d2bcdab082461efe2c5d87d8feb04d997d9f3d58.
- Raw module/test/artifact/document bytes are copied without edits under tools/cyberpilot/f70ub_metadata.
- Original README/DESIGN/PLAN remain historical descriptions of the external local stage. This publication record authorizes repository placement and CI only.
- New successor publication mapping and the full baseline 202 test IDs are explicit before new execution.
- Source pipeline: frozen JSON metadata -> strict contract/hash validation -> metadata-only admission flags. No calculator consumer or runtime hook.
- Existing repository license and attribution apply; no new upstream control code or dependencies are introduced.

## Changes and expected effect
- Added standalone files, publication inputs and this record; one isolated workflow is added separately.
- No existing F70U/F70PR/reference source, contract, workflow, threshold or safety enforcement is modified.
- Constants are frozen hashes and parser resource bounds, not vehicle rate budgets.
- State: no mutable trust cache; deterministic canonical JSON; fixed error codes.
- No Controller, Runtime, CAN, RLOG, candidate evaluation or numerical input adapter.

## Regression risk and acceptance
- Exact source bytes, relative layout, 45 original test IDs, 202 baseline test IDs and generated six-file hashes must match.
- Test count: 45 + 56 + 61 + 2 + 83 = 247, no failures/errors/skips.
- Ruff/Ty/Codespell/compile and two fresh byte-identical generations.
- Every baseline tracked path must retain mode/OID; additions must match the publication allowlist.
- Prior stage-specific branch/history scope verifiers are not repurposed. New publication tree checks use this exact baseline, while old suite/artifact/quality functions run unchanged.
- Local failure blocks publication. After push, exact-head CI failure is final for this stage; no edit/rerun.
- Rollback: leave the new branch unmerged. No vehicle or runtime deployment is authorized.

## Validation method and actual results
- Planned: local full verification then two commits, ordinary push and exact-head automatic CI.
- Actual command results are recorded in external F70UBM evidence; this immutable pre-execution record does not claim unrun success.
- Replay, simulation, shadow and vehicle application: NOT_RUN and outside scope.

## Handoff
- Existing F70UB instance remains BLOCKED; seven technical fields and two owner facts remain unresolved.
- R_BUDGET_UNRESOLVED, SOURCE_SCHEMA_UNQUALIFIED=6000, candidate NO-GO, D2/F19/NATIVE restrictions, RUNTIME_NO_GO and F64 historical failure remain.
- F70V/F71 remain disallowed. Only after publication PASS may F70UC be designed.
