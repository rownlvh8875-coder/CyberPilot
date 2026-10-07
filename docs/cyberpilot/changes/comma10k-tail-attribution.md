# comma10k directional tail attribution

## Identity and purpose

IMPLEMENTED / DIAGNOSTIC PUBLIC GT. Baseline feature/cyber-autotune 41cfd0c1f.
Explain the retained CLRerNet 608.405860 px pred-to-marking p95, without detector
tuning, outlier removal, acceptance changes or private data. Pixel marking
diagnostics apply to these public images only; no ego-lane or meter truth.

## Original references

- comma10k MIT, commit6c205fe4c43cc53b2b1befafb1060d0606555027:
  [category definitions](https://github.com/commaai/comma10k/blob/6c205fe4c43cc53b2b1befafb1060d0606555027/README.md).
  All visible paint, not ego boundary identity; segmentation can have multiple
  disconnected dashes of one physical lane.
- CLRerNet Apache2, dae038f67da57e292e5293a68c9c1c2922de13c2, official non-EMA
  CULane DLA34 weight/config/environment retained byte-for-byte. See prior
  public-lane-detector-execution.md and environment record.
- [CULane annotation semantics](https://xingangpan.github.io/projects/CULane.html)
  include context-inferred occluded/unseen portions of four selected markings.
  That target differs from comma10k visible-paint segmentation.
- Legacy lane_marking_metrics.py / lane_detector_runner.py / lane_public_protocol.py
  and published original result unchanged. No submodule or production edits.

Call path: immutable public manifest/pinned bytes → official BGR detector
pipeline → normalized Lane spline → original-row samples → legacy row-run
midpoints → additional spatial/component/semantic diagnostics → metadata ledger.

## Changes and expected effect

New offline-only lane_tail_diagnostics.py, lane_tail_capture.py,
lane_secondary_capture.py, lane_tail_report.py, lane_public_batch.py.
No production import, Params, CAN, CarController, profile mutation, network
acquisition, temporal fill, ensemble or reference serializer.

Legacy metric: for each predicted (x,y), nearest marking-run midpoint on SAME
integer row; empty rows are unavailable, never distance0. Opposite direction
uses each GT run midpoint to nearest prediction on that row. No prediction
rasterization/thickness. GT thickness affects midpoint and exact-cell support.
Duplicate/nonfinite/outside coordinates reject in the kernel; the retained
adapter individually excludes/counts valid off-canvas spline samples, not entire
frames. No clipping or fallback.

Spatial counterfactual: Euclidean nearest GT row-run midpoint across rows.
Both all-point and EXACT legacy supported-row sample populations are reported.
This does not replace the directional distribution. Symmetric distribution is
pooled directional samples, not balanced F1. Normalization is original width,
not meter conversion. The analytic adapter roundtrip describes normalized
geometry coordinates; it does not invert intensity resampling or establish
calibration/FOV agreement. Additional sampling test covers actual adapter
crop-validity and original resolution1164x874 /1928x1208.

8-connected painted components and per-predicted-lane support form a
many-to-many graph with exact mask pixel-cell overlap. No Hungarian ego matching,
new distance tolerance, component-to-physical-lane identity, or interpolation.
Unmatched means NO EXACT PAINT SUPPORT; a small offset may lack support, and
continuous unpainted lane portions can do so. These are not official F1.

Fixed thirds, confidence edges0,.2,.4,.6,.8,1, width-quarter diagnostic tail and
width-.05 spatial sensitivity bin are in comma10k-tail-policy.json, frozen before
these added calculations. They are geometry bins, not qualification thresholds.
The historical p95 cut is read from its immutable sealed published receipt.
All samples, including car/occlusion/remote components, remain in the old metrics.
Spatial pair cap25million bounds diagnostic computation; exceeding it fails
explicitly, never silently improves a distribution.

Config/source/weight/environment unchanged. Scores and per-lane points were not
retained historically: actual inference was rerun twice and the exact union,
geometry, sampling counters and count matched the original frozen artifact.
Raw score validation precedes empty-lane exclusion; historical union proof
requires exact schema and published prediction digest. Receipts bind sources,
policy, artifacts and inputs. Self-hashes establish consistency, not accuracy.

Detector physical delay/state not applicable. Source-native secondary dtype
mutation is separately recorded below; no controller delay/state is touched.

## Regression risk and acceptance

Analytic cases: identical0, +5shift5, -10shift10, thickness-only center0, remote
false-positive retained, missing paint/prediction, out-of-canvas rejection,
8-connectivity, dashed many-to-many support, resize/crop/original sampling.
No mathematical implementation failure observed; original3.884612/608.405860
result is NOT invalidated. Quantiles use linear interpolation and pooled samples.

New analysis is POST-RESULT diagnostic. Original metadata stride selection was
prefrozen; 99imgs +20imgs2_e, 0imgs2_f. Thus paired-view and sequence selection
bias remains, not a capture-level holdout. See selection audit. No detector,
confidence threshold or acceptance criterion selected from these results.

Private gate remains closed even when structural checks pass: official
reproduction and justified qualification thresholds are still missing. Independent
human semantic review is pending. An automated geometric taxonomy is not a human
causal label or proof of domain gap. Rollback: remove this offline increment;
retain original immutable results and production configuration.

## Validation method and actual results

| Stage | Actual evidence | Result / limitation |
| --- | --- | --- |
| GPU capture | comma10k-tail-clrernet-capture.json |119x2 exact repeat and historical union match; original model identities retained |
| Directional re-evaluation | comma10k-tail-clrernet-report.json |original median3.884612,p95608.405860; GT→pred p95343.351548 unchanged |
| Spatial same-population counterfactual |same report |42,296 samples, p95137.819733px; original608.405860 remains reported |
| All-point spatial diagnostic |same report |68,282 samples,p95286.837298px; DIFFERENT population, not a substitute |
| Complete119 ledger |comma10k-tail-clrernet-ledger.json |input/output SHA, components, scores, regions, categories; no raw pixels |
| Human review |comma10k-tail-clrernet-human-review.json |metadata manifest only; actual independent human review PENDING |
| Unit/regression/build |comma10k-tail-validation.json when finalized |executed counts recorded separately; no fabricated PASS |
| Replay / simulation / shadow |not applicable / unchanged |controller work untouched; private inference NOT_RUN |

The original upper5% tail consists of2,115 supported-row points:
road1,389; my_car607; movable95; undrivable24; lane_marking0; movable_in_car0.
1,079/2,115 have nearest spatial marking within .05image-width; 1,036 remain
farther. A row association sensitivity is numerically demonstrated, but it does
not prove every predicted unpainted lane is geometrically correct.

Width-quarter tail6,627points across73frames:3,610 spatially sensitive,
3,017 still remote. Frame taxonomy:25GT_UNAVAILABLE,15NO_PREDICTION,
19ROW_ASSOCIATION_SENSITIVE,50MIXED_ROW_AND_SPATIAL_TAIL,
4SPATIALLY_REMOTE_PREDICTION,6NO_LARGE_ROW_TAIL. Thus neither one/two remote
frames nor a pure coordinate bug explains the distribution.

Near p95776.546058px; mid451.137921px; far has no supported samples, null.
Public overlays of six deterministically chosen examples show contextual lane
continuations across dashed gaps, occlusion and hood; assistant visual inspection
is diagnostic only, not independent human-label validation. Raw overlays were inspected externally and never committed; they are now
unavailable after the cache loss described below. Semantic categories count every tail point.

Confidence0.4–.6/.6–.8/.8–1 has p95636.296120/613.371381/469.223174px.
Higher scores improve median but do not eliminate large tails. Scores below the
original.41 threshold are unobserved; no-output frames have no invented score.
Confidence buckets also show support and diagnostic large-tail rates with
explicit denominators. No confidence gate was optimized or promoted.

## Annotation provenance and full-run limitation

The pinned official comma10k README says imgs2 is unfinished. Metadata shows
2,000imgs2masks but only601distinct Git blobs:1,400share a379byte PNG whose
already-opened subset representative is entirely undrivable. These are not
verified human lane-absence labels. Thirteen occur in the119subset and contributed
zero original directional samples, so this does not invalidate or explain away
the608px tail. No frame was filtered or relabeled. See the annotation provenance
receipt. Image/mask file pairing alone does not prove annotation completeness.

The bounded full attempt reached an observed10,336/11,888before cache loss on WSL
restart. No full distribution survives; see the full availability receipt and
public-run persistence record. Independent human causal review remains pending.
The machine attribution verdict preserves this uncertainty.

## Handoff

Conclusion: MIXED representation/row-association sensitivity plus substantial
remaining paint-localization/coverage disagreement. No metric implementation
failure observed. Coordinate/FOV/domain effects cannot be conclusively separated
from model failure without additional appropriate GT. No ego-lane verdict.

BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Official CULane remains unavailable;
comma10k alone cannot grant PUBLIC_GT_PASS. Calibration, road registration,
desired-path reference and private human validation are still missing. No sealed
reference generated or private comma4 log opened. See blocker hierarchy.

REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED. V1/V2/FAMILY_REDESIGN history, comparator/A3 policy
and production LatControlTorque unchanged. Logical commits recorded in Git.
