# CORE36 Partition/Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect the existing batch consumer across all finite partitions of
the two CORE35 chains and interleaved singleton histories.

**Architecture:** Test-only real public API execution, unchanged CORE35 literal
rows and uninterrupted parity. External in-memory AST mutation proofs count
and hash observed execution without adding runtime hooks.

**Tech Stack:** Python 3.12, standard unittest/AST/hashlib; existing DEV gate.

**Spec:** [design](../specs/2026-11-10-core36-partition-resume-design.md)

## Global Constraints

- Exactly two unchanged nine-call CORE35 synthetic fixtures, 256 partitions each.
- Actual returned state feed; no new mandatory internal object-aliasing contract.
- No runtime/API/formula/old test/reference/wheel/cloud changes.
- Actual r/T2/vehicle_scale null; R_BUDGET UNRESOLVED; Static Gate FAIL.
- No F61/Controller/Runtime/CAN/actual input, actual r/dt or remote publication.
- Preserve local branch, host-owned worktree and external evidence.

## Review Focus

- A bug shared by uninterrupted and partitioned paths must still hit literal checks.
- Inactive and zero-budget boundaries must not reset or replace actual history.
- Missing/reordered outputs must fail assertions, not hide in state-only parity.
- Two interleaved histories must not overwrite one another.
- Finite same-process results must not be described as generic/durable recovery.

## Task 1: finite partition regression and evidence

**Files:**
- Create `project/test_partition_resume.py`.
- Create `docs/PARTITION_RESUME_CORE36_KO.md`, this plan and design.
- Modify `README.md`, `docs/CORE_DEVELOPMENT_BACKLOG_KO.md` (navigation only).
- External workspace owns ledger, proof scripts, logs and sealed evidence.

**Interfaces:**
- Consumes `simulate(tuple[LateralInput, ...], LateralState) -> SimulationResult`,
  `initial_state()`, unchanged `test_driver_state_chain` literal row tuples.
- Produces two discovered unittest methods; no exported runtime interface.

- [ ] Step 1: run the existing CORE35/34/state baseline (18 PASS), freeze old
  identities, write new tests and freeze their bytes before first new execution.
- [ ] Step 2: `PYTHONPATH=project:src .venv/bin/python -B -m unittest
  test_partition_resume -v` gives 2 PASS (existing-behavior characterization).
  Assert full output/state equality, literal selected values/types and all
  independently enumerated cut tuples; assert lengths before indexing.
- [ ] Step 3: six in-memory valid-domain simulate mutations each yield assertion
  failures and zero errors; baseline before/after gives 2 PASS. Preserve all
  failure traces and profile counters; source bytes unchanged. This is a
  test-only mutation RED/GREEN cycle, not a missing-feature implementation.
- [ ] Step 4: run proof twice; deterministic counters/observed hashes match.
  Expected each mode: 2 methods, 2,582 simulate, 4,662 step/quantizer calls,
  518 initializations and 2,064 returned batch-state links.
- [ ] Step 5: document scope, tests, limitations and navigation; local commit.
- [ ] Step 6: `.venv/bin/python -B dev.py verify --output <work>/final-verify`
  gives full DEV 1,920 PASS, Ruff/Ty/Codespell PASS, 330 own compiles, unchanged
  frozen wheel SHA and CORE32 stdout pins; 98-file DEV Manifest verified.
- [ ] Step 7: source custody 688 files, prior protected 682, preserved refs 40;
  test bytes equal preregistration; links valid; task-done focused 2 PASS.
- [ ] Step 8: fresh reviewer on full BASE..HEAD and evidence; regrade findings,
  one RED/GREEN plus full-gate fix pass if important, defer minors. Seal ZIP
  with deterministic rebuild, CRC/Manifest/source/ref verification.

Self-review: one cohesive deliverable, no cross-task interfaces; all five
Review Focus behaviors have direct assertions or explicit guide scope.
Standing delegated inline execution applies; no extra approval checkpoint.
