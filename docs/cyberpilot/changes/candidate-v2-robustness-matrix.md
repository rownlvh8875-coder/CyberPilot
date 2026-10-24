# Candidate v2 bounded robustness matrix

## Identity and purpose
Cyber Validation / AutoTune. IMPLEMENTED: frozen one-at-a-time native stress
runner, full-report matrix admission and final EVAL context binding.
SYNTHETIC SCREENING: selected config (0,0), final classification REJECTED.
BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE / actual performance qualification.
REAL VEHICLE STATUS: NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.
Branch feature/cyber-autotune; initial checkpoint 2e999233700426970eb2486a4c71ce985fcb2e23;
search increment 3da4306c1. This record's source/manifest SHA values are in the
sanitized receipts; commit identity follows in Git history.
No vehicle applicability, promotion, production controller, CAN, Params,
CarController, network, device or persistent profile changes.

## Original references
Reuse CyberPilot's pinned LatControlTorque c8fb906815530460ed156f14e09e1f312bb0f851
and opendbc 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76; existing project licenses.
No foreign implementation or new dependency.
Frozen policy SHA 7bc06b4f58d72a623cc6966b2fa7e6e4048243c457276323a8961309a39ebe96
was committed before first v2 output. Reuse existing plant, worker/public replay,
attribution and exact baseline/CURRENT alias contract.

## Changes and expected effect
curvature_yaw_v2_robustness.py enumerates nominal sharp_high_left plus 22
single-axis perturbations, in deterministic sorted order. Each case freezes
four role requests, source/config/identity, input/timebase and fresh controller
reset before two native repetitions per role. 23 x 4 x 2 =184 native runs.
Full final EVAL reports, ordered manifest-list and selection are admitted
before stress execution. Matrix freeze includes that EVAL context and separate
stress producer SHA; check before every case and after completion. Aggregate
revalidates all complete reports and rejects missing/reordered/incorrect
selection/config/matrix anchors; caller summaries cannot replace native proofs.

Ranges are small local software sensitivity probes, NOT confidence intervals
or calibrated vehicle uncertainty. Policy fixes delay steps1/3 around nominal2,
curvature gain terms x(1 +/-1/128), yaw AR +/-1/128, common CP software friction
x(1 +/-1/128), speed25 +/-1m/s, roll +/-0.002rad, initial curvature
+/-0.00015/8 (1/m), initial yaw +/-25*0.00015/8 rad/s, observer y +/-0.01m,
pressed/release and re-engagement transitions +/-1frame (10ms). Last two axes
use reengage_high; all other cases use sharp_high_left. Observer pose never
enters native controller input. CP friction is a common isolated software
fixture before all-arm freeze, NOT physical road/tire friction or a Params/profile
write. No random seed, factorial coverage, smoothing, physical queue or output
scale/bias/clipping added. Original A1 whole-run bounds stay fixed.

Producer and persisted validator now derive public replay dt and physical delay
from the frozen plant config. Native controller reference history remains the
same prediction mechanism; PLANT alone owns the command FIFO. FIFO length/reset
matches selected delay. Source identity changes with this harness correction;
the same frozen search policy was rerun in a fresh experiment directory, including
all DEV and EVAL before the corrected matrix. No result-driven range/threshold
change or EVAL reselection.

## Regression risk and acceptance
Original frozen comparator, distinct-arm policy and A3 rejection unchanged.
Experimental CURRENT=BASELINE remains explicit, never a third unique controller.
HIGH per-cell no-worse vs baseline and LOW/MID retention vs v1 remain exact IEEE
rules across eight separate metrics, without weighted compensation. Stress
subset cannot promote a rejected final evaluation. Result reports both
selected_candidate_status and stress_screen_status, with rejection precedence.
Worst absolute values are independently reported for baseline/v1/v2, plus
separate v2-minus-baseline/v1 maxima for each metric/unit. Baseline pathology
remains visible even when candidate delta is zero. Checksum/internal physical
consistency is not externally authenticated execution.

Only left sharp high-speed nominal and timing re-engagement are covered here.
No low/mid transition matrix, calibrated plant validation, real lane reference,
or vehicle safety conclusion. Independent review found the old nominal-only
delay domain mismatch; targeted actual 1/3-delay tests fail RED and pass GREEN
after correction. The first stress run (21 admitted,2 harness replay failures)
is INVALIDATED as robustness evidence; its failures are retained locally,
not misreported as candidate performance defects.

