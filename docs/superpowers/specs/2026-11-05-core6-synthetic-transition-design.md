# CORE6 — Current Synthetic Transition Check

## Intent and author-selected scope

Compare the current saved limited state and angle counter from CORE4 declarations
with one step of the unchanged public synthetic0.3.0 model, using CORE5's explicit
input preparation. A difference is data, not a preparation error, and must never
overwrite declarations or become a best-effort MATCH. Owner delegated native
offline development and opted out of repeated design approval questions.

Choose a single current-transition checker. Whole previous/current replay would
need additional previous driver/angle/prehistory authority and is deferred. Reusing
saved outputs as computed state or silently fixing them would hide failures and
is rejected. One small module, tests and guide; no CLI/JSON/workflow/wheel changes.

## Interface

New `integration_tools/synthetic_transition_check.py` exports:

- `TransitionCheckError(ValueError)` with fixed `.code`, no raw values in message.
- Frozen/slotted `SyntheticTransitionDifferenceV1(field:str,declared:int,computed:int)`.
  These are informational values; constructing one alone makes no validation claim.
- Frozen/slotted `SyntheticTransitionCheckV1(previous,current,context)` with all
  three inputs required, exact CORE4 frames and exact CORE5 context. `__post_init__`
  validates/computes, including for normal direct construction/dataclasses.replace.
- `check_synthetic_transition(previous:object,current:object,context:object)` returns
  that result. No prepared-object shortcut which could accept stale derived fields.

Derived fields(init=False): `prepared` (CORE5 result), `computed_next_state`
(public LateralState), `differences:tuple[SyntheticTransitionDifferenceV1,...]`,
`status:str` (`MATCH` or `DIFFERENT`). Fixed fields(init=False):

- contract_id=`CORE6_COUNTERFACTUAL_CURRENT_TRANSITION_V1`
- validation_claim=`CURRENT_SAVED_STATE_COUNTER_ONLY_NOT_PREHISTORY_OR_SOURCE_PROOF`
- checked_fields=('saved_limited_state','saved_angle_counter')
- synthetic_model_steps=1; previous_transition_checked=false; prehistory_checked=false;
  source_identity_reauthenticated=false; v4_payload_allowed=false;
  f61_input_allowed=false; actual_activation_allowed=false.

## Algorithm and validation

1. Require exact result class (`TRANSITION_TYPE`) before reading its fields.
2. Reuse unchanged `prepare_model_input(previous,current,context)`. Wrap only
   `ModelInputError` as `TRANSITION_INPUT:<original code>`. Invalid input runs
   no public model step. All CORE3/4/5 subsets/flags/time/order guards remain intact.
3. Call public `cyberlateral_dev.step(prepared.model_input,prepared.model_state)`
   exactly once. This is explicitly permitted **synthetic** computation, not
   Controller/Runtime/F61/original production-helper execution. Catch ValueError
   or ArithmeticError as `TRANSITION_MODEL_FAILURE`, preserving cause. Work before
   such an error may be nonzero; no result or zero-work claim is issued. Other
   unexpected exceptions propagate, not a silent DIFFERENT or MATCH.
4. Before accessing a returned next state require exact LateralOutput; next state
   must be exact LateralState. Require exact built-in int index==model_index+1,
   previous_requested and previous_applied in[-2048,2048], angle_counter in[0,90].
   Otherwise `TRANSITION_MODEL_RESULT`. Do not coerce bool/float or read foreign
   objects' fields. This checks only the consumed output boundary, not unrelated
   trace/projection consistency or arbitrary same-version package authenticity.
5. Compare current.saved_limited_state with computed_next_state.previous_applied
   (post-inactive-gate final command, **not pre-gate limited command**). Compare
   current.saved_angle_counter with computed_next_state.angle_counter. Create
   only differing field records, in that fixed field order; exact integer equality,
   no tolerances. Empty tuple means MATCH; otherwise DIFFERENT. Retain original
   inputs and computed state separately. Do not compare previous saved outputs to
   their uncomputed previous transition or certify prehistory.
6. Install derived fields only after successful computation/result checks.

Normal direct/replace construction reruns one synthetic step; no cache, stream
registry or automatic rolling replay. Frozen cooperative values are not a security
sandbox against hostile Python mutation. A match means only current declared
state/counter are consistent with this supplied synthetic input. It is not a full
output/limiter/intermediate trace parity, source observation, physical result,
vehicle policy approval, actual-source qualification or V4/F61 permission.

## Verification and concrete examples

Literal fixture from CORE5: previous raw request-0.25/current+0.5, stable synthetic
settings16/16,up2/down5,allowance7/factor1/multiplier3; current entry command-2,
counter4; explicit context modelindex5,previous_integer_request-4,driver1.5,angle85.
One synthetic next state is `(6,8,2,5)`. Declared saved(2,5) MATCH; saved(4,5)
DIFFERENT with only saved_limited_state(declared4,computed2); saved(4,6) gives both
differences in fixed order. Inactive current gives post-gate0 and counter0 even
if internal limiter result is nonzero. Angle85 threshold,89/90 fault wrap, sign
change, driver clip, zero explicit deltas, rounding ties and resumed state get
hand-checked expectations. None is an r/vehicle parameter policy.

Tests first for real calculation/classification/role preservation, preflight
failure/no model call, exact-one-step accounting/direct constructors/replace,
fixed flags/no extra constructor arguments, model failure and malformed consumed
result boundary, existing CORE5 rejections, deterministic frozen values and import
isolation. Model-step fault injection is allowed only to test external boundary
failures, not as expected arithmetic or a replacement for real-model cases.

Independent literal/rational acceptance uses no model quantizer/limiter/oracle
for its expected values; run twice with exact deterministic outputs. One fresh
whole-branch reviewer; final full dev.py verify, actual cloud gate consumer,
source custody/Manifest/wheel/ref checks. Baseline1015tests/244own compiles; final
1015+actual new tests/246own compiles. Existing frozen wheel SHA
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c unchanged.

## Preservation and authority

Python3.12.13 existing environment, no installs/network work. Existing linked
worktree, local stacked branch on118ac73b1ba12d1ef8415d031137417de4fc9224; preserve
old runtime/CORE1~5/public source/lock/workflow/imported files/source profiles.
Only new module/test/guide/spec/plan and component README/backlog are changed.
No push/merge/PR/HF/CI dispatch or cleanup. Preserve external evidence and refs.

Actual inputs/F61/Controller/Runtime/CAN/actual r calculations0. Synthetic work
is nonzero. Actual r/T2/vehicle_scale=null; R_BUDGET=UNRESOLVED;
STATIC_EVIDENCE_GATE=FAIL; SOURCE_SCHEMA_UNQUALIFIED=6000;
Candidate/Runtime=NO_GO; D2=PERFORMANCE_NOT_EVALUATED;
F19=LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY=NOT_PROVEN;
F70UH/F70V/F71 and actual activation=NOT_ALLOWED.
