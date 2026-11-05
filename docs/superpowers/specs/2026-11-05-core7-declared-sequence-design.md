# CORE7 — Declared Synthetic Sequence Check

## Intent and author-selected scope

Check all adjacent current transitions of one explicitly supplied synthetic
sequence using unchanged CORE5 preflight and CORE6 comparison. Preserve every
declaration, report every mismatch, and never treat an unchecked prefix or empty
sequence as success. Owner delegated ordinary offline implementation decisions
and opted out of repeated design questions.

Choose declared-entry diagnostics: each step uses that frame's declared entry
state, not the preceding computed state. A computed rolling simulation would
change the tested inputs after a mismatch; it is a different feature and is not
silently substituted. Streaming/checkpoint/automatic repair and first-frame
prehistory reconstruction are deferred. One small module/tests/guide, no CLI or
public wheel/workflow/JSON changes. Existing Python3.12.13/stdlib, no installs.

## API and result

New `integration_tools/synthetic_sequence_check.py` exports
`SequenceCheckError(ValueError)` with fixed `.code`,
`SyntheticSequenceCheckV1(frames,contexts)` and
`check_synthetic_sequence(frames:object,contexts:object)->SyntheticSequenceCheckV1`.

All inputs required. `frames` must be an exact tuple of CORE4 frames, length2..4096.
`contexts` must be an exact tuple of CORE5 SyntheticModelContextV1, length
len(frames)-1. Context i describes current frame i+1 with previous frame i.
The first frame is an uncomputed anchor. Capture sequences and model indices
remain different roles; explicit context model indices must additionally be
consecutive. No context is inferred from capture sequence or timestamps.

Result is frozen/slotted and validates/computes in __post_init__, including
normal direct construction/dataclasses.replace. Derived(init=False):
`checks:tuple[SyntheticTransitionCheckV1,...]`, `status:str`,
`differing_transition_indices:tuple[int,...]`, `checked_transition_count:int`,
`synthetic_model_steps:int`. Fixed(init=False):

- contract_id=`CORE7_COUNTERFACTUAL_DECLARED_SEQUENCE_V1`
- validation_claim=`ADJACENT_DECLARED_CURRENT_TRANSITIONS_ONLY_NOT_COMPUTED_ROLLOUT`
- state_feed_rule=`DECLARED_ENTRY_EACH_STEP_NO_REPAIR_OR_COMPUTED_ROLLOUT`
- first_frame_transition_checked=false; prehistory_checked=false;
  source_identity_reauthenticated=false; v4_payload_allowed=false;
  f61_input_allowed=false; actual_activation_allowed=false.

## Validation/calculation order

1. Exact result class before reads: `SEQUENCE_TYPE`.
2. Exact tuple containers before len/iteration: `SEQUENCE_CONTAINER`.
3. Frame count2..4096 and contexts count=frames-1: `SEQUENCE_COUNT`.
4. For every adjacent pair in order, call unchanged
   prepare_model_input(frames[i],frames[i+1],contexts[i]). Wrap ModelInputError
   as `SEQUENCE_INPUT:<i>:<code>`. i is zero-based transition ordinal, not capture
   sequence/model index; target frame ordinal is i+1. Complete all preflight
   checks before any public model step. Existing CORE3/4/5 exact classes,
   settings/state/counter links, time/context/reset, scopes/flags/override and
   quantization checks remain unchanged. Preflight quantization is nonzero work;
   zero public steps does not mean zero total computation.
5. After all inputs validate, require contexts[i].model_index ==
   contexts[i-1].model_index+1 for each i>=1, else `SEQUENCE_MODEL_ORDER:<i>`.
   No model step has run on any such failure.
6. Call unchanged check_synthetic_transition on each raw adjacent pair and its
   context, in order, exactly once per transition. CORE6 revalidates its input;
   do not add a trusted-prepared shortcut. A DIFFERENT result is retained and
   does not skip later transitions. Each later step still uses declared entry
   state/counter, not an earlier computed result. Wrap TransitionCheckError as
   `SEQUENCE_TRANSITION:<i>:<code>`. Other exceptions propagate. A late model
   failure may have executed a nonzero prefix or partial failed work; produce
   no completed/partial sequence result and no zero-work assertion.
7. differing_transition_indices lists all i with checks[i].status=DIFFERENT,
   in order. No differences means MATCH, otherwise DIFFERENT. Counts are
   len(checks)=len(frames)-1 and sum(each completed CORE6 synthetic_model_steps).
   Install derived fields only after the entire sequence completes.

A completed MATCH proves adjacent declared entry links and both current saved
state/counter values for frames1..end against supplied synthetic inputs. It does
not validate the anchor's own transition or history, full output/trace, actual
capture/source/settings, physical timing/rate, safety, V4/F61 or vehicle use.
No reset/epoch boundary is bridged; split into separate sequences explicitly.
No persistent dedup/cache/stream continuation or hostile-mutation sandbox.

## Literal expectations and verification

Four declared frames raw requests -0.25,+0.5,-0.5,+0.25; scale16/up2/down5/
allowance7/factor1/multiplier3. Anchor saved command-2,counter4. Current frames
entry/saved commands: -2->2,2->-2,-2->2; counters4->5,5->6,6->7. Context model
indices5,6,7; previous_integer_requests-4,8,-8; driver1.5,angle85. Expected
computed states(6,8,2,5),(7,-8,-2,6),(8,4,2,7), aggregateMATCH,3steps.

For no-repair diagnostics change first target's saved command to10 and next
entry to10; second saved/third entry to5 and third saved to4. Expected statuses
DIFFERENT,MATCH,MATCH, computed commands2,5,4. This distinguishes declared
entry from computed rolling input. Late counter mismatch and all-mismatch cases
must retain every row. Late invalid context, broken link, epoch/reset/time/order,
length/type errors must perform zero public steps even after a valid prefix.

Test RED then GREEN with actual model/literal expectations. Cover exact tuple/
carrier types and hostile objects, minimal/maximal sequence, bounds/end indices,
explicit context count/model order, direct/replace construction, immutability,
all false authority flags, late failure and fresh-process import isolation.
Expected final tests=1041+actual new methods, own compiles248. Fresh baseline
1041/246; final full dev.py verify/static/wheel, one fresh whole-branch review,
independent literal/rational sequence acceptance twice, source/Manifest/ref/
real cloud consumer checks. Frozen wheel SHA
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.

## Preservation

Base1651203989eb44186c6a14aec0a6d531807a81ac. Existing host linked worktree,
local stacked branch; old CORE1~6/runtime/public src/locks/workflows/imported
files/source profiles unchanged. Only new module/test/guide/spec/plan and
component README/backlog. No push/merge/PR/CI dispatch/HF/network work/cleanup;
preserve prior branches/worktree/evidence and external receipts.

Synthetic model work is explicitly nonzero. Actual inputs/F61/Controller/
Runtime/CAN/actual r calculation0. Actual r/T2/vehicle_scale=null;
R_BUDGET=UNRESOLVED; STATIC_EVIDENCE_GATE=FAIL;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; F70UH/F70V/F71/actual activation=NOT_ALLOWED.
