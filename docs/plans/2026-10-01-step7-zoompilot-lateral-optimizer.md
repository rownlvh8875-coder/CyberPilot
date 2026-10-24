# STEP 7 ZoomPilot Lateral Optimizer Implementation Plan

**Goal:** Extend the existing non-actuating Cyber Lateral implementation with deterministic metrics and offline-only A0-A5 candidate primitives derived from reviewed ZoomPilot concepts.

**Safety boundary:** No new module may publish cereal actuators, write Params, modify `controlsd` output, expand vehicle or panda limits, or enable itself by default. Online learning belongs to STEP 8.

## Task 1: Freeze the evidence and architecture review

- Write `docs/STEP7_ZOOMPILOT_LATERAL_REVIEW.md` with fixed repository identities, current data flow, planning/controller separation, and KEEP/ADAPT/REJECT/DEFER decisions.
- Write `docs/STEP7_LATERAL_METRICS.md` with metric definitions, provenance requirements, segment 29 coverage, and NOT-RUN baseline/result cells.
- Do not inspect holdout segments 53 or 71.

## Task 2: Extend metrics by tests first

- Extend `test_cyber_lateral_metrics.py` for command and torque derivatives, steering tracking error, reversal frequency, dominant oscillation frequency, torque saturation, left/right curve errors, and independent lane-edge margin.
- Run the test module and record the expected RED failure.
- Extend the immutable input contract and deterministic metric implementation.
- Run the targeted tests to GREEN.

## Task 3: Add offline candidate primitives by tests first

- Add tests for fail-closed speed-aware interpolation, explicit provenance and domain coverage.
- Add tests for a speed-dependent torque envelope that can only reduce authority below an existing vehicle limit.
- Add tests for a steering rate candidate that cannot use faster rates than the current controller.
- Add exact A0-A5 feature-combination tests.
- Run the new tests and record the expected RED failure.
- Implement pure offline modules with no openpilot runtime integration.
- Run the new and existing Cyber Lateral tests to GREEN.

## Task 4: Regression and documentation

- Run all affected controls tests and Ruff from the fixed worktree environment when available.
- Preserve failures caused by missing tooling or baseline environment as FAILED/BLOCKED, never as passed.
- Update both STEP 7 documents with actual test, replay, simulator and regression status.
- Keep replay, simulator, shadow and real-vehicle promotion as NOT-RUN until their separate evidence gates are satisfied.

## Task 5: Local history

- Review the exact diff and prohibited paths.
- Create separate local commits for documentation/metrics and offline candidate primitives only after their relevant checks pass.
- Do not push, merge, deploy or change the remote target branch without a separate request.
