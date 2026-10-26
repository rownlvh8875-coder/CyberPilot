# Declared-hypothesis approximate meter diagnostic

## Identity and purpose

IMPLEMENTED: DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1. Conditional pinhole
meter-equivalent diagnostics from frozen assisted pixel residuals. This answers
the scale/sensitivity engineering question without claiming physical lane error.
Status: CONDITIONAL_DIAGNOSTIC_COMPLETE / APPROX_METER_DIAGNOSTIC_AVAILABLE.
Baseline feature/cyber-autotune 7557e50803417fc3f0c99303d5b111d7a1a36541;
d32d5b65d ancestor, clean/local-origin equality and baseline CI SUCCESS verified.

All outputs are APPROXIMATE / CONDITIONAL / NON-QUALIFYING. No candidate/controller
evaluation, tuning, new inference, new image decode, new holdout opening, private
source crawl, model/planner/live calibration payload reads or vehicle/device write.
No external algorithm, dependencies, weights or assets added.

## Original references and input chain

Existing repository license applies. Reuse the source-bound
qcamera_pixel_registration.py conditional affine/K arithmetic, static
openpilot/common/transformations/camera.py OS04C10/mici narrow-road K, and
approximate_geometry_diagnostic.py convention adapter. Optical x-right/y-down/
z-forward maps through F * E(device_from_calib).transpose() * optical_to_device
to assumed flat road x-forward/y-left/z-up. No direct Euler sign reuse.

The prior source audit binds camera.py to native/VisionIPC1344×760, NOT raw sensor
2688×1520. Only the already-declared OS04C10 static candidate is used:
fx=fy1141.5, cx672, cy380. This is STATIC_INTRINSICS_PRIOR; per-unit/distortion/
physical applicability is unresolved. No new sensor candidate was invented.
Runtime camera-stack evidence and all original qcamera artifacts stay unchanged.

Frozen final assisted analysis + original assisted reference + original detector
rows + historical evaluation → exact receipt/public-aggregate binding checks →
unchanged observed-y assignment → recovery checked against stored matched pixel
residuals → conditional ray intersections → separate local derivatives →
numeric-only aggregate publication. Four SHA-bound JSON tables reconstruct the
exact full aggregate, preserving its receipt; this keeps every file below the
unchanged1MiB publication scanning cap.

Original manifest/image/human/prediction/analysis/evaluation binding is preserved.
No historical aggregate is re-evaluated or rewritten. Recovering the same
assignment for this derivative is checked against its stored residual sequence.
New math/executor and reused mapping/assignment/geometry helpers are source-bound;
Python/NumPy and float64 CPU execution identity are recorded. No submodule changes.

## Changes and expected effect

New declared_meter_diagnostic.py owns pure conditional geometry/quantiles.
declared_meter_evidence.py validates existing JSON receipts, saves immutable local
derivatives and publishes strict numeric aggregate tables. declared_meter_visualizer.py
adds /meter to a wrapper around the existing loopback visualizer. Existing
visualizer code/assets, detector config, matching policy and calibration admission
remain byte-identical. The new tab never opens raw inputs or serves private points.

Parameter policy is frozen BEFORE derivative execution:
- Historical height7 × pitch3 cells (21 unique poses; original84 distance rows).
- Historical roll/yaw24 probe rows collapse repeated distances/nominal duplicates
  to four additional unique poses. Their original policy receipt is bound.
- Physical observed mean1.385m adds one nominal-pose scenario:26 total.
- All three mappings at every scenario: CENTER_ALIGNED, ZERO_ORIGIN, CORNER_ALIGNED.
- User-requested fixed queries5/10/15/20/25/30m extend the distance reporting only;
  original height/pose ranges are unchanged.
- Height1.385m is physical observation with formal uncertainty PENDING.
  1.40m and1.33–1.47m remain HISTORICAL_DIAGNOSTIC_HEIGHT_SENSITIVITY_RANGE,
  never measurement uncertainty.
- Orientation0°/2.34°/0.2° remains MODEL_DERIVED_EXTRINSICS_PRIOR, with
  historical sensitivity probes only. Mount_y0 remains user declaration.
- Full1344×760 input rectangle and identity orientation are ASSUMED for every
  conditional mapping. Effective hardware crop/phase/orientation are not proven.
- Pinhole and flat road are conditional assumptions, not zero-distortion truth.

