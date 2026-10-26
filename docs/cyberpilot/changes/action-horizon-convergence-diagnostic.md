# Action-horizon convergence diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: descriptive software diagnostic only; no vehicle qualification or runtime use.
- Purpose: describe whether a caller-supplied local model-path offset from the
  model lane center is moving locally toward zero at a caller-owned action
  horizon.
- Scope: an already-valid RecenterConditionObservation plus two finite geometry
  scalars: path-minus-lane offset and its longitudinal slope.
- Branch / baseline: feature/cyber-autotune from
  22a38fd9da5fe9f903f640593d8e8ea714f03acb.

## Motivation

Private read-only latency-aware analysis of the existing log set found that the
published model action and the bound controls desired curvature were often
closer to local model-path curvature than to local model-lane-center curvature.
However, action-versus-lane curvature excess alone did not cleanly separate
future recenter success from failure.

For the strong turn-inside subset, the much stronger separator was local offset
direction at the action horizon: frames that later recentered were usually
already moving their path-to-lane offset toward zero, while non-recentering
frames usually were not. This motivates a small sign-only primitive for local
convergence, without embedding the private latency estimator, horizon selection,
curve threshold, speed threshold or route evidence.

## Implementation

- Added openpilot/tools/cyber_autotune/action_horizon_convergence.py.
- observe_action_horizon_convergence():
  - consumes an existing DESCRIPTIVE_ONLY RecenterConditionObservation;
  - reuses the existing fail-closed upstream condition validator;
  - accepts finite caller-owned path-minus-lane offset and offset slope;
  - normalizes offset and slope by model-action turn sign for INSIDE / OUTSIDE
    reporting;
  - classifies local convergence by the coordinate-invariant exact rule
    offset * slope < 0;
  - retains CENTER and FLAT as separate exact states;
  - copies the existing recenter outcome only for descriptive comparison;
  - blocks non-finite inputs and derived multiplication overflow.
- No epsilon or magnitude threshold is used.
- The module does not estimate model latency, select an action horizon, derive
  image or model geometry, predict future trajectory, rank candidates, tune
  parameters, generate curvature, or alter control.
- The output is frozen and hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.

## TDD and risk coverage

Synthetic public-safe tests cover:

- turn-inside convergence and divergence;
- turn-outside convergence using the general offset-times-slope rule;
- mirrored positive/negative turn conventions;
- exact CENTER and FLAT states;
- non-finite local geometry;
- finite-input multiplication overflow;
- blocked and forged upstream recenter-condition observations;
- forged authority/tracking/station fields;
- immutable output with no command/tune surface.

TDD red phase produced 9/9 expected failures before implementation. A later
numeric-boundary test reproduced the finite-input multiplication overflow case
as RED before the fail-closed derived-value check was added.

## Evidence boundary

Private route analysis remains descriptive motivation only. Model path, model
lane lines and model action are related model outputs and do not constitute
independent lane-center ground truth. A local derivative is not proof of a
future trajectory or a causal steering mechanism. The public primitive receives
caller-owned local geometry and contains no private route, image, raw log,
location, latency fixture or vehicle-specific threshold.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 9/9 expected failures before implementation |
| Overflow fail-closed red/green | finite-input multiplication overflow reproduced RED, then PASS after derived-value guard |
| Action-horizon + action-geometry + recenter + path-observer targeted tests | 49/49 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls regression | 915/915 PASS in 217.42 s |
| Native SCons build | PASS; existing non-fatal PWD warning only |
| Default verified-public suite | 1822 passed / 42 skipped / 1 xfailed / 0 failed in 329.85 s |

Private latency-aware analysis motivating this primitive remains descriptive
only. For the strong turn-inside subset, local convergence at the action horizon
separated future recenter outcome more clearly than action-versus-lane curvature
excess. This does not prove model causality and does not authorize a control
change.

Final staged source review found no remaining Critical or Important issue in
this bounded offline diagnostic.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
