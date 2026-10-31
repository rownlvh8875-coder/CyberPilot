# R11 — openpilot-shaped development bridge design

Status: DESIGN_ONLY_NOT_IMPLEMENTED. This specifies a future synthetic DEV bridge,
not a runtime hook, installed controller, F61 adapter or production approval.
User delegated routine choices; the technical choices below are the author's.

## Goal, scope and alternatives

Make the connection between source signal names and the existing pure0.3.0 API
explicit before writing glue. Reuse the verified module without changing its
arithmetic/API/wheel or hiding state, precision, context or policy assumptions.

Alternatives considered:

- A direct CarController hook would require original imports, mutable live state,
  CAN/runtime integration and actual context qualification; not this DEV step.
- A live observer would require collection/timing/state custody not established
  by existing evidence; no observer/capture is authorized or implemented here.
- Chosen: an isolated, typed, fixed-fixture-only DEV bridge using source-shaped
  field names. It imports only the installed pure package and stdlib, never
  openpilot/opendbc/cereal/capnp. Tradeoff: demonstrates glue on a closed synthetic
  subset, NOT a usable production adapter or an attestation of input provenance.

## Exact source context

OPENPILOT_DEV_BRIDGE_SOURCE_MAP.json records full hashes, sizes, commits and source
references. Selected source context is CyberPilot c8fb906815530460ed156f14e09e1f312bb0f851
with its exact opendbc gitlink4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76.
The controller/helper/schema bytes match the committed reference fixtures exactly.
interfaces.py, values.py and card.py were additionally checked against Git HEAD
blob bytes. Inspection was read-only text/hash/AST, no original import/execution.

This does not rebind the historical ajouatom/openpilot6ca11a4... or1dac44b... stages.
No equality to those branches, laptop deployment or installed vehicle is claimed.

Profile ID: R11_HYUNDAI_TORQUE_SYNTHETIC_V1.
Source-set ID: R11_C8FB9068_4134C0D1_V1.
Bridge contract ID: F70UGZ_R11_DEV_BRIDGE_V1.
These are reviewed labels, not cryptographic authentication or vehicle authority.

## Source-to-model mapping

All mappings below describe the selected source slice, not whole-controller parity.

| Source symbol / stage | Existing model field | Rule / boundary |
| --- | --- | --- |
| CC.actuators.torque, update line70 before integer conversion | LateralInput.request | Exact supplied builtin binary64 value; finite[-1,1]; no F32 rounding, sign flip, clamp or normalization |
| CS.out.steeringTorque, update line71 | LateralInput.driver | Preserve numeric value; schema says native CAN units, NOT physical Nm; tested dyadic subset only |
| CS.out.steeringAngleDeg, update line74 | LateralInput.angle_deg | Preserve degree-labelled numeric value; model finite/dyadic subset; no radian conversion |
| CC.latActive | LateralInput.lat_active | Exact builtin bool; distinct from CC.enabled and fault request bit |
| Six consumed self.params fields | LateralInput.limits | Exact explicit synthetic Limits; no CP constructor/default/config lookup |
| Prior post-inactive self.apply_torque_last, lines71/81 | LateralState.previous_applied | Previous final integer command, NOT previous normalized request or current pre-gate limiter result |
| self.angle_limit_counter, lines57/74 | LateralState.angle_counter | Previous fault counter; current result returned explicitly |
| No matching persisted source field | LateralState.previous_requested | MODEL_BOOKKEEPING_ONLY: prior integer candidate int(round(q*scale)), NOT previous normalized/native F61 sample |
| No source time/phase equivalence | LateralInput.index / LateralState.index | Synthetic invocation bookkeeping only, NOT self.frame, timestamp, seconds or10ms |

The model keeps quantization -> driver/history limiter -> fault request -> inactive
gate -> previous-applied update. A false fault request does not itself zero torque.
Integer command and steer_request remain separate. No pre-limit/requested value is
silently substituted for a post-inactive previous-applied value.

## Precision and supported domain

