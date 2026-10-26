# Predetermined segmented joint continuity

## Identity and purpose

Cyber Validation / offline STEP10 continuation. Baseline
`a762708403f0f72e92c562e3e658a05e686e10d6`, branch `feature/cyber-autotune`.
Status: bounded offline software verification complete. Exact Git delivery and
postcommit results are separately observed; this is not vehicle qualification.
Connect contiguous predeclared input segments to one existing native joint epoch.
The artificial segment boundaries do not reset either native controller. This is
not qualified replay, a live stream, a calibrated vehicle model or road approval.

## References and adopted call path

Repository: https://github.com/rownlvh8875-coder/CyberPilot at the baseline above.
Reuse `joint_epoch_sequence` admission, aggregate limits, absolute-budget session
specialization and cleanup receipts; `joint_session_protocol` epoch schemas;
`joint_continuity` exact trace/state validation; and the existing joint IPC worker.
Existing repository/native MIT attribution is retained. No third-party algorithm,
dependency, worker, schema, native control change or submodule update is introduced.
The opendbc pin remains `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.

Call path: segment byte envelopes -> existing ordered-sequence admission -> all
source checks -> immutable merged epoch -> ONE existing JointSession OPEN -> each
original chunk ADVANCE -> FINISH and exact one-shot baseline comparison -> normal
confirmed CLOSE -> sanitized segment-boundary hashes and whole-trace/state hashes.
Only one new helper, its tests and this record are added. Old modules remain intact.

## Design and behavior

Every input segment is known before execution. Across segments, source/CP/header
identity must match and timestamps must be exactly contiguous. The existing builder
checks aggregate raw bytes BEFORE JSON allocation; existing total-frame and combined
request-byte limits still apply. The additional plan wrapper and compiled epoch are
also capped. There is no gap repair, interpolation, mutable append or input sorting.

Compilation concatenates both axes' frames and original chunk partitions while
retaining all original content bindings. It never refreshes stale source identities
to make an old segment admissible. A segment offset is only a reporting boundary:
all segments form ONE preadmitted native epoch and one controller pair. Thus the
existing refusal to change a running session's input is neither removed nor bypassed.
No caller inserts unknown frames into a live session. Native off/driver-override/
reset behavior still operates; only extra resets induced by segmentation are absent.

The prior reset-sequence API remains unchanged and separately reports fresh resets.
The new API reports state carried between artificial segments only after complete
native trace/state parity and confirmed normal close. Tests include a nonzero PID
integrator counterexample, showing continuous output differs from resetting at the
second segment. Repartitioning identical combined frames must preserve whole-axis
output and state hashes even though boundary/checkpoint metadata changes.

One absolute timeout budget covers plan validation, compilation, all IPC calls and
final reporting. The inherited session refreshes its budget at spawn and exchange
after source checks. Normal close must report observed integer exit0 and confirmed
cleanup. Any failure, invalid result, source drift, timeout or unconfirmed close
removes all comparison rows. Original interruptions propagate; inherited cleanup
semantics preserve interruption precedence and fixed unconfirmed notes. No automatic
restart, state serialization, background processing or queue change is introduced.

The worker's inherited lifetime/byte/resource limits stay unchanged. Cleanup and OS
scheduling are bounded by existing contracts, not a hard-real-time or hostile-code
sandbox guarantee. Failure receipts contain fixed status, digest, observed exit and
cleanup state, never raw frames, CP bytes, controller snapshots, paths or child logs.

## Constants, scope and trade-offs

PASS/SCOPE/BOUNDARY are descriptive non-authorizing labels, not activation flags.
The single new overlay path binds this helper; the nested sequence and epoch bind
all reused code. Existing native frame cadence and size/time limits retain their
units/ranges. All executed inputs are synthetic compositions of the existing public
factories, including the previously tested nonzeroKi case. No vehicle tuning value
is introduced or recommended. No private/unclassified/reserved/holdout evidence is
read or promoted to a qualification role.

Rejected alternatives: relaxing same-session input immutability, inventing another
worker/transport or copying control loops. Reusing the existing native epoch gives
a bounded proof of segmentation invariance without changing global controllers.
The full plan must fit existing limits; unbounded or unknown live input is excluded.
Rollback is ceasing use of the added helper, not any vehicle/profile operation.

## Regression and verification

Risks: hidden boundary reset, source/config/time mixing, partial results after a
late failure, stale timeout budget, misidentified boundary hashes or leaked inputs.
Tests exercise real one-child IPC, independent whole-input native reference output,
nonzero memory, repartitioning, malformed future segments, resource admission,
mid-run drift, failure in a later segment, forged results, unconfirmed close,
cancellation, timeout and unchanged reset/same-session guard behavior.

| Check | Actual result and limitation |
| --- | --- |
| Test-first missing-feature RED |15 failures, 0.011 s, exit1; preserved |
| Initial feature GREEN |15 passed, 18.434 s, exit0 |
| Existing source-bound related regression |79passed,55.676s,exit0;historical execution verified,not rerun at delivery |
| Existing source-bound AutoTune+controls |832passed,188.85s,exit0;historical execution verified |
| Existing source-bound SCons |PASS,100%,exit0;PWD mismatch warning retained |
| Delivery Ruff/publication/old-source preservation |Fresh checks required by this closeout;see source-bound closing receipt |
| Independent source review |Previously APPROVE,0Critical/0Important/0Minor;exact reviewed executable source reconfirmed |
| Fresh independent process repetition |2parents,8native sessions;7401comparison-report bytes identical |
| Existing completed verified-public-fixture default suite |1739passed/42skipped/1xfailed,453.54s,exit0;source/fixture unchanged |
| Qualified replay / calibrated plant / device Shadow |NOT_RUN |

The existing Ubuntu24.04 virtualenv and linked worktree are retained; no installs
or forced TMPDIR. The unchanged verified-public-fixture runner is used with a new
exclusive evidence prefix. Default discovery is not full process replay/simulator
qualification. All failures are preserved; no assertion, ignore or reference changes.

## Handoff boundaries

This is bounded, predetermined state continuity across declared segment boundaries.
It does not solve actual runtime settings provenance, dynamic input admission, vehicle
calibration, perception or physical validation. Equal content/timestamps are only
structural evidence; all runtime/promotable/vehicle/profile/CAN authorities remain
false. No new logs, private simulator, frozen-policy changes, device writes, active
profile, road test, main/develop merge, force push or automation restart.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED persist.
Publication and hosted CI results are separate from local software test results.


## Delivery closeout and evidence boundaries

The full test result was recovered after remote reconnection;it had already finished
successfully. It was not restarted or relabeled as a new delivery-session test.
The current source hashes,Python version,submodule pins,and original review bindings
match that completed run. Related79,combined832,default1739 and SCons are existing
source-bound results. The separate repetition below is new execution at delivery.
Both original Python files and their assertions remain byte-identical throughout.

Repetition uses two independent parent Python processes,eight observed native child
sessions,and two/three-segment synthetic plans plus equivalent unsplit plans.
Reports are byte-identical;each whole result matches an independently constructed
native reference;repartitioning preserves both axes' trace/state hashes. Separately
resetting the last segment produces a different longitudinal state,so reset behavior
is not confused with continuous state. Children were observed closed with exit0 and
no owned process group remaining. No duration or random transport-ID determinism is
claimed. Inputs remain existing public synthetic factories,not user driving logs.

The prior repetition-supervisor write denial is retained as history. The same normal
write request succeeded at delivery;no tool permissions or safety settings changed.
During delivery,Windows executable dispatch in the remote WSL shell failed because
the runtime binfmt interop entry was absent. Current WSL interpreter dispatch and
the already existing session socket were used explicitly;no registry,binfmt,sudoers,
WSL install,remote configuration or vehicle setting was changed. This is an execution
transport observation,not a finding that prior tests failed or the PC overheated.

The reviewer inspected supplied source only,did not run tests or independently
recompute hashes. Its previous approval applies to unchanged executable bytes;no
new independent-review run is claimed. Optional post-close deadline/secondary
interruption tests remain suggestions,not implemented tests or completed gates.
This document records results only;fresh static/privacy checks and postcommit smoke
are required before ordinary feature-only delivery. No hostedCI outcome is asserted.

Completed full-suite receipt SHA256: `a036c21abdbcce669451980bc60df15da696a84081dd6342e72acc264337a7fe`.
Fresh deterministic report SHA256: `8253caff1bcad7e920ab60d08f63d88023de84643bfe007093f4b891170b0491`.

Verified executable identities:
- `openpilot/tools/cyber_autotune/joint_segmented_continuity.py`: `ff84e6b2d26dffaf25face283735a9340f4376b901d4255bfb4d5ab6d7b8fc1c`.
- `openpilot/tools/cyber_autotune/tests/test_joint_segmented_continuity.py`: `b6e26d068701fbf291dca94bd4bcb3ec7693e9a13c0b6be135b44af8a4342492`.

NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED persist.
