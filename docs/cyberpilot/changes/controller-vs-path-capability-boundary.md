# Controller versus path capability boundary
## Identity and purpose
Validation / implemented offline structural groundwork. Separate controller response effects from input/model/path effects.

## Changes and expected effect
For these37 failures, all arms receive identical desired curvature/time/speed/roll and initialization. Differential violations are controller tracking/command dynamics under this synthetic input. No model/planner runs and no independent lane geometry is supplied; desired path reasonableness in the real world is UNKNOWN.
The residuals do not establish lane-centering quality. Generic observer lateral excursion is not lane-center error. A prescribed desired curvature may expose controller limitations without identifying a planner fault.
curvature_yaw_effect_contract.py freezes a2x2 manifest: same input/different controller isolates descriptive controller effects; same controller/different input isolates synthetic/model input effects. Only explicit source roles SYNTHETIC_GENERATOR, RECORDED_CONTROLLER_OUTPUT, OFFLINE_MODEL_OUTPUT are allowed; none implies truth.
Inputs bind generator/model source SHA, exact timebase, speed and curvature frame SHA. Controller identities must be distinct; two input vectors must differ and share exact timebase. Trajectory source is NOT_PROVIDED rather than inferred from pose/GPS or candidate output.
This is STRUCTURAL_MANIFEST_ONLY_NOT_EXECUTED. It is groundwork, not production model/planner modification or a completed2x2 performance experiment. With FAMILY_REDESIGN, next work should freeze an offline architecture/input experiment rather than widen this factor/friction grid. Controller responsibility remains measurable; real path quality remains BLOCKED.

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
