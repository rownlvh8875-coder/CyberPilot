# Read-only real-log empirical plant identification

## Identity and purpose
Cyber Validation / AutoTune, feature/cyber-autotune, starting
a2380dd7805a967c085f8b405c496b567f9b6c32. Read-only actuator-only experiment completed; regression validation recorded below.
Identify only measured command-to-steering and, if its units/frame are
source-proven, steering-to-yaw response. No controller/candidate execution,
retuning, production integration, new capture or vehicle authority.

## Original references
Recording source candidate: ajouatom/openpilot,
5a970f1ad25d9f07d055955d7a7c14603b6b7813.
Trace car/card.py state_publish -> carOutput.actuatorsOutput, Hyundai
carcontroller update -> post-limit torqueOutputCan, Hyundai carstate ->
SAS11.SAS_Angle and ESP12.YAW_RATE. The ten exact schema, Hyundai, DBC and publish-path source blobs are bound in
real-log-signal-source-v1.json before numeric extraction. Existing descriptive plant and historical receipts stay
immutable. Reuse NumPy linear algebra and pycapnp/zstandard; no new dependency.

## Design and alternatives
Use separate extraction, model fitting/evaluation and publication contracts.
Prefer a small first-order delayed ARX and causal FIR comparison; reject neural
or unconstrained high-order models. Coefficients/traces remain private.

Metadata finds one route and 95 numeric segment files. Freeze ten-segment
temporal blocks before numeric inspection. Reserve first/last segment in every
block as embargo; all middle segments have one role. Hash-sort whole blocks
and allocate 60/20/20 by block count (floor TRAIN, floor DEVELOPMENT,
remainder HOLDOUT). No immediately adjacent included segment crosses roles.
This is a time-block holdout within one route, NOT route-independent evidence.
Segment-local histories remain separate; coefficients pool TRAIN support.
Event/rollout/history windows never cross
segment, mask or gap boundaries. Unusable or heterogeneous segments keep their
frozen role and explicit disposition; no replacement.

## Execution plan and constants
1. Freeze inventory, split, source/field policy and model family grid.
2. Audit only initData/CarParams metadata and envelope counts for every split.
3. Extract only TRAIN/DEVELOPMENT numeric whitelisted fields, source verified.
4. Align at 100 Hz using latest-past sample, maximum age two source periods;
   no future value, interpolation across gaps or duplicate timestamp ambiguity.
5. Fit TRAIN coefficients; choose on DEVELOPMENT only. Freeze one model and
   exact source/config/model SHA, then open HOLDOUT once and evaluate twice
   against the same immutable extracted receipt for repeatability.
6. Publish only aggregate counts/statistics and opaque SHA receipts.

Model candidates: first-order ARX with one input tap and FIR with 25 causal
input taps; delays 0/5/10/20 samples; eight configurations maximum per stage
and speed regime. Fixed NumPy least-squares backend, single BLAS thread,
no RNG. Stable first-order pole magnitude <1 is a mathematical admission
condition, not a performance threshold. Select smallest development RMSE;
ties use lower parameter count, then family/delay lexical order.
Speed regimes: 5–15, 15–25, >=25 m/s; below 5 excluded from fit/evaluation and
counted separately. These predeclared round-m/s regimes are diagnostic
categories, not fitted or admission thresholds; no result-based bin changes.
Rollouts: 25/50/100/200 samples (0.25/0.5/1/2 s), fully contiguous valid support.
TRAIN mask: valid finite streams, lateral active, no EPS fault, no driver
override, no unavailable limitation state. Missing safety/curvature-limit
observability blocks a clean primary mask rather than implying false.
Unknown units/frame block that stage. No automatic degrees/radians or 384
normalization based on signal magnitude.

## Regression risk and acceptance
Closed-loop identification is biased by feedback, road/driver disturbances
and limited excitation. Report rank/conditioning and residual correlations.
No fitted model is independent dynamics truth. Diagnostic READY additionally
requires stable repeatable fit and holdout primary metrics better than all
declared naive references with adequate disclosed support. Failure or absent
signals produce partial/unavailable states; no holdout-driven reselection.
No TA-B/SG-A counterfactual execution in this increment.

## Validation method and actual results
The official frozen run and immutable resume produced identical extraction,
coefficients, predictions, metrics and receipt identities. TRAIN/DEVELOPMENT
raw extraction was independently repeated twice per segment. HOLDOUT raw
payload was parsed once after model freeze; the immutable aligned cache was
evaluated twice. Resume checks source hashes and source/policy/model bindings
and never changes selection. No UI was added; browser validation is not
applicable. No image/video/GPS/model/path payload was opened.

