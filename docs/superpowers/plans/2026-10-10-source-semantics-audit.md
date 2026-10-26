# Empirical source semantics audit implementation plan

**Goal:** Source-audit predeclared metadata generations, preserving historical evidence and all numeric/vehicle gates.
**Spec:** User's EMPIRICAL_SOURCE_SEMANTICS_EQUIVALENCE_AUDIT_V1 request.
**Architecture:** Additive frozen triage, exact public source manifests/fingerprints, source-bound metadata adapters, redacted classifications and future untouched admission. Full file equality is sufficient only within a complete manifest; AST equality is a reviewed candidate, not automatic semantic proof.
**Execution:** Native implementation in the existing clean requested branch; independent reviewer at completion. User has explicitly authorized this design and execution.

## Constraints and review focus
- No driving signal bodies, GPS/media, fitting, support counts, numeric split or holdout access.
- Historical files immutable; no production/controller/device changes.
- PRIMARY: all clean DIFFERENT_SOURCE_GENERATION buckets; SECONDARY only if PRIMARY has no two-route admitted pool, fixed top3 ambiguous ranking; TERTIARY schema-only proven failures, max2; total10.
- Exact origin/commit, dirty build fail closed, source-specific adapter only.
- Unknown history stays TRAIN_DEV_CANDIDATE_ONLY; future untouched holdout mandatory.
- Relevant manifest completeness and dependency closure; no coarse whole-commit equivalence.
- Physical/lineage failures cannot be repaired by parser changes.
- Private metadata only in local store; explicit public whitelist.

## Tasks
- [x] Tests/red-green: triage, source identity, manifest, fingerprints, classes.
- [x] Freeze triage and manifest before selected public source audit.
- [x] Audit exact selected commits; conditional secondary/tertiary policy only.
- [x] Tests/red-green: metadata adapter, empirical profile, future admission.
- [x] Revalidate selected source metadata only; persist additive no-overwrite receipts.
- [x] Publish hashes/aggregate class, signal matrix, route readiness and documentation.
- [x] Independent review; focused/full/controls/replay/Ruff/syntax/publication/privacy/diff/SCons.
- [ ] Commit/push; exact latest CI SUCCESS and clean origin equality.
