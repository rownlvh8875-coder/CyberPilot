# Candidate history ledger and leakage audit
## Identity and purpose
Validation / implemented. Preserve baseline/current/v1/v2 evidence as an immutable history snapshot.

## Changes and expected effect
curvature_yaw_candidate_history.py validates append-only hash-chain records, external expected parent, unique candidate names and blocked qualification. append_history deep-copies its inputs. Duplicate V2 entries cannot overwrite REJECTED with a new status. CURRENT requires BASELINE alias and identical source/config/result/scenario/status/qualification.
candidate-history-ledger.json contains four ordered records plus all per-case native identity components. Source/config/result SHA are explicitly aggregate vectors, not a fabricated single native identity. The original13-case v1 archive and corrected v2 search/stress archive file SHA are retained. V1 remains a descriptive TRADEOFF_ONLY history entry, not a qualified/winning selection. V2 is REJECTED; V3 NOT_CREATED_FAMILY_REDESIGN.
Hash chains prove internal consistency, not authenticity. Retain external tip or Git revision to detect rewriting the entire chain. No earlier archive is edited or replaced.

candidate-search-leakage-audit.json verifies policy bytes equal first committed67cbf2a64, preceding search3da4306c1, stress3667fa9c1 and viewer8f712754e. No tracked policy/acceptance change after outputs was found. Harness consistency/domain fixes required reruns; they did not relax scoring.
Evaluation scenarios had already been inspected during v1 attribution. Evidence tier is EXPOSED_SYNTHETIC_DIAGNOSTIC_NOT_UNTOUCHED_HOLDOUT. This audit cannot prove unrecorded developer decisions or cognitive independence. Current ablations deliberately reuse failing evaluation cells for explanation; they cannot be used for selection or qualification.

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
