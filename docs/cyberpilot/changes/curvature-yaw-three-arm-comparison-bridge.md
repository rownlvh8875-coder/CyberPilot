# Curvature/yaw native three-arm comparison bridge

## Purpose

The native curvature/yaw producer is now connected to the existing frozen
three-arm comparison types without inventing independent lane truth. Native
controller/plant outputs provide only measurements they actually own; desired
path, lane-center offset, lane-edge margin, phase labels and corpus coverage must
arrive as a separate immutable reference-evidence bundle.

This is plumbing for offline evaluation. It is not a candidate acceptance,
vehicle qualification, shadow permission or profile activation path.

## Binding model

The bridge maps an isolated native result into RunBinding as follows:

- producer identity -> software identity;
- exact CarParams SHA-256 -> profile identity;
- native controller identity -> configuration identity;
- public transcript adapter / curvature-yaw plant source hashes -> adapter/plant;
- frame, reset, domain, environment and timebase hashes -> common comparison basis;
- frozen metric pipeline and mask hashes -> metric comparison basis.

The common MetricContract.reference_evidence_sha256 must equal the canonical
digest of the separate reference evidence. Reference source hashes for lane
center and lane edge must differ from the desired-path source and from the
closed-loop trace identity.

## Metric assembly

Closed-loop owned values:

- actual path observer (pose_y_m);
- requested/actual curvature;
- requested and delayed applied normalized torque;
- driver intervention state.

Native producer observations:

- feedback steering angle;
- desired steering angle from the same native VehicleModel;
- native torque-controller saturation state.

External mandatory reference evidence:

- desired path offset;
- independent lane-center offset;
- independent lane-edge margin;
- frozen curve-phase labels;
- all frozen coverage strata and coverage-review identity.

If those references are absent, malformed, insufficient, dependent on the
closed-loop trace, or not bound to the metric contract, the bridge raises a
fail-closed error before creating a comparison RunReceipt.

## Current qualification status

The end-to-end test deliberately feeds the same controller/result into all three
arms. Six repeatable receipts reach compare_receipts; the comparator correctly
returns FAIL / NO_PRIMARY_IMPROVEMENT. This proves pipeline connectivity only.
It does not create or imply an improved candidate.

Real independent path evidence, prospective plant calibration, uncertainty
qualification and authentic three-arm controller/profile declarations remain
mandatory before any performance conclusion. Vehicle status remains
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

## Validation results

| Check | Result |
| --- | --- |
| New bridge tests | 4/4 PASS |
| Bridge + native + plant + comparator focused regression | 74/74 PASS |
| Ruff changed Python files | PASS |
| git diff --check | PASS |
| Publication/privacy audit | 345 changed files / 0 findings |
| New-code authority-path search | no Params/sendcan/CarController/socket/HTTP/vehicle-write call sites |
| AutoTune package regression | 849/849 PASS in 373.65 s |
| Vehicle qualification | NOT RUN / NOT AUTHORIZED |

The six-receipt end-to-end fixture uses an identical native controller in all
three arms and therefore reaches the frozen comparator as repeatable but is
rejected with NO_PRIMARY_IMPROVEMENT. This is the expected negative control.