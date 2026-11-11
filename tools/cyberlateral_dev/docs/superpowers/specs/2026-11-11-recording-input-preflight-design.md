# CORE46 — synthetic recording input preflight

## Intent and delegated choice

Make a completed CORE41 synthetic recording useful for explicit input-compatibility
inspection before any model execution. Existing CORE41 preserves frames but does
not contain CORE5 driver/angle/previous-integer-request/model-index contexts.
The user delegated sequential offline development and opted out of repeated
approval questions. This small API and native execution are the author's choices,
not newly user-specified requirements or an individually approved design document.

## Approaches

1. Another saved-result comparator: duplicates the existing CORE10/14 family and
   does not resolve missing input contexts; not selected.
2. Send recordings directly to CORE7/model execution: conflates preservation with
   input readiness and changes execution permissions; not selected.
3. Typed recording + explicitly supplied CORE5 contexts, validation only: selected.
   Reuses existing CORE41/CORE5 checks without promoting any authorization flag.

## Exact interface

New `integration_tools/offline_recording_preflight.py` provides:

- `RecordingPreflightError(ValueError)` with fixed `.code` and identical message.
- `SyntheticRecordingInputPreflightV1(recording, contexts)`: frozen/slotted result.
- `preflight_recording_input(recording: object, contexts: object)` returns that exact type.

`recording` is the exact `FinishedSyntheticRecordingV1`; no bytes/dict/foreign
object intake or implicit decoding. Reuse CORE41 `_validate_finished`, including
metadata, 2..128 records, request/state/settings/time-order links.
`contexts` is an exact tuple of `SyntheticModelContextV1`, with records-1 members.
No contexts or fields are inferred. Model indices remain separate from capture
sequence/time and must be consecutive after all CORE5 inputs are validated.

## Validation and errors

Order: exact result type → CORE41 recording → exact context tuple/count → every
adjacent CORE5 `prepare_model_input` → consecutive model indices.

- `RECORDING_PREFLIGHT_TYPE`: result subclass, before field access.
- `RECORDING_PREFLIGHT_RECORDING:<RecorderError.code>`: any CORE41 rejection.
- `RECORDING_PREFLIGHT_CONTEXT_CONTAINER`: not exact tuple, before iteration.
- `RECORDING_PREFLIGHT_CONTEXT_COUNT`: count differs from records-1.
- `RECORDING_PREFLIGHT_INPUT:i:<ModelInputError.code>`: zero-based transition i.
- `RECORDING_PREFLIGHT_MODEL_ORDER:i`: context i not previous model_index+1.

Expected domain errors are wrapped without raw input/foreign exception messages.
Unexpected exceptions propagate, never produce success. No partial successful
result on a later failure. Direct construction and dataclasses.replace revalidate.

## Result and non-goals

Preserve original recording/contexts; derive `record_count` and
`validated_transition_count`. Fixed status `INPUTS_COMPATIBLE`, contract
`CORE46_COUNTERFACTUAL_RECORDING_INPUT_PREFLIGHT_V1`, validation_claim
`DECLARED_INPUT_COMPATIBILITY_NOT_OUTPUT_PARITY_OR_SOURCE_PROOF`.
`numeric_validation_work=NONZERO_NOT_AGGREGATED`; CORE5 decodes binary32 and
checks previous-request quantization. `new_synthetic_model_steps=0`,
`new_reference_steps=0`. Do not return prepared model inputs/states.

Fixed false: `first_frame_transition_checked`, `prehistory_checked`,
`source_identity_reauthenticated`, `model_input_allowed`, `v4_payload_allowed`,
`f61_input_allowed`, `actual_activation_allowed`. No flag is constructor-settable.
Retain `time_semantics=ORDER_ONLY_NO_DELTA_OR_PERIOD`.

No output/saved-state arithmetic parity, repair, rollout, source identity proof,
actual collector, external reader/CLI, serialization format, I/O, concurrency or
security sandbox. Accepted synthetic declarations can be arithmetically different.
Do not change CORE3~7/CORE41, model/public API/wheel/fixtures, CI or dependencies.
No dt/seconds/r/T2/vehicle-scale inference. Actual r/T2/scale remain null;
R_BUDGET UNRESOLVED, Static Gate FAIL, actual activation/F70UH/V/F71 prohibited.

## Verification

Test first: missing module fails by assertion, then real fixtures exercise exact
types, roles, full validation including the last context, order precedence,
metadata tampering, constructor/replace, original bytes and signed zero/subnormal,
record limits and exception propagation. Profile real model entry points to prove
no new steps in success/rejection paths. Whole DEV gate and independent review
remain required; sum neither test counts nor synthetic work as vehicle evidence.
