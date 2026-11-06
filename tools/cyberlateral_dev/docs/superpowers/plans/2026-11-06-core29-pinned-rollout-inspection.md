# CORE29 implementation plan

Spec: [design](../specs/2026-11-06-core29-pinned-rollout-inspection-design.md).
BASE a9863f4a6cba70ef8dadda2f17b28fe79ac7c2b0. Inline TDD, one final reviewer.

## Global constraints

No old code changes, arbitrary input semantics, numeric execution or new vehicle authority.
Use external evidence workspace, preserve branch refs and host-owned linked worktree.
Inspect pins from verified CORE28 result/ZIP; do not generate expected hashes with new code.

## Task 1 — fixed identity API and no-execution CLI

Interfaces: API consumes the exact historical artifact identities; CLI consumes only API
receipt/error. CLI inspection exit is independent of historical result exit. Docs must agree.

1. Commit spec/plan; fresh CORE28/CORE18 focused baseline. Expected: 46/35 PASS.
2. Write API/CLI behavioral tests, run them before modules exist. Expected: assertions
   naming missing CORE29 feature, not dependency/import failures. Record RED output.
3. Implement minimal fixed-pin API and descriptor CLI; no changes to old code. Expected:
   new tests PASS; original model/helpers/producer byte-identical.
4. Add Korean guide and three navigation links. Expected: valid local links.
5. Run new+old focused regressions and fresh complete DEV verification. Expected: all tests,
   Ruff/Ty/Codespell/own compile/wheel pass, unchanged frozen wheel and validated manifest.
6. Independently inspect sealed historical originals twice (API, direct/cold CLI), error and
   failed-output cases. Expected: matching receipts/artifacts, no new execution or writes;
   source649/protected639/ref32 custody, gate-consumer PASS. Count actual tests/compiles.
7. Commit implementation, task-done verification, one whole-range fresh review. Address
   Critical/Important in one RED/GREEN fix pass with full gate; defer Minor. Seal evidence.

## Review Focus

Check pin provenance and cross-case confusion; historical REJECTED vs inspection success;
hostile JSON/checksum bytes without parsing; bounded regular-file capture and race limits;
root replacement/post-layout checks; cold import cache/temp side effects; failed/partial
stdout/help/stderr and unknown backend status; globals restored even on BaseException;
no semantic/current-source/vehicle authority overclaims; synthetic fixture work vs inspection0.

Completion: fresh full gate, independent two-run byte parity, source/ref custody, honest
review disposition and unsigned ZIP/manifest verification. No publish or deployment.
