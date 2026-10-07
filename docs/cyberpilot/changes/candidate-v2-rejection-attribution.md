# Candidate v2 rejection attribution
## Identity and purpose
Validation / implemented, independently reviewed. Explain every frozen nominal violation, not build another candidate.
Public candidate-v2-violation-ledger.json carries all37 unique metric/cell IDs, four arm values, threshold, signed deltas, phase/speed/curvature ranges, original step indexes, torque/derivative/steering/pose ranges, saturation and exact event contexts. Its 12 deterministic clusters partition37 rows without merging units or relaxing rules.

## Changes and expected effect
curvature_yaw_rejection.py admits full native/replay reports before building rows. curvature_yaw_diagnostics.py and curvature_yaw_diagnostic_worker.py provide a passive isolated sys.setprofile collector and independent arithmetic reconstruction; stock production code and public producer/protocol are unchanged.
Data flow: prefrozen input and wire CP -> native parameter schedule evaluated before every update -> PID accel-space limits -> stock desired history100, delay index16, lookahead index-2 and1.2Hz filter -> PID -> linear factor conversion -> requested torque -> sign inversion -> sole physical plant queue2x10ms -> pre-step VM feedback next update.
Profiler records pre/post integral, P/I/D/F, unclipped/clipped control, limits, schedule, history SHA and jerk. Independent reconstruction includes stock pid_log.error float32 readback before PID. Inactive retains stock PID state while torque is0; pressed freezes integral. No added smoothing/output scale/bias/queue/reset.

Root timing:
- sharp_mid_left,17.5m/s: factor v1=4.013671875 versus v2=4.005859375; friction=.1258544921875 versus .1253662109375. First requested divergence frame41/.41s (10ms after entry begins), v2-v1 +1.1953331461062033e-5. At that instant P/I/error are0: the first difference is feedforward compensation and factor conversion, not gain/history/integral.
- speed_sweep: v1/v2 exact samples through frame200/15m/s; first difference frame201/15.05m/s/2.01s, delta=-1.8799959113247056e-5. P/I/error are still equal on this first step; factor/friction readback and feedforward differ.
- At frame300/20m/s v2 factor/friction equal baseline (4/.125), but feedback/P/I differ. At frame333/21.65m/s requested v2-baseline=-.37666547668019434: equal instantaneous config does not reset closed-loop history.
- KP/KI, delay/history hashes, raw/filtered jerk and lookahead are exact equal across arms for both failing scenarios. Subsequent P/I changes are responses to different feedback, not changed gain configuration.
- 37 metrics: curvature RMSE9, aligned RMSE7, steering residual7, requested derivative7, applied derivative7. No saturation-occupancy/zero-crossing/reversal metric violation. Their contexts remain visible; a claim that event counts explain all failures would be unsupported.

candidate-v2-dynamics-attribution.json retains A..O supporting/contradicting evidence, confidence and falsification tests. Saturation/anti-windup and integral carry-over are observed mechanisms, not uniquely isolated causes. Common history alignment versus plant delay and plant-specific artifacts remain unresolved. No fabricated additive causal percentages.
Risk: native pre-step steering/PID versus post-step curvature must not be phase shifted; no fitted lag or connected-bin derivative. Requested/applied signs retain original native convention.

## Original references
Repository: https://github.com/rownlvh8875-coder/CyberPilot, feature/cyber-autotune checkpoint 8f712754e643ca93c9f552aed35b47f9c32022b6.
Native upstream anchor c8fb906815530460ed156f14e09e1f312bb0f851; LatControlTorque SHA-256 9489bfd923246906ef543a1c305bf7a7fe534ee9754c94d8195ae98bb3a1f2cd.
opendbc 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. Existing source licenses/attribution retained; no external code/model adopted.
Frozen original search policy SHA-256 7bc06b4f58d72a623cc6966b2fa7e6e4048243c457276323a8961309a39ebe96; diagnostic policy SHA-256 1daffb92010e4bdf58b9fd0d12d8c6fba415b6ab9a1300695329610a41fe7c98.

## Regression risk and acceptance
Original comparator and exact IEEE cellwise rules unchanged: HIGH <= baseline; LOW/MID <= v1; all eight metrics lower-is-better; no weighted compensation. CURRENT=BASELINE exact alias. Original A3 rejection retained.
These scenarios were previously exposed, including v1 attribution: EXPOSED_SYNTHETIC_POST_EVALUATION_DIAGNOSTIC, never an untouched holdout. The ablations are explanations, not new selection.
Rollback removes these offline analysis modules/artifacts; original runtime and prior evidence remain unchanged. Independent reviewer required; no vehicle promotion authority.

## Validation method and actual results
| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit/regression/build | Focused new tests; full tools/test_runner.py -j2 openpilot/tools/cyber_autotune/tests; PATH=$PWD/.venv/bin:$PATH .venv/bin/scons -j2 | Native WSL Ubuntu-24.04, Python3.12.13 | Focused27 PASS; SCons100% PASS; AutoTune977/977 PASS268.77s; Ruff/syntax/authority/privacy/diff PASS; publication421files/0 findings |
| Replay vs baseline | Strict original native response plus public plant replay; 37 ledger completeness and malformed/rehashed tamper tests | Full original11-case EVAL receipts retained locally; public derived hashes only | 37 preserved; exact CURRENT alias; no lane-truth admission |
| Simulation/closed loop | Four prefrozen configurations x failing2 scenarios x four arms x2 repeats; passive profiler two cases x4arms x2 | 64 original native runs plus16 separate passive diagnostic runs; matrix and producer SHA frozen | Exact repeats/output equivalence; original full-v221+16 reproduced |
| Shadow | Not applicable: offline native subprocess only | No device/runtime integration | No CAN/Params/CarController/device/profile/network write path |

## Handoff
IMPLEMENTED: structural admission, deterministic diagnostic receipts, retained adverse evidence.
SYNTHETIC SCREENING: original v2 remains REJECTED; stress23/23 hard/no-worse PASS remains TRADEOFF_ONLY and cannot overturn nominal rejection.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Actual lane quality/performance and calibrated plant external validity remain unavailable.
REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
No raw private logs/images/routes published. No vehicle application authorized. Future work is a separately frozen offline experiment, not broader retrospective grid tuning.

Independent review: fixed nested profiler-hash forgery, per-run frozen source binding, persisted matrix-to-original-ledger binding and historical dynamics equality. Added regression tests; re-reviewed with no Important/Critical findings.
