# R23 — fixed synthetic native-to-model sequence

Baseline:f36749534e3937d4c0781804089f82a25c51f0fc. User requested next recommended
stage and previously delegated routine design/inline implementation/feature Draft
publication. These choices are the executor's, not vehicle-policy approval.

## Approach and scope

Use ONE four-step internally constructed synthetic native sequence, the existing
R21 semantic bridge/oracle preparation, unchanged public0.3.0 step and complete
preregistered literal comparisons. An arbitrary log/message reader would broaden
custody/lifetime/input authority; independent single steps would not test state
carry. Neither alternative fits this stage. No actual native history is claimed.

R22's historical single-step scope stays unchanged. R23 prospectively allows
four adjacent synthetic invocations with actual preceding model output state
carried forward inside the closed producer. Each step's full input/state must
match its own new SHA-pinned literal; each full output must match source-derived
expectations. The closed per-step helper does not authenticate history if called
separately with an equivalent declared state. Only the producer demonstrates carry.
No automatic initialization, retries, simulation or R22 fixture modification.

## Preregistration and exact derivation

Authority:unchanged public wheel SHA
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c;
src/cyberlateral_dev/_r4/request_quantizer.py:11-20,
_r4/oracle.py:43-84, _r4/state_model.py:50-59,
output_projection.py:12-28. New literal table is
reference/r23_sequence_expected_v1.json, committed before any R23 model execution.
Never replace expectations using observed results. All limits are synthetic:
MAX16, UP2, DOWN5, ALLOW7, FACTOR1, MULTIPLIER3; driver/angle positive0.
Angles are below85; fault condition false, counter0 throughout.

| index | native request | active | previous applied | integer request | invocation interval | limited | final | next previous request/applied |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Float32-promoted0.3 | true | 0 | 5 | [-2,2] | 2 | 2 | 5/2 |
| 1 | -0.25 | true | 2 | -4 | [-2,4] | -2 | -2 | -4/-2 |
| 2 | 0.25 | false | -2 | 4 | [-4,2] | 2 | 0 | 4/0 |
| 3 | 0.25 | true | 0 | 4 | [-2,2] | 2 | 2 | 4/2 |

For previous>0, bounds=max(previous-DOWN,-UP), previous+UP;
otherwise previous-UP, min(previous+DOWN,UP). Driver bounds[-16,16].
The third call's limiter result2 is retained in trace but inactive final0 is the
state carried into the fourth call; neither previous request4 nor pre-gate2 may
replace it. Negative final-2 projects to normalized-1/8, logical wordbe000000
and integer-command wordc0000000. Positive2 words3e000000/40000000; final0 words0.
Words are mathematical schema simulation, NOT native output/CAN wire evidence.
Trace kind labels are model labels, not a live NumPy ABI observation.

## Interfaces

integration_tools/sequence_reference.py:load_reference()->dict,
expected_input(index:int)->dict, expected_output(index:int)->dict. Stdlib and
representation-only assembly; no model/arithmetic calls. Return fresh data.

integration_tools/sequence_consumption.py:
consume_fixed_step(index:int,sample:LateralInput,state:LateralState)->LateralOutput.
Reject non-builtin/out-of-range index (SEQUENCE_INDEX), changed complete input
(SEQUENCE_INPUT_MISMATCH), changed complete output (SEQUENCE_OUTPUT_MISMATCH),
wrong package version; reuse R22 exact-class/type/recursive-output checks.
Reference identity mismatch is SEQUENCE_REFERENCE_IDENTITY. One step after input
match; output failure propagates, no successful artifact or fallback.

native_qualification/sequence_demo.py:demonstrate(car)->dict. Closed four native
frames with common sequence ID and indices0..3. Native scalar reads within owned
contexts, bridge/oracle exact preparation comparison, literal initial state data,
then previous verified output.next_state carried to next frame. Emit all prepared
inputs, outputs, per-row model_steps1 and prior-binding labels. No external input.

native_qualification/coverage.py:validate_coverage(observations:dict,mode:str)->int.
For R22 require exact five accepted/three rejected IDs, builtin bool acceptance,
builtin int0/1 row counts, no output on rejected rows, exact rejection codes,
top-level count5 and expected-match flags. For R23 require exact ordered indices
0..3, four accepted rows/count1, complete expected inputs/outputs, adjacent state
equality and top-level4. Reject missing/duplicate/extra/reordered rows, bool-as-int,
false match flags/counts as OBSERVATION_COVERAGE before creating output directory.
No native or public model import in parent coverage validation. Summary derives
counts from validated workers; R22 M1 fixed prospectively, old observations unchanged.

## Native mode and evidence

Explicit --model-sequence, mutually exclusive with owned/semantic/consumption
modes. Requires same exact public wheel/native wheel/schema, installed payload,
RECORD/cache/import-origin/interpreter guards. Default modes/observations unchanged.
Two workers:4 steps each,8 combined; relocated two workers add8. Counts cover
those processes ONLY, not unit/reviewer/CI/full-stage activity. New reference stays
outside old77-file frozen manifest and has separate SHA pin. Public0.3.0/API/
wheel/lock/default pure workflow unchanged. Native GitHub CI NOT_RUN.

Success: F70UGZ_R23_FIXED_SYNTHETIC_NATIVE_SEQUENCE_PASS.
No Controller/Runtime/CAN/F61/actual/log inputs/r/dt/deployment/main merge.
R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/vehicle scale=null;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; activation/F70UH/F70V/F71=NOT_ALLOWED.
