# CORE41 offline call recorder design

## Intent and authority

The user approved the transition to recorder design/offline implementation. Their
earlier instruction delegates implementation choices and opts out of repeated
questions. The choices below are the implementer's, not claims of separate
approval of a vehicle collector. No real capture, hardware, Controller, Runtime,
CAN, F61, actual dt/r calculation, policy number, upload or deployment is allowed.

## Approach

Keep the existing Python 3.12.13 DEV stack with no new dependencies. A new
in-memory transaction recorder consumes only the existing CORE3/4 frozen
counterfactual carriers. Do not modify their validators, the wheel, model, source
pins, fixtures or calculator. Reuse same-package CORE3/4 validation helpers for
single records and the public prepare_limiter_pair for adjacent state links.

Alternatives considered: a real Controller hook needs a separately qualified
source/build, observation-impact budget and execution scope; a generic JSON/log
reader would broaden accepted actual data unnecessarily. Neither is implemented.
The chosen recorder adds missing start/completion/abort/overflow behavior, not
another limiter or arithmetic oracle. No source objects/getters are read.

## Interfaces and lifecycle

integration_tools/offline_call_recorder.py:
- RecorderError(ValueError) has fixed code, never input/foreign exception text.
- SyntheticCallRecorderV1(capacity: int), exact built-in capacity 2..128.
- begin(request: object) -> None validates an exact CORE3 request, remembers it,
  and, if there is a prior completed call, checks same context, adjacent sequence,
  increasing original ns timestamps, no reset. No time difference is computed.
- complete(frame: object) -> None requires an exact CORE4 frame matching the
  pending request, validates it and every adjacent settings/state/counter link,
  and commits exactly one frame. Entry/settings in this frame are caller
  declarations supplied at completion, not independent consumption-time capture.
- abort() -> None permanently invalidates this recording. No resume/backfill.
- finish() -> FinishedSyntheticRecordingV1 only with no pending call and 2..capacity
  completed calls. It closes the recorder. It never exposes a successful prefix.
- FinishedSyntheticRecordingV1(records: tuple[SyntheticLimiterSnapshotV1, ...])
  revalidates every record and link. Metadata/permissions are constructor-fixed:
  contract_id CORE41_COUNTERFACTUAL_CALL_RECORDING_V1, scope
  COUNTERFACTUAL_RECORDING_ONLY, time_semantics ORDER_ONLY_NO_DELTA_OR_PERIOD;
  source_identity_reauthenticated/model_input_allowed/v4_payload_allowed/
  f61_input_allowed/actual_activation_allowed are false.

All validation failures on an open recorder permanently fail it. First error is
specific; later operations give RECORDER_FAILED. Explicit abort gives
RECORDER_ABORTED, successful finish gives RECORDER_CLOSED. Repeated begin, missing
begin, mismatched request, overflow, incomplete finish, fewer than two complete
records, invalid frame, lost/reset/context/settings/state/sequence/time continuity
cannot be resumed. Overflow never evicts or overwrites records. Fresh instances
start separate histories; there is no reset API or persistent resume. This is a
cooperative single-thread Python API, not an atomic source snapshot or sandbox.

## Exact portable format

integration_tools/offline_recording_codec.py:
- encode_recording(recording: object) -> bytes revalidates the exact result type.
- decode_recording(raw: object) -> FinishedSyntheticRecordingV1 accepts exact
  bytes, nonempty and <=262144 bytes, canonical UTF-8 JSON only; duplicate keys,
  NaN, wrong shape, extra/missing fields, actual scopes or changed permission
  flags reject with RECORDER_SERIALIZATION and no partial result.
- canonical JSON uses sorted keys, compact separators, ensure_ascii=False,
  allow_nan=False and a final newline. Request words are lowercase 8-digit
  MSB-first hex. Sequences, ns timestamps and context generation uint64s use
  canonical decimal strings, not float/JSON numeric conversion. Bounded CORE4
  settings/state/counter integers remain JSON integers. Flags remain booleans.
- Decode reconstructs the exact typed carriers and revalidates; encode(decoded)
  must equal the input bytes. This is no origin authentication, raw log reader,
  production Adapter, model/F61 input or rate-policy interface.

## Demo and documentation

tools/offline_call_recorder_demo.py takes no data/path/r/period arguments and
prints one fixed newly authored synthetic two-call example to stdout. It must
work from another cwd with -I -B, reject unknown arguments and never run a model.
No filesystem publisher, controller wrapper, thread, network or auto-capture.
Document API, errors, examples, declaration-vs-capture boundary, resource bound,
single-thread/non-atomic limit and the outstanding real-observation prerequisites.
README is append-only; all old source/fixture/wheel bytes remain unchanged.

## Validation

Test real lifecycle and portable behavior with hand-authored snapshots: signed
zero 80000000, subnormal 00000001, distinct request/state values, 7/8 sequences,
exact negative ns times -9/-8 and extreme uint64/int64 tokens. Cover invalid
ordering, scope/profile, settings/state/counter links, overflow, poison/abort,
completion mismatch, immutable return/permissions, encoding tamper, duplicate
keys, invalid UTF-8/numbers/extra fields, no actual-use imports and CLI isolation.
Run RED before implementation, targeted GREEN, whole DEV gate, static checks,
compile, exact demo twice, independent whole-branch review and source/ref custody.
Tests do not prove numerical correctness, source consumption, thread safety,
latency/resource impact in a real process, authenticity or vehicle qualification.

R_BUDGET UNRESOLVED; Static Evidence Gate FAIL; actual r/T2/scale=null; actual
activation/F70UH/V/F71 NOT_ALLOWED. No push/main merge in this stage.
