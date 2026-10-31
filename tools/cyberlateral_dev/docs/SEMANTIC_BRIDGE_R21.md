# R21 — synthetic declared-readback semantic bridge and independent oracle

Baseline:451a8ff9f38057cc94a0f19e283ca366ebd9ca13.
User requested the proposed next stage; routine choices/inline execution/feature
publication are delegated. This is synthetic development, not vehicle activation.

## Selected approach

Add a new pure bridge from R20 envelopes + exact declared scalar readback to the
unchanged public0.3.0 LateralInput/LateralState dataclasses. No native parsing in
the bridge. Actual readback is supplied only by a closed opt-in native fixture
producer. A generic raw-byte reader would require new lifetime/custody authority;
silently calling R14 would mislabel Float32-origin values as its binary64 profile.
Neither is selected. Constructors are data-only: do NOT call step, simulate,
initial_state, quantization, limiter, Controller/Runtime/CAN/F61 or calculate r/dt.

The bridge checks declared metadata binding, NOT authenticity or correspondence
of values to arbitrary bytes. A consistent fabricated envelope/readback can pass;
no actual-native-input permission follows. Closed producer readback is separately
observed in live owned contexts. Prior state remains a synthetic declaration.

## Interfaces and validation

integration_tools/semantic_types.py defines required frozen/slots records:

- ScalarReadback(stamp:R20 Stamp, cc_sha256:str, cs_sha256:str,
  representation:str, request:float, driver:float, angle_deg:float, lat_active:bool).
- PreparedSemanticInput(contract_id:str, stamp:Stamp, sample:public LateralInput,
  state:public LateralState, custody_claim:str, precision_claim:str, time_semantics:str).

semantic_bridge.prepare_semantic_input(frame:OwnedFrame, readback:ScalarReadback)
->PreparedSemanticInput. SemanticBridgeError(ValueError) has stable .code.

Validation order:

1. R20 prepare_owned_frame validates envelope; wrap its code as
   SEMANTIC_ENVELOPE:<OWNED_CODE>, no native decode or old-profile fallback.
2. SEMANTIC_READBACK_TYPE: exact ScalarReadback and exact Stamp before accessing
   attributes, no subclasses/coercion/callbacks.
3. SEMANTIC_BINDING: stamp fields exact builtin ASCII[A-Za-z0-9_-]{1,64}, index
   builtin0..4095 and stamp matches envelope; exact builtin cc/cs digests equal
   validated respective payload digests; representation=NATIVE_FLOAT32_DECLARATION.
4. SEMANTIC_DOMAIN: exact builtin finite floats, request abs<=1, driver abs<=1024,
   angle abs<=180 and active exact bool. Driver/angle denominator<=256. This is
   the existing synthetic subset, not original native/OEM validation.
5. SEMANTIC_PRECISION: every supplied float must already be exactly binary32
   representable, including signed zero. Adapter uses struct binary32 roundtrip
   only as validation; it never substitutes that rounded value. Binary64 literal
   0.3 rejects; actual Float32-promoted0.30000001192092896 can pass as request.
   The latter still rejects as driver/angle under the unchanged dyadic subset.
6. SEMANTIC_TARGET_VERSION: installed/public package exact builtin version0.3.0.

Construct Limits from the six explicit SettingsSnapshot fields. Construct sample
index from stamp; copy request/driver/angle/active verbatim, provenance=SYNTHETIC_ONLY.
Construct state(index, previous_requested, previous_applied, angle_counter) from
the validated prior declaration. Do not derive prior candidate from current value,
apply inactive gate, normalize, clip, round, scale, sign-flip or initialize state.

contract_id=F70UGZ_R21_SYNTHETIC_SEMANTIC_BRIDGE_V1;
custody_claim=DECLARED_READBACK_BINDING_NOT_AUTHENTICATED_NATIVE_CUSTODY;
precision_claim=EXACT_SUPPLIED_FLOAT32_PROMOTED_TO_PYTHON_FLOAT;
time_semantics=INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME.
Request normalized command; driver native CAN units (not Nm); angle degrees.

## Independent oracle

integration_tools/semantic_oracle.py imports data types and public dataclasses,
NEVER semantic_bridge or its validation/mapping helpers. Its explicit precondition
is a structurally valid R20 envelope and exact ScalarReadback/Stamp. It independently
checks readback metadata/domain, then uses integer significand/exponent analysis
of as_integer_ratio (not struct roundtrip) for binary32 representability.
OracleRejection.code matches semantic-layer codes; envelope validation is not
part of this oracle and remains covered by R20 tests. Mapping is independently
written field-by-field. Compare exact fields and float.hex, no tolerance. Hand
literal tests pin both oracle and adapter so agreement alone is insufficient.

## Explicit native experiment

--semantic-bridge and --owned-boundary are mutually exclusive, both default False.
R21 additionally REQUIRES --package-wheel: the exact sealed0.3.0 wheel SHA256
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Wrong/missing/unexpected wheel/mode rejects before native import/spawn. Verify
installed public-wheel payload/RECORD/namespace/cache as for pycapnp before imports;
verify public import origin. Separate native env contains ONLY those two packages.
No installation happens inside the qualifier. Default lock/wheel/pure CI unchanged.

R19 controls run first. Private empty bytecode prefix covers repository imports.
Closed R21 producer extends R20's private factory with optional driver/angle
arguments; default R20 observation bytes must remain unchanged. Eight fixed cases:
zero,rounded_request,signed_zero,resumed,driver_precision_reject,
angle_precision_reject,request_range_reject,smallest_subnormal.
Read only just-produced owned bytes in context, construct ScalarReadback directly
from builtin getters, prepare dataclasses and compare independent oracle. No model
transition or F61 input is generated. Preserve exact supplied signed-zero bits.
Add pure binding/type/domain/precision/state/guard/mutation tests and literal
native-output assertions; two isolated processes and new-env relocation must match.

## Completion and boundaries

STATUS on verified success:F70UGZ_R21_SYNTHETIC_SEMANTIC_BRIDGE_ORACLE_PASS.
This is NOT feasibility/performance/safety, actual custody/history, general reader,
native exact replay or production activation. Output is MODEL INPUT STRUCTURE ONLY,
not model execution or F61 FeasibilityInput.
Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; actual activation/F70UH/F70V/F71=NOT_ALLOWED.
Public0.3.0 API/wheel, lock, references, original trees and pure workflow unchanged.
Only existing feature Draft publication allowed; no main merge/deployment.
