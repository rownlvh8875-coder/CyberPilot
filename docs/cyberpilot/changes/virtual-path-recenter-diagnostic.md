# Virtual path recenter diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: implemented and software-verified for feature-branch publication; vehicle qualification remains not run.
- Purpose and concrete scenario: separate model-path lateral bias from path-shape
  continuity without changing planner, controller or vehicle behavior. Two virtual
  candidates are descriptive only: exact model-lane-center replacement, and a
  shape-preserving constant lateral mean shift. A stateless two-frame transition
  diagnostic then attributes mean-shift changes to lane-center motion, path motion,
  shared-station geometry and horizon composition.
- Scope, exclusions and vehicle applicability: offline geometry transforms only.
  There is no runtime caller, log loader, optimizer, tune selector, profile,
  Params/CAN/device write, planner/controlsd hook or actuator output. The result is
  not vehicle-specific qualification and applies only to already-observed
  PathQualityInput geometry.
- CyberPilot branch / baseline SHA / candidate SHA or uncommitted patch identity:
  `feature/cyber-autotune`, baseline `245e4b7c58eb5d574ab6c0868398baa7647c6136`;
  candidate is this change set; exact commit identity is recorded by Git history.

## Original references

- Source repository URL / verified branch / exact commit SHA:
  https://github.com/rownlvh8875-coder/CyberPilot,
  `feature/cyber-autotune` at the baseline above.
- Source files, symbols and license / attribution requirements:
  `openpilot/selfdrive/controls/lib/cyber_lateral/path_observer.py`,
  `PathQualityInput`, `PathQualityObservation`, `observe_path_quality`;
  repository MIT attribution remains unchanged.
- Traced callers → input data / state → algorithm → outputs / consumers:
  caller-owned PathQualityInput → existing fail-closed path-quality observation →
  immutable virtual geometry candidate and descriptive curvature metrics. Current
  repository search shows no production/runtime consumer.
