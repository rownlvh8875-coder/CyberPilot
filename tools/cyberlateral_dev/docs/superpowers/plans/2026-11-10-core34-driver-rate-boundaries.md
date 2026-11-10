# CORE34 Driver/Rate Boundary Characterization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox tracking.

**Goal:** Protect28 hand-derived public API driver/rate boundaries without changing runtime.
**Architecture:** Four table-driven unittest methods with preregistered literal stages;
separate in-memory mutation proof,not a new production oracle or CLI.
**Tech Stack:** Existing CPython3.12.13/stdlib/locked .venv;no installation.
**Spec:** [design](../specs/2026-11-10-core34-driver-rate-boundaries-design.md).

## Global Constraints

BASEaddf620d6c9c555890f186bffa0ebe38ebc20ba2;existing host-owned linked worktree/new branch.
Runtime/API/old test/reference/wheel/CORE32/33 changes0;old edits only README/backlog.
Requests±1,scale16,allowance7,factor1,multiplier3;UP2/DOWN5 or explicit0/0 hold.
Four methods/28literal cases,not28unittest methods. Actualr/T2/scale null,R_BUDGET
UNRESOLVED,StaticGateFAIL;no actual/F61/Controller/Runtime/CAN/r/dt or remote writes.

## Review Focus

Literal derivation versus mirrored oracle: expected stages must be fixed before new-case execution and never computed by the model.
Threshold representation: endpoint integer tags versus adjacent fractional hex and rounded zero must be distinct for both signs.
Asymmetric history: all seven previous commands and both directions must use literal bounds,not a symmetric absolute-delta assumption.
Sequential clips/state: rate can lift driver-clipped zero;zero budgets hold nonzero history without being mislabeled F61 r=0.
Mutation evidence/scope: six realistic in-memory changes must fail assertions,baseline must restore,and seed/coverage limits must remain explicit.

## Task 1 — literal public API boundary tests

Create project/test_driver_rate_boundaries.py,docs/DRIVER_RATE_BOUNDARIES_CORE34_KO.md,
spec/plan. Modify README/backlog links only. Consumes public step/Input/State/Limits;
produces four discoverable tests and28fixed row cases,not new product interfaces.

- [ ] Fresh old oracle11/state12 focused baselines;read brief and write literals/tests.
- [ ] AST-freeze row counts10/14/2/2 and test SHA with no new-case model execution;
  commit preregistered tests/spec/plan. Expected28rows and valid syntax.
- [ ] Run unchanged-model tests,expected4PASS/28model calls. Existing functionality
  characterization has no missing-feature RED/no production implementation.
- [ ] Compile six in-memory own-synthetic-oracle mutants and bind only for isolated
  tests. Expected each mutant assertion failures/no errors,then baseline4PASS again.
- [ ] Add guide/navigation;new+old focused regression,expected27testsPASS.
- [ ] Fresh dev.py verify NEW_EXTERNAL:expected1916tests/328owncompiles,static/wheelPASS,
  unchanged pinned CORE33 pair and98Manifest entries.
- [ ] Independent two mutation/profiling runs and expected freeze/source custody:
  corresponding proof bytes equal,baseline28models per run,source680/protected674/
  priorrefs38 preserved. Report actual mutated work,not whole-task totals.
- [ ] Commit/task-done test;one fresh whole-branch review. Regrade/exclusions;
  one test-proven fix pass/full gate if needed. Unsigned evidence ZIP/independent check.
