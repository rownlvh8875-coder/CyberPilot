# Causal retrospective dataset implementation plan

The user-authorized generation reopens only the exact two V2 TRAIN / V3 CV routes, using the existing source and segment receipts. Historical evidence remains immutable. No fitting, selection, candidate execution or holdout opening occurs.

1. Test and implement exact historical route resolution, source-specific adapter binding, route-set and numeric authorization receipts.
2. Read only declared event bodies and fields. Preserve actual steering rate, request/post-controller/raw command stages, source clocks and optional device gyro.
3. Build all 100 Hz aligned base rows, availability masks, separate causal and legacy run identities, and deterministic input snapshot digests.
4. Persist compact arrays in two external immutable execution replicas. Reject aliases, overlap, stale inputs and conflicting resume bytes.
5. Reproduce historical alignment, bridge and per-bin support without importing model execution. Compare independently repeated arrays and receipts.
6. Publish aggregate evidence, limitations and H1 mapping, run required regression/build/privacy checks, obtain independent review, commit/push and verify exact-HEAD CI.

Readiness is conditional on actual field, identity, bridge and reproduction evidence. The two previously exposed routes remain retrospective development inputs; they cannot become holdout or independent qualification evidence.
