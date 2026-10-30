# R13 — offline openpilot message-boundary design

Status: DESIGN_ONLY_NOT_IMPLEMENTED. Contract F70UGZ_R13_MESSAGE_BOUNDARY_V1.
R13 writes design/test specifications only; no new reader, extraction code or
schema/native execution. R12 remains the unchanged seven-fixture bridge.
User delegated routine choices; the alternatives and interface choices here are
the author's, not new vehicle/rate-policy approvals.

## Intent and alternatives

Move beyond field-name resemblance by defining what a future input boundary must
preserve, and what source text cannot prove. Do not call synthetic records native
messages or silently route arbitrary data through the R12 fixture whitelist.

- A direct Controller hook would execute/import prohibited native/runtime paths,
  require actual state/setting custody and CAN isolation: not selected.
- An unrestricted duck-typed CC/CS reader would execute arbitrary properties and
  conflate defaults with supplied values: not selected.
- Selected: two distinct layers. A future pure synthetic extraction contract can
  be implemented/tested without native imports. Actual message readers remain
  blocked behind a separately scoped ABI/schema qualification procedure. This
  advances the boundary specification but does NOT resolve actual reader behavior.

No actual/raw inputs, object observer/capture, runtime install, Controller/Runtime/
CAN/F61/schema execution, r/dt calculation, policy selection or main merge occurs.
Static Gate FAIL does not block synthetic development; it still blocks actual use.

## Exact authority and new source findings

Use the R11 source map's six pins: CyberPilot c8fb906815530460ed156f14e09e1f312bb0f851
and opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. R12 integration baseline is
a69025dad11c99877bf875bd188a6f6cb8f1753f. Recheck bytes/Git blobs before publishing.
The companion contract records four additional static source pins. None identifies
a deployed vehicle or rebinds the older ajouatom branches.

New facts, inspected as text/AST only:

- opendbc/car/structs.py:2,5-6 imports capnp, removes its hook and loads car.capnp
  at module import. Therefore importing it is NOT a passive metadata inspection.
- car.capnp:1 imports /include/c++.capnp. Its installed resolution/hash and native
  dependency closure have not been qualified by this work.
- openpilot/cereal/__init__.py:2,5,7-11 loads log/custom schemas at import, so it is
  not a permitted shortcut to obtaining a supposedly harmless message class.
- Root pyproject.toml:25 declares pycapnp==2.1.0; uv.lock:749-765 records version/
  candidate distributions. These are declaration/artifact candidates, not evidence
  of installed binary identity, reader class, ABI or vehicle deployment.
- interfaces.py:258 saves ret to self.CS.out;:267 initializes self.out from
  structs.CarState(). CS in Controller.update is a wrapper, NOT a bare CarState.

## Selected read boundary and fields

The conceptual boundary is entry to the selected steering slice, before line70
quantization and before any line74/81 state update. This is a DESIGN location,
not an installed observation hook or atomic-snapshot proof.

| Value to preserve | Exact source | Future extraction target / exclusion |
| --- | --- | --- |
| Requested normalized value | CC.actuators.torque, controller:66/70; schema:367 | LateralInput.request, NOT torqueOutputCan or returned torque |
| Driver value | CS.out.steeringTorque, controller:71; schema:188 | driver, native CAN units, NOT physical Nm |
| Angle value | CS.out.steeringAngleDeg, controller:74; schema:185 | angle_deg, no radians conversion |
| Lateral active | CC.latActive, controller:74/78; schema:346 | lat_active, NOT enabled/fault-request bit |
| Six actually consumed limits | self.params, controller:55/70/71; helper:72/76-88 | Explicit Limits snapshot, NOT CP reconstruction/config backup |
| Prior final command | self.apply_torque_last, controller:60/71/81 | previous_applied at entry, post-inactive previous invocation |
| Prior fault counter | self.angle_limit_counter, controller:57/74 | angle_counter BEFORE current update |
| Prior integer candidate | No persisted source field in selected slice | model-owned previous_requested; never infer from previous CC/returned output |
| Model invocation index | No elapsed-time equivalent | Explicit model bookkeeping; NOT frame, timestamp or10ms |

Copying mutable fields sequentially or comparing them twice does not establish
atomicity. A future native reader requires single-owner/quiescent synthetic message
ownership and one same-boundary params/state receipt; no concurrent/live reader is
supported. Do not invoke CI.apply/update, instantiate CP/CarControllerParams or read
carOutput to obtain missing values. card.py:245 precedes controls_update:250;
carOutput is not current apply-time/state authority.