Initialization is immutable JSON input validation. Drift, stale receipt, duplicate
IDs, geometry mismatch, residual-recovery mismatch or local-output conflict fails
closed. Local writes use temp/fsync/hard-link/no-overwrite/directory-fsync.
Re-running exact bytes verifies them; changed execution uses a distinct generation.

Alternatives rejected: guessed actual mapping; one global px→m multiplier;
posthoc probe/filter/threshold optimization; distortion coefficients invented from
nothing; physical admission or sealing with these priors. Maintenance is additive;
rollback removes new modules/artifacts without touching historical evidence.

## Fixed-distance analytic result

DETECTOR_EQUIVALENT_LATERAL_DIAGNOSTIC: at each requested distance, construct a
center-road nominal query using1.385m/model pose, hold its optical ray fixed across
scenario changes, and apply EVERY frozen matched absolute x residual at that query.
Both ± signs are evaluated and the larger finite pinhole lateral difference used.
The query is synthetic; annotation points did not all occur at that distance.
Changing height/pose can move its projected forward distance away from the nominal
query distance, explicitly recorded in each row. These are observed residual
distribution percentiles under declared queries, not a population physical p95.

| Query m | Mapping hypothesis | p50 cm | p95 cm | Residual samples |
| ---: | --- | ---: | ---: | ---: |
| 5 | CENTER_ALIGNED | 2.192 | 5.715 | 2240 |
| 5 | ZERO_ORIGIN | 2.192 | 5.715 | 2240 |
| 5 | CORNER_ALIGNED | 2.194 | 5.721 | 2240 |
| 10 | CENTER_ALIGNED | 4.359 | 11.365 | 2240 |
| 10 | ZERO_ORIGIN | 4.359 | 11.365 | 2240 |
| 10 | CORNER_ALIGNED | 4.364 | 11.379 | 2240 |
| 15 | CENTER_ALIGNED | 6.526 | 17.016 | 2240 |
| 15 | ZERO_ORIGIN | 6.526 | 17.016 | 2240 |
| 15 | CORNER_ALIGNED | 6.533 | 17.036 | 2240 |
| 20 | CENTER_ALIGNED | 8.693 | 22.667 | 2240 |
| 20 | ZERO_ORIGIN | 8.693 | 22.667 | 2240 |
| 20 | CORNER_ALIGNED | 8.703 | 22.694 | 2240 |
| 25 | CENTER_ALIGNED | 10.860 | 28.318 | 2240 |
| 25 | ZERO_ORIGIN | 10.860 | 28.318 | 2240 |
| 25 | CORNER_ALIGNED | 10.873 | 28.351 | 2240 |
| 30 | CENTER_ALIGNED | 13.027 | 33.969 | 2240 |
| 30 | ZERO_ORIGIN | 13.027 | 33.969 | 2240 |
| 30 | CORNER_ALIGNED | 13.042 | 34.009 | 2240 |

| Query m | All-declared min p95 cm | Max p95 cm | Extremum scenario / mapping |
| ---: | ---: | ---: | --- |
| 5 | 5.320 | 6.270 | S02 CENTER_ALIGNED / S18 CORNER_ALIGNED |
| 10 | 10.268 | 12.890 | S02 CENTER_ALIGNED / S18 CORNER_ALIGNED |
| 15 | 14.930 | 19.970 | S02 CENTER_ALIGNED / S18 CORNER_ALIGNED |
| 20 | 19.332 | 27.560 | S02 CENTER_ALIGNED / S18 CORNER_ALIGNED |
| 25 | 23.494 | 35.719 | S02 CENTER_ALIGNED / S18 CORNER_ALIGNED |
| 30 | 27.435 | 44.511 | S02 CENTER_ALIGNED / S18 CORNER_ALIGNED |

The three mapping variants remain side by side; none is selected as actual/default
truth. For attribution only, CENTER_ALIGNED is an explicitly named contrast anchor
for one-factor height/pose comparisons. All-scenario extrema include all mappings.
Height/pitch/roll/yaw/mapping spreads are separate contrasts, NOT additive causal
uncertainty terms. Pixel p50/p95 spread is explicitly named, not p95 extrema.
Intrinsics has one fixed source candidate: its uncertainty/sampled spread stay
null, not a fabricated zero intrinsic contribution.

## Observed matched-point projection

HOLDOUT_POINT_PROJECTED_ENVELOPE: recover left3901, right3069, center2240 paired
original526×330 points from the frozen60. Each human/detector point is mapped and
its ray intersected separately. Absolute difference in projected lateral Y is
computed; this preserves height/pitch/roll and original image-y effects.

