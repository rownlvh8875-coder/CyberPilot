# Curvature/yaw exact three-arm native coordinator

## Purpose

This increment adds the execution coordinator above the curvature/yaw native
producer and three-arm comparison bridge. All three arm declarations and the
common comparison basis are resolved before any child worker starts.

The coordinator runs exactly:

- UPSTREAM_BASELINE x 2;
- CYBER_CURRENT x 2;
- CYBER_CANDIDATE x 2.

Each repetition starts a fresh isolated native producer. A pair must return
byte-equivalent bounded results before either repetition is admitted to the
closed-loop receipt/comparison path.

## Pre-execution gates

Before native execution the coordinator requires:

- exactly one declaration for every comparison arm;
- canonical encoded requests;
- a common frame/input identity;
- a common reset, plant, metric mask/pipeline, domain, environment and timebase;
- a frozen MetricContract and CoveragePolicy;
- a separately bound independent ReferenceEvidence bundle;
- a valid plant-calibration evidence identity.

Missing reference evidence blocks before any worker launch. Mismatched inputs or
duplicate arm declarations also block before execution.

Controller source identity, exact CarParams profile identity and producer
software identity may differ by arm. These differences are retained in the
arm-specific RunBinding rather than being silently normalized.

## Execution and comparison behavior

For each arm:

1. run two fresh isolated native producers;
2. require exact producer-result repeatability;
3. create the comparison-bound ClosedLoopBinding;
4. independently replay/admit each transcript through the public curvature/yaw
   adapter;
5. build the metric/comparison RunReceipt from explicit reference evidence.

Only after all six receipts exist does the coordinator invoke the existing
compare_receipts implementation.

The negative-control test uses the same native controller for all three arms.
All six runs are repeatable and reach the comparator, which correctly returns
FAIL / NO_PRIMARY_IMPROVEMENT. No threshold or evidence value is changed to make
an identical candidate pass.

## Authority boundary

The coordinator has no CAN, Params, CarController, profile-write, device,
network, shadow, deployment or runtime activation surface. Its result hard-codes
runtime_accepted=false, promotable=false and vehicle_activation_allowed=false.

This closes execution orchestration only. Authentic distinct arm declarations,
independent real path evidence, prospective plant calibration and uncertainty
qualification remain separate gates. Vehicle status remains
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