## Future synthetic extraction interface (R14, not implemented)

Location: integration_tools/message_boundary_types.py and message_boundary.py;
excluded from wheel. Exact frozen/slots records, no defaults, unknown kwargs use
ordinary TypeError. No dictionary/JSON/file/log loader or arbitrary object reader.
All names below are proposed future APIs, not original openpilot API fields.

- SyntheticActuatorsV1(torque:float).
- SyntheticCarControlV1(actuators:SyntheticActuatorsV1, latActive:bool).
- SyntheticCarStateValuesV1(steeringTorque:float, steeringAngleDeg:float).
- SyntheticCarStateWrapperV1(out:SyntheticCarStateValuesV1).
- SyntheticPreviousV1(snapshot_stage:str, sequence_id:str,
  previous_invocation_index:int|None, source_previous_applied:int,
  source_angle_counter:int, model_state:public LateralState).
- SyntheticBoundaryFrameV1(schema_version:int, scope:str, profile_id:str,
  source_set_id:str, value_representation:str, sequence_id:str,
  invocation_index:int, static_context_reference:str, consumed_settings_origin:str,
  cc:SyntheticCarControlV1, cs:SyntheticCarStateWrapperV1,
  consumed_limits:public Limits, previous:SyntheticPreviousV1).
- PreparedLateralInputV1(contract_id:str, source_set_id:str, sequence_id:str,
  sample:public LateralInput, state:public LateralState, custody_claim:str,
  precision_claim:str, time_semantics:str).

extract_synthetic_message(frame:SyntheticBoundaryFrameV1)->PreparedLateralInputV1
only validates/copies supplied values. No step/simulate/quantization/model execution,
output command, next state, constructor args for F61 or state writeback is produced.
MessageBoundaryError(ValueError) has stable .code and no partial result.

Exact metadata:

- schema_version=1; scope=SYNTHETIC_DEVELOPMENT_ONLY.
- profile_id=R13_HYUNDAI_TORQUE_ENTRY_SYNTHETIC_V1.
- source_set_id=R11_C8FB9068_4134C0D1_V1.
- value_representation=SYNTHETIC_PYTHON_BINARY64.
- static_context_reference=SYNTHETIC_CONTEXT_NOT_VEHICLE_AUTHORITY.
- consumed_settings_origin=EXPLICIT_SYNTHETIC_CALL_ENTRY.
- previous.snapshot_stage=ENTRY_BEFORE_CURRENT_LIMITER.
- Sequence IDs: exact builtin ASCII[A-Za-z0-9_-]{1,64}.
- Output custody_claim=SYNTHETIC_DECLARATION_ONLY;
  precision_claim=EXACT_SUPPLIED_BINARY64_NOT_NATIVE_ABI;
  time_semantics=INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME.

This synthetic extractor is not a native adapter or replacement for R12.advance.
Its type/order/cross-field consistency cannot certify the previous transition.
It does not have a trusted arbitrary-input prefix, unlike R12's closed registry.
A valid but different prior integer candidate cannot be disproved from source
previous-applied/counter alone: preserve it with DECLARATION_ONLY, never claim
history validation or derive it from torque. Actual custody stays NOT_ESTABLISHED.

## Validation order and domains

Check exact root class before attributes; then exact nested classes before their
attributes, including public Limits/LateralState. Never use hasattr/getattr,
to_dict/as_builder, float()/int() coercion, callbacks or subclass operations.

1. Root/nested exact record classes: BOUNDARY_RECORD_TYPE. Missing constructor
   args fail TypeError; None payloads fail this boundary, not default recovery.
2. Builtin schema/scope/representation/context/settings labels: BOUNDARY_SCOPE.
   Exact profile/source-set and installed package0.3.0: BOUNDARY_SOURCE_PROFILE.
3. Builtin ASCII sequence labels matching frame/previous: BOUNDARY_SEQUENCE.
4. invocation_index builtin int0..4095, model_state.index builtin int0..4096
   equal to invocation_index. At0 previous_invocation_index is None; otherwise
   builtin int equal to invocation_index-1. Fail BOUNDARY_ORDER; no timestamp math.
