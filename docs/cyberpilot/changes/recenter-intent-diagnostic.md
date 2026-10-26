# Recenter intent diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: software diagnostic only; no vehicle qualification or runtime use.
- Purpose: distinguish an already-existing lateral path offset from whether the
  observed model path reduces that absolute offset at a later, caller-selected
  station.
- Scope: immutable PathQualityInput geometry only. The diagnostic does not
  generate path geometry, curvature, controller corrections, tuning values,
  profiles, Params/CAN/device writes, or actuator commands.
- Branch / baseline: feature/cyber-autotune from
  c424fa4a395b851238c7eec60ac24b94cecfd58d.

## Motivation

Private read-only investigation checked the projection convention against the
actual qcamera scaling and onroad UI renderer. On the fixed frames that passed
the current image detector, the model-relative inside-path sign remained under
predeclared scanline changes and recorded-calibration-spread stress. A stronger
pixel-distance ordering was not invariant under every stress corner, so that
stronger claim is not used here. Source tracing also confirmed that
modelV2.position is not the direct lateral control reference:
modelV2.action.desiredCurvature is the default control target when no lateral
maneuver plan overrides it.

The same private investigation showed that current path-to-lane-center offset
and future offset must be separated explicitly. Route-wide descriptive outcomes
were roughly balanced between absolute-offset reduction and non-reduction, while
the preselected high-bias frames were less consistently reduced at farther fixed
stations. A nonzero mean bias alone therefore does not show whether the geometry
returns toward lane center. Exact private route and numeric evidence remain
outside the repository and are not acceptance data.

## Implementation

- Added openpilot/tools/cyber_autotune/recenter_intent.py.
- observe_recenter_intent():
  - reuses the existing fail-closed PathQualityInput validation;
  - compares the first observed path-to-lane-center offset with the offset at an
    exact future station already supplied by the caller;
  - reports signed and absolute offsets, absolute-offset change, retained
    absolute-offset fraction, whether the path remains on the same side, and
    whether absolute offset is mathematically reduced;
  - performs no interpolation or target-station search, avoiding hidden policy;
  - blocks invalid geometry, lane changes/maneuvers, unavailable/invalid future
    stations, non-finite upstream PathQualityObservation derivatives, and
    non-finite local derived results.
- The output is frozen and hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.
- The recentered boolean is an exact descriptive comparison only. It is not a
  performance threshold, promotion gate, or tuning objective.

## TDD and risk coverage

Synthetic public-safe tests cover:

- decreasing, increasing, and unchanged absolute offsets;
- mirrored lateral coordinate conventions;
- crossing the model lane center;
- zero starting offset without an undefined retained ratio;
- invalid geometry and lane-change/maneuver fail-closed behavior;
- invalid or unavailable target stations;
- non-finite upstream path-quality derivatives and derived ratio overflow;
- input immutability and frozen non-authoritative output.

Risks are misuse of model lane center as independent ground truth, accidental
interpolation/search policy, numerical overflow, or treating small floating
point differences as vehicle performance. The module therefore remains a
descriptive offline primitive only.

## Evidence boundary

Private route-wide and selected-window analyses are descriptive motivation, not
software test fixtures or vehicle acceptance evidence. Model lane lines and
model path share the same model source. Independent pixel references used in
the investigation are not surveyed lane-center ground truth. No private route,
image, raw log, location, or private-derived fixture is added to this change.

## Validation results

| Check | Result |
| --- | --- |
| Recenter-intent + related path/model observer tests | 21/21 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 885/885 PASS in 229.54 s |
| Native SCons build | PASS, exit 0; existing non-fatal PWD warning only |
| Default verified-public suite | 1792 passed / 42 skipped / 1 xfailed / 0 failed in 332.45 s |
| Private projection/calibration stress | model-relative inside-path sign remained on the fixed current-detector-valid frame set; stronger pixel-distance ordering not claimed |
| Private recenter comparison | route-wide absolute-offset reduction was roughly balanced; preselected high-bias frames were less consistently reduced at farther fixed stations |

Final staged source review found no remaining Critical or Important issue in
this bounded offline diagnostic. The private analyses above remain descriptive
and are not publication fixtures, promotion gates or vehicle qualification.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
