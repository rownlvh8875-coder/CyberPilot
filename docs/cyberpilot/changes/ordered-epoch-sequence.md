# Ordered changing-input epochs with explicit resets

## Identity and purpose

Cyber Validation, bounded offline continuation on `feature/cyber-autotune`.
Baseline `f5245a93def65e181b9981b7a3bc405808bd4f77`. Status: software verified; independent final source review approved.
Actual commit/postcommit/push are separately checked after publication gates.
Process a finite,fully predeclared sequence of different native joint inputs in
order. Every boundary requires completed prior execution,confirmed session shutdown
and a fresh process/controller pair. This is NOT state-continuous driving replay,
unknown live input,device Shadow or qualification of real runtime configuration.

## Original references and adoption

Repository: https://github.com/rownlvh8875-coder/CyberPilot at the baseline above.
Reuse joint_session.JointSession, joint_session_protocol epoch validation/source
checks, joint_continuity native result validation, and native_protocol size/frame/
time constants. No existing source file is modified. Existing native/MIT attribution
and all six submodule pins remain; opendbc is
`4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`. No dependency,worker,protocol,scheduler,
controller,model or optimizer is added. No caller reaches vehicle actuation code.

Call path: ordered epoch byte envelopes -> whole-sequence structural admission ->
all-source verification -> existing JointSession per epoch -> exact native parity
result -> confirmed close -> next new session -> sanitized whole-sequence report.
Only the helper,three test modules and this feature record are new public files.

## Changes, alternatives and boundaries

`joint_epoch_sequence.py` supplies build/encode/decode/run functions. Input bytes
are copied into a sealed local snapshot before any worker starts. Every epoch is
validated before the first session. All source/configuration headers and source
hashes must match across the sequence; only frame values/counts and their valid
partitions can differ. First time of each successor must equal previous final
sample time plus inherited TIMESTEP_NS. Gap,overlap,clock reset,reverse order,
duplicate interval and configuration change are rejected,not repaired or resampled.
This describes structural order only,not physical clocks or settings provenance.

The existing same-session rejection of changed input is deliberately unchanged.
Different epochs are routed through newly constructed sessions,not hot-reloaded
into already imported worker state. Both controllers reset at EVERY epoch boundary,
even when the timestamps are contiguous. Tests show a carried PID integrator is
not equivalent to a fresh start; reports explicitly state state is not carried.
Within each epoch the existing IPC retains controller state across its chunks.

Alternative rejected:weakening JointSession's fixed-input guard to accept arbitrary
new inputs; silently calling reset/continuity equivalent; or introducing another
IPC worker or dropping queue. Explicit close/new-session composition changes no
existing interface and cannot accidentally activate an existing vehicle consumer.
It incurs process startup at boundaries; no speedup or real-time operation claimed.

One total positive timeout no greater than native MAX_TIMEOUT_S covers the sequence,
including validation and completed-epoch transitions. IPC exchanges get only the
remaining budget. Existing bounded cleanup may outlast the data-completion budget;
that is not permission to start another epoch. Before advancing to the next epoch,
normal CLOSED status,actual integer exit0 and cleanup_confirmed=true are required.
If any epoch fails,cleanup is unconfirmed,source changes or the budget expires,
no further epoch starts and no prior success rows are returned. Only completed count,
failed index,fixed status,observed exit code and cleanup status remain. Interruptions
retain their original exception/type; unconfirmed cleanup gets a fixed note.

MAX_TOTAL_FRAMES reuses native.MAX_FRAMES for the ENTIRE sequence,not for each new
independent worker. The combined request uses the existing MAX_REQUEST_BYTES cap.
No new physical tolerance,delay,gain or safety setting. BOUNDARY is a descriptive
fixed FRESH_PROCESS_RESET label; it is not a configurable activation switch.
SYNTHETIC_TARGET_INCREMENT_MPS2=.05 in tests changes a requested synthetic target,
not a vehicle gain,recommendation or actual applied acceleration. Test fixtures
are new local compositions of existing public factories; originals are unchanged.

## Regression risk and acceptance

