# Cyber Lateral path observer coordinate convention fix

## Identity and purpose

- Feature / area: Cyber Lateral diagnostic observation.
- Status: implemented and software verification gates complete; vehicle qualification remains NOT_RUN/BLOCKED.
- Purpose: allow the observer-only lane/path diagnostic to accept the model coordinate ordering actually emitted by `modelV2`, without changing any path, curvature, controller or actuator output.
- Scope: `PathQualityInput` geometry validation and one regression test module with two coordinate cases. No AutoTune candidate, lane offset command, planner mutation, profile activation or vehicle write.
- Branch / baseline: `feature/cyber-autotune` at `2bf57f44f42d9a2d38cb86ad88bdbae29bfd383f`.

## Original references

- Repository: https://github.com/rownlvh8875-coder/CyberPilot, baseline above, MIT root license.
- Existing implementation: `openpilot/selfdrive/controls/lib/cyber_lateral/path_observer.py` and the `Controls._cyber_lateral_model_observations` caller in `controlsd.py`.
- The observer receives semantic left/right lane boundaries and optional semantic left/right road edges. Its output remains `PathQualityObservation`; no cereal or actuator interface changes.
- Pinned opendbc remains `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.
- A private local user-log probe exposed the mismatch, but no route identifiers, raw messages or derived private evidence are included in this public tree.

## Changes and expected effect

The previous geometry check encoded one y-axis sign convention: left lane y had to be greater than right lane y and left road edge had to be numerically greater than the left lane. Real model output can use the mirrored numeric convention while preserving the same semantic left/right ordering.

The observer now:
- requires left/right lane ordering to remain nonzero and consistent across stations;
- when both road edges are available, requires their semantic ordering to match the lane ordering;
- computes lane width as absolute left/right separation;
- checks the desired path against the numerical interval between boundaries, independent of axis sign;
- checks each road edge as farther outward from the lane center on the same semantic side and reports absolute clearance.

No automatic axis flip, lane swap, threshold, path correction or fallback is introduced. A semantic boundary crossing, inconsistent ordering, path outside lane bounds or road edge on the wrong side still fails closed.

The added regression test uses the mirrored coordinate convention and verifies that mirroring the complete y-axis preserves lane width and edge clearance while reversing only the signed model-to-center bias.

## Regression risk and acceptance

Primary risk is accidentally accepting truly crossed boundaries while becoming sign-invariant. Acceptance therefore requires:
- new mirrored-coordinate tests RED before the production change and GREEN afterward;
- all pre-existing path-observer tests remain green, including `crossed_lane_boundaries` and invalid road-edge ordering;
- existing Cyber Lateral integration/native-parity tests remain green;
- no change to native lateral tuple, control state, controller state or actuator publication;
- Ruff, affected controls tests, AutoTune+controls regression, SCons, default suite, privacy scan and independent source review before publication.

Rollback is reverting this observer/test/document increment. No active configuration or vehicle state exists to roll back.

## Validation method and actual results

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Regression RED | new model-coordinate unittest | baseline observer | 2/2 expected failures; first reason `crossed_lane_boundaries` |
| Regression GREEN | same unittest after minimal observer change | uncommitted patch | 2/2 passed |
| Observer / metrics / integration | four unittest modules including the new coordinate test | final executable patch | PASS: 30/30, exit0, 0.091 s |
| AutoTune + controls | supported `tools/test_runner.py ... -j 2` | final executable patch | PASS: 840/840, 222.02 s |
| Ruff / whitespace / publication audit | changed Python + diff/publication checks | final executable patch | PASS; publication check 3 files, 0 findings |
| SCons | `.venv/bin` first on PATH, `scons -u -j2` | final executable patch | PASS, exit0; existing PWD warning retained |
| Default verified-public-fixture suite | unchanged default runner with verified public fixture and `.venv/bin` on PATH | final executable patch | PASS: 1747 passed / 42 skipped / 1 xfailed, exit0, 313.65 s; supervisor 314.50 s; source/fixture unchanged |
| Independent source review | embedded changed/source-call-path review | final executable patch | APPROVE; Critical/Important none. One stale-document Minor resolved by this closeout; optional coverage remains non-blocking |
| Private log probe | existing local user-owned rlogs | not public evidence | confirms diagnostic is now executable; separate private report only |
| Qualified replay / calibrated simulation / device shadow | separate vehicle evidence | none | NOT_RUN |

The first source-identical default-suite attempt is retained as an environment
failure rather than hidden: 1746 passed / 42 skipped / 1 xfailed / 1 failed.
The unchanged failure was `loggerd.TestLoggerd.test_record_audio_0`; diagnosis
showed the shell could not find the repository venv's `ffprobe`. The isolated
test passed after putting `.venv/bin` on PATH, with no source/test change. The
fresh final full-suite result above used that explicit environment and completed
normally.

## Handoff

Verified so far: the optional diagnostic no longer rejects a mirrored model y-axis solely because of numerical sign, while legacy coordinate fixtures and fail-closed cases remain valid.

This does not prove lane-center ground truth: model path and model lane lines share a model source. It only restores the intended observer so path-relative bias can be compared with independent controller-tracking diagnostics. It does not modify perception, planner output, steering gains or safety limits.

No new driving logs were requested; no CAN/device/profile/Params write or road test was performed.
`NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED` remain.
