# R20 — synthetic owned-message envelope and explicit construction ledger

Baseline:e00af768c26b0c401bc6bf98680062ab3f869c57. User requested the next proposed
owned-message/explicit-field/prior-state boundary and delegated routine choices.

## Approach and scope

Choose an immutable opaque-byte envelope with a PURE structural validator, plus
an opt-in closed native demonstration producing the envelope from fixed synthetic
messages. A generic reader of caller-supplied native objects would require broader
lifetime/concurrency/custody qualification; it is not selected. A metadata-only
design would not exercise byte ownership/default ambiguity; it is not selected.
The chosen approach makes those properties testable without a model adapter.

The native demonstration extends the existing explicit R19 worker, reusing its
pre-import wheel/installed/source/cache guards and exact schema/include loading.
Default R19 observations remain byte-identical. No capnp dependency or native
execution enters default component verification, public wheel or CI.

The pure boundary does NOT parse Cap'n Proto, infer field presence, authenticate
bytes, prove source writes, read commands, generate F61 args or run the model.
Schema IDs/hashes and ledgers are caller declarations checked for consistency,
NOT cryptographic call custody. Arbitrary bytes with internally consistent labels
may pass structural checks; that is not native-message validity or activation.
Only the closed opt-in producer actually constructs/reads synthetic native messages.

## Exact pure interface

integration_tools/owned_message_boundary.py, stdlib only, excluded from wheel:

- Stamp(sequence_id:str, invocation_index:int, capture_id:str).
- OwnedPayload(stamp:Stamp, schema_id:int, payload:bytes, payload_sha256:str).
- FieldLedger(stamp:Stamp, cc_sha256:str, cs_sha256:str, written_fields:tuple[str,...]).
- SettingsSnapshot(stamp:Stamp, steer_max:int, delta_up:int, delta_down:int,
  driver_allowance:int, driver_factor:int, driver_multiplier:int).
- PreviousSnapshot(stamp:Stamp, previous_invocation_index:int|None,
  source_previous_applied:int, source_angle_counter:int, previous_applied:int,
  angle_counter:int, previous_requested:int|None, stage:str).
- OwnedFrame(scope:str, source_set_id:str, schema_sha256:str,
  static_context_reference:str, stamp:Stamp, cc:OwnedPayload, cs:OwnedPayload,
  ledger:FieldLedger, settings:SettingsSnapshot, previous:PreviousSnapshot).
- PreparedOwnedFrame(contract_id:str, frame:OwnedFrame, custody_claim:str,
  precision_claim:str, time_semantics:str).
- prepare_owned_frame(frame:OwnedFrame)->PreparedOwnedFrame.
- OwnedBoundaryError(ValueError), stable .code, no partial result.

All records frozen/slots, required fields, no defaults, no subclasses/coercion.
Output retains the entire same immutable envelope, with no decoded control values.

## Validation order

1. OWNED_RECORD_TYPE: exact root/nested classes, including every Stamp, before
   touching children/properties. No callbacks/duck typing/native objects.
2. OWNED_SCOPE: exact builtin strings: scope=SYNTHETIC_OWNED_MESSAGES_ONLY,
   source_set_id=R11_C8FB9068_4134C0D1_V1,
   schema_sha256=098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788,
   static_context_reference=SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY.
3. OWNED_STAMP: each sequence/capture exact ASCII[A-Za-z0-9_-]{1,64}, builtin
   invocation_index0..4095; all six payload/ledger/settings/prior/root stamps
   value-equal. Equal stamps are declarations, not atomicity/history proof.
4. OWNED_SCHEMA: exact builtin schema IDs, CC17836551423953212591 and
   CS11359479080460390460. Generic dynamic class is not schema identity.
5. OWNED_PAYLOAD: exact builtin bytes, size1..65536 each, lowercase SHA256 matches
   actual bytes. Reject bytearray/memoryview/subclasses, no bytes() fallback.
6. OWNED_FIELD_LEDGER: ledger digests match respective payloads and exact sorted
   tuple is CC.actuators.torque,CC.latActive,CS.out.steeringAngleDeg,
   CS.out.steeringTorque. No missing/duplicate/extra/type-coerced fields. Never use
   default zero/False, _has or matching bytes to fill a missing ledger.
7. OWNED_SETTINGS: builtin ints only, MAX1..2048; UP/DOWN/ALLOWANCE0..64;
   FACTOR/MULTIPLIER0..8. All are synthetic, not vehicle/static scale authority.
8. OWNED_PREVIOUS: exact stage=ENTRY_BEFORE_CURRENT_LIMITER. Builtin applied ints
   [-2048,2048], counters0..90; source and declared model-owned applied/counter
   equal. At index0: previous index/request=None and applied/counters0. Otherwise
   previous index=index-1, previous_requested builtin int[-2048,2048]. No missing
   state initialization, no deriving prior candidate from request/returned torque.

Prepared contract_id=F70UGZ_R20_OWNED_SYNTHETIC_ENVELOPE_V1;
custody_claim=STRUCTURAL_SYNTHETIC_DECLARATION_ONLY;
precision_claim=OPAQUE_OWNED_WIRE_BYTES_NO_DECODE;
time_semantics=INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME.

## Controlled native demonstration

--owned-boundary explicitly selects R20 in native_qualification/run.py. In the
same verified worker/schema context, native_qualification/owned_demo.py constructs
four fixed frames: explicit zero/False, rounded0.3, negative zero and a resumed
index1 synthetic declaration. CC/CS builders are local and never escape. Write
ledgers are recorded while assigning fields; to_bytes creates immutable ownership.
Readback occurs only inside from_bytes contexts. After copying, mutate both
original builders and show owned hashes/readback unchanged. No reader is accessed
after close. No capture hook, concurrency, external object or user message mode.

Exercise missing ledger despite identical default bytes, wrong schema, crossed
frame/settings/prior stamps, mutated bytes, mutable payload and incorrect previous
index/state. The native report has exact readback and payload/envelope hashes,
rejection codes, provenance claims and unchanged gates. Independent literal
expectations test the report; two workers and a relocated/new-env run must agree.

## Boundaries and completion

Status on verified success: F70UGZ_R20_OWNED_SYNTHETIC_BOUNDARY_REFERENCE_PASS.
This is NOT native-reader registration, Q05 actual custody PASS, general lifetime
qualification, trusted retrospective history or native exact replay.
Public0.3.0 wheel/lock/goldens/default CI unchanged. Controller/Runtime/CAN/F61/
actual input/model execution/r/dt calculation by the new boundary/demo=0.
Actual r/T2/vehicle scale=null, R_BUDGET=UNRESOLVED, Static Gate=FAIL,
SOURCE_SCHEMA_UNQUALIFIED=6000, Candidate/Runtime=NO_GO,
D2=PERFORMANCE_NOT_EVALUATED, F19=LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY=NOT_PROVEN, actual activation/F70UH/F70V/F71=NOT_ALLOWED.
Original trees remain read-only; only existing feature Draft PR publication allowed.
