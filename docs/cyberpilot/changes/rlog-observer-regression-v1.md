# F-46 Recorded-command Replay / Input-quality Observer V1

## Identity and purpose

- Cyber Validation / Lateral diagnostic tool. Local implementation only.
- Baseline HEAD: `df8fc8b9d4094f03d8a426039bbe2d3c7b82759c`.
- Dataset: private F41-C01, exactly one existing file, 11,452,764 bytes,
  SHA256 `9db34f2698d6857c2f4c07298b973b3f731c76b0b5441f2a54159edcfa43d5a5`.
- Recorded Source: `a559fcd971ccaa5a87befb8ec080f59a2966325b`;
  schema/source manifest `96ec3bc609beac9fba027d5adf83ce72c2d7d70013e00e878c14e9da996dfa94`.
- Current Source is not the recorded Source. No controller/state reconstruction.

## Original references

F45 proposal and sealed F42/F43/F43R evidence; same repository's F42
`f42_common.py` bounded zstd and Cap'n Proto framing algorithm.
Project license/attribution remains unchanged.
Only pycapnp 2.1.0 and zstandard 0.25.0 from the existing environment are needed.
The reader loads the pinned historical schema in a child process.
The parent uses immutable primitive records; neither imports current cereal,
controlsd, a controller, Params, CAN, messaging, or a vehicle interface.

## Changes and expected effect

Exactly three new files:

- `tools/cyberpilot/rlog_observer_regression_v1.py`: pinned private reader,
  original ordinal/timestamp/scalar tape, pure quality observer, canonical summary.
- `tools/cyberpilot/tests/test_rlog_observer_regression_v1.py`: synthetic-only tests.
- This change record. No existing file or workflow changes.

The raw input and all22 schema/source members are verified before body decoding.
No QLOG fallback, network fetching, Source pin replacement, or runtime hook.
Resource bounds reuse F42: 512MiB decoded bytes, 64KiB compressed chunks,
maximum512 Cap'n Proto segments. They are analysis bounds, not driving limits.

Tape fields are allowlisted from carControl, controlsState, carState, carOutput,
selfdriveState and modelV2. Raw GPS/CAN/video/VIN/owner fields are not projected.
Reader order is the original file ordinal; no timestamp sorting.
Per-service duplicate/reversal and mixed-service archive time errors are distinct.
An archive time error is reported and retained; replay fidelity does not mean
all input timing is qualified. File order is not original SubMaster receive order.

Command rate uses actual adjacent positive timestamp differences and no invented
initial history; active transitions and invalid histories break the rate series.
The observer creates no command. A recorded inactive command is retained as fact.
Override is counted on carState, not fabricated as an exactly bound command flag.
The first recorded sample is not a reconstructed original controller state.
Unknown physical freshness, source-consumption binding, controller limits and
staleness remain UNQUALIFIED. No age threshold is accepted by the real CLI.
A pure function can test explicitly declared synthetic message-age policies,
which never qualify actual sensor freshness.

## Regression risk and acceptance

Reject wrong/missing raw input, source/manifest/schema mismatch, cross-binding,
unexpected projection keys, ordinal changes and unsafe output locations.
Detect invalid/nonfinite/missing, per-service duplicate/reversed time and file
archive inversions. Never fill gaps, replace missing fields with zero, or
synthesize Native results. Explicitly report incomplete recorded controller state.

Outputs must be outside the repository and /mnt and outside common sync paths.
Run folders are new, mode0700; files are exclusive, mode0600.
Existing output folders are never changed. Storage-error responses use fixed
codes without private-path tracebacks. No output or raw file is auto-deleted.
Private tape must not be included in published evidence.

## Validation method and actual results

Local synthetic suite:39 tests PASS; first red/negative failures retained outside
the repository. Existing5 F45 API regressions are checked separately.
Scoped Ruff/Ty/codespell/compile pass; final run identities and any remaining
checks are in the external F46 report/manifest, not an updated historical receipt.

The first real probe read86,400 messages/57 services and6,000 recorded commands.
It reported0 per-service reversals/duplicates, but4,450 selected mixed-service
archive timestamp inversions. These are not sorted away or called Deadline misses.
Final independent runs/oracle are separately identified in the external report.

Future/actual invocation (paths refer only to previously authorized local data):

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B tools/cyberpilot/rlog_observer_regression_v1.py \
  --raw "$PRIVATE_RLOG" --source-root "$RECORDED_SOURCE_CAPSULE" \
  --source-manifest "$RECORDED_SOURCE_MANIFEST" --output "$NEW_PRIVATE_OUTPUT"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B tools/test_runner.py \
  tools/cyberpilot/tests/test_rlog_observer_regression_v1.py
```

The real CLI is pinned to F41-C01. It has no source/hash override or actuation mode.
Private output: recorded_commands.jsonl, reader.json, summary.json and result hashes.
Independent new processes must produce identical canonical output bytes.
A summary PASS means recorded-command fidelity / observer software checks,
not complete Controller replay or qualified sensor timing.

## Handoff and limits

No existing Full CI5960/Baseline5927 ID or Required Check is changed.
Public tests use synthetic fixtures only; private RLOG is not added to Git.
No Native exact replay, internal-state reconstruction, counterfactual trajectory,
actual position/heading error, physical actuator delay, tracking improvement,
vehicle safety or target100Hz Deadline is qualified.

Rollback is a separately approved removal of only these three untracked files;
do not reset/clean/stash or remove logs/evidence. No rollback is executed here.
No commit, push, CI, SSH, runtime apply, CAN/Params write or vehicle permission.

D2 PERFORMANCE_NOT_EVALUATED / F19_LEGACY_UNRESOLVED / RUNTIME_NO_GO.
Private E2 NOT_AUTHORIZED / HOLDOUT CLOSED / Vehicle authority NONE.
selected_candidate=null / selected_policy=null / F-7/F-9 effective=false.