Distance bins use HUMAN projected forward position: [0,7.5), [7.5,12.5),
[12.5,17.5), [17.5,22.5), [22.5,27.5), [27.5,32.5], then restrict human distance
to5–30m. BOTH rays must intersect forward ground. The detector's own forward
coordinate is retained privately, not forced to equal human distance. Horizon/
nonforward, out-of-domain and empty groups remain unavailable/null; no clipping
or zero filling. Bin candidate/valid/unavailable counts are separate; human rays
without a forward distance cannot be assigned a distance bin and remain globally
counted. Fewer than30 point samples is a disclosure label, not a qualification
threshold. Points within a frame are correlated; point count is not frame count.

| Nominal mapping | Center p50 / p95 cm | Valid / total points | Nonforward / out of domain |
| --- | ---: | ---: | ---: |
| CENTER_ALIGNED | 3.461 / 12.620 | 2240 / 2240 | 0 / 0 |
| ZERO_ORIGIN | 3.473 / 12.692 | 2240 / 2240 | 0 / 0 |
| CORNER_ALIGNED | 3.461 / 12.621 | 2240 / 2240 | 0 / 0 |

Example CENTER_ALIGNED nominal distance bins (other hypotheses remain in JSON):

| Bin query m | Point samples | p50 cm | p95 cm | Disclosure |
| ---: | ---: | ---: | ---: | --- |
| 5 | 971 | 2.857 | 8.585 | point weighted |
| 10 | 913 | 3.615 | 10.637 | point weighted |
| 15 | 279 | 7.530 | 20.134 | point weighted |
| 20 | 66 | 4.031 | 25.798 | point weighted |
| 25 | 10 | 6.638 | 14.453 | SMALL_SAMPLE |
| 30 | 1 | 17.072 | 17.072 | SMALL_SAMPLE |

At nominal mean/pose all2240 center pairs project within5–30m for all three
mappings. Across the complete scenario grid, coverage and bucket membership can
change. The complete JSON reports every scenario, not only favorable cells.
Different per-scenario bins can contain different points, so extrema of their
percentiles are not a bound for a fixed physical population.

Frame matching remains44/55 both-visible (80%);11 unavailable centers, not zero
error. Five other frames are outside the both-visible center denominator.
Original accepted44:37/39 both-matched; modified16:7/16. The modified group's
lower matched pixel residuals do not imply better performance or hide its coverage.
Left/right missing geometry and exact historical group statistics accompany the
new aggregates. Assisted matching is not independent semantic ego association.


Nominal pinhole point projection also retains the tails:

| Side / CENTER_ALIGNED example | Valid / matched candidate points | p50 / p95 cm | Maximum cm |
| --- | ---: | ---: | ---: |
| left | 3876 / 3901 | 4.825 / 20.765 | 42.954 |
| right | 3059 / 3069 | 6.220 / 26.170 | 321.681 |
| center | 2240 / 2240 | 3.461 / 12.620 | 44.693 |

These maxima are conditional algebra, not measured meter errors. In particular
the right-side heavy tail is not removed by reporting smaller matched p95 values.
Close results among the three resize conventions do not validate hardware crop
or proprietary scaler behavior outside this non-exhaustive hypothesis set.

## Open terms and blockers

DISTORTION_CONTRIBUTION_UNBOUNDED_OR_PENDING. No coefficient evidence exists, so
distortion contribution and TOTAL_PHYSICAL_BOUND remain null. Mapping hypotheses
are not exhaustive; hardware effective crop/phase, orientation runtime confirmation,
mapping residual, intrinsics applicability, physical pose/height uncertainty,
road grade/camber/nonplanarity and assisted-annotation uncertainty remain open.

Actual forward mapping, actual Kq, pixel mapping residual bound and independent
numeric meter result remain null. Conditional K examples are labeled source prior
plus hypothetical transform, independently_calibrated=false.

New readiness copies the latest recorded-runtime blocker DAG exactly and adds a
separate diagnostic availability status. CALIBRATION_UNCERTAINTY_PENDING,
INDEPENDENT_CALIBRATION_VALIDATION_PENDING, PIXEL_GEOMETRY_REGISTRATION_PENDING,
METRIC_CALIBRATION_UNAVAILABLE and INDEPENDENT_REFERENCE_UNAVAILABLE persist.
No strict physical_projection_uncertainty.py admission gate is modified.

