# Action geometry alignment diagnostic

## Identity and purpose

- Feature / area: Cyber AutoTune / Cyber Lateral offline diagnostic.
- Status: descriptive software diagnostic only; no vehicle qualification or runtime use.
- Purpose: compare the already-published model action and bound controls desired
  curvature with caller-supplied local model-path and model-lane-center
  curvature, normalized to the requested turn direction.
- Scope: immutable upstream recenter-condition observation plus two finite local
  geometry scalars only. The diagnostic does not construct geometry, choose an
  action horizon, tune parameters, generate curvature commands, or write to
  Params/CAN/device state.
- Branch / baseline: feature/cyber-autotune from
  13c2a7339abf8d53dc0ca3e8c92455c804953d1f.

## Motivation

Private read-only analysis of the existing log set compared model action,
controlsState.desiredCurvature, model-path curvature and model-lane-center
curvature at a latency-aware action horizon. Model action and the bound controls
desired curvature were more often geometrically closer to the local model path
than to the local model lane center.

That result supports a narrower statement than direct causality: the action
signal often follows path geometry rather than independently correcting it back
to lane-center geometry. However, stronger action-versus-lane curvature excess
did not cleanly separate recenter success from failure. The stronger separator
was whether the path offset was already converging toward lane center at the
action horizon. Model path, lane lines and action remain outputs of the same
model family, so none is independent lane-center ground truth.

## Implementation

- Added openpilot/tools/cyber_autotune/action_geometry_alignment.py.
- observe_action_geometry_alignment():
  - accepts only an already-valid DESCRIPTIVE_ONLY RecenterConditionObservation;
  - revalidates upstream numeric identities, turn/tracking signs, recenter
    outcome, same-side state, station validity and blocked authority fields;
  - accepts finite caller-owned local path and lane-center curvature;
  - reports turn-normalized action-minus-lane, path-minus-lane,
    action-minus-path, controls-minus-lane and controls-minus-path curvature;
  - reports exact absolute errors from action/controls to path and lane;
  - labels action and controls as PATH_CLOSER, LANE_CLOSER or EQUAL_DISTANCE
    using exact absolute-distance comparison with no threshold;
  - labels path-vs-lane turn curvature as MORE_TURN_THAN_LANE,
    LESS_TURN_THAN_LANE or LANE_MATCH with no magnitude threshold.
- The output is frozen and hard-codes NOT_READY, REAL_VEHICLE_UNVERIFIED,
  VEHICLE_ACTIVATION_BLOCKED and vehicle_activation_allowed=False.
- The module intentionally does not compute model latency, vehicle speed
  projection, local geometric curvature, candidate ranking or a tuning value.
  Those remain caller-owned/private diagnostic concerns.

## TDD and risk coverage

Synthetic public-safe tests cover:

- action/controls closer to path versus lane;
- exact equal-distance classification without tolerance tuning;
- mirrored positive/negative turn conventions;
- more-turn, less-turn and lane-match path curvature relationships;
- non-finite local geometry;
- blocked upstream observations;
- forged tracking identity, forged recenter outcome, forged future station and
  forged authority fields;
- immutable non-authoritative output with no command/tune surface.

TDD red phase produced 9/9 expected failures before the module existed. Two
additional fail-closed tests then exposed missing upstream recenter/station
validation and were made green before broader validation.

## Evidence boundary

Private route analysis is descriptive motivation only. Exact route identifiers,
raw logs, image data, private paths and private-derived numeric fixtures are not
included in this change. The local geometric curvature supplied to this public
primitive is not assumed to be the model action contract, and the module does
not infer a causal steering error from geometric alignment.

## Validation results

| Check | Result |
| --- | --- |
| TDD red phase | 9/9 expected failures before implementation because the module did not exist |
| Upstream-hardening RED phase | 2/2 expected failures for forged recenter outcome / future station before hardening |
| Action-geometry unit tests after hardening | 11/11 PASS |
| Action-geometry + recenter-condition + recenter-intent + path-observer targeted tests | 39/39 PASS |
| Ruff / staged whitespace | PASS |
| Publication/privacy audit | 3 changed files / 0 findings |
| Production/runtime caller search | 0 callers |
| Cyber AutoTune + controls supported runner, 2 workers | 905/905 PASS in 218.81 s |
| Native SCons build | PASS, 100%, exit 0; existing non-fatal PWD warning only |
| Default repository runner, 2 workers | 1812 passed / 42 skipped / 1 xfailed / 0 failed in 336.23 s |
| Private latency-aware action-horizon attribution | model action and bound controls desired curvature were more often closer to local path geometry than lane-center geometry; recenter outcome separated more strongly by local path-offset convergence than by action-versus-lane excess alone |

An initial serial pytest invocation of the same AutoTune/controls directories was
stopped without a verdict after it proved inappropriate for the established
parallel validation workflow. The final supported two-worker runner above is the
recorded regression result.

Final source review found no remaining Critical or Important issue in this
bounded offline diagnostic. The private analysis remains descriptive and does
not establish independent lane truth, model causality, actuator behavior or a
safe runtime correction.

Vehicle decision remains:

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED
