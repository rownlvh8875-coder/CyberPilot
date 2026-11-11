# CORE55 — canonical synthetic recording and context input codec

## Intent and author choice

CORE52 accepts saved recording bytes but still needs explicit Python contexts.
Bundle the exact CORE41 recording encoding and explicit CORE5 contexts so a caller
can preserve a complete synthetic diagnostic input without reconstructing context
objects manually. The user delegated sensible next-step choices and opted out of
repeated questions; this wire-format choice is the author's,not new vehicle approval.

Approaches: a context-only codec still leaves two inputs to pair; a file CLI also
requires I/O/output publication policy. Choose one small in-memory input codec.
Existing CORE8 saved inputs are closed four-frame fixtures,not a general2..128
recording interface. Reuse CORE41/46 rather than generalizing that older contract.

## API and representation

New module:`integration_tools/offline_recording_input_codec.py`.

- `encode_recording_input(recording: object, contexts: object) -> bytes`:
  full existing CORE46 preflight,then canonical serialization;no model/reference step.
- `decode_recording_input(raw: object) -> SyntheticRecordingInputPreflightV1`:
  strict wire decoding,then existing full CORE46 preflight;return its unchanged
  false-authority receipt,not a new execution capability or a new F61 API.
- `RecordingInputCodecError(ValueError)` has fixed code/string
  `RECORDING_INPUT_SERIALIZATION` for structural wire failures.

Only exact bytes,1..1048576bytes. JSON UTF8 is sorted keys,ensure_ascii=False,
compact separators,allow_nan=False,and exactly one final newline. Duplicate keys,
nonfinite JSON tokens,pretty/alternate spellings or extra/missing fields reject.
Top-level exact fields:

schema_version=1 (built-in int,not bool)
contract_id=CORE55_COUNTERFACTUAL_RECORDING_INPUT_V1
scope=COUNTERFACTUAL_RECORDING_INPUT_ONLY
recording_json=(exact canonical CORE41 UTF8 text,including its final newline)
contexts=(list of1..127 explicit context records)
source_identity_reauthenticated=false
model_input_allowed=false
v4_payload_allowed=false
f61_input_allowed=false
actual_activation_allowed=false

Every context has exactly scope,model_index,previous_integer_request,
current_driver_hex,current_angle_deg_hex. The two hex strings must be canonical
finite built-in float.hex representations of at most32characters;negative zero
is preserved. Integer and float field semantics/ranges,context scope,pair
compatibility,context count and model-index order remain CORE46/5 authority.
No context,index,time,state,scale,r or missing value is inferred.
Inner recording_json must decode under the unchanged CORE41 codec;its binary32
words,int64 ns,clock labels,metadata and false gates remain exact.

## Validation and errors

Encoder propagates CORE46 errors unchanged for invalid declarations. Decoder
first checks exact bytes/bound/canonical outer JSON/header/shape,then inner
recording and context wire records;structural failures become the fixed codec
error without raw input text. It then invokes CORE46 outside structural exception
translation,so semantic compatibility errors retain exact existing codes/order.
Canonical malformed encoding therefore rejects before semantic checks. No broad
catch-all or partial success. No step/simulate/reference work on either API;
numeric validation is nonzero and not aggregated. No cached acceptance.

## Boundaries and delivery

The restored receipt must be explicitly unpacked into existing CORE49 if the
caller separately requests synthetic diagnostics;that performs N-1 model steps.
Codec creation/decoding/import never does so automatically. It does not establish
source authenticity,anchor/prehistory/full output or actual/native replay.
Cooperative single-thread Python,not hostile-process or atomic-capture security.
No filesystem/log/vehicle reader,CLI,result persistence,wheel export,new math,
CORE41/46/49/52 behavior change,dependency or workflow change.
Actual Controller/Runtime/CAN/F61/input/capture/dt/r/install/deploy0;
actual r/T2/scale=null,R_BUDGET UNRESOLVED,Static Gate FAIL,
actual activation/F70UH/F70V/F71 NOT_ALLOWED unchanged.
Local feature implementation/tests/review/evidence only;push/PR/main/CI NOT_RUN.
