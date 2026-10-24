# Native three-arm experiment orchestration

## Identity and purpose

- Cyber Validation STEP9; bounded component implemented and independently reviewed.
- feature/cyber-autotune/1ee1eb07f6cc48526f4d61265abe317fe67cc23b, uncommitted.
- Execute upstream/current/candidate requests twice each through the real isolated
  native worker. Diagnostic requested-torque comparison only, not quality promotion.
- Existing HYUNDAI_SANTA_FE_2022 worker boundary; no new vehicle claims.

## Original references

- Existing public CyberPilot native_protocol/native_runner and comparison constants
  reused unchanged. Upstream torque implementation c8fb9068 and opendbc4134c0d1 remain
  unchanged. No private/fork logic copied; repository/native licenses remain intact.
- Caller immutable requests -> exact3-arm/same-frame admission -> fresh native child
  twice/arm -> validate response -> trace repeatability -> aggregate diagnostics.
- No model use, extra dependencies, live process hooks or actual source role discovery.

## Changes and expected effect

- native_experiment.py: frozen experiment descriptors, exact matrix/input checks,
  six-process orchestration, status collection, ordered trace repetition, JSON-like
  aggregate result and internally generated Markdown.
- tests/test_native_experiment.py: real worker smoke run and independently shaped
  fault/diagnostic fixtures. Prior test and measurement code untouched.
- Same frames/fingerprint; source and CP may intentionally differ and retain separate
  digests. The caller supplies them; no CP/profile modification or tune generation.
- Two repeats establish only deterministic diagnostic behavior, not independent
  statistical samples. Timeout uses existing native supervisor60s upper bound.
- RMS command differences/rates and exact requested-bound occupancy are explicitly
  not physical steering jerk, applied actuator saturation or closed-loop response.
- Missing outputs omit comparisons. Nonrepeatability FAIL; otherwise always
  REVALIDATION_REQUIRED until missing physical/evidence/longitudinal gates are met.
- Fresh controller state and existing10ms time contract retained; no added delay.
- Rollback is cease using standalone tool. Stock active control unchanged.

## Regression risk and acceptance

- Role/scenario tags and hashes do not prove upstream provenance, CP qualification,
  independent center truth, physical plant validity or accepted candidate settings.
- Fixed CP execution cannot substitute for dynamic live-learner ownership.
- No new metric formula replaces v2; no threshold, reference or coverage relaxation.
- Root paths/CP bytes/raw frames/traces excluded from aggregate reporting.
- KeyboardInterrupt propagates with child cleanup; persistent crash-safe audit is
  not supplied. No holdout/H1/H2/device/CAN/Params access or deployment.
- Independent review required. Runtime accepted/promotable permanentlyfalse.

## Validation method and actual results

| Check | Method | Result |
| --- | --- | --- |
| TDD | missingmodule RED ->6tests | 6PASS |
| Package/controls/Ruff | existing environment | 150 package / 282 affected PASS; Ruff PASS |
| Default PC | 1264 collected, 300s deadline | interrupted, no final counts; NOT PASS |
| Two-checkout native execution | synthetic 20 frames, c8fb baseline/current/current | 6 completed, repeatable, equal command traces; REVALIDATION_REQUIRED |
| Independent review | one bounded-plan review | 0 Critical / 0 Important / 1 deferred Minor |
| Real route replay / closed loop / vehicle shadow | not executed | NOT RUN |

## Handoff

STEP9 PARTIAL. Native three-arm diagnostic execution is now connected; complete
v2 metric/coverage producer, candidate binding, plant/longitudinal integration and
asynchronous non-actuating shadow remain. Overall vehicle readiness NOT_READY.
Deferred minor: permanent distinct-CP/source cross-arm response-reuse fixture is
absent; reviewer in-memory probes passed. Work integration is not that permanent test.
