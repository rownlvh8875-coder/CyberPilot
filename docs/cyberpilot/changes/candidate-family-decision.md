# Candidate family decision
## Identity and purpose
AutoTune / implemented. GO/NO-GO for frozen nine-member high-speed attenuation family, not all possible parameterized controllers.

## Changes and expected effect
Diagnostic policy was written/hashed before new outputs. Only implemented factor_high_fraction/friction_high_fraction axes are ablated. No invented interpolation knob, gain/history/lookahead axis or disabled rate gate.
| Existing correction subset | sharp_mid_left | speed_sweep | Total violations |
| --- | ---: | ---: | ---: |
| Full v2 (0,0) |21|16|37|
| Factor only (0,1) |24|15|39|
| Friction only (1,0) |9|8|17|
| Neither (1,1), v1 schedule law |0|8|8|

FAMILY_REDESIGN. All four component combinations fail original rules on the two diagnostic cases; original nine-member DEVELOPMENT enumeration admitted only full-v2, which then failed frozen EVAL. Thus there is no admissible member under the existing global nine-member policy. This does not prove impossibility for all controller architectures.
The 20m/s knot correction necessarily changes the15..20m/s interpolated region; preserving only <=15 does not preserve the whole10..20 MID bucket. Parameter reversion at20 cannot erase earlier feedback/PID state. Friction-only mitigates some violations but is not a newly selected winner.
No v3 created, no expanded grid/breakpoints, no thresholds changed. Untested state-reset/delay interventions are proposed falsification ideas, not evidence or implemented candidates.

Reproducibility: each ablation has source/config/CP/software/plant/adapter/input/reset/environment/timebase identities, exactly two executions per arm, fixed original rules and a matrix freeze. Same input/source/environment/plant/reset/CP required across ablations; per-observation profiler sources must match freeze, not just files at the end.
Initial diagnostic validation variants were superseded after review found nested-hash forgery and mixed-source receipt risks. Final run uses independent state reconstruction and per-receipt source checks. Native dynamics remained identical; superseded runs are not published or promoted.

## Original references
Repository: https://github.com/rownlvh8875-coder/CyberPilot, feature/cyber-autotune checkpoint 8f712754e643ca93c9f552aed35b47f9c32022b6.
Native upstream anchor c8fb906815530460ed156f14e09e1f312bb0f851; LatControlTorque SHA-256 9489bfd923246906ef543a1c305bf7a7fe534ee9754c94d8195ae98bb3a1f2cd.
opendbc 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. Existing source licenses/attribution retained; no external code/model adopted.
Frozen original search policy SHA-256 7bc06b4f58d72a623cc6966b2fa7e6e4048243c457276323a8961309a39ebe96; diagnostic policy SHA-256 1daffb92010e4bdf58b9fd0d12d8c6fba415b6ab9a1300695329610a41fe7c98.

## Regression risk and acceptance
Original comparator and exact IEEE cellwise rules unchanged: HIGH <= baseline; LOW/MID <= v1; all eight metrics lower-is-better; no weighted compensation. CURRENT=BASELINE exact alias. Original A3 rejection retained.
The original13 scenarios were seen during v1 attribution; the derived15/17.5 m/s cases were frozen before v2 execution. The collection remains EXPOSED_SYNTHETIC_POST_EVALUATION_DIAGNOSTIC, never an untouched holdout. The ablations are explanations, not new selection.
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
