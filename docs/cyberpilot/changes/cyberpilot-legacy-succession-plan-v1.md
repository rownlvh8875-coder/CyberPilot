# Legacy V1 to Legacy V2 succession plan V1

Status: Proposed / NOT EFFECTIVE. Decider: repository owner, by explicit future approval.
This record is additive governance. Installing it neither activates succession nor disables a workflow.
The existing Shadow execution contract keeps its historical Shadow-only scope; its past runs are not reclassified as official succession.

## Decision and scope

Recommend B (repository-level operational retirement of V1) after A (both active during exact-HEAD qualification).
Keep all Frozen V1 YAML and all historical contracts/receipts byte-identical.
The prospective official responsibility is feature/cyber-autotune push and PR validation, not branch protection, vehicle authorization or whole-repository green status.
Qualified handoff is limited to feature/cyber-autotune push and PR1 feature/cyber-autotune to develop. The YAML still triggers unfiltered PRs, but other base branches are unqualified by this proposal.
Do not rename the workflow or `LEGACY_V2_SHADOW_FULL_VALIDATION`; GitHub identity and historical evidence remain unambiguous.
The Full CI V2 `CYBERPILOT_FULL_CI_V2_COMPLETE_COVERAGE_GATE` remains independently required by this qualification plan.

## Options

| Option | Frozen / integrity | CI and coverage | Maintenance / rollback |
| --- | --- | --- | --- |
| A: keep V1 active, designate V2 prospectively | No source changes | All original commands remain, repeated V1 timeout continues; no duplicate cost reduction | Lowest immediate operational risk; use for staging |
| B: disable V1 via workflow state after explicit approval | No Frozen byte/hash amendment; formal operational responsibility amendment required | V2 retains all13 validation intents plus5 extra prerequisites and final evidence; V1 historical CANCELLED stays CANCELLED | Removes future duplicate V1 triggers; re-enable is reversible; affects repository workflow across refs |
| C: edit Frozen YAML | Changes original SHA30fbd6d... and breaks current Frozen231/FullCI V2 checks | Requires a new prospective verifier/amendment closure, not replacing historical pins | Highest scope and review burden; reject for this migration |

## Validation scope map

The 13 original intents map to checkout, setup, publication_before, build, ruff,
test_dependency, autotune_controls, attribution, syntax, lateral, json,
publication_after, clean. The Shadow adds source_lfs, native_build, native_verify,
shadow_preflight, source_after and verifies all18 plus completion in shadow_complete.
No original postcheck is removed. Original target paths and assertion sources are identical.
Two workers use unchanged original runner collect/make_batches/run_batch semantics.
Attribution retains its original thread env and 95 tests; lateral retains both original modules and16 tests.
JSON validation still covers both original policy/evidence directories, publication scans twice, clean now also rejects untracked files.
V2 additionally pins checkout, PyYAML/pytest, exact5960 IDs, baseline5927 subset,59 fixture groups and fresh explicit Native receipt.
This is a responsibility designation, not proof that V1 execution succeeded or that every V1 event already has an equivalent successor.

## Event gap and operational consequences

V1 declares workflow_dispatch; Shadow does not. Before B, the owner must explicitly accept retiring that entry while disabled.
If manual parity is required, stay at A and commission a separately versioned manual successor. Full CI V2 has different global numerical environment pins and is not an exact manual-equivalence claim.
None of these three workflow files currently exists on main; YAML declaration is not evidence of a successful default-branch manual dispatch.
Disable has no branch/ref selector: plan for repository-wide workflow impact. Do not describe it as feature-only.
Existing runs are not cancelled by disable; drain them naturally. Historical reruns/jobs require re-enabling V1 first.
Offline retrieval and verification of old receipts/source stays possible while disabled; future hosted rerun success is not guaranteed (V1 retains known Native/time limit defects).

## Stage 0: authorization and fresh preflight

No commands in the write-operation example below are authorized by this plan.
Approve the exact patch raw SHA256, target repository/feature branch, add-only two-file commit/push,
and prospective push/PR responsibility amendment separately from workflow retirement.
Immediately before any future change fetch origin; require expected FEE feature, C8 develop, PR1 Draft/Open/unmerged/auto_merge=null and clean index/worktree.
Recheck all branch protections, inherited/repository rulesets, required workflows/checks and check-name consumers.
Any existing V1 requirement blocks retirement; do not remove it under this approval. Seek a separate exact policy decision.
Confirm workflow373991727/path cyberpilot.yaml/state active and successor391281255/path cyberpilot-legacy-v2.yaml/state active.
Snapshot all policies and workflow states. Check operator Actions-write authority without searching for or exposing tokens; current write capability is untested.

