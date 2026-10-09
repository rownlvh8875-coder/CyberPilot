# Assisted private holdout analysis implementation plan

**Goal:** bind completed 60-frame assisted review and frozen detector results without upgrading independence.
**Architecture:** new read-only analysis module consumes validated existing receipts; existing hashed admission/UI/math are unchanged. Local report contains per-frame binding and observed-support centers; public output is an explicit aggregate allowlist.
**Spec:** current user request, implemented in private-assisted-holdout-analysis.md.
**Tech stack:** existing Python / unittest / SHA-256 receipt utilities.

## Constraints and review focus
- Frozen60 selection and historical AI/human/detector/evaluation receipts unchanged.
- No threshold tuning, meter conversion, blind provenance or qualification.
- Point-weighted distributions; unavailable frames reported outside error denominator.
- Missing original AI boundary has no modification-distance sample.
- Geometry matching cannot adjudicate semantic wrong association or false-positive truth.
- Publication must contain no sample IDs, image coordinates, paths, timestamps or human comments.

## Tasks
- [x] Tests first: receipt drift, incomplete set, exact known group errors, modification side/state accounting, observed-only centers, confidence empty/boundaries, redaction, blocker retention and determinism.
- [x] Implement analyze(...) and publication(...) in a separate module using frozen math.
- [x] Execute on completed actual private receipts twice; store immutable local artifact and public aggregate.
- [x] Full AutoTune/controls, Ruff/syntax/publication/privacy/authority/diff/SCons.
- [x] Independent review; all findings resolved and re-reviewed.
- [ ] Post-publication handoff: exact origin and latest CI are verified live after push; no circular commit receipt.

Next priority is physical measurement and uncertainty propagation. Pixel evidence cannot remove calibration or ego-association blockers.
