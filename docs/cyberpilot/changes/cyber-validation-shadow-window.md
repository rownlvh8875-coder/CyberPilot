# Offline non-actuating shadow-window scheduler

## Identity and purpose

- STEP10 bounded component on feature/cyber-autotune, base
  1ee1eb07f6cc48526f4d61265abe317fe67cc23b, uncommitted.
- Native isolated requested-torque calculations run asynchronously against immutable
  active observations. This is laptop offline diagnostics, not on-device shadow.
- Vehicle boundary inherited HYUNDAI_SANTA_FE_2022 torque kernel, synthetic CP only
  in tests. No physical performance or hardware suitability claim.

## Source and call path

- Native worker/protocol/runner from CyberPilot STEP9 reused unchanged, upstream
  c8fb906815530460ed156f14e09e1f312bb0f851 and opendbc4134c0d1 pinned references.
- No fork/private code copied; existing repository/native licenses retained.
- Caller serialized job -> strict source/CP/input binding -> one pending slot ->
  worker thread -> native child -> bound response -> immutable aggregate result.
- No runtime controller caller, live transport, Params access or actuator consumer.

## Changes

- shadow.py: frozen ShadowJob; ShadowSession lifecycle/admission/poll/snapshot/close.
- tests/test_shadow.py: real native observation/candidate; controlled worker faults,
  queue saturation, stale output, deadline, cancellation and unexpected worker death.
- Session fixed source/CP/fingerprint, sequence monotonic; full windows reset native
  state. Timestamp/time unit inherited10ms; no physical delay inserted.
- One pending/one executing/one result. Full queues drop NEW item with counted gaps.
  Deadline covers queue+compute+waiting to poll; expired metrics removed.
- Timeout upper bound60s inherited from native supervisor; explicit caller deadline
  >0<=60s is experiment policy, not a steering latency threshold or tune parameter.
- Active request/response are bytes, never callback/output ownership. Exceptions
  cannot directly mutate supplied observations; generic fault codes only.
- All runtime_accepted/promotable false. Rollback: stop using this standalone tool.

## Risks and acceptance

- Not a hostile-source sandbox or hard real-time promise. Native work outside lock,
  but validation/copy/lock/OS scheduling still forbid using API on active control thread.
- close joins supervised worker; process creation/OS stalls have no absolute wallclock
  guarantee. Context manager or explicit close required; no automatic profile writes.
- Fresh state/window is not continuous vehicle shadow, warmup/learner ownership or
  multi-process integration. No lateral truth, applied saturation, longi/brake adapter.
- Source/CP hashes and active response claims are bindings, not authenticated evidence.
- No measurement/acceptance changes, holdout/H1/H2/device access or safety modifications.

## Tests and handoff

- TDD missing module RED -> 9 tests/18 subtests PASS before final review.
- 159 package tests / 447 subtests PASS; 291 affected controls+AutoTune tests PASS
  (10.94s, exit0); Ruff/diff whitespace PASS. Default PC1273 collected, 300s deadline
  interrupted, outer exit1/no final counts; NOT PASS, no named assertion failure established.
- Independent review: 0 Critical / 0 Important / 1 Minor deferred: terminal worker
  death clears buffered result without increasing result_drops; terminal_fault visible.
  Reviewer closure-during-admission and cross-source response-substitution probes PASS.
- Actual routes/closed-loop/on-device shadow NOT RUN. Overall NOT_READY.
- Remaining full STEP10: advisory promotion/rollback gates, continuous shadow and
  qualified failure/latency/performance evidence, persistent storage/runtime rollback.

## Subsequent accounting follow-up — 2026-10-02

The historical deferred Minor above was reproduced and resolved in the separate
`cyber-validation-shadow-drop-accounting.md` record. One locked counter statement
accounts for terminally discarded buffered results, with both-axis/five-mode tests.
Post-fix package243/775subtests,affected375 and whole-PC1282/43skipped/1xfailed
PASS; independent review0findings. This does not change the original run's scope
or qualify continuous/vehicle shadow. Longitudinal windows and advisory promotion
were also added in their separately recorded later work; runtime rollback remains absent.