## Stage 1: additive source publication (separate approval)

Apply only the two new docs in the supplied patch on the approved clean source; preserve all old files, contracts and receipts.
Review and audit publication; create a normal feature-only commit and push with no new LFS content/upload.
Keep this proposal status PROPOSED_NOT_EFFECTIVE forever as an immutable historical proposal.
Do not predict the future commit SHA in this file or overwrite old receipts to bind a new commit.
Capture new source commit/tree, PR source/base, synthetic merge ref/SHA and both parents.

## Stage 2: exact-HEAD qualification

Observe fresh automatically triggered push and PR runs; old39541785623/39541790840 are historical qualification only.
Require actual push checkout=new commit and PR checkout=synthetic merge, merge parents=(approved base,new source).
Bind workflow ID/path/hash, GitHub run ID/attempt/event, check ID/name/provider15368 and all18 stage outcomes/conclusions to each proof.
Verify same full5960 sorted ID set (SHA71a42e...), baseline5927 subset (SHAe293db...), each exactly once PASS, zero failures/errors/skips/duplicates/collection errors,59 atomic fixture groups.
Check source-before=source-after, Frozen231/LFS252/materialized251/submodule6 pins, native C/wrapper/compiler/flags/ABI/binary/receipt identity, attribution95/lateral16 and both publication scans findings0.
Require Unit, FullCI V2 producer+gate, Numerical3 and Native Bounded to succeed on the new source (push/PR where workflows provide them).
Record Static/Replay and V1 outcomes separately; neither old nor new failures may be rewritten or silently ignored.
No mandatory job may be pending, skipped, cancelled or failed at handoff. Drain in-flight V1 runs naturally, recording real conclusions.

## Stage 3: operational handoff (another explicit approval)

Only after Stage2, owner approves repository-wide disable373991727, manual-event retirement, expected before/after states and historical rerun restrictions.
Create a separate immutable activation record using the fields in the proposal (including exact proposal raw hash/receipt, qualification runs and human approval reference).
After approved operation record the actual response/status, GET state disabled_manually, successor active and unchanged policy/source snapshot. A204 alone is insufficient without GET confirmation.
If operation outcome is uncertain, perform GET reconciliation; do not assume success or repeat blind writes.
Only the completed record establishes effective prospective succession. Incomplete records remain NOT_EFFECTIVE.

Documentation-only API example, DO NOT EXECUTE during D4:

```text
PUT /repos/rownlvh8875-coder/CyberPilot/actions/workflows/373991727/disable
Expected204; subsequent GET must show id373991727/path.github/workflows/cyberpilot.yaml/state disabled_manually.
```

The actual permission is Actions write; read evidence does not prove that the current account can perform it.
Required Check / branch protection / ruleset / PR state changes are outside every stage above and require separate approval.

## Future tests and versions

Current Shadow intentionally hardcodes contract-v1/schema and5960 count/digest; a sidecar cannot make test growth accepted by runtime.
For additions preserve baseline5927 and current5960 subsets, collect new IDs and verify fixture ownership/repeats.
With separate approval add an execution-contract-v2, minimally change Shadow contract path/schema validations and workflow hash, then add succession-v2 and qualify exact new HEAD in both events.
Keep every old contract and receipt immutable; a new version must never silently accept arbitrary hashes/counts or removed tests.
The Frozen/fullCI locks need no change for this add-only proposal. Future edits to protected files require their own complete prospective amendment closure.

## Rollback

If successor fails, report official validation incomplete; never treat re-enabled V1 as an automatic PASS replacement.
After explicit rollback authority, re-enable exact workflow373991727, GET active, keep successor active and all source bytes untouched.
Re-enable does not automatically recreate missed runs. Any diagnostic rerun/dispatch needs its own approved execution and may still fail under historical V1 constraints.
Append a rollback/supersession record referencing the activation record; do not delete history, backdate evidence, reset or force-push.
The two-file proposal is inert and need not be deleted. A source revert, if chosen later, is a normal separate commit with exact-HEAD revalidation and preserved archive.

## Limits and references

No new automatic adoption-policy verifier is installed. Current workflow verifies Shadow contract-v1 only; governance activation is a human audited process, separate from runtime coverage enforcement.
No empirical D2, private E2, HOLDOUT or vehicle authority is created; selections stay null.
[Workflow disable/enable semantics](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows).
[Workflow REST interface and Actions-write permission](https://docs.github.com/en/rest/actions/workflows#disable-a-workflow).
The repository-wide impact is inferred from the owner/repo/workflow-ID interface lacking a ref selector.
