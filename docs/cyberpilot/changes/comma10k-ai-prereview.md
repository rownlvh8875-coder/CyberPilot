# Public comma10k AI pre-review — IMPLEMENTED

## Purpose, baseline and ownership
Cyber Validation/UI; feature/cyber-autotune; baseline b9b04f209de18ad105021599519d1122cc317f0a.
Fetch confirmed exact origin/local identity and a clean tree before implementation.
Provide comparable vision observations for the fixed 29-frame public diagnostic review.
AI_REVIEW_SUGGESTION != HUMAN_REVIEW.

AI REVIEW: SUPPORTING_DIAGNOSTIC_ONLY.
HUMAN REVIEW: FINAL TAIL ATTRIBUTION INPUT.
ASSISTED HUMAN: NOT INDEPENDENT BLIND HUMAN EVIDENCE.

## References and call path
Reuse the existing MIT CyberPilot lane_tail_review_contract.py, lane_tail_review_ui.py,
lane_tail_review_workflow.py and durable public storage. New implementation:
lane_tail_ai_review.py and tests/test_lane_tail_ai_review.py. No dependency/submodule change.
Public comma10k/CLRerNet identities and licenses remain in the completed full evaluation record.
The original helper/source/manifest/schema/selection policy and raw metric files are unchanged.

Completed public run → fixed29 manifest → verified original image/mask/prediction →
five-view presentation → Codex vision observation → versioned immutable AI suggestion store.
Separately: human decision → immutable canonical human row → AI reveal/provenance →
optional comparison. No detector inference rerun or controller/candidate change.

## Vision execution and identity
AI_REVIEW_V1 contains 29/29 actual vision suggestions. The Codex assistant viewed each
original, GT overlay, prediction overlay, GT-only and prediction-only presentation using
view_image; observations were written after viewing, not inferred from metric numbers.
The deterministic external renderer verifies existing public receipts and binds view-file
SHA, source image/mask/prediction/metric SHA, renderer SHA and presentation SHA.
The renderer is diagnostic tooling only, not a reference producer. Raw images/montages
remain outside Git. The result JSON commits public identifiers/hashes and concise observations only.

Five-view montages have 700px tiles and were displayed at 2048px overall width. This limits
fine alignment/horizon adjudication; uncertain observations use LOW/UNRESOLVED or secondary
possible labels. They are hypotheses for comparison, not causal truth about the full tail.
Nine questions distinguish visible correspondence, false positives, misses, displacement,
dash/polyline semantics, GT ambiguity, component association, far field and junction/multiple lanes.
The twelve existing labels are unchanged. There is no mandatory failure label for a control
with no clear failure; UNRESOLVED is allowed.

Provider OpenAI, model GPT-6 as exposed by the assistant context; exact build/version is
unavailable and stored as null. This is interactive vision, not an independently reproducible
model-weight inference experiment. AI generation repeatability is NOT_ASSERTED; the saved
observation snapshot is immutable and its receipt is deterministic. No invented model build.
Confidence HIGH/MEDIUM/LOW is uncalibrated suggestion certainty only; it is neither detector
confidence nor a detector/qualification threshold. No threshold/search/selection changes.
Every row has human_label=null, visual evidence, metric context, UTC timestamp, model identity,
prompt/policy/source identity and a sealed receipt. A rerun needs a new declared experiment,
not replacement of any V1 record.

## State, persistence and fail-closed admission
AI rows, experiment freeze and index use atomic fsync/rename with writer leases. Canonical
filenames bind manifest order. Row-before-index orphans are validated before index recovery;
indexed loss, stale frame/config/source identity, unknown/duplicate rows and symlinks fail closed.
The human manifest SHA remains
82d9c2163afe5bc8d22c6afc534f3a293723625b1072776f41604082f82cea10.
The selection-policy SHA remains
ef6c56d4f0f3fd1d377c8a35d8d92e9d5f78f8f3fd0440f998fd2f45db7bae54.

Default BLIND_HUMAN_FIRST hides all suggestions, including from config/state/frame responses.
An explicit before-save reveal requires warning acknowledgment. The first exposure row is
durably stored before any suggestion response; it cannot be overwritten or retrospectively
converted to blind. After-save reveal binds the immutable human receipt. Every request validates
the source/freeze/exposure admission. Refresh/process restart preserves the first exposure.

