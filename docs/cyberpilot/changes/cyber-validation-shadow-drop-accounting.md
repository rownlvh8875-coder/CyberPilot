# Shadow terminal-fault result accounting

## Identity and purpose

- Cyber Validation / STEP10, bounded diagnostic bug fix; focused verification and
  independent review and post-fix full-PC verification passed.
- A terminal worker fault discards a previously completed, unread result. Count
  that loss, just as normal close already does; do not leave a false zero-drop
  diagnostic. Applies to both offline lateral and longitudinal window sessions.
- Branch feature/cyber-autotune, HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b;
  uncommitted overlay. No vehicle/controller applicability or runtime promotion.

## Original references

- Existing CyberPilot shadow.py on the above HEAD's local offline-tooling overlay;
  prior independent shadow review recorded this as a deferred Minor.
- `_work` terminal BaseException -> condition-locked cleanup -> `snapshot` counters.
  `close` already increments result_drops when clearing a buffered result.
- No fork algorithm or private code copied. Existing license/attribution retained.
  No submodule/model/dependency changes; no new dependencies.

## Changes and expected effect

- shadow.py: increment result_drops only if a result remains immediately before
  terminal cleanup clears it, under the existing condition lock.
- tests/test_shadow_accounting.py: both axes; buffered/polled/empty/normal-close-first/
  prior-overflow cases with a pending job, exact cancellation/drop counts and repeated
  close. Mock only the native execution boundary; scheduler/validation/state are real.
- Alternative of adding a new counter/API rejected: existing result_drops already
  represents discarded completed results. No queue/scheduling/timeout/interface change.
- No tuning constants, physical parameters, delay or measurement thresholds change.
  Existing initialization/reset and closed/fault state remain unchanged.
- No safety/actuator/Params path affected; no runtime consumer of this package.
  Upstream maintenance cost is one local accounting statement and one regression test.

## Regression risk and acceptance

- Avoid double counting after normal close or poll; distinguish a previously
  overflow-dropped result from the still-buffered result. Preserve pending/running
  cancellations and idempotent close. Literal expected drop counts:1,0,0,1,2.
- Inputs are existing synthetic protocol fixtures, not driving samples or holdout.
- Rollback is removing this local diagnostic increment; no active profile changes.
- User delegated routine implementation decisions. One independent read-only review
  follows local tests. No commit/push/merge or vehicle-operation authority is inferred.

## Validation method and actual results

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression | `.venv/bin/python -m pytest -q openpilot/tools/cyber_autotune/tests/test_shadow_accounting.py` | two axes x five synthetic modes | RED:4 subtest failures (buffered0!=1, overflow1!=2),1 test passed/6 subtests passed,0.72s,exit1; final independent GREEN1test/10subtests,0.45s,exit0 |
| Final package | `.venv/bin/python -m pytest -q openpilot/tools/cyber_autotune/tests` | current patch and explicitly bound test closures | 243 passed / 775 subtests,27.14s,exit0 |
| Final affected controls/package | existing unchanged project runner | current patch | 375 passed,14.14s,exit0 |
| Full PC | existing unchanged runner with batch observation | post-fix run40549;1357collected;73overlay files and recorded identity fields unchanged | 1282passed43skipped1xfailed,1183.59s,exit0; no vehicle qualification |
| Independent review | read-only scoped reviewer | both axes and five fault/accounting cases | 0 Critical/Important/Minor; fresh1test/10subtests PASS |
| Lint / whitespace | Ruff / git diff --check | final source | PASS; initial10B023 findings fixed with explicit closure captures, no ignores |
| Replay vs baseline | not applicable to counter repair | no replay launched | no qualification claim |
| Simulation / closed loop | not run | no plant/input changes | prior gates unchanged |
| Shadow | real offline scheduler, controlled native-boundary faults | no candidate transport/output authority | offline only; no device shadow qualification |

## Handoff

- Expected effect: previously silent buffered-result loss counted exactly once.
- Actual vehicle validation, calibrated plant, continuous shadow and active rollback
  remain incomplete. Existing acceptance and frozen evidence are unchanged.
- Focused GREEN:18tests/45subtests,3.11s,exit0 (including unchanged lateral/longitudinal
  shadow tests). Final package/affected results above follow test closure cleanup.
- shadow.py SHA256:5be3d1e58e22724c68bacbe0cf3ff8fcb7b45fb8fedce767c90948afc9dbb099.
- test_shadow_accounting.py SHA256:fad53132725c039e981cada847062a89faeb1390a90ce4bb0240c9b6e8b612bd.
- Review excludes unrelated preserved dirty work, whole-PC execution, supervisor
  qualification, empirical/vehicle stages and overall STEP8–10 completion. Parent
  owns whole-PC verification; all real-stage prerequisites remain unchanged.
- Post-fix full-PC verification passed; final Ruff and diff whitespace rechecked PASS.
  No commit/PR created. Documentation updated after the source-after snapshot.