Primary risks:executing before future input validation;clock/configuration mixing;
reusing previous controller state;starting the next child before confirmed teardown;
accepting partial success;forgetting timeout accounting;leaking native inputs in
reports. Required tests cover all these cases with real native children,changed
input outputs,nonzero integrator counterexample,exact fresh native references,
failure in the second of three epochs,and cancellation/cleanup/source boundaries.

Reports carry only hashes/index/boundary/status,not raw frames,CP bytes,paths,
controller snapshots or child output. Content hashes do not authenticate data role,
producer,independent truth or actual runtime settings. All runtime/promotable/
vehicle/profile/CAN authorities stay false. Execution in this work uses synthetic
inputs only; no new log loader,holdout/reserved/frozen evidence,private settings or
simulator is accessed. Existing safety/driveroverride/policies/acceptance stay intact.

Rollback is ceasing use of/reverting the new helper,not applying a vehicle profile.
Publication requires the user's already specified regression,build,privacy and
independent-review gates. No changes to old tests,ignores or references are allowed.

## Validation method and actual results

Use existing Ubuntu24.04 WSL virtualenv without installs or forcedTMPDIR. Preserve
all failed and successful outputs with unique D-local evidence names. The existing
verified-public-fixture default runner remains unchanged and still excludes full
process replay/simulator qualification.

| Check | Actual result and limitation |
| --- | --- |
| Missing-feature test-first RED |16expected assertion failures,0.012s,exit1 |
| First new test run |16PASS,14.923s,exit0 |
| Final affected regression,including all23new tests |90PASS,63.710s,exit0 |
| Final AutoTune+controls |817PASS,178.87s,exit0 |
| Final SCons |PASS,100%,exit0;PWD/current-directory warning retained |
| Final Ruff/privacy/source preservation |PASS;5public files,0findings;all old tracked sources/tests unchanged |
| Final independent source review R3 |APPROVE;0Critical/0Important/0Minor defects;supplied code only |
| Final deterministic fresh-process repeat |2parents/10native child sessions;2992report bytes exactly equal |
| Final verified-public-fixture default suite |1724passed/42skipped/1xfailed,355.15s,exit0;source/fixture unchanged |
| Qualified replay/calibrated plant/device Shadow |NOT_RUN |

## Handoff

This step processes changing but predeclared inputs with explicit fresh resets.
It does not complete cross-epoch state-continuous replay or an unknown live stream.
Same-session changing input remains rejected. Source/parameter history,qualified
replay,calibrated vehicle feedback and non-actuating device Shadow are still
unverified. No performance/centering/comfort improvement or fullSTEP1-10 claim.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED remain in force.
Result-only document closeout,commit/postcommit and ordinary feature push follow
successful gates;hostedCI or actual delivery are not inferred from unit tests.


## Independent review correction

First source review:REQUEST_CHANGES,3Important findings,no Critical findings.
Five added tests reproduced four failures before correction (exit1,1.419s);all five
pass after correction (exit0,0.795s). Original16test bytes and new5test assertions
are unchanged. The earlier810-test regression and first repetition concern the
pre-correction source and are superseded by fresh final gates,not reused as passes.

The builder now sums raw input-byte lengths and rejects excess BEFORE any JSON
object allocation; whitespace cannot hide aggregate input size. A private local
JointSession subclass refreshes the absolute sequence budget at _spawn and _exchange
entry after inherited source validation. Old shared transport files stay unchanged.
Data execution cannot use a stale pre-validation budget to launch or send a job;
existing process-start/cleanup OS scheduling is still not a hard-real-time guarantee.

Ordinary cleanup exceptions produce unconfirmed cleanup metadata. A NEW interruption
while cleaning up an ordinary failure propagates with a fixed cleanup note instead
of disappearing into a status dictionary. If an original interruption is already
pending, a second cleanup interruption does not replace it;the original receives
the unconfirmed note. No private exception text is added to public result metadata.


## Internal cleanup interruption correction

