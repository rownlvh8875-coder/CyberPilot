# Offline controller candidate implementation plan

> Native inline execution using executing-plans, TDD and one fresh read-only final review. User authorizes commit/push and autonomous decisions without approval questions.

**Goal:** Differentiate a real native parameterized controller in feedback-bound
curvature/yaw simulation while retaining all real-evidence/vehicle blockers.

**Architecture:** Add opt-in strict v2 controller selector to existing offline
worker; preserve v1 and production LatControlTorque. Apply a frozen factor/friction
schedule through update_torque_parameters before native update. Separate synthetic
experimental manifest models CURRENT=BASELINE exactly; it never calls or changes
the production frozen performance comparator. Public adapter independently replays
all transcripts. Offline HTML renders bound trajectories and diagnostics.

**Tech stack:** Python 3.12, existing native controller and A1 schedule validator,
strict JSON/SHA-256, stdlib HTML/SVG/JavaScript; no new packages.
**Spec:** user task, baseline 57489486afd5a5197256570fae1bf12bfcfbb296,
and feature records generated per increment.

## Global constraints
- Production/live controller, runtime path, safety, comparator and A1/A3 rejection unchanged.
- No CAN/Params/CarController/device/network/profile write in candidate.
- Same synthetic CP factor=4, friction=.125 for every arm; not a vehicle tune.
- Schedule bounds and transition rules are existing a1_schedule rules.
- Candidate is the existing bounded_combined coordinates, no retuning/search.
- Physical delay owner PLANT; native reference history remains prediction.
- No independent lane truth or real performance qualification.
- NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
- No private raw input or logs/images/routes committed.

## Review focus
- Version/field/type/config mismatch rejected before native execution.
- Effective native float32 schedule/readback and bounds, no silent fallback.
- Alias must be identical canonical request; candidate must differ by controller selection.
- Common reset/input/plant/sign/CP, all six repetitions and public replay required.
- Visualization must revalidate immutable receipt, display no invented lane truth.

## Task 1: Parameterized native candidate
Files: new curvature_yaw_candidate.py/tests/test_curvature_yaw_candidate.py;
modify only curvature_yaw_native_protocol/worker/runner; feature record.
Interfaces: v2 controller {implementation, config}; candidate support file set;
candidate schedule immutable tuples; v2 result selector and effective rows SHA.
- [x] RED tests: v1 unsupported selector; identity/config drift; invalid late schedule; native difference/readback/repeatability/inactive.
- [x] Implement strict v2 selector; fixed precomputed whole schedule via existing A1 validator; native update_torque_parameters/readback before update.
- [x] GREEN focused and full AutoTune; Ruff/syntax/publication/diff/authority/SCons.
- [x] Record actual results and commit.

## Task 2: Declared-equivalent synthetic experiment
Files: new curvature_yaw_screening.py/tests/test_curvature_yaw_screening.py;
record and aggregate snapshot. Interfaces: frozen request triplet + canonical manifest;
six native results + independent replay; immutable sanitized report and plot samples.
- [x] Freeze synthetic matrix and diagnostic definitions before running.
- [x] RED: alias mismatch, basis/manifest drift, candidate no-op, repeatability,
  failed replay, low/high/mirrored curves/S/override/re-engagement.
- [x] Implement separate offline-only contract (2 unique controllers + 1 exact alias);
  structural replay and descriptive curvature/torque/pose diagnostics, never lane RMSE.
- [x] GREEN full gates; retain regressions, no best/acceptance; commit.

## Task 3: Offline visualizer
Files: curvature_yaw_visualizer.py + local JS/HTML asset + tests; feature record.
- [x] RED: malformed/forged report rejected; required traces/events/warnings;
  real browser UI renders scenario/arm selection and cursor data.
- [x] Implement deterministic network-free HTML with SVG trajectory/time traces,
  desired/actual curvature, requested/applied torque, angle, phases/saturation/reversals.
- [x] Analyze Sunnylink public source selector/visualization structure at exact SHA;
  adopt presentation ideas only, no heuristic simulated behavior as controller evidence.
- [x] GREEN full gates and final independent review; record artifacts;
  commit/push, verify HEAD/origin/clean.

## Verification exception
The real browser-render check in Task 3 is BLOCKED: browser tool explicitly
rejected local file protocol and prohibited workarounds. A separate Node DOM-double
control test passed, without claiming browser rendering, CSP enforcement or
visual/accessibility verification. Generated standalone artifact is delivered
locally for human opening; independent truth and readiness blockers stay intact.
Independent final review found two consistency issues, fixed through new RED
tests, focused regression and complete 901-test/build/static rerun; re-review clear.
