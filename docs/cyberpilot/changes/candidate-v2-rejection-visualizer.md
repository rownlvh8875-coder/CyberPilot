# Candidate v2 rejection visualizer and browser validation

## Identity and purpose
UI / IMPLEMENTED, independently reviewed. Expose the37 failed cells, controller schedules and passive PID without changing the rejected candidate.
Branch feature/cyber-autotune; increment baseline cd679975d9af58ccfe95bc35e541c24aa257ecf7. Prior checkpoint8f712754e. New source identities and browser artifact SHA are in candidate-v2-rejection-browser-results.json.

## Original references
Repository https://github.com/rownlvh8875-coder/CyberPilot. Existing shared curvature_yaw_visualizer.html/.js and v2 strict renderer reused without editing.
Original upstream native anchor c8fb906815530460ed156f14e09e1f312bb0f851; opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76; source licenses/attribution retained.
Full nominal EVAL, matrix ledger and passive state flow through strict original admission, reviewed export linkage, then a separate display projection.

## Changes and expected effect
curvature_yaw_rejection_visualizer.py/.js add37-row table,12-cluster selector and click-to-original-first-step cursor. Baseline/current/v1/v2 share401 samples and raw timebase; requested/applied torque, actual/desired curvature and angle, speed, adjacent derivatives, phase, saturation and reversal markers remain visible.
Parameter curves show readback delta relative to baseline; exact absolute factor/friction and P/I/F/control/clipping appear at cursor. Passive observations are provided only for the two failed scenarios; other scenarios explicitly say not supplied.
PID attachments require a complete admitted ablation export, original ledger match and exact fresh/historical samples. They carry separate profiler provenance. Native proofs remain omitted from display; checksums are recomputed after attachment and do not authenticate execution.
Exact divergence is calculated directly from raw signed V2/V1 requested torque for every displayed scenario, not only the two failed cases. White marker appears only when both overlays are enabled. No onset tolerance or altered acceptance rule.
Original independent-truth/vehicle/A3/comparator gates unchanged. No lane boundaries or real geometry synthesized. CURRENT remains exact BASELINE alias. No new model/planner/controller/runtime dependency.

## Regression risk and acceptance
Risk: stale projection SHA after schedules/PID attachment, missing divergence outside failed cells, wrong pre/post-step alignment, anonymous row selection or hidden rejected status.
FAMILY_REDESIGN and nominal REJECTED remain visible independently of per-case TRADEOFF_ONLY and previous stress23/23 PASS. No new candidate or retrospective selection.
Rollback removes this separate renderer/extension; original viewer, evidence and runtime remain intact.
Independent review found a real missing-divergence display defect for four high scenarios. Added a RED regression with absent failing-ledger divergence, fixed raw comparison, GREEN5/5, re-reviewed with no Important/Critical findings.

## Validation method and actual results
| Check / stage | Method and command | Evidence / identity | Actual result and limits |
| --- | --- | --- | --- |
| Unit / regression / build | Focused pytest; tools/test_runner.py -j2 openpilot/tools/cyber_autotune/tests; export PATH=$PWD/.venv/bin:$PATH; .venv/bin/scons -j2 | WSL Ubuntu24.04 Python3.12.13; browser result receipt/source SHA | Focused5/5; full982/982 PASS287.33s; SCons100%; Ruff/py_compile/Node syntax/diff/authority/privacy PASS |
| Replay vs baseline | Full original11-case EVAL plus reviewed exporter; exact samples/schedules | Display source receipts and separate display checksum |37 failures retained; CURRENT alias; private raw omitted |
| Simulation / closed loop | Previously frozen64 native+16 passive diagnostic executions | Exact native response equality/repeats; no new controller execution for GUI | Descriptive synthetic dynamics only |
| Browser | Existing test-only loopback_viewer_server at127.0.0.1, maximum300s; actual Chromium IAB | HTML22,268,628 bytes SHA5f9e5677f3ea5c54aabd4d16c8e6541d45ae74ad780f847efeb2f4c30b3fe8e0 | Load/table37/cluster3-of37/clickstep120/four401-point curves/8 torque series/4 PID series/selectors PASS; JS errors0; remote DOM assets0 |
| Cleanup | Close owned tab; SIGTERM server; existing context finally shutdown/server_close/join; process/listener check | Only our8111 listener/process targeted | Exit0; process absent; connect127.0.0.1:8111 refused. Screenshots test-output only; no binary committed |
| Shadow | Not applicable: offline display, cannot actuate | No CAN/Params/CarController/device/profile/network runtime path | No vehicle application |

## Handoff
IMPLEMENTED: complete diagnostic attribution, frozen family decision, append-only consistency history, controller/input provenance groundwork and browser-tested rejection viewer.
SYNTHETIC SCREENING: V2 REJECTED; FAMILY_REDESIGN; V3 NOT_CREATED. Old stress TRADEOFF_ONLY cannot overturn nominal rejection.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE. Model/planner effect experiment is structural groundwork, not executed; actual path/lane quality remains UNKNOWN.
REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Next work: separately prefrozen offline architecture or controller/input experiment with common plant/reset/CP/environment held fixed, complete source/input provenance, bounded deterministic evaluation and independent truth kept separate. Do not widen the rejected grid.
No production controller/threshold/A3 change, no private raw publication or vehicle activation.