Supporting feasibility: existing development metadata inventory has0 native/q
pairs. Synchronized wide/narrow frame availability, pair extrinsics/baseline and
conditioning are not established; STEREO_DISTANCE_DIAGNOSTIC_UNAVAILABLE.
Raw IMU payloads/stationary intervals were not read; IMU_CAMERA_TRANSFORM_UNAVAILABLE.
No raw-camera or new-log search was performed. Optional assisted vanishing-point
crosscheck NOT_RUN; it would remain supporting assumptions, never camera truth.
These supporting tracks do not block or strengthen the main conditional result.

## Local visualization and publication

Run .venv/bin/python -m openpilot.tools.cyber_autotune.declared_meter_visualizer
and open the printed127.0.0.1 URL's /meter tab. All assets local, strict CSP/Host/
Origin checks, no telemetry/cloud/CDN. Separate fixed-distance and observed-point
views, left/right/center selectors, all mappings, scenario extrema, sample counts,
matching coverage and open terms. No private coordinates/images are served.

Full q/native coordinates, per-point projections and sample bindings are local
private derivatives only. Git contains code, hashes and aggregate numeric tables.
Public rows have exact shapes/enums/scalar statistics and no arbitrary text/paths/
IDs. The public report reconstructs its local header and checks exact publication
identity before serving. Source/asset drift rejects requests. Evidence rows are
immutable and never merged with independent calibration or sealed reference inputs.

## Regression risk and acceptance

Primary risks: sign or pixel-center error; changing historical ranges; accidental
total-bound claim; low-coverage quantiles hiding unavailable frames; private data
escaping numeric fields; source drift; treating assisted reference as blind GT.
Acceptance is structural/synthetic correctness, exact historical binding and
non-qualifying labels. No centimeter PASS/FAIL criterion exists.
Public vs private semantic targets are not treated as one accuracy benchmark.
This increment never evaluates candidate/controller differences.

## Validation method and actual results

| Check | Actual final-source result |
| --- | --- |
| Focused conditional math/evidence/snapshot/UI | 66 PASS |
| Full AutoTune + controls | 1823 + 142 = 1965 PASS |
| Focused existing lateral replay | 16 PASS |
| Privacy/authority regression | 47 PASS |
| Exact derivative repeat / immutable writes | PASS; identical aggregate receipt |
| Ruff / syntax / staged+unstaged whitespace | PASS |
| SCons -j2 | PASS |
| Publication, unchanged scanner | 781 files / 0 findings |
| Actual Chrome desktop + mobile | PASS; 3 mappings, 6 distances, 3 groups, 2 views |
| Browser external requests / JS errors / failed resources | 0 / 0 / 0 |
| Loopback server clean shutdown | PASS |
| Separate independent code review | PASS; synthetic/publication/source integrity scope |
| New push GitHub Actions | verify actual conclusion after push; local checks are not remote CI |

Machine-readable validation receipt binds final source/asset/environment, aggregate
and local validation-log hashes. The reviewer did not access private images/points
or claim to rerun the full suite. Remote CI conclusion is verified separately after
push to avoid a circular self-referential commit identity.

Synthetic tests independently verify zero-angle closed-form geometry, conventions,
subpixel/anisotropic mapping, nonforward rays, exact bins, projection denominators,
immutable writes and contamination/publication rejection. Independent reviewer
found publication shape/source-guard gaps; failing regressions were added and
fixes re-reviewed. Earlier local draft computations were development executions,
not historical evidence replacements; final versioned derivatives preserve them.
Superseded full-suite snapshots were stopped after bin-denominator and
lossless-publication-sharding improvements;
only the final-source full run is completion evidence.

Replay vs baseline:16 existing isolated replay tests; no vehicle replay reference
changed. Simulation/closed-loop/shadow/real-vehicle validation NOT_RUN/NOT_AUTHORIZED:
offline algebra and browser verification do not establish those stages.

## Handoff and vehicle status

Next: independently identify scaler/crop/phase and mapping residual; provide height
repeats/instrument/formal uncertainty and independent target/pose/road calibration.
Do not retune the detector on this frozen evaluation set. Conditional centimeter
values may inform planning scale, but no candidate decision or activation follows.

No production authority changed: no CAN, Params, CarController, process injection,
device/Jetson write or actuation. Sealed reference NOT_GENERATED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
INDEPENDENT_REFERENCE_UNAVAILABLE remains BLOCKED.
