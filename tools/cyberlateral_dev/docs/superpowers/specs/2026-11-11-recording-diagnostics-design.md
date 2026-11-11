# CORE49 — Explicit diagnostics over a finished synthetic recording

## Intent and authority

The user delegated the remaining offline development choices and asked for the next
task after CORE48 main integration. This is the author's bounded next choice, not a
new vehicle requirement or individually approved API redesign. Use existing Python
and CORE46/CORE7 contracts without changing their semantics or the recovered F61.

## Approaches and author choice

1. A small explicit function composes CORE46 full recording/input preflight and
   CORE7 declared-transition diagnostics, returning the unchanged CORE7 result.
   Selected: least new state/schema and no duplicated limiter mathematics.
2. A new receipt/result class could retain recording metadata but duplicates
   existing checks/permissions and introduces constructor/copy semantics. Deferred.
3. A file reader/CLI could accept serialized material but adds ingestion and
   resource/authority boundaries. Out of scope; no automatic file or vehicle input.

## Exact API

New `integration_tools/offline_recording_diagnostics.py` exposes:

`check_recorded_synthetic_sequence(recording: object, contexts: object) -> SyntheticSequenceCheckV1`

Each explicit call first invokes existing `preflight_recording_input(recording,
contexts)`. Only its checked recording's records and explicit contexts are passed
to existing `check_synthetic_sequence(frames, contexts)`. No receipt input, cached
approval, flag promotion, field coercion, inferred context or fallback is added.
Return the existing CORE7 result directly; its contract ID and error families stay
CORE7/CORE46. Known and unexpected dependency exceptions propagate unchanged.

## Observable behavior

- Accept exact finished CORE41 recordings (2..128 frames) and exact tuples with
  records-1 explicit CORE5 contexts. The entire recording, metadata, adjacent links,
  all contexts and model-index ordering must validate before any model step.
- Invalid late inputs must not execute a compatible prefix. Preserve CORE46
  rejection order/code and its early foreign/subclass type checks.
- A valid N-frame call executes N-1 existing synthetic model transitions. No new
  reference/oracle/model mathematics; full validation work is nonzero.
- Preserve all declared states, counters, contexts, raw binary32 words, time tokens,
  live/replay labels and original objects. No repair or computed-state rollout.
- Return every declared-transition difference in CORE7 order, including later ones
  after an early difference. MATCH does not verify the first anchor or prehistory.
- A model/dependency failure returns no success result; already performed synthetic
  work is not rolled back and a failed call is not claimed to have zero work.
- Import, constructing/preflighting a recording and reading a prior receipt do not
  invoke this API or grant execution permission. Invocation is an explicit separate
  offline operation, not permission inferred from false recording/receipt flags.
- Do not accept a CORE46 receipt instead of the original recording. Mutations
  after a prior successful preflight must be freshly rejected on each new call.

## Non-goals and delivery

No new result schema, calculator, CLI, arbitrary reader, rollout, actual capture,
Controller/Runtime/CAN/F61, actual dt/r calculation, rate/static authority or vehicle
activation. No changes to CORE3..7/41/46, public model/wheel/fixtures/CI/dependencies.
Use a new feature branch in the existing isolated checkout. This task implements,
locally commits, verifies and reviews only; push/PR/main/CI remain NOT_RUN this task.
Preserve prior evidence and host-owned worktrees. Existing main remains f3ec626d.

Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; STATIC_EVIDENCE_GATE=FAIL;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO; D2=PERFORMANCE_NOT_EVALUATED;
F19=LEGACY_UNRESOLVED; NATIVE_EXACT_REPLAY=NOT_PROVEN;
actual activation/F70UH/F70V/F71=NOT_ALLOWED.
