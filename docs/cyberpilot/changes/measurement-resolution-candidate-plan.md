# Measurement-resolution candidate audit implementation plan

Goal: execute the user's audit specification against frozen candidate history and
the 9a6ae36a6 conditional meter aggregate, without new selection or qualification.
Architecture: additive pure distance/comparison module; exact historical snapshot
recovery executor; receipt-bound publication adapter; additive local visualizer.
Native implementation in this session, followed by separate independent review.
No historical source/evidence/controller/meter artifact changes.

- [x] Pin ledger, original archives and meter index/full receipt before outputs.
- [x] TDD: units/frame, strictly monotone world-forward distance, linear interpolation
  only inside observed span, exact boundaries, ratios, signs, coverage and firewalls.
- [x] Recover native trajectories only from identical historical controller,
  configuration, input/reset, harness and environment. Two fresh native executions.
  Relocation is explicit: restore only original request-root metadata in a copy;
  require original request SHA/manifest/summary/result binding, never rewrite history.
- [x] Freeze all declared nominal/development/stress cases before any worker execution.
  No family enumeration beyond existing archived cases, no selection/scoring changes.
- [x] Recovered historical outputs must exactly reproduce archived summary; refuse drift.
- [x] Compute separate distance/scenario/phase tables with existing tracking/smoothness
  context and verdicts. Direction is displacement, not measured improvement.
- [x] Bind all six center envelope extrema, 44/55 coverage and 11 unavailable frames.
  Hypotheses remain nonexhaustive; open physical terms and total bound null.
- [x] Add loopback-only comparison tab with band, effects, coverage and old verdicts.
- [x] Actual audit, browser, focused tests, replay, Ruff, syntax,
  publication/privacy checks, SCons and independent review.
- Release procedure: complete full AutoTune+controls, inspect staged diff,
  commit/push normally, and verify the exact pushed commit's Actions conclusion.
  The commit-specific CI result is recorded in the final handoff, outside this
  pre-push implementation plan.
