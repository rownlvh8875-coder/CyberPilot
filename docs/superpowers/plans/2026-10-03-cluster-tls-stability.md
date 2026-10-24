# Cluster-Aware Torque TLS Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compute authority-free pooled TLS estimates from frozen sufficient statistics and evaluate route/source-commit leave-one-cluster-out numerical stability.

**Architecture:** Add a pure Gram-matrix TLS kernel, then a cluster stability evaluator that consumes immutable route statistics. A frozen runner binds the predeclared policy and existing 85-route artifacts; every result remains diagnostic and cannot create a candidate.

**Tech Stack:** Python 3.12, NumPy, pytest, Ruff.

**Spec:** `docs/cyberpilot/changes/cyber-autotune-torque-aggregation.md`

## Global Constraints

- Work in existing `feature/cyber-autotune` workspace; do not commit, push, merge, reset or clean.
- Do not open holdout/H1/H2 data or write Params, CAN, controller, profile, vehicle or runtime state.
- Freeze thresholds before reading TLS estimate outcomes.
- Route is the minimum correlation cluster; source commit is an additional sensitivity cluster.
- No candidate generation, confidence qualification, promotion or deployment authority.

## Review Focus

- Gram-matrix TLS must match the existing raw-point native-parity diagnostic.
- Subtracted leave-one-cluster Gram matrices must fail closed on invalid/degenerate matrices.
- Route/source dominance and insufficient cluster counts must block before fitting.
- Stability thresholds must be bound by a frozen policy digest, not selected after outcomes.
- Passing numerical stability must not set confidence or candidate authority.

---
### Task 1: Gram-matrix TLS kernel

**Files:**
- Create: `openpilot/tools/cyber_autotune/torque_gram_tls.py`
- Test: `openpilot/tools/cyber_autotune/tests/test_torque_gram_tls.py`

**Interfaces:**
- Consumes: point count, 3×3 `X.T @ X`, and 8 bucket counts.
- Produces: `fit_torque_gram(TorqueGramInput) -> TorqueGramReport`.

- [ ] Write failing tests for affine/noisy parity with `identify_torque`, repeatability, invalid Gram, PSD/degeneracy, and authority flags.
- [ ] Run focused tests and confirm RED because the module is absent.
- [ ] Implement the minimal immutable Gram TLS diagnostic.
- [ ] Run focused tests and Ruff; confirm GREEN.

### Task 2: Route/source cluster stability evaluator

**Files:**
- Create: `openpilot/tools/cyber_autotune/torque_cluster_tls.py`
- Test: `openpilot/tools/cyber_autotune/tests/test_torque_cluster_tls.py`

**Interfaces:**
- Consumes: immutable route Gram statistics and frozen `TorqueClusterTLSPolicy`.
- Produces: pooled estimate, route/source-commit omission estimates, jackknife diagnostics and blockers.

- [ ] Write failing tests for stable clusters, factor/offset instability, insufficient routes/commits, dominance, invalid omission Gram, and no authority escalation.
- [ ] Run tests and confirm RED.
- [ ] Implement pooled, leave-one-route-out, leave-one-source-commit-out and route-jackknife diagnostics.
- [ ] Run focused tests and Ruff; confirm GREEN.
### Task 3: Frozen policy runner and evidence

**Files:**
- Create: `docs/cyberpilot/changes/cyber-autotune-cluster-tls-stability.md`
- Create: work evidence policy/result JSON and read-only runner under the existing D-drive work directory.

**Interfaces:**
- Consumes: frozen sufficient-statistics artifact and predeclared policy digest.
- Produces: authority-free cluster TLS result JSON and validation report.

- [ ] Freeze policy thresholds before any fit outcome is computed.
- [ ] Implement a runner that validates all artifact digests and invokes only the pure cluster evaluator.
- [ ] Execute once, then repeat byte-identically.
- [ ] Run affected AutoTune+controls tests, Ruff and `git diff --check`.
- [ ] Update validation documentation and progress ledger without commit/push/merge.

## Pre-flight shared interfaces

- Task 1 estimate fields are consumed verbatim by Task 2; tests pin names and units.
- Task 2 policy/result schema is consumed by Task 3; the policy digest is frozen before execution.
- Ruling: continue in the existing feature workspace because it contains the uncommitted STEP8 chain; a new worktree would omit that state. Cost if wrong: weaker isolation, mitigated by no destructive Git operations and full status/diff checks.
