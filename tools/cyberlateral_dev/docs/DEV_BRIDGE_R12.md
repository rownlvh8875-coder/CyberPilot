# R12 — fixed synthetic development bridge

This implements the R11 contract F70UGZ_R11_DEV_BRIDGE_V1 in DEV tools only.
The R11 design/source-map/plan are historical preregistration records; this file
records implementation. Nothing reads a real CC/CS/CI/CP object or raw log.

## Implemented boundary

- Exact frozen/slots DevSourceSnapshotV1, DevBridgeSessionV1, DevBridgeResultV1.
- Explicit fixture_snapshot(fixture_id, offset, sequence_id),
  begin_sequence(fixture_id, sequence_id), advance(snapshot, session) signatures.
- Seven fixed fixtures only; catalog fingerprint and package0.3.0 are prerequisites.
- Scope/profile/sequence/fixture/order/domain/bitwise payload/full previous-state
  checks in the preregistered rejection order. Stable DevBridgeError.code; unexpected
  model ValueError chains to BRIDGE_MODEL_REJECTED with no fallback or partial result.
- No original module imports, IO or native object introspection in advance.
  Metadata builtins are checked before comparison/hash/regex/numeric operations.
- offset0 uses the explicit initial state, including the history-scale stress seed;
  nonzero offsets recompute only the trusted prefix to verify all previous fields.
  Each accepted advance performs one NEW current step plus prefix validation work.
- Previous requested state is integer-candidate model bookkeeping, NOT previous
  normalized request or F61 native. Index is invocation bookkeeping, NOT time.
- Exact signed-zero/binary64 identity, no Float32 rounding, coercion, clamp, sign
  change or default scale. history-scale intentionally emits95/5=19.0 unchanged.
- Input/session are immutable. Same original pair retry is deterministic; an old
  snapshot with an advanced session rejects. Sessions do not share mutable state.
  This is not an ownership, anti-replay, concurrency or persistence protocol.

## Verification and evidence

23 bridge unit tests and8 probe/installed-artifact tests extend the existing156
tests. Literal first-transition/history-scale controls, real interleaved full-output
golden hashes and exact rejection codes exercise the real package. Invalid labels,
side-effecting/subclass values, unsupported allowance250, wrong scale, wrong full
previous state, signed zero and Float32-style substitution reject without repair.

The DEV probe accepts only --output NEW. Existing directories/files/dangling links
and unknown data/log/source/policy/time arguments reject before probe work. It
stages RESULTS.pending, writes the checksum, then publishes RESULTS.json last;
failure directories are not successful evidence. The core transition is pure;
the separate probe performs evidence IO.

The verifier installs the unchanged wheel offline/no-deps into an empty venv,
runs the probe twice under -I/-B from an unrelated cwd, requires no NumPy/original
modules and validates the actual environment facts. Both complete output pairs,
canonical JSON, frozen per-scenario result hashes, full final sessions, exact gates
and Manifest are checked. Identically tampered pairs with fresh checksums reject.
The additional installed probe is glue/regression coverage, not independent
arithmetic certification; existing separate helper arithmetic tests remain.

All77 imported bytes and the runtime API/version/dependencies remain unchanged.
Expected wheel:46646 bytes,27 RECORD entries, SHA256
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
The existing R9 caller-harness contract is unchanged. Top-level verifier success is
F70UGZ_R12_SYNTHETIC_DEV_BRIDGE_REFERENCE_PASS.

Individual report/numeric/harness/bridge pairs and wheel bytes are reproducible.
Whole verification Manifest hashes include logs, timings/platform/install output;
they are not claimed byte-identical across complete runs or different machines.

## Still not allowed

No original Controller/Runtime/CAN/F61/schema import, executable compile or runtime
hook; no actual input, r/dt calculation, candidate evaluation, observer/capture,
vehicle install or main merge. Only the existing two exact helper bodies execute
in authorized synthetic DEV reference tests, not the bridge/installed wheel.

Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Evidence Gate=FAIL;
Candidate/Runtime=NO_GO; actual activation/F70UH/F70V/F71=NOT_ALLOWED;
SOURCE_SCHEMA_UNQUALIFIED=6000; D2=PERFORMANCE_NOT_EVALUATED;
F19=LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY=NOT_PROVEN.

A future actual-object reader, vehicle-specific domain/profile, source hook,
timestamp/state custody or r policy requires separately scoped design/evidence.
Synthetic PASS does not authorize one.
