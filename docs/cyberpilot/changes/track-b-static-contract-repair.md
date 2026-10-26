# Track B: guarded type contracts and exact API spelling

## Identity and purpose

- Area: Validation / Static CI. Baseline feature688067298b414b15fa0ad87797f8a7519b5b3fd0; PR1 remains Draft.
- Scope: nonfrozen type expressions, exact spelling exceptions; original test/helper files restored. No numerical/control algorithm, model, source pin, reference, authority or workflow changes.
- Status: local targeted validation passed; upstream Static remains blocked by unresolved typing diagnostics. GitHub results belong to the resulting commit and are reported separately.

## Original references and call paths

- Repository rownlvh8875-coder/CyberPilot, feature/cyber-autotune; develop c8fb906815530460ed156f14e09e1f312bb0f851. Existing licenses and submodule pins preserved.
- `coordinator.py` and Cyber Long `policy.py`: timestamps have fixed four/three components; successful strict zip materialization preserves that cardinality. Grounded `typing.cast` retains the original generator, validation and watermark computation.
- Offline optimizer and path-tracking casts follow existing exact numeric guards or constructor-validated immutable rate configuration. Casts return the same object; no guard, assertion, clipping, ordering or failure branch is added/removed. No Any or ignore is introduced.
- `torque_gram_tls._valid_request`: early False is Python bool; the final unchanged NumPy comparison returns np.bool_. The union return annotation records the actual contract. Its consumer uses truth testing.
- Comfort-test explicit imports and the test-only HTTP callback correction were withdrawn after the actual V2 source gate rejected changed original test files. All test/helper bytes remain at the original baseline. The missing-import warnings and callback diagnostic remain unresolved; no gate or source-pin amendment is made.

## Changes and expected effect

- Ten identity casts in four files resolve statically lost tuple/numeric invariants without changing values. The NumPy return annotation records one actual return contract. Test import/helper changes are not retained.
- Codespell adds only exact `assertIn,writeable,ba,iff,labelled,cancelled,metres,acknowledgement` exceptions. All original dictionaries, paths and skips remain; ty settings are unchanged. Existing valid APIs and UK text are preserved.
- No thresholds, weights, tolerances, controller parameters or actuator consumers change. Cyber Long/Lateral algorithms and native invocation/publish paths are unchanged.

## Regression risk and acceptance

- Before: ty1170errors/5warnings, codespell512; 231 frozen source hashes match.
- First candidate: ty1158errors/0warnings, codespell0. After restoring all original test/helper bytes: ty1159errors/5warnings, codespell0. Actual local rerun confirms11 removals and0 additions. All remaining174 frozen typing instances in49files are preserved; intended negative-input/immutable-write tests remain untouched. No blanket suppression is allowed.
- Exact executable AST comparison after only introduced typing casts/imports confirms unchanged original guards, assertions, state updates and arithmetic in the four observer/offline modules. NumPy predicate type/value witnesses match before/after for valid and invalid inputs.
- Source identity is not limited to the aggregate231 list. A broader HTTP callback candidate caused existing source-identity failures (180passed/1failed/8errors). All production HTTP candidates were restored byte-for-byte; no published receipt or pin was resealed. The same18-module suite then passed226tests. The first commit retained the test helper and two test imports; actual GitHub V2 run39395292734 then failed CI_ORIGINAL_TEST_SOURCE_CHANGED before build. All three test/helper files were restored exactly in a follow-up commit; the V2 gate and historical tests were not weakened.
- Further producer typing changes can invalidate persisted source identities even outside231; they need separate version/contract review, not automatic cast insertion.

## Validation method and actual results

| Check | Actual local result | Limits |
|---|---|---|
| Core/comfort/negative tests |62passed baseline;62passed after type changes|Original assertions unchanged|
|18-module source/HTTP/torque regression after restoring candidates|226passed|Rejected candidate failure retained in external evidence|
|First candidate helper and Gram/cluster TLS tests|17passed|Helper change subsequently withdrawn; no private input or live learner|
|Original lint command in static-only environment|Final:8other checks PASS;codespell PASS;ty FAIL1164diagnostics (1159errors/5warnings)|Unit environment has5additional test packages; separate65-distribution static environment respects original dependency limits|
|Codespell witnesses|Valid names accepted; teh/recieve/lowercase assertin/colour still rejected|All original dictionaries retained|
|Integrity|231frozen hashes match; no source-pin/LFS/submodule edit; TrackC reviewed artifacts unchanged|TrackC evidence remains bound to its original688 source; no replay rerun|

## Handoff

- Remaining diagnostics include deliberate negative tests, analyzer shape limits, raw-source-bound files and unreviewed per-symbol contracts. Diagnostics are not all runtime defects. Full Static success is not claimed.
- External structured records include file/line/column/tool/rule/message/severity/frozen/test/root group/eligibility, with original and unique counts separately. Unknown root causes remain UNKNOWN.
- No controller/planner/native kernel/scientific frozen amendment, private E2, HOLDOUT, vehicle operation, reference update, PR Ready/merge, or repository policy change is authorized or performed. D2 remains PERFORMANCE_NOT_EVALUATED; selections null; HOLDOUT CLOSED; vehicle authority NONE.

## V2 source-contract restoration

- Actual PR-event V2 run39395292734 failed at source verification with CI_ORIGINAL_TEST_SOURCE_CHANGED; setup/publication passed, build and downstream tests were not executed. This is a real rejected candidate, not a V2 success.
- The independent CI contract also freezes the original test directory contents relative to5af7b52d9fd16f43e1def6f9b75e9f7913d14f53. The231 aggregate alone was insufficient. Three test/helper changes are restored to688 baseline in a separate ordinary commit. No history rewrite, test exclusion, gate modification or pin amendment.
- After restoration, the exact V2 source_integrity() routine passes locally:231frozen pins/252pointer members/source lock, no conflicts. Materialized payloads were not reverified by this particular source-only call. Related62tests and17helper/TLS tests pass again in fresh isolated processes. Final11typing diagnostic removals/0new; five original import warnings remain.
