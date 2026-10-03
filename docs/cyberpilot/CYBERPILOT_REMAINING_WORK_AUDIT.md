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

## 2026-10-04 continuation after the offline completion checkpoint

Base: `cfa169896ad2efd913ec2f99e968ece1fed8c475`, initially clean and matching the
local origin tracking ref. This continuation does not rewrite the prior publication
receipt or declare the original STEP1-10 goals done. Git delivery is checked
separately after the final verification below.

Completed bounded work:

- [Candidate diagnostics](changes/synthetic-candidate-failure-diagnostics.md):
  preserve original verdicts, separate delay variants, show metric direction and
  effective output changes, reject incomparable evidence before summarizing it.
- [Native longitudinal feedback parity](changes/cyber-long-native-feedback-parity.md):
  independent native planner/LongControl/generic-plant loops for lead transitions,
  true standstill/restart and supplied driver cancellation/reengagement. No sockets
  or actual device actuation; not a full coupled-process replay.
- Independent source review corrections are covered by regression tests. No
  policy, controller behavior, active profile, safety limit or holdout changes.

| Check | Result |
| --- | --- |
| Final AutoTune + controls supported runner, `-j 1` | PASS: 619 tests, exit 0, 124.95 s |
| Focused lateral process-replay tests | PASS: 16 tests and 4 subtests, exit 0 |
| Ruff / compileall / whitespace | PASS on changed source and applicable existing modules |
| SCons `-j2` | PASS, 100%, exit 0 |
| Full fresh-worker synthetic comparison twice | PASS for exact repeatability; candidates still REJECTED |
| Preserved-report diagnostic reader reruns | PASS for identical output bytes; not native qualification |
| Publication scanner | PASS: zero findings, including new untracked files; rechecked at handoff |
| Repository-wide default runner `-j 2` | FAILED execution: exit 1 without final summary; no full-suite PASS |
| Instrumented default-runner attempt | FAILED execution: exit 1 without final summary/traceback; cause unresolved |
| Later per-test/supervised default-runner observation | BLOCKED: explicit 900 s observation deadline; child terminated by SIGTERM, not a completed test verdict |
| Fresh overnight AutoTune + controls, `-j 1` | PASS: 619 tests, exit 0, 122.84 s |
| Final verified-fixture default runner, `-j 2 -v` | PASS: 1,526 passed, 42 skipped, 1 xfailed; exit 0, 353.59 s |
| Vehicle-calibrated qualification / live shadow / deployment | NOT_RUN, vehicle activation BLOCKED |

Both full-run attempts were bounded to 300 seconds. A local-only exception-tracing
wrapper left the runner/tests/filters/assertions untouched. It did not expose the
termination cause; no remaining Python/timeout processes were observed afterwards.
Do not infer a named failed test, an OOM, or the historical loggerd audio failure
from this symptom. The targeted final suite succeeded independently. At that point
full-suite verification was incomplete and publication remained blocked pending
the final verified-fixture run recorded below.

Later observation separated the shell result from the actual child result. An
external supervisor recorded `timed_out=true`, child returncode `-15` (SIGTERM)
and elapsed 900.018 s. Before that deadline the unchanged default suite recorded
1,483 individual passed, 32 skipped and one expected-failure stop event, without
a failed/error/unexpected-success event. These partial events are not a complete
suite PASS and do not count fixture-level skips that never start a test.
The outstanding worker stayed in `TestLagd.test_read_invalid_saved_params`, whose
first operation loads upstream's public CI log for CarParams. A separate bounded
stack diagnostic reached SSL response reads through URLFile and LogReader. An
HTTP206 range probe received only 327,244 bytes in 20.003 s from that public CI
fixture endpoint. This supports an external-transfer bottleneck for the observed
run; the two older attempts have no equivalent child receipt and remain historical
incomplete executions, not proven named test failures.

No assertions, time limits inside tests, collection rules, warnings, production
code, cache policy or replay reference were changed. The 900 s observation budget
belongs to the external diagnostic supervisor, not an acceptance threshold.
The next environment-only step was to verify the exact public upstream fixture bytes
against their server content length and digest before using the existing local
`DATA_ENDPOINT` source option. A mirror is not a replacement synthetic fixture,
and incomplete downloads must not be exposed as valid inputs. No user driving
logs or additional driving-data request is involved. Fresh Ruff, whitespace,
SCons and zero-finding publication checks passed; the full-suite publication gate
remained open until the unchanged full run in the verified environment below.

