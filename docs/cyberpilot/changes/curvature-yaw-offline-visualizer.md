# Curvature/yaw offline native screening visualizer

## Identity and purpose
Cyber UI / Validation, implemented offline viewer, final verification pending.
Branch feature/cyber-autotune, start cc8dc181a, source-bound uncommitted renderer
patch. Purpose: inspect actual native baseline/current/candidate synthetic traces
with frozen scenario/arm selection and time cursor. Software Santa Fe CP fixture
only; no device/live controller/model selection or vehicle validity.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Implementation and structural consistency admission are separate from synthetic
screening, actual performance qualification (BLOCKED), and real vehicle readiness.

## Original references
CyberPilot current native screening module, repository MIT, no new runtime package.
Native source upstream c8fb906815530460ed156f14e09e1f312bb0f851, opendbc
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76; exact execution/source SHA in each
manifest/receipt. No perception model or independent lane/road source.

User reference: https://sunnylink.wiki/models.
Public implementation inspected, not merely the rendered model library:
https://github.com/vinnie291/sunnylink-wiki/tree/7468293884d03468f371e1a39bb39eb2f6b73a9a
Verified branch main, MIT Copyright 2026 Vinh Le, no code copied. Relevant files:
- app/models/page.tsx: model library catalog, not native evidence.
- components/new-sim/SimulatorLab.tsx and ModelAccordionSelector.tsx:
  scenario/model state and selection controls.
- components/new-sim/WorldCanvas.tsx: fixed-step presentation, telemetry,
  route chapters, plus vote API updates.
- lib/new-sim/modelProfiles.ts, feedback.ts, simulation.ts and scene.ts:
  catalog/feedback-derived illustrative physics and synthetic road/path drawing.

Traced flow: model name/tags/steeringFeel/community feedback and votes →
deriveFeedbackPhysics → ModelSimProfile → Simulation fixed-step heuristic
controller/road → world/telemetry display. feedback.ts explicitly labels its
parameters illustrative rather than measured model outputs. This flow does not
establish real model/native-controller replay or independent lane truth.
Adopted presentation ideas only: stable same-scenario selection, trace colors,
section/cursor telemetry and visible baseline/candidate comparison.
Rejected as evidence: feedback-derived lane bias/wobble, synthetic road assumed
real, community votes changing physical parameters.
Also inspected official https://github.com/sunnypilot/sunnylink-frontend:
remote/device model selection is outside this offline task. No service dependency,
network API, Three.js dependency or model downloading is added.

## Changes and expected effect
curvature_yaw_visualizer.py loads bounded strict JSON with duplicate-key/nonfinite
rejection; validates catalog order/SHA, receipts/scope, finite/physical traces,
exact alias and diagnostics before writing any HTML. Candidate config and all
controller/sample/manifest identities remain bound by the input receipt.
Python CLI → admitted synthetic payload → deterministic HTML + local SVG/JS →
read-only scenario/arm/cursor controls. No new native controller callback or replay
input handling; viewer consumes existing replay-admitted screening output.

curvature_yaw_visualizer.html and .js are embedded locally; output binds input,
renderer, template and script SHA. No clock/random/remote assets, API, plugin,
writer or tuning control. CSP blocks connections and external resources.
16 MiB input cap bounds report transport; 13 scenarios/401 frames/10 ms from
the frozen screening catalog, not an acceptance threshold.
Tests: tests/test_curvature_yaw_visualizer.py (seven tests).

Shows desired/actual curvature, observer trajectories, requested/applied delayed
torque, native pre-step angle, phases, saturation and zero-crossing/reversal events;
a candidate-minus-baseline pose plot reveals small real differences.
CURRENT=BASELINE is displayed as an explicit exact alias. No fictional lane edges
or centerline are drawn. SYNTHETIC / NOT VEHICLE TRUTH and NO INDEPENDENT LANE TRUTH
are always visible. Observer x/y axes are scaled independently and labeled.
Curvature/pose are post-step states; torque is sampled at native command time and
angle is pre-step feedback. This sample timing is disclosed on screen.
All state is local display selection, initialized first scenario/step zero;
scenario change resets cursor. Plant remains sole 20 ms physical-delay owner.

