# R29 controlled synthetic adapter-to-model sequences

Intent: connect R28's actual owned synthetic-message reader to the existing
public0.3.0 development model and prove continuous state carry. User approved
this scope and delegated ordinary implementation choices, with no repeat menus.

## Approach selected by executor

Add fixed R29 orchestration; preserve all R19–R28 code and public model/wheel/lock.
Reuse the exact sealed R23 four-step sign-change/inactive/reactivation reference
and R26 ninety-nine-step negative-driver/fault/reset reference. They pin complete
inputs, intermediate traces, schema projections and outputs. This avoids inventing
new expected numbers or treating current outputs as an oracle. A generic stream
adapter or a model/API rewrite would exceed this task and is not selected.

## Profiles and source authority

`SIGN_CHANGE_4`:
R23 reference SHA221b04aae7a149409f5f91aa516e7f9fcefe090958e785d91bc6fd4153161e97;
requests promoted Float32 0.3,-0.25,0.25,0.25; active except index2;
driver/angle0.0. Literal next states distinguish previous request5 from applied2,
and inactive limited2 from final0.

`NEGATIVE_CYCLE_99`:
R26 reference SHAf3b60afc2e3ba8b100ee9dbcb2a125f9c27c797c3d6b4af7b882cc7c069390f8;
request-1.0, driver8.5, angle-85.0 except index92:-84.5; active except index94.
Pin fault counters89/90/0/1, negative driver limit, inactive reset and reactivation.

Both use exact synthetic limits16/2/5/7/1/3, NOT real scale or vehicle authority.
Each profile starts explicit State(0,None,0,0); thereafter only the preceding
verified model output supplies previous_requested, previous_applied and counter.
Sequence/capture stamps are `R29_<profile>` / `entry_<index>`. Invocation is
order only, not timestamp/dt. Model calls103/worker for both complete profiles.

## Interfaces

`consume_prepared(profile_id,index,PreparedNativeInput)` accepts only one exact
registered preparation with exact R28/R21 metadata, stamp and complete pinned
input/state. Existing consumers validate before exactly one p.step and check
the complete pinned output. It is a closed development gate, not native custody
authentication; fabricated Python records do not become actual observations.

`run_registered_sequence(adapter,profile_id)` uses R28's private exact adapter
type from a qualified session, builds SyntheticSpec from fixed input recipe and
carried state, constructs/reads owned bytes, independently compares conversion
to the existing ratio oracle, then calls consume_prepared. It records frozen
input/state/output projections and byte hashes. Stop at first rejection; no
partial successful final report, no fallback or repeated model invocation.

Only `SIGN_CHANGE_4` and `NEGATIVE_CYCLE_99`; no arbitrary frames/data/history,
profile subset CLI, user state, numeric policy, timestamp or r flags. The fixed
runner uses two fresh -I -B workers, empty cwd/private cold cache and unchanged
R28 qualified context. Separate receipts; portable observations must match.

## M1 regression and verification

Add pure construct() malformed-spec tests with an allocation tripwire. Current
R28 order is already correct: prove mutation sensitivity by temporarily moving
validation below allocation, observe RED, restore exact original source, GREEN.
No R28 executable change is retained.

Pure tests cover closed gate type/metadata/profile/state rejection, no step on
invalid input, complete output validation and fixed profile bounds. Native
worker reads real R28 bytes. Independent data-only checks pin every step/state
link and important boundary literals. Full pure gate, R28 and R27 regressions,
all native static checks and fresh relocated environments must pass. Formal
R29 model count206/location,412/two locations; R27 regressions908 additional;
pure/unit/CI/exploratory calls are additional, not a total-stage zero claim.

## Non-goals and handoff

No F61/Controller/Runtime/CAN/actual input/r/dt, candidate evaluation, installation
or deployment. R_BUDGET=UNRESOLVED, Static Gate=FAIL, actual r/T2/scale null;
actual custody NOT_QUALIFIED, generic external reader NOT_IMPLEMENTED, actual
activation/F70UH/F70V/F71 NOT_ALLOWED. Public0.3.0 and original10 guards unchanged.
Feature commits/push and existing Draft PR2 only; no main merge/force push.
One fresh final reviewer; exact-head dedicated pure CI; deterministic evidence
ZIP twice with fresh extraction and all nested manifests checked.
