# Completed public comma10k diagnostic and frozen tail review

## Identity and purpose — IMPLEMENTED
Cyber Validation/UI, feature/cyber-autotune baseline187b2515c, storage1a15e7c77,
review/analysisb05921c26, publication802c34037. Complete public11888-frame diagnostics and prepare real
human adjudication; no vehicle applicability or private input consumer.

## Original references and call path
comma10k MIT, official6c205fe4c43cc53b2b1befafb1060d0606555027; CLRerNet
Apache-2.0 officialdae038f67da57e292e5293a68c9c1c2922de13c2, non-EMA CULane DLA34
weight SHA424422f1008a5fe1717d52bbc5f631dcc2731808f8adb96110d126fa83d3a8aa.
Pinned official acquisition → Git blob/SHA verification → external persistent
cache → network-isolated official detector → original-row samples → frozen
metrics → durable receipts → LAST completion marker → pooled analysis →
frozen manifest → loopback human review. No production/submodule/controller
integration. Environment/config/preprocessing/postprocessing/package SHAs are
bound in the run receipt. Only metadata is published; no raw images/weights.

## Changes and expected effect
Publish complete metadata with existing reviewed storage/analysis/UI; no detector
parameter/acceptance change. Rebuilt NMS declares a new environment rather than
claiming historical binary identity. Restored119x2has exact historical prediction
canonical-content SHA cc3adad1df04b723a90e20e3a58b38e2c8ea07dea5c4c06c64f2bb7336ecdc55.
Environment SHAa4f0529fef22655b8e7509022f7f06acf4250c2a72681dc649801a829f2655e5.
Run SHAa78c65d0ec4c3b0d008e5aae5df8dc5509b98d0b070c6b76f3dd773389bd57e8.
Input manifest/protocol file SHAs7ed7c1d1a2a7351b2b06797797bfb0bd392cb92c1fbc37b65fd7678f58ba63c0 /
1875c97d37a1207d26ff8b1a0e5c2f6709f20a1ad8ef53f93f3076f37df98fb0.

Acquisition persisted across the actual reboot; all23776public files verified.
Old lost10336prefix never reused. Actual owned-process-group SIGKILL after128durable
rows; restart replayed identities/metrics and reused inference. All128receipt files
unchanged at completion; the bounded-window resume also verified all9472cached
receipt file SHAs unchanged at completion. Finite1800snew-inference windows keep the same freeze;
replay precedes the next window. Explicit frame states and no silent skip.
Completed reuse audits actual weights/images/masks, every receipt/index/artifact
without new inference. Source/environment guards surround admission.

Detector state/reset/physical actuator delay: not applicable to single images.
No CAN/Params/CarController/device/profile write. UI only binds127.0.0.1; no
external assets/telemetry. Maintenance: external cache must match frozen sources.

## Diagnostic public GT — distributions
All11888frames complete, full single pass; whole-population exact repeatability
NOT_EVALUATED. Repeatability proof is119x2only. Linear sample-pooled quantiles,
pixels, no outlier removal/meter conversion/averaging frame quantiles.

| Direction | Samples | p50 / median px | p90 px | p95 px | p99 px | max px |
| --- | --- | --- | --- | --- | --- | --- |
| same-row prediction→GT | 4242806 | 4.962068 | 496.492274 | 666.974077 | 865.165083 | 1923.733527 |
| same-row GT→prediction | 3546760 | 3.007036 | 164.620247 | 328.429491 | 719.210937 | 1923.733527 |
| same-supported-point 2D prediction→GT | 4242806 | 2.286415 | 101.716093 | 154.371065 | 321.509959 | 1208.481267 |

Same-point2D preserves exactly the legacy supported-row prediction population;
it does not replace row p95. All-point spatial/symmetric/normalized diagnostics
are separately retained. Coverage:
{"covered_runs": 2277102, "detection_failure_rate": 0.17810388513513514, "false_positive_components": 5569, "gt_eligible_frames": 9472, "gt_eligible_no_prediction_frames": 1687, "gt_runs": 4085905, "mask_coverage": 0.5573066432038924, "missed_marking_ratio": 0.44269335679610755, "missed_runs": 539145, "no_prediction_frames": 3285, "no_raw_output_frames": 3285, "off_mask_points": 5160440, "off_mask_prediction_ratio": 0.6938319031665348, "pred_points": 7437594, "tail_frame_count": 7260, "tail_frame_prevalence": 0.610699865410498, "unavailable_frames": 4109, "unmatched_gt_components": 61540, "unsupported_points": 3194788, "unsupported_prediction_ratio": 0.4295458988484717, "usable_frames": 7779}.
Exact paint-cell unmatched counts are geometric statistics, not semantic
false-positive/miss rates, officialF1or ego-left/right identity. Empty/unfinished
masks stay counted as unavailable, never zero-error success.

| Fixed image third | Pred samples | median px | p95 px | unavailable frames | GT run coverage |
| --- | --- | --- | --- | --- | --- |
| far | 0 | null / unavailable | null / unavailable | 11888 | 0.000000 |
| mid | 3096843 | 5.593488 | 502.120810 | 4122 | 0.516677 |
| near | 1145963 | 3.826886 | 797.743146 | 5061 | 0.668633 |

Crop-validity starts below the far third; missing far samples are structurally
unavailable. Count bins and y boundaries stay frozen. Analysis JSON includes
GT component/raw prediction/GT row-run complexity buckets preserving all frames.

