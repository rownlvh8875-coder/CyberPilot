# Paired native Shadow windows

## Identity and purpose

Cyber Validation, next bounded STEP10 offline two-axis/scheduler increment.
Baseline `d1c1209d1ccce5ecd897bc8b8449eeb286ac5a37`, branch
`feature/cyber-autotune`. Status: software verified; independent scoped source review approved.
Actual Git delivery is recorded after final publication checks.
Pair lateral and longitudinal requested-command diagnostics for the same declared
window using the existing bounded scheduler, with all-or-nothing comparison output.
This is NOT a continuous two-axis session, device shadow or coupled physical plant.

## Original references and adoption

Repository: https://github.com/rownlvh8875-coder/CyberPilot at the baseline above.
Reuse `shadow.py` ShadowSession/ShadowJob/_prepare/_diagnostic,
`long_shadow.py` axis hooks, native_protocol/native_long_protocol and their runner
validators. Existing repository/native MIT attribution remains; no external code,
dependencies or vehicle model are added. The opendbc pin is
`4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`; all six submodules are unchanged.

Call path: packed two-axis template and immutable active observations -> existing
scheduler admission -> paired hook -> existing isolated lateral then longitudinal
workers -> validated per-axis diagnostic -> atomic paired result. Consumers receive
bytes only; no callbacks, actuator transport, Params or profile writer exists.
Existing single-axis sessions and the completed persistent lateral IPC are unchanged.

Alternatives rejected: replacing the scheduler, adding another worker/IPC protocol,
or describing windowed LongControl as persistent merely because lateral IPC exists.
The new built-in paired hook is the smallest existing-flow change that checks
cross-axis input alignment and integrates queue/expiry/failure accounting.

## Changes and expected effect

Only `paired_shadow.py`, its new test module, and this record are added.
The envelope carries exact per-axis source/CP identity and separate frame arrays.
Both axes within each arm must have equal serialized CP and fingerprint, source
root/HEAD/opendbc revision, and digests for every shared source file. Corresponding
`time_ns`, `speed_mps` and `accel_mps2` must match canonically at every frame.
Frame counts and the existing uniform10ms timestep must agree. No resampling,
trimming,nearest-neighbor time matching,conversion or new delay is introduced.
Native per-axis active/candidate input and active-response validation completes
for BOTH axes before either candidate worker can run.

These checks establish `STRUCTURAL_WINDOW_MATCH_ONLY`. Equal timestamps and hashes
are not authenticated same-clock evidence, independent physical truth or actual
runtime parameter history. Source/CP declarations remain trusted-local inputs, not
approval tokens. The code adds no new data ingestion; this development uses only
existing public synthetic fixture factories. No private/reserved/holdout data read.

The existing one-running/one-pending/one-result scheduler is reused, including
sequence checks, bounded queues, drop accounting,close and terminal-fault behavior.
Both axis workers remain fresh-state-per-window. They execute sequentially, not
simultaneously or in a coupled dynamics loop. One positive requested timeout no
greater than the inherited60s ceiling covers preparation and both diagnostic calls;
the second receives only remaining time. First-axis failure or exhaustion skips it.
This is a scheduling budget,not hard-real-time process-start/cleanup assurance.

Only two fully validated diagnostics produce `COMPLETED_DIAGNOSTIC`. Failure or
expiry drops both sets of comparison values while retaining bounded status/identity
metadata. Torque and acceleration metrics stay separate in native requested-stage
units; they are never subtracted from one another or presented as applied commands.
No zero-error value is invented for a missing axis. Active observations remain
immutable bytes and are never overwritten by candidate outputs.

## Constants, state and boundaries

AXES defines the fixed built-in pair,not user worker selection. Shared frame fields
are timestamp(ns),speed(m/s),acceleration(m/s²); their exact equality is structural.
Existing request/response caps apply to the combined envelope,not twice the limit.
The inherited TIMESTEP_NS and MAX_TIMEOUT_S are not widened. METRICS/FAILURES are
fixed per-axis output contracts,not tunable acceptance thresholds or safety limits.
Source/template identity pins both axis configurations between submitted windows.
No change to PID/native reset,driver takeover,controller bounds,panda/CAN safety,
existing rejected candidate verdicts or frozen acceptance references.

## Regression risks and acceptance

