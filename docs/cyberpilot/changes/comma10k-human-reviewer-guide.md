# comma10k 29-frame reviewer instructions

PUBLIC COMMA10K / NO INDEPENDENT LANE TRUTH

Frozen manifest: 82d9c2163afe5bc8d22c6afc534f3a293723625b1072776f41604082f82cea10. Frame list and selection reasons must remain unchanged.

Inspect the original image with overlays both on and off. Automatic selection names are hypotheses, not labels. Choose one primary label and explain mixed causes in the comment. If unsure, use UNRESOLVED; reviewable=false requires UNRESOLVED. Save only after personally inspecting the frame. Save is immutable; duplicates/overwrites are rejected. Previous/Next and jumps do not save automatically. The checkbox resets on navigation. Export contains original V1 sealed rows and a sealed progress/result binding; raw images are excluded.

## Frozen taxonomy

- **DETECTOR_FALSE_POSITIVE**: A detector line is clearly unsupported by the visible road marking. A gap between painted dashes is not a painted-mask miss automatically.
- **DETECTOR_MISS**: A clearly visible relevant marking is not detected. All painted markings are GT, but the detector representation may target only lane boundaries; check representation first.
- **DETECTOR_LOCALIZATION_ERROR**: The same identifiable marking was detected, but the prediction is spatially displaced. No numerical threshold is inferred from this review.
- **GT_MASK_AMBIGUOUS**: The image does not support an unambiguous mask judgment, or the GT is incomplete. Do not force a detector-failure label.
- **GT_EXTRA_MARKING**: The GT includes additional paint types that the detector output does not represent. This is not automatically an ego-boundary miss.
- **COMPONENT_MATCHING_ERROR**: Prediction and paint are individually plausible, but row/component association compares the wrong structures.
- **REPRESENTATION_MISMATCH**: Continuous polylines versus dashed/painted masks account for the discrepancy; absence of paint between dashes is not automatically detector failure.
- **FAR_FIELD_AMBIGUOUS**: Distant/horizon geometry is not visually adjudicable. Image thirds are pixel regions, not calibrated distances.
- **INTERSECTION_OR_MERGE**: An intersection, split or merge prevents simple marking association. Do not infer an ego lane.
- **MULTI_LANE_AMBIGUOUS**: Several marking structures are plausible and assignment cannot be resolved from this frame.
- **OTHER**: A cause outside the frozen labels; explain it in the comment. It prevents a resolved causal verdict.
- **UNRESOLVED**: Evidence is insufficient. Use this for unreviewable frames; do not guess.

## Interpreting metrics

Prediction→GT is same-row midpoint distance; GT→prediction measures the reverse direction. Same-point 2D uses the identical supported prediction population with spatial matching. Neither metric is ego-lane truth or meters. Never subtract their p95 values as a causal matching-error magnitude. Selected29 category percentages describe the stratified review sample, not all11888 images. Final statistics pool original cached samples; no averaging per-frame percentiles, outlier removal or new detector run.

Detector scores use the existing public bins. They are not human confidence. Reviewer confidence is NOT_RECORDED in the immutable V1 annotation schema; export uses null rather than a fabricated HIGH/MEDIUM/LOW. Future confidence collection requires a declared versioned contract, not mutation of these rows.

## Local workflow

Use the persistent external recovery root as PUBLIC_CACHE and run from the prepared repository:

    .venv/bin/python -m openpilot.tools.cyber_autotune.lane_tail_review_workflow
      --run "$PUBLIC_CACHE/full-run-persistent-v3" --cache "$PUBLIC_CACHE/comma10k-full-cache"
      --manifest "$PUBLIC_CACHE/full-analysis/human-review-manifest.json"
      --output "$PUBLIC_CACHE/public-human-review" --port 0

Join the lines into one command. Startup verifies all11888 receipts before printing a127.0.0.1URL; wait for that URL before opening the page. No CDN/telemetry/external requests. Ctrl+C closes the server. Source/manifest/workflow identity drift blocks startup/requests. Never delete freeze files to bypass a mismatch.

Progress/export are available locally at /api/progress and /api/export. Final attribution at /api/final-attribution is blocked until29/29 valid rows exist. COMPLETE means annotation coverage, not resolved causes or qualification. Any UNRESOLVED/OTHER/unreviewable keeps the causal verdict unresolved. Descriptive dominance uses strict majority within the selected sample only. There is no new detector acceptance threshold; the maximum resulting status is PUBLIC_DIAGNOSTIC_RETAINED. Official reproduction/qualification remain blocked. A returned diagnostic report can be saved as a new immutable snapshot; it must not replace the historical raw/full result.

Current actual labels0/29: TAIL_HUMAN_REVIEW_PENDING. Private comma4 NOT_OPENED, sealed reference NOT_GENERATED.

BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
