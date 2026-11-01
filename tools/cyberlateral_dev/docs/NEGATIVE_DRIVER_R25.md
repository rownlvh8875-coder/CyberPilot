# R25 — fixed negative-angle/driver interaction and active-reference receipt

Baseline cf7ee17b004911574b0628389951d794f5b74331. User requested the recommended
next offline stage and delegated routine design/inline/feature-Draft publication.
No vehicle policy, main merge, installation or deployment authority.

## Approach

One internally produced20-step native/model sequence, complete literal expected
inputs/outputs preregistered BEFORE R25 model execution. Random driver sweeps or
a generic reader would broaden authority; isolated pairs would not test state
carry across sign changes and nonzero inactive reset. Neither is selected.
Keep public0.3.0/API/wheel/lock/default pure CI/old77 and R19–R24 observations.

Authority:sealed public wheel SHA
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c;
src/cyberlateral_dev/_r4/oracle.py:43-75,state_model.py:50-59,
request_quantizer.py:11-20,output_projection.py:12-28. No model/oracle execution
is used to derive or adjust the literal table. All limits16/2/5/7/1/3 synthetic.

## Exact source-derived cases

Driver-8.5 gives driver bounds[-16,11.5]; driver+8.5 gives[-11.5,16]. The
interior bound is python.float, so both clip results are labelled numpy.float64,
even where numerically integral. Fractional result11.5/-11.5 is nearest-even
rounded to final integer12/-12 after the rate clip. Do NOT normalize labels to
integers or invent another clamp. These are source-model trace kinds, NOT live
NumPy ABI or physical safety limits.

| index | normalized request | driver | angle/active | final command |
| --- | --- | --- | --- | --- |
| 0..5 | +1 | -8.5 | -85/true | 2,4,6,8,10,12 |
| 6..13 | -1 | +8.5 | -85/true | 7,2,-2,-4,-6,-8,-10,-12 |
| 14 | -1 | +8.5 | -84.5/true | -12 |
| 15 | -1 | +8.5 | -85/true | -12 |
| 16 | -1 | +8.5 | -85/false | 0 (limited-12) |
| 17 | -1 | +8.5 | -85/true | -2 (prior final0) |
| 18 | -1 | +16 | -85/true | 0, driver bounds[0,16], integer trace |
| 19 | +1 | -16 | -85/true | 0, driver bounds[-16,0], integer trace |

All other driver bounds above are fractional; direction-sensitive rate intervals
come from previous final command, UP2/DOWN5, not previous request or pre-gate value.
Negative85 is inclusive abs(angle)>=85; negative84.5 clears the counter. Counters
are1..14,0,1,0,1,2,3. Index16 enters with counter1 and final-12, resets both to0;
index17 uses those verified zeros. Final state(20,16,0,3).
This does NOT qualify negative-angle89-call suppression, all driver values or timing.

## Interfaces

reference/r25_driver_expected_v1.json stores20 complete literal prepared inputs
and nested outputs (projection normalized float assembled from its literal hex).
integration_tools/driver_reference.py:load_reference(),expected_input(index),
expected_output(index). SHA pin, exact builtin index0..19, fresh data; no model
or numerical oracle imports/calls. driver_consumption.consume_driver_step(index,
sample,state) runs ONE unchanged step after full exact input match, then full
recursive output comparison. DRIVER_INDEX/DRIVER_INPUT_MISMATCH/
DRIVER_OUTPUT_MISMATCH/DRIVER_REFERENCE_IDENTITY; no fallback/retry/initialization.

native_qualification/driver_demo.py closed20 frames, same semantic bridge/oracle,
actual verified model-state carry, owned-context scalar reads. --driver-boundaries
is exclusive with all old modes and requires same exact native/public wheel,
schema/runtime/installed-RECORD/cache/origin guards. Claims profile R25 scope:
TWENTY_FIXED_SYNTHETIC_NEGATIVE_ANGLE_DRIVER_STEPS_NOT_ACTUAL_HISTORY;
sequence R25_FIXED_DRIVER_CONTEXT, exact index/entry labels and reference SHA.
Coverage requires ordered20 complete records/count1 and state adjacency before
publication. Old modes retain their observation bytes and closed scope.

## Repair discovered R24 metadata drift

Sealed R24 ZIPec57d39799174f6cb9c04f797faa4c7753dbe97ec4908f90f96db2075088c052
contains correct v2 observation reference dfb150fc... but SUMMARY points to v1
7d0d6ab... because run.py hardcoded a stale path. No numerical result/reference
consumer is wrong. Preserve the old ZIP, publish a correction receipt in R25.
For every numerical mode derive summary model_reference_sha256 from the already
fully numerical/claims-validated observation, not a duplicate file-path branch.
Regression test must show R24 mismatch RED before repair, then equality PASS for
R22/R23/R24 and new R25. No source API change or historical evidence rewrite.

## Execution/gates

R25 two workers20 each=40; relocated pair adds40. Designated80 excludes R22/R23/
R24 controls216 and unit/reviewer/CI work. Do not claim aggregate or zero model work.
Success:F70UGZ_R25_FIXED_SYNTHETIC_NEGATIVE_DRIVER_PASS.
No Controller/Runtime/CAN/F61/actual/log input/r/dt/deployment/main merge.
R_BUDGET=UNRESOLVED; Static Gate=FAIL; r/T2/scale=null;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; activation/F70UH/F70V/F71=NOT_ALLOWED.
