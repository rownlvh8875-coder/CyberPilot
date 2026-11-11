# CORE52 — explicit diagnostics from canonical synthetic recording bytes

## Intent and choice

CORE49 diagnoses owned finished recordings; CORE41 already defines exact bounded
canonical bytes. Connect those two existing boundaries so a developer can diagnose
an explicitly supplied saved synthetic recording without manually decoding it.
The user delegated next-step choices and opted out of repeated questions. This is
the author's development choice, not a new vehicle or rate-policy approval.

## Approaches

1. A bytes-to-existing-diagnostics function: chosen; no filesystem or new schema.
2. A file CLI with serialized contexts and result persistence: would require new
   context/output contracts and file publication rules, deferred.
3. Changing CORE49 to accept both objects and bytes: obscures its exact object
   boundary, rejected. Keep the existing function unchanged.

## Contract

Add `check_serialized_synthetic_recording(raw: object, contexts: object) ->
SyntheticSequenceCheckV1` to `integration_tools/offline_recording_diagnostics.py`.
Decode with existing `decode_recording`, then call existing
`check_recorded_synthetic_sequence`. No alternative JSON reader or coercion.

Only exact bytes, 1..262144 bytes, canonical CORE41 encoding and 2..128 frames are
eligible. All existing codec metadata/type/shape/link checks apply first, before
contexts are inspected. Then CORE46 validates the full recording and all explicit
contexts/model indices before any CORE7 model step. No cached validation or receipt
capability; every invocation revalidates. Contexts remain a separate exact tuple of
CORE5 objects and are neither serialized here nor inferred from the recording.

Successful N-frame calls perform exactly N-1 existing synthetic model steps, zero
simulate/reference steps. Return the unchanged CORE7 result, all differences and
declared-state feed; do not repair, truncate or use computed-state rollout.
Raw binary32 words and int64 ns remain exact, clock labels remain declarations;
no dt, time conversion, model-index inference, r, T2 or scale policy is added.

Malformed bytes raise unchanged `RecorderError('RECORDER_SERIALIZATION')` before
any model work. Valid bytes with invalid contexts raise existing CORE46 errors.
Existing CORE7/model exceptions propagate unchanged; later model failure can
follow prior nonzero work and returns no successful prefix. No catch-all wrapper.

## Non-goals and authority

No file/path/log/vehicle reader, CLI, new codec, schema, receipt, arithmetic,
package export, wheel change, or dependency change. No source authenticity,
prehistory/first-anchor/full-output/native replay qualification. Cooperative
single-thread Python, not hostile-process or atomic-capture security.
No actual Controller/Runtime/CAN/F61/input/capture/dt/r/install/deploy execution.
Actual r/T2/vehicle scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
actual activation/F70UH/F70V/F71 NOT_ALLOWED remain unchanged.

## Delivery

Small, single native implementation task with focused RED/GREEN, fresh full DEV
gate, one independent final review and deterministic evidence archive. Preserve
the primary checkout, unrelated refs/source bytes and all prior evidence. Local
feature commits only in this task; push/PR/main integration/CI NOT_RUN.