Automatic hypotheses: GT_UNAVAILABLE:2416, MIXED_ROW_AND_SPATIAL_TAIL:5291, NO_LARGE_ROW_TAIL:525, NO_PREDICTION:1687, ROW_ASSOCIATION_SENSITIVE:1443, SPATIALLY_REMOTE_PREDICTION:526.
Historical608.405860px cut has282445full points;
106084are spatially sensitive under
the original diagnostic width-.05bin. This sensitivity does not establish correct
unpainted lane continuation or isolate detector/domain/calibration failure.

## Historical119subset representativeness
Unchanged metadata-stride diagnostic, never qualification. Derived119receipts
retain full-row and historical protocol identities. Pred median
3.884612,p95608.405860;
full-minus-subset median1.077456,
p9558.568217.
Subset GT p95343.351548,same-point2Dp95
137.819733.
Subset/full coverage/failure/y/count-bin/tail prevalence are side by side in the
comparison JSON. No significance/generalization claim. Sequence/paired-view bias
and label-completeness uncertainty remain; no metric reference qualification.

## Confidence and frozen human review
| Frozen score bucket | Lanes | median px | p95 px | width-quarter large-tail rate |
| --- | --- | --- | --- | --- |
| 0.0:0.2 | 0 | null / unavailable | null / unavailable | null / unavailable |
| 0.2:0.4 | 0 | null / unavailable | null / unavailable | null / unavailable |
| 0.4:0.6 | 9822 | 61.305039 | 703.665978 | 0.727440 |
| 0.6:0.8 | 11736 | 4.077618 | 660.290978 | 0.633244 |
| 0.8:1.0 | 3371 | 1.503382 | 570.994493 | 0.536166 |

Rate denominator: observable lanes with supported-row distance, not human semantic
failure labels. Below unchanged.41is unobserved; no optimized confidence gate.

Review policy frozen before this new full result, after historical diagnostics;
diagnostic selection, not a blind qualification holdout. Selected29
unique frames, max4per stratum, overlap reasons preserved. Counts:EXTREME_TAIL:4, FAR_FIELD_DOMINANT:0, GT_MISS_HYPOTHESIS:4, HIGH_COMPONENT_COUNT:4, LOW_ERROR_CONTROL:4, MULTI_LANE_ASSOCIATION_HYPOTHESIS:4, NO_OUTPUT:4, P90_TO_P95:4, P95_NEIGHBORHOOD:4, REMOTE_PREDICTION_HYPOTHESIS:4.
Empty strata stay empty. Manifest SHA82d9c2163afe5bc8d22c6afc534f3a293723625b1072776f41604082f82cea10;
tool SHA6b0ec140be7fe6862a071da3adf4da3ebc31f2de995067d7c1a9cadf9e4bec1f. Each frame binds image/mask/prediction/metric.

Actual public browser validation is read-only: load/navigation/paint/prediction
overlays and raw/display agreement; no annotation POST/ack or automated human
label. Separate TEST_ONLYfixture verifies save/taxonomy/race/restart persistence.
No external page requests/JS errors; servers closed and verified unreachable.
Screenshots stay external. Actual human annotations0/29;
TAIL_HUMAN_REVIEW_PENDING / detector TAIL_UNRESOLVED. No final causal taxonomy.

## Regression risk and acceptance
No justified qualification threshold exists here. Official CULane remains
NOT_RUN/BLOCKED; completed comma10k cannot replace reproduction. No confidence/
detector/acceptance selection on this result. Risks: representation ambiguity,
unfinished labels, source drift, subset bias and premature promotion.
Selected strata do not estimate population-wide human failure proportions.
Rollback removes new metadata; old history remains immutable. Existing comparator,
A3, V2REJECTED/FAMILY_REDESIGN and CLRNetREJECTED remain unchanged.

## Validation method and actual results
Focused storage/identity/review/analysis81PASS and new publication12PASS; final
current-source AutoTune count/time is in the companion validation receipt; SCons100%PASS using PATH with.venv/bin and.venv/bin/scons -j2.
Ruff/syntax PASS. Final publication/privacy/authority/diff/independent result review
are in the companion validation receipt. TDD covers kill/orphans/stale/corrupt/
early marker, review identity/deletion/recovery and async frame alignment.
Full public diagnostic replay and browser proof are actual; controller simulation,
shadow and vehicle stages NOT_RUN/not applicable to this increment.

## Handoff — BLOCKED / REAL VEHICLE STATUS
Use the persistent external recovery root as PUBLIC_CACHE:

    PYTHONPATH=. "$PUBLIC_CACHE/detector-env/bin/python" -m openpilot.tools.cyber_autotune.lane_tail_review_ui
      --run "$PUBLIC_CACHE/full-run-persistent-v3" --cache "$PUBLIC_CACHE/comma10k-full-cache"
      --manifest "$PUBLIC_CACHE/full-analysis/human-review-manifest.json"
      --output "$PUBLIC_CACHE/public-human-review" --port 0

Join command lines when executing. Tool prints a127.0.0.1URL; preserve source
identities and close server after review. Only genuine human inspection/annotations
can advance semantic adjudication; software never invents labels.
Private comma4 NOT_OPENED; no diagnostic-private exception; sealed reference
NOT_GENERATED. Meter calibration/independent extrinsics/ego association/road
registration/desired path/private human validation missing. New blocker hierarchy
supersedes current gates without altering historical records.

BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No actual vehicle performance, lane-centering or ground-truth qualification.
