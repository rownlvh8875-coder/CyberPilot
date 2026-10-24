# Paired standalone H1 comparison

## Identity and purpose

Cyber Validation / UI; CYBER_H1_PAIRED_COMPARISON_V1. Additive implementation on
feature/cyber-autotune after b743650cdcd48be0ab5b63c30447bb006fb16846.
All pre-existing tracked files, public receipts and submodule gitlinks are
immutable inputs. This viewer displays descriptive differences and never
recomputes a candidate verdict.

The two campaigns are separate:

- CYBER_H1_TA_B_STANDALONE_COMPARISON: UPSTREAM_BASELINE versus TA_B_V0;
  both pass through SG_DISABLED.
- CYBER_H1_SG_A_STANDALONE_COMPARISON: UPSTREAM_BASELINE versus SG_A_V0;
  identical native core implementation, separate own-feedback histories.

There is no CURRENT arm, third arm or TA/SG composition. TA-B remains
TA_STANDALONE_TRADEOFF_ONLY; SG-A remains SG_CLOSED_LOOP_TRADEOFF_ONLY.
COMPOSITION_NOT_RECOMMENDED and COMPOSITION_NOT_AUTHORIZED remain in force.

## Original references and receipt chain

Source repository: https://github.com/rownlvh8875-coder/CyberPilot at the minimum
ancestor above. Repository MIT provenance applies. No simulator source,
coefficients, web assets, candidate ranking or safety thresholds were imported.
The new policy resolves and validates the original trajectory V0 freeze and
standalone publication chain, smoothness V0 freeze and own-feedback closed-loop
publication chain, H1 V1 schema/policy and single-arm visual publication pins.
It binds exact source files, canonical configurations, state/reset policies,
scenario receipts, descriptive plant, native software, CarParams/profile and
100 Hz timebase. Filenames alone cannot establish admission.

Desired curvature is controller intent, not an independent reference.
Pre-step actual curvature is each arm's own descriptive plant state.
Applied torque is its delayed descriptive command, not EPS acknowledgement.
TA controller-limited output is the frozen TA returned output; it is never
labelled native pre-limit intent. SG pre-governor output is the native core
before shaping, and post-governor output is the SG shaped command.
Requested pre-limit torque, pre-limit torque, torqueOutputCan, measured
steering angle/rate, driver torque and real message-bus health remain null.

## Call path and state ownership

Explicit external output store → frozen policy → independent experiment arm →
detached H1 row → exact pair manifest → pure visual conversion → immutable
pages/catalog → verified localhost read-only server → same-origin browser.

Each arm owns controller history, governor, physical delay queue, curvature,
yaw/heading/pose, resets and H1 epoch/sequence/config. The TA disabled stage is
an exact stateless passthrough with the frozen output contract; it does not
execute SG-A. SG-A uses the historical own-feedback closed-loop runtime,
never frozen-command replay. Neither arm consumes the other's feedback.

Exogenous stimulus snapshots exclude actual curvature, arm/controller state,
commands, plant outputs and candidate identity. They bind the shared scenario
inputs, relative time grid, desired curvature, speed, roll, active/pressed/limit
flags, event and reset schedule. Every paired row has identical external
stimulus and distinct arm identity. Full consumed snapshots may differ.

## Frozen scenarios and deterministic execution

The authoritative scenario receipt supplies exactly straight, gentle_left,
gentle_right, sharp_left, sharp_right, low_speed, medium_speed, high_speed,
s_reversal, driver_events and limit_flags. Their original lengths, reset
schedules, phase labels and source hashes are retained; the implementation
does not choose a new common length.

Two campaigns × eleven scenarios × two arms × two repeats produce 88 H1
packages and 44 paired framesets. Each observed full experiment result is
byte-identical to the corresponding original observer-disabled historical
experiment and its frozen trace digest. Repeats compare rows, snapshots,
stimuli, configurations, traces, receipts, pairing and framesets exactly.
The deterministic clock uses capture k × 10 ms, decision capture + 1 logical
ns and completion capture + 10 ms; it measures ordering, not CPU latency.

Stored JSON roundtrip is tested explicitly. Source/config/scenario/plant
drift, forged own-feedback, duplicate/missing rows, timing/reset drift and
candidate identity reuse fail closed. Local stores use atomic no-overwrite
writes, symlink rejection, exact resume, page reconciliation and manifest-last
commit. A fixed public catalog anchors the exact output digest set against
jointly resealed local changes.

## Visual semantics

Each frame preserves INPUT / COMMAND k and PLANT COMPLETION k+1.
Charts place pre-step values at capture, commands at decision and post-step
values at completion. The first completion point is dt after the first capture;
the final completion reaches the run duration. Pose uses copied completion
coordinates with equal x/y scale and heading arrows; no map, lane or road.

