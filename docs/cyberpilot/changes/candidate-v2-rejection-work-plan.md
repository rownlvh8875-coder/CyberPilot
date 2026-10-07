# Candidate v2 rejection investigation implementation plan

> Execution: native implementation in this session with an independent final code review. User authorized autonomous execution.
**Goal:** Explain all 37 frozen evaluation failures, identify component contributions and freeze a family decision without resurrecting v2.
**Architecture:** Strict full native report admission precedes diagnostic ledger generation. Four existing factor/friction ablations use the original isolated producer. A separate passive profiler records controller state and must reproduce the original native response exactly.
**Tech stack:** Existing Python/Cap'n Proto/native subprocess infrastructure; bundled JavaScript viewer; loopback-only browser verification.
**Spec:** User checkpoint 8f712754e, original frozen v2 search policy and rejection diagnostic policy.

## Global constraints
Original comparator, thresholds, A3 rejection, production controller, source admission and CURRENT=BASELINE unchanged. No new physical delay, vehicle/CAN/Params/profile/network writes or private raw publication. All results are SYNTHETIC / NO INDEPENDENT LANE TRUTH. NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

## Review focus
- Rehashed malformed results must fail public replay admission.
- PID profiler must not change original output, input ordering or state.
- Counterfactuals must differ only in the declared existing parameter configuration.
- Stress PASS must never overwrite nominal REJECTED.
- Reused evaluation fixtures are explanatory diagnostics, not an untouched holdout or selection evidence.

## Task 1: Rejection ledger and passive dynamics
Create curvature_yaw_rejection.py, curvature_yaw_diagnostic_worker.py, curvature_yaw_diagnostics.py and tests/test_curvature_yaw_rejection.py / test_curvature_yaw_diagnostics.py.
Interfaces: build_ledger(reports, selection, evaluation_freeze); run_diagnostics(request, expected_native_result); run_ablations(output_dir).
- [x] Write completeness, cluster determinism, rehashed tamper, profiler equality and identity failure tests; observe RED.
- [x] Implement strict admitted ledger, passive isolated profile collector and immutable pre-execution ablation manifest.
- [x] Execute 8 cases x 4 arms x 2 repeats and passive dynamics for 2 cases x 4 arms x 2 repeats. Publish only derived synthetic receipts.
- [x] Focused/full AutoTune, Ruff, syntax, publication/privacy/authority, diff check, SCons; document attribution and commit/push.

## Task 2: Family decision, capability boundary and history
Create curvature_yaw_candidate_history.py with tests and feature records.
Interfaces: decide_family(ablations); experimental_contract(controller, input_source); append_history(history, entry, expected_parent_sha256).
- [x] Test deterministic verdict, rejected-history immutability, alias, source binding and unknown lane quality.
- [x] Implement conservative frozen verdict and source-bound controller/input factorial contract; no v3 unless justified.
- [x] Audit chronology and historical fixture exposure; publish machine-readable candidate history and evidence limitations.
- [x] Run required gates, independent review, fix regressions, commit/push.

## Task 3: Rejection viewer
Create curvature_yaw_rejection_visualizer.py; extend shared HTML/JS only with rejection-specific controls.
- [ ] Test 37 rows, clusters, four-arm overlays, click-to-frame navigation, schedule and divergence marker.
- [ ] Bind viewer data to admitted ledger and raw report projections, never caller-supplied status.
- [ ] Validate rendering/selectors/runtime via temporary 127.0.0.1 server; close server and browser.
- [ ] Full required gates; feature record; review; commit/push; fresh remote/local equality and clean tree.
