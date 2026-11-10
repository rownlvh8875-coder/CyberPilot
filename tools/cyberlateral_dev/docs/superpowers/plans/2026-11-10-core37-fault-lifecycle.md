# CORE37 Fault Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect canonical public fault-counter histories across mixed reset,
driver and batch-resume boundaries without altering existing model behavior.

**Architecture:** Two manually declared100-call trajectories with selected
independent expectations and uninterrupted full-output parity. External
function-only AST mutations test sensitivity and ordered execution hashes.

**Tech Stack:** Python3.12,standard unittest/AST/hashlib,existing DEV tooling.

**Spec:** [design](../specs/2026-11-10-core37-fault-lifecycle-design.md)

## Global Constraints

- Two100-call canonical synthetic chains,18declared schedules each/36total.
- Actual returned-state feed;no mandatory internal object-aliasing contract.
- Manual declared expectations frozen before new chain execution;not blind.
- No runtime/API/formula/oldtests/vectors/wheel/cloud changes.
- Actual r/T2/vehicle_scale=null,R_BUDGET UNRESOLVED,StaticGateFAIL.
- No F61/Controller/Runtime/CAN/actual data/actual r-dt/remote publication.
- Preserve host-owned worktree,local branches/commits and external evidence.

## Review Focus

- Fault-suppressed request must not independently zero an active command.
- Inactive and below-threshold resets must clear the returned counter/history.
- Batch entry/return must preserve nonzero counters through89/90/wrap boundaries.
- Signed threshold and driver histories must remain independent when interleaved.
- Fixed progressions and same-process parity must not imply general recovery or vehicle authority.

## Task 1: mixed fault lifecycle regression

**Files:**
- Create `project/test_fault_lifecycle.py`, `docs/FAULT_LIFECYCLE_CORE37_KO.md`.
- Create this plan and design;modify README/backlog navigation only.
- External task workspace owns ledger,proof scripts/logs and sealed evidence.

**Interfaces:**
- Consumes public `simulate(tuple[LateralInput,...],LateralState) -> SimulationResult`
  and `initial_state()`;existing own-model functions for in-memory mutation only.
- Produces2unittest methods;no runtime exports or new CLI.

- [ ] Step1: baseline CORE35/36/state16PASS;verify prior source/ref custody;
  write new vectors/test and AST freeze/commit before first new-chain execution.
- [ ] Step2: `PYTHONPATH=project:src .venv/bin/python -B -m unittest
  test_fault_lifecycle -v` ->2PASS characterization. Check every selected literal,
  each edge state,full uninterrupted parity and all18schedules/independent streams.
- [ ] Step3: six function-only in-memory mutations ->assertion failures/errors0;
  normal before/after GREEN;source/classes/callables restored. Per mode4200model/
  quantizer,494batch,42initializations,452returned batch-state links.
- [ ] Step4: repeat proof;both summaries and eight observed records byte-identical.
  Each8modes/33600model calls;additional DEV/reviewer work excluded from totals.
- [ ] Step5: guide and navigation,focused Ruff/Ty/Codespell PASS;local commit.
- [ ] Step6: `.venv/bin/python -B dev.py verify --output <work>/final-verify`
  ->1922PASS/staticPASS/331compiles,unchanged wheel/CORE32 pins/98DEV Manifest.
- [ ] Step7: source692/prior686/refs41 unchanged;new test matches preregistration;
  task-done focused2PASS,clean tree,whole-branch fresh review and effect regrade.
- [ ] Step8: important findings get one RED/GREEN+full-gate fix pass if required;
  defer minors. Independently verify unsigned ZIP CRC/Manifest/deterministic rebuild.

Self-review: one cohesive task,no shared task interfaces;five Review Focus lines
mapped to selected literal/state/parity assertions and explicit scope. Standing
delegated inline execution applies;no extra approval menu or remote integration.
