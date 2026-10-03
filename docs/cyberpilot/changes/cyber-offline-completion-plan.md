# Offline completion implementation plan

> Implement inline using executing-plans and test-driven-development; retain the
> existing branch and frozen evidence. User delegated intermediate decisions.

## Goal and design

Complete the requested offline-only engineering scope without expanding vehicle
authority. Existing v1 catalogs/gates/results are immutable historical evidence.
Use new versioned synthetic contracts for additional coverage, not changes to the
measurement rules that judged existing candidates. Reuse native torque/LongControl
and generic plant patterns; do not introduce a competing online writer.

Alternatives rejected: replacing the framework discards reviewed behavior;
labeling v1's 14 scenarios complete omits requested coverage. Selected approach:
incremental offline modules with fresh controller/plant state and aggregate-only
receipts. A supplied trajectory or longitudinal target is not a perception or
full-planner test. Every report must identify this distinction.

## Tasks and interfaces

1. Publication/CI: `audit_changed(root: Path, base: str)` must scan all candidate
   history, staged content and worktree additions/changes; unsupported content
   blocks, no diagnostic prints secrets. Test real temporary repositories,
   type changes, staged-only secrets, removed historical secrets, filename and
   error disclosure. No allowlist/ignore expansion. CI runs on privacy-only changes.
2. Metrics: add `synthetic_metrics.py` with `lateral_metrics(trace, dt_s)` and
   `longitudinal_metrics(trace, dt_s)` returning strict finite aggregate JSON.
   Unit tests use hand-derived trajectories and derivatives; reject empty,
   non-finite, mismatched/nonuniform samples. Synthetic lane truth remains labeled.
3. Versioned scenarios: add an extended catalog (26 lateral and 18 longitudinal
   required cases), immutable frame generation and explicit bad-input outcomes.
   Tests pin scenario physics/signs/temporal changes, not just labels. Freeze
   scenario and candidate selection policy before any candidate evaluation.
4. Offline sandbox: native controller adapters plus plant feedback, fresh
   baseline/current/candidate state, source/config/input/plant/metric identities,
   no files/Params/vehicle writes. In-memory synthetic-only parameter deltas.
   Test exact repeatability, limits, malformed input, mismatched identities and
   candidate rejection. Connect existing bounded worker lifecycle for resource
   faults; never place synchronous simulation on an active control thread.
5. Shadow/profile rehearsal: reuse immutable active snapshots and durable archive;
   add missing active digest/count noninterference, offline activation and rollback
   transitions, partial-write/crash/corruption/unknown-version tests. No vehicle
   ACTIVE state, including after confirmation. Receipts report simulated rollback
   separately from a vehicle rollback.
6. Final evidence: required full local tests/build, repeated synthetic outputs,
   independent review, public aggregate receipts, Korean manual checklist,
   release checklist and branch completion document. Record NOT_RUN honestly.
   Stage only explicit sanitized paths; audit index/history, commit logical units,
   fast-forward push only target branch and verify remote equality/clean tree.

## Review focus

- Deleted/renamed/type-changed private artifacts hidden from normal diffs.
- Policy/scenario names asserting outcomes without actual frame validation.
- Synthetic tracking metrics confused with independent vehicle lane truth.
- Duplicate delay ownership or requested versus applied command confusion.
- Rehearsal PASS accidentally granting runtime/profile/vehicle write authority.

## Evidence ledger

Publication test-first cycle observed failures before fixes for discovery,
unsupported content, history, redaction, type changes, route formats and CI
trigger filters. Initial full AutoTune+controls: 557 passed (pre-review follow-up).
SCons direct executable invocation failed because its child tools were absent
from PATH; activating the existing virtual environment succeeded to 100%, exit 0.
These are incremental checks, not final completion evidence.

## Limits

The publication guard detects declared formats/patterns and blocks unsupported
content. It is not a universal secret detector, nor a substitute for reviewing
staged diffs and source/data provenance. No user driving logs are consumed by
the new synthetic work. Real-vehicle verification stays unverified/blocked.
