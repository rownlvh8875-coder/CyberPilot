# Longitudinal state continuity and finite joint epochs

## Identity and purpose

Cyber Validation, bounded STEP10 continuation on feature/cyber-autotune.
Baseline `70e2cca0ef9da972814ee4cba1e297fc6336a86e`. Status: software verified; independent source review approved.
Final Git delivery and post-commit checks are recorded separately.
Preserve native longitudinal state across chunk advances and manage one complete
preadmitted two-axis epoch with shared success/abort/failure lifetime. This is not
persistent joint IPC, a live scheduler, two-axis physical dynamics or road approval.

## Original references and call path

Source: https://github.com/rownlvh8875-coder/CyberPilot at the baseline above.
Reuse native_long_worker._execute_request, lateral_continuity._TorqueChunkCursor,
paired_shadow admission, native per-axis response validators, source_only_imports,
native_runner._run_process and worker_resources. Existing native/MIT attribution
is retained; no copied external control algorithm, dependency or submodule change.
Pinned opendbc: `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.

Call path: owned-checkout paired native request + complete integer partition ->
strict pair/source admission -> one fixed isolated child -> independent one-shot
baselines and retained-state joint chunk execution -> exact per-axis parity and
checkpoint validation. All runtime/promotable/vehicle/profile/CAN authorities stay
false. No native CarController, CAN sender, device writer or Params consumer added.

## Changes and intended effect

- native_long_worker.py extracts its existing update loop into a private lazy
  generator; original callers still drain it immediately. Default v1 response
  keys and all native update/reset/limits expressions remain unchanged. Optional
  private capture records mode,last_output_accel and mutable PID fields only.
- joint_continuity.py reuses the existing cursor lifecycle for LongControl and
  coordinates a pair in one finite,immutable epoch. Each advance performs the
  declared next number of frames on each controller,never replaying prefixes or
  resetting at chunk boundaries. Native off/stop/override resets remain unchanged.
- joint_continuity_worker.py follows the existing source-only isolated bootstrap
  and resource caps. The existing parent supervisor owns timeout/process cleanup.
- New tests cover real update counts,stop-history/nonzero-integrator counterexamples,
  same-output/state partition parity,input/checkpoint ownership,source/time/partition
  rejection,wrong-thread refusal,partial failure,interrupt/cleanup and malformed
  result schemas. Existing test files remain unchanged.

The joint input is fully declared before execution and copied. Source/config
changes cannot be admitted between chunks. Both axes use one matched CP/source and
exact frame clocks/speed/acceleration through the existing paired validator. No
resampling or hidden delay. Success exists only after complete processing of both
axes;aborted/invalid/failed epochs close both cursors and cannot resume. A new epoch
creates two fresh controllers. Reverse-order finalization/close releases their
shared import-stack entries. Same-thread ownership is checked without disturbing
an epoch from a rejected foreign-thread call. Cleanup is best effort;failed cleanup
is marked unconfirmed rather than replacing a pending original exception.

## State, units and limits

PID_STATE_FIELDS names the inspected mutable PID storage p/i/d/f/control/speed/
pos_limit/neg_limit. Values use native units (requested acceleration,m/s² for the
longitudinal controller; speed,m/s). Immutable gains/CP/source are bound by the
existing content identities; there is no new tuning knob. The private state schema
is native-long-state-v1. Timestamp is ns;existing uniform10ms requirements and
request/response/frame-count limits are unchanged. Chunk counts are integer frame
counts summing exactly the paired epoch size,not physical tolerances.

Longitudinal state snapshots bind mode,requested output and all listed PID fields
with exact hashes. Lateral capture reuses the existing state/history/schedule
receipt. Independent one-shot and chunked traces/states must match byte-for-byte.
No observed output/state digest by itself authenticates the model,producer,clock,
actual runtime settings or correct physical behavior. Input alignment remains
STRUCTURAL_WINDOW_MATCH_ONLY; unknown input provenance is not promoted to qualified.

Inputs retain the previously supported trusted-local native diagnostic boundary,
restricted to this checkout;there is no new log loader. This work executes only
existing public synthetic fixture factories and the already-tested synthetic
nonzeroKi case. Those gains are not a candidate or recommended vehicle settings.
Stopping-output history provides a nonzero memory test even with stock zeroKi.
No holdout/reserved/frozen evidence,private log/settings/simulator or new drive input.

## Risks, alternatives and verification contract

Principal regression risk is changing the original native long loop. Preserve
pre-change complete outputs for two existing synthetic variants and compare after
refactor;also compare the loop AST after removing only optional capture/yield and
wrapper bookkeeping. All other existing tools/controllers/policies/tests must stay
byte-identical. Native per-axis schemas continue validating v1 data. New extended
schemas must reject malformed arm types before field access,not escape with a
Python AttributeError or expose partial result data.

Alternatives rejected: duplicate LongControl,change its math,reset/replay each chunk,
or replace existing paired scheduling/lateral IPC. The new logical epoch runs the
axes sequentially within each chunk;it does not interleave physical vehicle states,
prove simultaneity or couple feedback plants. Private cursors are child-only,not
concurrent parent-interpreter APIs. Public execution uses one bounded supervisor;
source checks and cleanup are not a hard-real-time scheduling guarantee or a
hostile-code sandbox. Directly invoking worker scripts is not the supported API.

Rollback is ceasing use of/reverting these offline modules,not profile activation.
Required gates:affected,AutoTune+controls,Ruff,SCons,verified-public-fixture default
suite,deterministic fresh process results,privacy/source preservation and independent
review. No threshold,test,ignore,reference or safety boundary may be weakened.

## Actual validation record

Existing Ubuntu24.04 virtual environment;no reinstall or forcedTMPDIR. All new
private receipts use exclusive D-local names. Default runner excludes complete
process replay/simulator qualification;that distinction is unchanged.

| Check | Actual result and limit |
| --- | --- |
| Preimplementation RED |17missing-feature assertion failures,exit1,0.017s |
| First implementation |17PASS,3.858s,exit0 |
| Malformed-arm boundary RED |2tests,22unexpected AttributeError subcases,exit1,0.325s |
| Corrected malformed-arm boundary |2PASS,0.299s,exit0;test assertions unchanged |
| Prior-output/AST preservation |PASS, freshly rerun: two pre-change native outputs identical; native long core unchanged |
| Fresh affected regression, including all19new tests |82PASS,41.454s,exit0 |
| Fresh AutoTune+controls |772PASS,159.30s,exit0 |
| Fresh default verified-public-fixture suite |1679passed/42skipped/1xfailed,336.35s,exit0;source/fixture unchanged |
| Ruff/SCons/privacy |PASS;SCons100%,exit0;6public files,0scanner findings |
| Fresh deterministic repetition |2parents/8isolated workers,2synthetic variants;121482report bytes exactly equal |
| Independent source review |APPROVE;0Critical/0Important/0Minor findings; supplied public source only |
| Qualified replay/calibrated plant/device Shadow |NOT_RUN |

The boundary failure was a reproduced implementation defect,not a relaxed test.
Exact arm dictionaries are now checked before iteration;raw malformed content is
not reflected. Both failed and passing evidence remain recorded. A unit-test
pass is not a useful tuning candidate or real-vehicle release approval.

## Remaining work and handoff

This increment supplies long state continuity and a finite joint lifecycle only.
Existing persistent lateral IPC and windowed paired scheduler are not rewritten or
silently enabled for joint streams. Cross-job joint IPC/scheduling,live input clocks,
runtime parameter history,qualified replay,vehicle-calibrated closed loop and device
non-actuating Shadow remain separate unverified work. No driving improvement claim.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED remain in force.
Result-only documentation,commit/postcommit smoke and actual feature-only normal
push are recorded after gates;no hostedCI or delivery success is assumed here.


## Resume and closing evidence

The earlier17-test implementation run and2-test boundary run are historical rows,
not one earlier combined19-test result. The fresh affected suite above now includes
both modules on the final source. Only one unused import in the new test was removed
at resume; all assertions remained identical. The prior F401 and security-indeterminate
blocked attempts are retained as history. The same ordinary authorized terminal
operation succeeded at resume without permission,route or environment installation
changes. New evidence filenames did not replace earlier results.

The reviewer inspected supplied code only: no reviewer-executed tests or independent
hash recomputation is claimed. Host verification tied that input to the tested bytes.
Optional coverage ideas (actual cursor cleanup failure,nested malformed state shapes,
foreign-thread advance/finish) were not defects or tests executed in this increment.
The independent baseline-output preservation gate was freshly executed using saved
pre-refactor observations,not merely two paths through the refactored worker.

SCons retained a PWD/current-directory mismatch warning but completed with actual
exit0. Full-suite discovery still excludes complete process replay/simulator
qualification. No source,fixture,old test,ignore,policy or safety threshold was
changed to secure a passing result. Existing six submodule pins are unchanged.

Full-suite receipt SHA256: `ababffa53f928887b1d934a81bcdaaa21e9f89a2b4603bb05a43cb3a0917412f`.
Deterministic complete-report SHA256: `40457c2a615588b5c2c32cdd162da30fe5494437670fedd5bd846e79ba313f98`.
Pre-change native observations SHA256:
`3b94fe6ff77f3f99f1c53815ef6731e09427907511f2158589f7e8c0dce2c765`.

Verified executable identities:
- `openpilot/tools/cyber_autotune/joint_continuity.py`: `0f91dbc49914243bc40c9520edee877df9b4a71292244ae7855325d1b8ca73fd`.
- `openpilot/tools/cyber_autotune/joint_continuity_worker.py`: `0f1e73c96217784a69d781178f2887bc8cdc6bf96949305adbf09fa8fbe0b238`.
- `openpilot/tools/cyber_autotune/native_long_worker.py`: `e9ad77620fd75f831ade9f1f75a1c7842ae6a0222ac35a1792687a361191bd53`.
- `openpilot/tools/cyber_autotune/tests/test_joint_boundaries.py`: `d520e4b42780dca1a956fcc42e14384d59f3792c6e1252bf641872172fb18a96`.
- `openpilot/tools/cyber_autotune/tests/test_joint_continuity.py`: `4b5eff7847d29685d5464b376d53a4c00f88a5311ba9749666e41b148526a8cf`.

This result-only document edit follows runtime verification/review; executable
source remains identical. Whitespace,links,publication scope,staged/committed blobs
and post-commit smoke are checked separately before ordinary feature-only delivery.
No vehicle readiness,performance improvement or full STEP1-10 completion follows.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED persist.
