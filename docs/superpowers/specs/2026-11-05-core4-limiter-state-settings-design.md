# CORE4 — Explicit counterfactual limiter state and settings links

Base `5b33af5bb85d3eb08c43d7016d580e9833a4fb4d`. Owner delegated native execution
and ordinary offline decisions, opting out of repeated approval. Extend the small
typed counterfactual boundary, not actual source instrumentation or V4/F61 input.

## Intent and author choices

CORE3 stores same-stage requests/flags/time/context but no previous limited state
or settings. Inferring limited state from the previous request conflates units;
repurposing the old UGY JSON checker changes a different profile. Choose a new
stdlib `integration_tools/limiter_snapshot.py` composing CORE3's public pair API
with immutable declared state/settings. Preserve all old runtime code and APIs.

This validates declarations and continuity, NOT original limiter arithmetic,
capture/consumption authenticity, applied hardware response or model-input readiness.
No model/controller/helper invocation, request quantization/native conversion,
dt/r computation, JSON reader/CLI or V4/F61 bridge.

## Carriers and bounded synthetic domain

`SyntheticConsumedSettingsV1` frozen slots, all seven fields REQUIRED:
request_scale:int, limiter_scale:int, delta_up:int, delta_down:int,
driver_allowance:int, driver_factor:int, driver_multiplier:int.
Scales1..2048; delta_up/down/allowance0..64; factor/multiplier0..8, exact built-in
ints only. request_scale==limiter_scale is this conservative stable-settings
subset, but keep the two declared occurrences separately. No defaults/coercion.
These bounds align with R31 `scenario_input.validate_spec`, not the entire helper
domain (whose Limits STEER_MAX can reach4096), OEM limits or a rate-policy authority.
The seven values are aggregate caller declarations, NOT all original repeated
read occurrences or proof they were actually consumed. No source getter is read.

`SyntheticLimiterSnapshotV1` frozen slots, all nine fields REQUIRED:
request:SyntheticRequestSnapshotV1, settings:SyntheticConsumedSettingsV1,
state_stage:str, settings_origin:str,
limited_state_at_entry:int, saved_limited_state:int,
angle_counter_at_entry:int, saved_angle_counter:int, inactive_gate_active:bool.
Exact state_stage=`DECLARED_LIMITED_STATE_POST_INACTIVE_GATE`,
settings_origin=`DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS`.
State fields use software integer command units [-2048,2048]; counters0..90, from
the existing bounded synthetic state contract. Do NOT clamp state to current scale
or require canonical state0 merely because capture sequence0: resumed seeds remain
explicit unproven prehistory. State roles differ from normalized request bytes.

inactive_gate_active is a REQUIRED separate later occurrence, not inferred from
CORE3 request_active. Require exact bool; when false, saved_limited_state must be0.
When true, arbitrary in-domain declared saved values are not rechecked by limiter
arithmetic. Request-active/gate-active disagreement may be preserved as distinct
declarations; it is not whole-model compatibility or source execution proof.

## Validated pair API

`LimiterSnapshotError(ValueError)` has fixed `.code`, no input forwarding.
`prepare_limiter_pair(previous:object,current:object)->PreparedSyntheticLimiterPairV1`.
Output frozen slots, previous/current required; derived request_pair init=False
is a freshly validated CORE3 pair. Direct result construction and dataclasses.replace
must run the same guards in __post_init__. Only set derived request_pair after all
own guards pass; no partial returned result or mutable cache.

Fixed init=False output fields:
contract_id=`CORE4_COUNTERFACTUAL_LIMITER_PAIR_V1`,
validation_claim=`DECLARED_STATE_LINKS_NOT_LIMITER_ARITHMETIC_OR_SOURCE_PROOF`,
state_link_scope=`PREVIOUS_SAVED_TO_CURRENT_ENTRY_ONLY_NOT_PREHISTORY`,
source_identity_reauthenticated=false, model_input_allowed=false,
v4_payload_allowed=false, f61_input_allowed=false, actual_activation_allowed=false.

Validation order: exact result/frame types (LIMITER_SNAPSHOT_TYPE); compose public
CORE3 prepare_request_pair, wrapping RequestSnapshotError as `LIMITER_REQUEST:` plus
its fixed code; then previous/current frame each: exact declaration strings
(LIMITER_DECLARATION), settings exact type (LIMITER_SETTINGS_TYPE), all setting
domains (LIMITER_SETTINGS_DOMAIN), equal within-frame scales (LIMITER_SCALE_MISMATCH),
both state domains (LIMITER_STATE_DOMAIN), both counters (LIMITER_COUNTER_DOMAIN),
gate exact bool (LIMITER_GATE_FLAG), false gate=>saved0 (LIMITER_INACTIVE_STATE).
Then same seven settings across pair (LIMITER_PAIR_SETTINGS), previous saved state
==current entry state (LIMITER_PAIR_STATE_LINK), previous saved counter==current
entry counter (LIMITER_PAIR_COUNTER_LINK). Do not reconstruct any missing value.

## Verification, preservation and limits

One module/test/Korean guide/spec/plan; component README/backlog updates only.
CORE3, V4/constants/oracle, CORE2 matrix, public src/imported77, locks/workflows and
cloud profiles unchanged. Existing wheel0.3.0 bytes fixed. Test-first missing-feature
RED then focused GREEN, full956+new methods/242compiles/static/frozen wheel gate.
Baseline956/240 from immutable Git export, separate from edits. Independent literal
state/settings/gate tests twice; check raw/request/state distinction and no imports.
One fresh whole-branch review may overlap the final gate on unchanged committed
bytes; completion waits for both. Any fix requires new full gate, no repeat review
after the one Critical/Important TDD fix pass. Retain all evidence/local branch.

Cooperative immutable Python only, not hostile/persistence/atomicity/stream-registry
security. Actual source consumption, complete repeated reads, dynamic settings,
integer previous_requested/model index/state conversion and model invocation are
not solved. All numeric settings are explicit synthetic fixtures, not actual scale/r.

Maintain R_BUDGET UNRESOLVED, Static Gate FAIL, actualr/T2/scale null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/F70V/F71 NOT_ALLOWED.
No actual inputs, F61/Controller/Runtime/CAN, push/PR/main merge/HF writes/CI dispatch.
