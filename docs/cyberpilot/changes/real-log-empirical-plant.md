# Read-only real-log empirical plant identification

## Identity and purpose
Cyber Validation / AutoTune, feature/cyber-autotune, starting
a2380dd7805a967c085f8b405c496b567f9b6c32. Implementation/validation pending.
Identify only measured command-to-steering and, if its units/frame are
source-proven, steering-to-yaw response. No controller/candidate execution,
retuning, production integration, new capture or vehicle authority.

## Original references
Recording source candidate: ajouatom/openpilot,
5a970f1ad25d9f07d055955d7a7c14603b6b7813.
Trace car/card.py state_publish -> carOutput.actuatorsOutput, Hyundai
carcontroller update -> post-limit torqueOutputCan, Hyundai carstate ->
SAS11.SAS_Angle and ESP12.YAW_RATE. Exact source blobs will be bound before
numeric extraction. Existing descriptive plant and historical receipts stay
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
Each segment is modeled separately; event/rollout/history windows never cross
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
Speed regimes: 5–15, 15–25, >=25 m/s; below5 diagnostic only. Boundaries reuse
existing synthetic speed categories in round m/s; no result-based bin changes.
Rollouts: 25/50/100/200 samples (0.25/0.5/1/2 s), fully contiguous valid support.
TRAIN mask: valid finite streams, lateral active, no EPS fault, no driver
override, no unavailable limitation state. Missing safety/curvature-limit
observability blocks a clean primary mask rather than implying false.
Unknown units/frame block that stage. No automatic degrees/radians or384
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
Pending focused, full AutoTune/controls, replay, Ruff, syntax, publication,
privacy/authority, whitespace, SCons and independent review.
No UI planned. No images/video/GPS/model/path payload access authorized.
Source-only metadata inventory has 95 rlog files; numeric inspection not run.

## Handoff
Keep TA-B/SG-A tradeoff, V1/V2 verdicts, composition/search/evaluation blocks,
reference/calibration blockers, sealed reference NOT_GENERATED, vehicle
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Rollback removes only new additive experiment artifacts/code.
