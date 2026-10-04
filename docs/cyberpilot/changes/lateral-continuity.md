# Preadmitted lateral native-state continuity

## Identity and purpose

Cyber Validation / first bounded STEP10 continuity increment. Baseline
10caa028251ba35c7bde4085e3525de0f984f43f on feature/cyber-autotune.
Implemented and software-verified; independent scoped source review approved.
Actual Git delivery is checked separately after final publication checks.
Preserve native torque-controller state across successive chunk advances within
ONE isolated process and ONE fully preadmitted synthetic epoch. This is not the
continuous cross-job/device Shadow scheduler, nor a performance-improved tune.
No new user log, runtime configuration, private simulator or physical vehicle input.

## Original references

Reuse https://github.com/rownlvh8875-coder/CyberPilot at the baseline above:
native_worker._execute_request and its existing state capture, native_runner's
owned process lifecycle, a1_experiment's fixed disabled fixture and strict
trace/state comparison, source_only_imports and worker_resources. Existing
repository/native MIT attribution is retained; no external implementation copied.
Pinned opendbc4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76 unchanged; all six
submodule pins, model assets and dependencies remain inherited.

Call path: fixed synthetic envelope + complete partition -> owned source binding
-> isolated bounded child -> native one-shot baseline and lazy chunk cursor ->
exact trace/state/checkpoint validation -> non-authoritative diagnostic report.
There is no caller in controlsd, ShadowSession, LongShadowSession or vehicle I/O.

## Changes and expected effect

- native_worker.py factors the existing loop into a private per-frame generator.
  Original callers still drain it to completion and receive the original result.
  Each yield occurs after the native update and all existing state checks; no
  controller arithmetic, update order, limit or native reset semantics changes.
- lateral_continuity.py adds a private cursor and fixed synthetic experiment.
  advance(N) executes exactly N more frames on the same controller; finish()
  requires complete consumption and performs final source checks. Complete input
  is copied before execution. Invalid advance, failure, incomplete finish or close
  terminates that cursor; there is no resume token or external state restoration.
- lateral_continuity_worker.py reuses source-only bootstrap and existing resource
  limits; native_runner._run_process provides timeout/owned-process cleanup.
- tests/test_lateral_continuity.py covers state/output parity, real update counts,
  a non-vacuous reset counterexample, cleanup, input ownership, malformed partitions,
  checkpoint/source/response binding and real subprocess repetition/failures.

Constants reuse existing601-frame disabled A1 fixture,10ms time step, request/
response size caps and supervisor maximum. Chunk sizes are positive integer frame
counts summing exactly601, not physical tolerances or speed-tune settings. The
existing synthetic factor/friction are reused as software inputs, never proposed
as vehicle parameters. The synthetic CP fingerprint is not user-vehicle evidence.

The fixture is preadmitted; no new input, source, CP or setting can be submitted
between advances. All controller/PID/history state remains process-local. The
original deactivate/override/reset behavior still executes at its original frames;
only chunk boundaries do not introduce extra resets. No physical delay is added.
One-shot and chunked traces, native state hashes and per-chunk checkpoint positions
must match exactly; thresholds and existing A1 validation are not weakened.

Alternatives rejected: duplicate the native controller, replace the existing
scheduler, concatenate/recompute prefixes while falsely claiming preserved state,
or immediately add persistent bidirectional IPC. A private lazy iterator gives a
small first step that is independently testable before those larger lifecycle tasks.
Maintenance risk is limited to the offline native loop extraction and two new tools.

## Regression risk and acceptance

Primary risks: changed one-shot behavior, hidden reset/precomputation, abandoned
source-import context, treating an incomplete epoch as complete, changed settings
or source identity mixed into state, malformed results or leaked child output.
Tests must demonstrate real update counts and a reset-at-boundary case that does
NOT match continuation; equality on only a zero/inactive trajectory is insufficient.
Pre-change native output/state for all five existing synthetic A1 variants is
preserved privately as an independent regression oracle. The complete old loop
body is AST-compared after removing only the new yield/docstring; other native
functions, old tests, controllers, policies and scheduler files remain unchanged.

