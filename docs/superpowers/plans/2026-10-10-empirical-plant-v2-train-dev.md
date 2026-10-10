# Empirical plant V2 TRAIN/DEV generation implementation plan

**Goal:** Execute the user's EMPIRICAL_PLANT_V2_TRAIN_DEV_GENERATION from cfeb0fc29; source audit is immutable input.
**Architecture:** Separate authorization/split, exact source-bound numeric extraction, coverage/bridge, TRAIN fit/DEV selection, private model freeze and public redacted receipts. Reuse the frozen eight model configs and numeric policies without changing historical modules.
**Spec:** User's explicit 18-step request; execute natively without intermediate questions, independent final review.
**Tech stack:** Existing Ubuntu 24.04 Python3.12/capnp/numpy; single-thread BLAS.

## Constraints
- Exactly three admitted old routes, lexical TRAIN/TRAIN/DEVELOPMENT; never HOLDOUT.
- Split and execution authorization persisted before numeric opening; immutable hashes and per-segment receipts.
- No V1 samples, partial classes, media/GPS/model/planner/TA/SG/composition/production writes.
- 100Hz integer latest-past,20ms age, no segment/mask/bin/route history crossing.
- ARX1/FIR25 x delays0/5/10/20; common DEV201, existing TRAIN dimensional support; no relaxed gate.
- Unknown limit states stay unknown; future untouched holdout CLOSED.

## Review focus
- Authorization must constrain source files, routes and exact adapters, not merely labels.
- qlog/rlog or copied streams must not double-count a segment.
- Development one-segment limitations cannot trigger route-role reassignment.
- Stage A valid mask cannot depend on gyro/yaw availability.
- No reported frozen model without private coefficients, source/environment and policy binding.

## Tasks
- [x] Add failing split/authorization tests; implement empirical_v2_policy.py; persist split/authorization before opening.
- [x] Add failing source-specific numeric/coverage tests; implement empirical_v2_signals.py and empirical_v2_execution.py; extract each admitted route with its exact schema in isolated worker.
- [x] Add failing common-support/bridge/selection/freeze tests; implement empirical_v2_generation.py using frozen model utilities; run TRAIN/DEV only.
- [x] Add publication/holdout package tests and empirical_v2_publication.py; publish new aggregate receipts and feature record.
- [x] Independent review; focused/full/controls/replay/Ruff/syntax/publication/privacy/diff/SCons.
- [ ] Commit/push; exact latest CI SUCCESS, origin equality and clean tree.

## Executed result

Three routes / 157 segments extracted; all three source-bound runtime bridges confirmed. TRAIN fit 24 models; DEVELOPMENT support is zero in all bins, so Stage A selection and Stage B admission are blocked. No selected model or holdout is invented. Two fit/evaluation runs have exact result-chain hashes; source-verified resume also preserves all three route receipts. Focused 63, empirical 462, full AutoTune 2831 + controls142, replay16, Ruff/syntax/publication/privacy/diff/SCons and independent review pass. Final push/CI verification is recorded in the task handoff after commit.
