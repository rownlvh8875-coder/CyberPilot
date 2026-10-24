# Track B-2: explicit axis summary types

## Identity and purpose

- Validation / Static CI; baseline feature/cyber-autotune b0f5ae6c8875a8e03b41d1670492a362114bd357, PR1 remains Draft. Develop c8fb906815530460ed156f14e09e1f312bb0f851.
- Scope: one private TypedDict and one local annotation in synthetic_diagnostics.py. No controller, planner, model, source pin, original test, workflow, reference or acceptance changes.
- Status: local targeted verification complete; remaining Static diagnostics are not suppressed. GitHub results must be checked separately for the resulting commit.

## Original references and call path

- Source: https://github.com/rownlvh8875-coder/CyberPilot, branch and baseline above. Existing licenses preserved; no external code adopted.
- diagnose validates the exact report fields, recomputes evaluate, compares canonical verdicts and rejects incomparable evidence before _candidate. The latter summarizes already computed public synthetic metrics.
- _candidate.axes contains five integer counters, one Counter later serialized as a dict and an effect_status added after the loop. Homogeneous dict inference confused these named fields. The new private schema describes those existing values; Counter is a dict subclass.
- No additional submodule/model dependency. All six existing gitlinks remain pinned. This descriptive tool grants no runtime or vehicle authority.

## Changes and expected effect

- synthetic_diagnostics.py: import TypedDict/NotRequired; declare _AxisDiagnostics; annotate the unchanged axes comprehension. Counter initialization, arithmetic, branching, ordering, serialization and failure paths remain unchanged.
- No Any, cast, ignore, suppression, input conversion, additional runtime validation or algorithm change. No constants, parameters, state resets or fallback behavior change.
- Alternative broad dictionary types cannot preserve the per-key contract. Changing consumers or negative tests would be unnecessary and conflict with original test integrity.
- Raw source identity review includes contracts beyond the 231 aggregate. No fixed receipt pins this source. The existing dynamic source_binding deliberately changes when any covered source changes; its semantics and checks remain intact.

## Root-cause analysis and regression risk

- Fresh pinned-tool baseline: 1164 instances (1159 errors/5 warnings), 1056 distinct file/line/column/rule/full-GitLab-description keys, codespell0. After:1156 (1151/5),1048 distinct keys. Exactly8 removed,0 added; no other diagnostic location changes.
- All original804 UNKNOWN instances reviewed as records:291 B2,34 B3,1 B1,478 UNKNOWN after review. This classification does not remove diagnoses. Original B3 set211 becomes114 B3/97 B2; valid fixture setup inside rejection tests must not be mislabeled as invalid input.
- Across the original1164 instances after review: B1=15,B2=520,B3=148,UNKNOWN=481. Three prior B2 instances were returned to UNKNOWN. After the eight B2 removals, remaining counts are15/512/148/481.146 prior B1/B2 classifications are explicitly carried forward rather than claimed newly proved.
- All Frozen174 instances in49 files separately reviewed:1 B1,165 B2,1 B3,7 UNKNOWN. None changed or resolved.166 need a source-contract amendment for the proposed direct annotation/schema repair;7 need more evidence;1 deliberate mutation test stays intact. No lawful nonFrozen remedy established.
- These are diagnostic instances and symbol/mechanism clusters, not a count of independent runtime defects. UNKNOWN cases require concrete caller/producer, optional-state, dynamic callback or native fixture evidence. No vehicle correctness claim follows.
- Historical1032 versus1067 distinct counts were reproduced from the same1175 diagnostic instances: CLI headers omit expected/found details retained by GitLab descriptions.15 collapsed header groups account for35 additional full-description keys. This is a fingerprint-definition difference, not defect growth.

## Validation method and actual results

| Check | Actual result | Limits |
|---|---|---|
| Static regression witness | Before:8 file diagnostics; after:0 | Complete ty remains FAILURE1156; no masking |
| Original diagnostic tests |9 PASS,17 subtests before and after | Original assertions and helper bytes unchanged |
| Same-input oracle |18 cases byte-exact against verified baseline module; inputs unchanged | Public synthetic only; complete canonical output includes all hashes |
| Function AST comparison |All original functions equal after erasing only new local annotation | New private type class/import remain real module additions |
| Independent fixture comparison |Only3 source/evidence/report binding hashes differ | Fresh reports bind different source bytes; not identical inputs. No fields ignored in the same-input oracle |
| Original lint |All8 non-ty/non-codespell checks PASS; codespell0 | Separate original65-distribution Static environment; runtime test extras remain separate |
| Integrity |231 frozen hashes,252 pointers,V2 lock/original-test gate PASS;6 submodules match | Materialized LFS payload check delegated to actual V2 run; no asset substitution |

Additional structured external evidence preserves every original instance ID, duplicate occurrence, root symbol, syntactic caller/callee, annotation, source excerpt, confidence, proposed repair, authority and remaining evidence. Independent audits cover all174 Frozen,211 prior negative-test and804 UNKNOWN instances, with overlap reconciled by original ID.37 original public tests plus3 tuple witnesses were run during the intent audit; these are scoped evidence, not a replacement for full regression.

## Handoff and promotion

- Acceptance: no new ty diagnostics, no numerical/function-body change, original targeted tests pass, unchanged Frozen/test/LFS contracts, fresh exact-head GitHub checks. Ordinary feature commit only; no history rewrite.
- Rollback: an ordinary revert of this annotation-only change, with validation. No historical evidence is rewritten or resealed.
- Remaining work requires specific authorization: Frozen/schema amendments, original-test contract design, explicit static treatment of deliberate invalid calls, or separately scoped runtime fixes supported by reproductions. No broad exclusions proposed.
- Replay not rerun. Existing Track C evidence remains bound to its original source. D2 PERFORMANCE_NOT_EVALUATED, selections null, private E2 NOT_AUTHORIZED, HOLDOUT CLOSED, vehicle authority NONE. PR Ready/merge and repository policy changes are not authorized.
