# CyberPilot branch completion

Engineering status: `ENGINEERING_COMPLETE_OFFLINE_ONLY`.
Vehicle: `REAL_VEHICLE_UNVERIFIED`; `VEHICLE_ACTIVATION_BLOCKED`.
Vehicle readiness: `NOT_READY`. Local validation date: 2026-10-04 KST.

This file did not exist at resumed baseline `abdcb5e88`; it records new evidence,
not a reconstruction of an earlier claim. Completion refers to the offline native
controller-core framework, defensive gates and rehearsals below. It does not mean
all planning/perception behaviors are exercised or a useful vehicle tune exists.

| Final gate | Status |
| --- | --- |
| 26 lateral / 18 longitudinal supplied-input fixture catalog | PASS, 50 separate delay variants; scope limitations below |
| AutoTune+controls regression | PASS, 607 tests, exit 0 |
| Focused lateral process replay tests | PASS, 16 tests / 4 subtests, exit 0 |
| Ruff / policy JSON / diff check | PASS, exit 0 |
| SCons `-j2` in activated existing environment | PASS, 100%, exit 0 |
| Two complete deterministic runner executions | PASS, byte-identical `cmp`, exit 0 |
| Privacy audit | PASS, zero findings; repeat against final index/history before push |
| Independent review | PASS after fixes; no remaining blocking scoped findings |
| Hosted GitHub Actions | NOT_RUN at local validation; local workflow tests PASS |
| Git delivery | Verify ordinary fast-forward push, clean tree and remote equality after committing this report |

## Implementation and evidence

Versioned synthetic inputs/metrics, memory-only candidate sandbox, exact input
and source bindings, one plant-owned physical delay, bounded fresh processes,
strict identity A/A and repeated A/B, rejection reports and complete failure
handling are implemented. Existing frozen v1 policies/results were not changed.

Each arm executes 43 nominal variants and rejects seven actually malformed inputs.
Baseline/current identity and each candidate are repeated twice; the entire runner
was then repeated twice. Full output SHA:
`4e5145c0b2385f08105657c059ee0c072660c62c46115f952700dad41af5e5f5`.
See the [sanitized aggregate receipt](changes/offline-completion-v2-receipt.json)
for source/policy/metric/environment identities. Full synthetic aggregates remain
local; no private driving logs, routes, paths, CP blobs or simulator code are added.

Both candidates are **SYNTHETIC_CANDIDATE_REJECTED**: gentle has 192 unique
case/metric regressions plus insufficient primary improvement; firm has 133
regressions despite improvement on a primary metric. The criteria were frozen before
candidate execution and were not adjusted to obtain acceptance. Example baseline
constant-left/right center RMS is about 0.71255 m in this generic experiment;
straight RMS is zero. These are synthetic outputs, not acceptable real-vehicle
tracking performance. False-stop fixture measured 1.60 s stopped under an incorrect
supplied stop demand; this is observation, not an improvement claim.

Shadow normal/failure/restart integration: active output bytes, command count and
input digest unchanged for both axes (one integration test, six subtests), with
existing queue/expiry/timeout/reap tests retained. Native worker entrypoints cap
CPU at 60 s, address space at 2 GiB, core dumps at zero and math-library threads at
one. This does not bound host scheduling jitter or prove active-loop timing.

Snapshot rehearsal: five tests cover immutable selection, blocked activation
even after operator confirmation, ordered rollback, partial/corrupt/version/source
rejection, actual process interruption, fresh-process recovery, preserved crash
residue and fsync failures. Existing durable proposal/audit archive is reused.
No runtime writer or vehicle rollback operation exists.

## Scope and residual limits

- Baseline/current are fresh identity arms of the same native controller core,
  not two complete fork pipelines. No perception/planner or vehicle CarController
  executes in the new synthetic runner.
- Lane visibility and radar/model disagreement have no consumer at this boundary.
  Their decision behavior is unverified; lane-loss recovery is null, never zero.
  Timestamp jitter is separately rejected; pose-value jitter is a stress fixture.
- Supplied avoidance and signal-stop targets do not test obstacle/light recognition.
- Generic plants are not calibrated to the user's vehicle. Existing descriptive
  plant and historical candidate performance 0/6 blockers remain unchanged.
- Real-time scheduling, actual bus consumption and on-device shadow are NOT_RUN.
  Local immutable-window noninterference does not certify those behaviors.
- Hashes bind local contents, not authenticated producer truth; external Python
  dependencies are versioned, not authenticated supply-chain measurements.
- Worker output caps are post-capture within fixed trusted workers, not a hostile
  arbitrary-code sandbox. Crash tests do not prove hardware power-loss durability.

No additional driving data was requested or used. Remaining real-world uncertainty
does not reopen completed offline tests, but it continues to prohibit activation.
Follow the [manual preparation checklist](MANUAL_VEHICLE_EVALUATION_KO.md), not an
automatic installation or tuning workflow.

All six vehicle authority flags must remain false: `real_vehicle_verified`,
`runtime_accepted`, `active_profile_enabled`, `vehicle_write_enabled`,
`can_write_enabled`, `promotable_to_vehicle`.

## Verified diagnostic continuation

The follow-up from `cfa169896ad2efd913ec2f99e968ece1fed8c475` adds a read-only
frozen-report diagnostic reader and native planner/LongControl/generic-plant
feedback parity tests. It does not change any controller, safety limit, frozen
policy or candidate verdict. See the [continuation audit](CYBERPILOT_REMAINING_WORK_AUDIT.md)
and its two feature records for exact source identities and limitations.

The unchanged default software suite completed with 1,526 passed / 42 skipped /
1 xfailed, exit 0, 353.59 s, with source and verified public fixture unchanged.
Targeted AutoTune/controls coverage increased to 619 passed; the prior 607-test
checkpoint above remains historical. Earlier incomplete default runs remain in
the audit rather than being relabeled successful. This is a bounded offline
engineering extension, not completion of active cut-in/comfort, an accepted
lateral optimizer or the original full STEP1-10 vehicle objectives.

REAL_VEHICLE_UNVERIFIED, VEHICLE_ACTIVATION_BLOCKED and NOT_READY remain in force.

## A1 native application extension

[A1 synthetic native speed tuning](changes/a1-native-speed-tune.md) adds actual
factor/friction application, full-schedule admission, exact OFF/identity parity,
retained-state receipts and fresh-process repeatability. It does not establish
centering/comfort improvement or admit a real vehicle tune. Legacy v1 interfaces,
live controllers, safety code and the command-only optimizer guard remain unchanged.
Verification:38 targeted /654 AutoTune+controls /1561 default tests passed, with
42existing skips and1expected failure; Ruff, SCons, privacy and independent review
passed. The feature record retains failures, environment corrections and one
deferred minor reporting issue. Engineering completion is scoped to this offline
increment; original STEP1-10 vehicle objectives and activation remain incomplete.
