# Trajectory authority V0 implementation plan

Goal: Source-justified TA-only causal prototype, exact native baseline, frozen development screen.
Architecture: TA-B one-step clipped-error innovation inside native PID update; SG disabled.
Tech stack: Existing Python/native LatControlTorque and unchanged descriptive curvature/yaw plant.
Spec: User's TA-only authorization; docs/cyberpilot/changes/trajectory-authority-v0.md.

## Constraints and review focus
No historical70 selection/search inputs, private data, production changes, tuning, frozen evaluation,
SG implementation or composition. Existing architecture and evidence remain byte-identical.
Inspect exact baseline, finite/bounded clipped-error state, correction before antiwindup, reset lifecycle,
one physical queue, original friction/conversion, unavailable observability and separate objectives.
User explicitly authorized autonomous selection/implementation; no additional approval handoff.

## Tasks
- [ ] Freeze source-only family selection, canonical config, metric policy, NEW synthetic scenarios/matrix.
  Test missing/changed source, unknown family/config, role authorization. Commit before algorithm/results.
- [ ] Write failing native-equivalence, clipped-error innovation, causality/reset/bounds tests.
  Implement new offline core using existing exact input/output schemas; no production mutation.
- [ ] Write metrics/runner accounting tests. Run baseline/current/TA twice on frozen development set.
  Verify full trace equality; report trajectory and smoothness separately with coverage and no thresholds.
- [ ] Independent review and regression repairs. Focused/full/controls/replay/Ruff/syntax/publication/
  privacy/authority/diff/SCons. No UI added: browser not applicable.
- [ ] Publish additive nonqualifying receipts and feature record; commit/push; verify actual latest CI,
  local/origin equality and clean tree.
