# Public comma10k assisted human review — IMPLEMENTED

## Identity, purpose and references

Cyber Validation; feature/cyber-autotune; baseline
001de8feac9e5728207a62ec7f244f6a3f420213. Fetch confirmed exact local/origin
identity and a clean tree before publishing this increment.

The user requested one public photo at a time and personally supplied all 29
responses in chat. The assistant showed the original, category-2 mask overlay,
prediction overlay, mask-only and prediction-only montage with a short proposed
interpretation. Every reply was saved before presenting the next frame.
This completes the assisted review, not an independent blind review.

Reuse the existing lane_tail_ai_review.py AIReviewSession, immutable human rows,
AI exposure provenance, export and comparison contracts. Source/configuration,
MIT attribution, detector weights, dependencies and submodule identities are
unchanged; no new runtime implementation or integration point.
The published frozen manifest and AI_REVIEW_V1 remain byte-identical.

## Evidence flow and immutable history

Fixed29 manifest → existing public receipts verified → image montage displayed →
AI/assistant interpretation exposed → actual user response → immutable assisted
human row → separate AI-human diagnostic comparison.

Manifest SHA:
82d9c2163afe5bc8d22c6afc534f3a293723625b1072776f41604082f82cea10.
Selection-policy SHA:
ef6c56d4f0f3fd1d377c8a35d8d92e9d5f78f8f3fd0440f998fd2f45db7bae54.
No selected frame, raw metric, AI suggestion or historical receipt was replaced.
Images, rendered montages, detector weights and cache remain outside Git.

Published artifacts:

- comma10k-assisted-human-review-v1.json: canonical export is still incomplete;
  separately includes the 29 actual assisted rows and mandatory exposure provenance.
- comma10k-assisted-chat-history-v1.json: literal responses, frozen frame/AI hashes,
  presentation bindings and the available contemporaneous question receipts.
- comma10k-assisted-ai-comparison-v1.json: human × AI primary-label confusion matrix.
- comma10k-assisted-review-status-v1.json: independent/assisted completion separately.
- comma10k-assisted-review-blockers-v1.json: new snapshot linked to the previous
  blocker receipt; previous blocker/history files are untouched.
- comma10k-assisted-review-validation-v1.json: current checks and artifact identities.

The original live helper accepted agreement with the canonical AI label and
explicit alternative labels. An external versioned helper preserved user
corrections without changing the frozen AI rows. Some displayed propositions
differed from the original AI suggestion; question V2 receipts declare that
difference and its proposed human label. A user agreeing with that proposition
was saved with the explicit human label, not silently mapped to the original AI.
Contemporaneous standalone question receipts exist from frame10 onward.
Earlier question text was not retroactively fabricated; presentation/response
receipts and the original conversation preserve that earlier review context.
Repeated or unknown/stale saves are rejected by the existing contract.

The twelve taxonomy labels are unchanged. One primary label per frame cannot
encode every observation: actual response and displayed question retain additional
misses, normal current-lane detection, junction context and other comments.
OTHER records two affirmative detection observations because the frozen taxonomy
has no NORMAL label. OTHER is not interpreted as a detector failure.
Reviewer confidence was not separately collected; AI confidence remains AI-only.

## SYNTHETIC SCREENING / public diagnostic result

This is public image review, not a new controller synthetic-screening experiment,
and not detector qualification. Actual assisted human answers: 29/29 COMPLETE.
Canonical independent blind answers: 0/29; TAIL_HUMAN_REVIEW_PENDING.

| Primary human label | Frames | Percentage of selected29 |
| --- | ---: | ---: |
| DETECTOR_MISS | 12 | 41.38% |
| REPRESENTATION_MISMATCH | 8 | 27.59% |
| DETECTOR_FALSE_POSITIVE | 3 | 10.34% |
| INTERSECTION_OR_MERGE | 3 | 10.34% |
| DETECTOR_LOCALIZATION_ERROR | 1 | 3.45% |
| OTHER | 2 | 6.90% |

Examples of preserved corrections: frame14 current boundaries good but outside
markings missing; frame18 current boundaries good but opposite markings missing;
frame25 extra central predictions plus a missing rightmost marking; frame29
existing predictions valid, with another right marking missing.
The comment that opposite-direction markings matter less is the user's relevance
observation, not a metric/coverage/threshold change or an ego-lane identity label.

Primary-label agreement with the unchanged AI snapshot: 18/29 (62.07%).
This is an assisted comparison, not independent AI accuracy or a human-replacement
validation. No AI/human label was overwritten to increase agreement. The selected
29 are diagnostic strata, not a prevalence sample of all11,888 frames.
These primary-label counts neither identify each point in the pooled heavy tail
nor estimate causal proportions of the whole dataset.

Full-run history remains: 11,888/11,888; pred→marking median4.96px,
p95 666.97px; same-point2D p95 154.37px. No outlier removal, rerun,
threshold relaxation or subtraction of the two p95 values as a causal quantity.
Independent final tail verdict remains TAIL_UNRESOLVED; no new retain/reject
or reference-estimator promotion is made from assisted labels.

## Validation, scope and regression risk

Main risks are losing literal user corrections, mixing assisted/blind labels,
mistaking OTHER for failure, extrapolating selected-frame counts, and interpreting
agreement as independent accuracy. Export admission revalidated the completed
public store and every manifest/row/AI/presentation binding, including montage SHA.
All29 human receipts and 29 actual-response receipts correspond exactly.
Repeated export and comparison are deterministic; confusion-matrix total is29.
The current AI-aware finalizer rejects these rows with
ASSISTED_HUMAN_NOT_BLIND_INDEPENDENT_ATTRIBUTION, as required.
No annotation, exposure or frozen identity may be deleted to restore blindness.

This increment adds authorized public review evidence/documentation only, with
no new controller/tool behavior. TDD implementation and fail-closed tests already
exist; current regression/build checks are recorded in the validation receipt.
No additional artificial tests were created merely to increase the test count.

## BLOCKED / REAL VEHICLE STATUS

AI REVIEW: SUPPORTING_DIAGNOSTIC_ONLY.
ASSISTED HUMAN REVIEW: COMPLETE, NOT INDEPENDENT BLIND HUMAN EVIDENCE.
HUMAN BLIND REVIEW: FINAL TAIL ATTRIBUTION INPUT, STILL PENDING.

CULane official reproduction remains blocked; comma10k supplies all marking
segmentation, not ego-left/right identities. Public pixel qualification thresholds,
metric calibration, independent extrinsics, road registration, desired-path
evidence and private-domain human validation remain unavailable/unverified.
CLRNet REJECTED; controller V2 REJECTED and stress TRADEOFF_ONLY unchanged.
Production controller, comparator thresholds and A3 rejection unchanged.

Private comma4 NOT_OPENED; sealed reference NOT_GENERATED.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

Handoff: use the assisted export/comparison for diagnostic follow-up only.
An independently blind study needs a separately declared design; this exposed
29-frame history cannot become blind by replaying labels or clearing provenance.
Rollback of this publication must preserve original working evidence and history;
it cannot justify reopening a reference gate.
