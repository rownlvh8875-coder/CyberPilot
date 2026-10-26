# Empirical Plant Implementation Plan

> For agentic workers: use superpowers:executing-plans for native implementation.

Goal: read-only measured signal identification with untouched holdout.
Architecture: source-bound numeric extraction -> frozen train/dev model
selection -> immutable model -> one holdout opening and exact repeat evaluation.
Tech stack: existing Python, pycapnp, zstandard, NumPy.
Spec: docs/cyberpilot/changes/real-log-empirical-plant.md

## Global constraints
No images/GPS/model/path payloads, production authority, TA/SG execution,
historical changes, tuning, raw publication or calibration promotion.
Private persistent data remains outside Git.

## Review focus
Wrong yaw unit despite a schema name; absent safety-limit observation;
single-route adjacent-segment leakage; truncated logs; stale cache/model.

## Task 1: Frozen policies and metadata
Create empirical_plant_policy.py and tests/test_empirical_plant_policy.py.
Tests first: strict file inventory, embargo/split disjointness, no adjacent
cross-role segments, immutable receipts, policies frozen before payloads.
Run focused RED, implement deterministic inventory/policy, run GREEN.
Commit policies and split before signal inspection.

## Task 2: Source-bound extraction
Create empirical_plant_signals.py and tests/test_empirical_plant_signals.py.
Tests first: exact field whitelist, units/sign contracts, duplicate/gap/future
rejection, limitation masks, source identity and cache corruption rejection.
Audit source blobs/metadata, then implement causal numeric extraction;
persist per-segment receipts atomically; holdout payload gate stays closed.

## Task 3: Identification and evaluation
Create empirical_plant_model.py and tests/test_empirical_plant_model.py.
Tests first: synthetic delay/sign/unit recovery, stable FIR/ARX admission,
one-step/free-rollout metrics, naive baselines, residual diagnostics,
model freeze before holdout, exact repeatability and no reselection.
Implement only predeclared families, fit TRAIN and select DEVELOPMENT.

## Task 4: Private run and publication
Create empirical_plant_run.py and tests/test_empirical_plant_run.py.
Tests first: holdout once-opening/resume, source/model/policy revalidation,
public whitelist, no candidate execution/promotion, historical immutability.
Run private extraction twice; freeze final model; open holdout once;
evaluate identically twice. Publish explicit unavailable stages and aggregates.
Perform independent review, full required checks, commit/push, latest CI success.
