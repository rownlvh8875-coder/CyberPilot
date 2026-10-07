# Native candidate declared-equivalent synthetic screening

## Identity, purpose and scope
Cyber Validation / Cyber Lateral. Starting implementation 06dfcd8c77bd3a1d3140f2fb524990ce1ea0388f.
Target: repository-owned Santa Fe software CP (factor 4, friction .125), not a vehicle tune.
Implementation complete: a separate offline experiment compares two unique native
controllers and one explicit exact baseline alias. Structural admission and
synthetic screening only; actual performance qualification BLOCKED.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

## Frozen arms and evidence boundary
UPSTREAM_BASELINE executes the unchanged pinned native core with current offline
producer infrastructure. git show verifies selected top-level native source bytes
against c8fb906815530460ed156f14e09e1f312bb0f851, and its opendbc gitlink
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. This is not a replay of a whole
historical upstream installation.
CYBER_CURRENT request is byte-identical to BASELINE, with alias_of declared.
CYBER_CANDIDATE activates the frozen bounded A1 combined factor/friction schedule
through native update_torque_parameters. Same CarParams, reset, frames, plant,
sign and execution checkout for all arms; no meaningless CP variation.

Active controller source SHA differs by the actually selected adapter dependencies;
configuration, request, producer, selected native/support files, CP, HEAD/opendbc,
environment, phases and diagnostic producer SHA are bound by the manifest.
All thirteen manifests and their ordered catalog SHA freeze before first worker.
No optimizer, best selection, new search range, acceptance threshold or policy.

This contract never calls the existing frozen three-distinct-arm production
comparator. That comparator and independent reference strict admission remain
unchanged. Historical source-audit snapshots and A1/A3 rejections remain historical
evidence, not rewritten successes. Real reference admission remains BLOCKED.

## Implementation and validation
New curvature_yaw_screening.py creates owned synthetic inputs, checks upstream
identity and exact alias/common basis, admits the entire candidate schedule and
checks owned CP/source/support before any worker. Canonical copy prevents caller
mutation. Source checks run again in each isolated worker.
Each arm executes twice from fresh controller/plant state; exact whole result
equality and public feedback-bound adapter replay are mandatory. Failure emits no
partial success report. Six runs are required, including both baseline aliases.

Thirteen 401-frame, 10 ms cases: low/high gentle and sharp left/right, low/high S,
low/high override/inactive/re-engagement, fixed speed sweep 5 to 25 m/s.
Demand, phases and descriptive plant coefficients are fixed, with no lane geometry.
Requested torque, applied delayed torque, native pre-step steering angle,
post-step actual plant curvature, yaw, heading, pose x/y and phase are reported.
Pose x uses the same heading integration convention as the existing pose-y observer.
Inactive torque is zero; pressed retains native driver/integrator semantics.
Fresh repeats verify reset; no additional controller physical-delay queue.
Only the plant owns the two-frame physical delay.

Diagnostics: command derivative RMS/max and total variation; nonzero-sign
zero crossings, derivative reversals/rate (descriptive oscillation proxy, not a
physical comfort measure); native saturation occupancy; curvature RMSE overall
and by predetermined phase; pose-y excursion. No lane-center/edge metric.
Receipt validation checks hashes, scope/authority, exact alias, finite/bounded
samples, frozen inputs, diagnostics and physical plant/pose replay. A self-hash
establishes internal consistency, not authenticity of native execution or truth.

## Results, failures and interpretation
Focused 36/36 PASS, including eleven new tests. Test-first missing-module RED.
Additional RED caught yaw-equivalent curvature sign and rehashed physical-trace
tampering. Curvature is now taken from the plant state directly: this plant's yaw
target convention is negative curvature times speed. No plant equation changed.
Additional RED showed support drift could start the first worker; parent preflight
now rejects it before any of the six executions.

Final catalog run and sanitized aggregate snapshot are recorded in
curvature-yaw-synthetic-screening-results.json. All cases show nonzero candidate
commands/trajectory differences, exact repeats and BASELINE=CURRENT alias.
At high speed the descriptive plant produces severe saturation and oscillation
for both controllers. Candidate sharp-high curvature RMSE and derivative RMS
worsen; re-engagement-high and speed-sweep also worsen some metrics. Low-speed
differences are small. No retuning after observing these results.
These failures cannot be interpreted as physical vehicle behavior or improved
lane centering. No qualification/acceptance/pass threshold is applied.

## Reproduction, privacy, license and rollback
Linux native execution:
.venv/bin/python -m openpilot.tools.cyber_autotune.curvature_yaw_screening --scenario all --output /tmp/cyber-screening.json
Or select one enumerated synthetic scenario. Output is synthetic, has no raw
route/image/log or source-root path. Only sanitized aggregate diagnostics are
committed; detailed generated traces stay local.
Existing CyberPilot MIT implementation only; no new dependency/foreign code.
No runtime/controller/profile/CAN/Params/network/device/safety/comparator edit.
Rollback: revert this standalone experiment/tests/snapshot; opt-in candidate
and production evidence boundaries remain independent.

## Verification and remaining work
Full AutoTune 891/891 PASS in 233.81 s (873 original + 7 candidate + 11 screening).
Ruff, py_compile, authority grep (no authority writers), git diff --check PASS.
publication_check: 366 changed files / 0 findings. SCons 100% PASS using
export PATH="$PWD/.venv/bin:$PATH"; .venv/bin/scons -j2.
Final catalog: 78 native runs, 78 public replays; all thirteen cases repeated exactly.
Catalog SHA-256: 85ff09f3203edd65e3b7e043f6aed1d8a7240ff0565b5f7d0db60046b3c821dd.
Historical snapshot uses the execution HEAD plus explicit diagnostic producer source
SHA because the experiment module was under development during this run.
Actual performance qualification / real reference / real vehicle readiness:
BLOCKED / UNAVAILABLE / NOT_READY. Next: standalone offline visualizer and final
review, keeping warnings and all regressions visible.
