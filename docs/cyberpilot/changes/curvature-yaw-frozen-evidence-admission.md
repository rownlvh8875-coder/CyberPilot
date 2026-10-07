# Frozen three-arm and independent reference-evidence admission

## Purpose

This increment adds the pre-execution evidence gate above the curvature/yaw
three-arm coordinator. It does not provide real independent path data itself.
Instead, it defines the only accepted path by which such evidence may enter the
offline comparison pipeline.

Vehicle status remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED

## Distinct arm manifest

Before any native worker starts, each declared arm is reduced to immutable
identity fields:

- canonical request SHA-256;
- producer/software SHA-256;
- exact CarParams/profile SHA-256;
- controller/configuration SHA-256;
- source HEAD and opendbc HEAD.

The three declarations must cover exactly UPSTREAM_BASELINE, CYBER_CURRENT and
CYBER_CANDIDATE. With the frozen evidence contract's distinct-arm requirement
enabled, all three request digests and all three controller/configuration
identities must differ. Renaming one identical request three times is rejected
before reference evidence is opened or a child worker is launched.

The complete declaration manifest is SHA-256 bound by the frozen evidence
contract.

## Sealed reference file

Independent reference evidence is supplied as one predeclared regular JSON file.
The grant binds:

- absolute root plus relative path;
- exact byte count;
- exact file SHA-256;
- semantic reference-evidence SHA-256;
- reference manifest SHA-256;
- frozen review SHA-256;
- independent-reference role.

The file is opened with no-follow semantics, copied once to a Linux memfd,
rechecked for identity/size/hash changes, sealed against write/grow/shrink and
only then parsed. Symlinks, size drift, hash drift, duplicate JSON keys,
non-finite JSON, provenance conflicts and candidate-output leakage claims fail
closed.

The admission receipt explicitly carries no runtime, promotion or vehicle
authority.

## Path/lane geometry correction

The prior bridge accepted a precomputed lane-center offset and lane-edge margin
as common reference values. Because those values were identical across arms,
the existing comparator's primary lane-center metric could never improve even
when the closed-loop plant trajectory changed.

The evidence semantics are now corrected. External evidence supplies independent
road geometry:

- desired path lateral offset;
- lane-center path lateral offset;
- left lane-edge lateral offset;
- right lane-edge lateral offset;
- reviewed vehicle half-width plus vehicle-geometry identity.

For every arm, the metric bridge derives:

lane_center_offset = closed_loop_pose_y - independent_lane_center

lane_edge_margin =
  min(closed_loop_pose_y - left_edge, right_edge - closed_loop_pose_y)
  - vehicle_half_width

Thus the road/lane reference remains common and independent, while the measured
lane-center error and edge margin correctly change with each arm's simulated
trajectory. The bridge still rejects invalid lane geometry or reference evidence
whose declared source identities conflict with closed-loop trace identity.

## Frozen evidence coordinator

The frozen coordinator requires all of the following before the six native runs:

1. declaration-manifest digest match;
2. distinct arm identities;
3. reference grant values matching the frozen evidence contract;
4. MetricContract reference digest match;
5. coverage-review digest match;
6. successfully sealed and parsed reference evidence.

Only then is the existing exact 3-arm x 2-repeat coordinator invoked. All later
structural admission, repeatability and comparison gates remain unchanged.

Synthetic tests verify the plumbing only. They do not establish that any real
lane/path source is independent, accurate, prospective or suitable for vehicle
qualification.

## Validation boundary

The new end-to-end fixture uses three different valid CarParams/controller
identities and a sealed synthetic reference file. All six native executions
complete and produce comparison receipts. The derived lane-center RMSE differs
between arms, demonstrating that the corrected primary metric is now sensitive
to arm-specific closed-loop behavior.

No real evidence is bundled, no candidate is approved, and no vehicle/CAN path,
Params write, CarController call, profile activation, shadow promotion or safety
limit change is introduced.

## Validation results

| Check | Result |
| --- | --- |
| Frozen reference / distinct-arm evidence tests | 7/7 PASS |
| Related curvature/yaw + comparison focused regression | 48/48 PASS |
| AutoTune package regression | 860/860 PASS in 382.19 s |
| Ruff / Python syntax / git diff check | PASS |
| Publication/privacy audit | 352 changed files / 0 findings |
| New-code authority-path search | no Params/sendcan/CarController/socket/HTTP/vehicle-write call sites |
| Native SCons build | PASS to 100% after adding .venv/bin to PATH; existing non-fatal PWD warning only |

The first SCons invocation lacked the virtual-environment tool path and therefore
could not find cythonize/capnpc. Re-running the same build with the repository
.venv/bin prepended to PATH completed successfully; this was an environment/path
issue, not a source-build failure.
