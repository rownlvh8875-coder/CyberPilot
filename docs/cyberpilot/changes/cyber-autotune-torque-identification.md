# Cyber AutoTune frozen-point torque identification

## Identity and purpose

- Area: Cyber AutoTune; implemented/reviewed numerical diagnostic, whole-PC validation pending.
- Scenario: repeat a fit on an explicit prepared development-fit selection without
  constructing the live learner or touching its Params cache.
- Scope: pure offline torque TLS only; no raw-log extraction, delay estimation,
  confidence qualification, speed bins, tuning application or vehicle-specific promotion.
- Branch feature/cyber-autotune; baseline/HEAD1ee1eb07f6cc48526f4d61265abe317fe67cc23b;
  new uncommitted torque_identification.py and test_torque_identification.py.

## Original references

- Source https://github.com/rownlvh8875-coder/CyberPilot branch feature/cyber-autotune,
  inherited commaai/openpilot at the exact HEAD above, MIT license.
- openpilot/selfdrive/locationd/torqued.py:estimate_params/slope2rot, inspected
  SHA256d0c9e29a1b2f80b27ff4a9d5c5377b6337235b1478eefe3e44c4d460aaa3f270.
- Native handle_log → negative applied normalized torque + calibrated roll-corrected
  lateral acceleration → bucket sampling → TLS → filtered learner → controlsd/LatControlTorque.
  This tool adapts only TLS; it has no consumer connection to that runtime path.
- opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 unchanged; model/firmware unknown
  for real qualification. Existing NumPy only; no new dependencies.
- Adopt numerical method, reject constructor/cache/random-subset ownership in offline API.

## Changes and expected effect

- New module: immutable prepared-point contract, validation, complete-input digest,
  deterministic TLS estimate and authority-free report. New tests: invalid input,
  exact repeatability, affine/noisy native parity and no permission/confidence escalation.
- No upstream integration. Alternative unbound native proxy retained only as prior probe;
  small independent formula avoids live-module imports, at cost of future parity maintenance.
- Expected effect: reproducible fixed-runtime numerical diagnostic, not improved steering.
- Constants:3 algebraic rows,12000 resource cap from8*1500 native buckets; native
  x[-.5,.5),abs(x)>.02,y[-1,1]m/s²; residual multiplier1.5; float64 epsilon-scaled
  degeneracy tolerance. These are NOT physical calibration/confidence policies.
- Stateless calls; caller declares lag alignment exactly once. Invalid/degenerate
  input returns BLOCKED/no estimate. Confidence and independent sample count unknown.
- Existing policy/profiles and Panda/opendbc safety untouched; no actuator or Params writes.
- Low upstream conflict; source numerical evolution requires parity review.

## Regression risk and acceptance

- Risks: falsely treating prepared-point metadata as authentication, frame count as
  independent evidence, spread as physical friction, or numerical fit as candidate approval.
- Require fixed-runtime repeatability, native parity1e-13 absolute/relative tolerance,
  invalid-input rejection, all authority flags false and existing tests unchanged.
- Inputs synthetic only. No holdout read, new private-log extraction or scenario claims.
- Rollback: do not import/use the new offline module; no runtime/profile state changed.
- One fresh reviewer required. Vehicle promotion remains separate and unavailable.

## Validation method and actual results

| Stage | Method | Evidence | Result/limits |
| --- | --- | --- | --- |
| Focused unit | .venv/bin/python -m pytest openpilot/tools/cyber_autotune/tests/test_torque_identification.py -q | synthetic affine/noisy points |8passed23subtests0.27s; independentreview8/23in0.44s |
| Package/affected | pytest AutoTune; tools/test_runner.py AutoTune+controls | laptop current snapshot |233passed748subtests25.40s;365passed14.47s; both exit0 |
| Lint | Ruff package; git diff --check | new local files | initial2stylefindings fixed; both final PASS |
| Whole PC | default runner, earlier1328collected snapshot | pre-matrix/cleanup/identification | timed out124at2400s; one recorded locationd setup error; diagnosis running, not PASS |
| Replay | qualified real-data pipeline | no fitted candidate | NOT_RUN |
| Closed loop | calibrated plant comparison | no fitted candidate | NOT_RUN |
| Shadow | non-actuating continuous evaluation | no fitted candidate | NOT_RUN |

## Handoff

- Observed: focused repeatability/native numerical parity; no empirical vehicle benefit.
- Missing: approved extraction/selection/alignment, independent confidence/convergence,
  firmware/model binding, physical bounds, candidate generation/evaluation integration.
- Independent review0Critical0Important0Minor; broader regression remains incomplete.
  Overall STEP8 PARTIAL/NOT_READY.
- No commit/PR; no real-vehicle application authorized by this diagnostic.