The source schema uses Float32 for actuator torque, driver torque and angle. That
does not establish actual Python reader/coercion/serialization behavior here.
The source torque comment says[0,1], while the tested pure API supports[-1,1]; the
comment is not adopted as runtime range validation. This design explicitly accepts
SYNTHETIC_PYTHON_BINARY64 records only, not claimed Cap'n Proto readback values.

No conversion is performed to make unsupported values fit. Preserve signed-zero
and exact float.hex values when comparing a snapshot with its registered fixture.
Reject NumPy scalars, numeric text, bool-as-int, nonfinite values and implicit casts.
Public package validation remains unchanged:

- request: builtin float, finite[-1,1].
- driver: builtin float, finite abs<=1024, as_integer_ratio denominator<=256.
- angle: builtin float, finite abs<=180, denominator<=256.
- STEER_MAX: builtin int1..2048 (intersection of input quantizer/output domain).
- UP/DOWN/ALLOWANCE: builtin int0..64; FACTOR/MULTIPLIER: int0..8.
- model index0..4095; returned state index may reach4096; previous integer fields
  bounded[-2048,2048], counter0..90; canonical index0 state is(None,0,0).

values.py makes vehicle/flag-dependent choices; e.g. its CANFD branch allowance250
exceeds the model's allowance64 bound. This is an explicit unsupported-context
example, not permission to reduce250, widen the module or choose another scale.
CustomSteerMax409 and historical LC/override paths are not authority for this
profile. The selected caller passes four helper arguments; dynamic steer_max
override and different callers need a separately reviewed profile.

## Future typed DEV interface — names are proposed, not implemented

Location: integration_tools/dev_bridge.py (DEV only, excluded from the wheel).
Records are exact frozen/slots dataclasses; no defaults and no duck-typed readers.

DevSourceSnapshotV1 fields:

- schema_version:int=explicit1; scope:str=explicit SYNTHETIC_DEVELOPMENT_ONLY;
  value_representation:str=explicit SYNTHETIC_PYTHON_BINARY64.
- profile_id:str; source_set_id:str; fixture_id:str; sequence_id:str.
- offset:int; model_index:int; requested_torque:float; driver_torque_native:float;
  steering_angle_deg:float; lat_active:bool; limits:public Limits.

DevBridgeSessionV1 fields:

- schema_version:int; scope:str; profile_id:str; source_set_id:str;
  fixture_id:str; sequence_id:str; next_offset:int; model_state:public LateralState.

DevBridgeResultV1 fields:

- contract_id:str; fixture_id:str; sequence_id:str; consumed_offset:int;
  diagnostic:public LateralOutput; next_session:DevBridgeSessionV1.

Success returns a complete immutable result; rejection raises
DevBridgeError(ValueError) with a stable .code and no partial result. This result
is NOT CarControl.Actuators, a message builder, a CAN packet or F61 constructor args.

Functions (required explicit arguments, no global mutable sessions):

- fixture_snapshot(fixture_id:str, offset:int, sequence_id:str) -> DevSourceSnapshotV1.
- begin_sequence(fixture_id:str, sequence_id:str) -> DevBridgeSessionV1.
- advance(snapshot:DevSourceSnapshotV1, session:DevBridgeSessionV1) -> DevBridgeResultV1.

Sequence ID is ASCII[A-Za-z0-9_-]{1,64}. Fixture IDs and data come only from the
existing seven-scenario fixed_catalog with catalog SHA
74095144882ff3977679ce92ec7dad0e7bf3f532a0cacae2cfa26f4aab0fd287.
No file/log/native-object loader or arbitrary data registration exists in V1.
The factory fills explicit fields from the registry, never from self.params/CP.
advance compares every payload field (including float.hex) with that registry.
Metadata labels/hash matches are not adversarial provenance attestations; the
controlled synthetic workflow remains necessary.

## State, ordering, retry and rejected contexts

begin_sequence uses that fixture's explicit initial_state. Six fixtures use the
canonical state; history-scale intentionally uses State(1,100,100,0). That special
seed is a registered synthetic stress case, not a Controller init or runtime
resume authority. Unknown state is never reset to zero as a recovery fallback.