## Regression risk and acceptance
A checksum validates internal consistency, not authenticated execution/truth.
Renderer never qualifies/promotes a candidate. Bad hashes/scope/authority/catalog
and physical traces must fail before output is written. Metadata is text or
script-safe escaped JSON, not executable markup.
Frontend logic tests use Node 22.14.0 DOM doubles; they do not prove browser layout,
CSP enforcement, accessibility or rendering performance.
No search/selection, holdout or new performance threshold; catalog remains the
same fixed matrix. Gains and source identities cannot be edited through UI.
Upstream synchronization cost: standalone viewer; screening schema drift must be
updated explicitly, with old records retained. Rollback: remove viewer/assets/tests;
candidate/native/runtime paths unaffected. Independent read-only reviewer required;
promotion authority and vehicle application: none.

## Validation method and actual results
Ubuntu 24.04 WSL, Python 3.12.13, Node 22.14.0.
Test-first RED: missing renderer module, five import errors and one CLI failure.
GREEN seven tests: deterministic render, warning/trace coverage, scope/hash/catalog
rejection, script-safe metadata, strict JSON, actual renderer SHA, CLI fail-before-write,
JS scenario/arm/time controls and finite SVG series in DOM double.
node --check and full AutoTune Ruff PASS.
Generated local HTML contains all 13 historical source-bound catalog reports;
input catalog SHA ec7b9557f91fc97fbd5012702d2367d9325310a000baa55884234a2219e5a027.
Generated HTML/traces are local artifacts, not committed.

Actual browser rendering: BLOCKED. Browser tool rejected file:// URL with security
policy stating only http/https allowed and explicitly prohibiting workaround.
No alternate browser surface/server/CDP workaround was attempted. DOM-double
logic verification is recorded separately and does not replace a browser PASS.
Final focused regression 46/46 PASS in 29.978 s; AutoTune 901/901 PASS in
235.93 s. Ruff over all AutoTune, compileall/py_compile, Node syntax, authority
grep and git diff --check PASS. publication_check: 372 files / 0 findings.
SCons 100% PASS with export PATH="$PWD/.venv/bin:$PATH"; .venv/bin/scons -j2.
Independent review found two binding consistency issues, corrected test-first
and re-reviewed with no remaining important finding; see canonical-binding record.
Local HTML SHA-256:
9d989914b7e96afe56f6e4711cfdc99f1ccc3bda45c5759bc4a77aaa1f40996f.
Browser rendering remains BLOCKED, not silently marked PASS.

| Stage | Method and evidence | Result and limit |
| --- | --- | --- |
| Unit/regression/build | Python tests, Node syntax/control logic, Ruff, full runner, SCons | UI 7 / focused 46 / full 901 PASS; build/static gates PASS |
| Replay vs baseline | Input screening receipts independently replayed during generation | All 78 public replays structural; no truth/qualification |
| Synthetic closed loop | Frozen 13 scenarios, 3 arms x 2 native repeats | Actual nonzero candidate differences; adverse metrics retained |
| Device shadow / real performance | No device/independent lane evidence | NOT_RUN / BLOCKED |
| Browser rendering | Attempted local generated file via browser tool | BLOCKED by file protocol security policy |

## Handoff and remaining work
Reproduce after native screening:
.venv/bin/python -m openpilot.tools.cyber_autotune.curvature_yaw_visualizer --input /tmp/cyber-screening.json --output /tmp/cyber-viewer.html
The generated file opens locally for a human; no web server is needed.
Implemented goal: real frozen controller candidate, native feedback-bound execution,
exact declared alias/repeats, descriptive diagnostics and local visualizer.
Remaining: human browser rendering/accessibility check; separately reviewed future
candidate hypotheses because this fixed candidate has high-speed regressions;
actual independent desired-path/lane geometry and appropriate plant calibration
before performance qualification; later non-actuating shadow evidence.
A calibrated plant and lane/model truth cannot be invented by a controller.
Historical source audit and strict evidence/comparator contracts remain unchanged;
A1/A3 rejection remains. No private raw logs/routes/images/CAN/GPS published.
No vehicle application authorized.

Production three-distinct-arm admission still cannot accept CURRENT=BASELINE.
This viewer consumes the separately declared-equivalent experiment; no production policy change.
