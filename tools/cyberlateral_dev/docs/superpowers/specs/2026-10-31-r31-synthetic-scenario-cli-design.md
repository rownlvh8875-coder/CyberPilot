# R31 user-declared synthetic scenario CLI

User approved continuing with R30's proposed developer scenario-file CLI. Ordinary
implementation choices are delegated; no routine design/permission menus. This
does not establish complete CyberPilot product requirements or vehicle authority.

## Chosen approach and boundaries

Add a separate repository DEV script `tools/scenario.py` over unchanged public0.3.0
source. Do not alter the frozen wheel, public `python -m cyberlateral_dev` CLI,
model math/API, existing fixed/native runners or default verification workflow.
An installed-wheel redesign or generic native/log reader is outside this task.
The new tool selects the verified local DEV source tree explicitly; receipts must
not describe this as installed-wheel execution. Pure API semantics are binary64,
NOT the narrower R28 exact-Float32 native subset.

## V1 input contract

Exactly these root keys: schema_version(int1), scope(string SYNTHETIC_ONLY),
scenario_id(ASCII letter then0..63 letters/digits/_/-), limits, initial_state,
samples. No unknown/optional/default fields, timestamps/dt/r, source paths,
vehicle context or execution hooks. All nested objects also have exact keys.

limits has the6 public Limits integer names. STEER_MAX1..2048; UP/DOWN/ALLOWANCE
0..64; FACTOR/MULTIPLIER0..8. These are explicit synthetic model parameters, not
physical scale or approved policy. initial_state has index,previous_requested,
previous_applied,angle_counter: index0..4095, applied[-2048,2048], counter0..90;
index0 requires null/0/0 canonical history, index>0 requires requested integer
[-2048,2048]. No history inference or repair.

samples is a list1..4096, each exactly index,request,driver,angle_deg,lat_active.
Indices are builtin int, adjacent from initial_state.index, never above4095.
request builtin finite float[-1,1]; driver float[-1024,1024] and angle float[-180,180]
with dyadic denominator<=256. lat_active builtin bool. No int→float coercion:
JSON 0.0/1.0 accepted for float fields, bare0/1 rejected. Decimal/exponent floating
tokens parse once to builtin binary64 using Python JSON rules; no Float32 rounding,
normalization/clamp or inverse transform. Signed zero is preserved in input hex.
The model retains its own defined integer quantization/output behavior.

UTF-8 strict JSON, no BOM/comments/trailing data/duplicate keys/NaN/Infinity.
Maximum input1MiB, float token128 characters, integer token32 characters and64
container nesting levels independent of caller recursion settings. These
are DEV resource caps, not vehicle constraints. Bounded regular-file read with
no final symlink/FIFO/device/directory input. POSIX nonblocking/nofollow support
required; validated platform Linux/CPython3.12.13/binary64. No portability promise.

Read owned bytes once and record their SHA; scope is a declaration, NOT origin
authentication. A JSON label cannot prove data is synthetic. This task uses only
constructed fixtures; real vehicle data remains unauthorized. Report must not
claim an observed actual-input count0 merely from a caller's label.

## Flow and output

Existing/dangling output or missing parent rejects before input read/model work.
Parse and validate the ENTIRE scenario before any model call. Domain bounds come
from exact frozen request_quantizer/state_model/domain source; model validates
again during simulation. Reject invalid late samples without partial simulation.

After preflight, verify imported source identity, pinned Python/binary64 and exact
source import origin. Private cold pycache prefix prevents stale caches from
substituting for source. Trust boundary is cooperative process/filesystem, not OS
attestation, hostile monkeypatch protection or race-free external custody.

Build p.Limits/LateralState/LateralInput then call unchanged p.simulate once.
Verify result type/length and use existing strict input/output projections.
Carry preceding actual model next_state; do not recompute prefixes or retry.
Generic custom outputs are model results, NOT independently proven predictions.

Write deterministic INPUT.json, TRACE.csv, SUMMARY_KO.md and RESULTS.json plus
environment-specific RECEIPT.json and5-entry SHA256SUMS.txt. RESULTS.json published
last; failed publication has no valid successful-final marker. No overwrite or
deletion. Crash atomicity/resume/concurrency is not promised. Invalid input creates
no output. Full files rendered in memory before publication; bounded4096 calls.

Portable input projection uses float.hex, explicit integer/null/bool and initial
state. RESULT includes raw-input SHA, model/source/tool identity, full per-step
prepared input/state/output, final state and gates. CSV13 fixed scalar columns:
index,request_hex,driver_hex,angle_hex,lat_active,previous_requested,previous_applied,
angle_counter_before,integer_request,limited_command,final_command,steer_request,
angle_counter_after. Null is explicit, no user text/formula column. Receipts retain
actual paths/Python identity; complete manifests need not match across locations.
Identical raw input bytes/code must produce identical4 portable files; input text
whitespace changes raw identity even if parsed numerical values are equal.

## Verification and handoff

TDD parser/IO/engine/CLI, literal4-step sign/inactive outputs and explicit resumed
fault state, binary64 0.3 vs Float32 distinction, signed zero,4096 bound, hostile
JSON/file/output inputs, late-invalid no-model guard, exact source/version guards,
no forbidden module imports, deterministic CSV/JSON and relocated reproduction.
Correct R30-M1 path wording as scoped documentation cleanup. Full suite/static/
wheel/original guards and unchanged native R27/R28/R29 regression; fresh final
review, exact-head pure CI and existing Draft PR2, no main merge.

R_BUDGET UNRESOLVED, Static Gate FAIL, actual r/T2/scale null. No F61/Controller/
Runtime/CAN/actual vehicle input/r/dt/performance/candidate evaluation or activation.
Output remains SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE. F70UH/F70V/F71 NOT_ALLOWED.
