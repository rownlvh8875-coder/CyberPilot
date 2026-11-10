# CORE34 — public API driver/rate boundary characterization

Builder choice under standing offline delegation. BASEaddf620d6c9c555890f186bffa0ebe38ebc20ba2.
This is regression coverage of existing behavior,not a new numerical feature or bug fix.

## Approaches and scope

Existing oracle/state tests cover representative driver/rate values and CORE30/31 have
closed rollout references. Select a test-only public step boundary matrix rather than
another wrapper/CLI (no numerical coverage gain) or changing the model (no demonstrated
defect). Add no production API or reference generator. Use native execution and one
fresh whole-branch reviewer under the existing delegation/question opt-out.

Four unittest methods exercise28 independent single-step cases through cyberlateral_dev.step.
All requests are±1.0,scale16,allowance7,factor1,multiplier3,active=true,angle0.0,
seed index1/previous_requested0/counter0. Normal UP2/DOWN5;two hold cases use0/0.
These are declared synthetic seeds,not demonstrated reachable prehistory or vehicle settings.

## Literal expectations

Ten driver cases: each sign at7-1/256,7,7+1/256 opposing torque;cap endpoint16 stays
integer-tagged,just inside the fractional envelope is4093/256 (hex1.ffap+3),then rounds
to16. Opposing12.25 yields±0.25 fractional clip/round0;12.5 clamps to integer0.
The exact zero crossing of16/3+7 is not dyadic and is not an accepted exact-boundary input.

Fourteen directional cases:previous -6,-4,-1,0,1,4,6 with each request sign.
Hand-written rate intervals respectively[-8,-1],[-6,1],[-3,2],[-2,2],[-2,3],[-1,6],[1,8].
Do not reduce asymmetric branches to a scalar/symmetric rate. Positive and negative
request saturation select each interval endpoint.

Two ordered-clip cases use previous±6 and strong opposing driver±12.5. Driver clip0
then rate interval[1,8]/[-8,-1] yields±1,not0. Two zero-step cases hold±6 after driver
clip0. Therefore do not assert final output always remains inside new driver bounds;
sequential clips are not a guaranteed intersection. This describes source-model behavior,
not a safety recommendation. State previous_applied must store final±1/±6 separately
from current request±16 and earlier driver clip0.

Tests compare exact tagged driver lower/upper/result and rate lower/upper/result,
limited/final/projected integer and next-state/request/counter fields. Quantized request
is the literal±16. Integers/bools must have exact types;float stage values use literal
hex strings. Not full-output serialization,whole quantizer,physical torque or F61 proof.

## Validation and preservation

Freeze AST-literal rows and test-file identity and commit before executing these new
cases. No expectation may be generated from target/model/oracle results. Earlier model
inspection/baselines exist,so this is not blind research or external independent approval.
Existing correct code should PASS;do not fabricate a missing-feature RED. Prove test
sensitivity with six in-memory synthetic-code mutations,then unchanged-model GREEN:
driver sign,endpoint kind,UP/DOWN swap,removed cross-zero caps,raw-request rate input,
and erroneous final driver reclip. No original source bytes are patched for mutation.
Fresh whole DEV/static/compile/frozen-wheel and two deterministic mutation/profiling
runs are required. All mutation errors must be assertion failures,not harness exceptions.

Only old README/backlog navigation may change. All runtime code,old tests,old reference
bytes,CORE32 receipts/CORE33 pins and wheel remain unchanged. New files:test,guide,spec,plan.
No install/network/merge/push/PR/CI/HF writes. Preserve worktree/old evidence/refs.
Actualr/T2/scale=null,R_BUDGET UNRESOLVED,StaticGateFAIL;actual inputs/F61/Controller/
Runtime/CAN/actualr/dt0,F70UH/V/F71 NOT_ALLOWED. Synthetic work is nonzero.