Only eleven matching-phase numeric outputs receive candidate-minus-baseline
deltas. If either value is null, its delta is null. Desired curvature, speed,
roll, event/reset and evidence metadata are shared inputs, never false deltas.
There is no interpolation, smoothing, resampling, filling, trimming, pose
reconstruction or controller/sensor inference.

The browser provides campaign/scenario selection, synchronized playback,
four playback speeds, frame steps/index/scrubber/event jumps, curvature/torque
overlays, descriptive pose, current deltas and per-run max/p50/p95/final/coverage.
Identity, historical verdicts, exact unavailable reasons/provenance and all
calibration/reference blockers remain visible. Asynchronous campaign changes
clear stale data immediately; late responses cannot relabel old frames.
No acceptance thresholds, winner wording or optimizer are provided.

## Local manual workflow

Use an explicitly supplied external local store, outside the repository and
private driving-log roots:

~~~sh
python -m openpilot.tools.cyber_autotune.cyber_h1_pair_producer --store "$PAIR_STORE"
python -m openpilot.tools.cyber_autotune.cyber_h1_comparison_server \
  --store "$PAIR_STORE/repeat-1" --host 127.0.0.1 --port 0
~~~

The server prints its OS-assigned loopback URL. Stop with Ctrl-C.
The old single-arm server, catalog, assets and receipts remain unchanged.
The new API exposes campaign/scenario catalog, metadata, bounded frame pages,
individual frames and health via GET/HEAD only. Mutations return 405, unknown
resources 404 and invalid bounds 400. Traversal, non-loopback binds, hostile
Host/Origin and cross-site requests are rejected. CSP permits only local assets
and same-origin fetch. There is no CORS wildcard, upload, shell, subprocess,
parameter editing, device or optimizer endpoint.

## Publication and authority

Public artifacts contain only policy/schema definitions, scenario names,
aggregate descriptive delta statistics, counts and receipt/source hashes.
Full synthetic H1 rows, per-frame values, local paths and arrays remain local.
No private driving log was opened. No production LatControlTorque, cereal,
CarController, Params, CAN, device or Jetson code was changed or written.

Every frame and campaign is T1_DESCRIPTIVE_COUNTERFACTUAL:
DESCRIPTIVE COUNTERFACTUAL ONLY, NOT VEHICLE QUALIFIED, NOT A PHYSICAL EPS MODEL,
NO INDEPENDENT REFERENCE. T2/T3 and vehicle claims are prohibited.
HOLDOUT stays CLOSED with opening_count = 0. No candidate search, acceptance,
composition or production integration is authorized.

The empirical simple observation track remains closed, no empirical model is
admitted for future holdout, Stage B signal admission stays blocked, and future
untouched holdout remains required. Existing calibration/reference uncertainty,
pixel registration, metric calibration and independent reference blockers stay
unchanged. Sealed reference is NOT_GENERATED; vehicle is NOT_READY,
REAL_VEHICLE_UNVERIFIED and VEHICLE_ACTIVATION_BLOCKED.

## Validation

Final execution, browser and regression counts are recorded in the aggregate
repeatability/browser/readiness receipts. The browser verification uses HTTP
loopback, never file URLs, and includes both campaign catalogs, scenario
switching, eight driver_events pages, synchronized controls, phase overlays,
pose/deltas, null reasons, verdict/blocker labels, zero JS/warning/network/
external-request errors, shutdown and port closure.

Full AutoTune: 3,458 PASS (previous 3,385 + 73 new tests), 1,610.89 seconds.
Focused pairing/storage/server/UI/publication tests: 73 PASS. Controls: 142 PASS.
Lateral replay: 16 PASS. Ruff, Python/JavaScript syntax, SCons and publication
privacy audit (zero findings) PASS.

Focused tests cover negative integrity
and authority cases. Independent review identified phase plotting, asynchronous
campaign switching and local-output anchoring issues; each has an executable
regression test. All required local checks passed: full AutoTune, controls, lateral replay, Ruff,
syntax, publication/privacy/authority, whitespace and SCons. Independent review
has no remaining findings. Remote exact-HEAD CI and clean/equal branch checks
are final delivery gates after commit/push.

## Limitations and next gate

VISUAL_DATA_COMPLETENESS_PARTIAL remains true. This is synthetic T1 visualization
of historical tradeoffs, not physical validation, a digital twin, real route
replay or vehicle readiness. New observation fields, empirical plant use,
candidate/controller changes, TA/SG composition or holdout opening require
separate authorization and evidence.
