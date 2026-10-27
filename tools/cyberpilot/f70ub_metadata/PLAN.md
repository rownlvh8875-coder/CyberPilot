# F70UB Static Source Boundary V1 implementation plan

> Execute inline under superpowers:executing-plans. The user approved the existing source-boundary draft and asked to proceed. No additional general permission checkpoint.

**Goal:** Deliver and verify a metadata-only source boundary contract outside the repository.

**Architecture:** Strict pure-stdlib parser/validator with an externally preregistered contract hash and frozen record hashes. Metadata validation returns no calculator request and preserves unresolved statuses.

**Spec:** DESIGN_KO.md and the previously approved F70UB_SOURCE_BOUNDARY_DRAFT_KO.md.

## Constraints

- Baseline: 08eaf10250b6a005fd9bc74f74d2ec7f67c61e79.
- External root: /home/cyberpilot/CyberPilot_F70UB_SOURCE_BOUNDARY_V1.
- Preserve every existing tracked file and all previous seals.
- No numeric sample admission, Controller/Runtime, r computation, historical payload or new RLOG access.
- Metadata hash registry is not physical vehicle or identity attestation.
- Current F70UB 16 resolved/7 unresolved and owner factual unknowns remain.

## Task 1 — pure contract validator

- Write tests for both legitimate classes and adversarial type/shape/source/hash inputs.
- Run RED and confirm missing implementation failures.
- Implement load_json, canonicalize_record, hash_record, validate_contract, validate_record.
- Validate a defensive canonical snapshot of caller-owned objects; never retain mutable trust state.
- Run all external tests GREEN.

## Task 2 — verification and reproducibility

- Run IO/network/reference-import sentinel tests and source relabel/unknown-value rejection tests.
- Run affected Ruff, Ty, Codespell and compile checks.
- Reproduce machine results in two separate fresh output directories/processes and compare bytes.
- Run existing F70U bounded exact 202-test verification and metadata-only Git integrity proof.

## Task 3 — review and delivery

- Fresh review of only new contract/source/tests/docs; never raw logs or snapshots.
- Address important findings through failing then passing tests.
- Produce Korean report, manifest, deterministic delivery ZIP and independent Windows verification.
- No repository commit/push/CI on this external-only task.

## Review focus

- Real/log source relabeling must not turn into admissible numeric input.
- Contract or registry mutation must invalidate trust.
- Unknown fields, nested paths and numeric payloads must fail closed.
- Parser/resource errors must be fixed diagnostic errors without leaking supplied content.
- Accepted metadata must never promote instance/r-budget/F70V/F71 status.
