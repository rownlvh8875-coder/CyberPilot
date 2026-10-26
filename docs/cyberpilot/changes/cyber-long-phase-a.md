# Cyber Long Phase A — observer connection

## Identity and purpose

- Area: Cyber Long / Validation. Status: observer seam implemented; native synthetic parity passed; broader validation pending.
- Purpose: observe stock candidate arbitration without changing follow, stop/start or accel/decel.
- Scope: DISABLED by default, optional OBSERVE_ONLY; no active comfort/cut-in, schema or actuator authority.
- Vehicle applicability: no vehicle qualification; all stock vehicle capabilities/limits remain authoritative.
- Branch: feature/cyber-long; baseline c8fb906815530460ed156f14e09e1f312bb0f851; uncommitted file hashes in verification record.

## Original references

- commaai/openpilot master c8fb906815530460ed156f14e09e1f312bb0f851 (fresh fetch 2026-09-29), root MIT LICENSE preserved.
- Planner: openpilot/selfdrive/controls/lib/longitudinal_planner.py, update candidates → min / stop OR / clip / feedback → publish.
- Consumers: longcontrol.py → controlsd.py → card.py → pinned opendbc → panda. These consumers remain unchanged.
- opendbc 4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76; panda 92eb565169fd553f4dfaf508c1a3f8dbc14fbfbf, uninitialized.
- Model/firmware provenance unavailable; observations are explicitly incomplete, not qualified replay/shadow evidence.
- Carrot carrot2-v6 c57d0ff11f766b7fd70e9a9eaec1247b623ffbea informs conceptual diagnostic separation only.
  No Carrot code copied; its file-level license/effect gates remain unresolved. See ../../CYBER_LONG_DESIGN.md.

## Changes and expected effect

- New cyber_long/types.py, policy.py: immutable snapshots and diagnostic lifecycle.
- Minimal planner constructor option / isolated observation call before unchanged arbitration.
- New portable contract, isolated-boundary and native differential tests; no live publication of diagnostics or new daemon.
- Expected control effect: none. Disabled has no additional SubMaster reads; observation returns None.
- Configuration epoch is a nonnegative identity counter, not a control parameter. Timestamps are monotonic nanoseconds.
- No new freshness/control numeric thresholds; consume upstream validity and ordered timestamps.
- Reset on driver input, inactive/reset, invalid/nonfinite inputs, repeated/reversed model or reversed asynchronous input time,
  binding change and observer failure. No retained diagnostic presented as fresh after reset.
- Rejections/faults invalidate diagnostics while retaining session input high-watermarks; known failing frame identities are
  consumed, so repeated/reversed frames cannot become fresh after an exception. Explicit new-session reset clears all state.
- Only diagnostic state changes; min candidate order/ties, all-candidate stop OR, clipping and feedback remain stock.
- Synchronization risk: planner update/reset/candidate seam may change upstream; rerun frozen-baseline parity before promotion.

## Regression risk and acceptance

- Risks: optional code exceptions, stale diagnostic identity, extra hot-path cost; no performance/safety improvement claim.
- Acceptance: exact deterministic scalar/state equality and numpy array equality vs frozen baseline, not tolerance expansion.
- Synthetic fixtures cover stop/start/lead/cruise/model/ties/OR/reset/driver/fault; no private driving data included.
- Rollback: retain default disabled; remove focused planner seam and independent package if needed. No Params/config persistence.
- Reviewer: fresh whole-change code review; promotion/real-vehicle authority remains with user, not granted by PC tests.

## Validation method and actual results

Planned: portable unittest and upstream runner; configured Ruff; real native planner/LongControl differential checks;
affected/full upstream suite; replay → closed-loop simulation → non-actuating shadow with reviewed input identities.
Actual: 13 observer and 5 isolated-boundary methods pass; 30 portable methods including admission pass.
The boundary suite executes actual extracted observer code only, not MPC/LongControl or whole-planner parity.
Native integration: exit 1, zero tests / one numpy collection error. Controls: 30 pass / 7 collection errors.
Full runner: 30 pass / 66 collection errors. See [implementation verification](../analysis/CYBER_LONG_IMPLEMENTATION_VERIFICATION.md).
Missing submodules/native assets and unsupported Ubuntu version cannot become PASS by substituting mock controllers.

Follow-up authorized native verification (same date; earlier results above retained): separate Ubuntu24.04.5,
exact six gitlinks initialized in an ext4 validation replica, Python3.12.14 and frozen dependencies.
Actual native parity: 5 passed, exit0; affected controls: 63 passed, exit0; longitudinal maneuver regression:
4 passed, exit0; full default scons build: exit0. Portable 30 also passed in the new environment.
Candidate source/test hashes unchanged; all 252 pinned root LFS assets verified by SHA256 and size.
The native parity includes real MPC and frozen upstream LongControl; its isolated arbitration method
is still separately labeled. Full runner was interrupted (exit2) on TLS-dependent log preparation and is not PASS.
An explicit partial rerun reproduced missing clang++ and TLS errors; clang preparation resolved the former
(services suite71 passed). The corporate CA trust decision remains a separate user approval.
The earlier unsupported-environment/import block is resolved in this replica, not erased from history.

Further authorized TLS follow-up: exact Windows-trusted public CA in a separate command-scoped bundle,
no private key export, permanent trust-store change or TLS bypass. Same unchanged candidate:
full default runner exit0 (954 passed / 42 skipped / 1 xfailed, 307.62s, collected1029),
controls rerun exit0 (63 passed, 28.10s). The PC hardware fixture collapse explains the32-record
collection/result difference (43 methods → 11 fixture skips); no test/skip/threshold changed.
These results supersede the current TLS blocker only; historical failures remain above.
See verification section9 for hashes, source preservation and remaining qualification gates.

## Handoff

- Verified vs expected effect: synthetic diagnostic/rejection contracts and stock update/publish AST preservation checked;
  native synthetic planner/control parity now established; whole qualification is not. No real-vehicle or empirical improvement claim.
- Replay/simulation/shadow and vehicle qualification: not run, not authorized as device operations.
- Publication follow-up: the user subsequently authorized commit/push to feature/cyber-long. No PR, develop/main promotion or road/device operation is included. Fresh controls regression passes63 (29.17s) and affected-file Ruff passes before publication; see verification section10. Next check remains fixed Cyber Long replay inputs/metrics and Phase B evidence/license/bounds review.