5. Builtin/domain validation: BOUNDARY_DOMAIN. Request finite float[-1,1]; driver
   finite float abs<=1024/denominator<=256; angle finite float abs<=180/denominator
   <=256; active exact bool. STEER_MAX int1..2048, UP/DOWN/ALLOWANCE int0..64,
   FACTOR/MULTIPLIER int0..8. Source/state prior applied and prior integer candidate
   ints[-2048,2048], counters int0..90. At index0 previous_requested must be None;
   otherwise it must be int in range. Bool/numeric strings/NumPy scalars reject.
6. snapshot_stage exact builtin ENTRY_BEFORE_CURRENT_LIMITER, source_previous_applied
   equals model_state.previous_applied, source_angle_counter equals model state's
   counter: BOUNDARY_CUSTODY. At index0 applied/counter must both0. Missing state
   is never initialized as a fallback. Same labels are not cryptographic custody.

All supplied float bits, including signed zero, survive unchanged. No IEEE32
rounding, normalization/sign/scale changes or clamp. A valid synthetic409 scale is
not authority for a vehicle setting; a250 allowance fails without reducing it.
Changing limits between declared adjacent samples does not retroactively rescale
previous command. Integer prior command can exceed current scale within the public
domain; extraction neither clamps nor produces the downstream95/5=19.0 result.

## Float32/native qualification specification — NOT_RUN, NOT_AUTHORIZED

Schema Float32 does not prove Python type, when assignment rounds, default/presence
behavior, reader/builder lifetime, serialization or bit preservation. A type name,
__module__, user label or dependency version alone is not qualification.

Future qualification MUST be a separately scoped isolated synthetic native-only
task. It does not authorize Controller/Runtime/CAN/F61/actual logs or deployment.
Do not add capnp to the current component lock/wheel/CI or run it during R13/R14.

Required evidence before specifying an actual-reader implementation:

Q1. An explicit native/schema-execution scope and closed runtime artifact receipt:
Python/platform, exact installed pycapnp/native binaries/distribution hashes,
resolved car.capnp, /include/c++.capnp and loader/dependency closure. Root lock
entries are candidates only. No default backend selection or missing-file fallback.

Q2. Record actual construction API, exact reader/builder classes AND schema identity,
field ordinals/types, object ownership/lifetime and exceptions. Reject wrong-schema
objects even if their generic dynamic class matches. No class/signature is guessed
here; native_constructor_signature and qualified_runtime_types remain null.

Q3. Synthetic construction ledger records explicitly written required field paths.
Schema defaults are not missing-field evidence: absent torque/active may read as
0/False. An all-default message is not accepted as a complete explicit sample.
Ordinary value equality or dynamic has-field guesses do not prove presence.

Q4. With synthetic messages only, compare assigned/observed value types and exact
float.hex/sign, reader vs builder and owned serialization readback. Mathematical
IEEE32 control0.3 has logical word3e99999a and value0.30000001192092896; this is a
reference expectation, NOT observed pycapnp behavior or claimed wire bytes.
Also negative zero, +/-1, smallest subnormal, normal boundary, NaN/inf, overflow,
unset fields and invalid lifetime. Preserve observed failures; no tolerance/coercion.
Out-of-model qualification values must never enter the model or F61 calculator.

Q5. Bind CC message, CS.out message, six consumed limits, both source prior-state
fields and separate model bookkeeping to one controlled call-entry snapshot.
Wrong source/schema/phase, cross-sequence/state or concurrent access rejects.
Qualification of synthetic messages still does not establish actual vehicle custody.

Q6. Only exact observed supported numeric types can be accepted; unsupported
readback blocks the native profile, never changes the pure package domain.
Native contract ID/API/rejection behavior require a new source-derived amendment
after Q1-Q5 PASS. R12 records remain binary64 fixtures, not retroactively Float32.

## Completion and next boundary

R13 readiness means design/contract/test matrix/future plan are coherent, source
facts rechecked and existing regression gates preserved. New boundary and native
test cases remain NOT_IMPLEMENTED/NOT_RUN, not PASS because they are written down.
R14 may implement the pure synthetic extraction-only plan; native qualification and
actual reader/hook remain closed and are not unconditionally executable plan tasks.
No property access to native objects is implemented by either completed R12 or R13.

Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
Candidate/Runtime=NO_GO; actual activation/F70UH/F70V/F71=NOT_ALLOWED;
SOURCE_SCHEMA_UNQUALIFIED=6000; D2=PERFORMANCE_NOT_EVALUATED;
F19=LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY=NOT_PROVEN.
