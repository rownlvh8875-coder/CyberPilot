# R22 — fixed synthetic single-step model consumption qualification

Baseline:8951ca46a6eeb3e16ec0a10bc3ba0edd73e7152c. User requested the proposed
next stage. Routine inline choices/feature publication remain delegated.

## Prospective scope amendment

R21 prohibited NEW model execution and only prepared data records. R22 permits
exactly ONE unchanged public0.3.0 step per accepted fixed fixture invocation.
The closed native experiment consumes FIVE preregistered inputs, independently,
not a simulation/chain or actual vehicle sequence. R21 and older modes retain
their zero-new-model-work behavior. Their historical restrictions stay accurate.
Controller/Runtime/CAN/F61, actual/log input, r/dt and deployment remain prohibited.

## Selected approach

Use a fixed literal expectation registry committed BEFORE the first R22 model
test execution, with hand derivations from exact sealed public source. A second
runtime oracle sharing the package's oracle functions would not be independent.
An unrestricted reader/model wrapper would widen the authorized input domain.
Neither is selected. The registry is small, closed, source-derived and not tuned
from observed outputs or historical feasibility/performance results.

## Preregistered derivations (no model execution used)

Authority:unchanged public wheel SHA256
3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c.
Source paths under src/cyberlateral_dev:
_r4/request_quantizer.py:11-20, _r4/oracle.py:43-84,
_r4/state_model.py:50-59, output_projection.py:12-28, api.py:9-13.
These are DEV-model semantics, not original Controller/OEM/vehicle authority.

For all five fixtures MAX16,UP2,DOWN5,ALLOW7,FACTOR1,MULTIPLIER3 are SYNTHETIC.
Driver values0,1.5,2 keep the driver interval exactly[-16,16]. Zero prior applied
gives invocation interval[-2,2]; declared prior3 gives[-2,5]. Angles0,-7.25,8
are below85, so fault condition false and counter resets to0. No timer is used.

- zero:request/product positive0; integer0; driver/rate/final0; inactive, request
  bit false; next(index1,prior request0,applied0,counter0).
- rounded_request:native request0x1.333334p-2 ×16 =0x1.333334p+2;
  nearest-even integer5; driver5, rate/final2; active request bit true;
  next(1,5,2,0);2/16=1/8 (binary32 logical word3e000000), command2 word40000000.
- signed_zero:negative zero survives input/product hex; round(-0.0) becomes
  integer0. Inactive final0, normalized +0, words00000000; next(1,0,0,0).
- resumed:request1/4 ×16 =4; driver4, rate4 within[-2,5]; final4, request true;
  next(2,4,4,0),4/16=1/4 word3e800000, command4 word40800000. Starting
  state(1,5,3,1) is a synthetic declaration, not proven prior-call history.
- smallest_subnormal:2^-149 ×16 =2^-145; nearest integer0; active final0 but
  request bit true; next(1,0,0,0). No clamp or subnormal substitution is assumed.

All projection words above are mathematical schema simulation, NOT actual Cap'n
Proto output/CAN bytes. Literal table:reference/r22_model_expected_v1.json.
Its exact byte SHA is pinned in the independent reference helper and receipts.
The first preregistration commit precedes all R22 consumer code/tests.

## Interfaces and fail-closed gates

integration_tools/fixed_model_reference.py contains no public model/quantizer/
limiter imports or calls. It verifies the fixed registry SHA, returns deep-copied
literal expected inputs and constructs a complete nested expected-output mapping
from literals. Conversion of literal hex to float is representation only; it
does not evaluate model formulas or derive expectations from actual output.

integration_tools/model_consumption.py:
consume_closed_case(case_id:str,sample:LateralInput,state:LateralState)->LateralOutput.
Require builtin registered case ID, exact public record/Limits classes and builtin
scalars, exact package version0.3.0, then FULL bit-exact input/limits/state/provenance
match to the registry. Unknown ID or any changed request/state/settings/type/zero
sign rejects BEFORE step. A registered ID alone is not authority. Call p.step ONCE,
compare complete asdict output to independent expected mapping with canonical JSON
(including original quantization hex, both clips/kinds, fault/request, both states,
projection value/hex/words/status); mismatch rejects without returning model output.
No simulate, initial_state fallback, retries, output tuning or new state chain.
Inputs remain unchanged. No actual command sink or original application import.

Codes:CONSUMPTION_CASE,CONSUMPTION_INPUT_TYPE,CONSUMPTION_INPUT_MISMATCH,
CONSUMPTION_PACKAGE_VERSION,CONSUMPTION_OUTPUT_TYPE,CONSUMPTION_OUTPUT_MISMATCH;
reference mismatch:MODEL_REFERENCE_IDENTITY. Errors are ValueError, no partial
successful result. Low-level model errors propagate and fail the experiment.

## Native integration and counts

Explicit --model-consumption is mutually exclusive with --semantic-bridge and
--owned-boundary, requires the same exact public wheel and native/schema guards.
Extend only the closed R21 demonstration's accepted path, keeping its preparation
oracle comparison. Five accepted rows each call the closed consumer once; three
domain-rejected rows never call it. Default R19/R20/R21 observation bytes unchanged.
Report actual per-worker successful model call count5; two workers=10. Relocated
two workers add10. These are sealed experiment counts, NOT aggregate unit-test/
whole-stage activity. Existing pure regression already runs model tests separately.

Success:STATUS F70UGZ_R22_FIXED_SYNTHETIC_MODEL_CONSUMPTION_PASS.
New output is synthetic DEV data only. It is not a candidate, actual actuator,
vehicle safety/performance assessment, elapsed-time/r policy or native exact replay.

## Maintained boundaries

Original trees, public0.3.0 API/wheel/lock and old frozen artifacts/default pure CI
unchanged. One NEW preregistered DEV reference file is outside the old77-file
import manifest and is independently SHA-pinned. No capnp added to pure CI.
Actual r/T2/vehicle scale=null; R_BUDGET=UNRESOLVED; Static Gate=FAIL;
SOURCE_SCHEMA_UNQUALIFIED=6000; Candidate/Runtime=NO_GO;
D2=PERFORMANCE_NOT_EVALUATED; F19=LEGACY_UNRESOLVED;
NATIVE_EXACT_REPLAY=NOT_PROVEN; actual activation/F70UH/F70V/F71=NOT_ALLOWED.
Only existing feature Draft publication allowed; no main merge or installation.