## Validation method and actual results
Fresh run-policy-v1-delay-admitted: nine DEV configurations, only(0,0) eligible;
same final REJECTED37. Fresh stress-policy-v1-delay-admitted:23/23 hard-pass,
0 hard failures,23/23 no-worse screens,0 regression buckets.
selected_candidate_status=REJECTED; stress_screen_status=TRADEOFF_ONLY;
aggregate status=REJECTED. Candidate equals baseline in every stress sample.
V1 comparison has mixed tradeoffs; no synthetic or vehicle winner.

Worst candidate absolute diagnostics below also equal baseline at these cells;
independent baseline/V1 maxima and all per-case cells are in sanitized receipts.
They expose a poor generic baseline, NOT satisfactory driving.

| Metric (separate native units) | Worst value | Scenario / perturbation / phase |
| --- | --- | --- |
| applied_torque_derivative_rms_per_s | 142.5614110862567 | reengage_high / {'reengage_shift_steps': 1} / exit |
| command_derivative_rms_per_s | 186.9459392648423 | sharp_high_left / {'curvature_gain_fraction': 1.0078125} / exit |
| curvature_residual_rmse_1pm | 0.02426008101395239 | sharp_high_left / {'delay_steps': 3} / exit |
| native_aligned_residual_rmse_1pm | 0.025022801659972824 | sharp_high_left / {'delay_steps': 3} / exit |
| reversals | 55 | sharp_high_left / {'delay_steps': 1} / apex |
| saturation_occupancy | 1.0 | sharp_high_left / {} / exit |
| steering_residual_rmse_deg | 92.08055114746094 | sharp_high_left / {'delay_steps': 3} / exit |
| zero_crossings | 56 | sharp_high_left / {'delay_steps': 1} / apex |

Sanitized candidate-v2-robustness-results.json and three stress receipt archives
recompose the exact original summary SHA. No native response, CP wire payload,
raw log/image/route or browser binary artifact is committed.
candidate-v2-delay-domain-search-results.json records new source-bound DEV/EVAL
selection/case receipts, full selection vectors and EVAL summaries; it is explicitly
a projection, with original full summary SHA. Older nominal search archives remain
valid historical records; earlier incorrect-delay stress run remains INVALIDATED.
TDD and focused57/57 PASS; actual delay1/3 public-repeat and persisted-admission
regression passes. Complete-matrix failure-receipt tests cover missing/reordered/
wrong anchor cases, plus final EVAL context mutation and rejection precedence.
Full AutoTune937/937 PASS (255.12s); SCons100% PASS with prescribed .venv PATH
and -j2; Ruff, py_compile, authority AST/grep, privacy/publication and diff checks PASS.
publication_check393 changed files /0 findings. Ubuntu24.04 / Python3.12.13.
Independent read-only review: one Important delay-domain defect fixed, no further
Critical/Important findings; matrix branch tests strengthened following minor
coverage note. Historical hashes identify source-bound runs separately.

| Stage | Method and identity | Actual result and limits |
| --- | --- | --- |
| Native replay | Frozen four roles x2; public transcript admission | Exact repeatability, CURRENT alias; internal consistency only |
| Synthetic closed loop | Frozen policy/selection/EVAL plus23 OAT manifests | Diagnostic sensitivity, no vehicle uncertainty guarantee |
| Shadow / real qualification | Independent lane/path truth required | BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE; not run |

## Handoff
A constant25m/s (0,0) hypothesis removes v1's high-speed parameter deltas;
it does not remove the generic baseline's strong saturation/oscillation.
Good stress subset results cannot erase the37 final EVAL cell violations
(sharp_mid_left21; speed_sweep MID10/HIGH6). Mixed-speed dynamic state remains
a plausible contributor, not a uniquely identified cause.
Rollback separate stress module/tests plus the two replay-domain lines; preserve
existing evidence chain and historical receipts. No vehicle activation authorized.
Next engineering: show these adverse raw-aligned diagnostics in the offline
viewer and validate actual loopback browser rendering. A future family would
require a new policy version frozen before output; do not alter this run.
