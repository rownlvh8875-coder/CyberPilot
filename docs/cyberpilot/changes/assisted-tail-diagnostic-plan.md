# Assisted tail diagnostic implementation plan

Baseline e2decd536e16ccf27d900845665cb41c32a17d31; user supplied the complete
design and authorized completion without intermediate approval questions.

1. TDD: add lane_tail_assisted_diagnostic.py tests for exact29 accounting,
   original pooled metrics (no average of percentiles), unavailable sample counts,
   strict AI/export/exposure/hash/time bindings, deterministic concordance,
   no qualification/private promotion. Preserve all existing source/receipts.
2. Implement separate ASSISTED_HUMAN_TAIL_DIAGNOSTIC_V1 aggregation;
   all12 labels, row provenance receipts, score/y distributions, concordance,
   association groups scoped to the selected sample. OTHER is not a failure.
   No causal dominance or p95 subtraction; detector qualification BLOCKED.
3. TDD: add lane_tail_second_review.py isolated protocol/store tests:
   opaque ID plus explicit not-previous-reviewer/no-prior-exposure attestation,
   presentation whitelist (images/GT/predictions, no metric/stratum/old labels),
   immutable separate store, unknown/stale/duplicate rejection, incomplete gate.
   Inter-rater statistics require all real second-review rows; undefined kappa
   remains null. No reviewer exists now, so no actual rows or statistics.
4. Add typed blocker DAG/NEXT_BLOCKER_PLAN and a proposed, non-executable
   PRIVATE_PIXEL_DIAGNOSTIC_ONLY contract. Actual private gate stays closed.
   Calibration/independent extrinsics, registration and desired-path provenance
   remain separate dependencies, not software estimates of missing truth.
5. Execute original public metric loader for only the frozen29 frames; publish
   metadata-only deterministic diagnostic/provenance/concordance/protocol/plan
   receipts. Do not mutate original annotations, metrics, selection or policy.
6. Focused tests, full AutoTune, Ruff, syntax, publication, scope/privacy,
   diff check, SCons; independent code/evidence review and regression repairs.
   Browser only if UI changes (none planned). Logical commits and normal push;
   exact origin/local SHA and clean tree at completion.

Interfaces:
aggregate(manifest, human_export, experiment, suggestions, metric_loader)
validate_assisted(manifest, human_export, experiment, suggestions)
protocol(manifest); register(protocol, opaque_reviewer_id, explicit attestations)
BlindStore(manifest, registration, separate_path): presentation, append, export
inter_rater(manifest, assisted_export, experiment, suggestions, blind_export): pending until all29
blocker_plan(diagnostic_receipt, blind_protocol_receipt); prior receipt pinned internally

Review focus: point-weighted pooling/unavailability denominators; provenance before
human save; first reviewer reuse; whitelisted blind presentation; fabricated
second-review completion; DAG cycle/overpromotion/private input opening.
