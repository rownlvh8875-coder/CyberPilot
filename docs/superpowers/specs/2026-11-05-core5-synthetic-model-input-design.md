# CORE5 — Explicit Synthetic Model Input

## Intent and scope

Connect the CORE4 counterfactual pair to the existing public synthetic0.3.0
model's **one current invocation input**, without inferring missing state or
claiming the declared saved outputs are model results. Owner delegated ordinary
offline implementation decisions and opted out of repeated approval questions.
This design is the author's narrow continuation, not new vehicle authority.

Use existing Python3.12.13/stdlb and the frozen model. No installs. Work in the
already host-owned linked worktree; preserve all previous refs/evidence. Local
stacked branch only, no push/merge/PR/HF writes/CI dispatch or cleanup.

## Approaches

Chosen by author under the delegated workflow: a typed current-input preparer
composing unchanged CORE4 and the existing synthetic request quantizer. This
adds a usable input seam while preserving distinct declarations. A whole pair
simulation/declared-output parity checker would add transition claims and is
deferred. Silent defaults or merging disagreeing active reads would hide missing
semantics and are rejected. No CLI, JSON reader, wheel change or actual-source bridge.

## Inputs and outputs

New `integration_tools/synthetic_model_input.py` uses the public model
`Limits`, `LateralState`, `LateralInput` types, and unchanged
`_r4.request_quantizer.quantize` solely for previous-request consistency. It
does not call model step/simulate, limiter/oracle or original source helpers.

Required frozen/slotted input `SyntheticModelContextV1` fields:
`scope:str`, `model_index:int`, `previous_integer_request:int`,
`current_driver:float`, `current_angle_deg:float`. Input construction itself
makes no validation claim. Scope is `COUNTERFACTUAL_MODEL_INPUT_ONLY`.

Required result inputs `previous`, `current`: CORE4 `SyntheticLimiterSnapshotV1`,
and `context`: the exact context type. `PreparedSyntheticModelInputV1` validates
in `__post_init__` and exposes derived `limiter_pair`, `model_state`,
`model_input`. `prepare_model_input(previous:object,current:object,context:object)`
constructs that result. Direct construction/replace must revalidate; derived
fields and fixed claims cannot be supplied by callers. Fixed fields:

- contract_id=`CORE5_COUNTERFACTUAL_CURRENT_MODEL_INPUT_V1`
- validation_claim=`CURRENT_INPUT_COMPATIBILITY_NOT_DECLARED_OUTPUT_PARITY`
- synthetic_model_input_allowed=true; source_identity_reauthenticated=false;
  v4_payload_allowed/f61_input_allowed/actual_activation_allowed=false.

## Validation order and exact errors

1. Exact result type: `MODEL_INPUT_TYPE`; unchanged CORE4 pair validation next,
   wrapping only `LimiterSnapshotError.code` as `MODEL_LIMITER:<code>`.
2. Exact context class: `MODEL_CONTEXT_TYPE`; exact scope string: `MODEL_SCOPE`.
3. Exact built-in model_index1..4095: `MODEL_INDEX`. It is explicitly supplied,
   not capture sequence or a timestamp. Index0 is excluded because this API
   represents a current invocation with an immediate previous request; the
   canonical initial state is a different API.
4. Exact int previous_integer_request in[-2048,2048]: `MODEL_PREVIOUS_REQUEST`.
5. Exact finite built-in float driver abs<=1024 and angle abs<=180, each with
   `as_integer_ratio()[1]<=256`: `MODEL_DRIVER`, then `MODEL_ANGLE`.
6. Neither frame's request_override may be true: `MODEL_OVERRIDE`; the target
   model has no corresponding override input. For each frame its request_active
   must equal its separate inactive_gate_active: `MODEL_ACTIVE_READS`. Different
   activity between previous/current is allowed. Current model uses the current
   common value. Do not relax CORE4, which continues to preserve disagreements.
7. Exact model version string0.3.0: `MODEL_VERSION`. This is an API compatibility
   check, not authentication of arbitrary same-version Python packages.
8. Decode each validated big-endian IEEE binary32 raw request using
   `struct.unpack('>f', raw)[0]`: exact embedding in built-in binary64, preserves
   signed zero and subnormals, no scaling/clamping. Validate the supplied
   previous_integer_request equals existing synthetic `quantize(previous_float,
   previous.settings.request_scale).integer_command`:
   `MODEL_PREVIOUS_REQUEST_MISMATCH`. This checks consistency, never fills a
   missing field or reuses a limited output. Quantizer uses binary64 multiply,
   round-to-even and int, not a vehicle normalization/r policy.
9. Map current settings' limiter_scale/deltas/driver parameters directly to
   public `Limits`. Equal request/limiter scales and stable settings were
   already required by CORE4. Map current entry limited state/counter to
   LateralState.previous_applied/angle_counter; use the explicitly supplied
   model_index and previous_integer_request. Map decoded current request,
   explicit current driver/angle, current gate active, limits and
   provenance=`SYNTHETIC_ONLY` to LateralInput of the same index.

Fixed `ModelInputError(ValueError).code` has no raw values or partial result.
All derived fields are installed only after every guard succeeds. Exact class
and primitive checks precede accesses/comparisons that could invoke foreign
methods. Frozen values are a cooperative boundary, not hostile-mutation security.

## Success, non-goals and tests

Success is input compatibility, not prehistory or declared-output arithmetic
parity. Current saved state/counter is retained only in the original pair and
must not become the current entry state or an approved next state. No rolling
simulation or model execution occurs in the new API. A focused test may pass a
prepared input to the existing **synthetic** public step to demonstrate usability;
it must neither compare to unproved saved output as authority nor call F61.

Tests first: literal pair request-0.25/+0.5, scales16, previous quantized-4,
current entry-2/counter4, modelindex5, driver1.5, angle85.0; exact mapped fields.
Cover required fields/types/domains/dyadic restriction, request quantization
ties and sign/subnormal preservation, different capture sequence/modelindex,
resumed unclamped state, active/override rejection, CORE4 error inheritance,
constructor/replace guards, fixed permissions, deterministic frozen output,
no calls to step/simulate and import isolation. Existing package/wheel/API,
source profiles and CORE1~4 are unchanged. Keep synthetic bounds distinct from
actual helper/OEM authority.

Final gate: baseline985tests/242own compiles, then985+actual new tests/244own
compiles, Ruff/Ty/Codespell, frozen wheel
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Independent literal acceptance twice, one fresh whole-branch review, source
custody/Manifest/Git checks and actual existing cloud gate consumer.

All actual r/T2/vehicle_scale remain null; R_BUDGET=UNRESOLVED;
STATIC_EVIDENCE_GATE=FAIL; SOURCE_SCHEMA_UNQUALIFIED=6000;
Candidate/Runtime=NO_GO; D2=PERFORMANCE_NOT_EVALUATED;
F19=LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY=NOT_PROVEN;
F70UH/F70V/F71 and actual activation=NOT_ALLOWED. No actual input, Controller,
Runtime, CAN, F61 import/compile/execution, actual dt/r or policy value generation.
