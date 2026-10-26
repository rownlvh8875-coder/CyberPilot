# Stage1 V4 saved-evidence attribution implementation plan

Goal: explain the completed V4 retrospective result using immutable saved arrays only.
Spec: the user's HURDLE_STAGE1_V4_CAUSAL_ROLLOUT_AND_STAGE1_ERROR_ATTRIBUTION_REVIEW request.
Baseline: 3943f5c2f4ef641e673ca6a47b24b44a359765c8; execution head remains bd8045ef2a0da62a92603439f38e7740f5923622.

Architecture: additive attribution math, manifest-bound read-only orchestration, and aggregate-only publication modules. Reuse V2 exact score-group AUC and verified saved-array IO where contracts match. No frozen executor changes or new dependencies.

## Constraints and review focus

- Verify authoritative repeat-1/repeat-2 byte and decoded content identity before analysis of repeat-1.
- Trap fitting, normalization, inference, threshold selection, rollout regeneration, source reconstruction, candidate selection and raw/qlog/HOLDOUT access.
- Verify reference anchors and array identities before joining V1 truth to V4 results; missing context is INPUT_INSUFFICIENT, never reconstructed from logs or model execution.
- Distinguish continuous one-step delta error from projected integer tick error; gate MOVE is not projected movement.
- Retain exact integer AUC fractions, one-step hit accounting and terminal telescoping identities.
- Freeze the first-quarter divergence definition and descriptive support 0 / 1..200 / >=201 before numerical analysis.
- Aggregate outputs only on the documented direct E external volume; preserve both actual replicas and all source bytes.
- Multiple mechanism states are allowed. Context drift is association; gate-perfect magnitude residual is nonexclusive evidence.
- Preserve null selection and all closed authority states. No V5 design or automatic next work.

## Tasks

- [x] Write failing synthetic tests for one-step accounting, exact AUC/ties, transfer, rollout identities/subsets/events/streaks, missing inputs, firewall, privacy, repeatability and trapped resume.
- [x] Implement empirical_hurdle_v4_attribution_math.py with deterministic aggregate reductions only.
- [x] Implement empirical_hurdle_v4_attribution.py with evidence/public receipt lock, E identity proof, immutable member readers, operation/write firewall, two fresh runs and verify-only resume.
- [x] Implement empirical_hurdle_v4_attribution_publication.py with explicit public projections, schema/privacy checks, mechanism accounting and a single review-category trigger.
- [x] Freeze attribution policy/source bindings; verify actual replica equality and all authorized reference manifests. Record input coverage before actual analysis.
- [x] Execute attribution twice independently; compare all authoritative aggregates; verify-only resume both with recompute_calls=0; reverify source manifests.
- [x] Publish the requested 18 aggregate JSON artifacts and Korean report; preserve missing analyses explicitly.
- [x] Run focused tests, historical/V4/combined/full AutoTune-controls/lateral regressions, Ruff, compileall, JSON, privacy/authority, whitespace and SCons.
- [ ] Complete independent numerical and authority/privacy attribution reviews, resolve findings, then commit/push and verify exact publication-head CI and clean local/origin equality.

## Execution decisions

The user supplied the complete analysis definitions and explicitly authorized implementation, two runs, publication and push; no additional scope or design approval is required. Reuse the existing clean feature checkout rather than create an unnecessary new checkout. Detailed job/fold aggregates retain their own denominators; candidate populations overlap and are not independent samples. Saved references are consumed only after exact manifest and anchor verification. No counterfactual execution is permitted.
