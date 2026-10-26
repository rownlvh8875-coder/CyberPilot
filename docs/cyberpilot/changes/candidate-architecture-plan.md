# Separated candidate architecture implementation plan

Goal: freeze offline interfaces, evaluation policy and diagnostic fixtures without implementing candidates.
Architecture: cascaded trajectory core then command governor, with plant-only physical delay.
Tech stack: Python frozen dataclasses, exact JSON schemas, SHA256 receipts, unittest.
Spec: candidate-architecture-separation.md and the user's architecture-only scope.

## Global constraints
Historical evidence at 6c60eb8ba is read-only. No production edits, private reads, candidate algorithm,
parameter search, composition execution or vehicle authority. CURRENT remains a BASELINE alias.
Independent calibration and pixel-registration blockers remain unchanged.

## Review focus
Role leakage, shared state, duplicate physical delay, fabricated observability, unsafe input types,
mutable identities, fake distinct arms, retroactive verdicts and unauthorized execution.

## Tasks
1. Audit source injection points; compare parallel, cascade and integrated alternatives. Select cascade.
2. Write failing tests for frozen inputs/outputs, identity, owner/reset and authorization guards.
3. Implement strict contracts and disabled-only passthrough; enabled algorithms raise unauthorized.
4. Freeze separate metric catalogs, cross-objective no-worse requirements and future search schemas.
5. Run synthetic architecture controls only; no historical controller/plant replay.
6. Emit additive SHA-bound contracts, matrix, decision, probe and readiness receipts.
7. Independent review; fix defects with regression tests.
8. Focused/full/controls/replay, lint/syntax/publication/authority/diff/build checks.
9. Commit/push, await actual GitHub Actions success, verify clean local/origin equality.

Implementation may proceed within the explicitly authorized scaffolding scope. This plan does not
authorize any future TA/SG algorithm or search.
