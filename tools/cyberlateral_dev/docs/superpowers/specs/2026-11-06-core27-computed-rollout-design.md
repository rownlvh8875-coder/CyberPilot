# CORE27 Counterfactual computed-state rollout

Builder-selected offline increment under delegated execution/approval opt-out.
Advance from independent declared-entry diagnostics to an explicit computed-state
chain,without changing CORE7 or the existing model/arithmetic.

## Approaches and scope

Changing CORE7 would silently reinterpret historical diagnostics. Chosen: a separate
pure API using CORE5 preflight and unchanged public model.step. A stream/checkpoint/
file reader/CLI or production bridge is unnecessary for proving the state-feed rule
and is excluded. No actual vehicle input,F61,real rate/dt policy or deployment.

## Inputs and validation order

`integration_tools.synthetic_sequence_rollout.rollout_synthetic_sequence(
frames: object, contexts: object)->SyntheticSequenceRolloutV1`.
Same explicit counterfactual carriers as CORE7: exact tuples;2..4096 frames,contexts
count frames-1. Exact result type required for direct constructor/subclass handling.
Preflight EVERY adjacent pair with unchanged CORE5 prepare_model_input,then check
all model indices advance by1. Do not derive index from sample time or sequence.
Late invalid data/order/epoch/reset/settings/active/override/domain reject before
ANY public model.step;preflight numeric work may already be nonzero.

## State feed and comparison

First entry is prepared[0].model_state: a supplied declaration,not a proven anchor
transition or reconstructed prehistory. Each subsequent entry is the identical
previous model output.next_state object,NEVER another declared entry or repaired
snapshot. Use each prepared current model_input as the exogenous sample.
Call model.step exactly once per transition,even after differences. Reuse CORE6
_next_state(output,index) to validate owned model output type/state/index/domains.
No new arithmetic/normalization/limiter formula or retry/fallback.

Each immutable SyntheticRolloutStepV1 records prepared,entry_state,output,
entry_differences,output_differences,status. Differences are immutable
SyntheticRolloutDifferenceV1(field,declared:int,computed:int).
Entry comparison ordered previous_requested,previous_applied,angle_counter against
prepared.model_state,with field labels entry_previous_requested,
entry_previous_applied,entry_angle_counter. Output comparison ordered
saved_limited_state,saved_angle_counter against output.next_state.previous_applied/
angle_counter. Row MATCH iff both difference tuples empty. Preserve all declarations,
including inconsistent saved values;computed state propagation does not repair them.

SyntheticSequenceRolloutV1(frames,contexts) is frozen/slotted,computed in __post_init__.
Derived init=False:steps,initial_declared_state,final_computed_state,status,
entry_differing_transition_indices,output_differing_transition_indices,
differing_transition_indices(union in order),checked_transition_count,
synthetic_model_steps. Successful counts=frames-1,aggregate MATCH iff all rows MATCH.
contract_id CORE27_COUNTERFACTUAL_COMPUTED_STATE_ROLLOUT_V1;
validation_claim COUNTERFACTUAL_COMPUTED_STATE_CHAIN_NOT_SOURCE_OR_PREHISTORY_PROOF;
state_feed_rule FIRST_DECLARED_ENTRY_THEN_COMPUTED_NEXT_STATE_NO_RESEED;
computed_state_fed true;first_frame_transition_checked/prehistory_checked/
source_identity_reauthenticated/v4_payload_allowed/f61_input_allowed/
actual_activation_allowed false. Direct constructor/replace rerun preflight+model;
derived fields cannot be injected. Owned result row records are not arbitrary-input
validators;cooperative frozen objects are not a hostile-Python sandbox.

## Literal examples and errors

Existing sign-cycle states: (6,8,2,5),(7,-8,-2,6),(8,4,2,7),all MATCH.
Existing declared-difference has the SAME computed states,but output differences
at0/1/2 and entry differences at1/2. CORE7 still produces2/5/4 from declared entries;
CORE27 produces2/-2/2 and never adopts the declared10/5 between calls.
Existing late-invalid rejects ROLLOUT_INPUT:2:MODEL_DRIVER with public steps0.

SequenceRolloutError.code:ROLLOUT_TYPE,ROLLOUT_CONTAINER,ROLLOUT_COUNT,
ROLLOUT_INPUT:i:<CORE5code>,ROLLOUT_MODEL_ORDER:i;
model ValueError/ArithmeticError ->ROLLOUT_MODEL_FAILURE:i:WORK_MAY_BE_NONZERO;
CORE6 result validation ->ROLLOUT_MODEL_RESULT:i:<CORE6code>:WORK_MAY_BE_NONZERO.
No returned partial result on failure;prefix/failed-call work may be nonzero.
Unexpected exceptions propagate;no result/state/input repair or retry.

## Verification and authority

TDD literal chains,declared-vs-computed distinction,entry/output/counter divergence,
inactive/resume,faultcounter boundaries,differencethenMATCH,minimum/maximum domain,
full preflight beforesteps,order/foreign carriers,model failure/result rejection,
constructor/frozen/flags/no IO. Baseline CORE5/6/7 tests and saved/preflight consumers,
fresh full1665+actualnew tests/306own compiles/static/frozenwheel unchanged.
Independent literal oracle table for existing three cases,API/directconstructor/
blockedproducer-F61 runs twice,explicit public model steps3/3/0 pervariant (not0),
no independent reference-model executions or imported rollout oracle implementation.
Registered635files/protected627oldbytesmodes/refs30,onefreshfinalreview,unsignedseal.
Existing CORE3~26/helper/model/wheel unchanged;only three guide links edited.
No actual r/T2/scale values,all denial gates retained;synthetic arithmetic/nonzero
unit/gate fixture work disclosed. No source/arithmetic-origin/prehistory/actual
native replay/vehicle performance/qualification authority. Keep hostworktree/branch/
external evidence,no merge/push/PR/CI/HF writes. Linux CPython3.12.13 cooperative scope.
