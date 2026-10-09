# Standalone Smoothness Governor V0 Implementation Plan

> Execute natively with TDD and an independent reviewer. User explicitly authorizes autonomous SG-only implementation, development screen and publication.

**Goal:** One canonical baseline-command governor, without TA composition/search/acceptance.
**Architecture:** SG-A unit-delta projection, last-output state only. Frozen baseline native commands generated once per scenario, then replayed identically to three descriptive plants.
**Tech stack:** Existing Python/native baseline, typed frozen role inputs, immutable JSON receipts.
**Spec:** User SG IMPLEMENTATION ONLY request and additive frozen selection/config/metric/matrix policies.

## Constraints and review focus
- Preserve all existing source, contracts, TA and historical evidence. Enabled output is a versioned extension; old disabled-only output remains authoritative for old experiments.
- Original GovernorCommand/InterventionInput exact type/field validation; reject TA identities, unknown fields, timeline drift/config mutation.
- Projection radius1 is normalized authority radius, not an identified rate or physical delay. No time constant/queue.
- Fresh and intervention resets rebase to current command; inactive nonzero input rejected. State never affects baseline controller.
- Pure frozen-command replay cannot establish feedback stability; distinguish plant tracking response from controller-in-loop evidence.
- TV/sign claims only with stated contiguous initial/reset support. Event boundary derivatives disclosed, no hidden mask improvement.
- Threshold unjustified; no search/evaluation/composition/vehicle authority.

## Tasks
- [ ] Policy: failing selection/pin/identity tests, source-only policy/config/scenario/matrix freeze commit BEFORE implementation/results.
- [ ] Governor: failing invariants/firewall/reset/identity tests; minimal SG-A implementation; unchanged inputs and additive strict output; independent preflight.
- [ ] Screen: failing replay/metrics/coverage tests; frozen command generation, source/execution binding BEFORE any screen; 11x3x2 exact repeats; test-only controls separate.
- [ ] Publication: additive aggregate results/readiness with source pins, preserved blocker/history bindings, all regressions/build/review.
- [ ] Commit/push, latest Actions SUCCESS, final HEAD/origin/clean check.