Assisted human rows use a separate immutable ai-assisted-annotations/index, preserving the
V1 human row bytes/schema. They do not enter canonical annotations or legacy completion.
AI-aware export includes canonical export, assisted rows and mandatory exposure provenance.
The AI-aware final endpoint rejects assisted exposure and otherwise delegates to unchanged
human-only aggregation. AI rows never supply missing human rows or affect the tail verdict.
Comparison requires every human/AI row, preserves both labels and reports exact agreement,
a human×AI confusion matrix, high-confidence and unresolved disagreements. It cannot edit labels
or promote AI to a human replacement.

A persistent anchor in the AI store binds the human workflow output and source/freeze.
Missing sidecars/anchor/index block reuse. Existing human rows cannot silently initialize a new
unbound AI provenance history. A canonical legacy write for an already assisted frame causes
companion quarantine. Use the AI-aware CLI/export for any workflow with AI exposure.
The frozen legacy tools cannot themselves certify blind provenance: direct legacy helper calls
do not consume this companion. Independently claimed blind evidence must include the AI-aware
provenance envelope; absence of it is not evidence of blindness.

The software records exposure through this UI only. It cannot prove that a reviewer did not read
a committed suggestion JSON, another browser/session or another AI source beforehand. To keep
review blind, do not open the result JSON or AI panel until saving that frame. Such external
exposure must be disclosed and cannot be called independently blind. No cryptographic receipt
can restore lost visual independence.

## Validation and review
TDD: absent AI tier RED; HTTP reveal gate RED; independent review reproduced full exposure
sidecar deletion and provenance-free legacy export; dedicated regression tests RED then GREEN.
Fix: anchored admission, separate assisted human store, AI-aware export, quarantine on improper
legacy writes, one writer lease around exposure classification and human row commit.
Additional tests cover 29 AI/0 human pending, schema/hash/unknown-frame/leakage rejection,
immutable rows, restart/provenance, lease conflict, same-row duplicate rejection, comparison
accounting and source path exclusion. Final runtime/log identities are in the validation receipt.

Real browser checks use installed Playwright/Chrome, 127.0.0.1 only, with external requests blocked.
Public mode navigates all29 images, checks overlay/frame agreement, hidden AI defaults and warning
cancel without POST or human/exposure writes. TEST_ONLY fixture exercises before-save assisted
and save-before-reveal blind paths, save/reload, immutable saved state and owned server restart.
TEST_ONLY rows are explicitly synthetic placeholders, never public human evidence.
All servers must be closed and unreachable at completion; screenshots remain external.

## Handoff, rollback and limitations — BLOCKED / REAL VEHICLE STATUS
Prepared repository command (join lines) using the existing persistent external PUBLIC_CACHE:

    .venv/bin/python -m openpilot.tools.cyber_autotune.lane_tail_ai_review
      --run "$PUBLIC_CACHE/full-run-persistent-v3" --cache "$PUBLIC_CACHE/comma10k-full-cache"
      --manifest "$PUBLIC_CACHE/full-analysis/human-review-manifest.json"
      --output "$PUBLIC_CACHE/public-human-review" --ai "$PUBLIC_CACHE/ai-review-v1" --port 0

Wait for full-store verification and the printed localhost URL. Ctrl+C shuts down the server.
Save a personally inspected frame first; the AI panel then opens for comparison.
A before-save reveal permanently records assisted provenance and excludes that row from the
canonical blind-human final attribution input. Never delete freezes/index/anchors to bypass a gate.
API /api/export includes provenance; /api/ai-comparison remains pending until full review.
Working caches/annotation stores are external; published result/policy receipts are immutable
history, not working files. Restoring them to a new working store does not restore blindness.
Rollback removes the companion; do not reinterpret assisted artifacts through the legacy path.

AI_PREREVIEW_COMPLETE, 29/29 suggestions; actual human 0/29, TAIL_HUMAN_REVIEW_PENDING.
No final human attribution, AI-human agreement measurement, detector verdict change or confidence
threshold calibration has been generated. No exposed public human frames in automated testing.
11,888 full results remain directional median4.96px/p95 666.97px, same-point2D p95 154.37px.
Their percentiles are never subtracted as a causal matching-error magnitude. Full and 119-subset
history is unchanged; CLRNet remains REJECTED and controller V2/comparator/A3 policy are unchanged.

CULane official reproduction, ego-lane identity, metric calibration, independent extrinsics,
road registration, desired-path evidence and private human validation remain blocked/not run.
No public detector qualification or reference promotion. Private comma4 NOT_OPENED.
Sealed reference NOT_GENERATED. Production controller/Params/CAN/device/network authority unchanged.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
