# Fixed-input persistent lateral IPC session

## Identity and purpose

Cyber Validation, STEP10 offline continuation on feature/cyber-autotune.
Baseline6dbf5e7031d9ffc5ceedb157274555fcbf3c9556. Implemented locally;
software gates pass on the final source; independent scoped review approved.
Actual Git delivery is recorded separately after final publication checks.
Preserve a single native lateral controller across separately submitted jobs in
one owned PC subprocess; support completed/aborted epochs without restarting that
child. This extends the prior finite-epoch cursor, not the live Shadow scheduler.
Only the existing fixed disabled601-frame synthetic fixture is admissible.

## References and call path

Source repository: https://github.com/rownlvh8875-coder/CyberPilot at the baseline
above. Reuse lateral_continuity._TorqueChunkCursor and its exact trace/state
validator, a1_experiment fixture/manifest, native_runner owned-process helpers and
worker_resources caps. Existing native MIT attribution retained; no external code
or new dependency. opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 and all
six submodule pins unchanged. No production control/safety/test/reference edits.

Call path: LateralSession -> exact-schema framed pipe message -> fixed isolated
lateral_session_worker -> EpochMachine -> existing native cursor -> checkpoint or
completed strict baseline/candidate comparison. Parent independently binds every
reply and validates completed data against the original native/continuity gates.
There is no new caller in controlsd, ShadowSession, LongShadowSession or vehicle I/O.

## Changes and expected behavior

- lateral_session.py owns one synchronous, thread-affine child and pipe exchange.
  OPEN/ADVANCE/FINISH/ABORT/CLOSE only; fixed worker executable path, no arbitrary
  command/transport/raw-log/configuration API. Handles bind session, epoch and
  source identity. Wrong-thread calls are refused without touching owner state.
- lateral_session_protocol.py checks version, sequence, epoch, source and exact
  progress; returns owned reply copies so clients cannot mutate native history.
  ADVANCE preserves native state and performs only its requested next frames.
  FINISH requires the entire preadmitted epoch; ABORT drops incomplete state.
  A new epoch starts a fresh controller on the same child. No retry/resume token.
- lateral_session_worker.py reuses source-only bootstrap and resource caps,
  rejects incomplete/oversized/malformed input and emits only fixed error codes.
- tests/test_lateral_session.py is the exact previously untracked20-test file,
  now executable without removing or weakening a test. New boundary tests cover
  output ownership, thread ownership, transport fragmentation/caps and cleanup.

Source/configuration bytes stay immutable across the child lifetime. Changed
bindings close the session and require a new process, never hot-reload already
imported code. This fixed synthetic configuration is not authenticated live Params
provenance. Caller frame streams, active profiles and user/holdout logs are absent.
Native reset/override behavior and all upstream control/safety limits are unchanged.

## Time, state and resource boundaries

The existing601-frame,10ms fixture is reused; positive frame counts and contiguous
start indices are checked, not interpolated or retimed. Random128-bit session IDs
are correlation-only, not credentials or approval tokens. Epoch numbers increase
monotonically. The existing60s ceiling bounds child lifetime including idle time,
and each exchange uses a separately supplied positive timeout no greater than60s.
This is not a real-time scheduler or an active-control-thread API.

PIPE_CHUNK_BYTES=64KiB is transfer granularity, not a physical tolerance. Existing
request/response byte limits bound each message; partial writes/reads are handled
without accepting extra lines. Native process-group helpers are reused for owned
kill/reap/exit confirmation; unrelated processes are never selected by name.
Cleanup failure cannot be reported as confirmed. Observed negative returncodes are
preserved; missing observations remain null. Child stderr/stdout details, paths,
PIDs and exception text are excluded from public failure receipts.

The parent requires its creating thread and either a context manager or
explicit close() in finally. Abandonment is not confirmed cleanup. Failure,
timeout, unexpected EOF or interruption ends the session; no automatic resend.
A cross-thread refusal is not cleanup of the owner's still-running session.
Partial checkpoints are observations, never completed qualification or output authority.
Only FINISH validates the full native trace/state and all previous checkpoints.

Alternatives rejected: restart per job/recompute prefixes (not persistence), raw
input streaming (unqualified input scope), or replacing existing async schedulers
(unnecessary expansion). Rollback is ceasing to use/reverting the offline module,
not applying a vehicle profile. Trusted local code, not a hostile-code sandbox.

## Validation and regression risks

Existing Ubuntu24.04 virtual environment; no forcedTMPDIR/install/test-filter
changes. Use unchanged verified-public-fixture default supervisor with a fresh
exclusive prefix. Default suite excludes full process replay/simulator coverage.

