# Remaining offline engineering audit

Audit baseline: `abdcb5e88acc24c8567accc949c2b7740b3ef02a`,
`feature/cyber-autotune`. Fresh fetch showed origin and local HEAD identical.
This document was absent at resume; it is a new evidence-based inventory, not a
reconstruction of an unobserved completion report.

## Scope and status

Target/current engineering status: `ENGINEERING_COMPLETE_OFFLINE_ONLY`.
This is the supplied-plan native-core/rehearsal scope, not perception or vehicle qualification.
Vehicle status: `REAL_VEHICLE_UNVERIFIED`, `VEHICLE_ACTIVATION_BLOCKED`.
No new driving data is required or requested for this engineering scope.
Historical physical qualification failures remain visible and are not software
completion prerequisites. Synthetic results never qualify a real vehicle.

## Existing work to preserve

| Area | Existing implementation | Remaining engineering work |
| --- | --- | --- |
| Long | native LongControl plus 18 synthetic supplied-plan cases and metrics | actual lead/signal/radar planning and vehicle qualification unverified |
| Lateral | preserved v1; v2 26-case fixture catalog and native generic closed loop | lane-perception behavior and independent physical truth unverified |
| AutoTune | prior identification/profile modules plus memory-only frozen candidate grid | both candidates rejected; no active tune |
| Closed loop | structural receipts and new repeated same-core identity/candidate matrix | calibrated physical plant still unavailable; no qualification claim |
| Shadow | bounded windows plus active-byte/count/input noninterference and restart tests | live control scheduling/bus consumption not exercised |
| Profiles | durable archive plus immutable offline activation/rollback receipt state machine | actual vehicle activation/rollback deliberately absent |
| Publication | reviewed fail-closed history/index/worktree privacy scanner and CI | hosted CI outcome separate; final push verification follows commits |
| Documentation | audit, branch completion, validation update, Korean manual/release checklist | no vehicle-use approval |

## Frozen evidence versus future work

Do not modify existing policies, historical results, holdout, H1/H2, safety,
control limits, upstream references or default experimental flags. New coverage
must use separately versioned synthetic inputs and predeclared policy. Existing
rejected candidates remain rejected. A software test of rejection is not candidate
performance acceptance. Provided avoidance paths and stop targets do not test
perception or traffic-signal recognition.

## Execution ledger

- [x] Read Git history/status, fetch target branch, preserve inherited untracked files.
- [x] Read validation and source modules; establish that both requested completion
  documents were absent.
- [x] Finish publication guard and CI; targeted negative tests.
- [x] Extend lateral scenario execution/metrics with immutable v1 compatibility.
- [x] Add longitudinal synthetic closed loop and metrics.
- [x] Integrate memory-only candidates, predeclared gate and repeatability.
- [x] Verify offline-window shadow noninterference and profile rollback rehearsal.
- [x] Complete documentation and independent review.
- [x] Final targeted tests, AutoTune+controls, replay, Ruff, JSON, diff check,
  SCons, deterministic reruns and zero-finding publication audit.
- Git delivery is verified after committing the report: logical reviewed commits,
  ordinary fast-forward push, clean worktree and local/remote equality.

## Resume diagnostics (not completion evidence)

Initial inherited publication/workflow tests: 12 passed, 1 failed subtest,
26 subtests passed. The workflow test compares a folded YAML command to its raw
source line, producing a formatting failure. Scanner inspection also identified
missing staged/unstaged discovery and silent skipping of unreadable/binary/large
files. These were fixed with negative tests and independent review. They remain
recorded here as initial failures, not misrepresented as a continuously green run.

## Design ruling

Use existing offline workers, plant, archive and gates; add versioned adapters and
scenario inputs only where coverage is missing. Replacing the whole framework
would discard established evidence; declaring completion from existing unit tests
would omit user requirements. Perform changes inline with test-first validation.
The user explicitly delegated intermediate design decisions and prohibited waiting
for approvals; record those decisions here. Commit/push only after final gates.