Focused 94 tests PASS. Full regression, publication and independent review
final counts are recorded in the final validation section below.

## Source/provenance findings
All 94 complete metadata segments record clean software
5a970f1ad25d9f07d055955d7a7c14603b6b7813, OS19.8-carrot-bt1 and one
CarParams generation, HYUNDAI_SANTA_FE_2022, legacy torque control. The last
segment is truncated and rejected in full; it was already EMBARGO. No parsed
prefix or replacement segment was used. Source inventory had 95 numeric logs
and 191 video files. Videos received file metadata inventory only.

[Recorded native publish path](https://github.com/ajouatom/openpilot/blob/5a970f1ad25d9f07d055955d7a7c14603b6b7813/openpilot/selfdrive/car/card.py)
publishes carOutput.actuatorsOutput from the returned CarController actuator
output. [Hyundai controller](https://github.com/ajouatom/openpilot/blob/5a970f1ad25d9f07d055955d7a7c14603b6b7813/opendbc_repo/opendbc/car/hyundai/carcontroller.py)
returns post-controller rate/driver/fault-limited raw torqueOutputCan. This is
a logged post-controller command, not EPS acknowledgement or proof that panda
transmitted every command. ANGLE_CONTROL and CANFD profiles are rejected by
the extractor because their command/sign paths differ. No 384 normalization
is applied to this raw CAN input.

[Hyundai measured state](https://github.com/ajouatom/openpilot/blob/5a970f1ad25d9f07d055955d7a7c14603b6b7813/opendbc_repo/opendbc/car/hyundai/carstate.py)
reads SAS11.SAS_Angle with
[DBC degree units](https://github.com/ajouatom/openpilot/blob/5a970f1ad25d9f07d055955d7a7c14603b6b7813/opendbc_repo/opendbc/dbc/hyundai_kia_generic.dbc).
The same source copies ESP12.YAW_RATE without conversion, while its DBC unit
is empty. Signal magnitude/schema naming is insufficient to choose radians
or degrees. Yaw/curvature model fitting is blocked. No independently calibrated
IMU-to-vehicle transform was admitted. The result is TIER_B only.

The 100 Hz integer grid uses actual event publish timestamps. Commands and
control context must precede the selected measured-state event, not merely
the later grid instant. Repeated output events, old samples and source gaps
break all 45-sample model history/rollout support. Duplicate/regressing source
times reject extraction. Sensor acquisition-to-publish age remains unverified.
The selected lag includes publish/alignment age and is not independently
measured physical actuator dead time.

Safety/curvature-limit flags are not proven observable in this extraction.
Their values remain null; clean-primary coverage is zero. Active/no-driver/
no-fault/forward/finite samples form a disclosed diagnostic mask only.
Excluded counts are nonexclusive; no difficult segment was reselected.

## Frozen selection and coverage
Split stayed 43 TRAIN /16 DEVELOPMENT /16 HOLDOUT /20 EMBARGO. All 75 active
segments extracted successfully. Segment-local history, mask and speed-bin
boundaries are never crossed. There is one route, so this is a temporal block
holdout, not independent route generalization.

| Split | Grid samples | Diagnostic valid | Unavailable | LOW valid | MEDIUM valid |
| --- | ---: | ---: | ---: | ---: | ---: |
| TRAIN |257947|82730|175217|65319|17411|
| DEVELOPMENT |95990|42103|53887|40364|1739|
| HOLDOUT |95987|30898|65089|30883|15|

HIGH has no supported samples. Common contiguous 45-sample LOW design support
is 26029 TRAIN /9915 DEVELOPMENT /25755 HOLDOUT. The eight predeclared configs
were fitted on TRAIN; DEVELOPMENT selected ARX1 with 10 samples of delay
(0.10s publish-time empirical lag). MEDIUM has fitted TRAIN models but only 192 common DEVELOPMENT samples, below 201; it lacks
minimum common DEVELOPMENT support; HIGH lacks TRAIN support. Neither is
merged, retuned or replaced. Coefficients and per-segment predictions/residuals
remain local/private. Their model SHA and aggregate dispositions are public.

## Untouched holdout findings
Errors below are steering-wheel angle degrees, not yaw, curvature, lane error
or pose error. Rollouts use observed exogenous command over the horizon;
they are conditional forecasts and not controller counterfactuals.

| Query | Support | Model RMSE deg | Hold-last RMSE deg | Model p95 deg | Hold-last p95 deg |
| --- | ---: | ---: | ---: | ---: | ---: |
| One-step |25755|0.060584|0.063113|0.106466|0.100000|
|0.25s endpoint|23249|0.709842|0.824270|0.915261|1.200000|
|0.50s endpoint|20799|1.016792|1.265099|1.556078|2.400000|
|1.00s endpoint|16653|1.606468|2.176954|2.973947|4.000000|
|2.00s endpoint|10668|2.408163|3.483395|5.329972|6.400000|

One-step model MAE 0.027189 deg is worse than hold-last 0.020427 deg, as is p95,
despite lower RMSE. At 1s endpoint model MAE 0.931499 deg, p95 2.973947 deg,
and bias -0.275513 deg are reported separately. At 2s bias is -0.448836 deg.
The declared strict better-than-each-naive primary rule is NOT satisfied.
empirical-plant-validation-gates-v1.json records every predeclared directional
comparison separately; no weighted score or new threshold is introduced.
No post-holdout reselection took place. No performance READY claim is made.
All zero-response, hold-last and TRAIN static-gain results use identical
support and are included in empirical-plant-holdout-validation-v1.json.

Residual lag 1 autocorrelation is 0.107327 (25649 pairs), past-input correlation
-0.047195 and past-output correlation 0.040037. Twenty lags, their support,
TRAIN-frozen command-amplitude quartiles, command-sign subsets and four
segment-index blocks are disclosed in the aggregate receipt. OLS on closed-loop
logs remains confounded by controller feedback, driver/road disturbances,
limited excitation and output quantization. Positive/negative command groups
are source CAN signs; physical left/right calibration is not inferred.
Stable first-order pole and finite conditional rollouts are mathematical
checks, not proof of real vehicle dynamics or arbitrary-input stability.

## Descriptive comparison and readiness
EMPIRICAL_ACTUATOR_MODEL_ONLY. Full yaw/curvature plant remains blocked on
measured units/frame and clean limit-mask provenance. The current descriptive
plant maps normalized torque to curvature/yaw/pose; this model maps logged raw
CAN command to measured steering degrees. Physical gain, time constant,
saturation and rollout comparisons across those bases are UNCOMPARABLE;
no invented 384 conversion, steering ratio or yaw units bridge the gap.
Existing descriptive, TA-B and SG-A results were not recomputed.
No TA/SG empirical-plant counterfactual, new candidate, ranking or tuning ran.

## Final validation
Final fixed-source full suite PASS: 2605 tests (AutoTune 2463, controls 142)
in 907.39s. Focused empirical tests: 94 PASS. Lateral replay: 16 PASS.
Publication check: 941 files, zero findings. No browser UI was added.
The first full run had 2588 passes and one existing synthetic worker
WORKER_FAILED result while new source files were still being added. Its worker
boundary suppresses the detailed exception, so the original cause is not
claimed proven. The identical test passed in isolated stable-source replay.
A controlled mismatched source-binding request reproduced the same fail-closed
WORKER_FAILED boundary without changing any production/source file. No timeout,
test threshold, historical worker or candidate evidence was changed.
SCons PASS; Ruff PASS; syntax PASS; lateral replay 16 PASS.
Independent review PASS; focused privacy/authority and exact publication pins PASS.
Historical evidence is unchanged; all new traces/models are outside Git.
empirical_plant_publication.py pins all twelve public receipts and the four
frozen executor source hashes. Re-sealed numeric changes, policy drift and
unknown publication members are rejected. The gates derivative is reproducible
from immutable aggregate results without opening private data or fitting again.


## Reproduction and resume
The public API includes empirical_plant_inventory for fresh metadata-only
bootstrap and empirical_plant_run for guarded extraction/fitting/evaluation.
Both accept explicit private-store and recorded-source arguments; bootstrap
additionally requires private-root. Operator paths never enter public evidence.
For the already completed generation, resume empirical_plant_run against its
existing immutable private store; do not rerun bootstrap into it. A changed
reader/policy/source requires a separate generation and cannot overwrite the
original receipts. The reusable bootstrap was synthetic-tested after the
official metadata audit and was not used to reopen any source in this run.

## Handoff
Keep TA-B/SG-A tradeoff, V1/V2 verdicts, composition/search/evaluation blocks,
reference/calibration blockers, sealed reference NOT_GENERATED, vehicle
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Rollback removes only new additive experiment artifacts/code.
