# Declared hypothesis meter diagnostic implementation plan

Baseline 7557e50803417fc3f0c99303d5b111d7a1a36541; minimum d32d5b65d ancestor verified.
User-specified diagnostic design: additive offline tier; preserve all historical
sources/receipts. No new inference, image decode, log crawl or candidate analysis.

1. TDD: pure batched pinhole projection, exact conditional affine/K, fixed-distance
   queries and per-point distance accounting. Load the historical height/pose
   policy unchanged; append physical mean at nominal pose only. No extra ranges.
2. Read-only adapter verifies the frozen final analysis, original assisted
   reference and detector receipts against the published binding. Recover matched
   point pairs with the unchanged assignment; check against stored residuals.
   Write new derivatives only to a separate local/private store.
3. Calculate all three conditional mappings with full-input rectangle and identity
   orientation ASSUMED. Static OS04C10 K is a source prior. Unknown crop, phase,
   distortion, road and metrology stay open. Fixed queries use nominal physical
   mean/pose rays held fixed over historical sensitivity probes; per-point
   projection intersects each original matched ray separately.
4. Strict aggregate publication with no private identities/coordinates/paths.
   Bind sources, policy, original receipts and full local derivative digest.
   Supporting IMU/stereo feasibility uses existing inventory only; no raw reads.
   Optional vanishing point is not needed for the main result.
5. Add a new meter section through a wrapper around the existing loopback
   visualizer, preserving its source/assets and historical source hashes.
6. Focused + full AutoTune/controls, replay, Ruff, syntax, publication/privacy/
   authority, SCons, actual browser, independent review, commit/push, actual CI.

Interpretation: point-weighted conditional absolute lateral differences; distance
assigned using HUMAN projected forward coordinate, both rays must be forward.
5–30m domain, half-open nearest-distance bins (last inclusive), no clipping.
0–5 / >30m excluded and counted despite edge bin support. No output is a
physical uncertainty bound. Fixed-distance queries are not observed point ranges.
No qualification threshold. Existing actual transforms/Kq/meters remain null;
new conditional meter-equivalent fields live only in the new diagnostic schema.
