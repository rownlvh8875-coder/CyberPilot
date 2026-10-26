# Joint IPC and complete-epoch offline queue

## Identity and purpose

Cyber Validation, bounded STEP10 continuation on `feature/cyber-autotune`.
Baseline `fee93ce277864147a68d7d107734273344574177`. Status: software verified; independent scoped source review approved.
Actual Git delivery and postcommit verification are recorded separately.
Preserve both native controller states across separately delivered IPC chunk jobs,
then reuse the existing bounded scheduler for complete identical epochs. This is
not an arbitrary live stream, calibrated vehicle evaluation or road-use approval.

## References, attribution and call path

Source repository: https://github.com/rownlvh8875-coder/CyberPilot at the baseline
above. Reuse `lateral_session.py` owned pipe/deadline/cleanup/owner-thread handling,
`lateral_session_worker.py` source bootstrap and resource caps, `joint_continuity.py`
finite joint cursor/validation, and `shadow.py` admission/drop/expiry/accounting.
Existing native/repository MIT attribution retained; no external control algorithm
copied, dependency installed or submodule changed. The opendbc pin remains
`4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`; all six submodule pins are unchanged.

Call path: immutable native joint request -> JointSession inherited fixed transport
-> built-in joint worker/protocol -> existing _JointEpoch -> one-shot reference
comparison and checkpoint validation. Queue path: complete ShadowJob -> existing
ShadowSession queue -> owner-thread JointSession -> ordered chunk jobs -> aggregate
comparison. There is no live controlsd, Params, CarController or CAN consumer.

## Changes

- `lateral_session.py` adds private protocol/worker-entry hooks. Default values
  retain its original lateral behavior; pipe I/O, deadlines, process ownership,
  handle rules and hardened cleanup are reused rather than duplicated.
- `lateral_session_worker.py` accepts only an internal fixed joint-mode selection.
  Existing default entry, absolute deadline, kernel expiry, source-only bootstrap,
  byte caps and owned resource limits are unchanged.
- `joint_session_worker.py` loads the fixed sibling worker from source via runpy,
  then selects its fixed joint mode. No caller-selected module, path or command.
- `joint_session_protocol.py` implements OPEN/ADVANCE/FINISH/ABORT/CLOSE for one
  immutable, source-bound joint input and partition. Sequence/epoch/handle/progress
  failures end the session; inputs cannot change inside a retained process.
- `joint_session.py` specializes only progress/final validation while reusing the
  hardened lateral transport. Copied checkpoints are bound to frame times, epoch
  partition and final native state output. Missing or partial completion is rejected.
- `joint_shadow.py` reuses the existing bounded queue. Complete epochs, not
  independently droppable stateful chunks, enter the queue. Its worker thread owns
  one JointSession; unchanged epochs can reuse the child, with fresh controller
  state at each epoch boundary. Faults or lifetime expiry do not restart it.
- Two previously prepared test files are preserved byte-for-byte;22tests now run
  against implementation. No old native/controller/scheduler test is changed.

## Admission, state, timing and failure semantics

Only fully preadmitted native diagnostic envelopes from the owned checkout are
accepted. Corresponding axes retain exact CP/source/timestamp/speed/acceleration
checks from the earlier paired interface. No resampling, raw-log loader or new
classification of unqualified data. This task executes only existing public
synthetic fixture factories, including the existing nonzeroKi case.

Within an epoch, separately received ADVANCE requests retain both native states.
FINISH requires all declared chunks, compares independent one-shot output and
binds every observed checkpoint. ABORT closes incomplete state. A subsequent OPEN
creates both controllers fresh on the same child. Input/config/source/partition
changes require a new session, not hot reload. Session IDs are correlation fields,
not credentials or approval tokens. No automatic retry/resume/state serialization.

The queue is deliberately A/A: exact same immutable request and validated reference
observation. It is not an optimizer or candidate-promotion gate. The inherited
one-running/one-pending/one-result bounds remain; overflow drops whole new jobs or
results, never a chunk already being processed. Expired data loses both axis
comparisons. Input observations are bytes, not callbacks/writable vehicle channels.

Both axes execute sequentially; retained logical state does not establish simultaneous
CPU execution or a coupled physical plant. Existing10ms frame cadence is unchanged.
Each queued epoch has one total budget; IPC calls receive only remaining time.
The existing60s worker lifetime, byte caps and native frame limits are not expanded.
Parent supervision covers startup; the common worker arms the absolute deadline
before repository imports. Hard expiry does not promise Pythonfinally execution
or temporary-directory reclamation. Cleanup confirmation concerns the owned child
and parent pipe handles, not hostile-code isolation or hard real-time scheduling.

Normal close joins the owning queue thread. A cleanup error is reported explicitly,
not inferred successful from a closed queue. Original caller exceptions are retained
with a fixed cleanup note if teardown is unconfirmed. Foreign-thread session calls
cannot consume state or close the owner's process. Active driver override, control
limits, panda/opendbc safety and all qualification restrictions are unchanged.

## Alternatives and regression risk

Rejected: duplicate IPC cleanup, replace the queue, enqueue droppable stateful chunks,
or accept arbitrary live input streams merely because synthetic parity passes.
The small inherited hooks reuse existing flow, while new joint code remains separate.
Risks include changing default lateral behavior, mixing epochs, losing a partial
chunk, publishing late or partial results, stale source state and missed cleanup.
Existing lateral failure/interrupt/buffer/expiry tests and all new joint tests must
pass; comparison of source bytes must show no controller/native arithmetic changes.
Rollback is reverting/ceasing use of these offline additions, not active-profile use.

