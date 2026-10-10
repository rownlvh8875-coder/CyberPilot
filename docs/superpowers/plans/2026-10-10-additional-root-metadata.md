# Additional private root metadata inventory plan

Goal: classify only the two explicitly approved roots, without opening any driving numeric body.
Baseline: 9d3df6222. The user's current detailed specification is the execution authority.
Architecture: new versioned policy, metadata scanner/grouping runner and redacted publication module;
reuse old receipt persistence and metadata field extraction read-only. Existing pinned sources/artifacts stay unchanged.
No model, numeric eligibility, support calculation, yaw crosscheck, candidate or production execution.

- [x] Freeze root-policy V2 and metadata identity/split rules with failing-then-passing tests.
- [x] Implement exact-root traversal, metadata-only reading, cross-root deduplication and generation buckets.
- [x] Execute repeat/resume inventory privately; publish only aggregate counts and opaque identities.
- [x] Independent review; regression/build/publication checks.

Commit/push and exact-HEAD CI are verified after this local validation snapshot; final remote outcome is reported in the task response.

Review focus: copies/recompression and partial files; schema differences; lineage collisions; unknown prior analysis;
source mutation/resume; source/CarParams/control mismatches; no numeric or media body access.

Ruling: all new routes have prior-analysis status UNKNOWN unless a trustworthy, route-bound declaration proves otherwise.
No such inference is made from filenames, dates, or filesystem access times. Unknown routes cannot enter HOLDOUT.
Ruling: source-different routes are buckets requiring a new source audit, never merged into the current generation.
Ruling: metadata reader schema is explicitly pinned; parse success on a different source is not schema/source compatibility.