All result authorities remain false. Source/request/state digests bind selected
bytes and claims, not authenticated runtime history or real-vehicle qualification.
A checkpoint is not a reusable approval token. This is trusted local code, not a
hostile-source sandbox, hard-real-time interface or concurrent parent-interpreter
API. Intermediate private cursor checkpoints alone are not a completed experiment.
Rollback is ceasing use of/reverting these tools, not activating a vehicle profile.
Commit/push requires regression/build/privacy/deterministic gates and independent
review; no merge, deployment, road test or automation restart is authorized.

## Validation method and actual results

Existing Ubuntu24.04 virtual environment, no forced TMPDIR, no test/ignore/reference
changes. Existing verified-public-fixture default supervisor uses a new exclusive
evidence namespace. That default suite excludes full process replay/simulation.

| Check | Actual result and limit |
| --- | --- |
| Preimplementation TDD |18 expected assertion failures for absent feature,exit1; preserved |
| New continuity unittest module |18PASS,6.908s,exit0 |
| Original native/A1/Shadow affected regression |69PASS,26.500s,exit0 |
| AutoTune+controls supported runner,-j2 |697PASS,135.59s,exit0 |
| Default verified-public-fixture runner |1604passed/42skipped/1xfailed,339.62s,exit0; source/fixture unchanged |
| Ruff / SCons / source preservation / privacy |PASS; native build100%, five public changed files, zero scanner findings |
| Fresh-process whole-report repetition |3partitions,2fresh parent processes,6isolated workers;1306605bytes exactly equal |
| Independent source review |APPROVE; no Critical/Important/Minor findings; no reviewer-executed tests |
| Qualified replay / calibrated vehicle closed loop / device Shadow |NOT_RUN |

## Handoff

This completes the stated first finite-epoch software continuity increment,
not the complete continuous Shadow subsystem. The existing ShadowSession and LongShadowSession
still reset per job. Persistent cross-job state, synchronized two-axis input,
continuous source/setting changes, active-loop timing/noninterference and device
integration remain separate work. No improvement to centering, comfort, accepted
tuning, runtime provenance or STEP1-10 physical qualification is claimed.
NOT_READY / REAL_VEHICLE_UNVERIFIED / VEHICLE_ACTIVATION_BLOCKED remain in force.
Actual Git delivery is recorded after successful gates, not inferred from this file.


## Source-bound closing record

Default supervisor receipt SHA256: `7032abfc732bc1e57ec8ba49019b2b1978e3ab0b687c34e28095df171ac7b031`.
Fresh repeat report SHA256: `580bcda612e22afdfbf90eb796dfe814794402687d6056de0c23e94c7112bf97`.
Pre-change and post-change five-variant native observation SHA256:
`1dbd7bfe40383803f72d8f85fbdb5e8f078ea8cf3938bdb8d644ff17d069680e`.
The independent review input was host-bound to these same source bytes and the
exact baseline native-worker Git object. Its verdict covers supplied code only;
all runtime gate results above were executed/observed by the host, not the reviewer.

Source identities:
- `openpilot/tools/cyber_autotune/lateral_continuity.py`: `5ff39041124d1fb3ed62ba4ba9629992e68f52ba260aed36816f207e9f6313b5`.
- `openpilot/tools/cyber_autotune/lateral_continuity_worker.py`: `41e3dc908b31e4914053c46fc0b371ccffd06764786ccff883e75016f6fc4717`.
- `openpilot/tools/cyber_autotune/native_worker.py`: `c79b75fd0a75d5dc58ebd459d80b89aeeb54bcd849afacd070cd2bace4bed1ac`.
- `openpilot/tools/cyber_autotune/tests/test_lateral_continuity.py`: `ea874c0073b4683fcf381b1d787ab15f878542b1bf73cfb173db7356b7574cd0`.

The original expected RED18 assertions remain preserved. No final test failure is
hidden by changing tests/ignores/thresholds/references. Optional reviewer suggestions
for injected premature/excess yields and BaseException coverage were explicitly not
bugs; they are not counted as executed tests. No production change was made after
review to manufacture approval. Result-only documentation follows the source-bound
run/review; executable hashes are unchanged. Source links/whitespace/privacy and
index/history scope must pass again before delivery. Post-commit verification and
actual local/remote equality are separately recorded, not presumed here.