## Actual verification

Existing Ubuntu24.04 WSL environment and virtualenv are retained, with no forced
TMPDIR or installs. New private evidence uses exclusive names. Default test runner
does not cover complete process replay or simulator/physical qualification.

| Check | Result and scope |
| --- | --- |
| Historical missing-feature RED |22expected assertion failures; prior-session evidence, not rerun as current progress |
| Current inherited joint IPC/queue tests |22PASS,15.937s,exit0; test files unchanged |
| Fresh affected regression |107PASS,53.815s,exit0 |
| Fresh AutoTune+controls |794PASS,171.17s,exit0 |
| SCons |PASS,100%,exit0 |
| Ruff/privacy/source preservation |PASS;9public files,0findings;original22test bytes and other tracked files unchanged |
| Independent public-source review |APPROVE;no Critical/Important/Minor findings;source-only,not reviewer-executed tests |
| Fresh deterministic IPC/queue repetition |2parents/8persistentchildren,16completedepochs/4aborts;127194data bytes equal |
| Fresh verified-public-fixture default suite |1701passed/42skipped/1xfailed,353.87s,exit0;source/fixture unchanged |
| Qualified replay/calibrated plant/device Shadow |NOT_RUN |

The earlier security-indeterminate draft write remained absent until the same
ordinary tool request succeeded in this session. No permission/tool route change
was made. Prior failure/block records remain intact. No old assertion, ignore,
policy, reference or safety limit was weakened to complete this increment.

## Handoff and limitations

Completed software scope: fixed preadmitted joint IPC plus complete identical
epoch queue integration. New epoch boundaries reset both controllers; it is not a
continuous unknown-input stream. Matching hashes/frames are structural evidence,
not authenticated live settings, clock truth, calibration or driving improvement.
All runtime/promotable/vehicle/profile/CAN authorities stay false. No new driving
logs, holdout/reserved/frozen evidence, private simulator/settings or credentials
are read/published. No device writes, road test or automation restart occurs.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED persist.
Commit, postcommit verification and normal exact-SHA push are performed only after
required gates; neither hosted CI nor real-vehicle qualification is inferred.


## Source-bound final evidence

The inherited22test files are byte-identical to the prior prepared tests; no test
or assertion was removed/relaxed. Existing control/native/safety/policy files and
six submodule pins are unchanged. Shared lateral-session edits are only declared
built-in hooks; reversing those hooks in memory exactly restores baseline source.
Fresh existing lateral cleanup/interrupt/deadline tests are included in the affected
suite, rather than assuming compatibility from source comparison alone.

Independent review used exact supplied public source. Host verification bound the
input to these runtime tests; reviewer test execution or independent hash computation
is not claimed. Optional direct joint lifetime-expiry,queue cleanup-failure and
preexecution-expiry coverage were suggestions,not required findings or extra tests
counted as executed. Generic inherited lifecycle tests remain in the regression.
Random session IDs and timing durations intentionally differ and are retained in
separate private receipts; deterministic equality applies to data only,not wire
payloads including transport IDs or wall-clock timing.

Default receipt SHA256: `389f4efd4dbd3737d25b81f037dca621bf62fab799a78553908402326b50ff08`.
Deterministic data SHA256: `9eef180829404683cbeb31cb18c089cb46e26f0ae38285b23000d9149a6b42fa`.

Verified executable content identities:
- `openpilot/tools/cyber_autotune/joint_session.py`: `fbdf0f912fc599db8455ec2ef713ba11da025afd1f61429eebacfbba1d22a0d9`.
- `openpilot/tools/cyber_autotune/joint_session_protocol.py`: `a2e5bd2125234a30dd7a3151b7fd540bf4210d5df39c8506b622bceeb502ef3f`.
- `openpilot/tools/cyber_autotune/joint_session_worker.py`: `b3db17858607dbbeda3c2d7967e7e1c3379979386e65e13ec62dcc3618c2c2bb`.
- `openpilot/tools/cyber_autotune/joint_shadow.py`: `ef765bb46560b3ef27eb083ed285735a42c32925276d3369a85db24cd990c566`.
- `openpilot/tools/cyber_autotune/lateral_session.py`: `dc4ded375360be798b7ec234187681a43f7de6d1de1ce92cd54b04f437098605`.
- `openpilot/tools/cyber_autotune/lateral_session_worker.py`: `67d10afacb8b22d1bf90118f2996a08431105d83fccb8d90fadf766711767225`.
- `openpilot/tools/cyber_autotune/tests/test_joint_session.py`: `ec80274739208d78e797435c9e8ac3380f5beda449abc476a161c03a6c7aefcf`.
- `openpilot/tools/cyber_autotune/tests/test_joint_shadow.py`: `f5c56e04cc6ab6a6392db93b5cc2a17c77255e8ea4d69decd5f2c1fc9075c27e`.

SCons retained its PWD/current-directory mismatch warning but completed with exit0.
This document update records results only; executable bytes still match tested and
reviewed source. Final whitespace/privacy checks,staged/committed blob identities,
postcommit tests and live remote equality are verified separately before delivery.
No process replay/device/physical qualification follows from default test success.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED remain.
