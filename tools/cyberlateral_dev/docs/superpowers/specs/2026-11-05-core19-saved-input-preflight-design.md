# CORE19 saved synthetic input semantic preflight

Builder-selected next offline increment under the user's delegated execution:
revalidate saved CORE8 input semantics without replay. CORE9 checks bounded bytes,
closed schema and stored relations but intentionally does not decode float text or
check CORE5 dyadic/quantization compatibility. A consistent saved MATCH can contain
incompatible input; conversely a recorded REJECTED label is not a current verdict.

## Approaches

Changing CORE9 would break its numeric-free/import-light contract. Adding replay
would introduce model work and conflate input compatibility with arithmetic truth.
A separate pure DEV API reusing CORE9 capture and CORE3~5 validation is the chosen
small increment. No CLI, arbitrary JSON reader, V4 bridge or F61 invocation.

## Interface and flow

`integration_tools.core_sequence_input_preflight.preflight_saved_sequence(input_path: Path) -> dict`
raises `InputPreflightError.code` only for saved-package capture/schema failures,
prefixed `INPUT_PREFLIGHT_SAVED:` plus the unchanged CORE9 code. Unexpected internal
exceptions propagate, never become compatible/rejected input verdicts.

1. Call unchanged `read_saved_sequence_records` once (exact3 regular captures,
   existing65536/524288/512byte caps, no symlinks/nonregular files).
2. Rebuild owned CORE3 request/context and CORE4 settings/frame dataclasses from
   closed captured records; binary32 hex becomes bytes, never an inferred signal.
3. Decode each CORE5 auxiliary hex float with exact `float.fromhex`, require
   `value.hex() == text`. Overflow/underflow/noncanonical aliases produce
   `INPUT_PREFLIGHT_FLOAT_ENCODING:i` with0 validated transitions. Preserve -0.0.
4. CORE5 `prepare_model_input` validates all adjacent pairs in order. First failure
   yields `SEQUENCE_INPUT:i:<original MODEL code>` and successful-prefix count.
   Explicit model-index adjacency is already enforced by CORE9's saved-schema
   validation; preserve that earlier saved-record rejection rather than bypass it.
   No model step, reference, elapsed-time calculation or silent fallback.
5. Return a JSON-compatible owned summary, never prepared model inputs/constructor
   args: schema_version1, contract_id `CORE19_SAVED_SYNTHETIC_INPUT_PREFLIGHT_V1`,
   case_id, preflight_status `INPUTS_COMPATIBLE` or `INPUTS_REJECTED`, rejection_code
   (null when compatible), validated_transition_count, declared_transition_count3,
   saved_status/rejection/model steps separately, captured_sha256, unchanged gates.
   New model/reference counts0; numeric_validation_work `NONZERO_NOT_AGGREGATED`.
   source_identity_reauthenticated/arithmetic_recomputed/prehistory_checked,
   v4_payload_allowed/f61_input_allowed/actual_activation_allowed all false.

Input bytes/layout/modes unchanged; no new writes or cache/temp operations by the
function. Cooperative ordinary Python API; import infrastructure, hostile races,
atime, provenance, recorded arithmetic and later mutation are not authenticated.
Compatible input does not validate saved outputs, authorize replay or approve any
vehicle/policy. Even the original declared-difference input can be compatible.
Existing saved-only APIs/algorithms/wheel and CPython3.12.13 Linux setup unchanged.
Actual r/T2/vehicle_scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
Candidate/Runtime=NO_GO; F70UH/F70V/F71/vehicle activation=NOT_ALLOWED.

## Verification

TDD covers real saved packages and coherent semantic counterexamples; independent
acceptance uses preserved CORE17 three-case files without fixture generation,
producer/reference execution, actual r/dt/F61/Controller/Runtime/CAN work. Numeric
decoding/quantization is nonzero; whole unit/gate fixture work is separately
NONZERO_NOT_AGGREGATED. Fresh full DEV gate,286 own compiles, unchanged frozen wheel,
two independent acceptance rounds, source/ref custody and one final fresh review.
