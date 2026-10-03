# Cyber AutoTune offline structural-preview job

## Identity and purpose

- Area: AutoTune offline proposal/audit integration. Status: implemented/reviewed; full-PC verification incomplete.
- Connect existing grid preview and immutable archive, including interruption/restart and explicit retry.
- Scope: trusted-local Linux artifact publication only, not actual optimization, control or vehicle qualification.
- Branch feature/cyber-autotune, HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b plus uncommitted files.

## Original references

- CyberPilot https://github.com/rownlvh8875-coder/CyberPilot at above HEAD; local reviewed
  profiles.py/search.py/audit.py/archive_codec.py/archive.py overlay reused, not fork code copied.
- New original orchestration follows existing repository license. No new third-party dependencies.
- Explicit caller -> pure template/grid validation -> immutable STARTED -> all proposals ->
  STRUCTURAL_PREVIEW terminal -> exact reload checks -> immutable aggregate result.
- Existing opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 unchanged/not invoked.
  Model and physical plant not applicable: no driving-data reader or evaluator.

## Changes and expected effect

- Added preview_job.py and tests/test_preview_job.py. No upstream integration or control consumer.
- Deterministic job identity binds exact serialized template/grid, software/configuration and evaluator digest.
- All artifacts revalidated; any incomplete/error result has no successful subset of profiles.
- No new vehicle constants. Existing finite grid budget and archive size/platform rules reused.
- No control state or delay. Failed storage retains partial artifacts for explicit idempotent retry;
  completed history with missing/corrupt proposals blocks without repair. Unexpected terminal preserved.
- Existing safety, limits, override and online writers untouched. No runtime/evaluation authority granted.
- Maintenance risk: small offline module depends on existing exact codec/audit contracts.

## Regression risk and acceptance

- Risks: false completion from terminal alone, silent partial success, identity rebinding,
  failed persistence acknowledged, conflicting bytes overwriting past history.
- Acceptance: every planned malformed/interruption/restart/concurrency test passes; prior tests unchanged.
- Inputs: synthetic unit fixtures only, not reviewed real vehicle parameters. No holdout/raw logs.
- Rollback: remove use of optional offline API; no active configuration ever changed. Existing artifacts retained.
- Fresh read-only review required before component completion. No receipt permits vehicle promotion.

## Validation method and actual results

| Check | Method | Current result / limit |
| --- | --- | --- |
| Focused | Python3.12 pytest tests/test_preview_job.py on Ubuntu24.04 | missing-module RED ->10 tests23subtests PASS |
| Full package/controls | pytest package and tools/test_runner.py affected targets |197 package603subtests PASS;329 affected PASS9.06s exit0 |
| Lint/diff | Ruff, git diff --check | PASS |
| Independent review | read-only file review, focused tests and tempdir probes |0Critical/0Important/0Minor;10 real fsync faults and competing-terminal interleavings fail closed |
| Replay | no evaluator or driving input | NOT RUN |
| Closed loop | no plant integration | NOT RUN |
| Shadow/vehicle | no runtime consumer | NOT RUN / not authorized |

## Handoff

- Structural artifact integration verified by package/affected tests and independent review.
- Full-PC1301 run33967 predates this module; interrupted1200s exit124. Current run15382
  uses2400s resource budget; no assertion/discovery/cache change and no full-suite PASS yet.
- Storage failures may leave STARTED-only or no journal; no guarantee to log failure onto failed storage.
- Digests/confidence are assertions, not authentication, empirical improvement or physical calibration.
- Hardware power loss/remote storage/hostile same-UID changes remain outside qualification;
  multi-file rollback is not promised. Partial files are retained for explicit retry.
- Commit/PR: none. STEP8–10 remains PARTIAL / NOT_READY; no active-profile/Params/CAN writer.