| Check | Actual result and limit |
| --- | --- |
| Prior missing-feature RED |20failed,exit1; historical preimplementation evidence, not a new run |
| First new implementation run |19passed/1failed of20,exit1; source guard order defect |
| Added boundary RED |9tests:1failure and1error,exit1; reply alias and wrong-thread close |
| Corrected original20tests |20PASS,18.102s,exit0; test file unchanged |
| Corrected boundary tests |9PASS,3.003s,exit0 |
| Final affected regression |89PASS,45.818s,exit0 |
| Final AutoTune+controls |737PASS,159.00s,exit0 |
| Final default verified-public-fixture suite |1644passed/42skipped/1xfailed,370.06s,exit0; source/fixture unchanged |
| Final Ruff/SCons/privacy/preservation |PASS; native build100%;9public files,zero scanner findings;old tracked files unchanged |
| Final deterministic repetition |2freshparents/2persistentchildren,4completedepochs/2aborts;871348completed-data bytes identical |
| Final independent source review |APPROVE;0Critical/0Important/0Minor;source-only,no reviewer-executed tests |
| Qualified replay/calibrated vehicle plant/device Shadow |NOT_RUN |

All initial failed attempts remain private evidence. A prior worker-draft write was
security-indeterminate and blocked; the same ordinary authorized write request
succeeded at resume without changed tool route, encoding, permissions or security
settings. It is not evidence about vehicle safety or a diagnosed code defect.
A private helper initially described9new boundary tests as10; actual discovery and
all reported test counts use9. No assertion/ignore/reference was altered to pass.

## Handoff and limits

This is bounded persistent IPC over fixed preadmitted lateral epochs. Existing
ShadowSession and LongShadowSession remain windowed. Two-axis synchronization,
unbounded/live input streams, actual runtime configuration history, integration
with live schedules and device latency/noninterference remain unimplemented or
unverified. No centering/comfort improvement, accepted tune or fullSTEP1-10 claim.
All authorities remain false. No new logs,protected evidence,private simulator,
CAN/device writes,active profile,road test or automation restart.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED persist.
Commit/push require every software gate and independent review; actual delivery
is recorded separately after verification, not assumed from this document.


## Independent lifecycle review correction

First source-only review: REQUEST_CHANGES,2Important/1Minor,0Critical.
Five new reproduction tests failed before correction (exit1,1.479s) and passed
unchanged after correction (exit0,1.497s; unused import only removed for lint).
The whole-life timer is now armed at worker entry before temporary-directory or
repository-import bootstrap. Parent supplies its absolute monotonic deadline, so
startup consumes, rather than extends, the existing60s budget. The standalone
bootstrap ceiling is checked against the inherited native supervisor constant.
The parent exchange also supervises initial interpreter startup. This is a bounded
trusted-code lifecycle, not a hard-real-time operating-system scheduling guarantee.

Unconfirmed cleanup during a caller exception or KeyboardInterrupt is now visible
in a structured public exception note while retaining the original exception/type.
The note contains only fixed receipt fields, never child output or exception text.
Explicit close ownership is documented as supported, matching the existing API/tests;
context entry is not falsely described as an enforced precondition.

The first default-suite run was deliberately stopped after review identified
required source changes. Its actual interrupted child result and unchanged-source/
fixture receipt are retained; it is NOT a full-suite PASS and not a newly diagnosed
unit-test failure. First combined726PASS and first repeat report are superseded
for publication by fresh gates on the corrected source. No tests/limits/ignores
or old evidence were changed to turn an incomplete run into success.


## Blocked-output expiry and stream-close review correction

Second independent review: REQUEST_CHANGES,2Important/0Minor/0Critical.
Three reproduction tests exposed one blocked-output lifetime failure and four
stream-close subcase errors (exit1,7.629s). After correction the same3tests pass
(exit0,4.980s). Existing20+9+5test assertions are unchanged.
Whole-life expiry now uses the kernel's defaultSIGALRM action. It cannot enter
another blocking rejection write after expiry. The real pipe test intentionally
stops reading FINISH, confirms partial output exists, and observes termination by
SIGALRM under a shorter test deadline; the normal60s ceiling is unchanged.
Python finally handlers and temporary-directory deletion are not promised on this
hard termination; cleanup confirmation refers to owned processes and parent pipe
handles, not arbitrary filesystem reclamation or real-time scheduling guarantees.