- Relevant submodule SHAs, model identity and external dependencies:
  no submodule or model change. Existing pins remain unchanged, including
  opendbc `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.
- Adoption decision: reimplement only the bounded diagnostic math around the
  existing observer. No external fork code is copied and no runtime path is
  adapted.

## Changes and expected effect

- Added `openpilot/tools/cyber_autotune/virtual_path_recenter.py`:
  - exact model-lane-center virtual candidate;
  - shape-preserving constant lateral mean-shift candidate;
  - exact two-frame mean-shift attribution into lane-center, path,
    shared-station and horizon-composition components, including full-frame and
    common-station left/right lane-boundary motion plus explicit station-axis-change
    reporting;
  - stable mean/RMSE and three-point spatial-curvature diagnostics;
  - fail-closed handling for invalid geometry, lane-change/maneuver state,
    insufficient common stations,
    derived numeric failure and mean-shift candidates leaving the observed lane
    envelope;
  - immutable outputs hard-code `NOT_READY`,
    `REAL_VEHICLE_UNVERIFIED`, `VEHICLE_ACTIVATION_BLOCKED` and
    `vehicle_activation_allowed=False`.
- Added `openpilot/tools/cyber_autotune/tests/test_virtual_path_recenter.py`
  for coordinate-convention independence, curvature geometry, station-normalized
  curvature change, fail-closed behavior, immutability, mean-shift properties and
  exact transition attribution.
- Exact-lane-center replacement is retained as a failed-hypothesis diagnostic:
  private offline evaluation found that replacing the full path shape with model
  lane-center geometry can worsen spatial continuity. It is not a proposed runtime
  behavior.
- Mean shift changes every lateral path sample by one constant within a frame, so
  same-frame spatial curvature is expected to remain invariant apart from floating
  point roundoff while the frame mean model-relative lane-center bias is removed.
  Private temporal diagnostics remain outside the repository and show that
  frame-to-frame shift stability is not yet sufficient for runtime use. Exact
  private decomposition further shows that large jumps persist with a fixed
  horizon and high lane confidence, and are more often associated with coherent
  ego-lane-center geometry motion than with horizon composition alone.
- Constants / parameters: no performance thresholds or vehicle tune constants are
  introduced. The only state/status literals are non-authoritative safety/readiness
  labels.
- State initialization, reset, delay assumptions and fallback: functions are
  stateless and deterministic. Transition attribution compares exactly two
  caller-owned inputs and retains no history. Invalid observations return a blocked
  immutable result; there is no retained fallback state and no temporal filtering.
- Safety boundaries: confirmed unaffected. No panda/opendbc safety code, actuator
  limits, driver monitoring, engagement logic, CAN permissions, controller output,
  Params or profile state is imported or modified.
- Upstream synchronization and maintenance: one independent offline module and one
  test module; no schema, build-system, submodule, LFS or model asset change.

## Regression risk and acceptance

- Risks: numeric overflow/degenerate geometry, mirrored coordinate convention,
  irregular or non-overlapping station axes, accidental mutation of source data,
  mean-shift candidate leaving the lane envelope, or later misuse of a descriptive
  candidate/transition attribution as an accepted control path.
- Baseline comparison and predeclared acceptance:
  - all candidate outputs remain immutable and vehicle authority false;
  - invalid/lane-change geometry fails closed;
  - constant translation preserves same-frame curvature RMSE, curvature jump and
    station-normalized spatial curvature-change metrics to numerical precision;
  - transition attribution satisfies the exact full-frame identity
    `delta_shift = lane_center_component + path_component`, separates shared
    stations from horizon composition, and fails closed without at least three
    common stations;
  - existing path observer, Cyber AutoTune and controls tests remain green;
  - Ruff, whitespace, publication/privacy audit, SCons and default verified-public
    fixture suite pass before commit/push;
  - repository search continues to show no runtime caller.
- Holdout / scenario coverage and input provenance: unit tests use synthetic public
  fixtures only. User-owned driving-log probes are private descriptive evidence and
  are not an acceptance gate, holdout mutation or vehicle qualification source.
- Rollback: stop using/revert this module; no vehicle configuration is changed.
- Required reviewer / promotion authority: software review and publication gates
  may permit a feature-branch commit only. Replay → calibrated simulation → shadow
  evidence remains required before any future vehicle application.

## Validation method and actual results

| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Targeted unit | supported `tools/test_runner.py -j2` on virtual recenter + path observer tests | final executable source | PASS: 27/27 |
| Ruff / whitespace / runtime-call-path | targeted Ruff, staged diff check, repository caller search | final executable source | PASS; no production/runtime caller found |
| AutoTune + controls regression | supported runner on Cyber AutoTune + controls | final executable source | PASS: 869/869 in 223.77 s |
| Native build | repository venv first on PATH, `scons -u -j2` | final executable source/submodule pins | PASS, exit 0; existing non-fatal PWD warning only |
| Default verified-public fixture suite | supported default runner, two workers, repository venv first on PATH | final executable source/public fixture environment | PASS: 1,776 passed / 42 skipped / 1 xfailed in 320.94 s |
| Publication/privacy | repository publication checker against feature-branch remote base | three final changed files | PASS: 3 files / 0 findings |
| Independent source review | staged diagnostic module + tests + existing `PathQualityInput` validation contracts | final executable source | APPROVE; Critical / Important / Minor findings: none |
| Replay vs baseline | qualified replay input | not run | NOT_RUN; diagnostic does not authorize vehicle use |
| Simulation / closed loop | calibrated vehicle simulation | not run | NOT_RUN |
| Shadow (candidate cannot actuate) | device shadow isolation | not run | NOT_RUN |

## Handoff

- Verified effect vs expected effect: software checks confirm the bounded,
  non-authoritative same-frame geometry and two-frame attribution properties.
  Private evidence rejects the exact-lane-center runtime hypothesis and keeps mean
  shift descriptive only because temporal shift discontinuities remain. Private
  decomposition shows that large shifts persist at fixed station axes and high lane
  confidence, are not explained by calibration-update timing alone, and occur with
  substantial lane/path shape motion. Exact-frame qcamera overlays for the selected
  curve windows reproduce the model-relative separation between the model path and
  the model lane center; because both originate from the same model, this is only a
  projection/consistency check and not independent lane-center ground truth.
  Road-edge comparison also shows strong
  same-frame co-motion with ego-lane-center translation in the bounded high-confidence
  subset. Independent physical-motion context and corrected exact-qcamera-frame
  phase-correlation probes do not show a strong enough association to attribute the
  residual jumps to ego motion or raw image translation. The qcamera probe remains
  perspective/depth-sensitive and is not independent lane-center ground truth, so
  these associations are descriptive rather than causal proof of a model artifact.
- Failed, blocked or not-run checks and missing inputs: qualified replay,
  calibrated simulation and device shadow are not run. They are not inferred from
  local software tests.
- Remaining risks and next verification: keep the candidate offline. Independent
  ego/image-motion probes are now complete but do not supply lane-center ground truth;
  qualified replay, calibrated simulation, device shadow, or another independent
  geometric reference is still required before any representation-level attribution
  can be promoted. Do not introduce smoothing, parameter search or a runtime hook from
  the current evidence.
- Commit / PR references: this change set is committed on the feature branch; PR not created here.
- Vehicle application decision:
  `NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED`.
