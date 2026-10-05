# Cyber Lateral path/tracking timeline analysis

## Identity and purpose

- Feature / area: Cyber Lateral offline diagnostic analysis.
- Status: implemented; final software gates and independent source review pass; vehicle qualification remains NOT_RUN/BLOCKED.
- Purpose: preserve the time relationship between model-path bias, requested
  curvature and curvature-tracking residual without collapsing them into an
  automatic root-cause label.
- Scope: immutable descriptive timeline and direction-bucket summaries only.
  No log loader, lag search, threshold, optimizer, planner/controller/actuator
  mutation, Params/profile/CAN/device write or vehicle-specific tune.
- Branch / baseline: `feature/cyber-autotune` at
  `f490f3a1360a0f9bc527220949b7c6e1baac8887`.

## Original references

- Repository: https://github.com/rownlvh8875-coder/CyberPilot at the baseline
  above; MIT root license.
- Reused diagnostics:
  `PathTrackingObservation`, `PathQualityObservation`,
  `LateralContext.desired_curvature_1pm` and
  `LateralContext.current_curvature_1pm`.
- Reused metric policy: existing Cyber Lateral code treats alignment as
  caller-owned and does not search a diagnostic lag. This increment keeps the
  same rule.
- No new dependency, cereal field, controller callback or runtime message is
  introduced.

## Changes and expected effect

- Added `openpilot/tools/cyber_autotune/path_tracking_timeline.py`:
  - immutable input, point, bucket and summary records;
  - path-reference and tracking timestamps remain independent;
  - path time must increase strictly; tracking time may repeat but may not
    reverse, matching the asynchronous observation contract;
  - the residual remains `current_curvature_1pm - desired_curvature_1pm`;
  - non-finite inputs or derived residuals fail closed;
  - positive, negative and zero requested-curvature samples are summarized
    separately;
  - maximum-absolute model-bias and tracking-residual timestamps are reported
    separately, plus their descriptive time difference; equal-magnitude peak
    ties deterministically keep the first input occurrence;
  - repeated tracking timestamps are retained as separate path-associated
    samples and therefore receive one aggregate weight per association;
    `unique_tracking_time_count` reports the distinct tracking timestamps
    without deduplicating aggregate statistics.
- Added
  `openpilot/tools/cyber_autotune/tests/test_path_tracking_timeline.py` for
  source-time separation, bucket summaries, time-axis rejection, numeric
  overflow rejection, immutability and determinism.
- Peak ordering is explicitly descriptive. It is not a causal onset detector,
  alignment correction or proof that one subsystem caused the other.
- Model-to-lane-center bias still uses model path and model lane geometry; it is
  not independent lane-center truth.

## Private evidence separation

A local-only adapter outside the repository can reconstruct timeline samples
from user-owned development logs by combining model geometry with logged
curvature state. Raw paths, route identifiers, message payloads and derived
private values remain outside the public tree. Private results are diagnostic
only and do not change qualification, frozen evaluation evidence or vehicle
authority.

## Regression risk and acceptance

Primary risks are silently treating asynchronous service times as one clock,
overweighting repeated tracking timestamps, overflow in derived statistics, or
turning descriptive peak order into causal classification.

Predeclared acceptance:
- test module RED before implementation and GREEN afterward;
- reversed path/tracking time fails closed while repeated tracking time remains
  allowed;
- numeric and subtraction overflow fail closed;
- existing path/tracking observer and Cyber Lateral integration remain green;
- AutoTune+controls, Ruff, whitespace, privacy, SCons, verified-public-fixture
  default suite and independent source review pass before publication.

No tuning/performance threshold is introduced. Failure to explain a private
driving event is an UNKNOWN diagnostic result, not permission to tune.

## Validation method and actual results

| Check / stage | Method | Actual result and limits |
| --- | --- | --- |
| Test-first RED | new timeline unittest before module creation | Historical tool chronology confirms the five-test file was written and RED run before production module creation; full RED stdout was omitted from retained tool history by its output-size cap |
| Initial feature GREEN | same unittest after minimal module | PASS: 5/5 before independent review |
| Review fix RED -> GREEN | cancellation remainder regression | RED: representable mean returned 0; GREEN after mean algorithm change |
| Boundary follow-up RED -> GREEN | representable subnormal mean regression | RED: representable minimum subnormal returned 0; GREEN after exact binary-rational mean |
| Exception-contract RED -> GREEN | oversized-integer curvature residual | RED: `OverflowError`; GREEN: normalized fail-closed `ValueError` |
| Current feature module | seven timeline tests | PASS: 7/7 |
| Pre-review software gates | targeted / AutoTune+controls / Ruff / SCons / default suite | Historical PASS results retained but invalidated as final evidence by subsequent numeric-source changes |
| Private development-log probe | local-only adapter, not public evidence | Final-code repeat PASS: two fresh reports byte-identical. Raw path, route identifier and private values remain outside the public tree |
| Final targeted / AutoTune+controls | repository supported commands | PASS: targeted 36/36; AutoTune+controls 852/852 in 219.79 s |
| Final Ruff / whitespace / privacy / SCons | changed-source and build checks | PASS; publication check 3 files / 0 findings; SCons exit0 with existing non-fatal PWD warning |
| Final default suite | verified public fixture environment | PASS: 1,759 passed / 42 skipped / 1 xfailed in 316.26 s; supervisor PASS, exit 0, source and fixture unchanged |
| Independent review | source-only review | APPROVE after cancellation/subnormal/oversized-integer fixes; Critical / Important / Minor findings: none |
| Qualified replay / calibrated simulation / device shadow | separate evidence | NOT_RUN |

## Handoff

The timeline can now preserve where the largest model-reference bias and
tracking residual occur on their own source clocks while keeping requested
curvature visible for direction stratification. Interpretation must remain
descriptive until independent lane truth or separately qualified evidence is
available.

No new driving logs were requested. No vehicle/device/profile/CAN/Params write
or road test was performed.

`NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED` remain.
