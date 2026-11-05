# CORE3 — Explicit counterfactual request snapshots

Base `e0d5225bee52e198afe4aab6c81ffcb244ecbff8`. Owner delegated ordinary offline
choices/native execution and opted out of repeated design questions. This small
boundary builds on CORE2, not on an invented production profile or broadened V4.

## Intent, approaches and author decisions

CORE2 found missing request-stage flags/reset/context. Retrofitting those into
existing UGY observations invents evidence; widening V4's source pins changes a
different contract. Choose one new stdlib DEV module for explicitly authored
counterfactual snapshots and a validated adjacent pair. No reader, CLI, source
instrumentation, model/F61 execution, payload bridge or history registry.

The first unit handles requests only. Previous limited outputs, consumed settings,
arithmetic/limiter parity and actual source binding remain outside it; no field
defaults or aliases pretend these are resolved. "Snapshot" means immutable,
already materialized caller values, not atomic source capture or single-read proof.

## Module and carriers

Create `tools/cyberlateral_dev/integration_tools/request_snapshot.py` with:

`RequestSnapshotError(ValueError)` exposing a fixed `.code`, no raw input output.

`SyntheticRequestContextV1`, frozen slots, all fields REQUIRED:
schema_version:int, scope:str, source_profile:str, capture_epoch_id:str,
controller_instance_id:str, configuration_epoch_id:str, clock_domain:str,
control_mode:str, request_stage:str, reset_generation:int, loss_generation:int.

Exact scope/profile/mode/stage:
`1`, `COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY`, `CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1`,
`DECLARED_TORQUE_CONTROL`, `REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER`.
clock_domain is `DECLARED_LIVE_MONOTONIC_NS` or `DECLARED_REPLAY_RECORDED_CAN_NS`.
Three ID strings use `[A-Za-z0-9_-]{1,64}`. Generations are built-in uint64 ints.
These are bounded synthetic grammar choices, not production identity authorities.

`SyntheticRequestSnapshotV1`, frozen slots, all fields REQUIRED:
context:SyntheticRequestContextV1, sequence:int, sample_time_ns:int,
requested_binary32:bytes, request_active:bool, request_override:bool,
reset_since_previous:bool.

sequence is uint64, sample_time_ns signed int64, all exact built-in types (no bool
as int, subclasses or coercion). requested_binary32 is exactly4 MSB-first bytes,
encoding a finite normalized request in [-1,1]. Validate bits without constructing
a numeric native float; preserve raw bytes, including signed zero/subnormals.
Input context/snapshot constructors are immutable carriers, not validation claims.

## Pair API and invariants

`prepare_request_pair(previous: object, current: object) -> PreparedSyntheticRequestPairV1`.
The result is frozen slots with required previous/current snapshots and init=False
fields: contract_id=`CORE3_COUNTERFACTUAL_REQUEST_PAIR_V1`,
validation_claim=`COOPERATIVE_SYNTHETIC_DECLARATION_ONLY`,
time_semantics=`ORDER_ONLY_NO_DELTA_OR_PERIOD`, source_identity_reauthenticated=false,
v4_payload_allowed=false, f61_input_allowed=false, actual_activation_allowed=false.
Direct construction of the result must validate the same invariants in __post_init__;
its fixed claim/permission fields cannot be supplied/replaced via constructor args.

Validation order: result/snapshot exact record types; each snapshot previous then
current: context type, schema/scope, source profile, mode/stage/clock, IDs,
generation types/ranges, sequence, time type/range, raw word, explicit bool flags.
Then pair context equality (all11 context fields), sequence adjacent/no wrap,
current_time>previous_time by comparison only, current.reset_since_previous=false.
Reject with respectively REQUEST_SNAPSHOT_TYPE, REQUEST_CONTEXT_TYPE,
REQUEST_SCOPE, REQUEST_SOURCE_PROFILE, REQUEST_CONTEXT_MODE, REQUEST_CONTEXT_ID,
REQUEST_GENERATION, REQUEST_SEQUENCE, REQUEST_TIME, REQUEST_WORD, REQUEST_FLAGS,
REQUEST_PAIR_CONTEXT, REQUEST_PAIR_SEQUENCE, REQUEST_PAIR_TIME, REQUEST_PAIR_RESET.

Previous reset_since_previous=true is allowed: it describes an interval BEFORE
the supplied pair, not the current interval. Current true always rejects even
when generations agree. Changed loss/reset generations or epochs also reject.
No default False and no inferred state reconstruction. Inactive/override flags
otherwise remain preserved metadata, never a feasibility or command decision.

Positive intervals including1ns/10ms/17ms are allowed as ordered raw times: this
does not compute dt, satisfy V4's exact-seconds subset or establish a real period.
The validated pair holds the same immutable snapshots, no mutable aliases/cache.
Cooperative Python only: object.__setattr__ bypass, hostile/concurrent mutation
and actual-origin authentication are not solved. No real source object is read.

## Preservation, evidence and completion

Only new module/test/Korean guide/spec/plan, component README and core backlog.
No old runtime code, V4/constants/oracle, CORE2 matrix, public src/imported77,
locks/workflows/cloud profiles edits. Keep wheel0.3.0 exact frozen bytes.
TDD against actual behavior, then full DEV gate and fixed independent literal
word/pair acceptance cases twice. One fresh whole-branch review; it may overlap
the final gate on identical committed bytes, with no completion before both finish.
Any source fix requires fresh full verification; no repeat reviewer after one
Critical/Important fix pass. Retain evidence/host worktree/local branch, no publish.

Baseline runs from a Git export so edits cannot contaminate its927tests/238compiles.
Final gate expects927+actual new methods and240 own compiles. Unit/gate preexisting
synthetic model/reference/time work is NONZERO_NOT_AGGREGATED; the new seam itself
does raw validation/order only, no native/dt/r/model/adapter/F61 computation.

Maintain R_BUDGET UNRESOLVED, Static Gate FAIL, actualr/T2/scale null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/F70V/F71 NOT_ALLOWED.
