# Persistent public lane evaluation and human review

Baseline187b2515c; user's latest detailed specification governs this work.
No private inputs/reference generation/promotion, no controller/comparator/A3
changes, no detector/config/confidence search, no human labels invented.

## Design
Plain sealed JSON per frame remains the existing numerical contract. A separate
durable store handles fsync(file), atomic rename, fsync(directory), no-follow
reads and immutable rows. Its schema/source SHA enters a new run freeze. A rebuilt
external GPU environment is a new declared identity, not the lost old runtime.
Resume scans and verifies every row against the exact freeze and input identities,
then recomputes metrics without re-inference. Orphan rows after a crash recover
through index reconstruction; corrupt/stale/duplicate rows fail PARTIAL_INVALID.
Index/status use the same durable writes. COMPLETED marker is written LAST,
binding all validated rows/index/aggregate artifacts; absent marker never qualifies
as completed. Completed verification does not rerun inference.

The GPU runner remains isolated from external network. Acquisition is a separate
bounded public-only operation against pinned official Git blobs. Data/weights,
full ledger/raw outputs and runtime remain outside Git in persistent storage.

Freeze review selection before the full result: ten declared geometric strata,
four entries each, frame-ID tie break, overlap retained as multiple reasons.
This is diagnostic sampling, not a held-out qualification sample. A manifest binds
input/prediction/metric/tool/policy/full completion identity before human viewing.
A localhost-only UI reads these artifacts, shows original/paint/lane/component/
error overlays and records human taxonomy and reviewability. Immutable per-frame
annotation receipts and no automatic labels. Browser validation uses separate
synthetic TEST_ONLY fixtures, never actual public human annotations.
Final causal aggregation requires all selected frames reviewed; otherwise
TAIL_HUMAN_REVIEW_PENDING and TAIL_UNRESOLVED. CULane NOT_RUN remains separate.

## Verification
TDD: process kill before rename/after row commit/before index, restart recovery,
SHA drift across source/environment/input fields, row corruption/duplicates/missing,
early marker, deterministic resume; review selection/bindings/taxonomy/save/restart.
Real browser: loopback load/overlays/navigation/select/save/no JS errors/no external
requests/server stop. Full AutoTune, Ruff/syntax/publication/privacy/authority/diff,
SCons, independent reviewer, logical commits/push/clean exact origin.
Full numeric output and subset comparison require11,888/11,888 valid receipts.
Human final attribution is explicitly pending until a real person supplies labels.