Parent shutdown attempts each stream close independently. A close failure marks
cleanup unconfirmed instead of skipping the other handle or replacing the original
caller exception/KeyboardInterrupt. Both failed-stream positions are exercised.
Normal error-report strings and receipts exclude child output and private details.
The second old-source default run was deliberately interrupted before source edits;
its receipt is retained and is not a full-suite PASS. Publication requires fresh
full-suite,source-review and deterministic evidence on this final correction.


## Interruption during cleanup correction

Third independent review: REQUEST_CHANGES,1Important/0Minor/0Critical.
Three regression tests exposed four original-exception replacement failures during
wait/stream-close/repeated interruption (exit1,1.965s). The same3tests pass after
correction (exit0,1.930s). Each bounded cleanup operation and both stream closes
are independently attempted even when cleanup receives BaseException. The pending
original exception/type is retained; any failed/interrupted operation leaves
cleanup_confirmed=false in the fixed public receipt. No successful confirmation
is inferred merely because a later poll observes the child gone.

All37previous test bodies and old tracked/control files remain unchanged. Whole
process tests validate the stated bounded paths, not immunity to arbitrary endless
signals, hostilecode or uninterruptible kernel scheduling. Source/request hashes
bind selected file bytes, not authenticated live settings or arbitrary previously
loaded parent modules. This remains a trusted offline tool, not a vehicle runtime.


## Final source-bound software verification

This completes the bounded fixed-input persistent lateral session, not full live
or two-axis Shadow. The original20tests and all subsequently added assertions
were preserved;40feature tests are covered by the final affected regression.
Independent reviewsR1/R2/R3 requested changes; all concrete findings were reproduced
and corrected before R4approval. Prior review outputs and interrupted/superseded
runtime results remain evidence, not alternate approvals or final-suite passes.
Final deterministic equality concerns complete data only: random session IDs
intentionally differ and are kept in separate transport receipts.

Default supervisor receipt SHA256: `4c4f583c4b333e01553f48fd791302c3aed58a237b3f755627904c429f849cc8`.
Final repeated data SHA256: `b673b544f6d00b4801c4c097721e4d1835e6bd83f62f2c95968ae2ab88c8d954`.
Final independent source-review receipt SHA256: `12e27bc4b4cf8f0864c450746c2d69ea042648a0c5240d0eb270568d31ac8bca`.

Verified executable content identities:
- `openpilot/tools/cyber_autotune/lateral_session.py`: `03f91c0ab20f334fc55d35388934036ed1d8e0be4771f50d1558146e51336d91`.
- `openpilot/tools/cyber_autotune/lateral_session_protocol.py`: `c1aa201e985c365036a244e17a1a7acfb3fec9559e44560187501aeab12fc1ee`.
- `openpilot/tools/cyber_autotune/lateral_session_worker.py`: `f1386276ae215cbc22cfaeced215caf03d97045acd232a6809d2f58c7b8884ad`.
- `openpilot/tools/cyber_autotune/tests/test_lateral_session.py`: `0d175fb382bd194e54c416a33c8184e12c5c4da7a158b5a8767bdc8524903c77`.
- `openpilot/tools/cyber_autotune/tests/test_lateral_session_boundaries.py`: `b0a71e371d255c87ac42119e8b612b784ee95d85665c5f4bd9a9e4b2a9bea4a2`.
- `openpilot/tools/cyber_autotune/tests/test_lateral_session_interrupt_cleanup.py`: `09ec0e5de6a2d51162f55a7daa8af9d373c1d8c528eb0dd53be238df7fcc6450`.
- `openpilot/tools/cyber_autotune/tests/test_lateral_session_review.py`: `c9ba98936fa04530d11f281ea1ac0758798b765976921a4b9b2661ed4f5fa2a4`.
- `openpilot/tools/cyber_autotune/tests/test_lateral_session_shutdown.py`: `b5e1959d22e085cef671ff235db95017c778f29137956089aef62521366d4f7e`.

The reviewer used only supplied public source and did not execute tests or
recompute hashes; the host bound input to the tested source. This result-only
closeout follows the runtime gates/review; no executable bytes were changed.
Final links/whitespace/privacy and committed blobs must be rechecked at delivery.
One static-gate launcher initially lacked the activated virtualenv PATH and could
not locate Ruff; no tests ran in that attempt. The existing environment was then
activated, with new log names, without installing or changing checks. One separate
Set-Location typo performed no repo operation and was corrected using the known
path. Neither launcher symptom is hidden as a passing test or a product defect.
Qualified replay,calibrated vehicle closed loop,deviceShadow,activeprofile,roadtest
and hostedCI remain NOT_RUN or unverified by this increment. No raw logs/private
configuration were used. NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED remain. Commit/push are verified separately, not inferred.
