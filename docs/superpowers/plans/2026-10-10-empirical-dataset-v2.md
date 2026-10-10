# Empirical Dataset V2 Implementation Plan

> For agentic workers: use superpowers:executing-plans task-by-task.

Goal: prepare route-disjoint V2 without reusing any V1 numeric data.
Architecture: exact root allowlist -> metadata receipts -> conservative route
identity / V1 exclusion -> immutable route split -> gated numeric eligibility.
Stack: existing Python, pycapnp, zstandard, NumPy; Ubuntu 24.04 / WSL.
Spec: docs/cyberpilot/changes/empirical-dataset-v2-readiness.md.

Global constraints: 201 support minimum; eight existing yaw configurations;
no V1 numeric reuse, media, GPS, candidate execution, production writes.
Review focus: copied/renamed V1 route; qlog/rlog duplicate segments; aliases
escaping root; insufficient route counts; holdout opened for eligibility.

1. Write failing tests for root validation, homogeneity, V1 exclusion and
   deterministic whole-route split. Implement empirical_dataset_v2_policy.py.
   Freeze root/homogeneity/split/eligibility policies before numeric work.
2. Write failing tests for metadata-only traversal, content identity, lineage
   grouping and atomic resume. Implement empirical_dataset_v2_inventory.py.
   Reuse publicly pinned existing metadata only for V1 exclusion; no V1 payload.
3. Write failing tests for causal support, gap/mask/bin boundaries, gyro clocks,
   missing signals, optional crosscheck gates and holdout authorization.
   Implement empirical_route_eligibility.py. No fitting or candidate execution.
4. Write failing tests for exact redacted publication and readiness. Implement
   empirical_dataset_v2_publication.py; run inventory twice, publish only
   aggregates. If fewer than three untouched compatible routes, do not extract.
5. Independent review; focused/full AutoTune/controls/replay/Ruff/syntax/privacy/
   publication/SCons/diff checks. Document executed results, commit/push and
   verify exact origin HEAD, clean tree and latest Actions SUCCESS.

The user's explicit execution authorization supplies the design and execution
approval; no additional permission handoff is required.