advance binds sequence/fixture/profile/source-set/offset before new transition.
Expected previous state is independently rebuilt from trusted fixed fixture data:
offset0 uses fixture.initial_state; offset>0 uses
simulate(fixture.samples[:offset], fixture.initial_state).next_state. Never call
simulate on the empty prefix. Compare all state fields and builtin types; do not
replace the caller's bad state with the expected state. This costs bounded prefix
work (catalog max94 samples) and is not an independent numerical oracle.

Only then map to LateralInput and call the current step. There is one NEW current
transition plus zero or offset prefix-validation transitions, not one total model
call. Return explicit next_session with offset+1. Sessions/inputs are never mutated.
Reusing the same original immutable pair is a deterministic retry, not prevented
replay. Using an old/duplicate sample with an advanced session rejects. No global
sequence-ID ownership, persistence, anti-replay or concurrent-session manager exists.

Rejection order/codes (constructors reject unknown kwargs with ordinary TypeError;
there is no JSON parser promising a different error API):

1. Exact snapshot/session classes, before attribute access: BRIDGE_RECORD_TYPE.
2. Builtin schema_version1 and exact scopes/representation: BRIDGE_SCOPE.
3. Exact profile/source-set on both records: BRIDGE_SOURCE_PROFILE.
4. Valid/matching sequence labels: BRIDGE_SEQUENCE.
5. Known/matching fixture IDs: BRIDGE_FIXTURE.
6. Builtin bounded/matching offset, registered model_index: BRIDGE_ORDER.
7. Exact Limits/LateralState and all builtin/domain checks: BRIDGE_DOMAIN.
8. All snapshot values equal the registered payload including float bits:
   BRIDGE_SNAPSHOT_MISMATCH.
9. Full previous state equals the trusted prefix state: BRIDGE_STATE_MISMATCH.
10. Unexpected package ValueError during trusted-prefix/current computation:
    BRIDGE_MODEL_REJECTED with chained original exception, no retry/default.

Steps1..8 do not feed arbitrary input into model calculations. Step9 may compute
only the trusted synthetic prefix; a rejected caller state never drives the new
transition. A real CC/CS/CI object is rejected at step1 without touching properties.
At each stage require builtin metadata types before equality, dictionary lookup,
regex or numeric operations; do not invoke methods of a string/int subclass or
arbitrary field object. Session has no value_representation field; step2 checks
that field only on the snapshot. The registry fingerprint/package version are
checked as a source-profile prerequisite, without original source imports or IO
inside the pure transition. A mismatch is BRIDGE_SOURCE_PROFILE, not auto-upgrade.

## Output, time and policy boundaries

diagnostic.projection.integer_command maps conceptually to final apply_torque.
normalized_expression is exact builtin command/scale expression, not an inverse
quantization or wire value. Float32 projections are diagnostics, not serializer
execution. History-scale can produce95/5=19.0: preserve it, no hidden[-1,1] clamp.
No result is written back to actuators, a controller state or sendcan.

card.py publishes carOutput before controls_update, uses live monotonic or replay
CAN log time for CI.apply, and the selected lateral slice does not consume
now_nanos. Therefore no carOutput timestamp/frame/DT_CTRL/dt field is accepted or
derived. This bridge does not revise the separate exact F61 time contract.
No rate_budget_per_s/r/R_BUDGET parameter, F61 invocation or owner-policy constant
is introduced. Synthetic limits are not an approved vehicle scale/rate budget.

Static Gate FAIL does not block this closed synthetic DEV exercise, but does block
all actual vehicle use. Matching source bytes or an Owner's general delegation
does not promote synthetic PASS to vehicle qualification. No live observer, import
of original modules, CAN, Runtime activation, actual log or vehicle input is allowed.

## Completion and next implementation boundary

R11 completes source-backed design and the separate implementation plan only.
No DevBridge classes/functions above exist yet. R12 may implement only this DEV
contract, test exact field/state/registry/order/precision rejection and isolated
installed-package use, then integrate into the existing one-command synthetic gate.
It must leave package0.3.0/wheel and original source bytes unchanged. Actual vehicle
integration, physical performance, policy r/T2/scale and F70UH/F70V/F71 remain closed.
