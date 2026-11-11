# CORE58 — explicit diagnostics from complete canonical synthetic inputs

## Intent and author choice

CORE55 can preserve a full recording and explicit contexts as one canonical input.
A caller currently decodes it,unpacks the compatibility receipt,and calls CORE49.
Add one explicit diagnostic entry point so a caller cannot accidentally pair a
restored recording with separately chosen contexts. This is an author choice
under the user's delegated next-stage work,not a new vehicle or policy approval.

Approaches:keep the existing manual two-call pattern(no convenience bridge);
add a small in-memory bridge in the existing diagnostics module(chosen);
or add a file/CLI reader and durable result publishing(deferred,because that adds
I/O/output policy beyond this bounded API). Reuse the existing Python code and
contracts rather than introducing a new format,result type,math,or dependency.

## Interface and behavior

Add to integration_tools/offline_recording_diagnostics.py:

check_serialized_recording_input(raw:object)->SyntheticSequenceCheckV1

Decode using unchanged CORE55 decode_recording_input,then explicitly diagnose
the returned recording and contexts using unchanged CORE49
check_recorded_synthetic_sequence. Return its existing CORE7 result.
No alternate format detection,context override,inference,cache,repair,default,
rate/time/scale policy argument,or promotion of the compatibility receipt.
CORE41-only bytes,recording objects and receipts are not complete input bytes.
The existing object API and CORE52 recording-plus-separate-context API remain
unchanged. Importing this module does not itself perform diagnostics.

## Validation and execution boundaries

CORE55 remains the exact raw-type/1..1048576bytes/canonical JSON/header/inner
recording/context-wire and full CORE46 compatibility authority. Recording counts
2..128,contexts1..127,and every existing scope/type/range/dyadic/count/order/pair
rule remain unchanged. No new validation ordering or exception translation.
Structural RecordingInputCodecError and semantic RecordingPreflightError codes
propagate unchanged before model work;late invalid input executes no prefix.

On valid input run all N-1 declared adjacent transition checks. Differences are
data,not an early stop or permission to repair state. Every transition uses its
declared entry state,not computed-state rollout. Preserve exact raw binary32
words,int64 times,clock labels,auxiliary float signs/precision and every context.
Late model failure may follow nonzero completed work;existing fixed transition
errors or unexpected exception identity propagate,without partial success,retry,
raw ValueError leakage,or claims of zero work after an execution failure.

The unchanged output is CORE7_COUNTERFACTUAL_DECLARED_SEQUENCE_V1 and grants no
source authentication,first-anchor/prehistory/native replay,F61,or actual-use
permission. CORE55 codec-only work remains zero model/reference steps;this new
explicit diagnostic performs N-1 model steps. Numeric validation is nonzero and
not aggregated. Repeated bounded validation is accepted rather than redesigned.

## Delivery limits

Cooperative single-thread development-tree API,not hostile-process isolation or
atomic capture. No filesystem/vehicle/log reader,CLI,result persistence,installed
wheel API change,Controller/Runtime/CAN/F61,input capture,actualdt/r,install/deploy,
dependency,workflow,rate policy or source-schema qualification change.
Actualr/T2/scale=null,R_BUDGET unresolved,Static Gate FAIL,sourceSchema6000,
Candidate/Runtime NO_GO,D2 PERFORMANCE_NOT_EVALUATED,F19 LEGACY_UNRESOLVED,
NATIVE_EXACT_REPLAY NOT_PROVEN,actual/F70UH/F70V/F71 NOT_ALLOWED.
Local feature implementation/tests/review/evidence only. Push/PR/main/CI NOT_RUN.
