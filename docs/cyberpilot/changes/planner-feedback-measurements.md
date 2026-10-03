# Planner feedback measurements

## Identity and purpose

Cyber Validation, bounded diagnostic extension from
`2a17919614632c4dd6f72cac65a09f6751b1ed07`, feature/cyber-autotune.
Purpose: quantify the existing native planner/controller/generic-plant fixture
without selecting a tune, changing control, or confusing parity with performance.
The user delegated intermediate offline design/testing decisions; this is not
permission for vehicle deployment. Status: implemented and reviewed, offline only.

## References and design decision

Repository reference: https://github.com/rownlvh8875-coder/CyberPilot at the base
above, root MIT license. Reuse `test_cyber_long_feedback.py`'s three six-second
fixtures and unchanged upstream planner/LongControl sources. Upstream top-level
reference remains `c8fb906815530460ed156f14e09e1f312bb0f851`, sharing the pinned
current dependencies; opendbc `4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76`.
No Carrot/Sunny/Zoom logic, constants or private inputs copied.

Alternatives: (1) reinterpret the existing positional parity tuples, rejected
because pre-step inputs and post-step response cannot be fully distinguished;
(2) reuse supplied-plan v2 metrics wholesale, rejected because its mandatory
desired-distance/stop-position truth is absent here; (3) retain the parity tuple
unchanged and add separately typed measurement rows, selected. No existing
frozen v1/v2 metric, acceptance or evidence changes.

Native planner20Hz → LongControl100Hz → one plant-owned30ms command queue →
generic200ms first-order response → next planner input. CP's200ms compensation
is not a second physical command queue. The fixture CP is SYNTHETIC_PARITY_ONLY,
not the user's vehicle tune; model/lead/driver events are supplied, not inferred.
No inference, sockets, CarController, vehicle bus or calibrated physical model.

## Files and measurements

`test_cyber_long_feedback.py` adds observational rows only; original trace,
control execution, test assertions, plant and scenario parameters are retained.
`planner_feedback_metrics.py` is a pure read-only summarizer, imported only by
offline callers. Its tests check hand-computed values, invalid data, timing,
native delay alignment and repeatability. Rollback: omit this diagnostic module
and measurement rows; no active configuration exists to roll back.

Each row covers [time_s,time_s+dt_s]. Speed, acceleration, position, lead speed
and signed gap are interval-start plant values. Planner target and requested
command are at interval start; applied command is the delay queue output for
this interval. Response speed/acceleration are interval-end values. The original
parity tuple still contains its original mixed-stage values, not this schema.

| Metric | Definition / missing coverage |
| --- | --- |
| planner_tracking_rms_mps2 | RMS of start acceleration minus contemporaneous planner target, all frames |
| request_to_applied_rms_mps2 | RMS requested minus queue-output acceleration command; not actuator telemetry |
| command / actual jerk RMS | first differences at native dt; actual uses response acceleration; includes transition edges |
| minimum lead gap / TTC | simultaneous start states, lead-present frames only; negative gap retained, contact TTC0, no closing lead null |
| stop episode counts | active stop-demand runs, standstill sample at response speed≤0.01m/s; not stopping accuracy |
| restart delay | stop-demand release from standstill to response speed≥0.5m/s, response-end timestamp; unresolved/moving releases null |
| cut-in response | explicit exogenous event even when lead remains present, requested drop≥0.1m/s² from preceding command; unresolved null |
| inactive maximum request | maximum absolute requested acceleration while inactive, no inactive coverage null |
| stop-position / desired-follow error | always null: no independent targets supplied |

Stop/restart/drop thresholds describe event measurements, not new safety limits
or candidate acceptance. Cut-in response ends on another cut-in, lead loss or
inactive interval. No causal attribution or perception quality is claimed.
Timestamps must start at0 with declared dt, finite bounded values, strict booleans,
and continuous adjacent speed/acceleration states; invalid inputs raise ValueError
without partial output. This validates measurement shape, not physical truth.
All vehicle authority flags remain false; status is DESCRIPTIVE_ONLY/NOT_READY.

## Candidate domains and acceptance

The pinned SantaFe vehicle Ki remains zero: scaling by0.95/1.05 is ineffective.
`cyber_long/params.py` declares controller gain/delay as offline-research-only,
with unreviewed bounds; every tuning proposal remains accepted=False. No gain,
delay, stopAccel, personality, actuator limit or optimizer bound changes here.
Driver preference is not a tunable vehicle-physics estimate. Effective candidate
generation is BLOCKED pending separately justified bounds and identifiable input
domain. These descriptive metrics cannot promote a candidate or rank a new grid.

Engineering acceptance: existing four-arm parity unchanged; measurement rows align
with real fixture execution; hand-calculated cases catch time/stage errors;
missing coverage stays null; malformed rows fail closed; deterministic reruns.
No claim of comfort improvement, safe following, calibrated closed loop, qualified
process replay or device shadow. Existing safety/driver-override behavior untouched.

## Verification and handoff

Test-first: six expected assertion failures for absent module/measurement rows,
exit1. Initial implementation plus original parity tests:9passed,exit0. A further
regression exposed falsely calling a moving stop-demand release a restart; that
case failed before correction and now must remain null with an explicit count.
Focused tests including the existing feedback suite:10passed,exit0. Independent
review found no actionable findings and separately ran10tests/9subtests. Combined
AutoTune+controls:626passed,exit0,123.08s. Ruff and SCons passed; publication scanner
checked228files with0findings. The initial two Ruff literal-style findings were
corrected without ignores or behavioral changes.

Two complete fresh-process aggregate runs compare the original fixture from the
base Git object to all four current/reference/observer arms, preserving exact
legacy trace values and exact measurement equality. Complete report SHA-256:
`83b037cc914aaad3e561597eab13fad821c7ec5ae60534a09406e09ec6ba5237`.
The report binds source file hashes, base HEAD, submodules and Python version;
both runs are byte-identical. This is shared-dependency native parity, not two
independently reconstructed fork stacks.

| Supplied scenario | Planner tracking RMS m/s² | Command jerk RMS m/s³ | Actual jerk RMS m/s³ | Minimum gap m |
| --- | ---: | ---: | ---: | ---: |
| Lead transition | 0.455923 | 5.329606 | 1.997847 | 6.081398 |
| Stop/start | 0.283258 | 2.875205 | 1.473495 | 5.532146 |
| Driver cancellation | 0.138834 | 2.197488 | 0.477739 | 18.354573 |

Stop/start records one standstill episode and a2.87s launch delay to0.5m/s.
The explicit cut-in yields0s **requested-command** response (same control tick),
not instantaneous physical response. Inactive maximum request is0 in the cancel
case. Other event metrics are null where no coverage exists. No values constitute
an acceptance threshold or vehicle-performance claim. The full default regression
for this new executable overlay completed:1,533passed,42skipped,1xfailed,exit0,
249.50s. The external supervisor recorded no timeout, unchanged source/submodules
and verified public fixture, and no verification errors. Receipt SHA-256:
`931b63d2cd577509fe9ab524398cb3303d6d719ef4e4466f1677f43570a7d894`.
That receipt binds the executable overlay at execution; final documentation-only
updates are separately reviewed, not retroactively included in its source hashes.
Earlier1,526-test checkpoint remains historical. Independent review also checked
report source hashes, preserved Git-object identity and numerical claims; the
legacy comparison is value equality, while complete report bytes are identical.
No additional driving logs, holdout, private simulator or device access is needed.
Remaining work: predeclared performance policy and trusted candidate domain;
these are not created retroactively from whichever metrics happen to improve.
