# Descriptive development speed coverage

## Identity and purpose

Cyber Validation / AutoTune; implemented and reviewed for offline description only.
Baseline `55e7c89ce5ff89db463210d82c0b726afa3b075f`, feature/cyber-autotune.
Measure existing development driving coverage before considering speed-dependent
tuning. This is descriptive analysis, not learner excitation or candidate admission.
No controller, tune, Params, CAN, estimator, safety, holdout or reference changes.

## Original references

Original Cyber implementation; no fork algorithm/constants copied. Existing
`coverage.py` covers reviewed scenario labels; this separate pure module counts
recorded speeds without claiming independent samples. Caller supplies exact-schema
carState valid/vEgo/logMonoTime observations; no cereal dependency in this module.
No submodule/model/dependency change. Private source-schema decoding and manifest
authority stay in a local, unpublished harness, not in a public driving-log CLI.

## Changes and expected effect

Add `openpilot/tools/cyber_autotune/speed_coverage.py` and its unit tests.
Stream each segment independently into a fixed histogram: 1 m/s descriptive
resolution, bins [0,1) through [59,60), plus >=60 overflow. These are neither tuning
knots nor an accepted vehicle operating domain. Negative/nonfinite speeds and
invalid events are excluded and counted, never clamped. Duplicate/backward times
are excluded and counted. No sorting that hides time resets. Clock resets break
continuity; no cross-segment interval or missing-time interpolation.
Adjacent valid forward observations no more than 200 ms apart contribute observed
interval duration. The 200 ms diagnostic gap marker is not a learner/test/vehicle
limit. Count gaps and min/max positive inter-message intervals explicitly.
Bound per-segment processing to two million observations (resource guard only).
Summarize pooled sample proportions and equal-weight nonempty-route proportions
separately; report empty routes and quality defects rather than asserting sufficiency.
Never expose sample times/route identities or imply confidence/promotion authority.

## Regression risk and acceptance

Risks: dropping bad observations silently, duplicates inflating sample counts,
bridging missing data, sample weighting mislabeled route weighting, empty-input
success, private output. Test hand-calculated histograms/durations/weights, input
faults, empty data, segment resets and deterministic serialization. Existing labels,
statistics, acceptance criteria and synthetic experiment results stay unchanged.
Public utility has no file/vehicle authority; private harness must bind allowlist,
exact schemas/source, roots/identity and an independently reviewed small fixed pilot
before opening logs. Separate retrospective evaluation routes are not pilot inputs.
Rollback is removal of this unreferenced offline utility; runtime remains stock.
Independent reviewer required before private pilot. No vehicle promotion authority.

## Validation method and actual results

Planned: test-first targeted checks; AutoTune/controls, default runner, Ruff,
SCons, deterministic repetitions, publication audit and independent code review.
Private pilot: at most first two declared segments of each of three development
routes ordered by existing route hash, selected before examining speed outcomes.
No fallback to other routes if a pilot fails. Source/identity failure is BLOCKED.
Record complete pilot scope separately from full-route/full-universe coverage.
Actual bounded results:

- Eight pure unit tests passed; six private-harness tests passed. Both new modules
  first failed due to missing implementation. One test fixture import was corrected
  before establishing the private harness's missing-module failure.
- Independent review: no Critical/Important findings; one Minor identity/path
  defense gap was reproduced with an authorized label pointing to a protected
  segment. Strict canonical path binding was added, failing then passing its test.
  Existing frozen intake already had matching identities; no authority was changed.
- Two fresh fixed-pilot runs exited zero with identical aggregate bytes. Selected
  six segments contained 36,333 observations, 34,878 accepted and 1,455 invalid;
  zero duplicate/backward timestamps or gaps over the descriptive marker. Quality
  remains `DESCRIPTIVE_INCOMPLETE`, not a clean-data or candidate acceptance.
- Accepted speed range: 0 to 13.60915470123291 m/s; no accepted samples >=15 m/s.
  This beginning-of-route pilot is not representative of full routes/universe.
  Invalid reasons were not subdivided in this version; do not infer their cause.
- Observed adjacent-valid duration: 348.287469480 seconds. Positive inter-message
  intervals: 2,754,808 to 42,934,389 ns. These are not independent sample counts or
  full-trip dwell time. No cross-segment duration was fabricated.
- Ruff, SCons and zero-finding three-file publication precheck passed. Final
  regression/default-runner and publication closeout are recorded below.

Pilot report SHA-256:
`63f2075bb2bac86f9fc30664766761bdd709908fdbcf8f81bcf5cfae6c3f3c61`.
Module SHA-256: `5419dc2c4a98cb8f7212a3f339389d4038e7256049f625659e1cf29da11dd8b0`.
Test SHA-256: `2caf62235800603396e2302277f996d834b658b9a8bbbb20b501a2ddc023ef57`.
The private harness/input/schema bindings stay in local evidence, not public source.

Replay, simulation, shadow and vehicle qualification are not exercised by this
descriptive utility and remain unverified. No new driving data requested.

Final AutoTune+controls: 669 passed, 226.37 s, actual exit 0. An earlier run printed
669 passed but an outer shell exit-capture quoting error prevented a valid terminal
receipt; it was replaced by this complete unchanged rerun, not test relaxation.
Final default runner: 1,576 passed / 43 skipped / 1 xfailed, 373.77 s, actual exit 0.
Supervisor: no timeout, code/overlay/submodules and verified public fixture unchanged.
Receipt SHA-256: `de7074aaf980418cbcb23e839aabc5ff098fc6027c9df3c5f5d6b3f835f84e80`.
Compared with the prior 42 skips, this run additionally reports a TestOnroad
setUpClass skip under the existing comma-hardware-on-PC guard. No test, collection,
guard or ignore was changed. Hardware execution remains NOT_RUN; do not interpret
the software suite as an onroad test. Eight new pure tests account for the passed
count increase. Ruff/SCons and deterministic/private-output privacy checks pass.
This final documentation-only closeout follows the full-suite receipt; executable
and test hashes above remain identical to the verified overlay.

## Handoff

Expected effect is reproducible descriptive evidence, not an improved controller.
No commit/push until required gates; no private harness/data in publication.
REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED / NOT_READY remain unchanged.