Risks: joining different clocks/configurations/inputs,executing one axis before the
other input is rejected,partial comparison surviving failure/expiry,timeout budget
doubling,wrong units,rebound responses,unbounded queues or altered active output.
Tests cover mismatches before execution,real native identity,nonzero axis-specific
metrics,remaining-time accounting,late results,forged metadata,expiry at poll and
execution,queue saturation and terminal interruption/restart. The baseline is the
existing independently executed native axis outputs; exact equality is required.
No new performance threshold,candidate tune,calibration or physical policy exists.
Rollback is removing/ceasing use of the added offline paired class,not a vehicle
profile operation. Publication requires full software gates and independent review.

## Validation method and actual results

Prepared Ubuntu24.04 WSL virtual environment; no reinstall or forcedTMPDIR.
Use unchanged verified-public-fixture supervisor with exclusive new evidence names.
Default discovery does not include full process replay/simulator qualification.

| Check | Actual result and limit |
| --- | --- |
| Preimplementation TDD |16expected missing-feature assertion failures,exit1,0.009s |
| Initial implementation test run |15passed/1test-harness error,exit1; function replacement had no call_count |
| Corrected new test module |16PASS,4.051s,exit0; all assertion ASTs unchanged |
| Affected regression |48PASS,13.639s,exit0 |
| AutoTune+controls |753PASS,159.36s,exit0 |
| Default verified-public-fixture suite |1660passed/42skipped/1xfailed,319.99s,exit0;source/fixture unchanged |
| Ruff/SCons/privacy/source preservation |PASS;build100%;3public files,0scanner findings;existing source unchanged |
| Deterministic fresh-worker repetition |2fresh parents/8native workers;3184diagnostic bytes equal,timing separately retained |
| Independent source review |APPROVE;no Critical/Important/Minor findings;supplied source only,no reviewer test execution |
| Qualified replay/calibrated plant/device shadow |NOT_RUN |

The call-count instrumentation correction uses a mock side_effect rather than a
plain replacement function. Every assertion is unchanged, and the failing log and
original test bytes remain private evidence. No product defense was weakened.

## Handoff

Verified intent: structural same-window pairing and existing offline scheduling,
not persistent longitudinal control or synchronized continuous two-axis execution.
Unfinished: continuous two-axis state,actual runtime settings provenance,live input
synchronization,device latency/noninterference and physical qualification. Existing
windowed and persistent-lateral components keep their original scope.
No new logs,CAN/vehicle/device writes,profile activation,road test or automation.
`NOT_READY` / `REAL_VEHICLE_UNVERIFIED` / `VEHICLE_ACTIVATION_BLOCKED` persist.
Git commit/push and final result-only documentation occur after gates; no delivery
or hosted CI success is inferred from a local test pass.


## Final source-bound closing evidence

All existing tracked controllers,schedulers,workers,tests and policies match the
baseline bytes; only the declared three public paths were added. Synthetic fixtures
are composed in the new tests,not rewritten in their original factories. Exact
outputs retain per-axis units and independently computed active observations.
One lint check initially reported an unused import and four loop-capture warnings;
these were corrected in the new test only,with identical assertion ASTs and no
ignore expansion. The initial missing-feature RED and test-spy error are preserved.

The independent reviewer inspected exact supplied public source. Host checks bind
that source to these test runs; reviewer test execution or independent physical
qualification is not claimed. Optional coverage ideas (combined size boundaries,
preparation budget exhaustion and extra forged longitudinal diagnostics) were not
required findings and are not counted as tests executed here. No source changes
were made after approval; this closing edit records results only.

Default receipt SHA256: `aeb0d480856755da5b961791f01bce77d078aed60df6d5f5d975fdf3552a190a`.
Repeated diagnostic report SHA256: `86c94a2d184c458db3edd32debf27b86551d2614b79d5455a31b0d201d129505`.
Timing fields queue_duration_s,processing_duration_s,admission_to_finish_s are
retained separately and excluded from deterministic-data equality;no duration or
full wire-payload reproducibility is claimed.

Verified executable content identities:
- `openpilot/tools/cyber_autotune/paired_shadow.py`: `385d8feeb65f8016de58a245ae9e41d85344a76a906dd952e23d1d5c83ca6f24`.
- `openpilot/tools/cyber_autotune/tests/test_paired_shadow.py`: `f2623435c503d387de383c0bb27884a2357c7459c8185647563abb884a83cef1`.

Result-only documentation is checked for whitespace/links/publication scope after
closing; executable source remains the exact tested/reviewed bytes. Post-commit
smoke and actual live-remote equality are separately verified,not assumed here.
Full process replay,vehicle-calibrated simulation,continuous two-axis/device Shadow,
active profiles,road use and hosted CI outcome remain NOT_RUN or unverified.
