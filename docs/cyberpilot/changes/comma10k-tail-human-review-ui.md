# Public marking-tail human review and completion-gated analysis

## Identity and purpose — IMPLEMENTED
Cyber Validation/UI, feature/cyber-autotune, baseline1a15e7c77. These offline
modules prepare public comma10k tail adjudication; they do not create human labels
or lane reference evidence. Vehicles are not applicable. Raw public inputs and
annotations live in external persistent storage.

## Original references and call path
comma10k commit6c205fe4c43cc53b2b1befafb1060d0606555027, category2 human semantic
paint masks; CLRerNet commitdae038f67da57e292e5293a68c9c1c2922de13c2,
Apache-2.0, frozen non-EMA CULane weight. Existing lane_public_batch durable
completed marker → exact ledger/input identities → lane_public_full_analysis
sample pooling → frozen lane_tail_review_contract manifest → lane_tail_review_ui
verified PNG/mask/prediction overlays → explicit human annotation. Dependencies
reuse Python/NumPy/Pillow and stdlib HTTP; existing Windows Playwright/Chrome is
test-only. No production dependencies or upstream controller integration.

## Changes and expected effect
- lane_public_full_analysis: requires exact completed frame population; streams
  compressed double arrays and preserves unchanged supported-row and same-point
  spatial metrics. Reports p50/p90/p95/p99/max, coverage/failure denominators,
  frozen y thirds and descriptive count bins. Quantiles pool original samples;
  they do not average frame quantiles. Own source, metric/policy SHA, NumPy
  version and linear quantile method bind output.
- lane_tail_review_contract: ten predeclared strata, at most4per stratum,
  deterministic rank/frame-ID ties, overlap preserves reasons. The policy was
  frozen before this new completed full result, after historical subset and
  interrupted-run work; this is diagnostic selection, not a qualification holdout.
  Exact completed ledger file SHA and each image/mask/prediction/metric identity
  bind the manifest. No auto semantic label.
- lane_tail_review_ui: only127.0.0.1; Host/Origin/nonce checks, local assets,
  restrictive CSP, no telemetry. Original image, exact category2 paint components,
  detector polylines, many-to-many paint-cell support, unsupported components,
  directional/same-point error, y bins, confidence and IDs are shown.
  Paint components are not ego lane identities. Pixel units are not meters. Unsupported paint-component counts are geometric diagnostics,
  including empty-marking masks; they are not final semantic detector-failure labels.

UI source/helper identity binds overlays, receipt validation and hashing helpers.
Frozen original diagnostic source identity is checked on opening and each selected
frame load; active review-tool identity is checked before load/save. Decoded image,
overlay, frame selector and save ordinal commit together using a request token;
stale asynchronous navigation responses cannot replace the current frame.
Labels require explicit acknowledgment, taxonomy, reviewable flag and UTC timestamp.
Unreviewable frames require UNRESOLVED. No prior-frame filling or model fallback.

Annotations use fsync/atomic rename/directory fsync, immutable ordinal rows and a
bound index. Missing indexed rows fail closed. A crash row before index update
can recover; startup publishes the validated recovered index under its writer lease,
so later deletion cannot silently permit relabeling. No silent source/schema
migration. Browser automation uses a separate TEST_ONLY_BROWSER_VALIDATION manifest;
its saved labels are TEST_ONLY_NOT_HUMAN_EVIDENCE and cannot enter public adjudication.

## Regression risk and acceptance
Risks: deletion/corruption, frame races, helper drift, wrong subset, pooled-metric
direction/denominator mistakes. No detector thresholds or qualification criteria
change. Historical119protocol is bound to SHA
1b6a1d3f3dda87a8ae173e3e1a32b9d5c86a488bb2af8a84374348ca45a14f4e;
derived subset receipts retain parent completion and original full-row identity.
All count/y bins are descriptive; unchanged .41 detector threshold is not optimized.
Rollback removes only these analysis/review modules; existing controller, comparator,
A3 and rejected CLRNet history remain intact. No raw images or weights are committed.

## Validation method and actual results
TDD covers selection/identity/completeness, annotation source/schema/timestamp,
test-label exclusion, missing indexed rows/recovered orphans, localhost controls,
malformed POST, drift, pooled quantiles and count/bucket/failure denominators.
New focused46PASS. Stable-source AutoTune1190PASS (295.40s); SCons100%PASS.
Publication520files/0findings; authority/privacy/diffPASS. A source-set-changing
regression execution is excluded from final proof; stable-source rerun passed.
Actual Chrome browser: load/overlays/navigation/taxonomy/save/reload and process
restart persistence PASS; delayed-response frame/save alignment PASS; JS errors0,
external page requests0. Both test loopback servers were closed and verified
unreachable. Screenshot stays outsideGit. Independent reviewer found four initial
defects and one orphan-recovery follow-up; all received regression fixes. Final independent review: no remaining important
findings; independently rerun new46tests PASS.

Replay/closed-loop/shadow vehicle stages are NOT_RUN: this public pixel review
track has no controller or actuator consumer. It does not supersede existing
controller experiment results.

## Handoff — BLOCKED / REAL VEHICLE STATUS
Full result/distribution and selected actual public manifest are pending acquisition
and complete-run proof. Human review remains TAIL_HUMAN_REVIEW_PENDING; automatic
geometry taxonomy is hypothesis only. No final cause or retain/reject verdict is
created without real review. CULane official reproduction remains NOT_RUN/BLOCKED.
Private comma4 NOT_OPENED. Sealed reference NOT_GENERATED.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
