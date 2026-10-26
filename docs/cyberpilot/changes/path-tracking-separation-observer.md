# Cyber Lateral path/tracking separation observer

## Identity and purpose

- Feature / area: Cyber Lateral diagnostic observation.
- Status: implemented and software verification gates complete; vehicle qualification remains NOT_RUN/BLOCKED.
- Purpose and concrete scenario: distinguish a model path that is offset from the observed lane center from a native controller that does not track the requested curvature, using values captured in the same accepted `LateralContext`.
- Scope, exclusions and vehicle applicability: observer-only. No automatic root-cause classification, threshold, planner/path/curvature mutation, steering-gain change, actuator command, Params/profile/CAN/device write or vehicle-specific tune.
- CyberPilot branch / baseline SHA / candidate SHA or uncommitted patch identity: `feature/cyber-autotune`, baseline `1ec5bb234dc8cf822b404ca2c5a58a356515bf72`, uncommitted patch.

## Original references

- Source repository: https://github.com/rownlvh8875-coder/CyberPilot, exact baseline above, MIT root license.
- Existing source: `path_observer.py::observe_path_quality`, `types.py::LateralContext`, `coordinator.py::CyberLateralCoordinator.observe`, and the `Controls._cyber_lateral_model_observations` call path.
- Traced data flow: checked `modelV2` lane/path geometry -> `PathQualityObservation.model_to_lane_center_bias_m`; checked control-state context -> requested/current curvature -> coordinator observation. The new observer combines only those already captured diagnostic values after native publication.
- Pinned opendbc remains `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`. No new dependency, schema or model field is introduced.
- Adoption decision: reuse existing context and path observer rather than create a log pipeline or new controller metric. This preserves one observation lifecycle and avoids a second source of alignment or delay policy.

## Changes and expected effect

- Added `openpilot/selfdrive/controls/lib/cyber_lateral/path_tracking.py`: immutable `PathTrackingObservation` and fail-closed `observe_path_tracking`.
- Updated `types.py`: `LateralObservation` carries the optional path/tracking diagnostic.
- Updated `coordinator.py`: after normal context admission, attaches the diagnostic from the same context.
- Updated package exports in `cyber_lateral/__init__.py`.
- Added `test_cyber_lateral_path_tracking.py`: same-sample separation, invalid reference/numeric/timestamp behavior and coordinator attachment.
- Expected values are intentionally independent rather than collapsed into one score:
  - model reference bias: `model_to_lane_center_bias_m`, unit m, inherited from valid `PathQualityObservation`;
  - controller tracking residual: `current_curvature_1pm - desired_curvature_1pm`, unit 1/m.
- No numeric dominance threshold or label such as “planner fault” / “controller fault” is introduced. Such a label would require separately reviewed evidence and convention-aware interpretation.
- The diagnostic preserves both `model_mono_time_ns` and `car_state_mono_time_ns`; it does not pretend asynchronous service timestamps are equal.
- Missing/invalid path reference, invalid timestamps or non-finite curvature fail closed and expose no partial bias/error pair.
- Native controller invocation count, native result tuple, controller state and actuator publication are unchanged. The diagnostic is created only inside the existing observe-only path after context admission.

## Regression risk and acceptance

- Primary risks: accidentally feeding diagnostic data back into control, confusing raw model y-axis sign with semantic left/right, emitting a partial pair when one reference is invalid, or breaking existing immutable observation interfaces.
- Baseline: exact native behavior at `1ec5bb234...`.
- Predeclared acceptance: new tests RED because the observer module is absent; GREEN after minimal observer integration; existing Cyber Lateral coordinator/path/integration parity remains exact; no control-path source edit outside the observer/type/coordinator export seam; Ruff/whitespace/privacy, AutoTune+controls, SCons and default suite before publication.
- No performance acceptance threshold is defined in this increment. It creates trustworthy separated measurements, not a steering candidate.
- No new driving logs are requested. Existing private user-log evidence, if later analyzed, remains local and is not publication evidence.
- Rollback: revert the added observer/test/document and small diagnostic type/coordinator wiring. No persistent runtime or vehicle state exists.
- Vehicle promotion authority: none.

## Validation method and actual results

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Test-first RED | new unittest module before production implementation | baseline `1ec5bb234...` | Historical tool chronology confirms test file write and RED run before module creation; four test methods all required the absent module. Full historical RED stdout was omitted from retained tool history by its output-size cap |
| Initial feature GREEN | same unittest after minimal implementation | pre-review patch | PASS: 4/4 |
| Independent review finding | source-only review | pre-review patch | REQUEST_CHANGES: finite curvature inputs could overflow subtraction to non-finite residual |
| Review fix RED -> GREEN | explicit finite-input subtraction-overflow regression | final executable patch | RED: 1/1 failed because `valid=True`; GREEN: 1/1 passed; final feature module PASS: 5/5 |
| Cyber Lateral regression | path/tracking + model-coordinate + path observer + coordinator + integration | final executable patch | PASS: 29/29, exit0, 0.074 s |
| Broad controls / AutoTune | repository supported runner, 2 workers | final executable patch | PASS: 845/845, 219.90 s |
| Ruff / whitespace / privacy | changed-source checks | final executable patch | PASS; publication check 6 files, 0 findings |
| SCons | `.venv/bin` first on PATH, `scons -u -j2` | final executable patch | PASS, exit0; existing PWD warning retained |
| Default suite | verified public fixture environment, `.venv/bin` first on PATH | final executable patch | PASS: 1752 passed / 42 skipped / 1 xfailed, exit0, 313.69 s; supervisor PASS 314.56 s; source/fixture unchanged |
| Final independent review | source-only review after closeout | final patch | APPROVE; Critical/Important/Minor none |
| Qualified replay / calibrated simulation / device shadow | separate evidence stages | none | NOT_RUN |

## Handoff

- Verified so far: one accepted observation can expose model-path bias and curvature-tracking residual as separate immutable values without a threshold or control authority.
- This does not establish independent lane-center ground truth: the path bias still derives from model path and model lane geometry. It also does not by itself prove why a real vehicle hugs the inside/outside lane.
- The next useful analysis after publication is time-series correlation on qualified or explicitly authorized evidence: path bias persistent with low tracking residual points toward the supplied path/reference; low path bias with persistent tracking residual points toward controller/vehicle tracking. Mixed cases remain mixed rather than force-classified.
- Qualified replay, calibrated vehicle simulation and non-actuating device shadow remain NOT_RUN.
- Vehicle decision: `NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED`.
