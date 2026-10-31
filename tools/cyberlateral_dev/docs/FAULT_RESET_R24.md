# R24 — fixed synthetic fault/reset boundaries and claim validation

Baseline942ee7ff3d8534636e660cb7ebada80aa159aac6. User requested the recommended
next offline stage and delegated routine choices/inline work/feature Draft
publication. No vehicle policy, installation, activation or main merge approval.

## Approach

One96-step internally produced native/model sequence covers the89-call threshold,
two suppressed request calls, periodic counter reset/recovery, below-threshold
angle reset and inactive reset. Independent complete literals are committed before
R24 execution. Random/general inputs would broaden authority; isolated resumed
boundary states would not prove carry across the threshold. Neither is selected.
Public0.3.0 code/API/wheel/lock, older references/observations and pure CI stay
unchanged. R24 adds a separate SHA-pinned DEV reference outside the old77 files.

## Source-derived expectations, no model execution

Authority:public wheel SHA
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c;
src/cyberlateral_dev/_r4/state_model.py:50-59, _r4/oracle.py:70-75,
request_quantizer.py:11-20 and output_projection.py:12-28.
condition=abs(angle)>=85; counted=counter+1 if condition and active else0;
request=active and counted<=89; next counter=counted if counted<91 else0.
Final command is limited if active else0; it is NOT gated by steer_request.
This is model behavior, NOT permission to send a nonzero command to a vehicle.

All96 requests=0.25, driver=0, synthetic limits16/2/5/7/1/3. Integer request4,
driver bounds[-16,16]. Index0 starts explicit state(0,None,0,0).

| indices (zero-based) | angle | active | next counter | request bit | limited/final |
| --- | --- | --- | --- | --- | --- |
| 0..88 | 85 | true | index+1 | true | 2/2 first, then4/4 |
| 89 | 85 | true | 90 | false | 4/4 |
| 90 | 85 | true | 0 | false | 4/4 |
| 91 | 85 | true | 1 | true | 4/4 |
| 92 | 84.5 | true | 0 | true | 4/4 |
| 93 | 85 | false | 0 | false | 4/0 |
| 94 | 85 | true | 1 | true | 2/2 |
| 95 | 84.5 | true | 0 | true | 4/4 |

Rate bounds[-2,2] at0/94,[-2,4] at1/95,[-1,6] otherwise. All previous
applied/state values come from the preceding final output, not requested4 or
pre-inactive limited4. Native Float32 values85/84.5/0.25/0 are exact dyadics.
The new reference/r24_fault_expected_v1.json contains ALL96 literal inputs,
previous/next states, quantization, clips, flags and projection words. It is
expanded from this hand-derived table without importing/running any model or
oracle; runtime reference helpers assemble representations only, no fault math.

## Interfaces and prospective amendment

integration_tools/fault_reference.py:load_reference(),expected_input(index),
expected_output(index), strict builtin index0..95 and exact file SHA.
integration_tools/fault_consumption.py:consume_fault_step(index,sample,state)
calls unchanged public step exactly once after complete preregistered input
match, then compares complete output. Stable FAULT_INDEX/FAULT_INPUT_MISMATCH/
FAULT_OUTPUT_MISMATCH/FAULT_REFERENCE_IDENTITY; reuse existing exact-type guards.
No fallback, retry, initialization, arbitrary state, source mutation or simulation.

native_qualification/fault_demo.py:demonstrate(car) constructs/reads owned frames
within native contexts, prepares through existing bridge/independent oracle,
and carries verified output.next_state. Explicit --fault-boundaries is mutually
exclusive with all existing modes and requires the same public/native wheel,
schema/installation/RECORD/cache/origin/interpreter guards. Old modes unchanged.

Two R24 workers96 steps each=192; two relocated workers add192. These384 are
designated-worker counts, NOT whole-stage totals. R22/R23 control pairs contribute
10/8 separately; tests/reviewer/CI work is additional, not silently zero.

## Resolve R23-M1 prospectively

native_qualification/claims.py:validate_claims(decoded_json,mode)->None, no public
model/native import. Call AFTER numerical coverage but BEFORE output mkdir for
R22/R23/R24. Reject OBSERVATION_CLAIMS for missing/contradictory/wrong-type claims:

- builtin schema_version1, package_version0.3.0, exact mode scope/reference SHA;
- exact schema/native-wheel identity dict, empty forbidden_modules_loaded list;
- actual_call_custody=NOT_QUALIFIED, per-row oracle_parity exactly true;
- CC/CS payload hashes must be builtin lowercase64-hex (consistency, not authentication);
- R22 accepted custody/precision labels exact; rejected oracle code must agree;
- R23/R24 stamps exact common fixed sequence, index and entry_<index>, initial vs
  previous-verified-model state labels exact; invocation-order-only time label.

Numerical coverage/count/full input/output/adjacency checks remain mandatory.
Complete existing test doubles to mirror actual worker records; never relax claims
to preserve incomplete doubles. Old actual observation bytes are unchanged. Claim
checking is declaration consistency, NOT external byte/readback/history/OS proof.

## Gates

Success:F70UGZ_R24_FIXED_SYNTHETIC_FAULT_RESET_PASS.
No Controller/Runtime/CAN/F61/actual/log inputs/r/dt/deployment/main merge.
Projection words are mathematical schema simulation, kind strings model labels,
not native output wire/NumPy ABI. Invocation indices are NOT elapsed time.
R_BUDGET=UNRESOLVED; Static Gate=FAIL; actual r/T2/vehicle scale=null;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; activation/F70UH/F70V/F71=NOT_ALLOWED.
