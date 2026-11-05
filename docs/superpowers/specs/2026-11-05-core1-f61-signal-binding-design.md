# CORE1 — Bring the approved synthetic F61 signal boundary into DEV

Base: main `eed06ee21765d9f61d0691824146725c1767e18d`. The owner delegated ordinary
offline choices and inline execution without repeated approval questions. CORE1
is an offline milestone name, **not authorization for the prohibited F-71 stage**.

## Intent and evidence

The current DEV component has a pure synthetic command/state model, R28 native
synthetic adapter, R31 scenario input and R70 saved-trace summaries. Those APIs are
not the recovered F61 API. The approved F70UGHR signal-pair reference and independent
oracle exist only in sealed external evidence, not in the current Git component.
Integrate that existing boundary before designing a new production reader.

Canonical F70UGHR ZIP SHA256:
`a2686fe18fe094ef3a9a5b452c71fd36b19f5d340e4aa90d3e95e4abfa879192`.
F61 original: `synthetic_rate_constraint_feasibility_v1.py`, 6735 bytes,
`f343b0edd5578348c570692f05d655dee8e2b1555492a1d99b218d3f81fab035`.
Verify ZIP CRC, complete Manifest, seal, original bytes and AST field inventory
before using the reference. Never import, execute or bytecode-compile F61.

## Approaches and author choice

1. Build a new real-call parser now: rejected. Existing F70UGZ already checks a
   different observation-record draft; no complete actual call pair or authenticated
   consumed state is established. A new parser would duplicate work and invent binding.
2. Change R31/R28 or public0.3.0: rejected. Invocation-only synthetic model records
   cannot silently become time-bearing F61 records; changing the frozen wheel broadens scope.
3. Integrate the already approved standalone synthetic pair projection, keeping its
   independent oracle and literal tests: chosen by the author under delegated authority.

## Deliverable and exact interfaces

Create `integration_tools/f61_signal_adapter_v4.py` exposing `adapt(payload: object)
-> dict`. Preserve all original return keys, codes, validation order and accepted
domain. Create `integration_tools/f61_signal_contract_v4.py` with only the frozen
data constants used by the reference; no schema builders, policy or calculator.
Use a relative contract import. Migrate original algorithms without redesign;
formatting/import relocation is allowed for these reference copies, not the F61 original.

Create test-only `project/f61_signal_oracle.py`: original independent integer/IEEE
oracle with only its contract import relocated. It must not import the adapter,
Fraction, model or F61. New unittest tests exercise actual APIs, literal expected
values and exact oracle equality. No new CLI, JSON reader, dependency or runtime hook.

Selected stage: declared `REQUESTED_NORMALIZED`, source symbol
`CarController.update::CC.actuators.torque`, before integer conversion/limiter.
Previous means same-stage immediately previous **request**, not applied/limited output.
Source commits remain the two original ajouatom/openpilot pins. Caller-provided
labels and source hashes are declarations, not source reauthentication.

Only `SYNTHETIC_REFERENCE_ONLY` / `PUBLIC_SYNTHETIC_SOURCE_FIXTURE` is accepted.
Any actual mode/vehicle context rejects even if caller says gate PASS. Never infer
or certify real provenance from the synthetic label. This is a cooperative in-memory
Python API, not a hostile-input sandbox or a bounded external-file reader.

Finite built-in float values must embed binary32 exactly and lie in [-1,1].
Preserve signed zero, no clamp/normalization/rounding; scale1/offset0 refer only to
the already-normalized request identity conversion, not vehicle integer STEER_MAX.
Sequences are adjacent uint64. Require same source/epoch/domain/stage/mode.
Both LIVE_MONOTONIC_NS and REPLAY_RECORDED_CAN_NS remain distinct explicit domains.

Time is the declared CI.apply now_nanos pair, shifted to previous_time=0.0.
Accept only an exact positive binary64 second interval; no tolerance, nominal
period or rounding. Exact 10ms and 1ns remain rejected. The inherited synthetic
reference permits arbitrary-size signed Python integer epochs; do not advertise
this as int64-ns production validation or silently narrow it in this migration.
Huge epoch hexadecimal traces preserve exact offsets without decimal-token limits.

Flags/reset are preserved, not evaluated for feasibility. `f61_input` retains the
marker `PARTIAL_ADAPTER_SIGNAL_PROJECTION_NOT_CONSTRUCTOR_ARGS`; its fields are
adapter-internal, not the 18-field `FeasibilityInput` constructor. `rate_budget_per_s`
is rejected as an adapter input; `calculator_invocation_allowed` is always false.

## Requirements and completion boundary

Add a concise Korean code-to-requirements/backlog document with evidence paths,
implemented/synthetic-only/unresolved distinctions and testable completion gates.
Separate confirmed user constraints from author-selected development priorities;
whole-product requirements and completion percentage remain NOT_ESTABLISHED.
Link it and the adapter guide from the component README, retaining historical guides.

Success means the existing V4 projection is available in DEV with exact independent
synthetic parity, without any changes to public src/imported77/lock/workflow/cloud
profile or old R28/R31 readers. No production installation/capture/decoder/controller/
Runtime/CAN, F61 invocation, actual r/scale/T2 choice, GitHub/HF publish or CI dispatch.
Synthetic time projection is NONZERO and reported separately from actual r/dt work.

Fresh baseline full DEV gate, test-first missing-feature failure, focused tests,
full final gate/static/frozen-wheel verification, exact Git source preservation,
and one fresh whole-branch review are required. Keep evidence and linked worktree.
External ledger replaces unavailable cloud skill bookkeeping scripts. Ordinary
local feature commits are allowed; no main merge/push/PR publication in this task.

Maintain R_BUDGET UNRESOLVED, Static Gate FAIL, actualr/T2/scale null,
SOURCE_SCHEMA_UNQUALIFIED6000, Candidate/Runtime NO_GO, D2 PERFORMANCE_NOT_EVALUATED,
F19 LEGACY_UNRESOLVED, NATIVE_EXACT_REPLAY NOT_PROVEN, F70UH/F70V/F71 NOT_ALLOWED.