Second source review:REQUEST_CHANGES,1Important finding. The inherited shared
cleanup intentionally reduces each caught BaseException to unconfirmed status.
For this sequence's cancellation contract,that could hide a new interruption
before it reached the outer handler. Two new tests reproduced four subcase
failures in wait,group confirmation,and both pipe closes (exit1,1.892s);the same
tests now pass (exit0,1.870s),including preserving a pending original interruption.

The sequence-local session specialization retains the first cleanup interruption
while attempting the same owned kill/wait/group-confirm/poll/close operations in
the same order with the same native bounds. New cancellation propagates after
those attempts;an already pending original interruption retains precedence.
Shared transport files remain byte-identical. This small local cleanup loop is
necessary because the base boolean receipt does not expose exception identity.
No infinite-signal,hostile-object or hard-real-time immunity is claimed.
All original21test bytes and new cleanup assertions remain unchanged. Earlier
815-test and second-repeat passes concern the pre-correction source and do not
satisfy final publication. Fresh final gates and independent review are required.


## Final source-bound verification

All23new test methods are included in the final affected regression. Both earlier
source-review REQUEST_CHANGES verdicts and their reproduced failures remain in
private evidence;only R3 approves the final code. Earlier810/815combined counts
and pre-correction repeat hashes are not final publication gates. No old test,
assertion,ignore,reference,submodule,controller or safety policy was changed.

The final reviewer used embedded public source only and did not execute tests or
independently recompute hashes. The host bound reviewed source to actual test runs.
Optional kill/poll interruption and further successful-close error combinations
remain suggestions,not extra tests claimed as executed. The final deterministic
runs exercise the actual sequence-local subclass and compare each completed epoch
against independent native output. Random process/session identities and elapsed
time are not included;report byte equality is not real-time determinism.

This result-only closeout follows source-bound runtime verification and review.
Executable code remains identical;links,whitespace,privacy,staged/committed hashes,
postcommit tests and actual live-remote equality must pass separately at delivery.

Default-suite receipt SHA256: `1077183a92875e8120dd4de5928c335cc8bf251c120dfab27a1cf44e2c3e1ada`.
Final deterministic report SHA256: `78a80d55c71036edb2cf887ce19924ed095df03044c800012cea0fc3a4e47ebd`.

Verified executable identities:
- `openpilot/tools/cyber_autotune/joint_epoch_sequence.py`: `ce6add6713dc928fd8ab9863f8a402d8e8e5c13249e202a445856e80dfd154b2`.
- `openpilot/tools/cyber_autotune/tests/test_epoch_sequence_boundaries.py`: `884affbd3caebf53919efed13e70c6fe6d427b1e952f0e08c2734e98a5069473`.
- `openpilot/tools/cyber_autotune/tests/test_epoch_sequence_cleanup.py`: `faf519e6045bdbd47e1976d76cb9530d93133f9c7a234d4d05089b237279f384`.
- `openpilot/tools/cyber_autotune/tests/test_joint_epoch_sequence.py`: `13826539c803d23b5a9443bbb296ae685267aa104cfd48b21f4dc433e32c998e`.

The supported result is ordered predeclared changing-input epochs with explicit
fresh-process resets,not state-continuous driving. Cross-epoch state continuity,
actual parameter history,qualified replay,vehicle-calibrated closed loop and device
Shadow are unverified. No new driving data,device/profile operation,roadtest or
automation restart. NOT_READY / REAL_VEHICLE_UNVERIFIED /
VEHICLE_ACTIVATION_BLOCKED remain. HostedCI outcome is not inferred from local gates.


## Preserved initial full-suite HTTP error

The first unchanged default execution completed with1723passed/42skipped/1xfailed/
1error,323.22s,actualexit1. The error was TestAgnosUpdater.test_manifest at its
requests.head URL check:RemoteDisconnected while receiving HTTP response. No
flashing/device update occurred. That test source and manifest were not changed.
The identical isolated test then passed13.205s,exit0 without mocks,retries inside
the test,timeout changes or ignore changes. A fresh complete default suite was
required afterward;its final result above is independent evidence,not removal or
relabeling of the first failure. Both runs preserve unchanged source/verified input.
The specific external cause of the first connection closure is not established.