New complete synthetic output SHA-256:
`9443899865794b59c731babd5754936c3488bb4204aa8a0c46059dcec2b9cf90`.
All 200 first-repetition case/arm trace identities (including unavailable fault
entries) are unchanged from the preserved artifact. Its original SHA remains
`4e5145c0b2385f08105657c059ee0c072660c62c46115f952700dad41af5e5f5`.
Frozen v2 policy SHA remains
`4ff9dcfaa369cbdcee53f56a8db9c160efb3005a50f463e4125a1f41b74e8d35`.

Final code/test content identities:

- `synthetic_diagnostics.py`: `72823a4fcd0636afdcb0dbfc80f2bba160dda8ddc6ccfde1726bbf22b5f3cee3`
- `test_synthetic_diagnostics.py`: `61721b6b281df4f9cad4fc44e856beecd3deec498f9f3a41fc55881ba2c4396b`
- `test_cyber_long_feedback.py`: `41d9b8de76ac7d30697cbbe5b6591e76b90345a72bfb94c7503429f1a016d847`

The historical full-suite publication blocker above was subsequently resolved:
the exact public upstream CarParams fixture was fully downloaded and independently
checked against server length and Content-MD5 before using the existing local
`DATA_ENDPOINT` option. Failed/partial download attempts remain local evidence;
no partial file was presented to tests. The final unchanged default runner completed
in 353.59 s with 1,526 passed, 42 skipped, one expected failure and actual exit 0.
The external supervisor recorded no timeout and identical before/after source,
submodule, overlay and fixture identities. Its receipt SHA-256 is
`ef6ebc76b01eb43dbbd4d91e10a53238e6ba3fd3011f3a7d10336dfa8ce55feb`.
The previously stalled CarParams test passed in 1.895 s. The slowest remaining
network test completed in 134.17 s. Existing skips, warnings, tests and references
were not changed; no private driving data was used. Local diagnostic-wrapper
tests and independent review additionally covered durable exit receipts and owned
child cleanup. The default suite is software regression coverage, not qualified
process replay, vehicle-calibrated simulation or device shadow.

Remaining order: define bounded planner-coupled performance evaluation and effective offline
candidate domains. Multiplying the pinned Santa Fe zero Ki cannot test a new
longitudinal tune. Active Carrot cut-in/comfort, accepted lateral optimizer,
qualified replay/calibrated plant and continuous device shadow remain incomplete.
No new driving data is requested. REAL_VEHICLE_UNVERIFIED and
VEHICLE_ACTIVATION_BLOCKED remain unchanged.

## Planner feedback measurement checkpoint

Follow-up from `2a17919614632c4dd6f72cac65a09f6751b1ed07` adds
[separate interval-aligned measurements](changes/planner-feedback-measurements.md)
to the existing native feedback fixture. Original parity trace values remain
exactly equal to the preserved Git-object fixture; four native reference/current/
observer arms agree. No controller, frozen metric/policy, plant calibration,
parameter bound or candidate verdict changes.

Focused10tests and combined AutoTune/controls626tests passed. New full default
suite:1,533passed /42skipped /1xfailed,exit0,249.50s, with unchanged source and
verified public input. Ruff, SCons, publication audit and independent review pass;
two complete fresh-process aggregate reports are byte-identical. Exact source and
receipt identities and descriptive metric values are in the linked feature record.
These results supersede the earlier counts only for this new executable overlay;
historical evidence above is not rewritten. Test-only helper identity necessarily
changed to emit separate rows; its prior hash remains a historical identity.

This completes descriptive planner-coupled measurement, not performance acceptance.
Desired-follow and stop-position errors remain null without independent targets.
Effective vehicle gain search remains BLOCKED by zero stock Ki and unreviewed
bounds. Do not insert an arbitrary nonzero gain or tune a generic plant as if it
were the user's vehicle. Qualified replay, calibrated simulation and device
shadow/activation remain unverified; all vehicle authority remains disabled.
