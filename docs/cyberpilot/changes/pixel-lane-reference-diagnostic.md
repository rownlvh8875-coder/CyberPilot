# Pixel lane reference diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: implementation under software verification; no vehicle qualification.
- Purpose: provide a bounded image-derived lane-midpoint reference that is
  independent of model lane/path geometry, then compare already-projected model
  lane-center and model-path x coordinates against that image reference.
- Scope: qcamera RGB pixels and scalar projected x coordinates only. There is no
  log loader, planner/controlsd hook, controller output, parameter search,
  smoothing, profile selection, Params/CAN/device write or vehicle activation.
- Branch / baseline: feature/cyber-autotune from
  f0c06bb6c84c0014625b96a60754e940a06b6838.

## Implementation

- Added openpilot/tools/cyber_autotune/pixel_lane_reference.py.
- detect_qcamera_lane_pair():
  - accepts only exact (330, 526, 3) uint8 qcamera RGB input;
  - scores lower-ROI edge/white-line evidence without model geometry;
  - searches a fixed perspective lane-pair envelope;
  - blocks blank/low-signal images rather than returning a geometry-only match;
  - returns immutable descriptive geometry and signal-quality metrics.
- compare_projection_to_pixel_reference():
  - accepts only finite scalar geometry, an in-frame pixel reference and a
    resolved nonzero turn direction;
  - reports absolute pixel errors and turn-normalized inside/outside separation;
  - is stateless and does not accept, rank or tune any candidate.
- Signal checks are detector-quality guards only. They are not vehicle safety,
  tuning, promotion or acceptance thresholds.
- Every output hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.

## TDD and regression intent

The tests are synthetic and public-safe. They cover:

- perspective-lane detection without any model input;
- caller-owned pixel immutability;
- exact frame shape/dtype enforcement;
- blank-frame fail-closed behavior;
- left/right directional projection decomposition;
- non-finite and unresolved-turn fail-closed behavior;
- frozen outputs and absence of command/tune/acceptance fields.

Private driving-log images and derived values are not copied into this repository,
are not a unit-test fixture, and are not an acceptance or promotion gate.

## Private descriptive cross-check

After the synthetic tests passed, the new module was exercised read-only against
two previously selected, independent left/right curve frames from the existing
private log set. It reproduced the prior ad-hoc pixel-reference decomposition
within floating-point rounding: in both withheld frames the projected model path
was farther from the image-derived lane midpoint than the projected model lane
center, and the model-path displacement was toward the inside of the requested
turn relative to the model lane center.

This remains descriptive evidence only. The image detector is a straight-line
lower-ROI approximation and may be affected by road-edge paint, occlusion,
shadows, perspective, lane merges or non-lane markings. The image midpoint is
more independent than model-lane-center self-comparison, but the model projection
still depends on camera calibration and the turn-normalized sign comes from the
caller's requested-curvature direction. It is not surveyed lane-center ground
truth and does not prove a causal model defect.

## Regression-gate finding and bounded fix

The first full verified-public suite run exposed one pre-existing cleanup race
under concurrent load: the kernel briefly exposed a terminated descendant with
/proc state X (dead), while the cleanup test accepted only ABSENT or Z (zombie).
The new pixel diagnostic did not call or modify that supervisor path.

A focused TDD fix was applied to the existing offline native supervisor:

- the test first added X/x as terminal synthetic states and failed against the
  previous implementation;
- native_runner now classifies Linux Z, X and x as terminal process states;
- the timeout postcondition accepts ABSENT, Z, X or x, all non-running states;
- the cleanup test passed in 10 repeated pre-fix reproductions after the original
  full-suite race, and the corrected native-runner/cleanup set passed 17/17.

This does not shorten the cleanup timeout, skip group confirmation, weaken a
vehicle safety limit, or authorize runtime use. It only prevents a kernel-dead
process state from being misclassified as running.

## Safety and authority

- No panda/opendbc safety code or actuator limit is changed.
- No real-vehicle interface is imported or called.
- No CAN, Params, profile or device write exists.
- No runtime caller is intended.
- No holdout/reserved evidence is modified.
- No parameter recommendation or vehicle activation is authorized.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED


## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 7/7 failed before implementation because the module did not exist |
| Pixel diagnostic unit tests | 7/7 PASS |
| Related pixel + virtual recenter + path observer tests | 34/34 PASS |
| Ruff / staged whitespace | PASS |
| AutoTune + controls regression | 876/876 PASS in 225.25 s |
| Native SCons build | PASS, exit 0; existing non-fatal PWD warning only |
| Default verified-public suite | 1783 passed / 42 skipped / 1 xfailed in 337.64 s |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Private two-frame read-only cross-check | reproduced prior decomposition within floating-point rounding |
| First post-publication full-suite rerun | 1782 passed / 42 skipped / 1 xfailed / 1 failed; sole failure observed kernel X(dead) cleanup state |
| Native cleanup TDD after observed race | synthetic X/x case RED before fix; corrected native runner / long runner / cleanup set 17/17 PASS; timeout cleanup repeated 10 times without failure before the focused fix |
| AutoTune + controls after cleanup-state fix | 876/876 PASS in 226.79 s |
| Native SCons build after cleanup-state fix | PASS, exit 0; existing non-fatal PWD warning only |
| Final full verified-public suite after cleanup-state fix | 1783 passed / 42 skipped / 1 xfailed / 0 failed in 327.73 s |

Review findings fixed before the full gates:

1. The exploratory detector could return a geometry-only pair on blank imagery.
   The repository implementation now blocks blank/low-signal frames.
2. Early draft tests contained private-derived numeric examples. Those values were
   replaced with synthetic-only fixtures before publication auditing.
3. The projection comparison accepted an out-of-frame pixel reference. It now
   fails closed when the image-derived center is outside the qcamera frame.

Final software review found no remaining Critical or Important issue within this
bounded offline module. This does not upgrade vehicle evidence or authorize any
runtime integration.
