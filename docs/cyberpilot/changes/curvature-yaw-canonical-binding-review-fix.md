# Canonical native and screening binding review fix

## Identity and purpose
Cyber Validation, implemented consistency fix following independent read-only
review of 57489486a through cc8dc181a plus pending visualizer.
feature/cyber-autotune; source-bound uncommitted patch. Purpose: reject JSON type
aliases and inconsistent self-rehashed reports, without changing measured control.
Santa Fe synthetic software fixture only.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED.

## Original references
CyberPilot MIT native v2 producer/runner and declared-equivalent synthetic report,
commits 06dfcd8c7 and cc8dc181a. Native core remains pinned upstream
c8fb906815530460ed156f14e09e1f312bb0f851, opendbc
4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76. No model/foreign code/dependency.
Independent reviewer traced request → expected CP schedule → native response
binding → sanitized screening manifest → renderer. Two P2 findings:
Python equality allowed 0.0/False/int aliases with original response hashes;
rehashed reports lacked strict field shape and recomputable identity validation.
Adoption: fix exact consistency invariants; keep all authenticity/truth disclaimers.

## Changes and expected effect
curvature_yaw_native_runner.py compares canonical response spec/effective rows
with canonical expected values and checks digest of actual supplied content.
Version 1 admission and controller output are unchanged.
curvature_yaw_screening.py uses canonical exact request/config/manifest equality
before workers; strict manifest version, HEAD/source/environment/digest fields;
recomputes frozen frames, selected config/active source/controller/producer SHA.
Canonical comparison also protects diagnostics and exact alias sample equality.
Three new test methods in candidate/screening tests cover type/hash drift and
failure before any worker; no test/metric/bound/ignore is loosened.

Report request hash cannot be reconstructed without omitted CP bytes/source-root
request contents. Effective-parameter hash cannot be reconstructed without bound
CP baseline-wire values. Native result/envelope hashes and steering/saturation
observations are provenance declarations here, not proof of execution authenticity.
Shape-checking these is explicit; existing producer result validation checked
actual schedule before the original structural report was emitted.
Physical plant/pose replay and recomputable bindings are consistency checks.
This distinction is retained in visualizer warnings. No new acceptance threshold,
physical constant, timing/state/reset behavior or candidate selection.
No live controller/safety/CAN/Params/network/profile/CarController/vehicle change.

## Regression risk and acceptance
Strict JSON canonical binding intentionally rejects 0 vs 0.0 response/config drift
as well as boolean substitutions. Generated native output is already canonical
to its declared request. Old valid historical reports remain viewable; stronger
consistency checks reject self-rehashed malformed metadata.
Holdout: not applicable, no search/selection. Same thirteen frozen scenarios,
same schedule and diagnostics; adverse results must remain numerically identical.
Rollback: revert only binding checks/tests, retain separate opt-in pipeline.
Reviewer: independent read-only code reviewer, original findings and re-review
recorded below. No promotion or vehicle application authority.

## Validation method and actual results
Ubuntu 24.04 WSL Python 3.12.13.
RED: 21 candidate/screening tests, 18 failing subcases reproducing the review gaps.
GREEN: focused 46/46 PASS in 29.978 s, includes v1 parity, native repeatability,
physical replay, declared alias, strict report, viewer controls/escaping.
Independent re-review: both P2 findings resolved; original eight repros now
rejected and historical valid report preserved; no additional important finding.
Final 78 native runs / 78 public replays PASS; all thirteen cases exactly repeat.
Every prior command-difference and diagnostic value is exactly preserved; only
source/head/receipt bindings change. Updated catalog SHA:
ec7b9557f91fc97fbd5012702d2367d9325310a000baa55884234a2219e5a027.
Full AutoTune 901/901 PASS in 235.93 s (+28 tests from original 873).
Full AutoTune Ruff, compileall/py_compile, Node syntax, authority grep,
git diff --check PASS. publication_check: 372 changed files / 0 findings.
SCons 100% PASS with export PATH="$PWD/.venv/bin:$PATH"; .venv/bin/scons -j2.
Code tested before commits, with execution HEAD cc8dc181a and explicit changed
file/diagnostic source SHA bindings; no runtime outputs or thresholds altered.
Previous UI increment full suite 898/898 PASS in 235.14 s; this did not cover the
then-missing reviewed invariants, which required the new RED tests.

| Stage | Evidence and method | Result / scope |
| --- | --- | --- |
| Unit/regression/build | New canonical/type/hash RED → full gates | Focused 46 PASS; full 901 PASS; all build/static gates PASS |
| Replay | Existing native public transcript replay | All new catalog repeats required; no independent truth |
| Synthetic closed loop | Same fixed 13-case x six matrix | Diagnostic equality checked against prior snapshot |
| Real reference / shadow | No lane truth/device input | BLOCKED / NOT_RUN |

## Handoff
Structural admission and synthetic screening only. Actual performance qualification
remains BLOCKED. Production three-distinct-arm admission remains blocked by
CURRENT=BASELINE; the separate experimental alias contract does not weaken it.
Independent road/lane geometry and qualified calibration remain missing.
A1/A3 rejection and historical evidence audit unchanged.
No private raw data or generated detailed traces committed.
