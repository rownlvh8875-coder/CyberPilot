# Cyber AutoTune grouped torque aggregation and point identity

## Identity and purpose

- Area: STEP8 / Cyber AutoTune offline torque identification preparation.
- Branch: `feature/cyber-autotune`; baseline HEAD `1ee1eb07f6cc48526f4d61265abe317fe67cc23b`.
- Purpose: preserve route/clock-epoch boundaries while combining only structural torque-bucket coverage from development-fit evidence.
- This layer does not flatten raw points across epochs, execute TLS, compute confidence, generate candidates, alter Params, touch vehicle/CAN I/O, relax native thresholds, or grant runtime/promotion authority.

## Design

- New `torque_aggregation.py` defines immutable `TorqueEpochEvidence`, `TorquePointIdentityEvidence`, `TorqueAggregationInput`, and authority-free `TorqueAggregationReport`.
- Epoch identity binds route SHA-256, source commit, segment range, boundary reason, source-algorithm SHA, signal contract and full provenance digest set.
- Same-route epochs must use the same source commit, must not overlap, and follow explicit boundary semantics:
  - contiguous successor => `CLOCK_RESET`
  - segment gap => `MANIFEST_GAP` or `MALFORMED_PREVIOUS`
  - later same-route epoch cannot claim `START`.
- Zero-point epochs are allowed only as boundary-only evidence; an all-zero request is blocked.
- Pooled counts are labeled `pooled_count_thresholds_met`; they are explicitly not native `is_valid()`.
- Group order is canonicalized by epoch SHA for the aggregate digest and never interpreted as a synthetic time sequence.

## Point identity evidence

- Read-only exact-schema extraction replays each frozen cold epoch with source-A-identical `torqued` acceptance.
- Only the final bounded native bucket contents are retained in the local point manifest.
- Exported per-point fields are limited to sample SHA-256, signal time, normalized torque and lateral acceleration.
- Sample identity excludes epoch index so accidental cross-group duplication cannot be hidden by reassignment.
- No raw CAN, GPS, video or unhashed route label is exported.
- A verified point-identity receipt can remove only `RAW_POINT_IDENTITY_UNVERIFIED`; it cannot remove statistical-independence, fit or candidate blockers.

## Development dry-run result

- aggregation groups: **19** total / **15** nonempty
- pooled final points: **31,595**
- pooled bucket counts: `[104, 608, 2709, 11591, 10588, 4443, 1194, 358]`
- pooled bucket deficits: all zero
- pooled count thresholds met: `true`
- point identity verified: `true`
- within-group duplicate sample IDs: `0`
- cross-group duplicate sample IDs: `0`
- duplicate signal times: `0`
- non-increasing signal times: `0`

Remaining blockers after point identity evidence:

1. `CROSS_GROUP_STATISTICAL_INDEPENDENCE_UNVERIFIED`
2. `NATIVE_EPOCH_VALIDITY_NOT_ESTABLISHED`
3. `FIT_NOT_AUTHORIZED`
4. `CANDIDATE_GENERATION_NOT_AUTHORIZED`

The pooled coverage therefore demonstrates only that the missing outer-torque coverage exists across the selected development corpus. It does not prove that the 31,595 points are IID/independent observations or that a pooled TLS estimate is statistically qualified.

## Validation

- focused aggregation tests: 11 passed / 15 subtests
- pre-point-identity full affected run: 427 passed
- final point-identity-integrated affected run: **428 passed**
- dry-run v4 repeat: byte-identical PASS
- Ruff: PASS
- `git diff --check`: PASS
- grouped no-fit dry-run v3 repeated byte-identically before point-identity integration
- grouped no-fit dry-run v4 binds point-identity summary and removes only the raw-identity blocker

Artifact identities:

- aggregation module: `1115a4142d62e4cfdd682e8d946fad58a3729a4599c2d48f98721b9d529843ac`
- aggregation tests: `e72665320ebae2cd0c8f6416b3c23178ff7dd1bed7227c9f1dccec2972f22e39`
- aggregation dry-run v4: `39bf5c6ef91931856c2ce6b24e08845096e1353b123467127506782a841b1dbe`
- point full manifest: `27ed097453beeb075b133cc492b8462d5b5c2de7bf36e2f1d94e145f95b846d8`
- point identity summary: `85f10e24a0992086e46ad4be873534f0bebf2ffad6f875dd83046605269aad9d`
- aggregation policy v2: `3e99bdd38efea917079c58a0ec89091056883c16504de40f3253139ce76b2d0d`
- point identity policy v2: `de8e714314651894cd30df7e29cfebabd79a8271fa72c12f4cbabb4bfc4290bd`

## Next gate

- Do not run a pooled fit until a reviewed cluster-aware statistical policy is frozen before observing pooled estimate outcomes.
- Treat route as the minimum correlation cluster; point count must not be treated as independent sample count.
- Define uncertainty/stability using route/epoch-aware methods (for example leave-one-route-out diagnostics) without silently selecting favorable groups.
- Preserve development/evaluation separation; the currently screened routes are development-fit evidence only.
- Keep candidate generation, profile promotion, vehicle application and real-time shadow blocked.
