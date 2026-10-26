# F-65 feature change record

## Identity and purpose
Cyber Validation, controller-free Source contract follow-up to sealed F64_HOLDOUT_FAIL.
Base04ae0f6644c7e94b8ed601c46fc45ccff03d0476, branch feature/f65-source-separation-contract.
Separate new version; no alteration/reclassification of F64 or prior T1 failures.

## References and adoption
MIT repository code. Reuse unchanged tools/cyberpilot/f64 source validation, exact Fraction metrics, independent integer oracle, early Controller sentinel, and private output writer. No Controller/Plant imports or device/RLOG access.
New Source provenance differs; low-level F64 scalar observation schema stays unchanged. Real6000 inputs remain unqualified.

## Changes and rationale
- synthetic_source_separation_f65.py: pure seed-to-actual-data encoding, normalized observation fingerprint, fixed terminal state validation.
- run_f65_source_separation_v1.py: complete frozen inventory proof, exact tests, source generation/oracle checks, artifact bundle verification.
- Focused tests/test_synthetic_source_separation_f65.py, independent new workflow, contract and public evidence.
- No existing file/workflow modification.
- Actual first sample and first integer interval encode seed. Opposite first signs separate PUBLIC/EVALUATION; no metadata-only fix.
- D and bit partition derive from signed-int64 storage and uint64 seed width, not performance gains or physical limits.
- New Source first magnitude>0.5 separates it from frozen F64 source magnitude<=63/1024. This is constructed software test coverage, not statistical independence.

## Acceptance and regression
Exact source/oracle metric equality, actual signal/time fingerprint disjointness, recoverable seed, boundary/error/symlink tests, zero Controller calls, deterministic bytes, immutable source/criteria after evaluation.
Full required Source inventory is computed from every new preregistration file plus all100 F64 files and required retained configs/dependencies; empty/partial/duplicate manifests fail.
Bundle inventory checks exact expected paths, not just length.
All public unit-test source seeds, including evaluation-shaped tests, are permanently exposed. Metadata JSON encodes the two largest development seeds as exact decimal strings; converted explicitly to uint64 specification values. Source payload fields stay exact int64.
One two-pass adjudication cohort includes bundle verification before results are inspected. Immutable artifact verification may regenerate the same sources/metrics; it is not adaptive reselection. No code/seed/criteria retries after inspection.
r budget unresolved; candidate/runtime/real performance gates remain closed.

## Planned/actual public validation
New28 synthetic tests passed; RED stages and fixes retained outside canonical evidence. Existing related tests and static checks are recorded in public_validation.json after execution.
Independent reviewer identified incomplete manifest closure. Public omission/duplicate tests reproduced it, and closure enforcement was added before any commit-derived evaluation seed.
Public Source contract revision added the complete exposed test seed inventory before pre-evaluation commitment; no performance threshold or candidate budget changed.
Unchanged F64 test contract55 and existing Exact157/Exact27/F60/F61 are regression targets. Do not call broad Controller-dependent suites.
CI job must execute terminal bundle gate; authentic F64 failed seal rejection is a negative control. Remote Push/manualCI not authorized.

## Boundaries and handoff
No real Controller output, model/tuning modifications, RLOG analysis, CAN/Params, Private E2/HOLDOUT, Git rewrite or remote publication.
Possible outcome only F65_SOURCE_SEPARATION_PARTIAL_PASS_R_BUDGET_UNRESOLVED or a sealed failure. No real performance/generalization, exact replay, candidate admissibility, or Runtime upgrade.
